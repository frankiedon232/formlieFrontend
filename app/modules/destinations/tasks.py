"""Workers for response storage (queue `destinations`): writing responses to their form's table, retrying failures
with growing waits (1 min, 5 min, 15 min, 1 h, then every 6 h), and backfills (earlier responses, in batches).

Beat runs the sweep every 30 seconds: deliveries whose time has come (missed or failed) and running backfills.
Every write is one response as one row (tables.row_for); a failure is recorded with its code, never its answers.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text, update

from app.core.db.session import db_session
from app.modules.data_sources import tables as T
from app.modules.data_sources.catalog import WriteError, write_row
from app.modules.data_sources.connect import ConnectError, connect
from app.modules.data_sources.models import DataSource
from app.modules.destinations.models import DestinationBackfill, DestinationDelivery, ResponseDestination
from app.modules.destinations.service import LEASE, fields_of, next_try, now
from app.modules.forms.models import Form
from app.modules.responses.models import Response
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.destinations")

BATCH = 100
SWEEP_ROWS = 500


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def file_links(subdomain: str, form_id: uuid.UUID, response_id: uuid.UUID, field_key: str):  # noqa: ANN201
    """Files as links to the response in the workspace (signing in shows them; the file itself never leaves)."""
    from app.core.security.refs import get_codec
    from app.modules.forms.answers import file_answers
    from app.modules.notifications.service import workspace_url

    codec = get_codec()

    def links(value: Any) -> list[str]:
        base = f"/forms/{codec.encode_id(str(form_id))}/responses?response={codec.encode_id(str(response_id))}"
        return [workspace_url(subdomain, f"{base}&file={field_key}.{i}") for i, _ in enumerate(file_answers(value))]
    return links


def row_of_response(destination: ResponseDestination, fields: list[dict[str, Any]], response: Response,
                    subdomain: str) -> dict[str, Any]:
    facts = {"id": str(response.id), "submitted_at": _iso(response.submitted_at), "form_version": response.form_version_no,
             "language": response.language, "number": response.number,
             "email": response.respondent_email or response.identity_email, "review_status": response.status}
    data = response.data or {}
    by_key = {f["key"]: f for f in fields}
    row = T.row_for(destination.columns, fields, data, facts, destination.settings)
    for column in destination.columns:  # files: their links, per question
        source = column.get("source")
        if source and source["kind"] == "field" and by_key.get(source["key"], {}).get("type") in T.FILES:
            link = file_links(subdomain, destination.form_id, response.id, source["key"])
            row[column["column"]] = T.row_for([column], fields, data, facts, destination.settings, link)[column["column"]]
    return row


async def deliver(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_ids: list[uuid.UUID],
                  subdomain: str = "") -> dict[str, int]:
    """Sends these deliveries (one destination each, grouped), over one connection per destination."""
    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    async with db_session("write", **scope) as db:
        deliveries = list((await db.execute(select(DestinationDelivery).where(
            DestinationDelivery.tenant_id == tenant_id, DestinationDelivery.id.in_(delivery_ids),
            DestinationDelivery.status.in_(("pending", "failed"))))).scalars())
        groups: dict[uuid.UUID, list[DestinationDelivery]] = {}
        for d in deliveries:
            groups.setdefault(d.destination_id, []).append(d)
        work = []
        for destination_id, items in groups.items():
            destination = await db.get(ResponseDestination, destination_id)
            if destination is None or destination.deleted_at is not None:
                for d in items:
                    d.next_attempt_at = None
                continue
            if destination.paused_at is not None:
                for d in items:
                    d.status, d.next_attempt_at = "held", None
                continue
            source = await db.get(DataSource, destination.datasource_id)
            form = await db.get(Form, destination.form_id)
            fields = await fields_of(db, form) if form else []
            responses = {r.id: r for r in (await db.execute(select(Response).where(
                Response.tenant_id == tenant_id, Response.id.in_([d.response_id for d in items])))).scalars()}
            taken = now()
            for d in items:  # the worker has them now; a change after this stamp wins over the result
                d.next_attempt_at, d.updated_at = taken + LEASE, taken
            stamps = {d.id: taken for d in items}
            work.append((destination, source, fields, items, responses, stamps))
    sent = failed = 0
    for destination, source, fields, items, responses, stamps in work:
        results = await _write_all(destination, source, fields, items, responses, subdomain)
        async with db_session("write", **scope) as db:
            for d in items:
                code = results.get(d.id)
                at = now()
                values: dict[str, Any] = {"attempts": DestinationDelivery.attempts + 1, "at": at, "updated_at": at}
                if code is None:
                    values.update(status="sent", sent_at=at, error_code=None, next_attempt_at=None)
                    sent += 1
                else:
                    values.update(status="failed", error_code=code, next_attempt_at=next_try(d.attempts + 1, at))
                    failed += 1
                # Changed again meanwhile (edited, retried): left pending for the next send.
                await db.execute(update(DestinationDelivery).where(
                    DestinationDelivery.id == d.id, DestinationDelivery.tenant_id == tenant_id,
                    DestinationDelivery.updated_at == stamps[d.id]).values(**values))
            if source is not None:
                from app.modules.data_sources.service import count_op

                await count_op(db, source, len(items))
            failures = sum(1 for d in items if results.get(d.id) is not None)
            if failures:  # the platform's operations analytics (PLATFORM-ADMIN-INTEGRATION §4)
                from app.modules.platform_bridge.events import emit

                await emit(db, "destination.failed", {"destination_id": str(destination.id), "failed": failures,
                                                      "sent": len(items) - failures},
                           tenant_id=tenant_id, organisation_id=organisation_id, source="worker")
    return {"sent": sent, "failed": failed}


async def _write_all(destination: ResponseDestination, source: DataSource | None, fields: list[dict[str, Any]],
                     items: list[DestinationDelivery], responses: dict[uuid.UUID, Response], subdomain: str) -> dict[uuid.UUID, str | None]:
    """delivery id → None (written) or the error code."""
    if source is None or source.deleted_at is not None:
        return {d.id: "FRM-DEST-1001" for d in items}
    if not source.enabled:
        return {d.id: "FRM-DEST-1009" for d in items}
    from app.modules.data_sources.service import target_of

    results: dict[uuid.UUID, str | None] = {}
    try:
        async with connect(target_of(source)) as c:
            for d in items:
                response = responses.get(d.response_id)
                if response is None:
                    results[d.id] = "FRM-DEST-1025"
                    continue
                try:
                    row = row_of_response(destination, fields, response, subdomain)
                    await write_row(c, source.engine, destination.table_schema, destination.table_name,
                                    destination.columns, row, destination.settings)
                    results[d.id] = None
                except WriteError as error:
                    log.info("delivery refused", extra={"delivery_id": str(d.id), "code": error.code, "error": error.detail})
                    results[d.id] = error.code
    except ConnectError as error:
        for d in items:
            results.setdefault(d.id, error.code)
    except Exception:  # noqa: BLE001 (a connection that breaks halfway: the rest is retried)
        log.exception("delivery batch failed", extra={"destination_id": str(destination.id)})
        for d in items:
            results.setdefault(d.id, "FRM-DEST-1001")
    return results


# ── Backfills ───────────────────────────────────────────────────────────────────

async def run_backfill(tenant_id: uuid.UUID, organisation_id: uuid.UUID, job_id: uuid.UUID, subdomain: str = "") -> None:
    """Sends the job's responses in batches, counting progress; done when none are left."""
    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    while True:
        async with db_session("write", **scope) as db:
            job = await db.get(DestinationBackfill, job_id)
            if job is None or job.status != "running":
                return
            destination = await db.get(ResponseDestination, job.destination_id)
            if destination is None or destination.deleted_at is not None:
                job.status, job.finished_at = "done", now()
                return
            batch = list((await db.execute(select(Response).where(
                Response.tenant_id == tenant_id, Response.form_id == destination.form_id, Response.deleted_at.is_(None),
                Response.submitted_at >= job.range_from, Response.submitted_at <= job.range_to,
                ~select(DestinationDelivery.id).where(
                    DestinationDelivery.tenant_id == tenant_id, DestinationDelivery.destination_id == destination.id,
                    DestinationDelivery.response_id == Response.id).exists())
                .order_by(Response.submitted_at).limit(BATCH))).scalars())
            if not batch:
                job.status, job.finished_at, job.done = "done", now(), job.total
                destination.covers_from = min(destination.covers_from, job.range_from)
                return
            ids = []
            for r in batch:
                d = DestinationDelivery(id=uuid.uuid4(), tenant_id=tenant_id, organisation_id=organisation_id,
                                        destination_id=destination.id, response_id=r.id, response_submitted_at=r.submitted_at,
                                        status="pending", attempts=0, next_attempt_at=now() + LEASE)
                db.add(d)
                ids.append(d.id)
        await deliver(tenant_id, organisation_id, ids, subdomain)
        async with db_session("write", **scope) as db:
            await db.execute(update(DestinationBackfill).where(DestinationBackfill.id == job_id,
                                                               DestinationBackfill.tenant_id == tenant_id)
                             .values(done=func.least(DestinationBackfill.done + len(ids), DestinationBackfill.total)))


# ── The sweep ───────────────────────────────────────────────────────────────────

async def sweep() -> int:
    """Deliveries whose time has come (missed or failed) and running backfills, per workspace."""
    async with db_session("read") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id, subdomain, delivery_id "
                                     "FROM platform.deliveries_due(:n)"), {"n": SWEEP_ROWS})).all()
        jobs = (await db.execute(text("SELECT tenant_id, organisation_id, subdomain, backfill_id "
                                      "FROM platform.backfills_running()"))).all()
    by_workspace: dict[tuple[uuid.UUID, uuid.UUID, str], list[uuid.UUID]] = {}
    for tenant_id, organisation_id, subdomain, delivery_id in due:
        by_workspace.setdefault((tenant_id, organisation_id, subdomain), []).append(delivery_id)
    for (tenant_id, organisation_id, subdomain), ids in by_workspace.items():
        try:
            await deliver(tenant_id, organisation_id, ids, subdomain)
        except Exception:  # noqa: BLE001 (one workspace never stops the others)
            log.exception("delivery sweep failed", extra={"tenant_id": str(tenant_id)})
    for tenant_id, organisation_id, subdomain, job_id in jobs:
        if await _claim(f"backfill:{job_id}"):
            try:
                await run_backfill(tenant_id, organisation_id, job_id, subdomain)
            except Exception:  # noqa: BLE001
                log.exception("backfill failed", extra={"backfill_id": str(job_id)})
    return len(due)


async def _claim(key: str) -> bool:
    """One worker per backfill at a time (a lock that expires)."""
    from app.core.cache.redis import get_redis

    try:
        return bool(await get_redis().set(f"lock:destinations:{key}", "1", nx=True, ex=600))
    except Exception:  # noqa: BLE001
        return True


# ── Celery ──────────────────────────────────────────────────────────────────────

def _run(coroutine: Any) -> Any:
    from app.core.db.engines import dispose_engines

    async def wrapped() -> Any:
        try:
            return await coroutine
        finally:
            await dispose_engines()
    return asyncio.run(wrapped())


@celery_app.task(name="destinations.deliver", ignore_result=True, acks_late=True)
def deliver_task(tenant_id: str, organisation_id: str, delivery_ids: list[str], subdomain: str = "") -> None:
    _run(deliver(uuid.UUID(tenant_id), uuid.UUID(organisation_id), [uuid.UUID(i) for i in delivery_ids], subdomain))


@celery_app.task(name="destinations.backfill", ignore_result=True, acks_late=True)
def backfill_task(tenant_id: str, organisation_id: str, job_id: str, subdomain: str = "") -> None:
    async def run() -> None:
        if await _claim(f"backfill:{job_id}"):
            await run_backfill(uuid.UUID(tenant_id), uuid.UUID(organisation_id), uuid.UUID(job_id), subdomain)
    _run(run())


@celery_app.task(name="destinations.sweep", ignore_result=True)
def sweep_task() -> None:
    _run(sweep())


def dispatch_delivery(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_id: uuid.UUID, subdomain: str) -> None:
    """To the `destinations` queue, after the change committed. Tests replace this."""
    deliver_task.apply_async(args=[str(tenant_id), str(organisation_id), [str(delivery_id)], subdomain], queue="destinations")


def dispatch_backfill(tenant_id: uuid.UUID, organisation_id: uuid.UUID, job_id: uuid.UUID, subdomain: str) -> None:
    backfill_task.apply_async(args=[str(tenant_id), str(organisation_id), str(job_id), subdomain], queue="destinations")

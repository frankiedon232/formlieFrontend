"""Response storage as the app sees it (mock: data/destinationStore.ts): where a form's responses are kept, the rows
and detail of each destination, every response with its delivery, and queueing deliveries.

A delivery is recorded with the response (same transaction) and sent by the worker right after the commit; a sweep
(Beat) sends what was missed and retries failures with growing waits. A response without a delivery was never sent
(it came before the destination covered it; a backfill sends those).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import after_commit
from app.modules.data_sources import tables as T
from app.modules.data_sources.models import DataSource, DataSourceTest
from app.modules.data_sources.service import iso, status_of_source
from app.modules.destinations.models import DestinationBackfill, DestinationDelivery, ResponseDestination
from app.modules.forms.models import Form
from app.modules.public.submit import all_fields, is_input_field
from app.modules.responses.models import Response

DAY = timedelta(days=1)
BACKOFF_S = (60, 300, 900, 3600, 6 * 3600)
LEASE = timedelta(seconds=120)  # a delivery just queued is the worker's; the sweep leaves it alone this long
FORMALIE_MARK = {"mode": "formalie", "datasource": None, "engine": None}


def now() -> datetime:
    return datetime.now(UTC)


def next_try(attempts: int, at: datetime) -> datetime:
    return at + timedelta(seconds=BACKOFF_S[min(max(attempts, 1), len(BACKOFF_S)) - 1])


def input_fields(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    """The form's answer fields (what gets a column)."""
    return [f for f in all_fields(schema or {"pages": []}) if is_input_field(f.get("type", "")) and f.get("key")]


async def fields_of(db: AsyncSession, form: Form) -> list[dict[str, Any]]:
    from app.modules.responses.service import response_schema

    return input_fields(await response_schema(db, form))


async def destinations_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[ResponseDestination]:
    return list((await db.execute(select(ResponseDestination).where(
        ResponseDestination.tenant_id == tenant_id, ResponseDestination.deleted_at.is_(None)))).scalars())


async def destination_of_form(db: AsyncSession, tenant_id: uuid.UUID, form_id: uuid.UUID) -> ResponseDestination | None:
    return (await db.execute(select(ResponseDestination).where(
        ResponseDestination.tenant_id == tenant_id, ResponseDestination.form_id == form_id,
        ResponseDestination.deleted_at.is_(None)))).scalar_one_or_none()


async def storage_marks(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, dict[str, Any]]:
    """Every form that stores in a database: form id → connection name and engine (for the form and response lists)."""
    rows = (await db.execute(select(ResponseDestination.form_id, DataSource.name, DataSource.engine).join(
        DataSource, (DataSource.tenant_id == ResponseDestination.tenant_id) & (DataSource.id == ResponseDestination.datasource_id))
        .where(ResponseDestination.tenant_id == tenant_id, ResponseDestination.deleted_at.is_(None)))).all()
    return {form_id: {"mode": "database", "datasource": name, "engine": engine} for form_id, name, engine in rows}


# ── Queueing ────────────────────────────────────────────────────────────────────

def queue(db: AsyncSession, delivery: DestinationDelivery) -> None:
    """Sent by the worker once this transaction committed."""
    from app.modules.destinations import tasks

    tenant_id, organisation_id, delivery_id = delivery.tenant_id, delivery.organisation_id, delivery.id
    subdomain = request_subdomain()
    after_commit(db, lambda: tasks.dispatch_delivery(tenant_id, organisation_id, delivery_id, subdomain))


def request_subdomain() -> str:
    """The workspace this request is for (links to files in rows go to its portal)."""
    from app.core.context import get_context

    ctx = get_context()
    return ctx.tenant.subdomain if ctx and ctx.tenant else ""


async def response_stored(db: AsyncSession, form: Form, response: Response) -> None:
    """A new response: on its way to the form's table (held while the destination is paused)."""
    destination = await destination_of_form(db, form.tenant_id, form.id)
    if destination is None:
        return
    paused = destination.paused_at is not None
    delivery = DestinationDelivery(
        id=uuid.uuid4(), tenant_id=form.tenant_id, organisation_id=form.organisation_id, destination_id=destination.id,
        response_id=response.id, response_submitted_at=response.submitted_at, status="held" if paused else "pending",
        attempts=0, next_attempt_at=None if paused else now() + LEASE)
    db.add(delivery)
    await db.flush()
    if not paused:
        queue(db, delivery)


async def response_changed(db: AsyncSession, form: Form, response: Response) -> None:
    """An edited answer or a review change: sent again when the table keeps one row per response (update-or-insert)."""
    destination = await destination_of_form(db, form.tenant_id, form.id)
    if destination is None or destination.settings.get("write_mode") != "upsert":
        return
    delivery = (await db.execute(select(DestinationDelivery).where(
        DestinationDelivery.tenant_id == form.tenant_id, DestinationDelivery.destination_id == destination.id,
        DestinationDelivery.response_id == response.id))).scalar_one_or_none()
    if delivery is None or delivery.status == "held":
        return
    delivery.status, delivery.next_attempt_at, delivery.updated_at = "pending", now() + LEASE, now()
    await db.flush()
    queue(db, delivery)


async def stop_deliveries(db: AsyncSession, destination: ResponseDestination) -> None:
    """The destination is gone: nothing more is sent (the rows stay as they are)."""
    await db.execute(update(DestinationDelivery).where(
        DestinationDelivery.tenant_id == destination.tenant_id, DestinationDelivery.destination_id == destination.id,
        DestinationDelivery.status.in_(("pending", "failed"))).values(next_attempt_at=None))


# ── Rows and detail ─────────────────────────────────────────────────────────────

class Facts:
    """What a list of destinations needs, read once: forms, connections and their status, delivery counts."""

    def __init__(self) -> None:
        self.forms: dict[uuid.UUID, Form] = {}
        self.fields: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self.sources: dict[uuid.UUID, DataSource] = {}
        self.source_status: dict[uuid.UUID, str] = {}
        self.counts: dict[uuid.UUID, dict[str, int]] = {}
        self.daily: dict[uuid.UUID, dict[date, int]] = {}
        self.last: dict[uuid.UUID, datetime] = {}
        self.recent_failed: set[uuid.UUID] = set()

    async def load(self, db: AsyncSession, tenant_id: uuid.UUID, destinations: list[ResponseDestination]) -> Facts:
        if not destinations:
            return self
        ids = [d.id for d in destinations]
        forms = (await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.id.in_([d.form_id for d in destinations]),
                                                     Form.deleted_at.is_(None)))).scalars()
        for form in forms:
            self.forms[form.id] = form
            self.fields[form.id] = await fields_of(db, form)
        sources = list((await db.execute(select(DataSource).where(
            DataSource.tenant_id == tenant_id, DataSource.id.in_([d.datasource_id for d in destinations]),
            DataSource.deleted_at.is_(None)))).scalars())
        tests = {t.id: t for t in (await db.execute(select(DataSourceTest).where(
            DataSourceTest.tenant_id == tenant_id, DataSourceTest.id.in_([s.last_test_id for s in sources if s.last_test_id])))).scalars()}
        for s in sources:
            self.sources[s.id] = s
            self.source_status[s.id] = status_of_source(s, tests.get(s.last_test_id) if s.last_test_id else None)
        live = (DestinationDelivery.tenant_id == tenant_id) & DestinationDelivery.destination_id.in_(ids)
        for dest_id, status, n in (await db.execute(select(DestinationDelivery.destination_id, DestinationDelivery.status,
                                                           func.count()).where(live).group_by(
                DestinationDelivery.destination_id, DestinationDelivery.status))).all():
            self.counts.setdefault(dest_id, {})[status] = n
        since = datetime.combine(now().date() - timedelta(days=59), datetime.min.time(), UTC)
        day = func.date(func.timezone("UTC", DestinationDelivery.sent_at))
        for dest_id, d, n in (await db.execute(select(DestinationDelivery.destination_id, day, func.count()).where(
                live, DestinationDelivery.status == "sent", DestinationDelivery.sent_at >= since)
                .group_by(DestinationDelivery.destination_id, day))).all():
            self.daily.setdefault(dest_id, {})[d] = n
        for dest_id, at in (await db.execute(select(DestinationDelivery.destination_id, func.max(DestinationDelivery.sent_at))
                                             .where(live).group_by(DestinationDelivery.destination_id))).all():
            if at:
                self.last[dest_id] = at
        recent = (await db.execute(text("""
            SELECT DISTINCT destination_id FROM (
                SELECT destination_id, status, row_number() OVER (PARTITION BY destination_id
                       ORDER BY response_submitted_at DESC) AS n
                  FROM formaly.destination_deliveries WHERE tenant_id = :t AND destination_id = ANY(:ids)) x
             WHERE n <= 50 AND status = 'failed'"""), {"t": tenant_id, "ids": ids})).scalars()
        self.recent_failed = set(recent)
        return self


def status_of(destination: ResponseDestination, facts: Facts) -> str:
    if destination.paused_at is not None:
        return "paused"
    if facts.source_status.get(destination.datasource_id, "failing") in ("failing", "disabled"):
        return "failing"
    return "failing" if destination.id in facts.recent_failed else "active"


def _mapped(destination: ResponseDestination) -> set[str]:
    return {c["source"]["key"] for c in destination.columns if c.get("source") and c["source"]["kind"] == "field"}


def daily_of(facts: Facts, destination_id: uuid.UUID, offset: int = 0) -> list[dict[str, Any]]:
    today = now().date()
    sent = facts.daily.get(destination_id, {})
    days = [today - timedelta(days=29 - i + offset) for i in range(30)]
    return [{"date": d.isoformat(), "count": sent.get(d, 0)} for d in days]


def row_of(destination: ResponseDestination, facts: Facts, names: Any) -> dict[str, Any] | None:
    """DestinationRow (shared/types/destinations.ts); None when its form or connection is gone."""
    form = facts.forms.get(destination.form_id)
    source = facts.sources.get(destination.datasource_id)
    if form is None or source is None:
        return None
    counts = facts.counts.get(destination.id, {})
    daily = daily_of(facts, destination.id)
    mapped = _mapped(destination)
    return {
        "id": str(destination.id), "form": {"id": str(form.id), "name": form.name, "status": form.status},
        "datasource": {"id": str(source.id), "name": source.name, "engine": source.engine,
                       "status": facts.source_status.get(source.id, "untested")},
        "table": {"schema": destination.table_schema, "name": destination.table_name, "created": destination.table_created},
        "status": status_of(destination, facts), "settings": destination.settings,
        "sent_30d": sum(d["count"] for d in daily), "pending": counts.get("pending", 0) + counts.get("held", 0),
        "failed": counts.get("failed", 0), "last_delivery_at": iso(facts.last.get(destination.id)), "daily": daily,
        "new_fields": sum(1 for f in facts.fields.get(form.id, []) if f["key"] not in mapped),
        "created_by": names.ref(destination.created_by) or {"id": "", "name": ""},
        "created_at": iso(destination.created_at), "updated_at": iso(destination.updated_at),
    }


def backfill_view(job: DestinationBackfill | None) -> dict[str, Any] | None:
    if job is None:
        return None
    return {"id": str(job.id), "from": iso(job.range_from), "to": iso(job.range_to), "total": job.total, "done": job.done,
            "status": job.status, "started_at": iso(job.started_at), "finished_at": iso(job.finished_at)}


async def latest_backfill(db: AsyncSession, destination: ResponseDestination) -> DestinationBackfill | None:
    return (await db.execute(select(DestinationBackfill).where(
        DestinationBackfill.tenant_id == destination.tenant_id, DestinationBackfill.destination_id == destination.id)
        .order_by(DestinationBackfill.started_at.desc()).limit(1))).scalar_one_or_none()


async def not_sent_count(db: AsyncSession, destination: ResponseDestination) -> int:
    return int((await db.execute(select(func.count()).select_from(Response).where(
        Response.tenant_id == destination.tenant_id, Response.form_id == destination.form_id, Response.deleted_at.is_(None),
        ~select(DestinationDelivery.id).where(
            DestinationDelivery.tenant_id == destination.tenant_id, DestinationDelivery.destination_id == destination.id,
            DestinationDelivery.response_id == Response.id).exists()))).scalar_one())


async def detail_of(db: AsyncSession, destination: ResponseDestination, names: Any) -> dict[str, Any]:
    facts = await Facts().load(db, destination.tenant_id, [destination])
    row = row_of(destination, facts, names)
    if row is None:
        from app.core.errors import FrmError

        raise FrmError("FRM-GEN-1004")
    source = facts.sources[destination.datasource_id]
    fields = facts.fields.get(destination.form_id, [])
    mapped = _mapped(destination)
    taken = {c["column"].lower() for c in destination.columns}
    unmapped = []
    for f in fields:
        if f["key"] in mapped:
            continue
        label = f.get("label")
        unmapped.append({"key": f["key"], "label": f["key"] if label is None else label,
                         "column": T.column_name_for(source.engine, f["key"], taken),
                         "type": T.column_type_for(source.engine, f, destination.settings["multi_value"])})
    return {
        **row, "columns": destination.columns,
        "fields": [{"key": f["key"], "label": f["key"] if f.get("label") is None else f["label"]} for f in fields],
        "unmapped_fields": unmapped, "backfill": backfill_view(await latest_backfill(db, destination)),
        "covers_from": iso(destination.covers_from), "not_sent": await not_sent_count(db, destination),
    }


async def deliveries_of(db: AsyncSession, destination: ResponseDestination, form: Form) -> list[dict[str, Any]]:
    """Every response of the form with its delivery, newest first (Delivery, shared/types/destinations.ts)."""
    from app.modules.responses.service import Entry, response_schema, responses_of

    schema = await response_schema(db, form)
    responses = await responses_of(db, destination.tenant_id, [form.id])
    by_response = {d.response_id: d for d in (await db.execute(select(DestinationDelivery).where(
        DestinationDelivery.tenant_id == destination.tenant_id, DestinationDelivery.destination_id == destination.id))).scalars()}
    out = []
    for r in sorted(responses, key=lambda r: r.submitted_at, reverse=True):
        d = by_response.get(r.id)
        base = {"response_id": str(r.id), "number": r.number, "submitted_at": iso(r.submitted_at),
                "respondent": Entry(r, form, schema).title}
        if d is None:
            out.append({**base, "status": "not_sent", "attempts": 0, "error_code": None, "at": None, "next_retry_at": None})
        else:
            out.append({**base, "status": d.status, "attempts": d.attempts, "error_code": d.error_code,
                        "at": iso(d.sent_at if d.status == "sent" else d.at),
                        "next_retry_at": iso(d.next_attempt_at) if d.status in ("pending", "failed") else None})
    return out

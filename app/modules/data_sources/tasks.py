"""Workers for data sources (queue `destinations`): connection tests, step by step, and health checks of every
enabled connection (Beat, every five minutes)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text, update

from app.core.db.session import db_session
from app.core.security.fernet_tokens import decrypt_secret
from app.modules.data_sources.connect import Target
from app.modules.data_sources.models import DataSource, DataSourceCheck, DataSourceTest
from app.modules.data_sources.probe import health_check, run_test, status_of
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.datasources")


async def run_connection_test(test_id: uuid.UUID, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> None:
    """Runs a test, writing each step as it finishes; then the connection's status, its count and the audit trail."""
    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    async with db_session("write", **scope) as db:
        test = await db.get(DataSourceTest, test_id)
        if test is None or test.status != "running" or not test.config_enc:
            return
        config = json.loads(decrypt_secret(test.config_enc))

    async def report(state: dict[str, Any]) -> None:
        async with db_session("write", **scope) as db:
            await db.execute(update(DataSourceTest).where(DataSourceTest.id == test_id).values(steps=state["steps"]))

    target = Target(config["engine"], config["settings"], config.get("secrets") or {})
    try:
        result = await run_test(target, config["access"], report)
    except Exception:  # noqa: BLE001 (a test must always finish)
        log.exception("connection test crashed", extra={"test_id": str(test_id)})
        result = {"steps": None}
    async with db_session("write", **scope) as db:
        test = await db.get(DataSourceTest, test_id)
        if test is None:
            return
        steps = list(test.steps)
        if any(s["status"] in ("pending", "running") for s in steps) and not any(s["status"] == "failed" for s in steps):
            steps = [{**s, "status": "failed" if s["status"] == "running" else "skipped"} if s["status"] in ("pending", "running")
                     else s for s in steps]
        test.steps = steps
        for key in ("server_version", "latency_ms", "permissions", "findings", "schemas", "tables_count"):
            if key in result:
                setattr(test, key, result[key])
        test.status = status_of(steps, test.findings or [])
        test.finished_at = datetime.now(UTC)
        test.config_enc = None  # the secrets it carried are gone
        source = await db.get(DataSource, test.datasource_id) if test.datasource_id else None
        if source is not None and source.last_test_id == test.id:
            from app.modules.data_sources.service import count_op

            await count_op(db, source)
        await _audit_test(db, test, source)


async def _audit_test(db: Any, test: DataSourceTest, source: DataSource | None) -> None:
    from app.modules.audit.service import Actor, record
    from app.modules.users.models import User

    user = await db.get(User, test.created_by) if test.created_by else None
    code = next((s["error_code"] for s in test.steps if s.get("error_code")), None)
    await record(db, tenant_id=test.tenant_id, organisation_id=test.organisation_id, action="data.connection_tested",
                 actor=Actor.user(user) if user else Actor.system(),
                 outcome="failure" if test.status == "failed" else "success",
                 resource={"type": "data_source", "id": str(source.id) if source else None,
                           "name": source.name if source else test.label},
                 metadata={"result": test.status, **({"code": code} if code else {})})
    test.audited = True


async def check_one(tenant_id: uuid.UUID, organisation_id: uuid.UUID, datasource_id: uuid.UUID) -> None:
    from app.modules.data_sources.service import count_op, target_of

    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    async with db_session("read", **scope) as db:
        source = await db.get(DataSource, datasource_id)
        if source is None or not source.enabled or source.deleted_at:
            return
        target = target_of(source)
    result = await health_check(target)
    async with db_session("write", **scope) as db:
        source = await db.get(DataSource, datasource_id)
        if source is None:
            return
        db.add(DataSourceCheck(tenant_id=tenant_id, organisation_id=organisation_id, datasource_id=datasource_id,
                               at=datetime.now(UTC), **result))
        await count_op(db, source)


async def check_all() -> int:
    async with db_session("read") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id, datasource_id FROM platform.datasources_due()"))).all()
    for tenant_id, organisation_id, datasource_id in due:
        try:
            await check_one(tenant_id, organisation_id, datasource_id)
        except Exception:  # noqa: BLE001 (one connection never stops the others)
            log.exception("health check failed", extra={"datasource_id": str(datasource_id)})
    return len(due)


def _run(coroutine: Any) -> Any:
    from app.core.db.engines import dispose_engines

    async def wrapped() -> Any:
        try:
            return await coroutine
        finally:
            await dispose_engines()
    return asyncio.run(wrapped())


@celery_app.task(name="datasources.test", ignore_result=True, acks_late=True)
def connection_test_task(test_id: str, tenant_id: str, organisation_id: str) -> None:
    _run(run_connection_test(uuid.UUID(test_id), uuid.UUID(tenant_id), uuid.UUID(organisation_id)))


@celery_app.task(name="datasources.health", ignore_result=True)
def health_task() -> None:
    _run(check_all())


def dispatch_test(test: DataSourceTest) -> None:
    """To the `destinations` queue, after the request committed. Tests replace this."""
    connection_test_task.apply_async(args=[str(test.id), str(test.tenant_id), str(test.organisation_id)], queue="destinations")


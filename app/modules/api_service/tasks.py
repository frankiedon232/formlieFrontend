"""API service upkeep (queue `scheduled`):
- request log bodies of public API calls are kept only as long as each workspace chose (`api_settings.log_days`: 1, 7
  or 30 days); the call itself stays in the log for the counts (DATABASE-DESIGN);
- Formalie-Keys (`api_idempotency`) answer replays for 24 hours, then they are retired (soft deleted)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.db.session import db_session
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.api_service")


async def prune_log_bodies() -> int:
    """Request log bodies older than each workspace keeps them are cleared (traffic.prune_bodies)."""
    from app.modules.api_service.traffic import prune_bodies

    async with db_session("read") as db:
        workspaces = (await db.execute(text("SELECT tenant_id, organisation_id, log_days "
                                            "FROM platform.api_log_body_settings()"))).all()
    cleared = 0
    for tenant_id, organisation_id, days in workspaces:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                cleared += await prune_bodies(db, tenant_id, days)
        except Exception:  # noqa: BLE001
            log.exception("pruning request log bodies failed", extra={"tenant_id": str(tenant_id)})
    return cleared


@celery_app.task(name="api_service.prune_log_bodies", ignore_result=True)
def prune_log_bodies_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await prune_log_bodies()
        finally:
            await dispose_engines()
    asyncio.run(run())


async def expire_call_keys() -> int:
    """Formalie-Keys older than 24 hours are retired, in every workspace that has some."""
    from sqlalchemy import update

    from app.modules.api_service.models import ApiIdempotency

    async with db_session("read") as db:
        workspaces = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.api_idempotency_expired()"))).all()
    retired = 0
    for tenant_id, organisation_id in workspaces:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                result = await db.execute(update(ApiIdempotency).where(
                    ApiIdempotency.tenant_id == tenant_id, ApiIdempotency.deleted_at.is_(None),
                    ApiIdempotency.at < text("now() - interval '24 hours'")).values(deleted_at=text("now()")))
                retired += result.rowcount or 0  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            log.exception("retiring Formalie-Keys failed", extra={"tenant_id": str(tenant_id)})
    return retired


@celery_app.task(name="api_service.expire_call_keys", ignore_result=True)
def expire_call_keys_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await expire_call_keys()
        finally:
            await dispose_engines()
    asyncio.run(run())

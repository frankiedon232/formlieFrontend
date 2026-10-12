"""AI assistant upkeep (queue `scheduled`): requests past each workspace's keep setting (30, 90, 180 or 365 days) are
emptied (prompt, result and draft) and soft deleted; the rows stay for the month's usage."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.db.session import db_session
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.ai")


async def expire_requests() -> int:
    from app.modules.ai.service import expire

    async with db_session("read") as db:
        workspaces = (await db.execute(text("SELECT tenant_id, organisation_id, keep_days "
                                            "FROM platform.ai_requests_expired()"))).all()
    emptied = 0
    for tenant_id, organisation_id, keep_days in workspaces:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                emptied += await expire(db, tenant_id, keep_days)
        except Exception:  # noqa: BLE001
            log.exception("emptying expired AI requests failed", extra={"tenant_id": str(tenant_id)})
    return emptied


@celery_app.task(name="ai.expire_requests", ignore_result=True)
def expire_requests_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await expire_requests()
        finally:
            await dispose_engines()
    asyncio.run(run())

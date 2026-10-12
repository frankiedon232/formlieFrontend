"""Response retention once a day (queue `scheduled`): in every workspace, responses older than their form's limit are
erased in place (privacy.service.apply_retention; the mock runs it once a day per workspace)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.db.session import db_session
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.privacy")


async def apply_everywhere() -> int:
    from app.modules.privacy.service import apply_retention

    async with db_session("read") as db:
        workspaces = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.retention_workspaces()"))).all()
    removed = 0
    for tenant_id, organisation_id in workspaces:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                removed += await apply_retention(db, tenant_id, organisation_id)
        except Exception:  # noqa: BLE001
            log.exception("retention failed", extra={"tenant_id": str(tenant_id)})
    return removed


@celery_app.task(name="privacy.apply_retention", ignore_result=True)
def apply_retention_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await apply_everywhere()
        finally:
            await dispose_engines()
    asyncio.run(run())

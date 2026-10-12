"""Request log upkeep (queue `scheduled`): bodies of public API calls are kept only as long as each workspace chose
(`api_settings.log_days`: 1, 7 or 30 days); the call itself stays in the log for the counts (DATABASE-DESIGN)."""

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

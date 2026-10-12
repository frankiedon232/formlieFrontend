"""Forms upkeep (queue `scheduled`; query review Q11): every 5 minutes, forms in Trash longer than 30 days are purged
in every workspace that has any (service.sweep_trash; the rows stay, with purged_at). The forms list used to do this
on every request; it now only reads, and leaves out what this sweep is about to purge."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.db.session import db_session
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.forms")


async def sweep_trash_everywhere() -> int:
    """→ how many workspaces were swept."""
    from app.modules.forms.service import sweep_trash

    async with db_session("read") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.trash_due_workspaces()"))).all()
    swept = 0
    for tenant_id, organisation_id in due:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                await sweep_trash(db, tenant_id)
            swept += 1
        except Exception:  # noqa: BLE001 (one workspace failing never stops the others)
            log.exception("trash sweep failed", extra={"tenant_id": str(tenant_id)})
    return swept


@celery_app.task(name="forms.sweep_trash", ignore_result=True)
def sweep_trash_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await sweep_trash_everywhere()
        finally:
            await dispose_engines()
    asyncio.run(run())

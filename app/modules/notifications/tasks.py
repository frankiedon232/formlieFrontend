"""Notifications upkeep (queue `scheduled`; query review Q11): every minute, in each workspace with something due
(a published form closing within a day, or daily summary lines waiting), service.announce_due announces the closing
forms once per closing time and sends the daily summaries once their hour has come. GET /notifications used to do
this on every poll; it now only reads."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from app.core.db.session import db_session
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.notifications")


async def announce_everywhere() -> int:
    """→ how many workspaces were looked at."""
    from app.modules.notifications.service import announce_due

    async with db_session("read") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id, subdomain, name "
                                     "FROM platform.notification_due_workspaces()"))).all()
    done = 0
    for tenant_id, organisation_id, subdomain, name in due:
        try:
            async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
                await announce_due(db, tenant_id, organisation_id, {"name": name, "subdomain": subdomain})
            done += 1
        except Exception:  # noqa: BLE001 (one workspace failing never stops the others)
            log.exception("due notifications failed", extra={"tenant_id": str(tenant_id)})
    return done


@celery_app.task(name="notifications.announce_due", ignore_result=True)
def announce_due_task() -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> Any:
        try:
            return await announce_everywhere()
        finally:
            await dispose_engines()
    asyncio.run(run())

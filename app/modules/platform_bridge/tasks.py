"""Platform bridge upkeep (queue `scheduled`): support access past its end is closed every minute (grants, sessions,
unused tickets, requests nobody answered), with the audit entries. Access itself already stops at the end."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.platform")


@celery_app.task(name="platform.expire_support_access", ignore_result=True)
def expire_support_access_task() -> None:
    from app.core.db.engines import dispose_engines
    from app.modules.platform_bridge.support import expire_due

    async def run() -> Any:
        try:
            return await expire_due()
        finally:
            await dispose_engines()

    closed = asyncio.run(run())
    if closed:
        log.info("support access closed", extra={"count": closed})

"""Celery tasks of the exports module (queue `exports`)."""

from __future__ import annotations

import asyncio
import uuid

from app.core.db.engines import dispose_engines
from app.modules.exports import service
from app.workers.celery_app import celery_app


async def _run(job_id: str, tenant_id: str, organisation_id: str) -> None:
    import app.modules.audit.export  # noqa: F401  (registers the audit trail's file)
    import app.modules.responses.exports  # noqa: F401  (registers responses' files)
    import app.modules.explorer.exports  # noqa: F401  (registers the explorer's and the Query editor's files)
    import app.modules.platform_bridge.workspace_export  # noqa: F401  (a whole workspace, for the platform admin)

    try:
        await service.build(uuid.UUID(job_id), uuid.UUID(tenant_id), uuid.UUID(organisation_id))
    finally:
        await dispose_engines()  # each task runs in its own event loop: no pooled connection outlives it


@celery_app.task(name="exports.build", ignore_result=True, acks_late=True, max_retries=2,
                 autoretry_for=(ConnectionError, OSError), retry_backoff=True)
def build_export(job_id: str, tenant_id: str, organisation_id: str) -> None:
    asyncio.run(_run(job_id, tenant_id, organisation_id))

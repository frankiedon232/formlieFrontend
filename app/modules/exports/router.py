"""Export jobs and their one-time download links (mock: routes/audit.ts getExportJob, download)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response

from app.core import storage
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.exports import service
from app.modules.exports.models import ExportJob

router = APIRouter(tags=["exports"])

EXPIRED = "This download link has expired. Start a new export."


@router.get("/exports/{job_id}", dependencies=[rate_limit("export-get", per_minute=120)])
async def get_export_job(job_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """Progress of an export: the person who started it, or someone who manages the workspace (mock: requireAdmin)."""
    try:
        wanted = uuid.UUID(job_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("write", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        job = await db.get(ExportJob, wanted)
    if job is None or job.tenant_id != principal.tenant.id or job.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    if job.created_by != principal.user.id and not principal.can("settings.manage"):
        raise FrmError("FRM-PERM-1001")
    return ok(service.view(job))


@router.get("/downloads/{token}", dependencies=[rate_limit("download", per_minute=30)])
async def download(token: str) -> Response:
    """Plain file (a browser download can't carry the envelope). The token is the permission: single use,
    EXPORT_DOWNLOAD_MINUTES, only on the workspace that made it. Anything else: 410 in plain text."""
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    if tenant is None:
        return PlainTextResponse(EXPIRED, status_code=410)
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        job = await service.take_download(db, tenant.id, token)
    content = storage.get(job.file_key) if job is not None and job.file_key else None
    if job is None or content is None:
        return PlainTextResponse(EXPIRED, status_code=410)
    return Response(content, media_type=service.CONTENT_TYPES[job.format], headers={
        "content-disposition": f'attachment; filename="{job.file_name}"', "cache-control": "no-store"})

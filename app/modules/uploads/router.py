"""Upload routes (mock: routes/uploads.ts). The storage PUT and the file GET are plain (documented exceptions):
a browser sends raw bytes and loads images by address."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from app.core import zod as z
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.core.security.refs import get_codec
from app.modules.auth.sessions import Principal, require_auth
from app.modules.uploads import service

router = APIRouter(tags=["uploads"])

ticket_schema = z.obj(
    purpose=z.enum(list(service.PURPOSES)),
    file_name=z.string().min(1).max(200),
    content_type=z.string().max(100),
    size=z.number().int().positive(),
)


@router.post("/uploads", dependencies=[rate_limit("upload-ticket", per_minute=30)])
async def create_upload(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = ticket_schema.parse(await request.json())
    if service.PURPOSES[body["purpose"]]["admin"] and not principal.can("settings.manage"):
        raise FrmError("FRM-PERM-1001")  # logos: someone who manages the workspace
    async with db_session("write", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        ticket = await service.create_ticket(
            db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
            user_id=principal.user.id, purpose=body["purpose"], file_name=body["file_name"],
            content_type=body["content_type"], size=int(body["size"]))
    return ok(ticket)


@router.put("/storage/{token}", dependencies=[rate_limit("upload-store", per_minute=30)])
async def store_upload(token: str, request: Request) -> Response:
    """Plain bytes, like an object-storage pre-signed address; the token is the permission (once, 5 minutes)."""
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    if tenant is None or len(token) > 100:
        return JSONResponse({"error": "Upload link expired."}, status_code=403)
    limit = max(p["max_bytes"] for p in service.PURPOSES.values())
    data = b""
    async for chunk in request.stream():
        data += chunk
        if len(data) > limit:
            return JSONResponse({"error": "Unexpected file size."}, status_code=400)
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        status, message = await service.store(db, tenant.id, token, request.headers.get("content-type"), data)
    return Response(status_code=204) if status == 204 else JSONResponse({"error": message}, status_code=status)


@router.post("/uploads/{upload_id}/complete", dependencies=[rate_limit("upload-complete", per_minute=30)])
async def complete_upload(upload_id: str, principal: Principal = Depends(require_auth)) -> Any:
    try:
        wanted = uuid.UUID(upload_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("write", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        return ok(await service.complete(db, principal.tenant.id, wanted))


@router.get("/files/{ref}", dependencies=[rate_limit("file", per_minute=600)])
async def serve_file(ref: str) -> Response:
    """A finished file by its reference (never its id). SVGs open as images only."""
    file_id = get_codec().decode_id(ref)
    found = None
    if file_id is not None:
        async with db_session("read") as db:
            found = await service.public_file(db, uuid.UUID(file_id))
    if found is None:
        return PlainTextResponse("Not found", status_code=404)
    data, content_type = found
    headers = {"x-content-type-options": "nosniff", "cache-control": "private, max-age=3600"}
    if content_type == "image/svg+xml":
        headers["content-security-policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return Response(data, media_type=content_type, headers=headers)

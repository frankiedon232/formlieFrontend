"""Files in responses (mock: routes/responseFiles.ts; the file viewer). Respondents' files are personal data and never
public:

    POST /responses/{id}/files { field, index }   ("Responses only" or more on the form) → a private link to that one
                                                  file, 5 minutes, bound to the workspace
    GET  /response-files/{token}                  (plain, so an <img>, <video> or PDF frame can load it) the file
                                                  inline, or ?download=1 to save it

The link is an encrypted, signed token (Fernet): it names the workspace and the upload, nothing to store.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response

from app.core import storage
from app.core import zod as z
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import current_host_context
from app.core.responses import ok
from app.core.security.fernet_tokens import make_token, read_token
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms.access import viewer_for
from app.modules.forms.answers import file_answers
from app.modules.responses.router import response_for
from app.modules.uploads.models import Upload

router = APIRouter(tags=["responses"])

TTL_S = 5 * 60
PREVIEWABLE = re.compile(r"^(image/(png|jpe?g|gif|webp|avif|svg\+xml|bmp)|application/pdf|video/(mp4|webm|ogg)|"
                         r"audio/(mpeg|mp3|ogg|wav|webm|mp4|aac|x-m4a)|text/(plain|csv))$", re.IGNORECASE)
link_schema = z.obj(field=z.string().max(64), index=z.number().int().min(0).max(50))


@router.post("/responses/{response_id}/files", dependencies=[rate_limit("response-files-link", per_minute=120)])
async def file_link(response_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = link_schema.parse(await request.json())
    async with db_session("read", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        entry = await response_for(db, await viewer_for(db, principal), response_id, "view")
    files = file_answers((entry.response.data or {}).get(data["field"]))
    if data["index"] >= len(files):
        raise FrmError("FRM-GEN-1004")
    file = files[data["index"]]
    kind = file.get("type") or "application/octet-stream"
    token = make_token({"t": "rfile", "w": str(principal.tenant.id), "o": str(principal.tenant.organisation_id),
                        "u": file["id"], "n": file["name"], "k": kind})
    url = f"{get_settings().api_prefix}/response-files/{token}"
    return ok({"url": url, "download_url": f"{url}?download=1", "name": file["name"], "type": file.get("type"),
               "size": file.get("size"), "previewable": bool(PREVIEWABLE.match(file.get("type") or "")), "sample": False,
               "expires_at": (datetime.now(UTC) + timedelta(seconds=TTL_S)).isoformat(timespec="milliseconds")
               .replace("+00:00", "Z")})


def _gone() -> PlainTextResponse:
    return PlainTextResponse("This file link has expired. Open the file again from the response.", status_code=410)


@router.get("/response-files/{token}", include_in_schema=False, dependencies=[rate_limit("response-files", per_minute=240)])
async def serve_response_file(token: str, request: Request) -> Response:
    link = read_token(token, TTL_S)
    if not link or link.get("t") != "rfile":
        return _gone()
    try:
        tenant_id, organisation_id, upload_id = uuid.UUID(link["w"]), uuid.UUID(link["o"]), uuid.UUID(link["u"])
    except (KeyError, ValueError):
        return _gone()
    # Only on the workspace's own host (a link copied elsewhere doesn't open)
    ctx = get_context()
    host = current_host_context()
    # A localhost / bare-address host skips the same-workspace check in development and tests only (B17 L11)
    local = host is not None and host.kind == "manage" and host.reason == "local" and get_settings().is_development
    if not local and (ctx is None or ctx.tenant is None or ctx.tenant.id != tenant_id):
        return _gone()
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        upload = await db.get(Upload, upload_id)
    if upload is None or upload.tenant_id != tenant_id or upload.purpose != "response_file" or upload.deleted_at \
            or upload.completed_at is None or not upload.file_key:
        return PlainTextResponse("Not found", status_code=404)
    data = storage.get(upload.file_key)
    if data is None:
        return PlainTextResponse("Not found", status_code=404)
    kind, name = str(link.get("k") or upload.content_type), str(link.get("n") or upload.file_name)
    # Inline only for types the viewer previews; anything else (text/html a respondent declared, ...) downloads, and
    # nothing a file carries ever runs (B17 L10)
    download = request.query_params.get("download") == "1" or not PREVIEWABLE.match(kind)
    headers = {"x-content-type-options": "nosniff", "cache-control": "private, no-store",
               "content-disposition": f"{'attachment' if download else 'inline'}; filename=\"{quote(name)}\"",
               "content-security-policy": "default-src 'none'; img-src 'self'; media-src 'self'; "
                                          "style-src 'unsafe-inline'; sandbox"}
    return Response(content=data, media_type=kind, headers=headers)

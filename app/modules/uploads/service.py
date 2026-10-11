"""Uploads (mock: routes/uploads.ts; SECURITY-PROTOCOL: files go to storage with a pre-signed, expiring link, and
only the request that gets the link is enveloped).

    POST /uploads → ticket · PUT /storage/{token} (plain bytes) · POST /uploads/{id}/complete → the file
    GET /files/{ref} serves a finished file (a CDN address in production)

The bytes must really be the declared image type (SVG only as a plain drawing). Virus scanning (ClamAV) is not
installed yet: the content checks stand in for it, and `scan_status` is where the scanner will report.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.core.errors import FrmError
from app.modules.uploads.models import Upload

MB = 1024 * 1024
# What each purpose may upload: logos (admins, 2 MB), link preview and form images (members, 5 MB)
PURPOSES: dict[str, dict[str, Any]] = {
    "logo": {"types": ("image/png", "image/jpeg", "image/webp"), "max_bytes": 2 * MB, "admin": True},
    "share_image": {"types": ("image/png", "image/jpeg", "image/webp"), "max_bytes": 5 * MB, "admin": False},
    "form_image": {"types": ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"),
                   "max_bytes": 5 * MB, "admin": False},
}
TICKET_MINUTES = 5
_SVG_OPEN = re.compile(rb"<svg[\s>]", re.IGNORECASE)
_SVG_ACTIVE = re.compile(rb"<script|\son\w+\s*=|javascript:|<foreignObject|<iframe|<embed|<object", re.IGNORECASE)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def looks_like(content_type: str, data: bytes) -> bool:
    """looksLike(): the bytes are the declared image type; an SVG is a plain drawing (no scripts, handlers, embeds)."""
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if content_type == "image/gif":
        return data.startswith(b"GIF8")
    if content_type == "image/svg+xml":
        head = data[:2_000_000]
        return bool(_SVG_OPEN.search(head)) and not _SVG_ACTIVE.search(head)
    return False


def file_url(upload_id: uuid.UUID) -> str:
    return f"{get_settings().api_prefix}/files/{upload_id}"


async def create_ticket(db: AsyncSession, *, tenant_id: uuid.UUID, organisation_id: uuid.UUID, user_id: uuid.UUID,
                        purpose: str, file_name: str, content_type: str, size: int) -> dict[str, Any]:
    rules = PURPOSES[purpose]
    if content_type not in rules["types"]:
        raise FrmError("FRM-GEN-1002", [{"field": "content_type", "message": "This file type is not allowed."}])
    if size > rules["max_bytes"]:
        raise FrmError("FRM-GEN-1002", [{"field": "size", "message": f"The file is larger than {rules['max_bytes'] // MB} MB."}])
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=TICKET_MINUTES)
    upload = Upload(tenant_id=tenant_id, organisation_id=organisation_id, purpose=purpose, file_name=file_name,
                    content_type=content_type, size=size, max_bytes=rules["max_bytes"], token_hash=_hash(token),
                    expires_at=expires, created_by=user_id)
    db.add(upload)
    await db.flush()
    return {
        "upload_id": str(upload.id),
        "upload_url": f"{get_settings().api_prefix}/storage/{token}",
        "method": "PUT",
        "headers": {"content-type": content_type},
        "max_bytes": rules["max_bytes"],
        "expires_at": expires.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


async def store(db: AsyncSession, tenant_id: uuid.UUID, token: str, content_type: str | None,
                data: bytes) -> tuple[int, str | None]:
    """PUT /storage/{token}: (204, None) or (status, the mock's message). The link works once."""
    upload = (await db.execute(select(Upload).where(
        Upload.token_hash == _hash(token), Upload.tenant_id == tenant_id, Upload.deleted_at.is_(None)))).scalar_one_or_none()
    if upload is None or upload.expires_at < datetime.now(UTC) or upload.stored_at is not None:
        return 403, "Upload link expired."
    if content_type != upload.content_type:
        return 400, "Unexpected file type."
    if not data or len(data) > upload.max_bytes or len(data) != upload.size:
        return 400, "Unexpected file size."
    if not looks_like(upload.content_type, data):
        upload.scan_status = "refused"
        return 400, "The file is not a valid image."
    key = storage.key_for(upload.tenant_id, upload.organisation_id, "uploads", upload.id)
    storage.put(key, data)
    upload.file_key, upload.stored_at, upload.token_hash, upload.scan_status = key, datetime.now(UTC), None, "clean"
    return 204, None


async def complete(db: AsyncSession, tenant_id: uuid.UUID, upload_id: uuid.UUID) -> dict[str, Any]:
    upload = await db.get(Upload, upload_id)
    if upload is None or upload.tenant_id != tenant_id or upload.stored_at is None or upload.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    if upload.completed_at is None:
        upload.completed_at = datetime.now(UTC)
    return {"id": str(upload.id), "url": file_url(upload.id), "content_type": upload.content_type, "size": upload.size}


async def completed_url(db: AsyncSession, tenant_id: uuid.UUID, upload_id: str) -> str | None:
    """completedUploadUrl(): the address of a finished upload of this workspace, else None."""
    try:
        wanted = uuid.UUID(upload_id)
    except ValueError:
        return None
    upload = await db.get(Upload, wanted)
    ok = upload is not None and upload.tenant_id == tenant_id and upload.completed_at is not None \
        and upload.deleted_at is None and upload.scan_status == "clean"
    return file_url(wanted) if ok else None


async def public_file(db: AsyncSession, file_id: uuid.UUID) -> tuple[bytes, str] | None:
    """A finished file by its id, for any page that shows it (platform.public_file: no workspace context needed)."""
    row = (await db.execute(text("SELECT file_key, content_type FROM platform.public_file(:id)"),
                            {"id": file_id})).first()
    if row is None:
        return None
    data = storage.get(row.file_key)
    return (data, row.content_type) if data is not None else None


"""Export jobs for every module (mock: routes/audit.ts → jobs, getExportJob, download).

A module registers how its file is made (`register(kind, builder)`); the request creates the job and hands it to the
`exports` Celery queue; the worker makes the file, stores it under the workspace's path and opens a one-time link
(`/api/v1/downloads/{token}`, EXPORT_DOWNLOAD_MINUTES). The link is the permission, so it is single use and only
answers on the workspace that made it.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.modules.exports.models import ExportJob

log = logging.getLogger("formalie.exports")

CONTENT_TYPES = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 "csv": "text/csv; charset=utf-8", "pdf": "application/pdf"}

# kind → async builder(db, job) → (file bytes, rows)
Builder = Callable[[AsyncSession, ExportJob], Awaitable[tuple[bytes, int]]]
_BUILDERS: dict[str, Builder] = {}
# Kinds whose file is kept for some days and downloaded through links of their own (response exports: 7 days)
_KEEP_DAYS: dict[str, int] = {}
# What to do once a kind's file is ready (tell the person who asked)
_ON_READY: dict[str, Callable[[AsyncSession, ExportJob], Awaitable[None]]] = {}


def register(kind: str, builder: Builder, keep_days: int | None = None,
             on_ready: Callable[[AsyncSession, ExportJob], Awaitable[None]] | None = None) -> None:
    _BUILDERS[kind] = builder
    if keep_days:
        _KEEP_DAYS[kind] = keep_days
    if on_ready:
        _ON_READY[kind] = on_ready


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def view(job: ExportJob) -> dict[str, Any]:
    """ExportJob (shared/types/audit.ts): the link only once the file is ready."""
    done = job.status == "done"
    token = decrypt_secret(job.token_enc) if done and job.token_enc else None
    return {
        "id": str(job.id), "status": job.status, "progress": job.progress, "rows": job.rows, "format": job.format,
        "file_name": job.file_name,
        "download_url": f"{get_settings().api_prefix}/downloads/{token}" if token else None,
        "expires_at": _iso(job.expires_at) if done else None,
    }


async def create(db: AsyncSession, *, tenant_id: uuid.UUID, organisation_id: uuid.UUID, user_id: uuid.UUID,
                 kind: str, format: str, file_name: str, rows: int, params: dict[str, Any]) -> ExportJob:
    job = ExportJob(tenant_id=tenant_id, organisation_id=organisation_id, kind=kind, format=format,
                    file_name=file_name, status="queued", progress=0, rows=rows, params=params, created_by=user_id)
    db.add(job)
    await db.flush()
    return job


def dispatch(job: ExportJob) -> None:
    """To the `exports` queue (after the request's transaction has committed). Tests replace this."""
    from app.modules.exports.tasks import build_export

    build_export.apply_async(args=[str(job.id), str(job.tenant_id), str(job.organisation_id)], queue="exports")


async def build(job_id: uuid.UUID, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> None:
    """Makes the file (the worker): running → done with a link, or failed with a code."""
    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    async with db_session("write", **scope) as db:
        job = await db.get(ExportJob, job_id)
        if job is None or job.tenant_id != tenant_id or job.status not in ("queued", "running"):
            return  # unknown, or already handled (a redelivered task)
        job.status, job.progress = "running", 10
    try:
        async with db_session("write", **scope) as db:  # just written: the primary
            job = await db.get(ExportJob, job_id)
            assert job is not None
            content, rows = await _BUILDERS[job.kind](db, job)
        key = storage.key_for(tenant_id, organisation_id, "exports", job_id)
        size = storage.put(key, content)
    except Exception:
        log.exception("export failed", extra={"export_id": str(job_id), "tenant_id": str(tenant_id)})
        async with db_session("write", **scope) as db:
            await db.execute(update(ExportJob).where(ExportJob.id == job_id, ExportJob.tenant_id == tenant_id)
                             .values(status="failed", error_code="FRM-GEN-5000"))
        return
    now = datetime.now(UTC)
    if job.kind in _KEEP_DAYS:  # kept, no single link: each download asks for its own
        async with db_session("write", **scope) as db:
            await db.execute(update(ExportJob).where(ExportJob.id == job_id, ExportJob.tenant_id == tenant_id).values(
                status="done", progress=100, rows=rows, file_key=key, file_size=size, ready_at=now,
                expires_at=job.created_at + timedelta(days=_KEEP_DAYS[job.kind])))
            if job.kind in _ON_READY:
                try:
                    await _ON_READY[job.kind](db, job)
                except Exception:  # noqa: BLE001 (telling people never fails the export)
                    log.exception("export ready hook failed", extra={"export_id": str(job_id)})
        log.info("export ready", extra={"export_id": str(job_id), "rows": rows, "bytes": size})
        return
    token = secrets.token_urlsafe(32)
    async with db_session("write", **scope) as db:
        await db.execute(update(ExportJob).where(ExportJob.id == job_id, ExportJob.tenant_id == tenant_id).values(
            status="done", progress=100, rows=rows, file_key=key, file_size=size, token_hash=_hash(token),
            token_enc=encrypt_secret(token), ready_at=now,
            expires_at=now + timedelta(minutes=get_settings().export_download_minutes)))
    log.info("export ready", extra={"export_id": str(job_id), "rows": rows, "bytes": size})


async def take_download(db: AsyncSession, tenant_id: uuid.UUID, token: str) -> ExportJob | None:
    """The job behind a link, used up at once (one UPDATE: two clicks can't both get it); None when the link is
    unknown, used, expired or of another workspace."""
    if not token or len(token) > 100:
        return None
    job_id = (await db.execute(
        update(ExportJob)
        .where(ExportJob.token_hash == _hash(token), ExportJob.tenant_id == tenant_id, ExportJob.status == "done",
               ExportJob.downloaded_at.is_(None), ExportJob.expires_at > datetime.now(UTC),
               ExportJob.deleted_at.is_(None))
        .values(downloaded_at=datetime.now(UTC), token_hash=None, token_enc=None)
        .returning(ExportJob.id))).scalar_one_or_none()
    if job_id is None:
        return None
    return (await db.execute(select(ExportJob).where(ExportJob.id == job_id))).scalar_one()

"""Explorer and Query editor exports (mock: routes/explorer.ts → exports; API-CONTRACT → Database explorer): a table's
rows (this page, or every matching row up to 5,000) or a reading statement's results, as CSV, Excel, JSON or SQL
INSERT statements. Made by the `exports` worker from the connection (never a whole large table); downloaded through
a one-time private link that lasts 5 minutes and only answers on the workspace that made it.

    POST /datasources/{id}/explorer/exports   → 201 TableExport
    GET  /explorer-exports/{id}               its progress
    POST /explorer-exports/{id}/link          { url, expires_at }
    GET  /datasource-exports/{token}          the file (plain download)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import js, storage
from app.core import zod as z
from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import after_commit, db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import current_host_context
from app.core.responses import ok
from app.core.security.fernet_tokens import make_token, read_token
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_admin
from app.modules.data_sources import ddl as D
from app.modules.data_sources import runner
from app.modules.data_sources.connect import connect
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.service import iso, target_of
from app.modules.explorer import service as X
from app.modules.exports import service as jobs
from app.modules.exports.models import ExportJob

router = APIRouter(tags=["database explorer"])

KIND = "datasource"
LINK_S = 5 * 60
EXPORT_LIMIT_S = 60
EXPIRED = "This download link has expired. Export the table again from the database explorer."
jobs.CONTENT_TYPES.update({"json": "application/json; charset=utf-8", "sql": "application/sql; charset=utf-8"})

export_schema = z.obj(
    schema=z.string(), table=z.string(), format=z.enum(["csv", "xlsx", "json", "sql"]),
    scope=z.enum(["page", "all"]).optional(), page=z.number().int().min(1).optional(),
    page_size=z.number().int().min(1).max(100).optional(), q=z.string().optional(), sort=z.string().optional(),
    filter=z.record(z.string(), z.string()).optional(),
)


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id, "user_id": principal.user.id}


def view(job: ExportJob) -> dict[str, Any]:
    """TableExport (shared/types/explorer.ts)."""
    p = job.params or {}
    ready = job.status == "done"
    return {"id": str(job.id), "table": p.get("label", ""), "format": job.format, "scope": p.get("scope", "page"),
            "total": p.get("total", 0), "capped": bool(p.get("capped")), "status": "ready" if ready else "running",
            "progress": 100 if ready else job.progress, "rows": job.rows, "size": job.file_size if ready else None}


async def start(principal: Principal, source: DataSource, params: dict[str, Any], file_name: str, rows: int) -> dict[str, Any]:
    """The job, queued for the worker once the request has committed."""
    async with db_session("write", **_scope(principal)) as db:
        job = await jobs.create(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                user_id=principal.user.id, kind=KIND, format=params["format"], file_name=file_name[:200],
                                rows=rows, params={**params, "datasource_id": str(source.id)})
        after_commit(db, lambda: jobs.dispatch(job))
        return view(job)


def _text(value: Any) -> str:
    return "" if value is None else js.stringify(value) if isinstance(value, (dict, list)) else js.to_string(value)


def _csv(head: list[str], lines: list[list[str]]) -> bytes:
    from app.modules.responses.exports import csv_cell

    return ("﻿" + "\r\n".join(",".join(csv_cell(cell) for cell in line) for line in [head, *lines])).encode("utf-8")


def _xlsx(name: str, rows: list[list[str]]) -> bytes:
    from app.modules.responses.exports import _xlsx as xlsx_file

    return xlsx_file(name, rows)


async def build(db: AsyncSession, job: ExportJob) -> tuple[bytes, int]:
    """The file (the worker): reads the connection again, one page or up to 5,000 rows."""
    from app.modules.audit.service import Actor, record
    from app.modules.users.models import User

    p = dict(job.params or {})
    source = await db.get(DataSource, uuid.UUID(p["datasource_id"]))
    if source is None or source.deleted_at is not None or not source.enabled:
        raise RuntimeError("connection gone")
    page, size, scope, fmt = int(p.get("page") or 1), int(p.get("page_size") or 20), p.get("scope", "page"), job.format
    async with connect(target_of(source)) as c:
        await c.limit(EXPORT_LIMIT_S)
        if p["mode"] == "table":
            table = X.find_table(await X.tables_of(c, source), p["schema"], p["table"])
            struct = await X.structure(c, source, table, None, None)
            query = {"q": p.get("q"), "sort": p.get("sort"), "filter": p.get("filter") or {}}
            found = await X.select_rows(c, source.engine, struct, query, size, (page - 1) * size) if scope == "page" \
                else await X.select_rows(c, source.engine, struct, query, D.EXPORT_MAX_ROWS, 0)
            columns = [{"name": col["name"], "type": col["type"], "primary": col["primary"], "has_default": col["has_default"]}
                       for col in struct["columns"]]
            head = [col["name"] for col in columns]
            if fmt == "json":
                content = D.json_export(columns, found).encode("utf-8")
            elif fmt == "sql":
                content = D.sql_insert_script(source.engine, {"schema": struct["schema"], "table": struct["name"]},
                                              columns, found).encode("utf-8")
            else:
                lines = [[_text(row.get(n)) for n in head] for row in found]
                content = _xlsx(struct["name"][:31], [head, *lines]) if fmt == "xlsx" else _csv(head, lines)
            rows = len(found)
            action, metadata = "data.table_exported", {
                "table": p["label"], "format": fmt, "scope": scope, "rows": str(rows),
                "filtered": "yes" if p.get("q") or p.get("filter") else "no"}
        else:
            cap = page * size if scope == "page" else D.EXPORT_MAX_ROWS + 1
            got = await runner.read(c, source.engine, p["sql"], p.get("params") or {}, cap)
            matched = got["rows"]
            picked = matched[(page - 1) * size:page * size] if scope == "page" else matched[:D.EXPORT_MAX_ROWS]
            head = [col["name"] for col in got["columns"]]
            if fmt == "json":
                columns = [{"name": col["name"], "type": col["type"] or "TEXT"} for col in got["columns"]]
                content = D.json_export(columns, [dict(zip(head, row, strict=False)) for row in picked]).encode("utf-8")
            else:
                lines = [[_text(v) for v in row] for row in picked]
                content = _xlsx("Results", [head, *lines]) if fmt == "xlsx" else _csv(head, lines)
            rows = len(picked)
            p.update(total=len(picked) if scope == "page" else len(matched), capped=scope == "all" and len(matched) > D.EXPORT_MAX_ROWS)
            job.params = p
            action, metadata = "data.query_exported", {"statement": p["sql"][:300], "format": fmt, "scope": scope, "rows": str(rows)}
    user = await db.get(User, job.created_by) if job.created_by else None
    await record(db, tenant_id=job.tenant_id, organisation_id=job.organisation_id, action=action,
                 actor=Actor.user(user) if user else Actor.system(),
                 resource={"type": "data_source", "id": str(source.id), "name": source.name}, metadata=metadata)
    return content, rows


jobs.register(KIND, build, keep_days=1)


# ── Routes ──────────────────────────────────────────────────────────────────────

@router.post("/datasources/{datasource_id}/explorer/exports", status_code=201, dependencies=[rate_limit("explorer-export", per_minute=20)])
async def start_table_export(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    from app.modules.explorer.router import _structure, opened, usable

    data = export_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    scope, page, size = data.get("scope") or "page", data.get("page") or 1, data.get("page_size") or 20
    query = {"q": data.get("q"), "sort": data.get("sort"), "filter": data.get("filter") or {}}
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, data["schema"], data["table"])
        matching = await X.count_rows(c, source.engine, struct, query)
    rows = max(0, min(size, matching - (page - 1) * size)) if scope == "page" else min(matching, D.EXPORT_MAX_ROWS)
    label = f"{struct['schema']}.{struct['name']}"
    return ok(await start(principal, source, {
        "mode": "table", "schema": struct["schema"], "table": struct["name"], "format": data["format"], "scope": scope,
        "page": page, "page_size": size, "q": data.get("q"), "sort": data.get("sort"), "filter": data.get("filter") or {},
        "label": label, "total": rows if scope == "page" else min(matching, X.COUNT_CAP),
        "capped": scope == "all" and matching > D.EXPORT_MAX_ROWS}, f"{struct['name']}.{data['format']}", rows))


async def _job(db: Any, principal: Principal, export_id: str) -> ExportJob:
    try:
        job = await db.get(ExportJob, uuid.UUID(export_id))
    except ValueError:
        job = None
    if job is None or job.tenant_id != principal.tenant.id or job.kind != KIND or job.deleted_at is not None:
        raise FrmError("FRM-EXP-1001")
    if job.status == "failed":
        raise FrmError(job.error_code or "FRM-GEN-5000")
    return job


@router.get("/explorer-exports/{export_id}", dependencies=[rate_limit("explorer-export-get", per_minute=240)])
async def get_table_export(export_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(view(await _job(db, principal, export_id)))


@router.post("/explorer-exports/{export_id}/link", dependencies=[rate_limit("explorer-export-link", per_minute=60)])
async def table_export_link(export_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        job = await _job(db, principal, export_id)
    if job.status != "done":
        raise FrmError("FRM-GEN-1002", [{"field": "status", "message": "The file is still being made."}])
    token = make_token({"t": "dexport", "j": str(job.id), "w": str(job.tenant_id), "o": str(job.organisation_id),
                        "n": uuid.uuid4().hex})
    return ok({"url": f"{get_settings().api_prefix}/datasource-exports/{token}",
               "expires_at": iso(datetime.now(UTC) + timedelta(seconds=LINK_S))})


@router.get("/datasource-exports/{token}", include_in_schema=False, dependencies=[rate_limit("datasource-exports-file", per_minute=60)])
async def download_table_export(token: str) -> Response:
    """The file; each link works once, for 5 minutes, only on the workspace that made it."""
    link = read_token(token, LINK_S)
    if not link or link.get("t") != "dexport":
        return PlainTextResponse(EXPIRED, status_code=410)
    try:
        job_id, tenant_id, organisation_id = uuid.UUID(link["j"]), uuid.UUID(link["w"]), uuid.UUID(link["o"])
    except (KeyError, ValueError):
        return PlainTextResponse(EXPIRED, status_code=410)
    ctx, host = get_context(), current_host_context()
    local = host is not None and host.kind == "manage" and host.reason == "local"
    if not local and (ctx is None or ctx.tenant is None or ctx.tenant.id != tenant_id):
        return PlainTextResponse(EXPIRED, status_code=410)
    try:  # one use
        first = bool(await get_redis().set(f"dexport:used:{link['n']}", "1", nx=True, ex=LINK_S))
    except Exception:  # noqa: BLE001 (Redis down: the 5-minute signed link still stands)
        first = True
    if not first:
        return PlainTextResponse(EXPIRED, status_code=410)
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        job = await db.get(ExportJob, job_id)
    content = storage.get(job.file_key) if job is not None and job.file_key else None
    if job is None or job.tenant_id != tenant_id or job.kind != KIND or content is None:
        return PlainTextResponse(EXPIRED, status_code=410)
    return Response(content, media_type=jobs.CONTENT_TYPES[job.format], headers={
        "content-disposition": f'attachment; filename="{job.file_name}"', "cache-control": "no-store"})

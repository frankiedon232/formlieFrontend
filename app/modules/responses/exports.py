"""Response exports (mock: routes/responseExports.ts; API-CONTRACT → Responses → Exports). A form's responses as a
file: all of them, the ones matching the list's filters, or the selected ones; the table's columns or every question;
with or without review details. Made by the `exports` worker, kept 7 days; each download asks for a one-time private
link (5 minutes). Every export, download and removal is in the audit trail.

    POST   /forms/{id}/responses/export     start one (202)
    GET    /responses/exports               the Exports page: format, status, form, period, search, sort, pages
    GET    /responses/exports/{id}          progress of one
    POST   /responses/exports/{id}/link     a one-time download link (5 minutes)
    DELETE /responses/exports/{id}          remove the file
    GET    /response-exports/{token}        the file (plain: a browser download can't carry the envelope)
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import xlsxwriter
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import js, storage
from app.core import zod as z
from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import current_host_context
from app.core.responses import PageParams, ok
from app.core.security.fernet_tokens import make_token, read_token
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.exports import service as jobs
from app.modules.exports.models import ExportJob
from app.modules.forms import access
from app.modules.forms.access import viewer_for
from app.modules.forms.models import Form
from app.modules.forms.service import forms_of, iso
from app.modules.responses import service
from app.modules.responses.answers import answer_text
from app.modules.responses.report import appearance_ink, response_report
from app.modules.settings.service import get_section

router = APIRouter(tags=["responses"])

KEEP_DAYS = 7
LINK_S = 5 * 60
SCOPES = {"all": "All responses", "filtered": "Matching the filters", "selected": "Selected responses"}
export_schema = z.obj(
    format=z.enum(["xlsx", "csv", "pdf"]), scope=z.enum(["all", "filtered", "selected"]),
    query=z.record(z.string(), z.union([z.string(), z.number()])).optional(),
    ids=z.array(z.string().max(64)).max(5000).optional(),
    columns=z.array(z.string().max(64)).max(500).optional(),
    details=z.boolean().optional(),
)


def csv_cell(value: Any) -> str:
    """A CSV cell; a leading = + - @ would run as a formula in spreadsheet apps (CSV injection)."""
    text = "" if js.nullish(value) else js.to_string(value)
    safe = f"'{text}" if re.match(r"[=+\-@\t\r]", text) else text
    return f'"{safe.replace(chr(34), chr(34) * 2)}"' if re.search(r'[",\n\r]', safe) else safe


def _slug(text: str) -> str:
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))[:40] or "form"


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


# ── The file (the worker) ───────────────────────────────────────────────────────

async def _picked(db: AsyncSession, form: Form, params: dict[str, Any]) -> list[service.Entry]:
    from app.modules.responses.router import _entries, filter_entries

    entries = await _entries(db, form.tenant_id, [form])
    if params["scope"] == "selected":
        wanted = set(params.get("ids") or [])
        return [e for e in entries if str(e.response.id) in wanted]
    query = {k: str(v) for k, v in (params.get("query") or {}).items()} if params["scope"] == "filtered" else {}
    return filter_entries(entries, query, True)


def _xlsx(name: str, rows: list[list[Any]]) -> bytes:
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    sheet = book.add_worksheet((re.sub(r"[\[\]:*?/\\]", " ", name).strip() or "Responses")[:31])
    bold = book.add_format({"bold": True})
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if isinstance(cell, (int, float)) and not isinstance(cell, bool) and r > 0:
                sheet.write_number(r, c, cell)
            else:
                sheet.write_string(r, c, js.to_string(cell), bold if r == 0 else None)  # never a formula
    sheet.freeze_panes(1, 0)
    book.close()
    return buffer.getvalue()


async def build_response_file(db: AsyncSession, job: ExportJob) -> tuple[bytes, int]:
    params = job.params
    form = await db.get(Form, uuid.UUID(params["form_id"]))
    if form is None or form.tenant_id != job.tenant_id:
        raise RuntimeError("form gone")
    picked = await _picked(db, form, params)
    questions = service.questions_of(await service.response_schema(db, form))
    by_key = {f["key"]: f for f in questions}
    fields = [by_key[k] for k in params.get("columns") or [] if k in by_key] if params.get("columns") else questions
    details = params.get("details", True)
    if job.format == "pdf":
        counts = {"new": 0, "reviewed": 0, "approved": 0, "rejected": 0}
        for e in picked:
            counts[e.response.status] += 1
        appearance = await get_section(db, job.tenant_id, "appearance")
        branding = await get_section(db, job.tenant_id, "branding")
        rows = []
        for e in picked:
            data = e.response.data or {}
            at = e.response.submitted_at.astimezone(UTC)
            rows.append({
                "number": e.response.number, "name": e.title or "",
                "email": (e.respondent.get("email") or "") if e.respondent.get("name") else "",
                "submitted": f"{at:%Y-%m-%d} {at:%H:%M} UTC", "status": e.response.status, "channel": e.response.channel,
                "tags": list(e.response.tags or []) if details else [],
                "answers": [{"question": (f.get("label") or "").strip() or f["key"], "answer": answer_text(f, data.get(f["key"]))}
                            for f in fields]})
        content = response_report(params["org"], form.name, appearance_ink(appearance, branding.get("brand_color")),
                                  params["by"], job.created_at.astimezone(UTC), SCOPES[params["scope"]], counts, rows)
        return content, len(picked)
    head = ["Number", "Submitted (UTC)",
            *(["Status", "Tags", "Came in", "Language", "Time taken (s)", "Notes"] if details else []),
            *[(f.get("label") or "").strip() or f["key"] for f in fields]]
    table: list[list[Any]] = [head]
    for e in picked:
        r, data = e.response, e.response.data or {}
        table.append([r.number, iso(r.submitted_at),
                      *([r.status, "; ".join(r.tags or []), r.channel, r.language,
                         r.duration_seconds if r.duration_seconds is not None else "", e.notes] if details else []),
                      *[answer_text(f, data.get(f["key"])) for f in fields]])
    if job.format == "xlsx":
        return _xlsx(form.name, table), len(picked)
    text = "﻿" + "\r\n".join(",".join(csv_cell(c) for c in row) for row in table) + "\r\n"
    return text.encode("utf-8"), len(picked)


async def tell_ready(db: AsyncSession, job: ExportJob) -> None:
    """"Your export is ready", only to whoever asked for it."""
    from app.modules.notifications.service import notify

    if job.created_by is None:
        return
    await notify(db, job.tenant_id, job.organisation_id, {"name": job.params["org"], "subdomain": job.params["subdomain"]},
                 "export_ready", {"file": job.file_name, "form": job.params["form_name"]}, "/responses/exports",
                 only=[job.created_by])


jobs.register("responses", build_response_file, keep_days=KEEP_DAYS, on_ready=tell_ready)


# ── Views ───────────────────────────────────────────────────────────────────────

def view(job: ExportJob) -> dict[str, Any]:
    """ResponseExport (shared/types/responses.ts)."""
    p = job.params
    expired = job.expires_at is not None and job.expires_at < datetime.now(UTC)
    status = "expired" if expired else {"done": "ready"}.get(job.status, job.status)
    return {
        "id": str(job.id), "form": {"id": p["form_id"], "name": p["form_name"]}, "format": job.format,
        "scope": p["scope"], "status": status, "progress": job.progress, "rows": job.rows, "columns": p["columns_count"],
        "file_name": job.file_name, "size": job.file_size, "created_by": {"id": str(job.created_by), "name": p["by"]},
        "created_at": iso(job.created_at),
        "expires_at": iso(job.expires_at or job.created_at + timedelta(days=KEEP_DAYS)),
    }


async def _audit(db: Any, principal: Principal, action: str, job: ExportJob) -> None:
    p = job.params
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource={"type": "export", "id": str(job.id), "name": job.file_name},
                 metadata={"form": p["form_name"], "format": job.format, "scope": p["scope"], "rows": str(job.rows)})


async def _visible(db: Any, principal: Principal) -> list[ExportJob]:
    """Exports of forms whose responses this person may export."""
    viewer = await viewer_for(db, principal)
    allowed = {str(f.id) for f in await forms_of(db, principal.tenant.id)
               if f.deleted_at is None and access.responses_allowed(f, viewer, "export")}
    rows = (await db.execute(select(ExportJob).where(
        ExportJob.tenant_id == principal.tenant.id, ExportJob.kind == "responses", ExportJob.deleted_at.is_(None))
        .order_by(ExportJob.created_at.desc()))).scalars()
    return [j for j in rows if j.params.get("form_id") in allowed]


async def _one(db: Any, principal: Principal, export_id: str) -> ExportJob:
    job = next((j for j in await _visible(db, principal) if str(j.id) == export_id), None)
    if job is None:
        raise FrmError("FRM-GEN-1004")
    return job


# ── Routes ──────────────────────────────────────────────────────────────────────

@router.post("/forms/{form_id}/responses/export", status_code=202, dependencies=[rate_limit("responses-export", per_minute=20)])
async def export_form_responses(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.responses.router import _form_for

    data = export_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        form = await _form_for(db, await viewer_for(db, principal), form_id, "export")
        params = {"form_id": str(form.id), "form_name": form.name, "scope": data["scope"],
                  "query": data.get("query") or {}, "ids": data.get("ids") or [], "columns": data.get("columns") or [],
                  "details": data.get("details", True), "org": principal.tenant.name,
                  "subdomain": principal.tenant.subdomain,
                  "by": f"{principal.user.first_name} {principal.user.last_name}".strip()}
        picked = await _picked(db, form, params)
        if not picked:
            raise FrmError("FRM-GEN-1002", [{"field": "scope", "message": "Nothing to export."}])
        questions = service.questions_of(await service.response_schema(db, form))
        keys = {f["key"] for f in questions}
        params["columns_count"] = len([k for k in params["columns"] if k in keys]) if params["columns"] else len(questions)
        name = f"{_slug(form.name)}-responses-{date.today().isoformat()}.{data['format']}"
        job = await jobs.create(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                user_id=principal.user.id, kind="responses", format=data["format"], file_name=name,
                                rows=len(picked), params=params)
        await _audit(db, principal, "responses.exported", job)
        result = view(job)
    jobs.dispatch(job)
    return ok(result)


@router.get("/responses/exports", dependencies=[rate_limit("responses-exports", per_minute=120)])
async def list_response_exports(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)

    def pick(key: str) -> list[str] | None:
        value = query.get(f"filter[{key}]")
        return value.split(",") if value else None
    formats, statuses, form_ids = pick("format"), pick("status"), pick("form")

    def day(value: str | None, end: bool) -> datetime | None:
        if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return None
        moment = datetime.combine(date.fromisoformat(value), datetime.min.time(), UTC)
        return moment + timedelta(days=1) - timedelta(milliseconds=1) if end else moment
    start, end = day(query.get("from"), False), day(query.get("to"), True)
    async with db_session("read", **_scope(principal)) as db:
        items = [view(j) for j in await _visible(db, principal)]
    items = [i for i in items if (not formats or i["format"] in formats)
             and (not statuses or ("running" if i["status"] in ("running", "queued") else i["status"]) in statuses)
             and (not form_ids or i["form"]["id"] in form_ids)
             and (start is None or i["created_at"] >= iso(start)) and (end is None or i["created_at"] <= iso(end))]
    q = (query.get("q") or "").strip().lower()
    if q:
        items = [i for i in items if q in i["file_name"].lower() or q in i["form"]["name"].lower()]
    sort = query.get("sort") or "-created_at"
    key = sort.lstrip("-")
    items.sort(key=lambda i: str(i.get(key) if not isinstance(i.get(key), dict) else i[key].get("name")),
               reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(items[params.offset:params.offset + params.page_size], params.meta(len(items)))


@router.get("/responses/exports/{export_id}", dependencies=[rate_limit("responses-exports", per_minute=240)])
async def get_response_export(export_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(view(await _one(db, principal, export_id)))


@router.post("/responses/exports/{export_id}/link", dependencies=[rate_limit("responses-exports-link", per_minute=60)])
async def response_export_link(export_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """A one-time private download link (5 minutes)."""
    async with db_session("write", **_scope(principal)) as db:
        job = await _one(db, principal, export_id)
        state = view(job)["status"]
        if state == "expired":
            raise FrmError("FRM-GEN-1004")
        if state != "ready":
            raise FrmError("FRM-GEN-1002", [{"field": "status", "message": "The file is still being made."}])
        token = make_token({"t": "rexport", "j": str(job.id), "w": str(job.tenant_id), "o": str(job.organisation_id),
                            "n": uuid.uuid4().hex})
        await _audit(db, principal, "responses.export_downloaded", job)
    return ok({"url": f"{get_settings().api_prefix}/response-exports/{token}",
               "expires_at": iso(datetime.now(UTC) + timedelta(seconds=LINK_S))})


@router.delete("/responses/exports/{export_id}", dependencies=[rate_limit("responses-exports", per_minute=60)])
async def delete_response_export(export_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """The file is removed (the job's row stays, deleted_at)."""
    async with db_session("write", **_scope(principal)) as db:
        job = await _one(db, principal, export_id)
        job.deleted_at, job.deleted_by = datetime.now(UTC), principal.user.id
        await _audit(db, principal, "responses.export_deleted", job)
        if job.file_key:
            storage.remove(job.file_key)
    return ok({"id": str(job.id)})


EXPIRED = "This download link has expired. Download the export again from Responses → Exports."


@router.get("/response-exports/{token}", include_in_schema=False, dependencies=[rate_limit("response-exports-file", per_minute=60)])
async def download_response_export(token: str) -> Response:
    """The file; each link works once, for 5 minutes, only on the workspace that made it."""
    link = read_token(token, LINK_S)
    if not link or link.get("t") != "rexport":
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
        first = bool(await get_redis().set(f"rexport:used:{link['n']}", "1", nx=True, ex=LINK_S))
    except Exception:  # noqa: BLE001 (Redis down: the 5-minute signed link still stands)
        first = True
    if not first:
        return PlainTextResponse(EXPIRED, status_code=410)
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        job = await db.get(ExportJob, job_id)
    content = storage.get(job.file_key) if job is not None and job.file_key else None
    if job is None or job.tenant_id != tenant_id or job.deleted_at or content is None or view(job)["status"] != "ready":
        return PlainTextResponse(EXPIRED, status_code=410)
    return Response(content, media_type=jobs.CONTENT_TYPES[job.format], headers={
        "content-disposition": f'attachment; filename="{job.file_name}"', "cache-control": "no-store"})

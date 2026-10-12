"""Responses (mock: routes/responses.ts; API-CONTRACT → Responses, decision 100). Reading needs at least "Responses
only" on the form; status, tags and notes need `review`; changing answers needs `edit`, deleting `delete` (each with
its scope, the form's sharing and its folder). Every change is in the response's history and the audit trail, and
the outbox carries response events for webhooks and destinations (B9).

    GET  /forms/{id}/responses            one form's responses with their answers (filters, search, sort, pages)
    GET  /forms/{id}/responses/tags       tags used on them, most used first
    GET  /forms/{id}/responses/insights   numbers and charts for one form
    GET  /responses                       the inbox: every form this person may see
    GET  /responses/forms                 the Responses page grouped by form
    GET  /responses/insights              the inbox numbers
    POST /responses/bulk                  the same change for many (those not allowed are skipped)
    GET / PATCH / DELETE /responses/{id}  one response; status, tags, duplicate flag, edited answers
    POST /responses/{id}/notes            a note for the team
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.events.outbox import record_event
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms import access
from app.modules.forms.access import Viewer, viewer_for
from app.modules.forms.answers import validate_answer
from app.modules.forms.models import Form
from app.modules.forms.service import Names, forms_of, iso
from app.modules.public.submit import all_fields
from app.modules.responses import service
from app.modules.responses.answers import ANSWER_FILTER_PREFIX, answer_matches, can_edit_answer, is_empty_answer
from app.modules.destinations.service import FORMALIE_MARK, storage_marks
from app.modules.responses.models import RESPONSE_STATUSES, Response, ResponseChange, ResponseNote
from app.modules.responses.service import Entry

router = APIRouter(tags=["responses"])

patch_schema = z.obj(
    status=z.enum(list(RESPONSE_STATUSES)).optional(),
    tags=z.array(z.string().trim().min(1).max(40)).max(20).optional(),
    data=z.record(z.string().max(64), z.unknown()).optional(),
    duplicate=z.literal("cleared").optional(),
)
note_schema = z.obj(text=z.string().trim().min(1).max(2000))
bulk_schema = z.obj(ids=z.array(z.string().max(64)).min(1).max(500), action=z.enum(["status", "tag", "untag", "delete"]),
                    value=z.string().trim().max(40).optional())


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _list(query: dict[str, str], key: str) -> list[str] | None:
    value = query.get(f"filter[{key}]")
    return value.split(",") if value else None


def _day(value: str | None, end: bool) -> datetime | None:
    try:
        moment = datetime.combine(date.fromisoformat(value[:10]), datetime.min.time(), UTC) if value else None
    except ValueError:
        return None
    return moment + timedelta(days=1) - timedelta(milliseconds=1) if moment and end else moment


def _name(principal: Principal) -> str:
    return f"{principal.user.first_name} {principal.user.last_name}".strip()


async def _entries(db: Any, tenant_id: uuid.UUID, forms: list[Form]) -> list[Entry]:
    """Every response of these forms, newest first, read with each form's questions."""
    schemas = {f.id: await service.response_schema(db, f) for f in forms}
    by_id = {f.id: f for f in forms}
    responses = await service.responses_of(db, tenant_id, list(by_id))
    notes = await service.notes_counts(db, tenant_id, [r.id for r in responses])
    return [Entry(r, by_id[r.form_id], schemas[r.form_id], notes.get(r.id, 0)) for r in responses]


def filter_entries(entries: list[Entry], query: dict[str, str], search_answers: bool) -> list[Entry]:
    """Status, tag, channel, form, flag, date, answer and search filters, then sort (lists and exports share it)."""
    status, tag, channel, forms = (_list(query, k) for k in ("status", "tag", "channel", "form"))
    flagged = query.get("filter[flag]") == "duplicate"
    start, end = _day(query.get("from"), False), _day(query.get("to"), True)
    q = (query.get("q") or "").strip().lower()
    answer_filters = []
    if search_answers:
        for name in query:
            if name.startswith(f"filter[{ANSWER_FILTER_PREFIX}") and name.endswith("]"):
                key = name[len(f"filter[{ANSWER_FILTER_PREFIX}"):-1]
                wanted = _list(query, f"{ANSWER_FILTER_PREFIX}{key}")
                if wanted:
                    answer_filters.append((key, wanted))
    empty = _list(query, "empty") if search_answers else None

    def keep(e: Entry) -> bool:
        r = e.response
        data = r.data or {}
        if status and r.status not in status or tag and not any(t in tag for t in r.tags or []):
            return False
        if channel and r.channel not in channel or forms and str(e.form.id) not in forms:
            return False
        if flagged and not (r.possible_duplicate and not r.duplicate_cleared):
            return False
        if start and r.submitted_at < start or end and r.submitted_at > end:
            return False
        if not all(answer_matches(data.get(k), w) for k, w in answer_filters):
            return False
        if empty and not all(is_empty_answer(data.get(k)) for k in empty):
            return False
        if q:
            text = f"{e.title or ''} {e.respondent.get('email') or ''} {e.form.name}".lower()
            if not (str(r.number) == q.lstrip("#") or q in text
                    or (search_answers and q in json.dumps(data, ensure_ascii=False).lower())):
                return False
        return True
    result = [e for e in entries if keep(e)]
    sort = query.get("sort") or "-submitted_at"
    desc, key = sort.startswith("-"), sort.lstrip("-")

    def value(e: Entry) -> Any:
        if key == "number":
            return e.response.number
        if key == "status":
            return service.STATUS_ORDER[e.response.status]
        if key == "respondent":
            return (e.title or "~").lower()
        if key == "form":
            return e.form.name.lower()
        return e.response.submitted_at
    # Equal values keep newest first
    result.sort(key=lambda e: e.response.submitted_at, reverse=True)
    result.sort(key=value, reverse=desc)
    return result


def _page(items: list[Any], query: dict[str, str]) -> tuple[list[Any], dict[str, Any]]:
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return items[params.offset:params.offset + params.page_size], params.meta(len(items)).model_dump(exclude_none=True)


async def _form_for(db: Any, viewer: Viewer, form_id: str, action: str = "view") -> Form:
    try:
        form = await db.get(Form, uuid.UUID(form_id))
    except ValueError:
        form = None
    if form is None or form.tenant_id != viewer.principal.tenant.id or form.deleted_at or form.purged_at:
        raise FrmError("FRM-GEN-1004")
    service.require_responses(form, viewer, action)
    return form


async def _visible_forms(db: Any, viewer: Viewer, query: dict[str, str] | None = None) -> list[Form]:
    folder, owner = (_list(query or {}, "folder_id"), _list(query or {}, "owner_id"))
    return [f for f in await forms_of(db, viewer.principal.tenant.id)
            if f.deleted_at is None and access.responses_allowed(f, viewer, "view")
            and (not folder or (str(f.folder_id) if f.folder_id else "none") in folder)
            and (not owner or str(f.owner_id) in owner)]


# ── Lists ───────────────────────────────────────────────────────────────────────

@router.get("/forms/{form_id}/responses", dependencies=[rate_limit("responses-list", per_minute=240)])
async def list_form_responses(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        form = await _form_for(db, await viewer_for(db, principal), form_id)
        entries = await _entries(db, principal.tenant.id, [form])
    page, meta = _page(filter_entries(entries, query, True), query)
    return ok([service.row_of(e, True) for e in page], meta)


@router.get("/forms/{form_id}/responses/tags", dependencies=[rate_limit("responses-tags", per_minute=120)])
async def form_response_tags(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        form = await _form_for(db, await viewer_for(db, principal), form_id)
        responses = await service.responses_of(db, principal.tenant.id, [form.id])
    counts: dict[str, int] = {}
    for r in responses:
        for t in r.tags or []:
            counts[t] = counts.get(t, 0) + 1
    return ok([{"value": v, "count": c} for v, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))])


@router.get("/forms/{form_id}/responses/insights", dependencies=[rate_limit("responses-insights", per_minute=120)])
async def form_insights(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        form = await _form_for(db, await viewer_for(db, principal), form_id)
        entries = await _entries(db, principal.tenant.id, [form])
        schema = await service.response_schema(db, form)
    return ok(service.insights_of(entries, dict(request.query_params), form, schema))


@router.get("/responses", dependencies=[rate_limit("responses-inbox", per_minute=240)])
async def list_responses(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """The inbox; `filter[folder_id]` (an id or `none`) and `filter[owner_id]` narrow the forms."""
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        entries = await _entries(db, principal.tenant.id, await _visible_forms(db, viewer, query))
    page, meta = _page(filter_entries(entries, query, False), query)
    return ok([service.row_of(e, False) for e in page], meta)


@router.get("/responses/insights", dependencies=[rate_limit("responses-insights", per_minute=120)])
async def inbox_insights(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        entries = await _entries(db, principal.tenant.id, await _visible_forms(db, viewer))
    return ok(service.insights_of(entries, dict(request.query_params)))


@router.get("/responses/forms", dependencies=[rate_limit("responses-forms", per_minute=120)])
async def list_response_forms(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """One row per form with responses: counts by review status, last response, a 30-day trend. `q`,
    `filter[form_status]`, `filter[folder_id]`, `filter[review]`, `from` / `to`; sort `-new` (default) · `-last_at` ·
    `-total` · `name` (with a review status asked for, the default counts that status)."""
    query = dict(request.query_params)
    form_status, folder, review = (_list(query, k) for k in ("form_status", "folder_id", "review"))
    start, end = _day(query.get("from"), False), _day(query.get("to"), True)
    q = (query.get("q") or "").strip().lower()
    today = datetime.now(UTC).date()
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        names = await Names().load(db, principal.tenant.id)
        forms = [f for f in await _visible_forms(db, viewer)
                 if (not form_status or f.status in form_status)
                 and (not folder or (str(f.folder_id) if f.folder_id else "none") in folder)
                 and (not q or q in f.name.lower())]
        responses = await service.responses_of(db, principal.tenant.id, [f.id for f in forms])
        marks = await storage_marks(db, principal.tenant.id)
    by_form: dict[uuid.UUID, list[Response]] = {}
    for r in responses:
        if (start is None or r.submitted_at >= start) and (end is None or r.submitted_at <= end):
            by_form.setdefault(r.form_id, []).append(r)
    rows = []
    for form in forms:
        items = by_form.get(form.id)
        if not items:
            continue
        counts = {s: 0 for s in RESPONSE_STATUSES}
        daily = [0] * 30
        for r in items:
            counts[r.status] += 1
            index = 29 - (today - r.submitted_at.astimezone(UTC).date()).days
            if 0 <= index < 30:
                daily[index] += 1
        if review and not any(counts[s] > 0 for s in review if s in counts):
            continue
        folder_row = viewer.folders.get(form.folder_id) if form.folder_id else None
        rows.append({
            "id": str(form.id), "name": form.name, "status": form.status,
            "folder": {"id": str(folder_row.id), "name": folder_row.name} if folder_row else None,
            "owner": names.ref(form.owner_id), "public_key": form.public_key, "custom_link": form.custom_link,
            "completion_rate": form.completion_rate, "total": len(items), "status_counts": counts,
            "last_at": iso(items[0].submitted_at), "daily": daily,
            "storage": marks.get(form.id, FORMALIE_MARK), "can": access.response_actions_of(form, viewer),
        })
    sort = query.get("sort") or "-new"
    desc, key = sort.startswith("-"), sort.lstrip("-")

    def value(row: dict[str, Any]) -> Any:
        if key == "name":
            return row["name"].lower()
        if key == "total":
            return row["total"]
        if key == "last_at":
            return row["last_at"] or ""
        if key != "new" and key in row["status_counts"]:
            return row["status_counts"][key]
        return sum(row["status_counts"].get(s, 0) for s in (review or ["new"]))
    rows.sort(key=lambda r: r["last_at"] or "", reverse=True)
    rows.sort(key=value, reverse=desc)
    page, meta = _page(rows, query)
    return ok(page, meta)


# ── One response ────────────────────────────────────────────────────────────────

async def response_for(db: Any, viewer: Viewer, response_id: str, action: str) -> Entry:
    try:
        wanted = uuid.UUID(response_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    r = (await db.execute(select(Response).where(Response.tenant_id == viewer.principal.tenant.id, Response.id == wanted,
                                                 Response.deleted_at.is_(None)))).scalar_one_or_none()
    form = await db.get(Form, r.form_id) if r is not None else None
    if r is None or form is None or form.deleted_at or form.purged_at:
        raise FrmError("FRM-GEN-1004")
    service.require_responses(form, viewer, action)
    notes = await service.notes_counts(db, viewer.principal.tenant.id, [r.id])
    return Entry(r, form, await service.response_schema(db, form), notes.get(r.id, 0))


@router.get("/responses/{response_id}", dependencies=[rate_limit("responses-get", per_minute=240)])
async def get_response(response_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        entry = await response_for(db, viewer, response_id, "view")
        return ok(await service.detail_of(db, entry, viewer))


async def _audit(db: Any, principal: Principal, action: str, entry: Entry, changes: list[dict[str, Any]] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), changes=changes or [],
                 resource={"type": "response", "id": str(entry.response.id),
                           "name": f"#{entry.response.number} · {entry.form.name}"})


async def _event(db: Any, kind: str, entry: Entry, extra: dict[str, Any] | None = None) -> None:
    """For webhooks and destinations (B9): ids only, never answers."""
    await record_event(db, kind, {"form_id": str(entry.form.id), "response_id": str(entry.response.id),
                                  "submitted_at": iso(entry.response.submitted_at), **(extra or {})})
    if kind in ("response.updated", "response.status_changed"):
        from app.modules.destinations.service import response_changed

        await response_changed(db, entry.form, entry.response)  # the row in the form's table follows
    from app.modules.webhooks.service import response_event

    await response_event(db, kind, entry.form, entry.response, (extra or {}).get("before"))  # the workspace's webhooks


async def _history(db: Any, principal: Principal, entry: Entry, changes: list[dict[str, Any]]) -> None:
    now = datetime.now(UTC)
    for change in changes:
        db.add(ResponseChange(tenant_id=entry.response.tenant_id, organisation_id=entry.response.organisation_id,
                              response_id=entry.response.id, response_submitted_at=entry.response.submitted_at,
                              at=now, by_id=principal.user.id, by_name=_name(principal), field=change["field"],
                              before=change["before"], after=change["after"]))


async def _check_edits(db: Any, entry: Entry, data: dict[str, Any]) -> None:
    """Edited answers are checked like a submission: only questions of the version answered that may be edited,
    each value through the same rules as the form page."""
    schema = await service.version_schema(db, entry.form, entry.response.form_version_no)
    fields = {f["key"]: f for f in all_fields(schema or {"pages": []})}
    problems = []
    for key, value in data.items():
        fld = fields.get(key)
        if fld is None or not can_edit_answer(fld):
            problems.append({"field": key, "message": "This answer can not be edited."})
        else:
            issue = validate_answer(fld, value, bool(fld.get("required")))
            if issue:
                problems.append({"field": key, "message": issue["code"]})
    if problems:
        raise FrmError("FRM-RESP-1001", problems)


@router.patch("/responses/{response_id}", dependencies=[rate_limit("responses-update", per_minute=240)])
async def patch_response(response_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Status, tags, the duplicate flag (review) or answers (edit); each change kept in the history."""
    data = patch_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        entry = await response_for(db, viewer, response_id, "edit" if "data" in data else "review")
        if "data" in data and any(k in data for k in ("status", "tags", "duplicate")):
            service.require_responses(entry.form, viewer, "review")
        if "data" in data:
            await _check_edits(db, entry, data["data"])
        r = entry.response
        current = r.data or {}
        changes: list[dict[str, Any]] = []
        old_status = r.status
        if data.get("status") and data["status"] != r.status:
            changes.append({"field": "status", "before": r.status, "after": data["status"]})
        tags = list(dict.fromkeys(data["tags"])) if "tags" in data else None
        if tags is not None and tags != list(r.tags or []):
            changes.append({"field": "tags", "before": list(r.tags or []), "after": tags})
        if data.get("duplicate") and r.possible_duplicate and not r.duplicate_cleared:
            changes.append({"field": "duplicate", "before": "possible", "after": "not a duplicate"})
        for key, value in (data.get("data") or {}).items():
            if json.dumps(current.get(key)) != json.dumps(value):
                changes.append({"field": f"answer:{key}", "before": current.get(key), "after": value})
        if changes:
            if data.get("status"):
                r.status = data["status"]
            if tags is not None:
                r.tags = tags
            if data.get("duplicate"):
                r.duplicate_cleared = True
            if data.get("data"):
                r.data, r.edited = {**current, **data["data"]}, True
            r.updated_at, r.updated_by, r.row_version = datetime.now(UTC), principal.user.id, r.row_version + 1
            await _history(db, principal, entry, changes)
            labels = {f"answer:{f['key']}": (f.get("label") or "").strip() or f["key"]
                      for f in all_fields(await service.version_schema(db, entry.form, r.form_version_no) or {"pages": []})}
            await _audit(db, principal, "responses.updated", entry,
                         [{**c, "field": labels.get(c["field"], c["field"])} for c in changes])
            if data.get("status") and data["status"] != old_status:
                await _event(db, "response.status_changed", entry, {"before": old_status, "after": data["status"]})
            if any(c["field"].startswith("answer:") for c in changes):
                await _event(db, "response.updated", entry)
            await db.flush()
        fresh = Entry(r, entry.form, entry.schema, entry.notes)
        return ok(await service.detail_of(db, fresh, viewer))


@router.post("/responses/{response_id}/notes", dependencies=[rate_limit("responses-notes", per_minute=120)])
async def add_note(response_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """A note for the team (never shown to the respondent)."""
    text = note_schema.parse(await request.json())["text"]
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        entry = await response_for(db, viewer, response_id, "review")
        db.add(ResponseNote(tenant_id=entry.response.tenant_id, organisation_id=entry.response.organisation_id,
                            response_id=entry.response.id, response_submitted_at=entry.response.submitted_at,
                            author_id=principal.user.id, author_name=_name(principal), text=text,
                            created_by=principal.user.id))
        await db.flush()
        await _audit(db, principal, "responses.updated", entry, [{"field": "note", "before": None, "after": "added"}])
        return ok(await service.detail_of(db, entry, viewer))


async def _delete(db: Any, principal: Principal, entry: Entry) -> None:
    entry.response.deleted_at, entry.response.deleted_by = datetime.now(UTC), principal.user.id
    await db.execute(update(Form).where(Form.id == entry.form.id, Form.responses_count > 0)
                     .values(responses_count=Form.responses_count - 1))
    await _audit(db, principal, "responses.deleted", entry)
    await _event(db, "response.deleted", entry)


@router.delete("/responses/{response_id}", dependencies=[rate_limit("responses-delete", per_minute=120)])
async def delete_response(response_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """Gone from every list and count (the row stays, deleted_at); editors only."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        await _delete(db, principal, await response_for(db, viewer, response_id, "delete"))
    return ok({"deleted": 1})


@router.post("/responses/bulk", dependencies=[rate_limit("responses-bulk", per_minute=30)])
async def bulk_responses(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """The same change for many; those the person may not change are skipped."""
    data = bulk_schema.parse(await request.json())
    action, value = data["action"], data.get("value")
    if action == "status" and value not in RESPONSE_STATUSES:
        raise FrmError("FRM-GEN-1002", [{"field": "value", "message": "Unknown status."}])
    if action in ("tag", "untag") and not value:
        raise FrmError("FRM-GEN-1002", [{"field": "value", "message": "Tag required."}])
    done = skipped = 0
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        for response_id in data["ids"]:
            try:
                entry = await response_for(db, viewer, response_id, "delete" if action == "delete" else "review")
            except FrmError:
                skipped += 1
                continue
            r = entry.response
            if action == "delete":
                await _delete(db, principal, entry)
            else:
                field = "status" if action == "status" else "tags"
                before = r.status if action == "status" else list(r.tags or [])
                after = value if action == "status" else (list(dict.fromkeys([*(r.tags or []), value])) if action == "tag"
                                                         else [t for t in r.tags or [] if t != value])
                if before != after:
                    if action == "status":
                        r.status = value  # type: ignore[assignment]
                    else:
                        r.tags = after  # type: ignore[assignment]
                    r.updated_at, r.updated_by, r.row_version = datetime.now(UTC), principal.user.id, r.row_version + 1
                    await _history(db, principal, entry, [{"field": field, "before": before, "after": after}])
                    await _audit(db, principal, "responses.updated", entry, [{"field": field, "before": before, "after": after}])
                    if action == "status":
                        await _event(db, "response.status_changed", entry, {"before": before, "after": value})
            done += 1
    return ok({"done": done, "skipped": skipped})

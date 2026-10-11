"""Forms and folders (mock: routes/forms.ts, API-CONTRACT → Forms). Every change bumps `row_version` (a stale one
is FRM-GEN-1009) and is recorded in the audit trail with before / after values. Each change is its own action
(F22 R2): name → rename, folder → move, dates → availability, tags → edit; lifecycle: unpublish · close · reopen →
close, archive · unarchive → archive, restore → delete; purging → purge.

Forms from a template: Formalie's (in the person's language) or the workspace's own (templates module).
"""

from __future__ import annotations

import copy
import re
import uuid
from datetime import UTC, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms import access, service
from app.modules.forms.access import Viewer, viewer_for
from app.modules.forms.catalogues import FOLDER_COLOR_KEYS
from app.modules.forms.models import Folder, Form
from app.modules.forms.schema import blank_schema, form_schema_v1
from app.modules.forms.service import Names, iso

router = APIRouter(tags=["forms"])

_name = z.string().trim().min(1, "Give the form a name.").max(120)
create_schema = z.obj(
    name=_name, folder_id=z.string().nullable().optional(), template_key=z.string().max(80).nullable().optional(),
    label_position=z.enum(["top", "left"]).optional(),
    language=z.string().regex(r"^[a-z]{2}(-[A-Z]{2})?$").optional(),
)
import_schema = z.obj(name=_name, folder_id=z.string().nullable().optional(), schema=form_schema_v1)
_datetime = z.string().regex(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$", "Invalid ISO datetime")
patch_schema = z.obj(
    row_version=z.number().int(), name=_name.optional(), folder_id=z.string().nullable().optional(),
    tags=z.array(z.string().trim().lower().min(1).max(30)
                 .regex(re.compile(r"^[\w \-]+$"), "Letters, numbers, spaces, - and _.")).max(20).optional(),
    opens_at=_datetime.nullable().optional(), closes_at=_datetime.nullable().optional(),
)
lifecycle_schema = z.obj(row_version=z.number().int().optional())
bulk_schema = z.obj(action=z.enum(["archive", "move", "delete", "restore", "purge"]),
                    ids=z.array(z.string()).min(1).max(100), folder_id=z.string().nullable().optional())
folder_schema = z.obj(
    name=z.string().trim().min(1, "Give the folder a name.").max(60),
    color=z.union([z.enum(list(FOLDER_COLOR_KEYS)), z.string().regex(r"^#[0-9a-fA-F]{6}$")]).optional(),
)
folder_patch = z.obj(
    name=z.string().trim().min(1, "Give the folder a name.").max(60).optional(),
    color=z.union([z.enum(list(FOLDER_COLOR_KEYS)), z.string().regex(r"^#[0-9a-fA-F]{6}$")]).optional(),
)
access_schema = z.obj(restricted=z.boolean(), roles=z.array(z.string().max(64)).max(50).optional(),
                      departments=z.array(z.string().max(64)).max(200).optional(),
                      people=z.array(z.string().max(64)).max(500).optional())

TRANSITIONS = {
    "unpublish": (("published",), "forms.unpublished"), "close": (("published",), "forms.closed"),
    "reopen": (("closed",), "forms.reopened"), "archive": (("draft", "published", "closed"), "forms.archived"),
    "unarchive": (("archived",), "forms.unarchived"),
}
LIFECYCLE_NEEDS = {"unpublish": "close", "close": "close", "reopen": "close", "archive": "archive",
                   "unarchive": "archive", "restore": "delete"}


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _list(query: dict[str, str], key: str) -> list[str] | None:
    value = query.get(f"filter[{key}]")
    return value.split(",") if value else None


def _day(value: str | None, end: bool) -> datetime | None:
    try:
        day = datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(day, time(23, 59, 59) if end else time(0, 0), tzinfo=UTC)


def _natural(value: Any) -> list[Any]:
    """localeCompare(…, { numeric: true }): numbers inside text compare as numbers."""
    text = "" if value is None else str(value)
    return [(0, int(part), "") if part.isdigit() else (1, 0, part.casefold()) for part in re.split(r"(\d+)", text)]


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


# ── Lists ───────────────────────────────────────────────────────────────────────

@router.get("/forms", dependencies=[rate_limit("forms-list", per_minute=240)])
async def list_forms(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Filters: status, folder_id (`none` = no folder), owner_id, tag, template (comma = any of), trash=1;
    from / to on updated_at; q on name, slug and tags."""
    query = dict(request.query_params)
    status, folder, owner = _list(query, "status"), _list(query, "folder_id"), _list(query, "owner_id")
    tag, template = _list(query, "tag"), _list(query, "template")
    trash = query.get("filter[trash]") == "1"
    start, end = _day(query.get("from"), False), _day(query.get("to"), True)
    async with db_session("write", **_scope(principal)) as db:
        await service.sweep_trash(db, principal.tenant.id)
        viewer = await viewer_for(db, principal)
        names = await Names().load(db, principal.tenant.id)
        forms = [f for f in await service.forms_of(db, principal.tenant.id) if access.can_see(f, viewer)
                 and (f.deleted_at is not None) == trash
                 and (trash or (f.status in status if status else f.status != "archived"))
                 and (not folder or str(f.folder_id or "none") in folder)
                 and (not owner or str(f.owner_id) in owner)
                 and (not tag or any(t in tag for t in f.tags))
                 and (not template or (f.template_key or "") in template)
                 and (start is None or f.updated_at >= start) and (end is None or f.updated_at <= end)]
        rows = [service.summary(f, viewer, names) for f in forms]
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in r["name"].lower() or q in r["slug"] or q in r["tags"]]
    sort = query.get("sort") or ("-deleted_at" if trash else "-updated_at")
    key = sort.lstrip("-")
    rows.sort(key=lambda r: _natural(r.get(key)), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    for row in rows:
        row["storage"] = {"mode": "formalie", "datasource": None, "engine": None}  # response storage: B9
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/forms/facets", dependencies=[rate_limit("forms-facets", per_minute=120)])
async def form_facets(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        names = await Names().load(db, principal.tenant.id)
        forms = [f for f in await service.forms_of(db, principal.tenant.id)
                 if f.deleted_at is None and access.can_see(f, viewer)]
        from app.modules.templates.service import all_templates

        made_from = {f.template_key for f in forms if f.template_key}
        templates = [{"key": t["key"], "name": t["name"]} for t in await all_templates(db, principal.tenant.id, "en", names)
                     if t["key"] in made_from] if made_from else []
    owners = {f.owner_id: names.ref(f.owner_id) for f in forms}
    return ok({
        "owners": sorted(owners.values(), key=lambda o: o["name"].casefold()),  # type: ignore[index]
        "tags": sorted({t for f in forms for t in f.tags}),
        "templates": sorted(templates, key=lambda t: t["name"].casefold()),
    })


@router.get("/forms/{form_id}", dependencies=[rate_limit("forms-get", per_minute=240)])
async def get_form(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await service.find_form(db, viewer, form_id, action="view")
        names = await Names().load(db, principal.tenant.id)
        # Without preview (responses only): no questions or design
        shown = access.allows(form, viewer, "preview") or access.allows(form, viewer, "edit")
        return ok({**service.summary(form, viewer, names), "template_key": form.template_key,
                   "schema": form.draft_schema if shown else None})


# ── Create ──────────────────────────────────────────────────────────────────────

@router.post("/forms", status_code=201, dependencies=[rate_limit("forms-create", per_minute=30)])
async def create_form(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = create_schema.parse(await request.json())
    key, language = body.get("template_key"), body.get("language") or "en"
    from app.modules.templates.service import schema_for_template

    async with db_session("write", **_scope(principal)) as db:
        # Templates: Formalie's (in the person's language, over the workspace's branding) or the workspace's own
        schema = await schema_for_template(db, principal.tenant.id, key, language) if key else blank_schema(language)
        if schema is None:
            raise FrmError("FRM-GEN-1002", [{"field": "template_key", "message": "Choose a template from the gallery."}])
        viewer = await viewer_for(db, principal)
        folder = service.visible_folder(viewer, body.get("folder_id"))
        form = await service.new_form(db, viewer, name=body["name"], folder=folder, schema=schema, template_key=key)
        await service.with_form_defaults(db, form, body.get("label_position"))
        await service.audit(db, viewer, "forms.created", form,
                            metadata={"source": "template", "template": key} if key else {"source": "blank"})
        return ok(service.summary(form, viewer, await Names().load(db, principal.tenant.id)))


@router.post("/forms/import", status_code=201, dependencies=[rate_limit("forms-create", per_minute=30)])
async def import_form(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = import_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        folder = service.visible_folder(viewer, body.get("folder_id"))
        form = await service.new_form(db, viewer, name=body["name"], folder=folder, schema=body["schema"])
        await service.audit(db, viewer, "forms.created", form, metadata={"source": "import"})
        return ok(service.summary(form, viewer, await Names().load(db, principal.tenant.id)))


@router.post("/forms/{form_id}/duplicate", status_code=201, dependencies=[rate_limit("forms-create", per_minute=30)])
async def duplicate_form(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        source = await service.find_form(db, viewer, form_id, action="duplicate")
        folder = viewer.folders.get(source.folder_id) if source.folder_id else None
        copy_ = await service.new_form(db, viewer, name=f"{source.name} (copy)"[:120], folder=folder,
                                       schema=copy.deepcopy(source.draft_schema) if source.draft_schema else None,  # type: ignore[arg-type]
                                       template_key=source.template_key)
        copy_.tags = list(source.tags)
        await service.audit(db, viewer, "forms.created", copy_, metadata={"source": "duplicate", "from": source.name})
        return ok(service.summary(copy_, viewer, await Names().load(db, principal.tenant.id)))


# ── Change ──────────────────────────────────────────────────────────────────────

@router.patch("/forms/{form_id}", dependencies=[rate_limit("forms-update", per_minute=120)])
async def patch_form(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await service.find_form(db, viewer, form_id, action="view")
        body = patch_schema.parse(await request.json())
        wants = ([*(["rename"] if "name" in body and body["name"] != form.name else []),
                  *(["move"] if "folder_id" in body and body["folder_id"] != (str(form.folder_id) if form.folder_id else None) else []),
                  *(["availability"] if "opens_at" in body or "closes_at" in body else []),
                  *(["edit"] if "tags" in body else [])])
        for action in wants:
            access.require_action(form, viewer, action)
        service.check_version(form, body["row_version"])
        changes: list[dict[str, Any]] = []
        if "name" in body and body["name"] != form.name:
            changes.append({"field": "name", "before": form.name, "after": body["name"]})
            form.name = body["name"]
        if "move" in wants:
            folder = service.visible_folder(viewer, body["folder_id"])
            before = viewer.folders.get(form.folder_id) if form.folder_id else None
            changes.append({"field": "folder", "before": before.name if before else None,
                            "after": folder.name if folder else None})
            form.folder_id = folder.id if folder else None
        for key in ("opens_at", "closes_at"):
            if key in body and _parse_time(body[key]) != getattr(form, key):
                changes.append({"field": key, "before": iso(getattr(form, key)), "after": body[key]})
                setattr(form, key, _parse_time(body[key]))
        if form.opens_at and form.closes_at and form.closes_at <= form.opens_at:
            raise FrmError("FRM-GEN-1002", [{"field": "closes_at", "message": "Choose an end after the start."}])
        if "tags" in body:
            tags = sorted(set(body["tags"]))
            if tags != list(form.tags):
                changes.append({"field": "tags", "before": ", ".join(form.tags) or None, "after": ", ".join(tags) or None})
                form.tags = tags
        if changes:
            service.touch(form, viewer)
            await service.audit(db, viewer, "forms.updated", form, changes)
        return ok(service.summary(form, viewer, await Names().load(db, principal.tenant.id)))


def _apply_lifecycle(form: Form, action: str) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    if action == "restore":
        if form.deleted_at is None:
            raise FrmError("FRM-FORM-1007")
        form.deleted_at, form.deleted_by = None, None
        return []
    allowed, _ = TRANSITIONS[action]
    if form.deleted_at is not None or form.status not in allowed:
        raise FrmError("FRM-FORM-1007")
    before = form.status
    form.status = {"unpublish": "draft", "close": "closed", "reopen": "published", "archive": "archived",
                   "unarchive": form.previous_status or "draft"}[action]
    form.previous_status = before if action == "archive" else None
    if action == "close":
        form.closed_at = now
    if action == "archive":
        form.archived_at = now
    return [{"field": "status", "before": before, "after": form.status}]


async def _purge(db: Any, viewer: Viewer, form: Form) -> None:
    """Gone from Trash and every list for good; the row stays (purged_at). Its short code is never reused."""
    form.purged_at = datetime.now(UTC)


@router.post("/forms/bulk", dependencies=[rate_limit("forms-bulk", per_minute=20)])
async def bulk_forms(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """One result per form; a form that can't take the action is reported, not fatal."""
    body = bulk_schema.parse(await request.json())
    needs = {"archive": "archive", "move": "move", "delete": "delete", "restore": "delete", "purge": "purge"}
    result: dict[str, Any] = {"updated": 0, "failed": []}
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        folder = service.visible_folder(viewer, body.get("folder_id")) if body["action"] == "move" else None
        for form_id in body["ids"]:
            try:
                async with db.begin_nested():
                    trash = body["action"] in ("restore", "purge")
                    form = await service.find_form(db, viewer, form_id, action=needs[body["action"]], trash=trash)
                    if body["action"] == "move":
                        if form.folder_id != (folder.id if folder else None):
                            before = viewer.folders.get(form.folder_id) if form.folder_id else None
                            form.folder_id = folder.id if folder else None
                            service.touch(form, viewer)
                            await service.audit(db, viewer, "forms.updated", form, [{
                                "field": "folder", "before": before.name if before else None,
                                "after": folder.name if folder else None}], {"via": "bulk"})
                    elif body["action"] == "delete":
                        form.deleted_at, form.deleted_by = datetime.now(UTC), viewer.user_id
                        service.touch(form, viewer)
                        await service.audit(db, viewer, "forms.deleted", form, metadata={"via": "bulk"})
                    elif body["action"] == "purge":
                        await _purge(db, viewer, form)
                        await service.audit(db, viewer, "forms.purged", form, metadata={"via": "bulk"})
                    else:
                        if body["action"] == "restore":
                            await service.require_form_slot(db, viewer)
                        changes = _apply_lifecycle(form, body["action"])
                        service.touch(form, viewer)
                        await service.audit(db, viewer, "forms.restored" if body["action"] == "restore" else "forms.archived",
                                            form, changes, {"via": "bulk"})
                    result["updated"] += 1
            except FrmError as error:
                result["failed"].append({"id": form_id, "code": error.code})
    return ok(result)


@router.delete("/forms/trash", dependencies=[rate_limit("forms-trash", per_minute=10)])
async def empty_trash(principal: Principal = Depends(require_auth)) -> Any:
    """Only the forms this person may purge; the others they can see stay and are counted in `skipped`."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        trashed = [f for f in await service.forms_of(db, principal.tenant.id) if f.deleted_at is not None]
        gone = [f for f in trashed if access.allows(f, viewer, "purge")]
        skipped = sum(1 for f in trashed if access.can_see(f, viewer) and not access.allows(f, viewer, "purge"))
        for form in gone:
            await _purge(db, viewer, form)
            await service.audit(db, viewer, "forms.purged", form, metadata={"via": "empty_trash"})
    return ok({"deleted": len(gone), "skipped": skipped})


@router.delete("/forms/{form_id}", dependencies=[rate_limit("forms-delete", per_minute=60)])
async def delete_form(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """→ Trash; `?permanent=1` on a form already in Trash purges it."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        if request.query_params.get("permanent") == "1":
            form = await service.find_form(db, viewer, form_id, action="purge", trash=True)
            await _purge(db, viewer, form)
            await service.audit(db, viewer, "forms.purged", form)
            return ok({"deleted": True})
        form = await service.find_form(db, viewer, form_id, action="delete")
        form.deleted_at, form.deleted_by = datetime.now(UTC), viewer.user_id
        service.touch(form, viewer)
        await service.audit(db, viewer, "forms.deleted", form, metadata={"kept_in_trash": "30 days"})
        return ok(service.summary(form, viewer, await Names().load(db, principal.tenant.id)))


@router.post("/forms/{form_id}/{action}", dependencies=[rate_limit("forms-lifecycle", per_minute=60)])
async def form_lifecycle(form_id: str, action: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """unpublish · close · reopen · archive · unarchive · restore (from Trash)."""
    if action not in LIFECYCLE_NEEDS:
        raise FrmError("FRM-GEN-1004")
    raw = await request.body()
    body = lifecycle_schema.parse((await request.json()) if raw else {})
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await service.find_form(db, viewer, form_id, action=LIFECYCLE_NEEDS[action], trash=action == "restore")
        service.check_version(form, body.get("row_version"))
        if action == "restore":
            await service.require_form_slot(db, viewer)
        changes = _apply_lifecycle(form, action)
        service.touch(form, viewer)
        await service.audit(db, viewer, "forms.restored" if action == "restore" else TRANSITIONS[action][1], form, changes)
        return ok(service.summary(form, viewer, await Names().load(db, principal.tenant.id)))


# ── Folders ─────────────────────────────────────────────────────────────────────

async def _folder_audit(db: Any, viewer: Viewer, action: str, folder: Folder, changes: list[dict[str, Any]] | None = None,
                        metadata: dict[str, str] | None = None) -> None:
    tenant = viewer.principal.tenant
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action=action,
                 actor=Actor.user(viewer.principal.user), resource={"type": "folder", "id": str(folder.id),
                                                                    "name": folder.name},
                 changes=changes or [], metadata=metadata or {})


async def _name_free(db: Any, tenant_id: uuid.UUID, name: str, except_id: uuid.UUID | None = None) -> None:
    taken = (await db.execute(select(Folder).where(Folder.tenant_id == tenant_id, Folder.deleted_at.is_(None)))).scalars()
    if any(f.id != except_id and f.name.lower() == name.lower() for f in taken):
        raise FrmError("FRM-FORM-1008", [{"field": "name", "message": "A folder with this name exists."}])


def _find_folder(viewer: Viewer, folder_id: str, *, visible: bool = True) -> Folder:
    try:
        folder = viewer.folders.get(uuid.UUID(folder_id))
    except ValueError:
        folder = None
    if folder is None or (visible and not access.folder_visible(folder, viewer)):
        raise FrmError("FRM-GEN-1004")
    return folder


@router.get("/folders", dependencies=[rate_limit("folders-list", per_minute=240)])
async def list_folders(principal: Principal = Depends(require_auth)) -> Any:
    """With the forms in each that this person can see (Trash and archived not counted)."""
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        names = await Names().load(db, principal.tenant.id)
        forms = [f for f in await service.forms_of(db, principal.tenant.id)
                 if f.deleted_at is None and f.status != "archived" and access.can_see(f, viewer)]
    rows = [{**service.folder_view(folder, viewer, names),
             "forms_count": sum(1 for f in forms if f.folder_id == folder.id)}
            for folder in viewer.folders.values() if access.folder_visible(folder, viewer)]
    return ok(sorted(rows, key=lambda r: r["name"].casefold()))


@router.post("/folders", status_code=201, dependencies=[rate_limit("folders-create", per_minute=30)])
async def create_folder(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = folder_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        await _name_free(db, principal.tenant.id, body["name"])
        folder = Folder(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                        name=body["name"], color=body.get("color") or "ink", created_by=principal.user.id)
        db.add(folder)
        await db.flush()
        await db.refresh(folder)
        viewer = await viewer_for(db, principal)
        await _folder_audit(db, viewer, "forms.folder_created", folder)
        return ok({**service.folder_view(folder, viewer, await Names().load(db, principal.tenant.id)), "forms_count": 0})


@router.patch("/folders/{folder_id}", dependencies=[rate_limit("folders-update", per_minute=60)])
async def rename_folder(folder_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """The name, the colour, or both."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        folder = _find_folder(viewer, folder_id)
        if not access.folder_actions(folder, viewer)["edit"]:
            raise FrmError("FRM-PERM-1001")
        body = folder_patch.parse(await request.json())
        name = body.get("name") or folder.name
        await _name_free(db, principal.tenant.id, name, folder.id)
        before, before_color = folder.name, folder.color or "ink"
        folder.name = name
        if body.get("color"):
            folder.color = body["color"]
        folder.updated_at, folder.updated_by = datetime.now(UTC), principal.user.id
        changes = ([{"field": "name", "before": before, "after": name}] if before != name else []) + (
            [{"field": "colour", "before": before_color, "after": body["color"]}]
            if body.get("color") and body["color"] != before_color else [])
        if changes:
            await _folder_audit(db, viewer, "forms.folder_renamed", folder, changes)
        return ok(service.folder_view(folder, viewer, await Names().load(db, principal.tenant.id)))


@router.delete("/folders/{folder_id}", dependencies=[rate_limit("folders-delete", per_minute=30)])
async def delete_folder(folder_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """Only empty folders (forms in Trash just lose the folder)."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        folder = _find_folder(viewer, folder_id)
        if not access.folder_actions(folder, viewer)["delete"]:
            raise FrmError("FRM-PERM-1001")
        forms = [f for f in await service.forms_of(db, principal.tenant.id) if f.folder_id == folder.id]
        if any(f.deleted_at is None for f in forms):
            raise FrmError("FRM-FORM-1013")
        for form in forms:
            form.folder_id = None
        folder.deleted_at, folder.deleted_by = datetime.now(UTC), principal.user.id
        await _folder_audit(db, viewer, "forms.folder_deleted", folder, metadata={"forms_moved_out": str(len(forms))})
    return ok({"deleted": True, "forms_moved_out": len(forms)})


@router.put("/folders/{folder_id}/access", dependencies=[rate_limit("folders-access", per_minute=30)])
async def set_folder_access(folder_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Who may see the folder and its forms (needs folders.access). Restricted with nobody listed = only Owner and
    the people who decide folder access."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        folder = _find_folder(viewer, folder_id, visible=False)
        body = access_schema.parse(await request.json())

        def describe(restricted: bool, roles: list[Any], departments: list[Any], people: list[Any]) -> str:
            return (f"restricted: {len(roles)} roles, {len(departments)} departments, {len(people)} people"
                    if restricted else "everyone")
        before = describe(folder.access_restricted, folder.access_roles, folder.access_departments, folder.access_people)
        restricted = body["restricted"]
        folder.access_restricted = restricted
        folder.access_roles = list(dict.fromkeys(body.get("roles") or [])) if restricted else []
        folder.access_departments = list(dict.fromkeys(body.get("departments") or [])) if restricted else []
        folder.access_people = list(dict.fromkeys(body.get("people") or [])) if restricted else []
        after = describe(restricted, folder.access_roles, folder.access_departments, folder.access_people)
        if before != after:
            await _folder_audit(db, viewer, "forms.folder_access_changed", folder,
                                [{"field": "access", "before": before, "after": after}])
        return ok(service.folder_view(folder, viewer, await Names().load(db, principal.tenant.id)))

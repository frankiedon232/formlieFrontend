"""Option lists (mock: routes/optionLists.ts, API-CONTRACT → Option lists, docs/OPTION-LISTS.md).

    GET    /option-lists                       all (builder) · with ?page= the Option sets page (rows, filters, sort)
    GET    /option-lists/insights              counts for the page's chart cards
    POST   /option-lists                       { name, description?, levels?, columns?, large?, options }
    GET    /option-lists/{id} · PATCH · DELETE (delete: forms keep their copies)
    GET    /option-lists/{id}/usage            forms and fields using it, and whether they match it
    GET    /option-lists/{id}/options          one level of a list as people type (q, values, parents)
    POST   /option-lists/{id}/sync             { form_ids? } → copies the list into those drafts
    POST   /option-lists/{id}/duplicate

Values must be different within a list (FRM-FORM-1020); a list holds up to 20,000 options, a large one up to
200,000 (FRM-FORM-1022). Every change is in the audit trail.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms.service import Names
from app.modules.lists import rules, service
from app.modules.lists.models import OptionList
from app.modules.rbac.resources import require_resource, resource_actions

router = APIRouter(tags=["option-lists"])

_item = z.obj(
    value=z.string().trim().min(1).max(200), label=z.string().max(500), score=z.number().optional(),
    active=z.boolean().optional(), translations=z.record(z.string().max(10), z.string().max(500)).optional(),
    level=z.number().int().min(0).max(rules.MAX_LIST_LEVELS - 1).optional(), parent=z.string().trim().max(200).optional(),
    attrs=z.record(z.string().max(40), z.union([z.string().max(500), z.number()])).optional(),
)
_level = z.obj(key=z.string().trim().min(1).max(40), label=z.string().trim().min(1).max(60))
_column = z.obj(key=z.string().trim().min(1).max(40).regex(r"^[a-z][a-z0-9_]*$"),
                label=z.string().trim().min(1).max(60))


def _list_body(partial: bool) -> z.Schema:
    def maybe(schema: z.Schema) -> z.Schema:
        return schema.optional() if partial else schema
    return z.obj(
        name=maybe(z.string().trim().min(1).max(80)),
        description=z.string().trim().max(300).nullable().optional(),
        levels=z.array(_level).max(rules.MAX_LIST_LEVELS).optional(),
        columns=z.array(_column).max(10).optional(),
        large=z.boolean().optional(),
        options=maybe(z.array(_item).min(1).max(rules.MAX_LARGE_OPTIONS)),
    )


create_body, patch_body = _list_body(False), _list_body(True)
sync_body = z.obj(form_ids=z.array(z.string().max(64)).max(500).optional())


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _levels(levels: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    return [{"key": i["key"], "label": i["label"]} for i in levels] if levels and len(levels) > 1 else None


def _columns(columns: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    seen: set[str] = set()
    kept = []
    for column in columns or []:
        if column["key"] not in seen:
            seen.add(column["key"])
            kept.append({"key": column["key"], "label": column["label"]})
    return kept or None


def _size(count: int, large: bool) -> None:
    if count > (rules.MAX_LARGE_OPTIONS if large else rules.MAX_OPTIONS):
        raise FrmError("FRM-FORM-1022", [{"field": "options", "message": str(count)}])


async def _name_free(db: Any, tenant_id: Any, name: str, except_id: Any = None) -> None:
    if any(r.id != except_id and r.name.lower() == name.lower() for r in await service.lists_of(db, tenant_id)):
        raise FrmError("FRM-FORM-1009", [{"field": "name", "message": "taken"}])


async def _audit(db: Any, principal: Principal, action: str, row: OptionList, *, changes: list[dict[str, Any]] | None = None,
                 metadata: dict[str, str] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource={"type": "option_list", "id": str(row.id), "name": row.name},
                 changes=changes or [], metadata=metadata or {})


def _can(row: OptionList, principal: Principal) -> dict[str, bool]:
    return resource_actions("lists", row.created_by, principal, system=bool(row.system_key))


def _row(lst: dict[str, Any], forms: list[Any], languages: list[str], can: dict[str, bool]) -> dict[str, Any]:
    """OptionListRow: counts, languages fully translated, use."""
    usage = service.usage_of(forms, lst)
    active = [o for o in lst["options"] if o.get("active") is not False]
    return {**lst, "description": lst.get("description"), "items_count": len(active),
            "retired_count": len(lst["options"]) - len(active),
            "languages": [c for c in languages if active and all((o.get("translations") or {}).get(c, "").strip() for o in active)],
            "forms_count": len(usage), "fields_count": sum(len(u["fields"]) for u in usage), "can": can}


async def _everything(db: Any, principal: Principal) -> tuple[list[tuple[OptionList, dict[str, Any]]], list[Any]]:
    names = await Names().load(db, principal.tenant.id)
    rows = sorted(await service.lists_of(db, principal.tenant.id), key=lambda r: r.name.casefold())
    lists = [(r, service.as_list(r, await service.options_of(db, r), names)) for r in rows]
    return lists, await service.live_forms(db, principal.tenant.id)


def _languages(lists: list[tuple[OptionList, dict[str, Any]]]) -> list[str]:
    return list(dict.fromkeys(code for _, lst in lists for o in lst["options"] for code in (o.get("translations") or {})))


@router.get("/option-lists", dependencies=[rate_limit("lists-list", per_minute=120)])
async def list_option_lists(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        lists, forms = await _everything(db, principal)
    if "page" not in query:
        # The builder wants them all; lists kept on the server: counts per level instead of their options
        return ok([{**({**lst, "options": [], "level_counts": rules.level_counts(lst)} if rules.kept_on_server(lst) else lst),
                    "can": _can(row, principal)} for row, lst in lists])
    languages = _languages(lists)
    rows = [_row(lst, forms, languages, _can(row, principal)) for row, lst in lists]
    status = query["filter[status]"].split(",") if query.get("filter[status]") else []
    if status:
        rows = [r for r in rows if ("in_use" in status and r["forms_count"] > 0) or ("unused" in status and not r["forms_count"])
                or ("retired" in status and r["retired_count"] > 0)]
    sort = query.get("sort") or "name"
    key = sort.lstrip("-")
    rows.sort(key=lambda r: r[key] if isinstance(r.get(key), int) else str(r.get(key) or "").casefold(),
              reverse=sort.startswith("-"))
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in " ".join([r["name"], r["description"] or "", "" if r.get("large") else
                                                   " ".join(o["label"] for o in r["options"])]).lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    page = rows[params.offset:params.offset + params.page_size]
    # Rows show a few options; a list kept on the server doesn't send them all
    return ok([{**r, "options": r["options"][:20]} if rules.kept_on_server(r) else r for r in page], params.meta(len(rows)))


@router.get("/option-lists/insights", dependencies=[rate_limit("lists-insights", per_minute=60)])
async def option_list_insights(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        lists, forms = await _everything(db, principal)
    languages = _languages(lists)
    rows = [_row(lst, forms, languages, {}) for _, lst in lists]
    return ok({"total": len(rows), "in_use": sum(1 for r in rows if r["forms_count"] > 0),
               "unused": sum(1 for r in rows if not r["forms_count"]), "items": sum(r["items_count"] for r in rows),
               "retired": sum(r["retired_count"] for r in rows),
               "largest": [{"id": r["id"], "name": r["name"], "count": r["items_count"]}
                           for r in sorted(rows, key=lambda r: -r["items_count"])[:8]]})


async def _one(db: Any, principal: Principal, list_id: str) -> tuple[OptionList, dict[str, Any]]:
    row = await service.find_list(db, principal.tenant.id, list_id)
    return row, service.as_list(row, await service.options_of(db, row), await Names().load(db, principal.tenant.id))


@router.get("/option-lists/{list_id}", dependencies=[rate_limit("lists-get", per_minute=120)])
async def get_option_list(list_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        lists, forms = await _everything(db, principal)
    found = next(((r, lst) for r, lst in lists if lst["id"] == list_id), None)
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return ok(_row(found[1], forms, _languages(lists), _can(found[0], principal)))


@router.post("/option-lists", status_code=201, dependencies=[rate_limit("lists-create", per_minute=30)])
async def create_option_list(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = create_body.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        await _name_free(db, principal.tenant.id, data["name"])
        levels, columns = _levels(data.get("levels")), _columns(data.get("columns"))
        _size(len(data["options"]), bool(data.get("large")))
        options = service.clean_options(data["options"], len(levels or [None]), [c["key"] for c in columns or []])
        row = OptionList(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                         name=data["name"], description=data.get("description") or None, levels=levels, columns=columns,
                         large=bool(data.get("large")), created_by=principal.user.id)
        db.add(row)
        await db.flush()
        await service.save_options(db, row, options, principal.user.id)
        await _audit(db, principal, "forms.list_created", row, metadata={"options": str(len(options))})
        return ok(service.as_list(row, options, await Names().load(db, principal.tenant.id)))


@router.patch("/option-lists/{list_id}", dependencies=[rate_limit("lists-update", per_minute=60)])
async def update_option_list(list_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = patch_body.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        row, before = await _one(db, principal, list_id)
        require_resource("lists", "edit", row.created_by, principal, system=bool(row.system_key))
        if data.get("name"):
            await _name_free(db, principal.tenant.id, data["name"], row.id)
        levels = _levels(data["levels"]) if "levels" in data else row.levels
        columns = _columns(data["columns"]) if "columns" in data else row.columns
        options = (service.clean_options(data.get("options") or before["options"], len(levels or [None]),
                                         [c["key"] for c in columns or []])
                   if "options" in data or "levels" in data or "columns" in data else None)
        large = data["large"] if "large" in data else row.large
        _size(len(options if options is not None else before["options"]), large)
        retired_before = sum(1 for o in before["options"] if o.get("active") is False)
        changes = []
        if data.get("name") and data["name"] != row.name:
            changes.append({"field": "name", "before": row.name, "after": data["name"]})
        if "description" in data and (data["description"] or None) != row.description:
            changes.append({"field": "description", "before": row.description, "after": data["description"] or None})
        if options is not None and len(options) != len(before["options"]):
            changes.append({"field": "options", "before": str(len(before["options"])), "after": str(len(options))})
        if options is not None and sum(1 for o in options if o.get("active") is False) != retired_before:
            changes.append({"field": "retired", "before": str(retired_before),
                            "after": str(sum(1 for o in options if o.get("active") is False))})
        if large != row.large:
            changes.append({"field": "large", "before": str(row.large).lower(), "after": str(large).lower()})
        if len(levels or [None]) != len(row.levels or [None]):
            changes.append({"field": "levels", "before": str(len(row.levels or [None])), "after": str(len(levels or [None]))})
        was_kept = rules.kept_on_server(before)
        row.name = data.get("name") or row.name
        if "description" in data:
            row.description = data["description"] or None
        row.levels, row.columns, row.large = levels, columns, large
        row.updated_at, row.updated_by, row.row_version = datetime.now(UTC), principal.user.id, row.row_version + 1
        if options is not None:
            await service.save_options(db, row, options, principal.user.id)
        names = await Names().load(db, principal.tenant.id)
        after = service.as_list(row, options if options is not None else before["options"], names)
        await service.follow_list(db, principal.tenant.id, after, was_kept)
        await _audit(db, principal, "forms.list_updated", row, changes=changes)
        lists, forms = await _everything(db, principal)
        return ok(_row(after, forms, _languages(lists), _can(row, principal)))


@router.delete("/option-lists/{list_id}", dependencies=[rate_limit("lists-delete", per_minute=30)])
async def delete_option_list(list_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """Forms keep their copies of the options; the link just leads nowhere now."""
    async with db_session("write", **_scope(principal)) as db:
        row, lst = await _one(db, principal, list_id)
        require_resource("lists", "delete", row.created_by, principal, system=bool(row.system_key))
        used = service.usage_of(await service.live_forms(db, principal.tenant.id), lst)
        row.deleted_at, row.deleted_by = datetime.now(UTC), principal.user.id
        await _audit(db, principal, "forms.list_deleted", row, metadata={"forms": str(len(used))})
        return ok({"id": str(row.id)})


@router.get("/option-lists/{list_id}/usage", dependencies=[rate_limit("lists-usage", per_minute=120)])
async def option_list_usage(list_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        _, lst = await _one(db, principal, list_id)
        return ok(service.usage_of(await service.live_forms(db, principal.tenant.id), lst))


@router.get("/option-lists/{list_id}/options", dependencies=[rate_limit("lists-lookup", per_minute=600)])
async def lookup_list_options(list_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """One level of a list as people type: kept to what is under `parents`, at most 50 with the total."""
    query = dict(request.query_params)

    def csv(value: str | None) -> list[str] | None:
        return value.split(",")[:500] if value else None
    try:
        level = int(query.get("level") or 0)
    except ValueError:
        level = 0
    async with db_session("read", **_scope(principal)) as db:
        _, lst = await _one(db, principal, list_id)
    options = rules.offered_options(lst, max(0, min(level, rules.MAX_LIST_LEVELS - 1)))
    return ok(rules.lookup_options(options, q=query.get("q") or "", values=csv(query.get("values")),
                                   parents=csv(query.get("parents"))))


@router.post("/option-lists/{list_id}/sync", dependencies=[rate_limit("lists-sync", per_minute=20)])
async def sync_option_list(list_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    raw = await request.body()
    data = sync_body.parse((await request.json()) if raw else {})
    async with db_session("write", **_scope(principal)) as db:
        row, lst = await _one(db, principal, list_id)
        require_resource("lists", "edit", row.created_by, principal, system=bool(row.system_key))
        wanted = set(data["form_ids"]) if "form_ids" in data else None
        fields, touched = 0, []
        for form in await service.live_forms(db, principal.tenant.id):
            if wanted is not None and str(form.id) not in wanted or not form.draft_schema:
                continue
            schema = copy.deepcopy(form.draft_schema)
            changed = service.sync_schema(schema, lst)
            if not changed:
                continue
            fields += changed
            form.draft_schema, form.row_version = schema, form.row_version + 1
            form.updated_at = datetime.now(UTC)
            if form.status == "published":
                form.has_unpublished_changes = True
            touched.append(form)
        if touched:
            await _audit(db, principal, "forms.list_synced", row, metadata={"forms": str(len(touched)), "fields": str(fields)})
        return ok({"forms": len(touched), "fields": fields, "published": sum(1 for f in touched if f.status == "published")})


@router.post("/option-lists/{list_id}/duplicate", status_code=201, dependencies=[rate_limit("lists-create", per_minute=30)])
async def duplicate_option_list(list_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        source, lst = await _one(db, principal, list_id)
        taken = {r.name.lower() for r in await service.lists_of(db, principal.tenant.id)}
        name, n = f"{source.name} (copy)"[:80], 2
        while name.lower() in taken:
            name, n = f"{source.name} (copy {n})"[:80], n + 1
        row = OptionList(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, name=name,
                         description=source.description, levels=source.levels, columns=source.columns,
                         large=source.large, created_by=principal.user.id)
        db.add(row)
        await db.flush()
        await service.save_options(db, row, lst["options"], principal.user.id)
        await _audit(db, principal, "forms.list_created", row,
                     metadata={"options": str(len(lst["options"])), "copy_of": source.name})
        return ok(service.as_list(row, lst["options"], await Names().load(db, principal.tenant.id)))

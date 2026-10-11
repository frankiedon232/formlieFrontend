"""Templates (mock: routes/templates.ts, API-CONTRACT → Templates): the gallery (Formalie's and the workspace's
own), one template with its form, categories, insights, and the workspace's own templates (save a form as a
template, edit, update from its form, duplicate, delete). Formalie's can't be changed: duplicate them instead.
Every change is in the audit trail.
"""

from __future__ import annotations

import copy
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.locales import APP_LOCALE_CODES
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.design.catalogues import TEMPLATE_CATEGORIES
from app.modules.forms.access import viewer_for
from app.modules.forms.router import _natural
from app.modules.forms.service import Names, find_form
from app.modules.forms.service import forms_of as all_forms
from app.modules.rbac.resources import require_resource, resource_actions
from app.modules.templates import catalogue, service
from app.modules.templates.models import WorkspaceTemplate

router = APIRouter(tags=["templates"])

CATEGORY_KEYS = [c["key"] for c in TEMPLATE_CATEGORIES]
create_schema = z.obj(form_id=z.string().min(1), name=z.string().trim().min(1).max(80),
                      description=z.string().trim().max(300).optional(), category=z.enum(CATEGORY_KEYS))
patch_schema = z.obj(name=z.string().trim().min(1).max(80).optional(), description=z.string().trim().max(300).optional(),
                     category=z.enum(CATEGORY_KEYS).optional())
translate_schema = z.obj(schema=z.record(z.string(), z.unknown()), **{"from": z.string().max(10)}, to=z.string().max(10))


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _lang(query: dict[str, str]) -> str:
    return query.get("lang") or "en"


def _filter(query: dict[str, str], key: str) -> list[str] | None:
    raw = query.get(f"filter[{key}]") or query.get(key)
    return [v for v in raw.split(",") if v] if raw else None


def _can(item: dict[str, Any], principal: Principal) -> dict[str, bool]:
    system = item["source"] == "system"
    try:
        by = None if system else uuid.UUID((item.get("created_by") or {}).get("id", ""))
    except ValueError:
        by = None
    return resource_actions("templates", by, principal, system=system)


async def _audit(db: Any, principal: Principal, action: str, item: WorkspaceTemplate,
                 changes: list[dict[str, Any]] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), changes=changes or [],
                 resource={"type": "template", "id": service.ws_key(item), "name": item.name})


async def _name_free(db: Any, tenant_id: Any, name: str, except_id: Any = None) -> None:
    if any(i.id != except_id and i.name.lower() == name.lower() for i in await service.own_templates(db, tenant_id)):
        raise FrmError("FRM-FORM-1012", [{"field": "name", "message": "A template with this name exists."}])


async def _own(db: Any, tenant_id: Any, key: str) -> WorkspaceTemplate:
    """The workspace's own only: Formalie's can't be changed (FRM-FORM-1011)."""
    if not key.startswith("ws_") and catalogue.system_template(key):
        raise FrmError("FRM-FORM-1011")
    item = await service.find_own(db, tenant_id, key)
    if item is None:
        raise FrmError("FRM-GEN-1004")
    return item


def _new_key() -> str:
    return secrets.token_hex(6)


@router.get("/templates", dependencies=[rate_limit("templates-list", per_minute=120)])
async def list_templates(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Search in the person's language; category, source, feature and form filters; sort (most used first)."""
    query = dict(request.query_params)
    category, source, features, from_form = (_filter(query, k) for k in ("category", "source", "features", "form"))
    async with db_session("read", **_scope(principal)) as db:
        items = await service.all_templates(db, principal.tenant.id, _lang(query), await Names().load(db, principal.tenant.id))
    items = [i for i in items if (not category or i["category"] in category)
             and (not from_form or (i["source_form_id"] and i["source_form_id"] in from_form))
             and (not source or i["source"] in source)
             and (not features or all(i["calculations_count"] > 0 if f == "calculations" else i["logic_count"] > 0
                                      if f == "logic" else True for f in features))]
    q = (query.get("q") or "").strip().lower()
    if q:
        items = [i for i in items if q in i["name"].lower() or q in i["description"].lower()
                 or any(q in t for t in i["tags"]) or q.replace(" ", "_") in i["key"]]
    sort = query.get("sort") or "-forms_count"
    items.sort(key=lambda i: _natural(i.get(sort.lstrip("-"))), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    page = items[params.offset:params.offset + params.page_size]
    return ok([{**i, "can": _can(i, principal)} for i in page], params.meta(len(items)))


@router.get("/templates/categories", dependencies=[rate_limit("templates-categories", per_minute=60)])
async def list_template_categories(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Formalie's categories with counts and use of the templates inside."""
    query = dict(request.query_params)
    lang = _lang(query)
    async with db_session("read", **_scope(principal)) as db:
        items = await service.all_templates(db, principal.tenant.id, lang, await Names().load(db, principal.tenant.id))
        logo, primary = await service.branding(db, principal.tenant.id)
    system = [i for i in items if i["source"] == "system"]
    rows = []
    for category in TEMPLATE_CATEGORIES:
        inside = sorted((i for i in system if i["category"] == category["key"]), key=lambda i: -i["forms_count"])
        if not inside:
            continue
        lasts = [i["last_used_at"] for i in inside if i["last_used_at"]]
        rows.append({
            "key": category["key"], "name": catalogue.category_name(lang, category["key"]), "icon": category["icon"],
            "templates_count": len(inside), "calculations_count": sum(1 for i in inside if i["calculations_count"] > 0),
            "logic_count": sum(1 for i in inside if i["logic_count"] > 0),
            "forms_count": sum(i["forms_count"] for i in inside), "responses_count": sum(i["responses_count"] for i in inside),
            "last_used_at": max(lasts) if lasts else None,
            "theme": catalogue.template_theme({"category": category["key"]}, logo, primary),
            "examples": [i["name"] for i in inside[:3]],
        })
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in r["name"].lower() or any(q in e.lower() for e in r["examples"])]
    sort = query.get("sort") or "-forms_count"
    rows.sort(key=lambda r: _natural(r.get(sort.lstrip("-"))), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/templates/insights", dependencies=[rate_limit("templates-insights", per_minute=60)])
async def template_insights(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Forms made from templates over time (from / to, default the last 30 days) and use per category."""
    query = dict(request.query_params)

    def day(value: str | None, fallback: date) -> date:
        try:
            return date.fromisoformat(value) if value and len(value) == 10 else fallback
        except ValueError:
            return fallback
    today = datetime.now(UTC).date()
    end = day(query.get("to"), today)
    start = min(end, day(query.get("from"), end - timedelta(days=29)))
    days = (end - start).days + 1
    daily = [{"date": (start + timedelta(days=i)).isoformat(), "count": 0} for i in range(days)]
    async with db_session("read", **_scope(principal)) as db:
        items = await service.all_templates(db, principal.tenant.id, "en", await Names().load(db, principal.tenant.id))
        forms = [f for f in await all_forms(db, principal.tenant.id) if f.deleted_at is None and f.template_key]
    category_of = {i["key"]: i["category"] for i in items}
    by_category: dict[str, int] = {}
    previous = 0
    for form in forms:
        if form.template_key in category_of:
            by_category[category_of[form.template_key]] = by_category.get(category_of[form.template_key], 0) + 1
        made = form.created_at.astimezone(UTC).date()
        if start <= made <= end:
            daily[(made - start).days]["count"] += 1
        elif start - timedelta(days=days) <= made < start:
            previous += 1
    return ok({
        "period": {"from": daily[0]["date"], "to": daily[-1]["date"], "count": sum(d["count"] for d in daily),
                   "previous": previous},
        "daily": daily, "forms_total": len(forms),
        "system_count": sum(1 for i in items if i["source"] == "system"),
        "workspace_count": sum(1 for i in items if i["source"] == "workspace"),
        "categories": [{"key": k, "forms": v} for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])],
    })


@router.get("/templates/facets", dependencies=[rate_limit("templates-facets", per_minute=60)])
async def template_facets(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        items = await service.all_templates(db, principal.tenant.id, "en", await Names().load(db, principal.tenant.id))
    return ok({"total": len(items), "categories": {k: sum(1 for i in items if i["category"] == k) for k in CATEGORY_KEYS},
               "workspace": sum(1 for i in items if i["source"] == "workspace")})


@router.post("/templates/translate-content", dependencies=[rate_limit("templates-translate", per_minute=30)])
async def translate_form_content(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """A form's template text in another language (text written by people stays)."""
    data = translate_schema.parse(await request.json())

    def known(code: str) -> str | None:
        return code if code == "en" or code in APP_LOCALE_CODES else None
    source, target = known(data["from"]), known(data["to"])
    if not source or not target:
        raise FrmError("FRM-GEN-1002", [{"field": "to", "message": "Unknown language."}])
    result = catalogue.translate_content(data["schema"], catalogue.translation_dict(source), catalogue.translation_dict(target))
    return ok({"schema": result["schema"], "translated": result["translated"], "kept": len(result["kept"])})


@router.get("/templates/{key}", dependencies=[rate_limit("templates-get", per_minute=120)])
async def get_template(key: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        found = await service.detail(db, principal.tenant.id, key, _lang(dict(request.query_params)),
                                     await Names().load(db, principal.tenant.id))
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return ok({**found, "can": _can(found, principal)})


async def _detail_of(db: Any, principal: Principal, item: WorkspaceTemplate) -> dict[str, Any]:
    found = await service.detail(db, principal.tenant.id, service.ws_key(item), "en",
                                 await Names().load(db, principal.tenant.id))
    return {**found, "can": _can(found, principal)}  # type: ignore[dict-item]


@router.post("/templates", status_code=201, dependencies=[rate_limit("templates-create", per_minute=30)])
async def create_template(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """Save a form (its current draft, design included) as a workspace template."""
    data = create_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await find_form(db, viewer, data["form_id"], action="save_template")
        await _name_free(db, principal.tenant.id, data["name"])
        category = catalogue.category_of(data["category"])
        item = WorkspaceTemplate(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                 key_id=_new_key(), name=data["name"], description=data.get("description") or "",
                                 category=data["category"], icon=(category or {}).get("icon") or "i-lucide-layout-template",
                                 schema=copy.deepcopy(form.draft_schema or {}), source_form_id=form.id,
                                 created_by=principal.user.id)
        db.add(item)
        await db.flush()
        await _audit(db, principal, "forms.template_created", item, [{"field": "form", "before": None, "after": form.name}])
        return ok(await _detail_of(db, principal, item))


@router.patch("/templates/{key}", dependencies=[rate_limit("templates-update", per_minute=60)])
async def update_template(key: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = patch_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        item = await _own(db, principal.tenant.id, key)
        require_resource("templates", "edit", item.created_by, principal)
        if data.get("name"):
            await _name_free(db, principal.tenant.id, data["name"], item.id)
        changes = [{"field": f, "before": getattr(item, f), "after": data[f]} for f in ("name", "description", "category")
                   if f in data and data[f] != getattr(item, f)]
        for field in ("name", "description", "category"):
            if field in data:
                setattr(item, field, data[field])
        if "category" in data:
            item.icon = (catalogue.category_of(data["category"]) or {}).get("icon") or item.icon
        item.updated_at, item.updated_by, item.row_version = datetime.now(UTC), principal.user.id, item.row_version + 1
        await _audit(db, principal, "forms.template_updated", item, changes)
        return ok(await _detail_of(db, principal, item))


@router.post("/templates/{key}/sync", dependencies=[rate_limit("templates-update", per_minute=30)])
async def sync_template(key: str, principal: Principal = Depends(require_auth)) -> Any:
    """Update a workspace template from the current draft of the form it was saved from (name, description and
    category stay)."""
    async with db_session("write", **_scope(principal)) as db:
        item = await _own(db, principal.tenant.id, key)
        require_resource("templates", "edit", item.created_by, principal)
        if not item.source_form_id:
            raise FrmError("FRM-GEN-1004")
        viewer = await viewer_for(db, principal)
        form = await find_form(db, viewer, str(item.source_form_id), action="save_template")
        item.schema = copy.deepcopy(form.draft_schema or {})
        item.updated_at, item.updated_by, item.row_version = datetime.now(UTC), principal.user.id, item.row_version + 1
        await _audit(db, principal, "forms.template_updated", item, [{"field": "content", "before": None, "after": form.name}])
        return ok(await _detail_of(db, principal, item))


@router.post("/templates/{key}/duplicate", status_code=201, dependencies=[rate_limit("templates-create", per_minute=30)])
async def duplicate_template(key: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """A workspace copy of any template (Formalie's included)."""
    async with db_session("write", **_scope(principal)) as db:
        source = await service.detail(db, principal.tenant.id, key, _lang(dict(request.query_params)),
                                      await Names().load(db, principal.tenant.id))
        if source is None:
            raise FrmError("FRM-GEN-1004")
        taken = {i.name.lower() for i in await service.own_templates(db, principal.tenant.id)}
        name, n = f"{source['name']} (copy)"[:80], 2
        while name.lower() in taken:
            name, n = f"{source['name']} (copy {n})"[:80], n + 1
        item = WorkspaceTemplate(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                 key_id=_new_key(), name=name, description=source["description"],
                                 category=source["category"], icon=source["icon"], schema=source["schema"],
                                 created_by=principal.user.id)
        db.add(item)
        await db.flush()
        await _audit(db, principal, "forms.template_duplicated", item,
                     [{"field": "template", "before": None, "after": source["name"]}])
        return ok(await _detail_of(db, principal, item))


@router.delete("/templates/{key}", dependencies=[rate_limit("templates-delete", per_minute=30)])
async def delete_template(key: str, principal: Principal = Depends(require_auth)) -> Any:
    """Forms made from it keep their fields and design."""
    async with db_session("write", **_scope(principal)) as db:
        item = await _own(db, principal.tenant.id, key)
        require_resource("templates", "delete", item.created_by, principal)
        item.deleted_at, item.deleted_by = datetime.now(UTC), principal.user.id
        await _audit(db, principal, "forms.template_deleted", item)
    return ok({"deleted": True})

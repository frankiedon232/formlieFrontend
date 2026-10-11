"""Themes, page designs and saved fields (mock: routes/themes.ts, pageDesigns.ts, library.ts).

Themes and page designs come in three kinds (owner 2026-10-03): system (Formalie's, built from presets over the
workspace's brand colour and logo, read-only: duplicate to change), saved (from a form's design) and created
(made in the editor). Forms keep a copy of the tokens and the id they came from, so changing or deleting one never
breaks a form. Both libraries work the same way, so one definition builds both route sets.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
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
from app.modules.design import theme
from app.modules.design.models import PageDesign, SavedField, Theme
from app.modules.forms.models import Form
from app.modules.forms.router import _natural
from app.modules.forms.schema import form_field
from app.modules.forms.service import Names, iso
from app.modules.rbac.resources import require_resource, resource_actions
from app.modules.settings.service import get_section

router = APIRouter(tags=["design"])

SYSTEM_AUTHOR = {"id": "system", "name": "Formalie"}
SYSTEM_DATE = "2026-09-01T09:00:00.000Z"


@dataclass(frozen=True)
class Library:
    path: str  # themes · page-designs
    model: Any
    area: str  # permission area: themes · pages
    tokens: z.Schema
    schema_key: str  # the form schema key that remembers it: theme_id · page_design_id
    resource: str  # theme · page_design
    label: str  # in messages: theme · page design
    actions: tuple[str, str, str]  # created, updated, deleted

    def name_key(self, item_id: str) -> str | None:
        """i18n key of a system item's name, so it shows in the person's language."""
        if self.area == "pages":
            return f"pages.preset.{item_id[9:]}" if item_id.startswith("sys_page_") else None
        if item_id.startswith("sys_preset_"):
            return f"designer.preset.{item_id[11:]}"
        if item_id.startswith("sys_category_"):
            return f"templates.categories.{item_id[13:]}"
        return None


THEMES = Library("themes", Theme, "themes", theme.theme_schema, "theme_id", "theme", "theme",
                 ("forms.theme_created", "forms.theme_updated", "forms.theme_deleted"))
PAGES = Library("page-designs", PageDesign, "pages", theme.page_design_schema, "page_design_id", "page_design",
                "page design", ("forms.page_design_created", "forms.page_design_updated", "forms.page_design_deleted"))


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


async def _branding(db: Any, tenant_id: uuid.UUID) -> tuple[str | None, str | None]:
    branding = await get_section(db, tenant_id, "branding")
    return branding.get("logo_url"), branding.get("brand_color")


async def system_items(db: Any, lib: Library, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    logo, primary = await _branding(db, tenant_id)
    items = theme.system_themes(logo, primary) if lib is THEMES else theme.system_pages(logo, primary)
    return [{**item, "source": "system", "created_by": SYSTEM_AUTHOR, "created_at": SYSTEM_DATE,
             "updated_at": SYSTEM_DATE} for item in items]


async def _usage(db: Any, lib: Library, tenant_id: uuid.UUID) -> tuple[dict[str, int], list[Form]]:
    """How many forms (not in Trash) use each item, and those forms."""
    forms = list((await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.deleted_at.is_(None),
                                                      Form.purged_at.is_(None)))).scalars())
    counts: dict[str, int] = {}
    for form in forms:
        used = (form.draft_schema or {}).get(lib.schema_key)
        if used:
            counts[str(used)] = counts.get(str(used), 0) + 1
    return counts, forms


def _row(lib: Library, item: Any, principal: Principal, names: Names, counts: dict[str, int]) -> dict[str, Any]:
    if isinstance(item, dict):  # Formalie's
        return {**item, "name_key": lib.name_key(item["id"]), "forms_count": counts.get(item["id"], 0),
                "can": resource_actions(lib.area, None, principal, system=True)}
    return {"id": str(item.id), "name": item.name, "tokens": item.tokens, "source": item.source,
            "forms_count": counts.get(str(item.id), 0), "created_by": names.ref(item.created_by),
            "created_at": iso(item.created_at), "updated_at": iso(item.updated_at),
            "can": resource_actions(lib.area, item.created_by, principal)}


async def _own(db: Any, lib: Library, tenant_id: uuid.UUID) -> list[Any]:
    return list((await db.execute(select(lib.model).where(lib.model.tenant_id == tenant_id,
                                                          lib.model.deleted_at.is_(None))
                                  .order_by(lib.model.created_at.desc()))).scalars())


async def _find_own(db: Any, lib: Library, tenant_id: uuid.UUID, item_id: str) -> Any:
    """Workspace items only: Formalie's can't be changed or deleted (FRM-FORM-1014)."""
    if item_id.startswith("sys_"):
        raise FrmError("FRM-FORM-1014")
    try:
        item = await db.get(lib.model, uuid.UUID(item_id))
    except ValueError:
        item = None
    if item is None or item.tenant_id != tenant_id or item.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return item


async def _name_free(db: Any, lib: Library, tenant_id: uuid.UUID, name: str, except_id: Any = None) -> None:
    if any(i.id != except_id and i.name.lower() == name.lower() for i in await _own(db, lib, tenant_id)):
        raise FrmError("FRM-FORM-1010", [{"field": "name", "message": f"A {lib.label} with this name exists."}])


async def _audit(db: Any, lib: Library, principal: Principal, which: int, item: Any,
                 changes: list[dict[str, Any]] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                 action=lib.actions[which], actor=Actor.user(principal.user), changes=changes or [],
                 resource={"type": lib.resource, "id": str(item.id), "name": item.name})


def _register(lib: Library) -> None:
    body = z.obj(name=z.string().trim().min(1).max(80), tokens=lib.tokens, source=z.enum(["saved", "created"]).optional())
    patch = z.obj(name=z.string().trim().min(1).max(80).optional(), tokens=lib.tokens.optional(),
                  source=z.enum(["saved", "created"]).optional())
    duplicate_body = z.obj(name=z.string().trim().min(1).max(80).optional())
    base = f"/{lib.path}"

    async def everything(db: Any, principal: Principal) -> tuple[list[dict[str, Any]], list[Form]]:
        counts, forms = await _usage(db, lib, principal.tenant.id)
        names = await Names().load(db, principal.tenant.id)
        own = [_row(lib, i, principal, names, counts) for i in await _own(db, lib, principal.tenant.id)]
        system = [_row(lib, i, principal, names, counts) for i in await system_items(db, lib, principal.tenant.id)]
        return own + system, forms

    async def list_items(request: Request, principal: Principal = Depends(require_auth)) -> Any:
        """`filter[source]=system,saved,created`, search, sort (newest change first)."""
        query = dict(request.query_params)
        async with db_session("read", **_scope(principal)) as db:
            rows, _ = await everything(db, principal)
        sources = query["filter[source]"].split(",") if query.get("filter[source]") else None
        rows = [r for r in rows if not sources or r["source"] in sources]
        q = (query.get("q") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in r["name"].lower()]
        sort = query.get("sort") or "-updated_at"
        rows.sort(key=lambda r: _natural(r.get(sort.lstrip("-"))), reverse=sort.startswith("-"))
        params = PageParams.from_query(query.get("page"), query.get("page_size"))
        return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))

    async def insights(principal: Principal = Depends(require_auth)) -> Any:
        async with db_session("read", **_scope(principal)) as db:
            rows, forms = await everything(db, principal)
        out: dict[str, Any] = {"by_source": {"system": 0, "saved": 0, "created": 0},
                               "in_use": sum(1 for r in rows if r["forms_count"] > 0), "forms_total": len(forms)}
        for row in rows:
            out["by_source"][row["source"]] += 1
        if lib is THEMES:
            ids = {r["id"] for r in rows}
            out["forms_styled"] = sum(1 for f in forms if (f.draft_schema or {}).get("theme_id") in ids)
            out["top"] = [{"id": r["id"], "name": r["name"], **({"name_key": r["name_key"]} if r.get("name_key") else {}),
                           "forms": r["forms_count"]}
                          for r in sorted((r for r in rows if r["forms_count"] > 0), key=lambda r: -r["forms_count"])[:3]]
        return ok(out)

    async def get_item(item_id: str, principal: Principal = Depends(require_auth)) -> Any:
        async with db_session("read", **_scope(principal)) as db:
            rows, _ = await everything(db, principal)
        row = next((r for r in rows if r["id"] == item_id), None)
        if row is None:
            raise FrmError("FRM-GEN-1004")
        return ok(row)

    async def create_item(request: Request, principal: Principal = Depends(require_auth)) -> Any:
        data = body.parse(await request.json())
        async with db_session("write", **_scope(principal)) as db:
            await _name_free(db, lib, principal.tenant.id, data["name"])
            item = lib.model(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                             name=data["name"], tokens=data["tokens"], source=data.get("source") or "saved",
                             created_by=principal.user.id)
            db.add(item)
            await db.flush()
            await _audit(db, lib, principal, 0, item, [{"field": "source", "before": None, "after": item.source}])
            return ok(_row(lib, item, principal, await Names().load(db, principal.tenant.id), {}))

    async def update_item(item_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
        data = patch.parse(await request.json())
        async with db_session("write", **_scope(principal)) as db:
            item = await _find_own(db, lib, principal.tenant.id, item_id)
            require_resource(lib.area, "edit", item.created_by, principal)
            if data.get("name"):
                await _name_free(db, lib, principal.tenant.id, data["name"], item.id)
            changes = ([{"field": "name", "before": item.name, "after": data["name"]}]
                       if data.get("name") and data["name"] != item.name else []) + (
                [{"field": "design", "before": None, "after": "updated"}] if "tokens" in data else [])
            item.name = data.get("name") or item.name
            if "tokens" in data:
                item.tokens = data["tokens"]
            item.updated_at, item.updated_by, item.row_version = datetime.now(UTC), principal.user.id, item.row_version + 1
            await _audit(db, lib, principal, 1, item, changes)
            counts, _ = await _usage(db, lib, principal.tenant.id)
            return ok(_row(lib, item, principal, await Names().load(db, principal.tenant.id), counts))

    async def duplicate_item(item_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
        """Any item (Formalie's included) → a workspace copy to change."""
        raw = await request.body()
        wanted = duplicate_body.parse((await request.json()) if raw else {}).get("name")
        async with db_session("write", **_scope(principal)) as db:
            rows, _ = await everything(db, principal)
            source = next((r for r in rows if r["id"] == item_id), None)
            if source is None:
                raise FrmError("FRM-GEN-1004")
            taken = {r["name"].lower() for r in rows if r["source"] != "system"}
            name, n = (wanted or f"{source['name']} (copy)")[:80], 2
            while name.lower() in taken:
                name, n = f"{wanted or source['name']} (copy {n})"[:80], n + 1
            item = lib.model(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, name=name,
                             tokens=copy.deepcopy(source["tokens"]),
                             source="created" if source["source"] == "system" else source["source"],
                             created_by=principal.user.id)
            db.add(item)
            await db.flush()
            await _audit(db, lib, principal, 0, item, [{"field": "copied_from", "before": None, "after": source["name"]}])
            return ok(_row(lib, item, principal, await Names().load(db, principal.tenant.id), {}))

    async def delete_item(item_id: str, principal: Principal = Depends(require_auth)) -> Any:
        async with db_session("write", **_scope(principal)) as db:
            item = await _find_own(db, lib, principal.tenant.id, item_id)
            require_resource(lib.area, "delete", item.created_by, principal)
            item.deleted_at, item.deleted_by = datetime.now(UTC), principal.user.id
            await _audit(db, lib, principal, 2, item)
            return ok({"id": str(item.id)})

    limit = rate_limit(f"design-{lib.area}", per_minute=120)
    router.add_api_route(base, list_items, methods=["GET"], dependencies=[limit])
    router.add_api_route(f"{base}/insights", insights, methods=["GET"], dependencies=[limit])
    router.add_api_route(f"{base}/{{item_id}}", get_item, methods=["GET"], dependencies=[limit])
    router.add_api_route(base, create_item, methods=["POST"], status_code=201, dependencies=[limit])
    router.add_api_route(f"{base}/{{item_id}}", update_item, methods=["PATCH"], dependencies=[limit])
    router.add_api_route(f"{base}/{{item_id}}/duplicate", duplicate_item, methods=["POST"], status_code=201,
                         dependencies=[limit])
    router.add_api_route(f"{base}/{{item_id}}", delete_item, methods=["DELETE"], dependencies=[limit])


_register(THEMES)
_register(PAGES)


async def theme_for_new_form(db: Any, tenant_id: uuid.UUID, theme_id: str | None) -> dict[str, Any] | None:
    """A theme's design for a new form (Settings → Form defaults), or None when it no longer exists."""
    if not theme_id:
        return None
    if theme_id.startswith("sys_"):
        found = next((i for i in await system_items(db, THEMES, tenant_id) if i["id"] == theme_id), None)
        return {"id": found["id"], "tokens": copy.deepcopy(found["tokens"])} if found else None
    try:
        item = await db.get(Theme, uuid.UUID(theme_id))
    except ValueError:
        return None
    if item is None or item.tenant_id != tenant_id or item.deleted_at is not None:
        return None
    return {"id": str(item.id), "tokens": copy.deepcopy(item.tokens)}


# ── Saved fields ────────────────────────────────────────────────────────────────

_field_without_id = z.obj({k: v for k, v in form_field.shape.items() if k != "id"})
saved_field_schema = z.obj(name=z.string().trim().min(1).max(80), field=_field_without_id)


def _field_row(item: SavedField, principal: Principal, names: Names) -> dict[str, Any]:
    return {"id": str(item.id), "name": item.name, "field": item.field, "created_by": names.ref(item.created_by),
            "created_at": iso(item.created_at), "can": resource_actions("fields", item.created_by, principal)}


@router.get("/field-library", dependencies=[rate_limit("field-library", per_minute=120)])
async def list_saved_fields(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        items = (await db.execute(select(SavedField).where(SavedField.tenant_id == principal.tenant.id,
                                                           SavedField.deleted_at.is_(None)))).scalars().all()
        names = await Names().load(db, principal.tenant.id)
    return ok([_field_row(i, principal, names) for i in sorted(items, key=lambda i: i.name.casefold())])


@router.post("/field-library", status_code=201, dependencies=[rate_limit("field-library", per_minute=60)])
async def save_field(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = saved_field_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        count = len((await db.execute(select(SavedField.id).where(SavedField.tenant_id == principal.tenant.id,
                                                                  SavedField.deleted_at.is_(None)))).all())
        if count >= 500:
            raise FrmError("FRM-GEN-1002", [{"field": "name", "message": "Library is full."}])
        item = SavedField(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          name=data["name"], field=data["field"], created_by=principal.user.id)
        db.add(item)
        await db.flush()
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="forms.field_saved", actor=Actor.user(principal.user),
                     resource={"type": "saved_field", "id": str(item.id), "name": item.name},
                     metadata={"field_type": data["field"]["type"]})
        return ok(_field_row(item, principal, await Names().load(db, principal.tenant.id)))


@router.delete("/field-library/{field_id}", dependencies=[rate_limit("field-library", per_minute=60)])
async def delete_saved_field(field_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        try:
            item = await db.get(SavedField, uuid.UUID(field_id))
        except ValueError:
            item = None
        if item is None or item.tenant_id != principal.tenant.id or item.deleted_at is not None:
            raise FrmError("FRM-GEN-1004")
        require_resource("fields", "delete", item.created_by, principal)
        item.deleted_at, item.deleted_by = datetime.now(UTC), principal.user.id
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="forms.field_removed", actor=Actor.user(principal.user),
                     resource={"type": "saved_field", "id": str(item.id), "name": item.name})
        return ok({"id": str(item.id)})

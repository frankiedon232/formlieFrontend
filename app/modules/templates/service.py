"""Templates of a workspace (mock: data/templateStore.ts): Formalie's catalogue in the person's language and over the
workspace's branding, plus the workspace's own templates; usage from the forms made with them."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forms.models import Form
from app.modules.forms.overview import preview_labels, schema_stats
from app.modules.forms.schema import all_fields
from app.modules.settings.service import get_section
from app.modules.templates import catalogue
from app.modules.templates.models import WorkspaceTemplate

CATALOGUE_DATE = "2026-10-03T08:00:00.000Z"
SYSTEM_AUTHOR = {"id": "system", "name": "Formalie"}


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def ws_key(item: WorkspaceTemplate) -> str:
    return f"ws_{item.key_id}"


async def branding(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[str | None, str | None]:
    section = await get_section(db, tenant_id, "branding")
    return section.get("logo_url"), section.get("brand_color")


async def own_templates(db: AsyncSession, tenant_id: uuid.UUID) -> list[WorkspaceTemplate]:
    return list((await db.execute(select(WorkspaceTemplate).where(WorkspaceTemplate.tenant_id == tenant_id,
                                                                  WorkspaceTemplate.deleted_at.is_(None))
                                  .order_by(WorkspaceTemplate.created_at.desc()))).scalars())


async def find_own(db: AsyncSession, tenant_id: uuid.UUID, key: str) -> WorkspaceTemplate | None:
    if not key.startswith("ws_"):
        return None
    return (await db.execute(select(WorkspaceTemplate).where(
        WorkspaceTemplate.tenant_id == tenant_id, WorkspaceTemplate.key_id == key[3:],
        WorkspaceTemplate.deleted_at.is_(None)))).scalar_one_or_none()


async def schema_for_template(db: AsyncSession, tenant_id: uuid.UUID, key: str, lang: str = "en") -> dict[str, Any] | None:
    """The form a template makes: a system one in the person's language over the workspace's branding, or a copy of
    the workspace's own (None: no such template)."""
    found = catalogue.system_template(key)
    if found:
        logo, primary = await branding(db, tenant_id)
        return catalogue.system_schema(found, lang, logo, primary)
    own = await find_own(db, tenant_id, key)
    return copy.deepcopy(own.schema) if own else None


async def usage(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, dict[str, Any]]:
    """Forms made from each template (not in Trash): how many, their responses and the last use."""
    out: dict[str, dict[str, Any]] = {}
    forms = (await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.deleted_at.is_(None),
                                                 Form.purged_at.is_(None), Form.template_key.is_not(None)))).scalars()
    for form in forms:
        entry = out.setdefault(form.template_key, {"forms": 0, "responses": 0, "last": None})  # type: ignore[arg-type]
        entry["forms"] += 1
        entry["responses"] += form.responses_count
        created = iso(form.created_at)
        if not entry["last"] or (created and created > entry["last"]):
            entry["last"] = created
    return out


def summary(base: dict[str, Any], schema: dict[str, Any], used: dict[str, Any] | None) -> dict[str, Any]:
    stats = schema_stats(schema)
    return {**base, "pages_count": stats["pages"], "fields_count": stats["fields"], "logic_count": stats["logic"],
            "calculations_count": stats["calculations"], "theme": schema.get("theme") or {},
            "preview": preview_labels(schema), "forms_count": (used or {}).get("forms", 0),
            "responses_count": (used or {}).get("responses", 0), "last_used_at": (used or {}).get("last"),
            "source_form_id": base.get("source_form_id")}


def system_summary(template: dict[str, Any], lang: str, schema: dict[str, Any], used: dict[str, Any] | None) -> dict[str, Any]:
    return summary({
        "key": template["key"], "source": "system", "category": template["category"], "icon": template["icon"],
        "name": catalogue.item_text(lang, template["key"], "name") or template["name"],
        "description": catalogue.item_text(lang, template["key"], "description") or template["description"],
        "tags": template["tags"], "minutes": template["minutes"], "created_by": SYSTEM_AUTHOR,
        "updated_at": CATALOGUE_DATE, "source_form_id": None}, schema, used)


def own_summary(item: WorkspaceTemplate, names: Any, used: dict[str, Any] | None) -> dict[str, Any]:
    return summary({
        "key": ws_key(item), "source": "workspace", "category": item.category, "icon": item.icon, "name": item.name,
        "description": item.description, "tags": [], "minutes": max(1, round(schema_stats(item.schema)["fields"] / 3)),
        "created_by": names.ref(item.created_by), "updated_at": iso(item.updated_at),
        "source_form_id": str(item.source_form_id) if item.source_form_id else None}, item.schema, used)


async def all_templates(db: AsyncSession, tenant_id: uuid.UUID, lang: str, names: Any) -> list[dict[str, Any]]:
    """The workspace's own first, then Formalie's catalogue."""
    used = await usage(db, tenant_id)
    logo, primary = await branding(db, tenant_id)
    own = [own_summary(item, names, used.get(ws_key(item))) for item in await own_templates(db, tenant_id)]
    system = [system_summary(t, lang, catalogue.system_schema(t, lang, logo, primary), used.get(t["key"]))
              for t in catalogue.system_templates()]
    return own + system


async def detail(db: AsyncSession, tenant_id: uuid.UUID, key: str, lang: str, names: Any) -> dict[str, Any] | None:
    """One template with its form and calculations."""
    used = await usage(db, tenant_id)
    found = catalogue.system_template(key)
    if found:
        logo, primary = await branding(db, tenant_id)
        schema = catalogue.system_schema(found, lang, logo, primary)
        base = system_summary(found, lang, schema, used.get(key))
    else:
        own = await find_own(db, tenant_id, key)
        if own is None:
            return None
        schema = copy.deepcopy(own.schema)
        base = own_summary(own, names, used.get(key))
    calculations = [{"label": f.get("label", ""), "formula": str((f.get("props") or {}).get("formula") or ""),
                     "internal": bool((f.get("props") or {}).get("internal"))}
                    for f in all_fields(schema) if f["type"] == "calculated"]
    return {**base, "schema": schema, "calculations": calculations}

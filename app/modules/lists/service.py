"""Option lists of a workspace (mock: routes/optionLists.ts, data/largeLists.ts): reading a list with its options,
saving them, where a list is used, and keeping forms in step with it.

Lists kept on the server (large, or above 20 active options) are not copied into forms: a field filled from one
keeps the list's id, its level and `options_large` (how many, and which choices above have options under them),
with no options; the server reads them from the list when it needs them (lookups as people type, submission
checks). Smaller lists are copied into the field, and "Update forms" copies them again (sync).
"""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FrmError
from app.modules.forms.models import Form
from app.modules.forms.schema import all_fields
from app.modules.lists import rules
from app.modules.lists.models import OptionItem, OptionList


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def _option(item: OptionItem) -> dict[str, Any]:
    out: dict[str, Any] = {"value": item.value, "label": item.label}
    if item.score is not None:
        out["score"] = int(item.score) if float(item.score).is_integer() else item.score
    if not item.active:
        out["active"] = False
    if item.translations:
        out["translations"] = item.translations
    if item.level:
        out["level"], out["parent"] = item.level, item.parent_value
    if item.attrs:
        out["attrs"] = item.attrs
    return out


async def options_of(db: AsyncSession, row: OptionList) -> list[dict[str, Any]]:
    items = (await db.execute(select(OptionItem).where(OptionItem.tenant_id == row.tenant_id,
                                                       OptionItem.list_id == row.id, OptionItem.deleted_at.is_(None))
                              .order_by(OptionItem.sort_order, OptionItem.id))).scalars()
    return [_option(i) for i in items]


def as_list(row: OptionList, options: list[dict[str, Any]], names: Any) -> dict[str, Any]:
    """OptionList (shared/types/forms.ts)."""
    out: dict[str, Any] = {"id": str(row.id), "name": row.name, "description": row.description}
    if row.levels:
        out["levels"] = row.levels
    if row.columns:
        out["columns"] = row.columns
    if row.large:
        out["large"] = True
    out.update({"options": options,
                "created_by": {"id": "system", "name": "Formalie"} if row.system_key else names.ref(row.created_by),
                "created_at": iso(row.created_at), "updated_at": iso(row.updated_at)})
    return out


async def lists_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[OptionList]:
    return list((await db.execute(select(OptionList).where(OptionList.tenant_id == tenant_id,
                                                           OptionList.deleted_at.is_(None)))).scalars())


async def find_list(db: AsyncSession, tenant_id: uuid.UUID, list_id: str) -> OptionList:
    try:
        row = await db.get(OptionList, uuid.UUID(list_id))
    except ValueError:
        row = None
    if row is None or row.tenant_id != tenant_id or row.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return row


def clean_options(options: list[dict[str, Any]], levels: int, columns: list[str]) -> list[dict[str, Any]]:
    """Values differ within a list (FRM-FORM-1020); below the top, every option sits under one on the level above
    (FRM-FORM-1021); translations without empty ones; details only for the list's columns."""
    seen: set[str] = set()
    by_level: dict[int, set[str]] = {}
    for option in options:
        key = option["value"].lower()
        if key in seen:
            raise FrmError("FRM-FORM-1020", [{"field": "options", "message": option["value"]}])
        seen.add(key)
        at = min(option.get("level") or 0, levels - 1)
        by_level.setdefault(at, set()).add(option["value"])
    out = []
    for option in options:
        at = min(option.get("level") or 0, levels - 1) if levels > 1 else 0
        if at > 0 and (not option.get("parent") or option["parent"] not in by_level.get(at - 1, set())):
            raise FrmError("FRM-FORM-1021", [{"field": "options", "message": option["label"]}])
        translations = {k: v for k, v in (option.get("translations") or {}).items() if v.strip()}
        attrs = {k: v for k, v in (option.get("attrs") or {}).items() if k in columns and v != "" and v is not None}
        item: dict[str, Any] = {"value": option["value"], "label": option["label"]}
        if option.get("score") is not None:
            item["score"] = option["score"]
        if option.get("active") is False:
            item["active"] = False
        if translations:
            item["translations"] = translations
        if at > 0:
            item["level"], item["parent"] = at, option["parent"]
        if attrs:
            item["attrs"] = attrs
        out.append(item)
    return out


async def save_options(db: AsyncSession, row: OptionList, options: list[dict[str, Any]], by: uuid.UUID) -> None:
    """The list's options become exactly these, matched by value (left-out ones keep their row, deleted)."""
    existing = {i.value.lower(): i for i in (await db.execute(select(OptionItem).where(
        OptionItem.tenant_id == row.tenant_id, OptionItem.list_id == row.id,
        OptionItem.deleted_at.is_(None)))).scalars()}
    now = datetime.now(UTC)
    wanted = set()
    for order, option in enumerate(options):
        key = option["value"].lower()
        wanted.add(key)
        fields = {"value": option["value"], "label": option["label"], "score": option.get("score"),
                  "active": option.get("active") is not False, "translations": option.get("translations"),
                  "level": option.get("level") or 0, "parent_value": option.get("parent"),
                  "attrs": option.get("attrs"), "sort_order": order}
        item = existing.get(key)
        if item is None:
            db.add(OptionItem(tenant_id=row.tenant_id, organisation_id=row.organisation_id, list_id=row.id,
                              created_by=by, **fields))
        else:
            for name, value in fields.items():
                if getattr(item, name) != value:
                    setattr(item, name, value)
    for key, item in existing.items():
        if key not in wanted:
            item.deleted_at, item.deleted_by = now, by
    row.active_count = sum(1 for o in options if o.get("active") is not False)
    await db.flush()


# ── Forms that use a list ───────────────────────────────────────────────────────

async def live_forms(db: AsyncSession, tenant_id: uuid.UUID) -> list[Form]:
    return list((await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.deleted_at.is_(None),
                                                     Form.purged_at.is_(None)))).scalars())


def usage_of(forms: list[Form], lst: dict[str, Any]) -> list[dict[str, Any]]:
    """Forms and fields using the list, and whether they still match it (lists kept on the server always do)."""
    kept = rules.kept_on_server(lst)
    out = []
    for form in forms:
        fields = [f for f in all_fields(form.draft_schema) if f.get("option_set_id") == lst["id"]]
        if fields:
            out.append({"form": {"id": str(form.id), "name": form.name, "status": form.status}, "fields": [
                {"id": f["id"], "key": f["key"], "label": (f.get("label") or "").strip() or f["key"],
                 "in_sync": True if kept else rules.matches_list(f.get("options"), lst, f.get("option_level") or 0)}
                for f in fields]})
    return out


def fill_large_lists(schema: dict[str, Any] | None, lists: dict[str, dict[str, Any]], only: str | None = None) -> int:
    """Fields filled from lists kept on the server carry no options, only `options_large` (and become a dropdown or
    multi-select when they were something else); fields whose list is no longer kept there get a copy again.
    → how many fields changed."""
    if not schema:
        return 0
    changed = 0
    for field in all_fields(schema):
        list_id = field.get("option_set_id")
        if not list_id or (only and list_id != only):
            continue
        lst = lists.get(list_id)
        if lst and rules.kept_on_server(lst):
            options = rules.offered_options(lst, field.get("option_level") or 0)
            large: dict[str, Any] = {"total": len(options)}
            if field.get("option_parent"):
                large["parents"] = list(dict.fromkeys(o["parent"] for o in options if "parent" in o))
            if field.get("options") != [] or field.get("options_large") != large:
                field["options"], field["options_large"] = [], large
                changed += 1
            if field["type"] not in rules.LARGE_LIST_TYPES:
                field["type"] = "multi_select" if field["type"] == "checkbox" else "dropdown"
        elif field.get("options_large"):
            if lst:
                field["options"] = rules.offered_options(lst, field.get("option_level") or 0)
            del field["options_large"]
            changed += 1
    return changed


def sync_schema(schema: dict[str, Any], lst: dict[str, Any]) -> int:
    """Copies the list into a draft: options of every linked field, and label translations for the languages the
    form offers. → how many fields changed."""
    languages = [c for c in rules.form_languages(schema) if c != rules.main_language(schema)]
    changed = 0
    for field in all_fields(schema):
        if field.get("option_set_id") != lst["id"]:
            continue
        level = field.get("option_level") or 0
        if not rules.matches_list(field.get("options"), lst, level):
            changed += 1
        field["options"] = rules.offered_options(lst, level)
        for language in languages:
            for option in lst["options"]:
                text = (option.get("translations") or {}).get(language)
                if option.get("active") is False or (option.get("level") or 0) != level or not text:
                    continue
                key = f"field.{field['id']}.option.{option['value']}"
                schema.setdefault("translations", {}).setdefault(language, {})[key] = text
                schema.setdefault("translated_from", {}).setdefault(language, {})[key] = rules.text_hash(option["label"])
    return changed


async def follow_list(db: AsyncSession, tenant_id: uuid.UUID, lst: dict[str, Any], was_kept: bool) -> int:
    """After a list is saved: forms using a list kept on the server follow it at once (live versions are
    snapshots and keep theirs); a list no longer kept there gives its fields a copy again."""
    if not (rules.kept_on_server(lst) or was_kept):
        return 0
    touched = 0
    for form in await live_forms(db, tenant_id):
        schema = copy.deepcopy(form.draft_schema) if form.draft_schema else None
        if not schema:
            continue
        changed = (sync_schema(schema, lst) if rules.kept_on_server(lst) else 0) + fill_large_lists(schema, {lst["id"]: lst}, lst["id"])
        if changed:
            form.draft_schema = schema
            touched += 1
    return touched


async def lists_by_id(db: AsyncSession, tenant_id: uuid.UUID, ids: set[str]) -> dict[str, dict[str, Any]]:
    """The lists a schema refers to, with their options (for fill_large_lists)."""
    out: dict[str, dict[str, Any]] = {}
    for list_id in ids:
        try:
            row = await db.get(OptionList, uuid.UUID(list_id))
        except ValueError:
            continue
        if row is not None and row.tenant_id == tenant_id and row.deleted_at is None:
            out[list_id] = {"id": list_id, "large": row.large, "levels": row.levels, "columns": row.columns,
                            "options": await options_of(db, row)}
    return out


async def fill_schema(db: AsyncSession, tenant_id: uuid.UUID, schema: dict[str, Any] | None) -> None:
    """A form schema as it is saved (draft save, create, import): fields from lists kept on the server carry none
    of their options."""
    if not schema:
        return
    ids = {str(f["option_set_id"]) for f in all_fields(schema) if f.get("option_set_id")}
    if ids:
        fill_large_lists(schema, await lists_by_id(db, tenant_id, ids))



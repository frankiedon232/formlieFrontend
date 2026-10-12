"""AI assistant, creating (mock: routes/aiCreate.ts; API-CONTRACT → AI assistant). Drafts are proposals: they are kept
with the request until a person applies (creates the form, template or design) or discards them.

    POST /ai/forms/draft          { prompt, document?, pages?, variant?, replaces? } → AiFormDraft (ai.create)
    POST /ai/templates/draft      { prompt, variant?, replaces? } → AiTemplateDraft (ai.create)
    POST /ai/themes/draft         { colour, mood?, replaces? } → AiThemeDraft (ai.create)
    POST /ai/requests/{id}/apply  form { name, folder_id? } (forms.create) · template { name, description, category }
                                  (forms.save_template) · theme { name, key } (themes.create) · translate
                                  { translations } · rewrite { texts } (into the saved draft) · builder, translate or
                                  rewrite { count } (the builder applied them) → AiApplyResult; audited ai.applied
    POST /ai/requests/{id}/discard yours, while it waits for review
"""

from __future__ import annotations

import copy
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import null

from app.core import js
from app.core import zod as z
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.locales import APP_LOCALE_CODES
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.ai import checks as C
from app.modules.ai import engine_forms as F
from app.modules.ai import engine_themes as TH
from app.modules.ai import prompts as P
from app.modules.ai import service as A
from app.modules.ai.assistant import produce
from app.modules.ai.kinds import credits_of
from app.modules.ai.kit import build_schema, form_texts, main_language, mask_text, schema_stats, text_hash, walk_texts
from app.modules.ai.models import AiRequest
from app.modules.ai.provider import ModelTask
from app.modules.ai.router import scope
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth

router = APIRouter(tags=["ai"])
CATEGORY_KEYS = list(P.CATEGORY_KEYS)


def reference(value: Any) -> uuid.UUID | None:
    """An id that came in as a reference (anything else matches nothing)."""
    ctx = get_context()
    if not isinstance(value, str) or ctx is None or value.lower() not in {i.lower() for i in ctx.ref_ids}:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def _branding(db: Any, tenant_id: uuid.UUID) -> tuple[str | None, str | None]:
    from app.modules.templates.service import branding

    return await branding(db, tenant_id)


async def workspace_look(db: Any, tenant_id: uuid.UUID) -> dict[str, Any]:
    """The look a new form gets in this workspace (its default theme, else the default with its brand colour)."""
    from app.modules.design.router import theme_for_new_form
    from app.modules.design.theme import default_theme
    from app.modules.settings.service import get_section

    defaults = await get_section(db, tenant_id, "form_defaults")
    chosen = await theme_for_new_form(db, tenant_id, defaults.get("theme_id"))
    if chosen:
        return chosen["tokens"]
    logo, primary = await _branding(db, tenant_id)
    return default_theme(logo, primary)


def _summary_of(stats: dict[str, int]) -> str:
    pages = f"{stats['pages']}-page " if stats["pages"] > 1 else ""
    logic = f", {stats['logic']} rule{'' if stats['logic'] == 1 else 's'}" if stats["logic"] else ""
    calcs = (f" and {stats['calculations']} calculation{'' if stats['calculations'] == 1 else 's'}"
             if stats["calculations"] else "")
    return f"A {pages}draft with {stats['fields']} question{'' if stats['fields'] == 1 else 's'}{logic}{calcs}."


form_input = z.obj(
    prompt=z.string().trim().min(3).max(2000),
    document=z.string().max(20_000).nullable().optional(),
    pages=z.enum(["auto", "one", "several"]).optional(),
    variant=z.number().int().min(0).max(20).optional(),
    replaces=z.string().nullable().optional(),
)
template_input = z.obj(
    prompt=z.string().trim().min(3).max(2000),
    variant=z.number().int().min(0).max(20).optional(),
    replaces=z.string().nullable().optional(),
)


async def _draft(prompt: str, document: str | None, pages: str, variant: int, *, template: bool,
                 mask: bool) -> tuple[dict[str, Any], A.Made]:
    """Personal data is masked before anything reaches the model when the workspace asks for it."""
    def hide(text: str | None) -> str | None:
        return mask_text(text) if mask and text else text

    def standin() -> dict[str, Any]:
        return F.draft_form(prompt, document, pages, variant)

    task = ModelTask(
        task="template_draft" if template else "form_draft", system=P.form_system(), schema=P.FORM_DRAFT,
        content=P.content({"kind": "template" if template else "form", "prompt": hide(prompt), "document": hide(document),
                           "pages": pages, "variant": variant}),
        standin=standin, max_tokens=24_000)
    return await produce(task, lambda data: C.form_from_model(data, prompt=prompt, document=document, pages=pages,
                                                              template=template))


@router.post("/ai/forms/draft", dependencies=[rate_limit("ai-create", per_minute=20)])
async def draft_form_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "form")
        values = form_input.parse(await request.json())
        look = await workspace_look(db, principal.tenant.id)
    prompt, document = values["prompt"], values.get("document")
    result, made = await _draft(prompt, document, values.get("pages") or "auto", values.get("variant") or 0, template=False,
                                mask=settings["mask_personal"])
    schema = {**result["schema"], "theme": look}
    stats = schema_stats(schema)
    shown = mask_text(prompt) if settings["mask_personal"] else prompt
    if document:
        shown = f"{shown}\n\n({len([line for line in document.splitlines() if line])} lines of a document)"
    async with db_session("write", **scope(principal)) as db:
        await A.replace(db, principal, reference(values.get("replaces")))
        saved = await A.record_request(
            db, principal, settings, kind="form", status="proposed", title=result["name"], credits=credits_of("form"),
            prompt=shown, result=_summary_of(stats), read=[], made=made, notes=result["notes"], stats=stats,
            output={"name": result["name"], "description": result["description"], "schema": schema})
        return ok({"request_id": str(saved.id), "name": result["name"], "description": result["description"],
                   "schema": schema, "notes": result["notes"], "based_on": result["based_on"], "source": result["source"],
                   "stats": stats, "credits": saved.credits})


@router.post("/ai/templates/draft", dependencies=[rate_limit("ai-create", per_minute=20)])
async def draft_template_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.templates.catalogue import template_theme

    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "template")
        values = template_input.parse(await request.json())
        logo, primary = await _branding(db, principal.tenant.id)
    prompt = values["prompt"]
    result, made = await _draft(prompt, None, "auto", values.get("variant") or 0, template=True,
                                mask=settings["mask_personal"])
    # The category decides the design (the template gallery's look for that kind)
    ranked = F.rank_templates(prompt)
    category = result.get("category") if made.engine == "model" and result.get("category") else \
        (ranked[0]["template"]["category"] if ranked else "business")
    schema = {**result["schema"], "theme": template_theme({"category": category, "design": result["design"]}, logo, primary)}
    stats = schema_stats(schema)
    async with db_session("write", **scope(principal)) as db:
        await A.replace(db, principal, reference(values.get("replaces")))
        saved = await A.record_request(
            db, principal, settings, kind="template", status="proposed", title=result["name"],
            credits=credits_of("template"), prompt=mask_text(prompt) if settings["mask_personal"] else prompt,
            result=_summary_of(stats), read=[], made=made, notes=result["notes"], stats=stats,
            output={"name": result["name"], "description": result["description"], "category": category, "schema": schema})
        return ok({"request_id": str(saved.id), "name": result["name"], "description": result["description"],
                   "category": category, "schema": schema, "notes": result["notes"], "based_on": result["based_on"],
                   "source": result["source"], "stats": stats, "credits": saved.credits})


theme_input = z.obj(
    colour=z.string().regex(r"^#[0-9a-fA-F]{6}$"),
    mood=z.string().trim().max(200).optional(),
    replaces=z.string().nullable().optional(),
)

# A short sample form to show designs on (the mock's SAMPLE)
SAMPLE = {"pages": [{"title": "About you", "rows": [
    {"fields": [{"type": "full_name", "label": "Full name", "required": True}]},
    {"fields": [{"type": "email", "label": "Email address", "required": True}, {"type": "phone", "label": "Phone number"}]},
    {"fields": [{"type": "section", "label": "Your visit"}]},
    {"fields": [{"type": "rating", "label": "How was your visit?"}]},
    {"fields": [{"type": "long_text", "label": "Anything we could do better?"}]},
]}]}


@router.post("/ai/themes/draft", dependencies=[rate_limit("ai-create", per_minute=20)])
async def draft_theme_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "theme")
        values = theme_input.parse(await request.json())
        logo, _ = await _branding(db, principal.tenant.id)
    colour, mood = values["colour"], values.get("mood") or ""
    brand = TH.brand_of(colour)
    task = ModelTask(task="theme_draft", system=P.theme_system(), schema=P.THEME_DRAFT, fast=True,
                     content=P.content({"colour": brand, "readable": TH.readable(brand), "mood": mood,
                                        "default_theme": TH.base_theme(colour, logo)}),
                     standin=lambda: TH.themes_from_colour(colour, mood, logo))
    suggestions, made = await produce(task, lambda data: C.themes_from_model(data, colour=colour, mood=mood, logo_url=logo))
    upper = colour.upper()
    async with db_session("write", **scope(principal)) as db:
        await A.replace(db, principal, reference(values.get("replaces")))
        saved = await A.record_request(
            db, principal, settings, kind="theme", status="proposed", title=f"Designs from {upper}",
            title_key={"code": "theme", "params": {"colour": upper}}, credits=credits_of("theme"),
            prompt=f"Brand colour {upper}{f', {mood}' if mood else ''}",
            result=f"{len(suggestions)} designs: {', '.join(s['name'] for s in suggestions)}. "
                   "Buttons keep a shade of the colour that white text reads well on.",
            read=[], made=made, notes=[{"code": "themes", "params": {"n": len(suggestions)}}],
            output={"suggestions": suggestions})
        return ok({"request_id": str(saved.id), "colour": colour.lower(), "suggestions": suggestions,
                   "sample": build_schema(SAMPLE), "credits": saved.credits})


# ── Apply or discard ──────────────────────────────────────────────────────────

async def _waiting(db: Any, principal: Principal, request_id: str) -> AiRequest:
    try:
        wanted = uuid.UUID(request_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    found = await db.get(AiRequest, wanted)
    if found is None or found.tenant_id != principal.tenant.id or found.by_id != principal.user.id \
            or found.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    if found.status != "proposed" or not found.output:
        raise FrmError("FRM-AI-1004")
    return found


apply_form = z.obj(name=z.string().trim().min(1).max(120), folder_id=z.string().nullable().optional())
apply_template = z.obj(name=z.string().trim().min(1).max(80), description=z.string().trim().max(300).optional(),
                       category=z.enum(CATEGORY_KEYS))
apply_theme = z.obj(name=z.string().trim().min(1).max(60), key=z.string().min(1))
apply_translations = z.obj(translations=z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(50_000))))
apply_texts = z.obj(texts=z.record(z.string().max(200), z.string().trim().min(1).max(50_000)))
apply_count = z.obj(count=z.number().int().min(1).max(500))


async def _apply_form(db: Any, principal: Principal, found: AiRequest, body: Any) -> dict[str, Any]:
    from app.modules.forms import service as forms
    from app.modules.forms.access import viewer_for

    if not principal.can("forms.create"):
        raise FrmError("FRM-PERM-1001")
    values = apply_form.parse(body)
    viewer = await viewer_for(db, principal)
    folder = forms.visible_folder(viewer, values.get("folder_id"))
    form = await forms.new_form(db, viewer, name=values["name"], folder=folder,
                                schema=copy.deepcopy(found.output["schema"]))  # type: ignore[index]
    await forms.with_form_defaults(db, form)
    await forms.audit(db, viewer, "forms.created", form, metadata={"source": "ai"})
    return {"type": "form", "id": str(form.id), "name": form.name}


async def _apply_template(db: Any, principal: Principal, found: AiRequest, body: Any) -> dict[str, Any]:
    from app.modules.templates import catalogue
    from app.modules.templates.models import WorkspaceTemplate
    from app.modules.templates.router import _audit, _name_free
    from app.modules.templates.service import ws_key

    if not principal.can("forms.save_template"):
        raise FrmError("FRM-PERM-1001")
    values = apply_template.parse(body)
    await _name_free(db, principal.tenant.id, values["name"])
    category = catalogue.category_of(values["category"])
    item = WorkspaceTemplate(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                             key_id=secrets.token_hex(6), name=values["name"], description=values.get("description") or "",
                             category=values["category"], icon=(category or {}).get("icon") or "i-lucide-layout-template",
                             schema=copy.deepcopy(found.output["schema"]),  # type: ignore[index]
                             created_by=principal.user.id)
    db.add(item)
    await db.flush()
    await _audit(db, principal, "forms.template_created", item, [{"field": "source", "before": None, "after": "AI assistant"}])
    return {"type": "template", "id": ws_key(item), "name": item.name}


async def _apply_theme(db: Any, principal: Principal, found: AiRequest, body: Any) -> dict[str, Any]:
    from app.modules.design.models import Theme
    from app.modules.design.router import THEMES, _audit, _name_free

    if not principal.can("themes.create"):
        raise FrmError("FRM-PERM-1001")
    values = apply_theme.parse(body)
    suggestion = next((s for s in found.output.get("suggestions") or [] if s.get("key") == values["key"]), None)  # type: ignore[union-attr]
    if suggestion is None:
        raise FrmError("FRM-GEN-1002", [{"field": "key", "message": "Choose one of the designs."}])
    await _name_free(db, THEMES, principal.tenant.id, values["name"])
    item = Theme(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, name=values["name"],
                 tokens=copy.deepcopy(suggestion["tokens"]), source="created", created_by=principal.user.id)
    db.add(item)
    await db.flush()
    await _audit(db, THEMES, principal, 0, item, [{"field": "source", "before": None, "after": item.source}])
    return {"type": "theme", "id": str(item.id), "name": item.name}


async def _apply_texts(db: Any, principal: Principal, found: AiRequest, body: Any) -> dict[str, Any]:
    """From the AI pages: into the saved draft, unless the form changed since the assistant read it."""
    from app.modules.forms import service as forms
    from app.modules.forms.access import viewer_for
    from app.modules.forms.models import Form
    from app.modules.forms.schema import blank_schema

    output = found.output or {}
    form = await db.get(Form, uuid.UUID(output["form_id"]))
    if form is None or form.tenant_id != principal.tenant.id or form.deleted_at is not None or form.purged_at is not None:
        raise FrmError("FRM-GEN-1004")
    viewer = await viewer_for(db, principal)
    from app.modules.forms.access import require_action

    require_action(form, viewer, "edit")
    if form.row_version != output.get("row_version"):
        raise FrmError("FRM-GEN-1009")
    schema = copy.deepcopy(form.draft_schema) if form.draft_schema else blank_schema()
    settings = schema.get("settings") or {}
    original = {t["key"]: t["text"] for t in form_texts({**schema, "settings": {**settings, "title": settings.get("title") or form.name}})}
    changed = 0
    if found.kind == "translate":
        values = apply_translations.parse(body)
        main = main_language(schema)
        for code, texts in values["translations"].items():
            if code == main or code not in APP_LOCALE_CODES:
                continue
            kept = {key: text for key, text in texts.items() if key in original and js.trim(text)}
            schema["translations"] = {**(schema.get("translations") or {}),
                                      code: {**((schema.get("translations") or {}).get(code) or {}), **kept}}
            schema["translated_from"] = {**(schema.get("translated_from") or {}),
                                         code: {**((schema.get("translated_from") or {}).get(code) or {}),
                                                **{key: text_hash(original[key]) for key in kept}}}
            settings = schema.get("settings") or {}
            schema["settings"] = {**settings, "languages": list(dict.fromkeys([*(settings.get("languages") or []), code]))}
            changed += len(kept)
    else:
        values = apply_texts.parse(body)

        def visit(key: str, text: str, kind: str, page: str | None) -> str:
            nonlocal changed
            if key == "form.title" or key not in values["texts"]:
                return text
            changed += 1
            return values["texts"][key]
        walk_texts(schema, visit)
    from app.modules.forms.schema import form_schema_v1

    good, _ = form_schema_v1.safe_parse(schema)
    if not good:
        raise FrmError("FRM-GEN-1002", [{"field": "translations" if found.kind == "translate" else "texts",
                                         "message": "These texts don't fit the form."}])
    form.draft_schema = schema
    form.has_unpublished_changes = form.status != "draft"
    forms.touch(form, viewer)
    await forms.audit(db, viewer, "forms.updated", form, metadata={
        "change": "translated_with_ai" if found.kind == "translate" else "rewritten_with_ai", "texts": str(changed)})
    found.notes = [{"code": "assist_applied", "params": {"n": changed, "total": changed}}]
    return {"type": "form", "id": str(form.id), "name": form.name}


@router.post("/ai/requests/{request_id}/apply", status_code=201, dependencies=[rate_limit("ai-apply", per_minute=60)])
async def apply_ai_request(request_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    raw = await request.body()
    body = (await request.json()) if raw else {}
    async with db_session("write", **scope(principal)) as db:
        found = await _waiting(db, principal, request_id)
        if found.kind == "form":
            target = await _apply_form(db, principal, found, body)
        elif found.kind == "template":
            target = await _apply_template(db, principal, found, body)
        elif found.kind == "theme":
            target = await _apply_theme(db, principal, found, body)
        elif found.kind in ("translate", "rewrite") and isinstance(body, dict) and "count" not in body:
            target = await _apply_texts(db, principal, found, body)
        elif found.kind in ("builder", "translate", "rewrite"):
            values = apply_count.parse(body)
            if not found.target:
                raise FrmError("FRM-AI-1004")
            total = (found.output or {}).get("count") or values["count"]
            found.result = f"{values['count']} of {total} suggestions applied."
            found.notes = [{"code": "assist_applied", "params": {"n": values["count"], "total": total}}]
            target = dict(found.target)
        else:
            raise FrmError("FRM-AI-1004")
        found.status, found.applied_at, found.target, found.output = "applied", datetime.now(UTC), target, null()
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="ai.applied", actor=Actor.user(principal.user), resource=dict(target),
                     metadata={"kind": found.kind, "request": found.title})
        return ok({"target": target})


@router.post("/ai/requests/{request_id}/discard", dependencies=[rate_limit("ai-apply", per_minute=60)])
async def discard_ai_request(request_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        found = await _waiting(db, principal, request_id)
        found.status, found.output = "discarded", null()
        return ok({"discarded": True})

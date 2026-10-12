"""AI assistant in the builder and for a form's texts (mock: routes/aiAssist.ts, routes/aiWrite.ts). Each reads the
form (the builder's current draft when it sends one, else the saved draft) and proposes; nothing changes until the
person applies, in the builder or with POST /ai/requests/{id}/apply.

    POST /ai/forms/{id}/assist     { action (fields · help · logic · check), schema } → AiAssistResult (ai.assist)
    POST /ai/forms/{id}/translate  { languages [codes], schema? } → AiTranslation (ai.translate; 4 credits a language)
    POST /ai/forms/{id}/rewrite    { tone (plain · friendly · formal), schema? } → AiRewrite (ai.translate)

Translating: Formalie's own dictionaries first, the model for what they don't know (rich text included, its markup
kept tag for tag); a current translation someone made is kept.
"""

from __future__ import annotations

import copy
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.locales import APP_LOCALE_CODES
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.ai import checks as C
from app.modules.ai import prompts as P
from app.modules.ai import service as A
from app.modules.ai.assistant import produce, produce_all
from app.modules.ai.engine_builder import assist_form
from app.modules.ai.engine_writing import reading_age, rewrite, translator_for
from app.modules.ai.kinds import AI_ASSIST_ACTIONS, AI_TONES, credits_of
from app.modules.ai.kit import form_texts, main_language, stale_keys, with_title
from app.modules.ai.provider import ModelTask
from app.modules.ai.router import scope
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms.schema import form_schema_v1

router = APIRouter(tags=["ai"])
TITLES = {"fields": "Suggest fields", "help": "Write help texts", "logic": "Add logic", "check": "Check my form"}


async def _editable(db: Any, principal: Principal, form_id: str) -> Any:
    from app.modules.forms.access import viewer_for
    from app.modules.forms.service import find_form

    viewer = await viewer_for(db, principal)
    return await find_form(db, viewer, form_id, action="edit")


def _brief(schema: dict[str, Any]) -> dict[str, Any]:
    """What the model needs to see of a form: pages and questions (no design, no translations)."""
    def field(f: dict[str, Any]) -> dict[str, Any]:
        out = {k: f[k] for k in ("id", "key", "type", "label", "help", "required") if k in f}
        if f.get("options"):
            out["options"] = [{"value": o.get("value"), "label": o.get("label")} for o in f["options"][:50]]
        if isinstance(f.get("props"), dict) and f["type"] in ("rating", "scale", "image"):
            out["props"] = {k: v for k, v in f["props"].items() if k in ("min", "max", "alt")}
        return out
    return {"pages": [{"id": p["id"], "title": p.get("title"), "fields": [field(f) for r in p["rows"] for f in r["fields"]]}
                      for p in schema["pages"]],
            "rules": len(schema.get("logic") or [])}


assist_input = z.obj(action=z.enum(list(AI_ASSIST_ACTIONS)), schema=form_schema_v1)


@router.post("/ai/forms/{form_id}/assist", dependencies=[rate_limit("ai-assist", per_minute=30)])
async def assist_form_route(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "builder", ["forms"])
        form = await _editable(db, principal, form_id)
        values = assist_input.parse(await request.json())
    action, schema = values["action"], values["schema"]
    task = ModelTask(task=f"assist_{action}", system=P.assist_system(), schema=P.ASSIST,
                     content=P.content({"action": action, "form_name": form.name, "form": _brief(schema)}),
                     standin=lambda: assist_form(action, copy.deepcopy(schema), form.name))
    suggestions, made = await produce(task, lambda data: C.assist_from_model(
        data, action=action, schema=schema, standin=lambda: assist_form(action, copy.deepcopy(schema), form.name)))
    count = len(suggestions)
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="builder", status="proposed" if count else "discarded", title=TITLES[action],
            title_key={"code": f"assist_{action}"}, target={"type": "form", "id": str(form.id), "name": form.name},
            credits=credits_of("builder"), prompt=TITLES[action], result=f"{count} suggestion{'' if count == 1 else 's'}.",
            read=["forms"], made=made, notes=[{"code": "assist_found", "params": {"n": count}}],
            output={"form_id": str(form.id), "count": count})
        return ok({"request_id": str(saved.id), "action": action, "suggestions": suggestions, "credits": saved.credits})


async def _source(db: Any, principal: Principal, form_id: str, sent: dict[str, Any] | None) -> tuple[Any, dict[str, Any]]:
    """An editable form and the text to work on (with its title, which respondents see too)."""
    from app.modules.forms.schema import blank_schema

    form = await _editable(db, principal, form_id)
    schema = sent if sent is not None else (copy.deepcopy(form.draft_schema) if form.draft_schema else blank_schema())
    return form, with_title(schema, form.name)


translate_input = z.obj(languages=z.array(z.string()).min(1).max(19), schema=form_schema_v1.optional())
CHUNK = 150  # texts per model call


@router.post("/ai/forms/{form_id}/translate", dependencies=[rate_limit("ai-write", per_minute=20)])
async def translate_form_route(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    values = translate_input.parse(await request.json())
    async with db_session("read", **scope(principal)) as db:
        form, schema = await _source(db, principal, form_id, values.get("schema"))
        source = main_language(schema)
        languages = [code for code in dict.fromkeys(values["languages"]) if code in APP_LOCALE_CODES and code != source]
        if not languages:
            raise FrmError("FRM-GEN-1002", [{"field": "languages", "message": "Choose a language other than the form’s own."}])
        cost = credits_of("translate") * len(languages)
        settings = await A.require_ai(db, principal.tenant, "translate", ["forms"], cost)
    texts = form_texts(schema)
    plans = []
    jobs = []
    for code in languages:
        known = translator_for(code)
        saved = (schema.get("translations") or {}).get(code) or {}
        stale = stale_keys(schema, code, texts)
        items = []
        for t in texts:
            existing = saved[t["key"]] if isinstance(saved.get(t["key"]), str) and saved[t["key"]].strip() else None
            keep = existing is not None and t["key"] not in stale
            items.append({"key": t["key"], "text": t["text"], "kind": t["kind"], "page": t["page"],
                          "translation": None if keep or t["kind"] == "html" else known(t["text"]), "existing": existing,
                          "_keep": keep})
        left = {i["key"]: i for i in items if not i["_keep"] and i["translation"] is None}
        plans.append((code, items))
        keys = list(left)
        for start in range(0, len(keys), CHUNK):
            part = {k: left[k] for k in keys[start:start + CHUNK]}
            jobs.append((code, ModelTask(
                task="translate", system=P.translate_system(), schema=P.TRANSLATE,
                content=P.content({"from": source, "to": code,
                                   "items": [{"key": k, "text": i["text"], "kind": i["kind"]} for k, i in part.items()]}),
                standin=dict), part))
    answers, made = await produce_all([(task, lambda data, part=part: C.translations_from_model(data, part))
                                       for _, task, part in jobs])
    by_code: dict[str, dict[str, str]] = {}
    for (code, _, _), found in zip(jobs, answers, strict=True):
        by_code.setdefault(code, {}).update(found or {})
    result = []
    for code, items in plans:
        made_now = by_code.get(code, {})
        shown = [{k: v for k, v in i.items() if k != "_keep"} | ({"translation": made_now[i["key"]]} if i["key"] in made_now else {})
                 for i in items]
        result.append({"code": code, "items": shown,
                       "translated": sum(1 for i in shown if i["translation"]),
                       "missing": sum(1 for i in shown if not i["translation"] and not i["existing"])})
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="translate", status="proposed",
            title=f"Translate {form.name} into {', '.join(languages)}",
            title_key={"code": "translate", "params": {"form": form.name, "languages": ",".join(languages)}},
            target={"type": "form", "id": str(form.id), "name": form.name}, credits=cost,
            prompt=f"Translate the form from {source} into {', '.join(languages)}.",
            result="; ".join(f"{r['code']}: {r['translated']} translated, {r['missing']} left" for r in result),
            read=["forms"], made=made,
            notes=[{"code": "translated_total", "params": {"n": sum(r["translated"] for r in result),
                                                            "left": sum(r["missing"] for r in result)}}],
            output={"form_id": str(form.id), "row_version": form.row_version})
        return ok({"request_id": str(saved.id), "form": {"id": str(form.id), "name": form.name}, "from": source,
                   "languages": result, "credits": cost})


rewrite_input = z.obj(tone=z.enum(list(AI_TONES)).optional(), schema=form_schema_v1.optional())


@router.post("/ai/forms/{form_id}/rewrite", dependencies=[rate_limit("ai-write", per_minute=20)])
async def rewrite_form_route(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    values = rewrite_input.parse(await request.json())
    tone = values.get("tone") or "plain"
    async with db_session("read", **scope(principal)) as db:
        form, schema = await _source(db, principal, form_id, values.get("schema"))
        settings = await A.require_ai(db, principal.tenant, "rewrite", ["forms"])
    language = main_language(schema)
    english = language == "en"
    texts = [t for t in form_texts(schema) if t["kind"] != "html" and t["key"] != "form.title"]
    originals = {t["key"]: t["text"] for t in texts}

    def standin() -> list[dict[str, Any]]:
        out = []
        for t in texts:
            new = rewrite(t["text"], tone, english)
            if new["reasons"]:
                out.append({"key": t["key"], "text": t["text"], "rewrite": new["text"], "reasons": new["reasons"]})
        return out
    task = ModelTask(task="rewrite", system=P.rewrite_system(), schema=P.REWRITE,
                     content=P.content({"tone": tone, "language": language,
                                        "items": [{"key": t["key"], "text": t["text"]} for t in texts[:400]]}),
                     standin=standin)
    changed, made = await produce(task, lambda data: C.rewrites_from_model(data, originals))
    after = {c["key"]: c["rewrite"] for c in changed}
    reading = {"before": reading_age([t["text"] for t in texts]),
               "after": reading_age([after.get(t["key"], t["text"]) for t in texts])}
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="rewrite", status="proposed" if changed else "discarded",
            title=f"Rewrite {form.name} ({tone})", title_key={"code": "rewrite", "params": {"form": form.name, "tone": tone}},
            target={"type": "form", "id": str(form.id), "name": form.name}, credits=credits_of("rewrite"),
            prompt=f"Make the form easier to read, {tone} tone.",
            result=f"{len(changed)} of {len(texts)} texts could be clearer; reading age {reading['before']} to {reading['after']}.",
            read=["forms"], made=made,
            notes=[{"code": "rewrite_result", "params": {"n": len(changed), "total": len(texts),
                                                        "before": reading["before"], "after": reading["after"]}}],
            output={"form_id": str(form.id), "row_version": form.row_version})
        return ok({"request_id": str(saved.id), "form": {"id": str(form.id), "name": form.name}, "tone": tone,
                   "items": changed, "reading": reading, "total": len(texts), "credits": saved.credits})


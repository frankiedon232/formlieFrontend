"""Formalie's template catalogue (port of shared/templates: index.ts, localise.ts, and the mock's templateStore.ts
dictionaries), held to the frontend's answers by tests/parity/test_templates_rules.py.

The built English forms come from data/system_templates.json (scripts/dump_templates_rules.py); the text per
language from data/messages (template text), data/vocabulary (everyday form words) and data/ui (template names,
category names, the builder's default texts), copied by scripts/sync_frontend_data.py.
"""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from app.modules.design.catalogues import TEMPLATE_CATEGORIES
from app.modules.design.theme import apply_patch, default_theme

DATA = Path(__file__).parent / "data"
TEXT_PROPS = ("text", "html", "description", "min_label", "max_label", "link_label", "alt", "caption")
_LITERAL = re.compile(r'"([^"\\]*)"')
_LANG = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")


@lru_cache(maxsize=1)
def _catalogue() -> dict[str, Any]:
    return json.loads((DATA / "system_templates.json").read_text(encoding="utf-8"))


def system_templates() -> list[dict[str, Any]]:
    return _catalogue()["templates"]


def system_template(key: str) -> dict[str, Any] | None:
    return next((t for t in system_templates() if t["key"] == key), None)


def category_of(key: str) -> dict[str, Any] | None:
    return next((c for c in TEMPLATE_CATEGORIES if c["key"] == key), None)


def lang_code(lang: str | None) -> str:
    return lang if lang and _LANG.match(lang) else "en"


@lru_cache(maxsize=64)
def _json(folder: str, code: str) -> Any:
    path = DATA / folder / f"{code}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def content_dict(code: str) -> dict[str, str] | None:
    """Template text English → this language (None for English or a language without one)."""
    return None if code == "en" else _json("messages", code)


def _ui(code: str) -> dict[str, Any]:
    return _json("ui", code) or {}


def item_text(lang: str, key: str, part: str) -> str | None:
    """A system template's name or description in the person's language (None: the catalogue's English)."""
    return ((_ui(lang_code(lang)).get("templates") or {}).get("items") or {}).get(key, {}).get(part)


def category_name(lang: str, key: str) -> str:
    pick = lambda code: ((_ui(code).get("templates") or {}).get("categories") or {}).get(key)  # noqa: E731
    return pick(lang_code(lang)) or pick("en") or key


def _builder_dict(code: str) -> dict[str, str]:
    """The builder's own default texts English → this language (field names, Option / Row / Page {n})."""
    en, local = _ui("en").get("builder"), _ui(code).get("builder")
    out: dict[str, str] = {}
    if not en or not local:
        return out
    for kind, text in (en.get("field") or {}).items():
        if isinstance(text, str) and isinstance((local.get("field") or {}).get(kind), str):
            out[text] = local["field"][kind]
    pairs = [((en.get("defaults") or {}).get("option"), (local.get("defaults") or {}).get("option")),
             ((en.get("defaults") or {}).get("row"), (local.get("defaults") or {}).get("row")),
             ((en.get("page") or {}).get("default"), (local.get("page") or {}).get("default"))]
    for source, target in pairs:
        if source and target:
            for n in range(1, 51):
                out[source.replace("{n}", str(n))] = target.replace("{n}", str(n))
    return out


@lru_cache(maxsize=32)
def _translation_dict(code: str) -> tuple[tuple[str, str], ...] | None:
    if code == "en":
        return None
    merged = {**(_json("vocabulary", code) or {}), **_builder_dict(code), **(content_dict(code) or {})}
    return tuple(merged.items()) if merged else None


def translation_dict(code: str) -> dict[str, str] | None:
    """Everything Formalie can move into another language: vocabulary, builder defaults, template text."""
    found = _translation_dict(code)
    return dict(found) if found is not None else None


# ── Walking a form's readable text (shared/templates/localise.ts) ───────────────

def _translate_literals(formula: str, visit: Callable[[str], str]) -> str:
    """Text results in a formula; values compared against answers (`{x} = "yes"`) stay as they are."""
    def swap(match: re.Match[str]) -> str:
        whole, inner, at = match.group(0), match.group(1), match.start()
        before = formula[:at].rstrip()[-1:]
        after = formula[at + len(whole):].lstrip()[:1]
        compared = (before or " ") in "=<>!" or (after or " ") in "=<>!"
        return f'"{visit(inner)}"' if inner and not compared else whole
    return _LITERAL.sub(swap, formula)


def _walk(schema: dict[str, Any], visit: Callable[[str], str]) -> None:
    for page in schema.get("pages", []):
        if page.get("title"):
            page["title"] = visit(page["title"])
        for row in page.get("rows", []):
            for field in row.get("fields", []):
                for key in ("label", "help", "placeholder"):
                    if field.get(key):
                        field[key] = visit(field[key])
                for option in field.get("options") or []:
                    if option.get("label"):
                        option["label"] = visit(option["label"])
                props = field.get("props")
                if not props:
                    continue
                for name in TEXT_PROPS:
                    if isinstance(props.get(name), str) and props[name]:
                        props[name] = visit(props[name])
                if isinstance(props.get("rows"), list):
                    props["rows"] = [visit(r) if isinstance(r, str) else r for r in props["rows"]]
                if isinstance(props.get("formula"), str):
                    props["formula"] = _translate_literals(props["formula"], visit)
    for page in schema.get("pages", []):
        for row in page.get("rows", []):
            for field in row.get("fields", []):
                message = (field.get("validation") or {}).get("pattern_message")
                if isinstance(message, str) and message:
                    field["validation"]["pattern_message"] = visit(message)
    settings = schema.get("settings") or {}
    if settings.get("title"):
        settings["title"] = visit(settings["title"])
    guide = settings.get("guide")
    if guide and guide.get("title"):
        guide["title"] = visit(guide["title"])
    header = (schema.get("theme") or {}).get("header") if isinstance(schema.get("theme"), dict) else None
    if isinstance(header, dict) and isinstance(header.get("subtitle"), str) and header["subtitle"]:
        header["subtitle"] = visit(header["subtitle"])
    thanks = schema.get("thank_you")
    if thanks:
        for key in ("title", "message"):
            if thanks.get(key):
                thanks[key] = visit(thanks[key])


def localise_schema(schema: dict[str, Any], dictionary: dict[str, str] | None, language: str) -> dict[str, Any]:
    """A copy in another language; `language` is recorded in the form settings (English without a dictionary)."""
    out = copy.deepcopy(schema)
    if dictionary:
        _walk(out, lambda text: dictionary.get(text, text))
    out["settings"] = {**(out.get("settings") or {}), "language": language if dictionary else "en"}
    return out


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def translate_content(schema: dict[str, Any], source: dict[str, str] | None, target: dict[str, str] | None) -> dict[str, Any]:
    """A form's text moved to another language: any text from the dictionaries, in English or in the form's previous
    language (`source`); text people wrote themselves stays (`kept`). None = English."""
    english = {_normalise(k): k for k in (target or source or {})}
    back = {_normalise(text): key for key, text in (source or {}).items()}
    out = copy.deepcopy(schema)
    counts = {"translated": 0}
    kept: dict[str, None] = {}

    def visit(text: str) -> str:
        key = _normalise(text)
        found = english.get(key) if key in english else back.get(key)
        result = None if found is None else (target.get(found) if target else found)
        if result is None:
            if any(ch.isalpha() for ch in text):
                kept[text] = None
            return text
        if result != text:
            counts["translated"] += 1
        return result
    _walk(out, visit)
    return {"schema": out, "translated": counts["translated"], "kept": list(kept)}


# ── Templates as forms ──────────────────────────────────────────────────────────

def template_theme(template: dict[str, Any], logo_url: str | None, primary: str | None) -> dict[str, Any]:
    """Category design, then the template's own accents (the logo follows the workspace)."""
    category = category_of(template["category"])
    return apply_patch(apply_patch(default_theme(logo_url, primary), (category or {}).get("design") or {}),
                       template.get("design") or {})


def template_schema(template: dict[str, Any], logo_url: str | None, primary: str | None) -> dict[str, Any]:
    return {**copy.deepcopy(template["schema"]), "theme": template_theme(template, logo_url, primary)}


def system_schema(template: dict[str, Any], lang: str, logo_url: str | None, primary: str | None) -> dict[str, Any]:
    """A system template's form in the person's language (English when there is no translation)."""
    code = lang_code(lang)
    return localise_schema(template_schema(template, logo_url, primary), content_dict(code), code)

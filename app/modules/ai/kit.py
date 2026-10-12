"""Form building blocks the assistant works with, ported from the frontend and held to its answers by
tests/parity/test_ai_rules.py:

- shared/templates/kit.ts: `slug`, `opts`, `agreeScale`, `buildSchema` (a short definition → a real FormSchema v1)
  and `schemaStats` (shared/templates/index.ts);
- shared/utils/forms/translations.ts: `formTexts` (every text people read, with its key, kind and page), `staleKeys`;
- the mock's `maskText` (server/mock/data/aiStore.ts): emails, phone numbers and long digit runs replaced.

A definition (`TemplateDef`) is a dict: {name, description, pages: [{title, rows: [{fields: [seed]}]}],
logic: [{match, when: [{key, op, value}], then: [{action, target, value}]}], thank_you: {title, message}}; a seed
is {type, label, key?, required?, help?, placeholder?, width?, readonly?, options?, validation?, props?, formula?,
default?}.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from typing import Any, Callable

from app.core import js
from app.core.locales import APP_LOCALE_CODES
from app.modules.forms.catalogues import FIELD_TYPES
from app.modules.forms.logic import END_OF_FORM

# JavaScript's \s (WhiteSpace and LineTerminator), for patterns that must match what the browser's regexes match
JS_SPACE = "[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]"
WORD_B = r"(?a:\b)"  # JavaScript's \b (ASCII word characters)


def is_input(field_type: str) -> bool:
    return bool(FIELD_TYPES.get(field_type, {}).get("input"))


def has_options(field_type: str) -> bool:
    return bool(FIELD_TYPES.get(field_type, {}).get("options"))


def all_fields(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not schema:
        return []
    return [f for page in schema.get("pages") or [] for row in page.get("rows") or [] for f in row.get("fields") or []]


def slug(text: str) -> str:
    out = unicodedata.normalize("NFKD", text.lower())
    out = re.sub("[\u0300-\u036f]", "", out)
    out = re.sub(r"[^a-z0-9]+", "_", out).strip("_")[:48]
    return out or "field"


def opts(*labels: str) -> list[dict[str, Any]]:
    return [{"value": slug(label), "label": label} for label in labels]


def scored(*pairs: tuple[str, int]) -> list[dict[str, Any]]:
    return [{"value": slug(label), "label": label, "score": score} for label, score in pairs]


def agree_scale() -> list[dict[str, Any]]:
    return scored(("Strongly disagree", 1), ("Disagree", 2), ("Neutral", 3), ("Agree", 4), ("Strongly agree", 5))


def _unique_key(wanted: str, taken: set[str]) -> str:
    base = slug(wanted)
    if not re.match(r"^[a-z]", base):
        base = f"q_{base}"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}_{n}", n + 1
    taken.add(key)
    return key


# Same starting props as a field added in the builder (field-registry.ts)
DEFAULT_PROPS: dict[str, dict[str, Any]] = {
    "long_text": {"rows": 4},
    "currency": {"currency": "USD"},
    "full_name": {"show_title": False, "show_middle": False},
    "consent": {"text": "", "link_label": "", "link_href": ""},
    "ip_address": {"ip_version": "any"},
    "rating": {"max": 5},
    "scale": {"min": 0, "max": 10, "min_label": "", "max_label": ""},
    "slider": {"min": 0, "max": 100, "step": 1},
    "file_upload": {"max_files": 1, "max_mb": 10, "accept": ""},
    "image_upload": {"max_files": 1, "max_mb": 10, "accept": "image/*"},
    "address": {"require_postal_code": True, "require_region": False},
    "matrix": {"rows": ["Quality", "Speed", "Value"]},
    "section": {"description": "", "size": "lg", "divider": True, "align": "start"},
    "paragraph": {"html": ""},
    "divider": {"style": "solid", "spacing": "md"},
    "hidden": {"param": ""},
}


def to_field(seed: dict[str, Any], id_: str, key: str, width: int) -> dict[str, Any]:
    kind = seed["type"]
    props = {**DEFAULT_PROPS.get(kind, {}), **(seed.get("props") or {}),
             **({"formula": seed["formula"]} if seed.get("formula") else {})}
    out: dict[str, Any] = {"id": id_, "key": key, "type": kind, "label": seed["label"],
                           "width": min(12, max(1, width)), "required": bool(seed.get("required"))}
    if seed.get("help"):
        out["help"] = seed["help"]
    if seed.get("placeholder"):
        out["placeholder"] = seed["placeholder"]
    if seed.get("readonly"):
        out["readonly"] = True
    if seed.get("validation"):
        out["validation"] = seed["validation"]
    if "default" in seed and seed["default"] is not js.UNDEFINED:
        out["default"] = seed["default"]
    if props:
        out["props"] = props
    if kind == "percentage" and not seed.get("validation"):
        out["validation"] = {"min": 0, "max": 100}
    if has_options(kind):
        out["options"] = seed.get("options") or opts("Option 1", "Option 2", "Option 3")
    return out


def build_schema(definition: dict[str, Any]) -> dict[str, Any]:
    """buildSchema(): ids are stable (`f_<key>`, `p1`, `r1`, `rule1`) so logic and calculations line up."""
    taken: set[str] = set()
    id_of: dict[str, str] = {}
    row_count = 0
    pages = []
    for p, page_seed in enumerate(definition["pages"]):
        rows = []
        for row_seed in page_seed["rows"]:
            row_count += 1
            share = max(1, 12 // max(1, len(row_seed["fields"])))
            fields = []
            for seed in row_seed["fields"]:
                key = _unique_key(seed.get("key") or seed["label"], taken)
                id_ = f"f_{key}"
                id_of[key] = id_
                fields.append(to_field(seed, id_, key, seed.get("width") or share))
            rows.append({"id": f"r{row_count}", "fields": fields})
        pages.append({"id": f"p{p + 1}", "title": page_seed["title"], "rows": rows})
    page_ids = {slug(page_seed["title"]): f"p{p + 1}" for p, page_seed in enumerate(definition["pages"])}

    def target(name: Any) -> Any:
        if name is None or name is js.UNDEFINED:
            return js.UNDEFINED
        if name == END_OF_FORM:
            return END_OF_FORM
        return id_of.get(name) or page_ids.get(slug(name)) or name

    logic = []
    for index, rule in enumerate(definition.get("logic") or []):
        conditions = [{"field": id_of.get(c["key"], c["key"]), "op": c["op"], "value": c.get("value")}
                      for c in rule["when"]]
        effects = []
        for effect in rule["then"]:
            out: dict[str, Any] = {"action": effect["action"]}
            aimed = target(effect.get("target"))
            if aimed is not js.UNDEFINED:
                out["target"] = aimed
            if effect.get("value", js.UNDEFINED) is not js.UNDEFINED:
                out["value"] = effect["value"]
            effects.append(out)
        logic.append({"id": f"rule{index + 1}",
                      "when": {"any": conditions} if rule.get("match") == "any" else {"all": conditions},
                      "then": effects})
    thanks = definition.get("thank_you") or {}
    return {
        "schema_version": 1,
        "settings": {"progress_bar": len(pages) > 1, "save_resume": len(pages) > 2, "language": "en"},
        "pages": pages,
        "logic": logic,
        "calculations": [],
        "thank_you": {"title": thanks.get("title") or "Thank you!",
                      "message": thanks.get("message") or "Your response has been recorded.", "redirect_url": None},
    }


def field_from(seed: dict[str, Any], new_id: Callable[[], str]) -> dict[str, Any]:
    """A field the builder can take (builderEngine fieldFrom): built as a template field, fresh id, full width."""
    built = all_fields(build_schema({"pages": [{"title": "x", "rows": [{"fields": [seed]}]}]}))[0]
    return {**built, "id": new_id(), "width": 12}


def schema_stats(schema: dict[str, Any]) -> dict[str, int]:
    fields = all_fields(schema)
    return {
        "pages": len(schema.get("pages") or []),
        "fields": sum(1 for f in fields if is_input(f["type"]) and f["type"] not in ("calculated", "hidden")),
        "logic": len(schema.get("logic") or []),
        "calculations": sum(1 for f in fields if f["type"] == "calculated"),
    }


# ── Texts of a form (translations.ts) ─────────────────────────────────────────

_TEXT_PROPS = {"text": "long", "html": "html", "description": "long", "min_label": "text", "max_label": "text",
               "link_label": "text", "alt": "text", "caption": "text"}
_LITERAL = re.compile(r'"([^"\\]*)"')
_LETTER = re.compile(r"[^\W\d_]")
_ADDRESS = re.compile(r"^" + JS_SPACE + r"*([a-z][a-z0-9+.-]*://\S*|[^\s@]+@[^\s@]+)" + JS_SPACE + r"*$", re.I)

Visit = Callable[[str, str, str, "str | None"], str]


def has_words(text: str) -> bool:
    return bool(_LETTER.search(text)) and not _ADDRESS.match(text)


def _walk_literals(formula: str, key: str, page: str, visit: Visit) -> str:
    n = 0

    def swap(match: re.Match[str]) -> str:
        nonlocal n
        whole, inner, at = match.group(0), match.group(1), match.start()
        before = js.trim_end(formula[:at])[-1:]
        after = js.trim_start(formula[at + len(whole):])[:1]
        if not inner or (before or " ") in "=<>!" or (after or " ") in "=<>!":
            return whole
        out = f'"{visit(f"{key}.{n}", inner, "text", page)}"'
        n += 1
        return out
    return _LITERAL.sub(swap, formula)


def walk_texts(schema: dict[str, Any], visit: Visit) -> None:
    """Every readable text of a form with its key, kind and page; `visit` returns the replacement (in place)."""
    def swap(holder: Any, prop: str, key: str, kind: str, page: str | None) -> None:
        if isinstance(holder, dict) and isinstance(holder.get(prop), str) and holder[prop]:
            holder[prop] = visit(key, holder[prop], kind, page)
    settings = schema.get("settings") if isinstance(schema.get("settings"), dict) else None
    swap(settings, "title", "form.title", "text", None)
    guide = settings.get("guide") if settings else None
    swap(guide, "title", "guide.title", "text", None)
    swap(guide, "html", "guide.html", "html", None)
    theme = schema.get("theme")
    swap(theme.get("header") if isinstance(theme, dict) else None, "subtitle", "header.subtitle", "text", None)
    for page in schema.get("pages") or []:
        pid = page["id"]
        swap(page, "title", f"page.{pid}.title", "text", pid)
        for row in page.get("rows") or []:
            for fld in row.get("fields") or []:
                at = f"field.{fld['id']}"
                swap(fld, "label", f"{at}.label", "text", pid)
                swap(fld, "help", f"{at}.help", "long", pid)
                swap(fld, "placeholder", f"{at}.placeholder", "text", pid)
                for option in fld.get("options") or []:
                    swap(option, "label", f"{at}.option.{js.to_string(option.get('value'))}", "text", pid)
                swap(fld.get("validation"), "pattern_message", f"{at}.pattern_message", "text", pid)
                props = fld.get("props")
                if not isinstance(props, dict):
                    continue
                for name, kind in _TEXT_PROPS.items():
                    swap(props, name, f"{at}.{name}", kind, pid)
                if isinstance(props.get("rows"), list):
                    props["rows"] = [visit(f"{at}.row.{i}", r, "text", pid) if isinstance(r, str) and r else r
                                     for i, r in enumerate(props["rows"])]
                if isinstance(props.get("formula"), str):
                    props["formula"] = _walk_literals(props["formula"], f"{at}.formula", pid, visit)
    swap(schema.get("thank_you"), "title", "thanks.title", "text", None)
    swap(schema.get("thank_you"), "message", "thanks.message", "long", None)


def form_texts(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """formTexts(): every text people read, in form order (things without letters are left out)."""
    found: list[dict[str, Any]] = []

    def visit(key: str, text: str, kind: str, page: str | None) -> str:
        if has_words(re.sub(r"<[^>]*>", "", text) if kind == "html" else text):
            found.append({"key": key, "text": text, "kind": kind, "page": page})
        return text
    walk_texts(json.loads(json.dumps(schema)), visit)
    return found


def main_language(schema: dict[str, Any] | None) -> str:
    main = ((schema or {}).get("settings") or {}).get("language")
    main = "en" if js.nullish(main) else main
    return main if main in APP_LOCALE_CODES else "en"


def text_hash(text: str) -> str:
    from app.modules.lists.rules import text_hash as fnv

    return fnv(text)


def stale_keys(schema: dict[str, Any], language: str, texts: list[dict[str, Any]] | None = None) -> set[str]:
    texts = form_texts(schema) if texts is None else texts
    saved = (schema.get("translations") or {}).get(language) or {}
    made_from = (schema.get("translated_from") or {}).get(language) or {}
    return {t["key"] for t in texts if js.trim(saved.get(t["key"]) or "") and made_from.get(t["key"])
            and made_from[t["key"]] != text_hash(t["text"])}


def with_title(schema: dict[str, Any], name: str) -> dict[str, Any]:
    """The form's texts include its title, which respondents see too (the name when it has none)."""
    out = copy.deepcopy(schema)
    settings = out.get("settings") if isinstance(out.get("settings"), dict) else {}
    out["settings"] = {**settings, "title": settings.get("title") or name}
    return out


# ── Personal data kept out (aiStore.ts maskText) ──────────────────────────────

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", re.ASCII)
_NUMBER = re.compile(r"\+?\d(?:[\d().-]|" + JS_SPACE + r"){7,}\d", re.ASCII)
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(T[\d:.]+Z?)?$", re.ASCII)


def mask_text(text: str) -> str:
    out = _EMAIL.sub("[email]", text)
    return _NUMBER.sub(lambda m: m.group(0) if _ISO.match(js.trim(m.group(0))) else "[number]", out)

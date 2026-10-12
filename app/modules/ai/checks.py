"""Model answers are checked and repaired with Formalie's own rules before anyone sees them (owner, 2026-10-12).

Each function takes the model's JSON (in the schema of app/modules/ai/prompts.py) and returns the final answer in
the mock's shapes, or raises `OutputInvalid` when it can't be made valid (the caller then answers with the stand-in).
Repairs: unknown field types become short text, keys are made unique snake_case, choice questions get options, props
are limited to what each type uses, formulas must parse and use the form's keys, rules must point at real questions
and pages with operators that fit, the schema must pass FormSchema v1 (app/modules/forms/schema.py); designs must pass
the theme schema with a readable button colour; translations keep their keys, and rich text keeps its markup tag for
tag; rewrites, labels, question plans and summaries keep only what the form has.
"""

from __future__ import annotations

import copy
import re
from datetime import date
from typing import Any, Callable

from app.core import js
from app.core.locales import APP_LOCALE_CODES
from app.modules.ai import engine_analysis as AN
from app.modules.ai import engine_themes as TH
from app.modules.ai.engine_builder import ai_rule_id, similar, suggestion_id
from app.modules.ai.engine_forms import one_page, title_from
from app.modules.ai.kinds import AI_PROBLEMS, AI_REWRITE_REASONS, AI_THEMES
from app.modules.ai.kit import all_fields, build_schema, field_from, has_options, is_input, opts, schema_stats, slug
from app.modules.ai.prompts import CATEGORY_KEYS, DRAFT_NOTES, LOGIC_ACTIONS, MODEL_FIELD_TYPES
from app.modules.design.theme import apply_patch, default_theme, theme_schema
from app.modules.forms.builder import publish_issues
from app.modules.forms.formula import formula_keys, is_valid_formula
from app.modules.forms.logic import END_OF_FORM
from app.modules.forms.schema import form_schema_v1

MAX_FIELDS = 120
MAX_PAGES = 20
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class OutputInvalid(Exception):
    """The model's answer can't be made valid; `reason` says why (kept with the request, never shown as text)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _text(value: Any, size: int) -> str:
    return js.trim(value)[:size] if isinstance(value, str) else ""


def _dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OutputInvalid("not_an_object")
    return value


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _params(value: Any) -> dict[str, str | int | float]:
    out: dict[str, str | int | float] = {}
    for item in _list(value)[:8]:
        if isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("value"), (str, int, float)) \
                and not isinstance(item.get("value"), bool):
            out[item["name"][:40]] = item["value"][:200] if isinstance(item["value"], str) else item["value"]
    return out


def notes_of(value: Any, allowed: tuple[str, ...]) -> list[dict[str, Any]]:
    out = []
    for item in _list(value)[:10]:
        if isinstance(item, dict) and item.get("code") in allowed:
            params = _params(item.get("params"))
            out.append({"code": item["code"], **({"params": params} if params else {})})
    return out


# ── Logic (logic.ts: operators per kind of field, actions and what they point at) ──

_KIND = {"number": "number", "currency": "number", "rating": "number", "scale": "number", "slider": "number",
         "calculated": "number", "percentage": "number", "dropdown": "choice", "radio": "choice", "country": "choice",
         "language": "choice", "timezone": "choice", "currency_code": "choice", "multi_select": "multi",
         "checkbox": "multi", "ranking": "multi", "toggle": "toggle", "consent": "toggle", "date": "date",
         "datetime": "date", "time": "date", "file_upload": "presence", "image_upload": "presence",
         "signature": "presence", "address": "presence", "matrix": "presence", "date_range": "presence",
         "full_name": "presence", "duration": "presence"}
_OPERATORS = {
    "number": ("eq", "neq", "gt", "gte", "lt", "lte", "between", "not_between", "empty", "not_empty"),
    "choice": ("eq", "neq", "in", "not_in", "empty", "not_empty"),
    "multi": ("contains", "not_contains", "in", "contains_all", "count_gte", "count_lte", "empty", "not_empty"),
    "toggle": ("true", "false"),
    "date": ("eq", "before", "after", "between", "not_between", "empty", "not_empty"),
    "presence": ("not_empty", "empty"),
    "text": ("eq", "neq", "contains", "not_contains", "starts_with", "ends_with", "empty", "not_empty"),
}
_TARGET = {"show": "field", "hide": "field", "require": "input", "unrequire": "input", "enable": "input",
           "disable": "input", "set_value": "input", "clear_value": "input", "show_page": "page", "hide_page": "page",
           "jump": "page", "skip_to_end": "none"}


def operators_for(field_type: str) -> tuple[str, ...]:
    return _OPERATORS[_KIND.get(field_type, "text")]


def _condition(c: Any, by_id: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(c, dict) or c.get("field") not in by_id:
        return None
    field = by_id[c["field"]]
    op = c.get("op")
    if not is_input(field["type"]) or op not in operators_for(field["type"]):
        return None
    raw = c["values"] if "values" in c else c.get("value")
    items = raw if isinstance(raw, list) else ([] if raw is None or raw == "" else [raw])
    if op in ("empty", "not_empty", "true", "false"):
        return {"field": field["id"], "op": op, "value": None}
    if op in ("between", "not_between") or not items:
        return None  # a range needs a second value the assistant doesn't give; the others need one
    values = {o.get("value") for o in field.get("options") or []}
    value: Any
    if op in ("in", "not_in", "contains_all"):
        value = [js.to_string(v) for v in items]
        if values and not set(value) <= values:
            return None
    elif op in ("count_gte", "count_lte", "gt", "gte", "lt", "lte") or _KIND.get(field["type"]) == "number":
        value = number_of(items[0])
        if value is None:
            return None
    elif _KIND.get(field["type"]) in ("choice", "multi"):
        value = items[0]
        if value not in values:
            return None
    else:
        value = items[0]
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return None
    return {"field": field["id"], "op": op, "value": value}


def number_of(value: Any) -> int | float | None:
    """A number the model wrote (as a number or as digits)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        n = float(js.trim(value)) if isinstance(value, str) else None
    except ValueError:
        return None
    if n is None or n != n or n in (float("inf"), float("-inf")):
        return None
    return int(n) if n.is_integer() else n


def clean_rule(rule: Any, schema: dict[str, Any], rule_id: str) -> dict[str, Any] | None:
    """A rule with only conditions and effects that point at real questions and pages (None when nothing is left)."""
    if not isinstance(rule, dict) or not isinstance(rule.get("when"), dict):
        return None
    by_id = {f["id"]: f for f in all_fields(schema)}
    pages = {p["id"] for p in schema["pages"]}
    group = "any" if "any" in rule["when"] else "all"
    conditions = [c for c in (_condition(c, by_id) for c in _list(rule["when"].get(group))) if c]
    watched = {c["field"] for c in conditions}
    effects = []
    for effect in _list(rule.get("then")):
        if not isinstance(effect, dict) or effect.get("action") not in _TARGET:
            continue
        action, target = effect["action"], effect.get("target")
        aim = _TARGET[action]
        if aim == "none":
            effects.append({"action": action})
            continue
        if aim == "page" and (target in pages or (action == "jump" and target == END_OF_FORM)):
            effects.append({"action": action, "target": target})
        elif aim in ("field", "input") and target in by_id and target not in watched \
                and (aim == "field" or is_input(by_id[target]["type"])):
            out = {"action": action, "target": target}
            if action == "set_value":
                if not isinstance(effect.get("value"), (str, int, float)) or isinstance(effect.get("value"), bool):
                    continue
                out["value"] = effect["value"]
            effects.append(out)
    if not conditions or not effects:
        return None
    return {"id": rule_id, "when": {group: conditions}, "then": effects}


# ── Form drafts ───────────────────────────────────────────────────────────────

_PROPS: dict[str, tuple[str, ...]] = {"rating": ("max",), "scale": ("min", "max", "min_label", "max_label"),
                                      "slider": ("min", "max", "step"), "matrix": ("rows",), "calculated": ("format",),
                                      "consent": ("text",)}


def _props(kind: str, raw: Any, rows: Any = None) -> dict[str, Any] | None:
    """Only the props the type uses; the model gives them as name and value pairs."""
    if isinstance(raw, list):
        raw = {p.get("name"): p.get("value") for p in raw if isinstance(p, dict) and isinstance(p.get("name"), str)}
    raw = dict(raw) if isinstance(raw, dict) else {}
    if isinstance(rows, list) and rows:
        raw["rows"] = rows
    out: dict[str, Any] = {}
    for name in _PROPS.get(kind, ()):
        value = raw.get(name)
        if value is None or value == "":
            continue
        if name in ("min", "max", "step") and number_of(value) is not None:
            out[name] = number_of(value)
        elif name in ("min_label", "max_label", "text") and isinstance(value, str):
            out[name] = _text(value, 200)
        elif name == "rows" and isinstance(value, list):
            out[name] = [_text(r, 200) for r in value if isinstance(r, str) and js.trim(r)][:20]
        elif name == "format" and value in ("number", "currency", "percentage"):
            out[name] = value
    if kind == "rating" and not (isinstance(out.get("max"), int) and 3 <= out["max"] <= 10):
        out["max"] = 5
    if kind == "scale":
        out["min"] = out["min"] if out.get("min") in (0, 1) else 0
        out["max"] = out["max"] if isinstance(out.get("max"), int) and out["min"] < out["max"] <= 10 else 10
    return out or None


def _options(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for o in _list(raw)[:100]:
        if not isinstance(o, dict):
            continue
        label = _text(o.get("label"), 500)
        value = slug(_text(o.get("value"), 200) or label)[:200]
        if not label or value in seen:
            continue
        seen.add(value)
        out.append({"value": value, "label": label})
    return out


def _seed(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("type") if raw.get("type") in MODEL_FIELD_TYPES else "short_text"
    label = _text(raw.get("label"), 500) or ("" if kind == "divider" else "Section" if kind == "section" else "Question")
    seed: dict[str, Any] = {"type": kind, "label": label, "required": bool(raw.get("required")) and is_input(kind)
                            and kind != "calculated"}
    if isinstance(raw.get("key"), str) and js.trim(raw["key"]):
        seed["key"] = raw["key"]
    for name, size in (("help", 2000), ("placeholder", 500)):
        if _text(raw.get(name), size):
            seed[name] = _text(raw.get(name), size)
    if has_options(kind):
        options = _options(raw.get("options"))
        seed["options"] = options if options else opts("Option 1", "Option 2", "Option 3")
    props = _props(kind, raw.get("props"), raw.get("rows"))
    if props:
        seed["props"] = props
    if kind == "calculated":
        seed["formula"] = _text(raw.get("formula"), 2000)
    return seed


def _key_map(seeds: list[dict[str, Any]]) -> dict[str, str]:
    """The key each question gets (unique snake_case, as build_schema makes them), from what the model called it."""
    taken: set[str] = set()
    mapping: dict[str, str] = {}
    for seed in seeds:
        wanted = seed.get("key") or seed["label"]
        base = slug(wanted)
        if not re.match(r"^[a-z]", base):
            base = f"q_{base}"
        key, n = base, 2
        while key in taken:
            key, n = f"{base}_{n}", n + 1
        taken.add(key)
        for name in (seed.get("key"), slug(seed.get("key") or "")):
            if name and name not in mapping:
                mapping[name] = key
        seed["key"] = key
    return mapping


def _formula(formula: str, mapping: dict[str, str], keys: set[str]) -> str | None:
    swapped = re.sub(r"\{([A-Za-z0-9_]+)((?:\.[a-z0-9_]+)?)\}", lambda m: "{" + mapping.get(m.group(1), m.group(1)) + m.group(2) + "}",
                     formula)
    if not swapped or not is_valid_formula(swapped) or not set(formula_keys(swapped)) <= keys:
        return None
    return swapped


def form_from_model(data: Any, *, prompt: str, document: str | None, pages: str, template: bool = False) -> dict[str, Any]:
    """A form draft from the model: {name, description, schema (no theme), notes, based_on, source, category,
    design, language}."""
    from app.modules.templates.catalogue import system_template

    data = _dict(data)
    page_list = []
    count = 0
    for p, raw_page in enumerate(_list(data.get("pages"))[:MAX_PAGES]):
        if not isinstance(raw_page, dict):
            continue
        rows = []
        for raw_row in _list(raw_page.get("rows")):
            seeds = [s for s in (_seed(f) for f in _list(raw_row.get("fields") if isinstance(raw_row, dict) else None)) if s]
            for i in range(0, len(seeds), 2):  # two questions side by side at most
                chunk = seeds[i:i + 2][:max(0, MAX_FIELDS - count)]
                if chunk:
                    rows.append({"fields": chunk})
                    count += len(chunk)
        if rows:
            page_list.append({"title": _text(raw_page.get("title"), 200) or f"Page {p + 1}", "rows": rows})
    seeds = [s for page in page_list for row in page["rows"] for s in row["fields"]]
    if not any(is_input(s["type"]) for s in seeds):
        raise OutputInvalid("no_questions")
    mapping = _key_map(seeds)
    keys = {s["key"] for s in seeds}
    for page in page_list:
        for row in page["rows"]:
            row["fields"] = [s for s in row["fields"] if s["type"] != "calculated"
                             or _set_formula(s, mapping, keys)]
        page["rows"] = [r for r in page["rows"] if r["fields"]]
    page_list = [p for p in page_list if p["rows"]]
    rules = []
    for rule in _list(data.get("rules"))[:100]:
        if not isinstance(rule, dict):
            continue
        rules.append({"match": "any" if rule.get("match") == "any" else "all",
                      "when": [{"key": mapping.get(c["key"], c["key"]), "op": c.get("op"),
                                "value": c["values"] if "values" in c else c.get("value")}
                               for c in _list(rule.get("when")) if isinstance(c, dict) and isinstance(c.get("key"), str)],
                      "then": [{"action": e.get("action"),
                                **({"target": mapping.get(e["target"], e["target"])} if e.get("target") else {}),
                                **({"value": e["value"]} if e.get("value") not in (None, "") else {})}
                               for e in _list(rule.get("then")) if isinstance(e, dict)]})
    thanks = data.get("thank_you") if isinstance(data.get("thank_you"), dict) else {}
    name = _text(data.get("name"), 80 if template else 120) or title_from(prompt, "New form")
    definition = {"name": name, "description": _text(data.get("description"), 300), "pages": page_list, "logic": rules,
                  "thank_you": {"title": _text(thanks.get("title"), 200), "message": _text(thanks.get("message"), 2000)}}
    schema = build_schema(definition)
    schema["logic"] = [r for r in (clean_rule(rule, schema, rule["id"]) for rule in schema["logic"]) if r]
    if pages == "one":
        schema = one_page(schema)
    language = data.get("language")
    if language in APP_LOCALE_CODES:
        schema["settings"]["language"] = language
    good, _ = form_schema_v1.safe_parse(schema)
    if not good:
        raise OutputInvalid("schema")
    if any(issue["code"] == "no_inputs" for issue in publish_issues(schema)):
        raise OutputInvalid("no_questions")
    based = system_template(data["based_on"]) if isinstance(data.get("based_on"), str) and data["based_on"] else None
    source = data.get("source")
    if document and js.trim(document):
        source = "document"
    elif not (source in ("list", "basic") or (source == "template" and based)):
        source = "list"
    category = data.get("category") if data.get("category") in CATEGORY_KEYS else None
    return {"name": name, "description": definition["description"], "schema": schema,
            "notes": notes_of(data.get("notes"), DRAFT_NOTES),
            "based_on": {"key": based["key"], "name": based["name"]} if based else None, "source": source,
            "category": category, "design": copy.deepcopy(based.get("design") or {}) if based else {}}


def _set_formula(seed: dict[str, Any], mapping: dict[str, str], keys: set[str]) -> bool:
    formula = _formula(seed.get("formula") or "", mapping, keys - {seed["key"]})
    if formula is None:
        return False
    seed["formula"] = formula
    return True


# ── Designs ───────────────────────────────────────────────────────────────────

def _colour(value: Any) -> str | None:
    return value.lower() if isinstance(value, str) and _HEX.match(value) else None


def _clean_patch(raw: Any) -> dict[str, Any]:
    """Only the parts of a theme the assistant may set, with valid colours (the model gives part and value pairs)."""
    if isinstance(raw, list):
        nested: dict[str, Any] = {}
        for pair in raw:
            if not isinstance(pair, dict) or not isinstance(pair.get("part"), str):
                continue
            part, value = pair["part"], pair.get("value")
            if part in ("container.border", "buttons.full_width", "blocks.section_caps"):
                value = {"true": True, "false": False}.get(js.to_string(value).lower())
            elif part == "page.gradient_angle":
                value = number_of(value)
                value = int(value) if value is not None else None
            if value is None:
                continue
            if "." in part:
                group, name = part.split(".", 1)
                nested.setdefault(group, {})[name] = value
            else:
                nested[part] = value
        raw = nested
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for group, value in raw.items():
        if group == "layout" and value in ("card", "plain"):
            out["layout"] = value
        elif isinstance(value, dict):
            part = {}
            for name, item in value.items():
                if item is None:
                    continue
                if name in ("bg", "bg_to", "primary", "text", "input_border", "band_bg", "band_to"):
                    if _colour(item):
                        part[name] = _colour(item)
                else:
                    part[name] = item
            if part:
                out[group] = part
    return out


def themes_from_model(data: Any, *, colour: str, mood: str, logo_url: str | None) -> list[dict[str, Any]]:
    """Three designs (calm, bold, minimal; each once), each a full valid theme with a readable button colour; a
    design that can't be made valid is the stand-in's for that key."""
    data = _dict(data)
    brand = TH.brand_of(colour)
    readable = TH.readable(brand)
    base = default_theme(logo_url, readable)
    standin = {s["key"]: s for s in TH.themes_from_colour(colour, mood, logo_url)}
    out: list[dict[str, Any]] = []
    for raw in _list(data.get("suggestions")):
        if not isinstance(raw, dict) or raw.get("key") not in standin or any(s["key"] == raw["key"] for s in out):
            continue
        tokens = apply_patch(base, _clean_patch(raw.get("patch")))
        primary = tokens["colors"]["primary"]
        if TH.contrast(primary, "#ffffff") < 4.5:
            tokens["colors"]["primary"] = TH.readable(primary)
        if tokens["header"]["band"] != "none" and TH.contrast(tokens["header"]["band_bg"], "#ffffff") < 4.5:
            tokens["header"]["band_bg"] = TH.readable(tokens["header"]["band_bg"])
        good, parsed = theme_schema.safe_parse(tokens)
        fallback = standin[raw["key"]]
        out.append({"key": raw["key"], "name": _text(raw.get("name"), 40) or fallback["name"],
                    "description": _text(raw.get("description"), 200) or fallback["description"],
                    "tokens": parsed if good else fallback["tokens"]})
    if not out:
        raise OutputInvalid("no_designs")
    for key in TH.order_for(mood):
        if all(s["key"] != key for s in out):
            out.append(standin[key])
    return out


# ── Builder help ──────────────────────────────────────────────────────────────

def _patch_for(problem: str, field: dict[str, Any] | None, text: str) -> tuple[dict[str, Any] | None, bool]:
    if problem in ("email_type", "phone_type", "date_type", "number_type"):
        return {"type": problem.split("_")[0]}, False
    if problem == "image_alt" and field is not None:
        return {"props": {**(field.get("props") or {}), "alt": text or field.get("label") or "Image"}}, False
    if problem == "long_label" and text and field is not None:
        return {"label": text[:500], "help": " ".join(p for p in [field.get("label"), field.get("help")] if p)[:2000]}, False
    if problem == "no_required":
        return {"required": True}, False
    if problem == "duplicate":
        return None, True
    return None, False


def assist_from_model(data: Any, *, action: str, schema: dict[str, Any], standin: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Suggestions that fit the action and the form being edited (ids are made here; unknown ids are dropped)."""
    data = _dict(data)
    if "suggestions" not in data and any(isinstance(data.get(k), list) for k in ("add_fields", "set_help", "add_rules", "fixes")):
        data = {"suggestions": [
            *({"kind": "add_field", **x} for x in _list(data.get("add_fields")) if isinstance(x, dict)),
            *({"kind": "set_help", **x} for x in _list(data.get("set_help")) if isinstance(x, dict)),
            *({"kind": "add_rule", "rule": x} for x in _list(data.get("add_rules")) if isinstance(x, dict)),
            *({"kind": "fix", **x} for x in _list(data.get("fixes")) if isinstance(x, dict)),
        ]}
    if not isinstance(data.get("suggestions"), list):
        raise OutputInvalid("no_suggestions")
    fields = all_fields(schema)
    by_id = {f["id"]: f for f in fields}
    pages = {p["id"] for p in schema["pages"]}
    out: list[dict[str, Any]] = []
    for raw in data["suggestions"][:20]:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("kind")
        if action == "fields" and kind == "add_field":
            seed = _seed(raw.get("field"))
            if not seed or not is_input(seed["type"]) or seed["type"] == "calculated" \
                    or any(similar(f.get("label") or "", seed["label"]) for f in fields) \
                    or any(similar(s["field"]["label"], seed["label"]) for s in out):
                continue
            seed.pop("key", None)
            page_id = raw.get("page_id") if raw.get("page_id") in pages else schema["pages"][-1]["id"]
            after = raw.get("after_id") if raw.get("after_id") in by_id else (fields[-1]["id"] if fields else None)
            from app.modules.ai.engine_builder import ai_field_id

            out.append({"id": suggestion_id(), "kind": "add_field", "field": field_from(seed, ai_field_id),
                        "page_id": page_id, "after_id": after, "note": {"code": "common"}})
        elif action == "help" and kind == "set_help":
            field = by_id.get(raw.get("field_id"))
            help_ = _text(raw.get("help"), 300)
            if field and is_input(field["type"]) and help_ and not js.trim(field.get("help") or "") \
                    and all(s["field_id"] != field["id"] for s in out):
                out.append({"id": suggestion_id(), "kind": "set_help", "field_id": field["id"], "label": field["label"],
                            "help": help_})
        elif action == "logic" and kind == "add_rule" and isinstance(raw.get("rule"), dict):
            rule = raw["rule"]
            shaped = {"when": {"any" if rule.get("match") == "any" else "all":
                               [{"field": c.get("field_id"), "op": c.get("op"),
                                 "value": c["values"] if "values" in c else c.get("value")}
                                for c in _list(rule.get("when")) if isinstance(c, dict)]},
                      "then": [{"action": e.get("action"), "target": e.get("target_id")}
                               for e in _list(rule.get("then")) if isinstance(e, dict)]}
            clean = clean_rule(shaped, schema, ai_rule_id())
            if not clean:
                continue
            first = by_id[next(iter(clean["when"].values()))[0]["field"]]
            target = by_id.get(clean["then"][0].get("target") or "")
            code = "low_rating" if first["type"] in ("rating", "scale") else "other_option" if first["type"] in ("radio", "dropdown") \
                else "follow_up"
            out.append({"id": suggestion_id(), "kind": "add_rule", "rule": clean,
                        "note": {"code": code, "params": {"field": target["label"] if target else "", "after": first["label"]}}})
        elif action == "check" and kind == "fix" and raw.get("problem") in AI_PROBLEMS:
            problem = raw["problem"]
            field = by_id.get(raw.get("field_id")) if raw.get("field_id") else None
            if problem != "long_page" and field is None:
                continue
            patch, remove = _patch_for(problem, field, _text(raw.get("text"), 500))
            if problem == "long_label" and patch is None:
                continue
            label = field["label"] if field else next((p.get("title") or "" for p in schema["pages"]
                                                       if p["id"] == raw.get("page_id")), "")
            out.append({"id": suggestion_id(), "kind": "fix", "field_id": field["id"] if field else None, "label": label,
                        "problem": problem, "patch": patch, **({"remove": True} if remove else {})})
    if action == "check":
        # The built-in checks are certain; the model's add what they can't see
        found = standin()
        known = {(s["field_id"], s["problem"]) for s in found}
        found.extend(s for s in out if (s["field_id"], s["problem"]) not in known)
        return found
    return out[:8]


# ── Writing ───────────────────────────────────────────────────────────────────

_TAG = re.compile(r"<[^>]+>")


def translation_ok(original: str, kind: str, translation: Any) -> str | None:
    """A translation that keeps the text's markup exactly (rich text) or adds none (plain text)."""
    if not isinstance(translation, str) or not js.trim(translation) or len(translation) > 50_000:
        return None
    if kind == "html":
        return translation if _TAG.findall(original) == _TAG.findall(translation) else None
    if _TAG.search(translation) and not _TAG.search(original):
        return None
    return translation


def translations_from_model(data: Any, wanted: dict[str, dict[str, Any]]) -> dict[str, str]:
    """{key: translation} for the keys asked (`wanted`: key → item); anything else is ignored."""
    data = _dict(data)
    out: dict[str, str] = {}
    for item in _list(data.get("items")):
        if isinstance(item, dict) and item.get("key") in wanted and item["key"] not in out:
            ok = translation_ok(wanted[item["key"]]["text"], wanted[item["key"]]["kind"], item.get("translation"))
            if ok:
                out[item["key"]] = ok
    return out


def rewrites_from_model(data: Any, texts: dict[str, str]) -> list[dict[str, Any]]:
    data = _dict(data)
    out = []
    seen: set[str] = set()
    for item in _list(data.get("items")):
        if not isinstance(item, dict) or item.get("key") not in texts or item["key"] in seen:
            continue
        original = texts[item["key"]]
        new = _text(item.get("rewrite"), 50_000)
        if not new or new == original or _TAG.search(new) or len(new) > 2 * len(original) + 200:
            continue
        reasons = [r for r in dict.fromkeys(_list(item.get("reasons"))) if r in AI_REWRITE_REASONS] or ["plain_words"]
        seen.add(item["key"])
        out.append({"key": item["key"], "text": original, "rewrite": new, "reasons": reasons})
    return out


# ── Reading responses ─────────────────────────────────────────────────────────

def labels_from_model(data: Any, count: int) -> dict[int, tuple[str, list[str]]]:
    data = _dict(data)
    out: dict[int, tuple[str, list[str]]] = {}
    for item in _list(data.get("labels")):
        if not isinstance(item, dict) or not isinstance(item.get("i"), int) or not 0 <= item["i"] < count:
            continue
        mood = item.get("sentiment") if item.get("sentiment") in ("positive", "neutral", "negative") else None
        if mood is None:
            continue
        themes = [t for t in dict.fromkeys(_list(item.get("themes"))) if t in AI_THEMES and t != "other"]
        out[item["i"]] = (mood, themes or ["other"])
    return out


def plan_from_model(data: Any, fields: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """The model's reading of a question, kept to the form's questions and real dates; Formalie counts."""
    data = _dict(data)
    kind = data.get("kind")
    if kind not in ("count", "top", "average", "trend"):
        raise OutputInvalid("kind")
    by_key = {f["key"]: f for f in fields}
    field = by_key.get(data.get("field_key") or "")
    numeric = field is not None and (field["type"] in AN.RATING or field["type"] in ("number", "currency", "percentage"))
    if kind == "average" and not numeric:
        field = None
    if kind == "trend" and not numeric:
        field = None
    if kind == "top" and (field is None or not (field.get("options") or field["type"] in AN.CHOICE)):
        field = None
    period = None
    raw = data.get("period")
    if isinstance(raw, dict):
        try:
            start, end = date.fromisoformat(str(raw.get("from"))[:10]), date.fromisoformat(str(raw.get("to"))[:10])
        except ValueError:
            start = end = None  # type: ignore[assignment]
        if start and end:
            end = min(end, today)
            if start <= end:
                period = {"from": AN.day_ms(start.isoformat()), "to": AN.day_ms(end.isoformat()),
                          "label": _text(raw.get("label"), 40) or f"{start.isoformat()} to {end.isoformat()}"}
    answer = None
    raw_answer = data.get("answer")
    if kind != "top" and isinstance(raw_answer, dict) and raw_answer.get("field_key") in by_key:
        options = by_key[raw_answer["field_key"]].get("options") or []
        if any(o.get("value") == raw_answer.get("value") for o in options):
            answer = {"field_key": raw_answer["field_key"], "value": raw_answer["value"]}
    status = data.get("status") if data.get("status") in AN.STATUSES else None
    bucket = data.get("bucket") if data.get("bucket") in ("day", "week", "month") else "month"
    return {"kind": kind, "field_key": field["key"] if field else None, "period": period, "status": status,
            "answer": answer, "bucket": bucket if kind == "trend" else None, "guessed": False}


def summary_from_model(data: Any, fields: list[dict[str, Any]], answers: dict[str, Any],
                       mask: Callable[[str], str]) -> dict[str, Any]:
    data = _dict(data)
    by_key = {f["key"]: f for f in fields}
    points = []
    for item in _list(data.get("points")):
        if len(points) >= 6:
            break
        if not isinstance(item, dict) or item.get("field_key") not in by_key \
                or any(p["key"] == item["field_key"] for p in points):
            continue
        field = by_key[item["field_key"]]
        # Dates, ratings and choices as they were answered; written answers in the model's words
        value = AN.point_text(field, answers[field["key"]]) if field["type"] not in ("long_text", "short_text", "rich_text") \
            else _text(item.get("value"), 300)
        if value:
            points.append({"key": field["key"], "label": field["label"], "value": mask(value)})
    if not points:
        raise OutputInvalid("no_points")
    mood = data.get("sentiment") if data.get("sentiment") in ("positive", "neutral", "negative") else None
    themes = [t for t in dict.fromkeys(_list(data.get("themes"))) if t in AI_THEMES and t != "other"]
    return {"points": [{"label": p["label"], "value": p["value"]} for p in points], "sentiment": mood, "themes": themes}


def draft_stats(schema: dict[str, Any]) -> dict[str, int]:
    return schema_stats(schema)

"""The stand-in's help in the builder: port of the mock's server/mock/ai/builderEngine.ts (no outside service).

  fields  questions the form is likely missing (from the closest Formalie template, plus common ones)
  help    short help texts for questions that have none, by kind of question
  logic   follow-ups: details after a yes, "what went wrong" after a low rating, "other" after Other
  check   problems: the wrong kind of field for what is asked, duplicates, images without a description, very long
          questions, nothing required, choices with too few options, long pages

Each result is a suggestion the builder applies or skips (AiSuggestion). Held to the mock's answers by
tests/parity/test_ai_engines.py (ids are random in both).
"""

from __future__ import annotations

import re
import secrets
from typing import Any, Callable

from app.core import js
from app.modules.ai.engine_forms import I, rank_templates, rx
from app.modules.ai.kit import all_fields, field_from, is_input, slug


def suggestion_id() -> str:
    return f"sg_{secrets.token_hex(4)}"


def ai_field_id() -> str:
    return f"fld_ai{secrets.token_hex(5)}"


def ai_rule_id() -> str:
    return f"rule_ai{secrets.token_hex(4)}"


def _norm(text: str) -> str:
    return slug(text).replace("_", " ")


def words_of(text: str) -> set[str]:
    return {w for w in _norm(text).split(" ") if len(w) > 2}


def similar(a: str, b: str) -> bool:
    """Two labels ask the same thing when most of their words match."""
    x, y = words_of(a), words_of(b)
    if not x or not y:
        return _norm(a) == _norm(b)
    return len(x & y) / min(len(x), len(y)) >= 0.6


_UNIQUE = {"full_name", "email", "phone", "signature", "consent", "address"}


def inputs(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in all_fields(schema) if is_input(f["type"]) and f["type"] not in ("hidden", "calculated")]


def _template_seed(field: dict[str, Any]) -> dict[str, Any]:
    """A template's question as a seed without its key (the builder gives it a clean key from its label)."""
    keep = ("type", "label", "required", "help", "placeholder", "readonly", "options", "validation", "default")
    seed = {k: field[k] for k in keep if k in field}
    if isinstance(field.get("props"), dict):
        seed["props"] = field["props"]
    return seed


def suggest_fields(schema: dict[str, Any], name: str) -> list[dict[str, Any]]:
    present = inputs(schema)
    last_page = schema["pages"][-1]
    every = all_fields(schema)
    last_field = every[-1]["id"] if every else None
    out: list[dict[str, Any]] = []

    def has(seed: dict[str, Any]) -> bool:
        return any((seed["type"] in _UNIQUE and f["type"] == seed["type"]) or similar(f["label"], seed["label"])
                   for f in present) \
            or any(s["kind"] == "add_field" and similar(s["field"]["label"], seed["label"]) for s in out)

    def add(seed: dict[str, Any], note: dict[str, Any]) -> None:
        out.append({"id": suggestion_id(), "kind": "add_field", "field": field_from(seed, ai_field_id),
                    "page_id": last_page["id"], "after_id": last_field, "note": note})

    # The form's name decides the closest template (its questions' words alone mislead)
    ranked = rank_templates(name)
    match = ranked[0] if ranked and ranked[0]["score"] >= 3 else None
    if match:
        template = match["template"]
        for field in all_fields(template["schema"]):
            if len(out) >= 5 or not is_input(field["type"]) or field["type"] in ("calculated", "hidden") or has(field):
                continue
            add(_template_seed(field), {"code": "from_template", "params": {"name": template["name"]}})
    personal = any(f["type"] in ("email", "phone", "address", "full_name") for f in present)
    common: list[dict[str, Any]] = []
    if not any(f["type"] == "email" for f in present) and any(f["type"] == "full_name" for f in present):
        common.append({"type": "email", "label": "Email address", "required": True})
    common.append({"type": "long_text", "label": "Anything else you would like to tell us?"})
    for seed in common:
        if not has(seed):
            add(seed, {"code": "common"})
    consent = {"type": "consent", "label": "I agree to my details being used to handle this request", "required": True}
    if personal and not has(consent):
        add(consent, {"code": "consent"})
    return out


def _num(value: Any, fallback: float) -> str:
    n = js.to_number(value) if value is not None else float("nan")
    return js.number_to_string(n if n and not js.is_nan(n) else fallback)


HELP: dict[str, Callable[[dict[str, Any]], str]] = {
    "email": lambda f: "We only use this to reply to you.",
    "phone": lambda f: "Include the country code, for example +44 7700 900123.",
    "date": lambda f: "As shown on your ID." if re.search("birth", f["label"], I) else "Pick the date from the calendar.",
    "datetime": lambda f: "Pick the date, then the time.",
    "date_range": lambda f: "Pick the first day, then the last.",
    "time": lambda f: "Use the time where you are.",
    "file_upload": lambda f: f"PDF, Word or images, up to {_num((f.get('props') or {}).get('max_mb'), 10)} MB.",
    "image_upload": lambda f: f"A clear photo, up to {_num((f.get('props') or {}).get('max_mb'), 10)} MB.",
    "signature": lambda f: "Sign with your finger, mouse or pen.",
    "long_text": lambda f: "A few sentences is enough.",
    "rating": lambda f: f"1 is poor, {_num((f.get('props') or {}).get('max'), 5)} is excellent.",
    "scale": lambda f: f"{_num((f.get('props') or {}).get('min'), 0)} is the lowest, "
                       f"{_num((f.get('props') or {}).get('max'), 10)} the highest.",
    "currency": lambda f: "Numbers only, without the currency sign.",
    "number": lambda f: "Numbers only.",
    "address": lambda f: "Where we can reach you by post.",
    "checkbox": lambda f: "Choose all that apply.",
    "multi_select": lambda f: "Choose all that apply.",
    "ranking": lambda f: "Drag to put them in order, most important first.",
    "url": lambda f: "The full address, starting with https://",
}
_REFERENCE = rx(r"\b(id|number|reference|code)\b", I)


def help_texts(schema: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for field in inputs(schema):
        if js.trim(field.get("help") or ""):
            continue
        make = HELP.get(field["type"]) or ((lambda f: "You can find it on your letter or email from us.")
                                           if _REFERENCE.search(field["label"]) else None)
        if make:
            out.append({"id": suggestion_id(), "kind": "set_help", "field_id": field["id"], "label": field["label"],
                        "help": make(field)})
    return out


_FOLLOW_UP = rx(r"\b(details?|describe|explain|which|if yes|if so|specify|tell us more|please give|reason)\b", I)
_OTHER = rx(r"^other\b", I)


def logic_rules(schema: dict[str, Any]) -> list[dict[str, Any]]:
    fields = all_fields(schema)
    targeted = {e.get("target") for rule in schema.get("logic") or [] if isinstance(rule, dict)
                for e in rule.get("then") or [] if isinstance(e, dict)}
    out: list[dict[str, Any]] = []

    def rule(field: dict[str, Any], op: str, value: Any, target: dict[str, Any]) -> dict[str, Any]:
        return {"id": ai_rule_id(), "when": {"all": [{"field": field["id"], "op": op, "value": value}]},
                "then": [{"action": "show", "target": target["id"]}]}
    for i in range(len(fields) - 1):
        field, nxt = fields[i], fields[i + 1]
        if nxt["id"] in targeted or not is_input(nxt["type"]):
            continue
        follow_up = bool(_FOLLOW_UP.search(nxt["label"])) or any(len(w) > 3 and w in words_of(nxt["label"])
                                                                  for w in words_of(field["label"]))
        if field["type"] == "toggle" and nxt["type"] in ("long_text", "short_text", "file_upload") and follow_up:
            out.append({"id": suggestion_id(), "kind": "add_rule", "rule": rule(field, "true", None, nxt),
                        "note": {"code": "follow_up", "params": {"field": nxt["label"], "after": field["label"]}}})
        elif field["type"] in ("rating", "scale") and nxt["type"] == "long_text":
            out.append({"id": suggestion_id(), "kind": "add_rule",
                        "rule": rule(field, "lte", 2 if field["type"] == "rating" else 6, nxt),
                        "note": {"code": "low_rating", "params": {"field": nxt["label"], "after": field["label"]}}})
        elif field["type"] in ("radio", "dropdown") and nxt["type"] == "short_text":
            other = next((o for o in field.get("options") or [] if _OTHER.search(o.get("label") or "")), None)
            if other:
                out.append({"id": suggestion_id(), "kind": "add_rule", "rule": rule(field, "eq", other["value"], nxt),
                            "note": {"code": "other_option", "params": {"field": nxt["label"], "after": field["label"]}}})
    return out


_CHOICES = ("radio", "dropdown", "checkbox", "multi_select", "ranking")


def check(schema: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def fix(field: dict[str, Any] | None, problem: str, patch: dict[str, Any] | None, remove: bool = False) -> None:
        out.append({"id": suggestion_id(), "kind": "fix", "field_id": field["id"] if field else None,
                    "label": field["label"] if field else "", "problem": problem, "patch": patch,
                    **({"remove": True} if remove else {})})
    seen: list[dict[str, Any]] = []
    for field in all_fields(schema):
        text = field["type"] == "short_text"
        label = field.get("label") or ""
        if text and rx(r"\be-?mail\b", I).search(label):
            fix(field, "email_type", {"type": "email"})
        elif text and rx(r"\b(phone|mobile|telephone)\b", I).search(label):
            fix(field, "phone_type", {"type": "phone"})
        elif text and rx(r"\b(date|birthday|dob)\b", I).search(label):
            fix(field, "date_type", {"type": "date"})
        elif text and rx(r"\b(how many|number of|quantity|age)\b", I).search(label):
            fix(field, "number_type", {"type": "number"})
        props = field.get("props") if isinstance(field.get("props"), dict) else None
        if field["type"] == "image" and not js.trim(js.to_string((props or {}).get("alt") or "")):
            fix(field, "image_alt", {"props": {**(props or {}), "alt": label or "Image"}})
        if is_input(field["type"]) and not js.trim(label):
            fix(field, "no_label", None)
        if js.utf16_len(label) > 120:
            first, *rest = re.split(r"(?<=[.?!])\s+", label)
            fix(field, "long_label", {"label": first, "help": " ".join(p for p in [" ".join(rest), field.get("help")] if p)}
                if rest else None)
        options = field.get("options")
        if (len(options) if options is not None else 2) < 2 and field["type"] in _CHOICES:
            fix(field, "few_options", None)
        if is_input(field["type"]) and js.trim(label) and any(_norm(o.get("label") or "") == _norm(label)
                                                               and o["type"] == field["type"] for o in seen):
            fix(field, "duplicate", None, True)
        seen.append(field)
    askable = inputs(schema)
    if askable and not any(f.get("required") for f in askable):
        first = next((f for f in askable if f["type"] in ("full_name", "email")), askable[0])
        fix(first, "no_required", {"required": True})
    for page in schema["pages"]:
        if sum(len(row["fields"]) for row in page["rows"]) > 12:
            out.append({"id": suggestion_id(), "kind": "fix", "field_id": None, "label": page.get("title") or "",
                        "problem": "long_page", "patch": None})
    return out


def assist_form(action: str, schema: dict[str, Any], name: str) -> list[dict[str, Any]]:
    if action == "fields":
        return suggest_fields(schema, name)
    if action == "help":
        return help_texts(schema)
    if action == "logic":
        return logic_rules(schema)
    return check(schema)

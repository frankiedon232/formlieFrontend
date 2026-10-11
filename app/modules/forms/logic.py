"""Form logic, auto-fill from list details and lists with levels (port of shared/utils/forms/logic.ts, fills.ts and
cascade.ts), one evaluator for the public form and the API, held to the frontend's answers by
tests/parity/test_submission_rules.py.

Rules: { id, when: { all | any: [{ field, op, value?, value2?, detail? }] }, then: [{ action, target?, value? }] }.
Conditions test answers by field id; actions show / hide fields and pages, require / make optional, enable /
disable, set / clear a value, jump to a page or to the end.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from app.core import js
from app.modules.forms.formula import detail_answer

END_OF_FORM = "__end__"
MAX_LIST_LEVELS = 4
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}", re.ASCII)


@dataclass
class LogicState:
    hidden: set[str] = field(default_factory=set)
    hidden_pages: set[str] = field(default_factory=set)
    required: set[str] = field(default_factory=set)
    optional: set[str] = field(default_factory=set)
    disabled: set[str] = field(default_factory=set)
    enabled: set[str] = field(default_factory=set)
    values: dict[str, Any] = field(default_factory=dict)  # field id → value (None = clear); last rule wins
    jumps: dict[str, str] = field(default_factory=dict)  # page id → next page id or END_OF_FORM; first rule wins


def is_empty(value: Any) -> bool:
    if js.nullish(value) or value == "" or value is False:
        return True
    if isinstance(value, list):
        return not value
    if isinstance(value, dict):
        return not any(not js.nullish(v) and v != "" for v in value.values())
    return False


def _to_number(value: Any) -> float:
    return math.nan if js.nullish(value) or value == "" else js.to_number(value)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [js.to_string(v) for v in value]
    return [] if js.nullish(value) or value == "" else [js.to_string(value)]


def _test(condition: dict[str, Any], answer: Any) -> bool:
    op = condition.get("op")
    value, value2 = condition.get("value", js.UNDEFINED), condition.get("value2", js.UNDEFINED)
    if op == "empty":
        return is_empty(answer)
    if op == "not_empty":
        return not is_empty(answer)
    if op == "true":
        return answer is True
    if op == "false":
        return answer is not True

    if isinstance(answer, list):
        chosen = [js.to_string(a) for a in answer]
        wanted = _list(value)
        if op in ("contains", "eq"):
            return js.to_string(value) in chosen
        if op in ("not_contains", "neq"):
            return js.to_string(value) not in chosen
        if op == "in":
            return any(w in chosen for w in wanted)
        if op == "not_in":
            return not any(w in chosen for w in wanted)
        if op == "contains_all":
            return bool(wanted) and all(w in chosen for w in wanted)
        if op == "count_gte":
            return len(chosen) >= js.to_number(value)
        if op == "count_lte":
            return len(chosen) <= js.to_number(value)
        return False
    if op == "in":
        return js.to_string("" if js.nullish(answer) else answer) in _list(value)
    if op == "not_in":
        return js.to_string("" if js.nullish(answer) else answer) not in _list(value)

    if op in ("before", "after"):
        if not isinstance(answer, str) or not answer or not _truthy(value):
            return False
        other = js.to_string(value)
        return js.js_less(answer, other) if op == "before" else js.js_less(other, answer)

    if op in ("gt", "gte", "lt", "lte", "between", "not_between"):
        is_date = isinstance(answer, str) and bool(_ISO_DATE.match(answer))
        if is_empty(answer):
            return False
        if op in ("between", "not_between"):
            if is_date:
                text = js.to_string(answer)
                inside = (not _truthy(value) or not js.js_less(text, js.to_string(value))) and \
                         (not _truthy(value2) or not js.js_less(js.to_string(value2), text))
            else:
                a = _to_number(answer)
                inside = (js.nullish(value) or value == "" or a >= _to_number(value)) and \
                         (js.nullish(value2) or value2 == "" or a <= _to_number(value2))
            return inside if op == "between" else not inside
        a, b = _to_number(answer), _to_number(value)
        if math.isnan(a) or math.isnan(b):
            return False
        return a > b if op == "gt" else a >= b if op == "gte" else a < b if op == "lt" else a <= b

    text = "" if js.nullish(answer) else js.to_string(answer).lower()
    expected = "" if js.nullish(value) else js.to_string(value).lower()
    if op == "contains":
        return expected in text
    if op == "not_contains":
        return expected not in text
    if op == "starts_with":
        return text.startswith(expected)
    if op == "ends_with":
        return text.endswith(expected)
    if op == "eq":
        return text == expected
    if op == "neq":
        return text != expected
    return False


def _truthy(value: Any) -> bool:
    """JavaScript truthiness of a condition value (string, number, list, null)."""
    if js.nullish(value) or value is False or value == "":
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0 and not math.isnan(value)
    return True


def rule_matches(rule: dict[str, Any], answers: dict[str, Any], fields: dict[str, dict[str, Any]],
                 picked: dict[str, Any] | None = None) -> bool:
    def check(condition: dict[str, Any]) -> bool:
        fld = fields.get(condition.get("field"))  # type: ignore[arg-type]
        if fld is None:
            return False
        answer = answers.get(fld["key"], js.UNDEFINED)
        if condition.get("detail"):
            return _test(condition, detail_answer(fld, answer, condition["detail"], picked))
        return _test(condition, answer)
    when = rule.get("when") or {}
    if when.get("any"):
        return any(check(c) for c in when["any"])
    if when.get("all"):
        return all(check(c) for c in when["all"])
    return False


def evaluate_logic(schema: dict[str, Any], answers: dict[str, Any], picked: dict[str, Any] | None = None) -> LogicState:
    """The current effect of all rules. "show" hides its target until the rule matches; "hide" while it matches.
    Jumps apply on the page that holds the rule's first condition field."""
    fields: dict[str, dict[str, Any]] = {}
    page_of: dict[str, str] = {}
    for page in schema.get("pages", []):
        for row in page.get("rows", []):
            for fld in row.get("fields", []):
                fields[fld["id"]] = fld
                page_of[fld["id"]] = page["id"]
    state = LogicState()
    for rule in schema.get("logic") or []:
        match = rule_matches(rule, answers, fields, picked)
        for effect in rule.get("then") or []:
            target = effect.get("target") or ""
            action = effect.get("action")
            if action == "show" and not match:
                state.hidden.add(target)
            elif action == "hide" and match:
                state.hidden.add(target)
            elif action == "show_page" and not match:
                state.hidden_pages.add(target)
            elif action == "hide_page" and match:
                state.hidden_pages.add(target)
            elif action == "require" and match:
                state.required.add(target)
            elif action == "unrequire" and match:
                state.optional.add(target)
            elif action == "enable" and match:
                state.enabled.add(target)
            elif action == "disable" and match:
                state.disabled.add(target)
            elif action == "set_value" and match:
                value = effect.get("value", js.UNDEFINED)
                state.values[target] = None if js.nullish(value) else value
            elif action == "clear_value" and match:
                state.values[target] = None
            elif action in ("jump", "skip_to_end") and match:
                when = rule.get("when") or {}
                first = (when.get("all") or [None])[0] or (when.get("any") or [None])[0]
                origin = page_of.get(first.get("field")) if first else None
                if origin and origin not in state.jumps:
                    state.jumps[origin] = target if action == "jump" else END_OF_FORM
    apply_fills(state, list(fields.values()), answers, picked)
    return state


# ── Auto-fill from list details (fills.ts) ──────────────────────────────────────

def fills_of(fld: dict[str, Any]) -> list[dict[str, Any]]:
    raw = (fld.get("props") or {}).get("fills")
    if not isinstance(raw, list):
        return []
    return [f for f in raw if isinstance(f, dict) and isinstance(f.get("column"), str) and isinstance(f.get("target"), str)]


def _value_for(target: dict[str, Any], attr: Any) -> Any:
    if target.get("type") in ("number", "currency", "percentage", "slider"):
        n = float(attr) if isinstance(attr, (int, float)) and not isinstance(attr, bool) \
            else js.to_number(js.to_string(attr).replace(",", ".", 1))
        return n if math.isfinite(n) else js.to_string(attr)
    return js.to_string(attr)


def apply_fills(state: LogicState, fields: list[dict[str, Any]], answers: dict[str, Any],
                picked: dict[str, Any] | None = None) -> None:
    by_id = {f["id"]: f for f in fields}
    for source in fields:
        fills = fills_of(source)
        if not fills:
            continue
        options = source.get("options") or list((picked or {}).get(source["id"], []))
        chosen = answers.get(source.get("key"), js.UNDEFINED)
        option = next((o for o in options if o.get("value") == chosen), None) if isinstance(chosen, str) else None
        for fill in fills:
            target = by_id.get(fill["target"])
            if target is None or target["id"] == source["id"]:
                continue
            attr = ((option or {}).get("attrs") or {}).get(fill["column"], js.UNDEFINED) if option else js.UNDEFINED
            value = None if attr is js.UNDEFINED or attr == "" else _value_for(target, attr)
            if fill.get("lock"):
                state.disabled.add(target["id"])
                state.enabled.discard(target["id"])
                state.values[target["id"]] = value
                continue
            current = answers.get(target.get("key"), js.UNDEFINED)
            filled = {js.to_string(a) for o in options
                      for a in [((o.get("attrs") or {}).get(fill["column"], js.UNDEFINED))]
                      if a is not js.UNDEFINED and a != ""}
            untouched = js.nullish(current) or current == "" or js.to_string(current) in filled
            if untouched and (value is not None or js.to_string(current) in filled):
                state.values[target["id"]] = value


# ── Lists with levels (cascade.ts) ──────────────────────────────────────────────

def _remote_level(fld: dict[str, Any]) -> bool:
    return bool(fld.get("options_large")) and not fld.get("options")


def _chosen(value: Any) -> list[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return [value] if isinstance(value, str) and value else []


def cascade_options(fld: dict[str, Any], by_id: dict[str, dict[str, Any]], answers: dict[str, Any],
                    depth: int = 0) -> list[dict[str, Any]]:
    options = fld.get("options") or []
    if not fld.get("option_parent") or depth > MAX_LIST_LEVELS:
        return options
    parent = by_id.get(fld["option_parent"])
    if parent is None:
        return options
    if cascade_closed(parent, by_id, answers, depth + 1):
        return []
    above = _chosen(answers.get(parent.get("key"), js.UNDEFINED))
    return [o for o in options if "parent" in o and o["parent"] in above] if above else []


def cascade_closed(fld: dict[str, Any], by_id: dict[str, dict[str, Any]], answers: dict[str, Any], depth: int = 0) -> bool:
    if not fld.get("option_parent") or depth > MAX_LIST_LEVELS:
        return False
    if not _remote_level(fld):
        return len(cascade_options(fld, by_id, answers, depth)) == 0
    parent = by_id.get(fld["option_parent"])
    if parent is None:
        return False
    if cascade_closed(parent, by_id, answers, depth + 1):
        return True
    above = _chosen(answers.get(parent.get("key"), js.UNDEFINED))
    known = (fld.get("options_large") or {}).get("parents")
    if not known:
        return not above
    open_ = set(known)
    return not any(v in open_ for v in above)


def fit_answer(fld: dict[str, Any], by_id: dict[str, dict[str, Any]], answers: dict[str, Any]) -> Any:
    """The answer kept to what the field offers now (UNDEFINED: dropped)."""
    value = answers.get(fld.get("key"), js.UNDEFINED)
    if not fld.get("option_parent") or js.nullish(value) or _remote_level(fld):
        return value
    allowed = {o.get("value") for o in cascade_options(fld, by_id, answers)}
    if isinstance(value, list):
        kept = [v for v in value if isinstance(v, str) and v in allowed]
        return value if len(kept) == len(value) else kept if kept else js.UNDEFINED
    return value if isinstance(value, str) and value in allowed else js.UNDEFINED

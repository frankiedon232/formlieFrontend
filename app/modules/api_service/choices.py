"""Choice answers in the public API (port of shared/utils/apiService/choices.ts, owner 2026-10-08), held to the
frontend's answers by tests/parity/test_api_rules.py. Answers are stored as option values (codes that never change);
the API speaks labels:
- out (GET, records, examples): each chosen value becomes its option's label;
- in (POST, PUT, GET filters): a label or a value is accepted; labels become values before the form's own checks.
  A label used by two options of one level (a city name under two regions) is settled by the choice one level up.
"""

from __future__ import annotations

from typing import Any

from app.modules.api_service.access import js_trim


def _label_of(options: list[dict[str, Any]], value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return next((o["label"] for o in options if o.get("value") == value), value)


def choice_out(field: dict[str, Any], value: Any) -> Any:
    """A stored answer as the API returns it: option labels instead of values."""
    options = field.get("options") or []
    if not options or value is None:
        return value
    return [_label_of(options, v) for v in value] if isinstance(value, list) else _label_of(options, value)


def _value_of(options: list[dict[str, Any]], item: Any, above: list[str] | None) -> Any:
    """One sent item → its option value (a value as is, else the option with that label), or the item unchanged."""
    if not isinstance(item, str):
        return item
    if any(o.get("value") == item for o in options):
        return item
    wanted = js_trim(item).lower()
    matches = [o for o in options if js_trim(str(o.get("label", ""))).lower() == wanted]
    if len(matches) > 1 and above:
        pick = next((o for o in matches if o.get("parent") is not None and o["parent"] in above), matches[0])
    else:
        pick = matches[0] if matches else None
    return pick["value"] if pick is not None else item


def _js_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def choices_in(fields: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    """Sent answers with labels turned into values, for every question with options. `fields` in form order, so a
    level's choice above is already a value when the level is read."""
    out = dict(answers)
    key_of_id = {f["id"]: f["key"] for f in fields if f.get("id")}
    for field in fields:
        options = field.get("options") or []
        if not options or out.get(field["key"]) is None:
            continue
        parent_key = key_of_id.get(field["option_parent"]) if field.get("option_parent") else None
        raw = out.get(parent_key) if parent_key else None
        above: list[str] | None = None
        if parent_key:
            above = [_js_string(v) for v in raw] if isinstance(raw, list) else [_js_string(raw)] if raw is not None else []
        value = out[field["key"]]
        out[field["key"]] = [_value_of(options, v, above) for v in value] if isinstance(value, list) \
            else _value_of(options, value, above)
    return out


def choice_filter(field: dict[str, Any], wanted: str) -> str:
    """A GET filter's wanted text → the option value it names (label or value), else the text."""
    value = _value_of(field.get("options") or [], wanted, None)
    return value if isinstance(value, str) else wanted

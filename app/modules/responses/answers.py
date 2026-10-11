"""Answers after they arrive (ports of shared/utils/forms/answer-edit.ts, answer-filter.ts and answer-text.ts, and
the mock's keepAnswered), held to the frontend's answers by tests/parity/test_responses_rules.py: which answers a
team member may change, filtering by answer, and an answer as plain text for titles and export files.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from app.core import js
from app.modules.public.submit import all_fields, is_input_field

_LOCKED = {"file_upload", "image_upload", "signature", "payment", "calculated", "hidden"}
_CHOICES = {"dropdown", "radio", "checkbox", "multi_select"}
ANSWER_FILTER_PREFIX = "a_"
EN_WORDS = {"yes": "Yes", "no": "No", "agreed": "Agreed"}


def can_edit_answer(fld: dict[str, Any]) -> bool:
    """Files, signatures and payments are evidence; calculated and hidden values follow from others."""
    return is_input_field(fld.get("type", "")) and fld.get("type") not in _LOCKED


# ── Filtering by answer ─────────────────────────────────────────────────────────

def filter_values(fld: dict[str, Any]) -> list[str] | None:
    """The values a question can be filtered on, or None when it gets no filter of its own."""
    kind = fld.get("type")
    if kind in _CHOICES:
        options = fld.get("options") or []
        return [o["value"] for o in options] if options else None
    if kind == "toggle":
        return ["true", "false"]
    if kind in ("rating", "scale"):
        props = fld.get("props") or {}
        low = 1.0 if kind == "rating" else js.to_number(0 if js.nullish(props.get("min", js.UNDEFINED)) else props["min"])
        raw_max = props.get("max", js.UNDEFINED)
        high = js.to_number((5 if kind == "rating" else 10) if js.nullish(raw_max) else raw_max)
        if high - low <= 10 and high >= low:
            return [js.number_to_string(low + i) for i in range(int(high - low) + 1)]
        return None
    return None


def answer_values(value: Any) -> list[str]:
    if js.nullish(value) or value == "":
        return []
    return [js.to_string(v) for v in value] if isinstance(value, list) else [js.to_string(value)]


def answer_matches(value: Any, wanted: list[str]) -> bool:
    return any(v in wanted for v in answer_values(value))


def is_empty_answer(value: Any) -> bool:
    return not answer_values(value) or (isinstance(value, dict) and all(js.nullish(v) or v == "" for v in value.values()))


# ── An answer as plain text (export files, titles) ──────────────────────────────

def _js_truthy(value: Any) -> bool:
    if js.nullish(value) or value is False or value == "" or value == 0:
        return False
    return not (isinstance(value, float) and value != value)


def answer_text(fld: dict[str, Any] | None, value: Any, words: dict[str, str] | None = None) -> str:
    words = words or EN_WORDS
    if js.nullish(value) or value == "" or (isinstance(value, list) and not value):
        return ""
    options = {o.get("value"): o.get("label") for o in ((fld or {}).get("options") or [])}

    def label(v: Any) -> str:
        text = js.to_string(v)
        found = options.get(text, js.UNDEFINED)
        return text if js.nullish(found) else js.to_string(found)
    obj = value if isinstance(value, dict) else {}
    kind = (fld or {}).get("type")
    if kind in ("checkbox", "multi_select"):
        return "; ".join(label(v) for v in (value if isinstance(value, list) else [value]))
    if kind in ("radio", "dropdown"):
        return label(value)
    if kind == "ranking":
        return "; ".join(f"{i + 1}. {label(v)}" for i, v in enumerate(value if isinstance(value, list) else []))
    if kind == "matrix":
        return "; ".join(f"{row}: {label(v)}" for row, v in obj.items())
    if kind == "toggle":
        return words["yes"] if value is True or value == "true" else words["no"]
    if kind == "consent":
        return words["agreed"] if _js_truthy(value) else ""
    if kind == "date_range":
        return " / ".join(js.to_string(v) for v in (obj.get("from"), obj.get("to")) if _js_truthy(v))
    if kind == "duration":
        def number(part: str) -> str:
            raw = obj.get(part, js.UNDEFINED)
            return js.number_to_string(js.to_number(0 if js.nullish(raw) else raw))
        return f"{number('hours')}h {number('minutes')}m"
    if kind == "full_name":
        return " ".join(js.to_string(obj.get(k)) for k in ("title", "first", "middle", "last") if _js_truthy(obj.get(k)))
    if kind == "address":
        return ", ".join(js.to_string(obj.get(k)) for k in ("line1", "line2", "city", "region", "postal_code", "country")
                         if _js_truthy(obj.get(k)))
    if kind in ("file_upload", "image_upload"):
        names = []
        for f in (value if isinstance(value, list) else []):
            if isinstance(f, (dict, list)) and f is not None:
                raw = f.get("name", js.UNDEFINED) if isinstance(f, dict) else js.UNDEFINED
                names.append("" if js.nullish(raw) else js.to_string(raw))
            else:
                names.append(js.to_string(f))
        return "; ".join(n for n in names if n)
    if kind == "signature":
        return words["agreed"]
    if kind == "rich_text":
        return js.trim(re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", js.to_string(value))))
    if isinstance(value, list):
        return "; ".join(js.to_string(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(js.to_string(v) for v in obj.values() if not js.nullish(v) and v != "")
    return js.to_string(value)


# ── Long lists in a response's form (largeLists.ts keepAnswered) ────────────────

def keep_answered(schema: dict[str, Any] | None, answers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fields of lists kept on the server carry only the options that were answered (`options_large.partial`), so
    labels read as usual without sending the whole list."""
    if not schema or not any(f.get("options_large") for f in all_fields(schema)):
        return schema
    out = copy.deepcopy(schema)
    for fld in all_fields(out):
        if not fld.get("options_large"):
            continue
        used: set[str] = set()
        for data in answers:
            value = data.get(fld["key"], js.UNDEFINED)
            for item in (value if isinstance(value, list) else [value]):
                if isinstance(item, str):
                    used.add(item)
        options = fld.get("options") or []
        total = (fld["options_large"] or {}).get("total")
        fld["options"] = [o for o in options if o.get("value") in used]
        fld["options_large"] = {"total": total if not js.nullish(total) else len(options), "partial": True}
    return out

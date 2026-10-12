"""Endpoint rules (port of shared/utils/apiService/endpoints.ts, F13), held to the frontend's answers by
tests/parity/test_api_rules.py: which questions an endpoint may accept, filter on and return, the defaults for a new
endpoint, the API names, the name check, the example request / record and what a new form version changes for apps.
Values in examples are neutral and made up.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any

from app.modules.api_service.access import js_trim
from app.modules.api_service.choices import choice_out
from app.modules.api_service.labels import icon_from_label, key_from_label

API_PAGE_SIZE_MAX = 100
# Layout blocks are not questions.
LAYOUT_TYPES = ["section", "paragraph", "divider", "image"]
# Never sent through the API: signatures, calculated values, payments. Files are uploaded first (`…/files`).
NOT_ACCEPTED_TYPES = ["signature", "calculated", "payment"]
# Questions a GET list can be narrowed by.
FILTER_TYPES = ["short_text", "email", "phone", "number", "currency", "percentage", "date", "datetime", "dropdown",
                "radio", "multi_select", "checkbox", "toggle", "consent", "rating", "scale", "slider", "country",
                "language", "hidden"]
# Paths the API service uses itself.
RESERVED_ENDPOINT_NAMES = ["token", "files", "docs", "health", "status", "openapi", "webhooks"]
# Words an API name can not be: they are the record's own fields and the list options.
RESERVED_API_NAMES = ["id", "submitted_at", "status", "data", "meta", "page", "per_page", "sort", "error"]
ENDPOINT_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,62}[a-z0-9])")
_API_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MARKS = re.compile("[̀-ͯ]")


def all_fields(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not schema:
        return []
    return [f for page in schema.get("pages", []) for row in page.get("rows", []) for f in row.get("fields", [])]


def is_acceptable(field: dict[str, Any]) -> bool:
    """Can be sent through the API: not read-only, disabled, calculated, a signature or a payment."""
    return not field.get("readonly") and not field.get("disabled") and field.get("type") not in NOT_ACCEPTED_TYPES


def check_api_name(name: str) -> str | None:
    """An API name: lower-case letters, digits and underscores, starting with a letter, up to 64."""
    if not js_trim(name):
        return "required"
    if not _API_NAME.fullmatch(name):
        return "pattern"
    return "reserved" if name in RESERVED_API_NAMES else None


def endpoint_fields_of(schema: dict[str, Any], saved: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """One question as an endpoint field (ApiEndpointField), with the defaults for a new endpoint. API names: the saved
    one when it is valid and free, else a clean one from the label (first_name, first_name_2)."""
    by_key = {item["key"]: item for item in (saved or [])}
    taken: list[str] = []
    page_of: dict[Any, int] = {}
    for index, page in enumerate(schema.get("pages", [])):
        for row in page.get("rows", []):
            for f in row.get("fields", []):
                page_of[f.get("id")] = index
    fields = all_fields(schema)
    key_of_id = {f.get("id"): f.get("key") for f in fields}
    out: list[dict[str, Any]] = []
    for field in fields:
        if field.get("type") in LAYOUT_TYPES:
            continue
        acceptable = is_acceptable(field)
        filterable = field.get("type") in FILTER_TYPES
        form_required = bool(field.get("required")) and acceptable
        own = by_key.get(field.get("key"))
        accept = acceptable and (form_required or (bool(own["accept"]) if own else True))
        own_name = own.get("name") if own else None
        kept = own_name if own_name and not check_api_name(own_name) and own_name not in taken else None
        label = field.get("label")
        name = kept or key_from_label(js_trim(label or "") or field.get("key") or "", [*taken, *RESERVED_API_NAMES])
        taken.append(name)
        item: dict[str, Any] = {
            "key": field.get("key"), "name": name, "label": label, "type": field.get("type"),
            "page": page_of.get(field.get("id"), 0), "form_required": form_required, "acceptable": acceptable,
            "filterable": filterable, "accept": accept,
            "required": accept and (form_required or bool(own and own.get("required"))),
            "returned": bool(own["returned"]) if own else True,
            "filter": filterable and bool(own and own.get("filter")),
        }
        options = field.get("options") or []
        large = field.get("options_large")
        if options:
            shown = options[:20] if large else options
            item["options"] = [{"value": o.get("value"), "label": o.get("label"), **({"parent": o["parent"]} if o.get("parent") else {})}
                               for o in shown]
        if large:
            item["options_total"] = len(field["options"]) if field.get("options") is not None else large.get("total")
        parent = field.get("option_parent")
        if parent and key_of_id.get(parent):
            item["depends_on"] = key_of_id[parent]
        out.append(item)
    return out


def not_accepted_reason(field: dict[str, Any]) -> str | None:
    """Why a field can't be sent, for the hint beside it (None = it can)."""
    if field.get("acceptable"):
        return None
    if field.get("type") in ("signature", "calculated", "payment"):
        return field["type"]
    return "locked"


def check_endpoint_name(name: str) -> str | None:
    """Problems with an endpoint name: `required`, `pattern` (lower-case words and hyphens, 3 to 64) or `reserved`."""
    if not name:
        return "required"
    if not ENDPOINT_PATTERN.fullmatch(name) or "--" in name:
        return "pattern"
    return "reserved" if name in RESERVED_ENDPOINT_NAMES else None


def endpoint_name_from(text: str) -> str:
    """A suggested endpoint name from a form name (`Register account` → `register-account`)."""
    out = _MARKS.sub("", unicodedata.normalize("NFKD", text)).lower()
    out = re.sub(r"[^a-z0-9]+", "-", out)
    out = re.sub(r"^-+|-+$", "", out)[:64]
    return re.sub(r"-+$", "", out)


def sample_for_label(field: dict[str, Any]) -> str | int | None:
    """An example text answer that fits the label ("First name" → Alex, "City" → a city)."""
    raw = (field.get("label") or field.get("key") or "").lower()
    text = f" {re.sub(r'[_-]+', ' ', raw)} "
    if re.search(r" (first|given) name ", text) or re.search(r"prénom|vorname|nombre ", text):
        return "Alex"
    if re.search(r" (last|family) name | surname ", text) or re.search(r"apellido|nachname", text):
        return "Morgan"
    return {
        "i-lucide-user": "Alex Morgan", "i-lucide-mail": "alex.morgan@example.com", "i-lucide-phone": "+44 7700 900123",
        "i-lucide-building-2": "Example Ltd", "i-lucide-briefcase": "Product designer",
        "i-lucide-map-pin": "1 Example Street", "i-lucide-building": "Sample City", "i-lucide-map": "Sample Region",
        "i-lucide-mailbox": "10115", "i-lucide-earth": "GB", "i-lucide-globe": "https://example.com",
        "i-lucide-link": "https://example.com", "i-lucide-cake": "1990-04-12", "i-lucide-banknote": 1250,
        "i-lucide-hash": 2, "i-lucide-hourglass": 34, "i-lucide-message-square": "A few sentences of text.",
        "i-lucide-tag": "General enquiry", "i-lucide-at-sign": "alexmorgan", "i-lucide-receipt": "INV-2026-0042",
        "i-lucide-id-card": "X1234567",
    }.get(icon_from_label(field.get("label"), field.get("key")) or "")


_FIXED: dict[str, Any] = {
    "email": "alex.morgan@example.com", "phone": "+44 7700 900123", "url": "https://example.com", "domain": "example.com",
    "slider": 42, "currency": 120.5, "percentage": 75, "full_name": {"first": "Alex", "last": "Morgan"},
    "time": "09:30", "datetime": "2026-10-06T09:30:00Z", "date_range": {"from": "2026-10-06", "to": "2026-10-10"},
    "duration": {"hours": 1, "minutes": 30}, "multi_select": ["option_1", "option_2"], "checkbox": ["option_1", "option_2"],
    "ranking": ["option_1", "option_2"], "dropdown": "option_1", "radio": "option_1", "toggle": True, "consent": True,
    "rating": 4, "scale": 4, "matrix": {"row_1": "column_2"},
    "address": {"line1": "1 Example Street", "city": "Sample City", "postal_code": "00000", "country": "GB"},
    "country": "GB", "language": "en", "timezone": "Europe/London", "iban": "GB33BUKB20201555555555", "bic": "DEUTDEFF",
    "currency_code": "EUR", "ip_address": "203.0.113.10", "mac_address": "00:1A:2B:3C:4D:5E", "color": "#1F2937",
    "file_upload": ["FILE_ID_FROM_FILES_UPLOAD"], "image_upload": ["FILE_ID_FROM_FILES_UPLOAD"], "signature": None,
    "long_text": "A few sentences of text.", "rich_text": "A few sentences of text.",
}


def sample_value(field: dict[str, Any]) -> Any:
    """A made-up value of the right shape for a question, for examples (the form's own answer values for choices)."""
    key = f"{field.get('key')} {field.get('label')}".lower()
    kind = field.get("type")
    values = [o.get("value") for o in (field.get("options") or [])]
    if values and kind in ("dropdown", "radio"):
        return values[0]
    if values and kind in ("multi_select", "checkbox", "ranking"):
        return values if kind == "ranking" else values[:2]
    if kind == "number":
        from_label = sample_for_label(field)
        return from_label if isinstance(from_label, int) else 42
    if kind == "date":
        return "1990-04-12" if sample_for_label(field) == "1990-04-12" else "2026-10-06"
    if kind in _FIXED:
        return copy.deepcopy(_FIXED[kind])
    from_label = sample_for_label(field)
    if isinstance(from_label, str):
        return from_label
    if re.search("name", key):
        return "Alex Morgan"
    return "Example Ltd" if re.search(r"company|organi[sz]ation", key) else "Some text"


def _sample_of(field: dict[str, Any]) -> Any:
    if field.get("depends_on") and not field.get("options"):
        return None
    return sample_value(field)


def with_level_samples(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Examples for lists with levels (F15 M2): each level's example takes only values under the example chosen one
    level up, so an example body is one the API accepts. A level prefers options with something under them all the
    way down; a level with nothing to offer has no options (its example is None)."""
    chosen: dict[str, Any] = {}
    by_key = {f["key"]: f for f in fields}
    child_of: dict[str, dict[str, Any]] = {}
    for f in fields:
        if f.get("depends_on"):
            child_of[f["depends_on"]] = f
    deep: dict[str, list[dict[str, Any]]] = {}

    def deep_of(field: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
        if field["key"] in deep:
            return deep[field["key"]]
        options = field.get("options") or []
        child = child_of.get(field["key"]) if depth < 5 else None
        if child:
            below = {o.get("parent") for o in deep_of(child, depth + 1)}
            leading = [o for o in options if o.get("value") in below]
            if leading:
                options = leading
        deep[field["key"]] = options
        return options

    narrowed: dict[str, dict[str, Any]] = {}

    def visit(field: dict[str, Any]) -> dict[str, Any]:
        if field["key"] in narrowed:
            return narrowed[field["key"]]
        result = {**field, "options": deep_of(field)} if field.get("options") else field
        parent = by_key.get(field["depends_on"]) if field.get("depends_on") else None
        if parent:
            visit(parent)
            above = chosen.get(parent["key"])
            values = above if isinstance(above, list) else [above] if above is not None else []

            def under(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
                return [o for o in items if o.get("parent") is not None and o["parent"] in values]

            leading = under(deep_of(field))
            result = {**field, "options": leading if leading else under(field.get("options") or [])}
        narrowed[field["key"]] = result
        chosen[field["key"]] = _sample_of(result)
        return result

    return [visit(f) for f in fields]


def _example_of(field: dict[str, Any]) -> Any:
    if field.get("depends_on") and not field.get("options"):
        return None
    return choice_out(field, sample_value(field))


def example_request_body(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """The JSON body a POST / PUT sends: every accepted field, in the form's order, choices as their labels."""
    return {f["name"]: _example_of(f) for f in with_level_samples(fields) if f.get("accept")}


def example_record(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """One record as GET returns it: the reference, when, its status and every returned field, in the form's order."""
    data = {}
    for f in with_level_samples(fields):
        if not f.get("returned"):
            continue
        data[f["name"]] = [{"id": "f_Hc71mQpZsA", "name": "document.pdf", "size": 20480, "type": "application/pdf"}] \
            if f.get("type") in ("file_upload", "image_upload") else _example_of(f)
    return {"id": "rsp_9fK2mQ7xLp", "submitted_at": "2026-10-06T09:30:00Z", "status": "new", "data": data}


def api_changes(live: list[dict[str, Any]], draft: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """What publishing a new version changes for apps calling endpoints that follow the latest version: questions
    added, removed, and required that were not before. Label and design changes keep the keys, so change nothing."""
    def counts(f: dict[str, Any]) -> bool:
        return f.get("type") not in LAYOUT_TYPES and f.get("type") not in NOT_ACCEPTED_TYPES

    before = {f["key"]: f for f in live if counts(f)}
    after = [f for f in draft if f.get("key") and counts(f)]
    keys = {f["key"] for f in after}
    return {
        "added": [{"key": f["key"], "label": f.get("label") if f.get("label") is not None else f["key"],
                   "required": bool(f.get("required"))} for f in after if f["key"] not in before],
        "removed": [{"key": f["key"], "label": f.get("label")} for f in before.values() if f["key"] not in keys],
        "nowRequired": [{"key": f["key"], "label": f.get("label") if f.get("label") is not None else f["key"]}
                        for f in after if f.get("required") and f["key"] in before and not before[f["key"]].get("required")
                        and not f.get("readonly") and not f.get("disabled")],
    }

"""A whole submission, checked the way the form page checks it page by page (port of
shared/utils/forms/submission.ts), so a changed or hand-made request can't skip a required question or slip in a
value the form doesn't have:

- only pages on the respondent's path count (hidden pages and jumped-over pages are skipped);
- hidden, read-only, disabled and restricted fields are never required;
- calculated fields are worked out again from the answers (the client's values are ignored);
- answers for unknown fields are dropped.

Held to the frontend's answers by tests/parity/test_submission_rules.py.
"""

from __future__ import annotations

from typing import Any

from app.core import js
from app.modules.forms.answers import validate_answer
from app.modules.forms.catalogues import FIELD_TYPES
from app.modules.forms.formula import calculate_result
from app.modules.forms.logic import END_OF_FORM, LogicState, cascade_closed, evaluate_logic, fit_answer


def all_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for p in schema.get("pages", []) for r in p.get("rows", []) for f in r.get("fields", [])]


def is_input_field(kind: str) -> bool:
    return bool((FIELD_TYPES.get(kind) or {}).get("input"))


def is_locked(fld: dict[str, Any]) -> bool:
    return bool(fld.get("readonly")) or bool(fld.get("disabled"))


def is_restricted(fld: dict[str, Any]) -> bool:
    audience = fld.get("audience")
    return bool(audience) and audience.get("mode") != "everyone"


def cannot_be_required(fld: dict[str, Any]) -> bool:
    return is_locked(fld) or is_restricted(fld) or fld.get("type") == "hidden"


def effective_field(fld: dict[str, Any], logic: LogicState) -> dict[str, Any]:
    """The field as respondents get it right now (logic can disable / enable it and change "required")."""
    disabled = True if fld["id"] in logic.disabled else False if fld["id"] in logic.enabled else fld.get("disabled")
    wanted = False if fld["id"] in logic.optional else bool(fld.get("required")) or fld["id"] in logic.required
    required = wanted and not cannot_be_required({**fld, "disabled": disabled})
    return {**fld, "disabled": disabled, "required": required}


def next_page_index(schema: dict[str, Any], logic: LogicState, index: int) -> int:
    pages = schema.get("pages", [])
    page = pages[index] if 0 <= index < len(pages) else None
    jump = logic.jumps.get(page["id"]) if page else None
    if jump == END_OF_FORM:
        return -1
    target = next((i for i, p in enumerate(pages) if p["id"] == jump), -1) if jump else -1
    start = target if target > index else index + 1
    return next((i for i, p in enumerate(pages) if i >= start and p["id"] not in logic.hidden_pages), -1)


def path_pages(schema: dict[str, Any], logic: LogicState) -> list[int]:
    """Pages a respondent passes through with these answers."""
    pages = schema.get("pages", [])
    path: list[int] = []
    index = next((i for i, p in enumerate(pages) if p["id"] not in logic.hidden_pages), -1)
    while index >= 0 and index not in path:
        path.append(index)
        index = next_page_index(schema, logic, index)
    return path


def settle_answers(schema: dict[str, Any], given: dict[str, Any]) -> dict[str, Any]:
    """Answers with calculated fields worked out again (and logic's "set value" applied)."""
    fields = all_fields(schema)
    by_key = {f["key"]: f for f in fields}
    answers: dict[str, Any] = {}
    for fld in fields:
        if is_input_field(fld["type"]) and fld["key"] in given:
            answers[fld["key"]] = given[fld["key"]]
    for _ in range(2):  # set values and calculations can depend on each other once
        logic = evaluate_logic(schema, answers)
        for field_id, value in logic.values.items():
            fld = next((f for f in fields if f["id"] == field_id), None)
            if fld:
                answers[fld["key"]] = value
        for fld in fields:
            if fld["type"] == "calculated":
                formula = (fld.get("props") or {}).get("formula", js.UNDEFINED)
                answers[fld["key"]] = calculate_result("" if js.nullish(formula) else js.to_string(formula), answers, by_key)
    return answers


def check_submission(schema: dict[str, Any], given: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every problem with a submission (empty when it can be stored) and the answers to store."""
    settled = settle_answers(schema, given)
    by_id = {f["id"]: f for f in all_fields(schema)}
    dropped: set[str] = set()
    for fld in by_id.values():
        if not fld.get("option_parent"):
            continue
        fitted = fit_answer(fld, by_id, settled)
        if fitted is js.UNDEFINED:
            dropped.add(fld["key"])
        settled[fld["key"]] = fitted
    answers = {k: v for k, v in settled.items() if k not in dropped}
    logic = evaluate_logic(schema, answers)
    issues: list[dict[str, Any]] = []
    for index in path_pages(schema, logic):
        for row in schema["pages"][index].get("rows", []):
            for raw in row.get("fields", []):
                if raw["id"] in logic.hidden or cascade_closed(raw, by_id, answers):
                    continue
                fld = effective_field(raw, logic)
                if not is_input_field(fld["type"]) or fld["type"] in ("hidden", "calculated") or is_locked(fld):
                    continue
                issue = validate_answer(fld, answers.get(fld["key"], js.UNDEFINED), bool(fld.get("required")))
                if issue:
                    issues.append({"key": fld["key"], **issue})
    return issues, answers

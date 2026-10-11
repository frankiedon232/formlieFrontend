"""Submission rules give the frontend's own answers (tests/vectors/submission_rules.json, recorded by
scripts/dump_submission_rules.py): whole submissions on every system template and on hand-made forms, formulas,
logic conditions, single answers, time zones and the proof of work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core import js
from app.modules.forms import answers as A
from app.modules.forms.formula import calculate_result
from app.modules.forms.logic import evaluate_logic, rule_matches
from app.modules.public.pow import check_work, has_leading_zero_bits
from app.modules.public.submit import check_submission
from app.modules.templates import catalogue

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "submission_rules.json").read_text(encoding="utf-8"))
SCHEMAS = {t["key"]: t["schema"] for t in catalogue.system_templates()}


def _same(a: object, b: object) -> bool:
    """JSON equality where 7 == 7.0 (Python keeps floats), nothing else loosened."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b, strict=True))
    return a == b


@pytest.mark.parametrize("case", RULES["submissions"], ids=lambda c: c["template"])
def test_template_submissions(case: dict) -> None:
    issues, answers = check_submission(SCHEMAS[case["template"]], case["answers"])
    assert _same(issues, case["result"]["issues"]), (issues, case["result"]["issues"])
    assert _same(answers, case["result"]["answers"]), (answers, case["result"]["answers"])


@pytest.mark.parametrize("case", RULES["custom"], ids=lambda c: json.dumps(c["answers"])[:60])
def test_handmade_submissions(case: dict) -> None:
    issues, answers = check_submission(case["schema"], case["answers"])
    assert _same(issues, case["result"]["issues"]), (issues, case["result"]["issues"])
    assert _same(answers, case["result"]["answers"])
    state = evaluate_logic(case["schema"], case["answers"])
    expected = case["logic"]
    assert sorted(state.hidden) == expected["hidden"] and sorted(state.hidden_pages) == expected["hiddenPages"]
    assert sorted(state.required) == expected["required"] and sorted(state.optional) == expected["optional"]
    assert sorted(state.disabled) == expected["disabled"] and sorted(state.enabled) == expected["enabled"]
    assert _same(state.values, expected["values"]) and state.jumps == expected["jumps"]


FIELDS = {
    "size": {"id": "s", "key": "size", "type": "radio", "options": [{"value": "s", "label": "Small", "score": 1},
                                                                     {"value": "l", "label": "Large", "score": 3}]},
    "extras": {"id": "e", "key": "extras", "type": "checkbox", "options": [{"value": "a", "label": "A", "score": 2},
                                                                           {"value": "b", "label": "B", "score": 5}]},
    "tags": {"id": "t", "key": "tags", "type": "checkbox", "options": [{"value": "x", "label": "X"}, {"value": "y", "label": "Y"}]},
    "plan": {"id": "p", "key": "plan", "type": "dropdown", "options": [{"value": "premium", "label": "Premium"},
                                                                       {"value": "10", "label": "Ten"}]},
    "product": {"id": "pr", "key": "product", "type": "multi_select", "options": [
        {"value": "desk", "label": "Desk", "attrs": {"price": 420, "region": "North"}},
        {"value": "lamp", "label": "Lamp", "attrs": {"price": "32,5", "region": "South"}},
        {"value": "pen", "label": "Pen", "attrs": {"region": ""}}]},
}


@pytest.mark.parametrize("case", RULES["formulas"], ids=lambda c: f"{c['formula']}#{c['set']}")
def test_formulas(case: dict) -> None:
    result = calculate_result(case["formula"], RULES["answer_sets"][case["set"]], FIELDS)
    assert _same(result, case["result"]), (result, case["result"])


DETAIL_FIELD = {"id": "f", "key": "k", "type": "multi_select", "options": [
    {"value": "desk", "label": "Desk", "attrs": {"price": 420, "region": "North"}},
    {"value": "lamp", "label": "Lamp", "attrs": {"price": "32,5", "region": "South"}}]}


@pytest.mark.parametrize("case", RULES["conditions"], ids=lambda c: c["rule"]["when"].get("all", c["rule"]["when"].get("any"))[0]["op"])
def test_conditions(case: dict) -> None:
    fields = {"f": DETAIL_FIELD} if case.get("detailField") else {"f": {"id": "f", "key": "k", "type": "short_text"}}
    assert rule_matches(case["rule"], case["answers"], fields) is case["result"]


@pytest.mark.parametrize("case", RULES["validate"], ids=lambda c: f"{c['field']['type']}:{str(c['value'])[:20]}:{c['required']}")
def test_single_answers(case: dict) -> None:
    value = js.UNDEFINED if case["value"] == "__undefined__" else case["value"]
    result = A.validate_answer(case["field"], value, case["required"])
    assert _same(result, case["result"]), (result, case["result"])


@pytest.mark.parametrize("case", RULES["offsets"], ids=lambda c: c["value"])
def test_time_zone_offsets(case: dict) -> None:
    assert A.is_time_zone(case["value"]) is case["ok"]


@pytest.mark.parametrize("case", RULES["pow"], ids=lambda c: f"{c['salt'][:6]}:{c['nonce']}")
def test_proof_of_work(case: dict) -> None:
    digest = hashlib.sha256(f"{case['salt']}:{case['nonce']}".encode()).digest()
    assert [has_leading_zero_bits(digest, bits) for bits in (0, 1, 4, 8, 9, 12)] == case["bits"]
    assert check_work(case["salt"], 4, case["nonce"]) is case["bits"][2]

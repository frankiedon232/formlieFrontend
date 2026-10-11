"""Answer rules give the frontend's own answers (tests/vectors/responses_rules.json, recorded by
scripts/dump_responses_rules.py): editable answers, filter values, answer filters, answers as text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import js
from app.modules.responses import answers as A

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "responses_rules.json").read_text(encoding="utf-8"))
FIELDS = [None if f == "__undefined__" else f for f in RULES["fields"]]
VALUES = [js.UNDEFINED if v == "__undefined__" else v for v in RULES["values"]]


@pytest.mark.parametrize("case", RULES["text"], ids=lambda c: f"{c['f']}:{c['v']}")
def test_answer_text(case: dict) -> None:
    fld, value = FIELDS[case["f"]], VALUES[case["v"]]
    assert A.answer_text(fld, value) == case["text"]
    assert A.answer_text(fld, value, RULES["words"]) == case["fr"]


@pytest.mark.parametrize("case", RULES["filters"], ids=lambda c: str(c["f"]))
def test_filter_values_and_editing(case: dict) -> None:
    fld = FIELDS[case["f"]]
    if fld is None:
        return
    assert A.filter_values(fld) == case["values"]
    assert A.can_edit_answer(fld) is case["edit"]


def test_matches_and_empty() -> None:
    for case in RULES["matches"]:
        assert A.answer_matches(VALUES[case["v"]], RULES["wanted"][case["w"]]) is case["match"], case
    for case in RULES["empties"]:
        assert A.is_empty_answer(VALUES[case["v"]]) is case["empty"], case
        assert A.answer_values(VALUES[case["v"]]) == case["values"], case

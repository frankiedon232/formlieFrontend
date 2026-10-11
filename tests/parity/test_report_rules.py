"""The export report gives the frontend's own bytes (tests/vectors/report_rules.json, recorded by
scripts/dump_report_rules.py), with the workspace colour for files, readable ink and CSV cells."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.core import js
from app.modules.responses.exports import csv_cell
from app.modules.responses.report import appearance_ink, readable_on, response_report

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "report_rules.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", RULES["reports"], ids=lambda c: c["input"]["form"][:20])
def test_report_bytes(case: dict) -> None:
    i = case["input"]
    made = response_report(i["org"], i["form"], i["brand"], i["exportedBy"],
                           datetime.fromisoformat(i["exportedAt"].replace("Z", "+00:00")), i["scope"], i["counts"],
                           i["responses"])
    expected = base64.b64decode(case["pdf"])
    if made != expected:  # the first difference, readable
        at = next(n for n, (a, b) in enumerate(zip(made, expected, strict=False)) if a != b) if len(made) == len(expected) \
            else min(len(made), len(expected))
        raise AssertionError(f"differs at {at}: {made[max(0, at - 80):at + 80]!r}\nvs {expected[max(0, at - 80):at + 80]!r}")


def test_colours_and_cells() -> None:
    for case in RULES["inks"]:
        assert appearance_ink(case["appearance"], case["brand"]) == case["ink"], case
    for case in RULES["readable"]:
        assert readable_on(case["color"]) == case["on"], case
    for case in RULES["cells"]:
        value = js.UNDEFINED if case["value"] == "__undefined__" else case["value"]
        assert csv_cell(value) == case["cell"], case

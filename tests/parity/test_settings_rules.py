"""The settings rules give the frontend's own answers (tests/vectors/settings_rules.json, recorded from
shared/utils/settings/schemas.ts by scripts/dump_settings_rules.py): accepted or not, the cleaned value, and every
problem's field and message; plus IP ranges, time zones and the audit change lines."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.net import ip_in_cidr, parse_cidr
from app.modules.settings import schemas
from app.modules.settings.changes import settings_changes

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "settings_rules.json").read_text(encoding="utf-8"))
CASES = [(name, i, case) for name, cases in RULES["schemas"].items() for i, case in enumerate(cases)]


@pytest.mark.parametrize(("name", "index", "case"), CASES, ids=[f"{n}-{i}" for n, i, _ in CASES])
def test_schema_answers_like_zod(name: str, index: int, case: dict) -> None:  # noqa: ARG001
    ok, result = schemas.SCHEMAS[name].safe_parse(case["input"])
    if case["ok"]:
        assert ok, result
        assert result == case["data"]
    else:
        assert not ok, result
        assert [(i["field"], i["message"]) for i in result] == [(i["path"], i["message"]) for i in case["issues"]]


@pytest.mark.parametrize("case", RULES["ip_ranges"], ids=lambda c: repr(c["value"]))
def test_ip_ranges(case: dict) -> None:
    assert (parse_cidr(case["value"]) is not None) == case["valid"]


@pytest.mark.parametrize("case", RULES["ip_matches"], ids=lambda c: f"{c['ip']} in {c['cidr']}")
def test_ip_matches(case: dict) -> None:
    assert ip_in_cidr(case["ip"], case["cidr"]) == case["match"]


@pytest.mark.parametrize("case", RULES["time_zones"], ids=lambda c: repr(c["value"]))
def test_time_zones(case: dict) -> None:
    assert schemas.is_time_zone(case["value"]) == case["valid"]


@pytest.mark.parametrize("case", RULES["settings_changes"], ids=lambda c: str(len(c["changes"])))
def test_settings_changes(case: dict) -> None:
    assert settings_changes(case["before"], case["after"]) == case["changes"]

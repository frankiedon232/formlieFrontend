"""Design rules give the frontend's own answers (tests/vectors/design_rules.json, recorded by
scripts/dump_design_rules.py): theme and page design validation, the default theme per branding, Formalie's
themes and page designs, theme patches."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.design import theme

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "design_rules.json").read_text(encoding="utf-8"))


def _check(schema, case: dict) -> None:  # noqa: ANN001
    ok, result = schema.safe_parse(case["input"])
    if case["ok"]:
        assert ok, result
        assert result == case["data"]
    else:
        assert not ok, result
        assert [(i["field"], i["message"]) for i in result] == [(i["path"], i["message"]) for i in case["issues"]]


@pytest.mark.parametrize("case", RULES["theme_cases"], ids=lambda c: str(c["ok"]))
def test_theme_tokens(case: dict) -> None:
    _check(theme.theme_schema, case)


@pytest.mark.parametrize("case", RULES["page_cases"], ids=lambda c: str(c["ok"]))
def test_page_design_tokens(case: dict) -> None:
    _check(theme.page_design_schema, case)


@pytest.mark.parametrize("entry", RULES["brandings"], ids=lambda e: str(e["branding"]))
def test_defaults_and_system_designs(entry: dict) -> None:
    b = entry["branding"]
    assert theme.default_theme(b["logo_url"], b["primary"]) == entry["default"]
    assert theme.system_themes(b["logo_url"], b["primary"]) == entry["themes"]
    assert theme.system_pages(b["logo_url"], b["primary"]) == entry["pages"]
    for item in entry["themes"]:
        assert theme.theme_schema.safe_parse(item["tokens"])[0], item["id"]


@pytest.mark.parametrize("case", RULES["patches"], ids=lambda c: json.dumps(c["patch"])[:30])
def test_patches(case: dict) -> None:
    assert theme.apply_patch(theme.default_theme(), case["patch"]) == case["result"]

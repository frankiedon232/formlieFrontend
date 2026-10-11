"""The forms rules give the frontend's own answers (tests/vectors/forms_rules.json, recorded by
scripts/dump_forms_rules.py): the FormSchema v1 validation, blank forms, slugs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.forms import schema as forms
from app.modules.forms.slugs import slugify

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "forms_rules.json").read_text(encoding="utf-8"))
CASES = list(enumerate(RULES["schema_cases"]))


def _not_web(case: dict) -> bool:
    """Ours takes web addresses only for the thank-you redirect (see app/modules/forms/schema.py)."""
    data = case["input"] if isinstance(case["input"], dict) else {}
    url = (data.get("thank_you") or {}).get("redirect_url") if isinstance(data.get("thank_you"), dict) else None
    return isinstance(url, str) and url.lower().startswith("javascript:")


@pytest.mark.parametrize(("index", "case"), CASES, ids=[str(i) for i, _ in CASES])
def test_form_schema_answers_like_zod(index: int, case: dict) -> None:  # noqa: ARG001
    ok, result = forms.form_schema_v1.safe_parse(case["input"])
    if _not_web(case):
        assert not ok and result == [{"field": "thank_you.redirect_url", "message": "Invalid URL"}]
        return
    if case["ok"]:
        assert ok, result
        assert result == case["data"]
    else:
        assert not ok, result
        assert [(i["field"], i["message"]) for i in result] == [(i["path"], i["message"]) for i in case["issues"]]


def test_count_fields() -> None:
    assert forms.count_fields(RULES["schema_cases"][0]["input"]) == RULES["count_fields"]


@pytest.mark.parametrize("language", sorted(RULES["blank_schemas"]))
def test_blank_forms(language: str) -> None:
    made = forms.blank_schema(language)
    page_id = made["pages"][0]["id"]
    assert page_id.startswith("pg_") and len(page_id) == 13
    made["pages"][0]["id"] = "__PAGE_ID__"
    assert made == RULES["blank_schemas"][language]
    assert forms.form_schema_v1.safe_parse(forms.blank_schema(language))[0]


@pytest.mark.parametrize("case", RULES["slugs"], ids=lambda c: c["slug"])
def test_slugs(case: dict) -> None:
    assert slugify(case["value"]) == case["slug"]

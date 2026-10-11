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


@pytest.mark.parametrize("case", RULES["publish_cases"], ids=lambda c: str(len(c["issues"])))
def test_publish_checks(case: dict) -> None:
    from app.modules.forms.builder import publish_issues

    assert publish_issues(case["schema"]) == case["issues"]


# ── Option lists (shared/utils/forms/options.ts) ────────────────────────────────

from app.modules.lists import rules as lists  # noqa: E402


@pytest.mark.parametrize("name", sorted(RULES["option_lists"]))
def test_list_levels_and_counts(name: str) -> None:
    lst = RULES["option_lists"][name]
    assert [lists.offered_options(lst, level) for level in (0, 1, 2)] == RULES["option_offered"][name]
    assert lists.level_counts(lst) == RULES["option_level_counts"][name]
    assert lists.kept_on_server(lst) == RULES["option_kept"][name]


@pytest.mark.parametrize("case", RULES["option_matches"], ids=lambda c: f"{c['list']}-{c['match']}")
def test_list_matches(case: dict) -> None:
    assert lists.matches_list(case["options"], RULES["option_lists"][case["list"]], case["level"]) == case["match"]


@pytest.mark.parametrize("case", RULES["option_lookups"], ids=lambda c: json.dumps(c["query"], ensure_ascii=True))
def test_list_lookups(case: dict) -> None:
    cities = lists.offered_options(RULES["option_lists"]["places"], 2)
    query = case["query"]
    got = lists.lookup_options(cities, q=query.get("q", ""), values=query.get("values"), parents=query.get("parents"))
    assert got == case["result"]


def test_list_values_and_hashes() -> None:
    for case in RULES["option_values"]:
        assert lists.value_from_label(case["label"]) == case["value"]
    for case in RULES["option_unique"]:
        assert lists.unique_value(case["wanted"], case["taken"]) == case["value"]
    for case in RULES["text_hashes"]:
        assert lists.text_hash(case["text"]) == case["hash"], case["text"]
    assert RULES["option_limits"] == {"LIVE_FROM": lists.LIVE_FROM, "MAX_OPTIONS": lists.MAX_OPTIONS,
                                      "SEARCH_FROM": lists.SEARCH_FROM, "LONG_FROM": lists.LONG_FROM}

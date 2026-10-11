"""Public-link rules give the frontend's own answers (tests/vectors/links_rules.json, recorded by
scripts/dump_links_rules.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.links import urls

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "links_rules.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", RULES["custom_links"], ids=lambda c: repr(c["value"]))
def test_custom_links(case: dict) -> None:
    assert urls.custom_link_problem(case["value"]) == case["problem"]
    assert urls.is_form_address(case["value"]) == case["address"]


@pytest.mark.parametrize("case", RULES["tidy"], ids=lambda c: repr(c["value"]))
def test_tidy(case: dict) -> None:
    assert urls.tidy_custom_link(case["value"]) == case["tidy"]


@pytest.mark.parametrize("case", RULES["addresses"], ids=lambda c: c["value"])
def test_addresses(case: dict) -> None:
    assert urls.is_form_address(case["value"]) == case["address"]
    assert bool(urls.FORM_KEY_PATTERN.fullmatch(case["value"])) == case["key"]


@pytest.mark.parametrize("case", RULES["short_codes"], ids=lambda c: c["value"])
def test_short_codes(case: dict) -> None:
    assert bool(urls.SHORT_CODE_PATTERN.fullmatch(case["value"])) == case["ok"]


def test_new_short_codes_match_the_pattern() -> None:
    assert all(urls.SHORT_CODE_PATTERN.fullmatch(urls.new_short_code()) for _ in range(200))


@pytest.mark.parametrize("case", RULES["embed_domains"], ids=lambda c: repr(c["value"]))
def test_embed_domains(case: dict) -> None:
    assert urls.normalise_embed_domain(case["value"]) == case["domain"]


@pytest.mark.parametrize("case", RULES["frame_ancestors"], ids=lambda c: ",".join(c["domains"]) or "none")
def test_frame_ancestors(case: dict) -> None:
    assert urls.frame_ancestors(case["domains"], "formalie.dev") == case["value"]


def test_lists() -> None:
    assert sorted(urls.RESERVED_LINKS) == RULES["reserved"]
    assert urls.MAX_EMBED_DOMAINS == RULES["max_embed_domains"]

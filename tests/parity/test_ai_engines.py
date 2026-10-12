"""The AI stand-in gives the mock's answers (tests/vectors/ai_rules.json, recorded by scripts/dump_ai_rules.py from the
mock's server/mock/ai/*): the question dictionary, form drafts, builder suggestions, designs from a colour, rewriting
and reading age, text labels, periods in questions, analyses, questions in plain words and response summaries."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from app.modules.ai import engine_analysis as AN
from app.modules.ai import engine_builder as B
from app.modules.ai import engine_forms as F
from app.modules.ai import engine_themes as T
from app.modules.ai import engine_writing as W
from app.modules.ai import kit

V = json.loads((Path(__file__).parents[1] / "vectors" / "ai_rules.json").read_text(encoding="utf-8"))
NOW = V["now"]


def plain(value: object) -> object:
    return json.loads(re.sub(r'"(sg|fld_ai|rule_ai)[0-9a-z_-]*"', r'"\1"', json.dumps(value)))


def test_question_dictionary() -> None:
    for case in V["phrases"]:
        assert F.clean_label(case["phrase"]) == case["clean"], case
        assert F.seed_for(case["phrase"]) == case["seed"], case


def test_titles_lists_and_ranking() -> None:
    for case in V["titles"]:
        assert F.title_from(case["prompt"], "Fallback") == case["title"], case["prompt"]
        assert F.listed_items(case["prompt"]) == case["items"], case["prompt"]
        ranked = [{"key": r["template"]["key"], "score": r["score"]} for r in F.rank_templates(case["prompt"])[:6]]
        assert ranked == case["ranked"], case["prompt"]
    for case in V["documents"]:
        assert F.document_questions(case["document"]) == case["pages"], case["document"]


@pytest.mark.parametrize("chunk", range(4))
def test_form_drafts(chunk: int) -> None:
    for case in V["drafts"][chunk::4]:
        got = F.draft_form(case["prompt"], case["document"], case["pages"], case["variant"])
        expected = case["schema"]
        if case["source"] == "template" and case["pages"] == "one" and (case["template_pages"] or 0) > 1:
            # One page: rules aimed at the template's other pages are dropped here (the mock keeps their titles)
            gone = {e.get("target") for rule in expected["logic"] for e in rule["then"]} - {
                f["id"] for f in kit.all_fields(expected)} - {"p1"}
            expected = copy.deepcopy(expected)
            expected["logic"] = [{**r, "then": [e for e in r["then"] if e.get("target") not in gone]} for r in expected["logic"]]
            expected["logic"] = [r for r in expected["logic"] if r["then"]]
        assert got["schema"] == expected, (case["prompt"], case["pages"], case["variant"])
        assert (got["name"], got["description"], got["notes"], got["based_on"], got["source"]) == \
            (case["name"], case["description"], case["notes"], case["based_on"], case["source"]), case["prompt"]


def test_builder_suggestions() -> None:
    for case in V["assists"]:
        got = plain(B.assist_form(case["action"], copy.deepcopy(V["schemas"][case["schema"]]), case["name"]))
        assert got == case["suggestions"], (case["schema"], case["name"], case["action"])


def test_designs_from_a_colour() -> None:
    for case in V["readables"]:
        assert T.readable(case["colour"]) == case["readable"]
        assert T.contrast(case["colour"], "#ffffff") == pytest.approx(case["contrast"])
    for case in V["themes"]:
        assert T.themes_from_colour(case["colour"], case["mood"], None) == case["suggestions"], case


def test_rewriting_and_reading_age() -> None:
    for case in V["rewrites"]:
        assert W.rewrite(case["text"], case["tone"], case["english"]) == case["out"], case
    for case in V["ages"]:
        assert W.reading_age(case["texts"]) == case["age"], case


def test_text_labels_and_periods() -> None:
    for case in V["labels"]:
        assert AN.themes_of(case["text"]) == case["themes"] and AN.sentiment_of(case["text"]) == case["sentiment"], case
    for case in V["periods"]:
        assert AN.period_in(case["q"], NOW) == case["period"], case


def _schema() -> dict:
    return V["form"]["schema"]


def test_analyses() -> None:
    form = {"id": V["form"]["id"], "name": V["form"]["name"]}
    for case in V["analyses"]:
        assert AN.analyse(form, _schema(), V["entries"], case["from"], case["to"], kit.mask_text) == case["masked"], case["from"]
        assert AN.analyse(form, _schema(), V["entries"], case["from"], case["to"], lambda t: t) == case["plain"], case["from"]


def test_questions() -> None:
    for case in V["asks"]:
        assert AN.ask(_schema(), V["entries"], case["question"], NOW) == case["answer"], case["question"]


def test_summaries_and_written_answers() -> None:
    by_id = {e["id"]: e for e in V["entries"]}
    fields = kit.all_fields(_schema())
    for case in V["summaries"]:
        data = by_id[case["id"]]["data"]
        assert AN.summarise(_schema(), data, kit.mask_text) == case["masked"], case["id"]
        assert AN.summarise(_schema(), data, lambda t: t) == case["plain"], case["id"]
    for case in V["written"]:
        assert AN.text_of(fields, by_id[case["id"]]["data"]) == case["texts"], case["id"]

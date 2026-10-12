"""The help centre's rules give the frontend's answers (tests/vectors/help_rules.json, recorded by
scripts/dump_help_rules.py): areas and their icons, article addresses, `routeMatches`, the mock's words and little
words, an article's text, search snippets and the short answer. The shipped help files match the frontend's."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.modules.help import rules as R
from app.modules.help.seed import DATA

V = json.loads((Path(__file__).parents[1] / "vectors" / "help_rules.json").read_text(encoding="utf-8"))
FILES = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in DATA.glob("*.json")}


def sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def article(lang: str, article_id: str) -> dict | None:
    """The mock's helpContent: the translation's words over English, English when not translated."""
    source = next((a for a in FILES["en"]["articles"] if a["id"] == article_id), None)
    if source is None:
        return None
    local = next((a for a in FILES.get(lang, {}).get("articles", []) if a["id"] == article_id), None) if lang != "en" else None
    return {**source, **({k: local[k] for k in ("title", "summary", "blocks")} if local else {}),
            "language": lang if local else "en"}


def summary_id(item: dict | None) -> dict | None:
    return item and {"article": item["article"]["id"], "blocks": item["blocks"]}


def test_categories_icons_and_paths() -> None:
    assert list(R.HELP_CATEGORIES) == V["categories"]
    assert R.HELP_CATEGORY_ICONS == V["icons"]
    for case in V["paths"]:
        assert R.help_article_path(case) == case["path"]


def test_route_matches() -> None:
    for case in V["route_matches"]:
        assert R.route_matches(case["pattern"], case["path"]) is case["match"], case


def test_words_and_little_words() -> None:
    assert set(R.STOP) == set(V["stop"])
    for case in V["words"]:
        assert R.words(case["text"]) == case["words"], case
    for search in V["searches"]:
        assert R.asked_words(R.words(search["q"])) == search["asked"], search["q"]


def test_search_terms_are_the_mock_words_in_plain_latin_text() -> None:
    for search in V["searches"]:
        if search["lang"] == "en":
            assert R.search_terms(search["q"]) == search["asked"], search["q"]
    assert R.search_terms("创建表单") == ["创建", "建表", "表单", "创建表单"]
    assert R.search_terms("أنشئ نموذجك") == ["أنشئ", "نموذجك"]  # whole words (the mock splits at the hamza)
    assert R.search_terms("फ़ॉर्म बनाएँ") == ["फ़ॉर्म", "बनाएँ"]
    assert R.search_terms("Créer un formulaire") == ["creer", "un", "formulaire"]
    assert R.search_terms("how do I") == ["how", "do"]


def test_article_text() -> None:
    for item in FILES["en"]["articles"]:
        assert R.article_text(item["blocks"]) == V["article_text_en"][item["id"]], item["id"]
    for lang, digest in V["article_text"].items():
        texts = [R.article_text(article(lang, a["id"])["blocks"]) for a in FILES["en"]["articles"]]  # type: ignore[index]
        assert sha(texts) == digest, lang


def test_snippets_of_the_mock_searches() -> None:
    for search in V["searches"]:
        for article_id, expected in search["articles"]:
            item = article(search["lang"], article_id)
            assert item is not None
            got = R.snippet(R.article_text(item["blocks"]), search["asked"], item["summary"])
            assert got == expected, (search["lang"], search["q"], article_id)


def test_answers() -> None:
    for case in V["answers_for"]:
        item = article(case["lang"], case["id"])
        got = R.answer_for(case["q"], case["asked"], item, {"id": item["id"]} if item else None)
        assert summary_id(got) == case["answer"], (case["lang"], case["q"], case["id"])
    for search in V["searches"]:
        best = article(search["lang"], search["articles"][0][0]) if search["articles"] else None
        got = R.answer_for(search["q"], search["asked"], best, {"id": best["id"]} if best else None)
        assert summary_id(got) == search["answer"], (search["lang"], search["q"])


def test_counts_of_the_shipped_files() -> None:
    assert set(FILES) == set(V["counts"])
    for lang, counts in V["counts"].items():
        data = FILES[lang]
        assert len(data["articles"]) == counts["translated"] and len(data["faqs"]) == counts["faqs"]
        assert len(data["glossary"]) == counts["glossary"] and len(data["tours"]) == counts["tours"]


def test_shipped_files_are_the_frontends(frontend_dir: Path) -> None:
    source = frontend_dir / "server" / "mock" / "data" / "help"
    stale = [p.name for p in source.glob("*.json") if not (DATA / p.name).exists()
             or (DATA / p.name).read_bytes() != p.read_bytes()]
    if stale:
        pytest.fail(f"Run scripts/sync_frontend_data.py, then scripts/seed_help.py: {stale}")

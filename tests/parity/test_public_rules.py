"""Public-page rules give the frontend's own answers (tests/vectors/public_rules.json, recorded by
scripts/dump_public_rules.py): identity, translations, long-list lookups, file types, resolved themes and the
answers' fingerprint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.design.theme import resolve_theme
from app.modules.public import rules as R
from app.modules.templates import catalogue

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "public_rules.json").read_text(encoding="utf-8"))
SCHEMAS = {t["key"]: t["schema"] for t in catalogue.system_templates()}
MANY = [{"value": f"v{i}", "label": f"Item {i}"} for i in range(120)]
IDENTITY_FORM = {"settings": {"identity": {"email": "email", "verify": False}}, "pages": [{"id": "p", "rows": [{"id": "r", "fields": [
    {"id": "a", "key": "email", "type": "email", "label": "Your email"},
    {"id": "b", "key": "first_name", "type": "short_text", "label": "First name"},
    {"id": "c", "key": "last_name", "type": "short_text", "label": "Last name"},
    {"id": "d", "key": "manager_name", "type": "short_text", "label": "Manager name"}]}]}]}
EARLIER = [
    {"id": "r1", "submitted_at": "2026-10-01T10:00:00.000Z",
     "data": {"email": "sarah.jones@example.org", "first_name": "Sarah", "last_name": "Jones"}},
    {"id": "r2", "submitted_at": "2026-10-02T10:00:00.000Z", "data": {"email": "mike@example.org", "first_name": "Mike", "last_name": "Brown"}},
]
CITIES = ["São Paulo", "Santos", "Sao Luis", "Nairobi", "Paris", "Saint-Denis", "Osaka", "Sakai", "Toronto", "Montréal"]
OPTIONS = [{"value": f"c{i}", "label": label, "parent": "br" if i < 3 else "other", **({"attrs": {"pop": i}} if i % 2 else {})}
           for i, label in enumerate(CITIES)]


@pytest.mark.parametrize("case", RULES["identities"], ids=lambda c: c["key"])
def test_identity_of_templates(case: dict) -> None:
    assert R.identity_of(SCHEMAS[case["key"]]) == case["identity"]


def test_identity_people() -> None:
    for case in RULES["stored_identity"]:
        assert R.identity_of({**IDENTITY_FORM, "settings": {"identity": case["identity"]}}) == case["result"]
    for case in RULES["emails"]:
        assert R.normalise_email(case["value"]) == case["email"], case
        assert R.mask_email(case["value"]) == case["mask"], case
    for case in RULES["names"]:
        assert R.normalise_name(case["value"]) == case["name"], case
    for case in RULES["similarity"]:
        assert R.name_similarity(case["a"], case["b"]) == pytest.approx(case["value"])
    for case in RULES["distance"]:
        assert R.edit_distance(case["a"], case["b"]) == case["value"]
    for case in RULES["matches"]:
        m = R.match_identity(IDENTITY_FORM, case["answers"], EARLIER)
        assert {"level": m["level"], "reason": m.get("reason"), "record": (m.get("record") or {}).get("id")} == case["result"]


@pytest.mark.parametrize("case", RULES["translations"], ids=lambda c: c["key"])
def test_translations(case: dict) -> None:
    schema = case["schema"]
    assert R.form_languages(schema) == case["languages"] and R.main_language(schema) == case["main"]
    for language in ("fr", "de", "en"):
        assert R.translate_schema(schema, language) == case[language], language


def test_long_lists() -> None:
    for case in RULES["lookups"]:
        q = case["query"]
        assert R.lookup_options(OPTIONS, q.get("q", ""), q.get("values"), q.get("parents")) == case["result"], q
    for case in RULES["many_lookups"]:
        assert R.lookup_options(MANY, case["query"]["q"]) == case["result"]
    for case in RULES["remote"]:
        fld = {**case["field"], "options": MANY[:case["field"]["options"]] if not case["many"] else MANY}
        if case["field"]["options"] == 0:
            fld["options"] = []
        assert R.served_remotely(fld) is case["result"], case


def test_file_types() -> None:
    for case in RULES["files"]:
        assert R.accepts_file(case["accept"], case["name"], case["type"]) is case["accepts"], case
    for case in RULES["pictures"]:
        assert R.picture_accept(case["accept"]) == case["picture"]
        assert R.parse_accept(case["accept"]) == case["parsed"]
        assert R.non_picture_types(case["accept"]) == case["non"]
    for case in RULES["looks"]:
        assert R.looks_like_picture(case["name"], case["type"]) is case["picture"], case


@pytest.mark.parametrize("case", RULES["themes"], ids=lambda c: f"{str(c['stored'])[:30]}#{c['branding']}")
def test_resolved_themes(case: dict) -> None:
    b = RULES["brandings"][case["branding"]]
    assert resolve_theme(case["stored"], b["logo_url"], b["primary"]) == case["result"]


@pytest.mark.parametrize("case", RULES["prints"], ids=lambda c: str(len(c["answers"])))
def test_fingerprints(case: dict) -> None:
    assert R.fingerprint_of(case["answers"]) == case["hash"]

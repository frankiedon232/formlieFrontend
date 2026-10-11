"""Formalie's templates in every language and branding give the frontend's own forms, byte for byte (fingerprints
in tests/vectors/templates_rules.json, recorded by scripts/dump_templates_rules.py), and so do the translation
dictionaries and moving a form's text to another language."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.modules.templates import catalogue

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "templates_rules.json").read_text(encoding="utf-8"))


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def test_every_template_in_every_language_and_branding() -> None:
    wrong = []
    for case in RULES["fingerprints"]:
        branding = RULES["brandings"][case["branding"]]
        made = catalogue.system_schema(catalogue.system_template(case["key"]), case["language"],
                                       branding["logo_url"], branding["primary"])
        if fingerprint(made) != case["hash"]:
            wrong.append((case["key"], case["language"], case["branding"]))
    assert not wrong, f"{len(wrong)} of {len(RULES['fingerprints'])} differ, e.g. {wrong[:5]}"


@pytest.mark.parametrize("code", sorted(RULES["dictionaries"]))
def test_translation_dictionaries(code: str) -> None:
    found = catalogue.translation_dict(code)
    assert (fingerprint(found) if found is not None else None) == RULES["dictionaries"][code]


@pytest.mark.parametrize("case", RULES["translate"], ids=lambda c: f"{c['from']}-{c['to']}")
def test_translate_content(case: dict) -> None:
    result = catalogue.translate_content(case["schema"], catalogue.translation_dict(case["from"]),
                                         catalogue.translation_dict(case["to"]))
    assert fingerprint(result["schema"]) == case["hash"]
    assert (result["translated"], result["kept"]) == (case["translated"], case["kept"])

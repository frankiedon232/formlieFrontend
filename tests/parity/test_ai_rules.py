"""The AI assistant's shared rules give the frontend's answers (tests/vectors/ai_rules.json, recorded by
scripts/dump_ai_rules.py): shared/types/ai.ts and shared/utils/ai/kinds.ts (kinds, statuses, sources, keep days,
actions, themes, tones, credits and permissions), the mock's maskText, and a form's texts (formTexts, staleKeys,
schemaStats) that translating and rewriting work on."""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.ai import kinds as K
from app.modules.ai import kit

V = json.loads((Path(__file__).parents[1] / "vectors" / "ai_rules.json").read_text(encoding="utf-8"))


def test_catalogue_and_credits() -> None:
    c = V["catalogue"]
    assert list(K.AI_KINDS) == c["kinds"] and list(K.AI_STATUSES) == c["statuses"]
    assert list(K.AI_SOURCES) == c["sources"] and list(K.AI_KEEP_DAYS) == c["keep_days"]
    assert list(K.AI_ASSIST_ACTIONS) == c["assist"] and list(K.AI_THEMES) == c["themes"] and list(K.AI_TONES) == c["tones"]
    assert K.AI_KIND_META == c["meta"] and K.AI_DEFAULT_MONTHLY_CREDITS == c["default_credits"]


def test_masking() -> None:
    for case in V["masks"]:
        assert kit.mask_text(case["text"]) == case["out"], case


def test_form_texts_stale_and_stats() -> None:
    t = V["translations"]
    assert kit.form_texts(t["schema"]) == t["texts"]
    assert kit.stale_keys(t["schema"], "fr") == set(t["stale"])
    assert kit.schema_stats(t["schema"]) == t["stats"]

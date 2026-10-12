"""The assistant's catalogue: port of the frontend's shared/types/ai.ts (kinds, statuses, sources, keep days, assist
actions, themes, tones, problems, note codes) and shared/utils/ai/kinds.ts (credits and permission per kind), held to
the frontend's answers by tests/parity/test_ai_rules.py."""

from __future__ import annotations

AI_KINDS = ("form", "template", "theme", "builder", "analysis", "question", "summary", "translate", "rewrite")
AI_STATUSES = ("proposed", "applied", "discarded", "failed")
AI_SOURCES = ("forms", "responses", "data")
AI_KEEP_DAYS = (30, 90, 180, 365)
AI_ASSIST_ACTIONS = ("fields", "help", "logic", "check")
AI_THEMES = ("speed", "ease", "staff", "price", "quality", "mobile", "communication", "scheduling", "location",
             "delivery", "other")
AI_TONES = ("plain", "friendly", "formal")
AI_PROBLEMS = ("email_type", "phone_type", "date_type", "number_type", "duplicate", "image_alt", "long_label",
               "no_required", "few_options", "long_page", "no_label")
AI_REWRITE_REASONS = ("plain_words", "long_sentence", "passive", "caps", "tone_friendly", "tone_formal")
AI_NOTE_CODES = ("follow_up", "total", "pages", "document_questions", "document_sections", "document_none",
                 "added_contact", "from_list", "template", "try_again", "basic", "themes", "low_rating", "other_option",
                 "from_template", "common", "consent", "assist_found", "assist_applied", "translated_total",
                 "rewrite_result", "busiest_day", "responses_up", "responses_down", "rating_up", "rating_down",
                 "theme_negative", "theme_positive", "no_text", "few_responses", "period_default", "field_guess",
                 "no_field", "no_answers")
AI_TITLE_CODES = ("analysis", "digest_week", "digest_month", "digest_quarter", "response_summary", "translate",
                  "rewrite", "theme", "assist_fields", "assist_help", "assist_logic", "assist_check")

# Icon, credits a request costs, the permission it needs and the page it belongs to (AI_KIND_META)
AI_KIND_META: dict[str, dict[str, object]] = {
    "form": {"icon": "i-lucide-file-plus-2", "credits": 5, "permission": "ai.create", "page": "/ai/create-form"},
    "template": {"icon": "i-lucide-layout-template", "credits": 5, "permission": "ai.create", "page": "/ai/templates"},
    "theme": {"icon": "i-lucide-palette", "credits": 2, "permission": "ai.create", "page": "/ai/templates"},
    "builder": {"icon": "i-lucide-wand-sparkles", "credits": 2, "permission": "ai.assist", "page": "/ai"},
    "analysis": {"icon": "i-lucide-chart-scatter", "credits": 8, "permission": "ai.analyse", "page": "/ai/analysis"},
    "question": {"icon": "i-lucide-message-circle-question", "credits": 3, "permission": "ai.analyse",
                 "page": "/ai/analysis"},
    "summary": {"icon": "i-lucide-lightbulb", "credits": 3, "permission": "ai.analyse", "page": "/ai/insights"},
    "translate": {"icon": "i-lucide-languages", "credits": 4, "permission": "ai.translate", "page": "/ai/translate"},
    "rewrite": {"icon": "i-lucide-pen-line", "credits": 1, "permission": "ai.translate", "page": "/ai/translate"},
}

# The monthly allowance until plans arrive (F24); a plan's own allowance wins (billing/plans.py `ai_credits`)
AI_DEFAULT_MONTHLY_CREDITS = 500


def credits_of(kind: str) -> int:
    return int(AI_KIND_META[kind]["credits"])  # type: ignore[call-overload]

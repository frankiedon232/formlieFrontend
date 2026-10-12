"""What the model is told (system prompts, stable so they are cached) and the JSON schema each answer must follow
(structured output: every object closed, every property listed; "nothing" is an empty string or list).

The prompts describe Formalie's rules; the answers are still checked and repaired by app/modules/ai/checks.py.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.core.locales import APP_LOCALE_CODES, APP_LOCALES
from app.modules.ai.kinds import AI_PROBLEMS, AI_REWRITE_REASONS, AI_THEMES
from app.modules.design.catalogues import TEMPLATE_CATEGORIES
from app.modules.forms.catalogues import FIELD_TYPES

# Field types the assistant may use (payments, hidden values, network addresses and images need a person)
MODEL_FIELD_TYPES = tuple(t for t in FIELD_TYPES if t not in ("payment", "hidden", "ip_address", "mac_address", "image",
                                                              "paragraph"))
LOGIC_OPERATORS = ("eq", "neq", "contains", "not_contains", "starts_with", "ends_with", "empty", "not_empty", "gt", "gte",
                   "lt", "lte", "between", "not_between", "in", "not_in", "contains_all", "count_gte", "count_lte",
                   "true", "false", "before", "after")
LOGIC_ACTIONS = ("show", "hide", "require", "unrequire", "enable", "disable", "set_value", "clear_value", "show_page",
                 "hide_page", "jump", "skip_to_end")
DRAFT_NOTES = ("follow_up", "total", "pages", "document_questions", "document_sections", "document_none",
               "added_contact", "from_list", "template", "try_again", "basic")
CATEGORY_KEYS = tuple(c["key"] for c in TEMPLATE_CATEGORIES)

COMMON = """You work inside Formalie, a form builder used by organisations of every size, anywhere in the world.
Write in plain, friendly, international English unless the request is in another language (then use that language).
Never use em dashes or spaced en dashes: use a comma, a colon or a full stop. Keep examples neutral (no country,
culture or real company); fictional phone numbers use the +44 7700 900xxx range. Promise controls, never
certifications. Answer only with JSON in the schema given."""


# ── JSON schema helpers ───────────────────────────────────────────────────────

def obj(**props: Any) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def arr(item: Any) -> dict[str, Any]:
    return {"type": "array", "items": item}


def enum(values: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


# No unions (anyOf, nullable types) anywhere: structured output limits them, so "nothing" is an empty string or list
S, B, INT = {"type": "string"}, {"type": "boolean"}, {"type": "integer"}
PARAMS = arr(obj(name=S, value=S))
PROP_NAMES = ("min", "max", "step", "min_label", "max_label", "format", "text")

SEED = obj(
    type=enum(MODEL_FIELD_TYPES), label=S, key=S, required=B, help=S, placeholder=S,
    options=arr(obj(value=S, label=S)), props=arr(obj(name=enum(PROP_NAMES), value=S)), rows=arr(S), formula=S,
)
RULE = obj(match=enum(("all", "any")),
           when=arr(obj(key=S, op=enum(LOGIC_OPERATORS), values=arr(S))),
           then=arr(obj(action=enum(LOGIC_ACTIONS), target=S, value=S)))

FORM_DRAFT = obj(
    name=S, description=S, language=enum(APP_LOCALE_CODES), source=enum(("list", "template", "basic", "document")),
    based_on=S, category=enum(CATEGORY_KEYS),
    pages=arr(obj(title=S, rows=arr(obj(fields=arr(SEED))))),
    rules=arr(RULE), thank_you=obj(title=S, message=S),
    notes=arr(obj(code=enum(DRAFT_NOTES), params=PARAMS)),
)

# The parts of a theme the assistant may set (group.name); values as text ("true", "160", "#0f766e", "xl")
THEME_PARTS = ("layout", "page.bg_type", "page.bg", "page.bg_to", "page.gradient_angle", "container.radius",
               "container.shadow", "container.border", "colors.primary", "colors.text", "colors.input_border",
               "typography.font", "typography.heading_weight", "inputs.radius", "inputs.style", "buttons.radius",
               "buttons.variant", "buttons.full_width", "header.band", "header.band_bg", "header.band_to",
               "blocks.section", "blocks.section_color", "blocks.section_caps", "blocks.divider")
THEME_DRAFT = obj(suggestions=arr(obj(key=enum(("calm", "bold", "minimal")), name=S, description=S,
                                      patch=arr(obj(part=enum(THEME_PARTS), value=S)))))

ASSIST = obj(
    add_fields=arr(obj(field=SEED, page_id=S, after_id=S)),
    set_help=arr(obj(field_id=S, help=S)),
    add_rules=arr(obj(match=enum(("all", "any")), when=arr(obj(field_id=S, op=enum(LOGIC_OPERATORS), values=arr(S))),
                      then=arr(obj(action=enum(("show", "hide", "require")), target_id=S)))),
    fixes=arr(obj(problem=enum(AI_PROBLEMS), field_id=S, page_id=S, text=S, remove=B)),
)

TRANSLATE = obj(items=arr(obj(key=S, translation=S)))
REWRITE = obj(items=arr(obj(key=S, rewrite=S, reasons=arr(enum(AI_REWRITE_REASONS)))))
LABELS = obj(labels=arr(obj(i=INT, sentiment=enum(("positive", "neutral", "negative")), themes=arr(enum(AI_THEMES)))))
QUESTION = obj(
    kind=enum(("count", "top", "average", "trend")), field_key=S,
    period=obj(**{"from": S, "to": S, "label": S}),
    status=enum(("any", "new", "reviewed", "approved", "rejected")),
    answer=obj(field_key=S, value=S), bucket=enum(("day", "week", "month")),
)
SUMMARY = obj(points=arr(obj(field_key=S, value=S)), sentiment=enum(("positive", "neutral", "negative", "none")),
              themes=arr(enum(AI_THEMES)))


# ── System prompts ────────────────────────────────────────────────────────────

FIELD_GUIDE = """Field types: short_text (a line), long_text (a paragraph), rich_text, email, phone, url, number,
currency, percentage, full_name, date, time, datetime, date_range, duration, dropdown / radio (one choice, needs
options), checkbox / multi_select (several choices, options), ranking (options), matrix (options are the columns,
props.rows the rows), toggle (yes or no), consent (an agreement, required), rating (props.max 3 to 10), scale (props.min
0 or 1, props.max up to 10, min_label, max_label), slider, file_upload, image_upload, signature, address, country,
language, timezone, currency_code, domain, color, iban, bic, calculated (props.format and a formula such as
"{quantity} * {price}" over other questions' keys), section (a heading), divider."""


@lru_cache(maxsize=1)
def template_list() -> str:
    from app.modules.templates.catalogue import system_templates

    return "\n".join(f"- {t['key']}: {t['name']} ({t['category']}). {t['description']}" for t in system_templates())


def form_system() -> str:
    return f"""{COMMON}

You design forms. From what the person describes (and an optional pasted document), write one form:
- Each thing to ask becomes the question type that fits it best, with the person's own words as labels. Short
  questions may share a row (two per row at most); long answers and choices get a row of their own.
- About people: their name and contact details first; agreement and signature last.
- After a yes / no question, a question asking for details is shown only after "yes": a rule
  {{"match": "all", "when": [{{"key": "<toggle key>", "op": "true", "values": []}}], "then": [{{"action": "show",
  "target": "<details key>", "value": ""}}]}}. Condition values are text: option values, numbers as digits.
- A quantity and a price get a calculated Total. Keys are short snake_case words; rules and formulas use keys.
- More than eight questions: group them on pages with short titles (unless asked for one page); "several" means
  pages even when short. Ten to twenty five questions is usually enough; never more than eighty.
- A pasted document: every line that reads like a question becomes one, its headings become pages, and source is
  "document". Otherwise source is "list" (built from what was listed), "template" (adapted from one of Formalie's
  templates below, with based_on its key) or "basic" (too little to go on: a short form to build on).
- "variant" above 0 means the person asked to try again: give a clearly different take.
- notes say what you did, as codes: follow_up {{field, after}}, total {{a, b}}, pages {{n}}, document_questions {{n}},
  document_sections {{n}}, added_contact, from_list {{n}}, template {{name}}, try_again, basic.
- category is the gallery category that fits best; language is the language the form is written in.
- Anything not used is empty: "" for text, [] for lists (props are name and value pairs, rows are a matrix's rows).

{FIELD_GUIDE}

Formalie's templates:
{template_list()}"""


def theme_system() -> str:
    return f"""{COMMON}

You design form themes from a brand colour. Give exactly three designs, keys calm, bold and minimal, ordered so the
one that fits the mood comes first. Each is a patch over Formalie's default theme: only the parts you change, each
as a part name and its value as text (true / false, whole numbers, #rrggbb colours). The primary colour (buttons, progress) must keep a contrast of at least 4.5 : 1 with white
text: use the given readable shade, or a darker one. Page backgrounds are light tints; text stays dark. Fonts: sans,
serif, rounded, mono. A name is one or two words; a description is one sentence."""


def assist_system() -> str:
    return f"""{COMMON}

You help someone build a form in Formalie's builder. You get the form (pages, fields with id, key, type, label, help,
options) and one action. Suggest changes the person can apply one by one; never repeat what the form has.
Fill only the list for the action; leave the others empty.
- fields (add_fields): up to five questions the form is likely missing (field as a seed, page_id and after_id of
  existing ids, or "" for the end).
- help (set_help): a short help text (under 20 words, plain words) for questions that have none.
- logic (add_rules): follow-ups only: details shown after a yes, "what went wrong" after a low rating, "other"
  details after an Other choice. when uses field ids and the operators that fit the field (toggle: true / false with
  no values; choices: eq with an option value; rating and scale: lte with a number); then shows the follow-up.
- check (fixes): problems with their code and field_id: email_type, phone_type, date_type, number_type (a short text
  asking for that), duplicate (remove true), image_alt (text = the description), long_label (text = a shorter label),
  no_required, few_options, long_page (page_id, field_id ""), no_label.

{FIELD_GUIDE}"""


def translate_system() -> str:
    names = ", ".join(f"{loc['code']} ({loc['englishName']})" for loc in APP_LOCALES)
    return f"""{COMMON}

You translate the texts of a form into one language. Each item has a key, the text and its kind (text, long, html).
Translate the meaning naturally for people filling in a form, keep it as short as the original, keep any markup in
html items exactly (same tags in the same order, attributes untouched) and translate only the words between them.
Never add, remove or rename keys; numbers, emails, web addresses and words in curly braces stay as they are. When a
text should not be translated (a brand or product name), give it unchanged; "" leaves it for a person. Languages: {names}."""


def rewrite_system() -> str:
    reasons = ", ".join(AI_REWRITE_REASONS)
    return f"""{COMMON}

You make a form's texts easier to read, in the tone asked for: plain (everyday words, short sentences), friendly
(warm, "please" for instructions) or formal (no contractions, polite). Keep the meaning and the language of each text,
keep it short, never add markup. Only list texts that really change, each with its reasons: {reasons}."""


def labels_system() -> str:
    themes = ", ".join(AI_THEMES)
    return f"""{COMMON}

You read written answers from a form's responses. For each answer (by its number i) give its tone (positive,
neutral or negative) and the themes it is about, from: {themes} (other when none fits). Personal details may have been
replaced by [email] or [number]; ignore them."""


def question_system() -> str:
    return f"""{COMMON}

Someone asks a question about a form's responses in plain words. You do not see the responses: you only say what to
count, and Formalie counts. Choose kind: count (how many), top (the most common answers of a choice question), average
(of a number, rating or scale question) or trend (per day, week or month, of the number of responses, or of an
average when field_key is a number question). field_key is the question meant (a key from the list) or "". period
is the dates the question names (from and to as YYYY-MM-DD, up to today, with a short label such as "last month"),
all "" when it names none. status filters by review status when asked ("any" otherwise). answer filters responses by
one option value (field_key and the option's value) when the question names an answer, never for top ("" otherwise).
bucket is for trends (month when unsure)."""


def summary_system() -> str:
    themes = ", ".join(AI_THEMES)
    return f"""{COMMON}

You summarise one response to a form in a few points: at most six, each the key of a question and a short value in
plain words (what the person answered, not a judgement), the most telling first. Then its tone (positive, neutral,
negative, or none when nothing is written) and its themes from: {themes}. Names, emails, phone numbers and addresses
are never part of a summary."""


def content(data: dict[str, Any]) -> str:
    """The request itself, as stable JSON."""
    return json.dumps(data, ensure_ascii=False, sort_keys=True)

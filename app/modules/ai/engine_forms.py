"""The stand-in's form maker: port of the mock's server/mock/ai/formEngine.ts and questions.ts (no outside service).

From a description in plain words, or a pasted document, it writes a form definition (app/modules/ai/kit.py) and so a
real FormSchema v1: document lines that read like questions, a listed description ("name, company, arrival time and
a photo") with each item asked by the field that fits it best, else the closest of Formalie's templates, else a basic
form to build on. Then people's details first, a follow-up after a "yes", a total for a quantity and a price, pages
when it is long. `variant` gives another take for "Try again". Held to the mock's answers by
tests/parity/test_ai_engines.py.

One deliberate difference: when a template is put on one page, rules that pointed at its other pages are dropped
(the mock leaves the page's title as the rule's target, which matches nothing).
"""

from __future__ import annotations

import copy
import re
from typing import Any, Callable

from app.core import js
from app.modules.ai.kit import agree_scale, build_schema, opts, slug
from app.modules.templates.catalogue import system_templates


def rx(pattern: str, flags: int = 0) -> re.Pattern[str]:
    """A JavaScript pattern: `\\b` is an ASCII word boundary there."""
    return re.compile(pattern.replace(r"\b", r"(?a:\b)"), flags)


I = re.IGNORECASE


# ── The dictionary of common questions (questions.ts) ─────────────────────────

def _consent(label: str) -> dict[str, Any]:
    if not label:
        return {"type": "consent", "label": "I agree", "required": True}
    rest = rx(r"^(agree(ment)? (to|with)|accept(ance of)?|consent to)\s+", I).sub("", label, count=1)
    rest = rx(r"^the\s+", I).sub("the ", rest, count=1)
    return {"type": "consent", "label": f"I agree to {rest}", "required": True}


def to_question(label: str) -> str:
    return label if label.endswith("?") else f"{label}?"


QUESTION_PATTERNS: list[tuple[re.Pattern[str], Callable[[str], dict[str, Any]]]] = [
    (rx(r"^(?!.*\b(company|organi[sz]ation|business|school|event|project|product|item|file|user ?name|site|venue|course)\b).*\b(full name|name|names)\b", I),
     lambda label: {"type": "full_name", "label": "Full name", "required": True}),
    (rx(r"\be-?mail", I), lambda label: {"type": "email", "label": "Email address", "required": True}),
    (rx(r"\b(phone|mobile|telephone|cell)\b", I), lambda label: {"type": "phone", "label": "Phone number"}),
    (rx(r"\b(date of birth|birth ?date|birthday|dob)\b", I), lambda label: {"type": "date", "label": "Date of birth"}),
    (rx(r"\b(age)\b", I), lambda label: {"type": "number", "label": "Age", "validation": {"min": 0, "max": 130}}),
    (rx(r"\b(signature|sign(ed)? (here|below|off))\b", I),
     lambda label: {"type": "signature", "label": "Signature", "required": True}),
    (rx(r"\b(agree|agreement|consent|accept|terms|rules|policy|declaration|confirm that)\b", I), _consent),
    (rx(r"\b(photos?|pictures?|images?|selfie|headshot)\b", I), lambda label: {"type": "image_upload", "label": "Photo"}),
    (rx(r"\b(cv|resume|résumé|attachments?|documents?|files?|upload|receipts?|invoices? copy|evidence|certificates?)\b", I),
     lambda label: {"type": "file_upload", "label": label or "Attachment"}),
    (rx(r"\b(address|where (do )?you live|street|postal)\b", I), lambda label: {"type": "address", "label": "Address"}),
    (rx(r"\b(country|nationality)\b", I), lambda label: {"type": "country", "label": label or "Country"}),
    (rx(r"\b(language)\b", I), lambda label: {"type": "language", "label": "Preferred language"}),
    (rx(r"\b(website|url|link to|portfolio|linkedin)\b", I), lambda label: {"type": "url", "label": label or "Website"}),
    (rx(r"\b(arrival|departure|check-?in|check-?out|start|end|meeting|appointment) (time|date and time)\b|\bdate and time\b|\bwhen (exactly)?\b", I),
     lambda label: {"type": "datetime", "label": label or "Date and time"}),
    (rx(r"\b(time|hour)\b", I), lambda label: {"type": "time", "label": label or "Time"}),
    (rx(r"\b(dates?|when|deadline|day)\b", I), lambda label: {"type": "date", "label": label or "Date"}),
    (rx(r"\b(from .* to|period|date range|how long were|stay)\b", I),
     lambda label: {"type": "date_range", "label": label or "Dates"}),
    (rx(r"\b(how long|duration)\b", I), lambda label: {"type": "duration", "label": label or "Duration"}),
    (rx(r"\b(price|cost|amount|budget|salary|fee|total paid|expenses?|spend)\b", I),
     lambda label: {"type": "currency", "label": label or "Amount"}),
    (rx(r"\b(quantity|how many|number of|count|qty)\b", I),
     lambda label: {"type": "number", "label": label or "Quantity", "validation": {"min": 0}}),
    (rx(r"\b(percent|percentage|%)\b", I), lambda label: {"type": "percentage", "label": label or "Percentage"}),
    (rx(r"\b(nps|recommend us|how likely)\b", I),
     lambda label: {"type": "scale", "label": "How likely are you to recommend us to a friend or colleague?",
                    "props": {"min": 0, "max": 10, "min_label": "Not at all likely", "max_label": "Extremely likely"}}),
    (rx(r"\b(rating|rate|stars?|score|satisf(ied|action)|how (good|happy|was))\b", I),
     lambda label: {"type": "rating", "label": label or "How would you rate it?", "props": {"max": 5}}),
    (rx(r"\b(agree or disagree|statements?)\b", I),
     lambda label: {"type": "radio", "label": label or "How much do you agree?", "options": agree_scale()}),
    (rx(r"\b(priority|urgency|how urgent)\b", I),
     lambda label: {"type": "radio", "label": "Priority", "options": opts("Low", "Medium", "High", "Urgent")}),
    (rx(r"\b(department|team)\b", I),
     lambda label: {"type": "dropdown", "label": label or "Department",
                    "options": opts("Finance", "Operations", "People", "Sales", "Support", "Technology")}),
    (rx(r"\b(gender)\b", I),
     lambda label: {"type": "radio", "label": "Gender",
                    "options": opts("Woman", "Man", "Non-binary", "Prefer to self-describe", "Prefer not to say")}),
    (rx(r"\b(size)\b", I), lambda label: {"type": "radio", "label": label or "Size", "options": opts("XS", "S", "M", "L", "XL")}),
    (rx(r"\b(dietary|allerg(y|ies)|food)\b", I),
     lambda label: {"type": "checkbox", "label": "Dietary requirements",
                    "options": opts("None", "Vegetarian", "Vegan", "Halal", "Kosher", "Gluten free", "Other")}),
    (rx(r"\b(how did you (hear|find)|source|referr(al|ed))\b", I),
     lambda label: {"type": "dropdown", "label": "How did you hear about us?",
                    "options": opts("Search engine", "Social media", "Friend or colleague", "Event", "Advertisement", "Other")}),
    (rx(r"\b(contact (method|preference)|best way to contact)\b", I),
     lambda label: {"type": "radio", "label": "How should we contact you?", "options": opts("Email", "Phone", "Text message")}),
    (rx(r"\b(yes or no|whether|do you|have you|are you|is (there|it)|any)\b", I),
     lambda label: {"type": "toggle", "label": to_question(label) if label else "Yes or no?"}),
    (rx(r"\b(company|organi[sz]ation|employer|business)\b", I), lambda label: {"type": "short_text", "label": label or "Company"}),
    (rx(r"\b(comments?|feedback|notes?|describe|description|details?|explain|reason|why|message|anything else|suggestions?|story|summary)\b", I),
     lambda label: {"type": "long_text", "label": label or "Comments"}),
]

_SMALL_WORDS = re.compile(r"^(a|an|the|their|your|his|her|its|our|my|some|any|optional|required)\s+", I)


def clean_label(phrase: str) -> str:
    """"the arrival time" → "Arrival time"; trims list words and punctuation."""
    text = js.trim(re.sub(r"[.;:,]+$", "", re.sub(r"^[-*•\d.)\]\s]+", "", js.trim(phrase))))
    for _ in range(3):
        if not _SMALL_WORDS.search(text):
            break
        text = _SMALL_WORDS.sub("", text, count=1)
    text = js.trim(re.sub(r"^(and|or|also|plus)\s+", "", text, count=1, flags=I))
    return text[0].upper() + text[1:] if text else ""


def seed_for(phrase: str) -> dict[str, Any]:
    """The field for one phrase: the first pattern that matches, else a short text answer."""
    label = clean_label(phrase)
    for pattern, make in QUESTION_PATTERNS:
        if not pattern.search(phrase):
            continue
        seed = make(label)
        fixed = seed.pop("label", None)
        return {**seed, "label": (fixed if fixed is not None else label) or "Question"}
    long_ = len(phrase) > 60 or phrase.endswith("?")
    kind = ("long_text" if rx(r"\b(what|how|why|describe|tell)\b", I).search(phrase) else "short_text") if long_ \
        else "short_text"
    return {"type": kind, "label": label or "Question"}


# ── Ranking Formalie's templates ──────────────────────────────────────────────

_STOP = set(("a an and are as at be by for from i in is it me my of on or our the their them they this to us we what "
             "with you your form survey please need want make create build new should can that which who will would "
             "like about").split())
_PEOPLE = rx(r"\b(visitors?|applicants?|candidates?|employees?|staff|customers?|clients?|patients?|guests?|students?|members?|volunteers?|attendees?|participants?|tenants?|suppliers?|contractors?|parents?|people|users?|respondents?|registrations?|sign-?ups?|bookings?|requests?)\b", I)
_KINDS = rx(r"\b(form|survey|checklist|application|request|questionnaire|registration|feedback|report|log|booking|order|sign-?in|sign-?up|assessment|inspection|evaluation|review|enquiry|inquiry|claim|poll|quiz)\b", I)


def _words(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s-]|_", " ", text.lower())
    out = []
    for word in re.split(r"\s+", cleaned):
        word = re.sub(r"(?<!s)s$", "", re.sub(r"(ies)$", "y", word))
        if len(word) > 2 and word not in _STOP:
            out.append(word)
    return out


def rank_templates(prompt: str) -> list[dict[str, Any]]:
    """Formalie's templates, best match first, with a score (0 = nothing in common) → [{template, score}]."""
    asked = set(_words(prompt))
    ranked = []
    for template in system_templates():
        score = (sum(1 for w in _words(template["name"]) if w in asked) * 3
                 + sum(1 for tag in template.get("tags") or [] for w in _words(tag) if w in asked) * 2
                 + sum(1 for w in _words(template["description"]) if w in asked))
        if score > 0:
            ranked.append({"template": template, "score": score})
    ranked.sort(key=lambda item: -item["score"])
    return ranked


def title_from(prompt: str, fallback: str) -> str:
    """"A sign-in form for visitors at reception" → "Visitor sign-in form"."""
    first = re.split(r"[.\n:]", prompt)[0]
    kind = _KINDS.search(first)
    if not kind:
        return fallback
    before = js.trim(rx(r"^.*\b(a|an|the|need|want|create|make|build)\b\s*", I).sub("", first[:kind.start()], count=1))
    for_who = rx(r"\bfor ((?:new|existing|our|all|the) )?((?:[^\W\d_]|-)+)").search(first[kind.end():])
    who = None
    if for_who:
        lead_word = for_who.group(1) if for_who.group(1) and not re.match(r"^(our|all|the) $", for_who.group(1)) else ""
        who = f"{lead_word}{for_who.group(2)}"
    noun = "form" if rx(r"\bform$", I).search(kind.group(0)) else kind.group(0).lower()
    lead = " ".join(part for part in [
        rx(r"s\b").sub("", who, count=1) if who and not rx(r"\b(the|our|us|people)\b", I).search(who) else "",
        before] if part)
    if noun == "form" or re.search(r"form$", lead, I):
        tail = noun
    else:
        tail = f"{noun}{'' if re.search(r'form|survey|checklist|request|report|log|order|review|quiz|poll|claim', noun) else ' form'}"
    title = js.trim(f"{lead} {tail}")
    clean = rx(r"\b(form) form\b", I).sub(r"\1", re.sub(r"\s+", " ", title), count=1)
    return clean[0].upper() + clean[1:].lower()[:79] if js.utf16_len(clean) >= 4 else fallback


def listed_items(prompt: str) -> list[str]:
    """The items a description lists ("name, company, arrival time and a photo")."""
    lead = rx(r"\b(with|including|includes?|asking (?:for|about)|asks? (?:for|about)|collect(?:s|ing)?|capture[sd]?|fields?|questions?|need(?:s)? to know|covering)\b[:\s]+([\s\S]+)", I).search(prompt)
    text = lead.group(2) if lead else (prompt if len(re.split(r"[,;]", prompt)) >= 4 else "")
    if not text:
        return []
    out = []
    for part in re.split(r"\n|;|,|\s+and\s+|\s+or\s+|\s+plus\s+|\.\s", text):
        part = js.trim(rx(r"\b(etc|and so on)\.?$", I).sub("", part, count=1))
        if len(part) > 1 and len(re.split(r"\s+", part)) <= 9:
            out.append(part)
    return out


def document_questions(doc: str) -> list[dict[str, Any]]:
    """Lines of a pasted document that read like questions; `#`, "Section …" or ALL CAPS lines start a page."""
    pages: list[dict[str, Any]] = []
    current: dict[str, Any] = {"title": "Questions", "items": []}
    for raw in re.split(r"\r?\n", doc):
        line = js.trim(raw)
        if not line:
            continue
        heading = bool(re.match(r"^#+\s+", line)) or bool(re.match(r"^(section|part|step)\s+\w", line, I)) \
            or (js.utf16_len(line) <= 40 and line == line.upper() and bool(re.search(r"[^\W\d_]", line)))
        if heading:
            if current["items"]:
                pages.append(current)
            current = {"title": clean_label(re.sub(r"^#+\s+", "", line, count=1).lower()), "items": []}
            continue
        question = bool(re.search(r"[?:]\s*$", line)) or bool(re.search(r"_{3,}|\[\s?\]|\(\s?\)", line)) \
            or bool(re.match(r"^[^:]{2,60}:\s*\S+( / \S+)+", line)) \
            or (bool(re.match(r"^[-*•\d]", line)) and js.utf16_len(line) <= 90)
        if question:
            current["items"].append(js.trim(re.sub(r"[:]\s*$", "", re.sub(r"_{3,}.*$", "", line, count=1), count=1)))
    if current["items"]:
        pages.append(current)
    return pages


def _with_inline_options(line: str, seed: dict[str, Any]) -> dict[str, Any]:
    """A choice question written with its answers: "Shift: Morning / Afternoon / Night" or "( ) A ( ) B"."""
    boxes = [js.trim(m.group(1)) for m in re.finditer(r"[(\[]\s?[)\]]\s*([^(\[]+)", line)]
    boxes = [b for b in boxes if b]
    slashed = [js.trim(p) for p in re.split(r"[:?]", line)[-1].split(" / ")] if " / " in line else []
    slashed = [p for p in slashed if p]
    options = boxes if len(boxes) >= 2 else slashed if len(slashed) >= 2 else []
    if len(options) < 2:
        return seed
    if len(options) == 2 and all(re.match(r"^(yes|no)$", o, I) for o in options):
        return {**seed, "type": "toggle"}
    label = clean_label(re.sub(r"\?.*$", "?", re.sub(r"[(\[]\s?[)\]].*$", "", line, count=1).split(":")[0], count=1))
    kind = "dropdown" if len(options) > 5 else "checkbox" if boxes and "[" in line else "radio"
    return {"type": kind, "label": label or seed["label"], "options": [{"value": slug(o), "label": o} for o in options]}


_CONTACT = {"full_name", "email", "phone"}
_LAST = {"consent", "signature"}
_SHORT = {"full_name", "email", "phone", "date", "time", "number", "currency", "short_text", "country", "datetime",
          "percentage", "url", "language"}


def _rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Short fields side by side (two per row), long answers and choices on their own."""
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(items):
        a = items[i]
        b = items[i + 1] if i + 1 < len(items) else None
        if b and a["type"] in _SHORT and b["type"] in _SHORT and a["type"] != "full_name":
            out.append({"fields": [a, b]})
            i += 2
        else:
            out.append({"fields": [a]})
            i += 1
    return out


def _chunk(fields: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    front = [f for f in fields if f["type"] in _CONTACT]
    back = [f for f in fields if f["type"] in _LAST]
    middle = [f for f in fields if f["type"] not in _CONTACT and f["type"] not in _LAST]
    paged = mode == "several" or (mode == "auto" and len(fields) > 8)
    if not paged:
        return [{"title": "Your answers", "rows": _rows([*front, *middle, *back])}]
    pages: list[dict[str, Any]] = []
    if front:
        pages.append({"title": "About you", "list": front})
    for i in range(0, len(middle), 6):
        pages.append({"title": f"Details {i // 6 + 1}" if len(middle) > 6 else "Details", "list": middle[i:i + 6]})
    if back:
        if pages:
            pages[-1]["list"].extend(back)
        else:
            pages.append({"title": "Confirm", "list": back})
    return [{"title": p["title"], "rows": _rows(p["list"])} for p in pages]


_FOLLOW = rx(r"\b(detail|describe|explain|which|if yes|specify|what)\b", I)
_QUANTITY = rx(r"\b(quantity|how many|number of|qty)\b", I)


def _add_logic(fields: list[dict[str, Any]], notes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Follow-ups after a yes ("Any allergies?" → "Please give details") and a total for quantity × price."""
    logic: list[dict[str, Any]] = []
    keys: set[str] = set()

    def key_of(field: dict[str, Any]) -> str:
        key = slug(field.get("key") or field["label"])
        if not re.match(r"^[a-z]", key):
            key = f"q_{key}"
        n = 2
        while key in keys:
            key = f"{slug(field['label'])}_{n}"
            n += 1
        keys.add(key)
        return key
    out = [{**f, "key": key_of(f)} for f in fields]
    for i in range(len(out) - 1):
        field, nxt = out[i], out[i + 1]
        if field["type"] == "toggle" and (nxt["type"] == "long_text" or _FOLLOW.search(nxt["label"])):
            logic.append({"match": "all", "when": [{"key": field["key"], "op": "true"}],
                          "then": [{"action": "show", "target": nxt["key"]}]})
            notes.append({"code": "follow_up", "params": {"field": nxt["label"], "after": field["label"]}})
    quantity = next((f for f in out if f["type"] == "number" and _QUANTITY.search(f["label"])), None)
    price = next((f for f in out if f["type"] == "currency"), None)
    if quantity and price and not any(f["type"] == "calculated" for f in out):
        total = {"type": "calculated", "label": "Total", "key": key_of({"type": "calculated", "label": "Total"}),
                 "formula": f"{{{quantity['key']}}} * {{{price['key']}}}", "props": {"format": "currency"}}
        out.insert(out.index(price) + 1, total)
        notes.append({"code": "total", "params": {"a": quantity["label"], "b": price["label"]}})
    return out, logic


def _from_fields(name: str, prompt: str, fields: list[dict[str, Any]], mode: str, notes: list[dict[str, Any]]) -> dict[str, Any]:
    with_logic, logic = _add_logic(fields, notes)
    pages = _chunk(with_logic, mode)
    if len(pages) > 1:
        notes.append({"code": "pages", "params": {"n": len(pages)}})
    return {"key": f"ai_{slug(name)}", "category": "business", "icon": "i-lucide-sparkles",
            "minutes": max(1, int(js.math_round(len(with_logic) / 3))), "name": name,
            "description": js.utf16_slice(prompt, 200), "pages": pages, "logic": logic,
            "thank_you": {"title": "Thank you!", "message": "Your answers have been sent."}}


def one_page(schema: dict[str, Any]) -> dict[str, Any]:
    """A template's form on a single page (its first page's title, every row in order); rules that pointed at the
    other pages are dropped."""
    out = copy.deepcopy(schema)
    pages = out["pages"]
    if len(pages) <= 1:
        return out
    gone = {p["id"] for p in pages[1:]}
    out["pages"] = [{"id": pages[0]["id"], "title": pages[0].get("title"), "rows": [r for p in pages for r in p["rows"]]}]
    logic = []
    for rule in out.get("logic") or []:
        effects = [e for e in rule["then"] if e.get("target") not in gone]
        if effects:
            logic.append({**rule, "then": effects})
    out["logic"] = logic
    out["settings"] = {**(out.get("settings") or {}), "progress_bar": False, "save_resume": False}
    return out


def draft_form(prompt: str, document: str | None = None, pages: str = "auto", variant: int = 0) -> dict[str, Any]:
    """A draft for a description (and optional document): {name, description, schema (no theme), notes, based_on,
    source, design (the template's own design patch, for templates), category (the source template's, if any)}."""
    prompt = js.trim(prompt)
    mode = pages or "auto"
    notes: list[dict[str, Any]] = []
    ranked = rank_templates(f"{prompt} {document or ''}")
    top = ranked[0]["template"]["name"] if ranked else None

    def made(definition: dict[str, Any], source: str) -> dict[str, Any]:
        return {"name": definition["name"], "description": definition["description"], "schema": build_schema(definition),
                "notes": notes, "based_on": None, "source": source, "design": {}, "category": None}

    # 1. A pasted document
    if document and js.trim(document):
        parsed = document_questions(document)
        items = [line for page in parsed for line in page["items"]]
        if items:
            name = title_from(prompt, top or "Form from a document")
            seeds = [_with_inline_options(line, seed_for(line)) for line in items]
            notes.append({"code": "document_questions", "params": {"n": len(items)}})
            if len(parsed) > 1 and mode != "one":
                definition = _from_fields(name, prompt, seeds, "one", notes)
                flat = [f for row in definition["pages"][0]["rows"] for f in row["fields"]]
                at = 0
                sections = []
                for page in parsed:
                    rows = []
                    for _ in page["items"]:
                        rows.append({"fields": [flat[at]] if at < len(flat) else []})
                        at += 1
                    sections.append({"title": page["title"], "rows": [r for r in rows if r["fields"]]})
                definition["pages"] = sections
                notes.append({"code": "document_sections", "params": {"n": len(parsed)}})
                return made(definition, "document")
            return made(_from_fields(name, prompt, seeds, mode, notes), "document")
        notes.append({"code": "document_none"})

    # 2. A description that lists what to ask
    items = listed_items(prompt)
    if len(items) >= 3:
        name = title_from(prompt, top or "New form")
        seeds = [seed_for(item) for item in items]
        asks_people = bool(_PEOPLE.search(prompt)) and not any(s["type"] == "full_name" for s in seeds)
        if asks_people and variant % 2 == 0:
            seeds.insert(0, {"type": "full_name", "label": "Full name", "required": True})
            if not any(s["type"] == "email" for s in seeds):
                seeds.insert(1, {"type": "email", "label": "Email address", "required": True})
            notes.append({"code": "added_contact"})
        notes.append({"code": "from_list", "params": {"n": len(items)}})
        layout = "several" if variant % 2 == 1 and mode == "auto" else mode
        return made(_from_fields(name, prompt, seeds, layout, notes), "list")

    # 3. The closest template (another one on "Try again")
    match = ranked[variant % max(1, len(ranked))] if ranked else None
    if match and match["score"] >= 3:
        template = match["template"]
        schema = copy.deepcopy(template["schema"])
        if mode == "one":
            schema = one_page(schema)
        notes.append({"code": "template", "params": {"name": template["name"]}})
        if len(ranked) > 1:
            notes.append({"code": "try_again"})
        return {"name": title_from(prompt, template["name"]), "description": template["description"], "schema": schema,
                "notes": notes, "based_on": {"key": template["key"], "name": template["name"]}, "source": "template",
                "design": copy.deepcopy(template.get("design") or {}), "category": template["category"]}

    # 4. Not much to go on: a basic form to build on
    notes.append({"code": "basic"})
    basic = [{"type": "full_name", "label": "Full name", "required": True},
             {"type": "email", "label": "Email address", "required": True},
             {"type": "long_text", "label": js.utf16_slice(clean_label(prompt), 120) or "Your message"}]
    return made(_from_fields(title_from(prompt, "New form"), prompt, basic, mode, notes), "basic")

"""The stand-in's analysis: ports of the mock's server/mock/ai/textAnalysis.ts and analysisEngine.ts.

  text_of / themes_of / sentiment_of  word lists find what written answers are about and their tone (the model
                                      replaces these with its own reading, `labels`)
  analyse                             a period against the one before: responses, tone, themes with examples,
                                      average ratings, top choices, and what stands out
  ask                                 a question in plain words → count, top answers, average or trend, with the
                                      period and filters it understood (`plan_question` / `run_question`: the model
                                      may plan instead, the numbers are always counted here)
  summarise                           one response in a few lines

Responses are {id, number, at (ms since 1970, UTC), status, data}. Numbers are always counted here, never by a
model. Held to the mock's answers by tests/parity/test_ai_engines.py.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Callable

from app.core import js
from app.modules.ai.engine_forms import I, rx
from app.modules.ai.kit import all_fields, is_input

DAY = 86_400_000
Labels = Callable[[str], tuple[str, list[str]]]  # text → (sentiment, themes)


def iso_day(ms: int | float) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%d")


def day_ms(day: str) -> int:
    return int(datetime.strptime(day[:10], "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)


def utc_ms(year: int, month: int, day: int) -> int:
    """Date.UTC(year, month (0-based, may overflow), day)."""
    year += month // 12
    month %= 12
    return int(datetime(year, month + 1, 1, tzinfo=UTC).timestamp() * 1000) + (day - 1) * DAY


def num(x: float | int) -> float | int:
    """A number as JSON shows it in the browser (4.0 → 4)."""
    return int(x) if isinstance(x, float) and x.is_integer() else x


def rnd(n: float, digits: int = 1) -> float | int:
    return num(js.math_round(n * 10 ** digits) / 10 ** digits)


# ── Text (textAnalysis.ts) ────────────────────────────────────────────────────

_W = "[A-Za-z0-9_]"
THEME_WORDS = {
    "speed": rx(r"\b(quick|quickly|fast|slow|wait|waiting|delay|delayed|took|later than|on time|minutes?|hours?)\b", I),
    "ease": rx(rf"\b(easy|simple|clear|instructions?|confus{_W}*|repetitive|find|understand|steps?|help text|complicated)\b", I),
    "staff": rx(r"\b(team|staff|friendly|welcoming|professional|helpful|rude|polite|people|service)\b", I),
    "price": rx(rf"\b(price|prices|cost|costs|fee|fees|expensive|cheap|value|fair|afford{_W}*)\b", I),
    "quality": rx(r"\b(quality|great|excellent|poor|better|worse|best|experience)\b", I),
    "mobile": rx(r"\b(phone|mobile|app|online|website|laptop|screen)\b", I),
    "communication": rx(r"\b(email|e-mail|call|copy|contact|reply|replies|answer|answers|update|records)\b", I),
    "scheduling": rx(r"\b(time slot|slots?|morning|mornings|evening|schedule|session|booking|appointment|draft)\b", I),
    "location": rx(r"\b(location|reach|parking|place|site|building|room)\b", I),
    "delivery": rx(r"\b(delivery|deliveries|shipping|shipped|arrived|parcel)\b", I),
}
_POSITIVE = rx(r"\b(good|great|quick|fast|friendly|easy|clear|liked|love|loved|excellent|fair|better than|welcoming|professional|recommend|happy|thank|thanks|simple|well|helpful|polite|on time)\b", I)
_NEGATIVE = rx(rf"\b(slow|late|later than|hard|difficult|confus{_W}*|repetitive|expensive|poor|bad|rude|problem|issue|wait{_W}*|delay{_W}*|worse|missing|broken|disappoint{_W}*|took a moment)\b", I)
_NOT_WRITTEN = rx(r"\b(name|email|phone|company|city|title|role|job|reference)\b", I)


def text_of(fields: list[dict[str, Any]], data: dict[str, Any]) -> list[str]:
    """The written answers in a response (short and long text, and rich text without tags)."""
    out = []
    for f in fields:
        if not (f["type"] in ("long_text", "rich_text") or (f["type"] == "short_text" and not _NOT_WRITTEN.search(f.get("label") or ""))):
            continue
        value = data.get(f["key"])
        if isinstance(value, str) and len(js.trim(value)) > 3:
            out.append(js.trim(re.sub(r"<[^>]+>", " ", value)))
    return out


def themes_of(text: str) -> list[str]:
    found = [key for key, pattern in THEME_WORDS.items() if pattern.search(text)]
    return found or ["other"]


def sentiment_of(text: str) -> str:
    positive = len(list(_POSITIVE.finditer(text)))
    negative = len(list(_NEGATIVE.finditer(text)))
    return "positive" if positive > negative else "negative" if negative > positive else "neutral"


def word_labels(text: str) -> tuple[str, list[str]]:
    return sentiment_of(text), themes_of(text)


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def period_in(question: str, now: int) -> dict[str, Any] | None:
    """The period a question names ("last month", "this week", "in March", "last 30 days"), else None."""
    q = question.lower()
    today = day_ms(iso_day(now))
    date = datetime.fromtimestamp(today / 1000, UTC)
    start_of_week = today - date.weekday() * DAY
    y, m = date.year, date.month - 1

    def month(offset: int) -> dict[str, int]:
        return {"from": utc_ms(y, m + offset, 1), "to": min(utc_ms(y, m + offset + 1, 1) - DAY, today)}
    days = rx(r"\b(?:last|past)\s+(\d{1,3})\s+days?\b").search(q)
    if days:
        return {"from": today - (int(days.group(1)) - 1) * DAY, "to": today, "label": f"last {days.group(1)} days"}
    if rx(r"\btoday\b").search(q):
        return {"from": today, "to": today, "label": "today"}
    if rx(r"\byesterday\b").search(q):
        return {"from": today - DAY, "to": today - DAY, "label": "yesterday"}
    if rx(r"\bthis week\b").search(q):
        return {"from": start_of_week, "to": today, "label": "this week"}
    if rx(r"\blast week\b").search(q):
        return {"from": start_of_week - 7 * DAY, "to": start_of_week - DAY, "label": "last week"}
    if rx(r"\bthis month\b").search(q):
        return {**month(0), "label": "this month"}
    if rx(r"\blast month\b").search(q):
        return {**month(-1), "label": "last month"}
    if rx(r"\bthis year\b").search(q):
        return {"from": utc_ms(y, 0, 1), "to": today, "label": "this year"}
    if rx(r"\blast year\b").search(q):
        return {"from": utc_ms(y - 1, 0, 1), "to": utc_ms(y, 0, 1) - DAY, "label": "last year"}
    named = next((i for i, name in enumerate(MONTHS) if rx(rf"\b(in )?{name}\b").search(q)), -1)
    if named >= 0:
        year = y - 1 if named > m else y
        return {"from": utc_ms(year, named, 1), "to": min(utc_ms(year, named + 1, 1) - DAY, today), "label": MONTHS[named]}
    return None


# ── Analysis (analysisEngine.ts) ──────────────────────────────────────────────

RATING = {"rating", "scale", "slider"}
CHOICE = {"radio", "dropdown", "checkbox", "multi_select", "toggle", "country", "language"}


def label_of(field: dict[str, Any], value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    option = next((o for o in field.get("options") or [] if o.get("value") == value and not isinstance(value, bool)), None)
    return option["label"] if option else js.to_string(value)


def max_of(field: dict[str, Any]) -> float | int:
    value = (field.get("props") or {}).get("max")
    n = js.to_number(value) if value is not None else float("nan")
    if n and not js.is_nan(n):
        return num(n)
    return 10 if field["type"] == "scale" else 100 if field["type"] == "slider" else 5


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def average(rows: list[dict[str, Any]], field: dict[str, Any]) -> float | int | None:
    values = [r["data"].get(field["key"]) for r in rows]
    values = [v for v in values if _is_number(v)]
    return rnd(sum(values) / len(values)) if values else None


def _rows_in(entries: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    return [e for e in entries if start <= e["at"] < end + DAY]


def fields_of(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [f for f in all_fields(schema) if is_input(f["type"])]


def analyse(form: dict[str, Any], schema: dict[str, Any] | None, entries: list[dict[str, Any]], start: int, end: int,
            mask: Callable[[str], str], labels: Labels = word_labels) -> dict[str, Any]:
    """A period's analysis against the period of the same length before it (no request_id or credits yet)."""
    fields = fields_of(schema)
    length = end - start + DAY
    rows = _rows_in(entries, start, end)
    before = _rows_in(entries, start - length, start - DAY)

    def tone(items: list[dict[str, Any]]) -> dict[str, int]:
        totals = {"positive": 0, "neutral": 0, "negative": 0}
        for row in items:
            for text in text_of(fields, row["data"]):
                totals[labels(text)[0]] += 1
        return totals
    sentiment = tone(rows)
    themes: dict[str, dict[str, Any]] = {}
    text_answers = 0
    for row in rows:
        for text in text_of(fields, row["data"]):
            text_answers += 1
            mood, keys = labels(text)
            for key in keys:
                item = themes.setdefault(key, {"count": 0, "positive": 0, "negative": 0, "examples": []})
                item["count"] += 1
                if mood == "positive":
                    item["positive"] += 1
                if mood == "negative":
                    item["negative"] += 1
                shown = mask(text)
                if len(item["examples"]) < 3 and shown not in item["examples"]:
                    item["examples"].append(shown)
    theme_list = [{"key": key, **item, "share": rnd(item["count"] / text_answers * 100, 0) if text_answers else 0}
                  for key, item in themes.items()]
    theme_list.sort(key=lambda t: (int(t["key"] == "other"), -t["count"]))
    theme_list = theme_list[:8]

    ratings = []
    for f in fields:
        if f["type"] in RATING:
            now = average(rows, f)
            if now is not None:
                ratings.append({"key": f["key"], "label": f["label"], "average": now, "previous": average(before, f),
                                "max": max_of(f)})
    choices = []
    for f in [f for f in fields if f["type"] in CHOICE][:4]:
        counts: dict[str, int] = {}
        answered = 0
        for row in rows:
            value = row["data"].get(f["key"])
            if value is None or value == "":
                continue
            answered += 1
            for item in value if isinstance(value, list) else [value]:
                label = label_of(f, item)
                counts[label] = counts.get(label, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:1]
        if top and answered:
            choices.append({"key": f["key"], "label": f["label"], "top": top[0][0], "share": rnd(top[0][1] / answered * 100, 0)})

    days = int(js.math_round(length / DAY))
    shown_days = min(days, 92)
    daily = []
    for index in range(shown_days):
        date = iso_day(end - (shown_days - 1 - index) * DAY)
        daily.append({"date": date, "count": sum(1 for r in rows if iso_day(r["at"]) == date)})

    findings: list[dict[str, Any]] = []
    if len(rows) < 5:
        findings.append({"code": "few_responses", "params": {"n": len(rows)}})
    if before and rows:
        change = int(js.math_round((len(rows) - len(before)) / len(before) * 100))
        if abs(change) >= 10:
            findings.append({"code": "responses_up" if change > 0 else "responses_down", "params": {"n": abs(change)}})
    busiest = sorted(daily, key=lambda d: -d["count"])[:1]
    if busiest and busiest[0]["count"] >= 3:
        findings.append({"code": "busiest_day", "params": {"day": busiest[0]["date"], "n": busiest[0]["count"]}})
    for rating in ratings:
        if rating["previous"] is not None and abs(rating["average"] - rating["previous"]) >= 0.3:
            findings.append({"code": "rating_up" if rating["average"] > rating["previous"] else "rating_down",
                             "params": {"label": rating["label"], "from": rating["previous"], "to": rating["average"]}})
    worst = sorted([t for t in theme_list if t["key"] != "other" and t["negative"] >= 2 and t["negative"] >= t["positive"]],
                   key=lambda t: -t["negative"])[:1]
    if worst:
        findings.append({"code": "theme_negative", "theme": worst[0]["key"], "params": {"n": worst[0]["negative"]}})
    best = sorted([t for t in theme_list if t["key"] != "other" and t["positive"] >= 2 and t["positive"] > t["negative"]],
                  key=lambda t: -t["positive"])[:1]
    if best:
        findings.append({"code": "theme_positive", "theme": best[0]["key"], "params": {"n": best[0]["positive"]}})
    if not text_answers:
        findings.append({"code": "no_text"})
    return {
        "form": form,
        "period": {"from": iso_day(start), "to": iso_day(end)},
        "previous": {"from": iso_day(start - length), "to": iso_day(start - DAY)},
        "totals": {"responses": len(rows), "previous": len(before), "text_answers": text_answers},
        "daily": daily,
        "sentiment": sentiment,
        "previous_sentiment": tone(before),
        "themes": [{"key": t["key"], "count": t["count"], "share": t["share"], "positive": t["positive"],
                    "negative": t["negative"], "examples": t["examples"]} for t in theme_list],
        "ratings": ratings,
        "choices": choices,
        "findings": findings,
    }


# ── Questions in plain words ──────────────────────────────────────────────────

_STOP = set(("a an and are as at be by did do does for from how i in is it many me most much my of on or our per the "
             "their there this to was we were what when which who with you your any all average mean number count "
             "responses response answers answer people times total last this month week year day days today yesterday "
             "said say").split())
STATUSES = ("new", "reviewed", "approved", "rejected")


def _content_words(text: str) -> list[str]:
    out = []
    for word in re.split(r"\s+", re.sub(r"[^\w\s]|_", " ", text.lower())):
        word = re.sub(r"(?<!s)s$", "", word)
        if len(word) > 2 and word not in _STOP:
            out.append(word)
    return out


def field_in(question: str, fields: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The question the form asks that the person most likely means."""
    asked = set(_content_words(question))
    lowered = question.lower()
    scored = []
    for f in fields:
        score = sum(1 for w in _content_words(f.get("label") or "") if w in asked) \
            + sum(1 for o in f.get("options") or [] if (o.get("label") or "").lower() in lowered) * 2
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda item: -item[0])
    return scored[0][1] if scored else None


def _numeric(field: dict[str, Any]) -> bool:
    return field["type"] in RATING or field["type"] in ("number", "currency", "percentage")


def plan_question(question: str, fields: list[dict[str, Any]], now: int) -> dict[str, Any]:
    """What the question asks, the mock's way: {kind, field_key, period, status, answer {field_key, value}, bucket,
    guessed}. The model may write the same plan (app/modules/ai/checks.py checks it); `run_question` counts."""
    q = question.lower()
    period = period_in(question, now)
    status = next((s for s in STATUSES if rx(rf"\b{s}\b").search(q)), None)
    wants_average = bool(rx(r"\b(average|mean|avg|typical)\b").search(q))
    wants_trend = bool(rx(r"\b(per (day|week|month)|by (day|week|month)|each (day|week|month)|trend|over time|monthly|weekly|daily)\b").search(q))
    wants_top = bool(rx(r"\b(most|top|which|popular|common|best|worst|favourite|favorite|breakdown|split)\b").search(q))
    named = None
    for f in fields:
        for o in f.get("options") or []:
            label = o.get("label") or ""
            if len(label) > 2 and rx(rf"\b{re.escape(label.lower())}\b").search(q):
                named = {"field_key": f["key"], "value": o["value"]}
                break
        if named:
            break
    plan: dict[str, Any] = {"period": period, "status": status, "answer": named if named and not wants_top else None,
                            "field_key": None, "bucket": None, "guessed": False}
    if wants_trend:
        by_month = bool(rx(r"\bmonth").search(q)) or not rx(r"\b(day|week)").search(q)
        field = field_in(question, [f for f in fields if _numeric(f)]) if wants_average else None
        return {**plan, "kind": "trend", "field_key": field["key"] if field else None,
                "bucket": "month" if by_month else "week" if rx(r"\bweek").search(q) else "day"}
    if wants_average:
        named_field = field_in(question, [f for f in fields if _numeric(f)])
        field = named_field or next((f for f in fields if _numeric(f)), None)
        return {**plan, "kind": "average", "field_key": field["key"] if field else None,
                "guessed": bool(field) and not named_field}
    if wants_top:
        by_name = next((f for f in fields if named and f["key"] == named["field_key"]), None) \
            or field_in(question, [f for f in fields if f["type"] in CHOICE])
        field = by_name or next((f for f in fields if f["type"] in CHOICE), None)
        return {**plan, "kind": "top", "field_key": field["key"] if field else None, "guessed": bool(field) and not by_name}
    return {**plan, "kind": "count"}


def run_question(plan: dict[str, Any], fields: list[dict[str, Any]], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """The answer for a plan, counted from the responses (AiAnswer without request_id, credits or question)."""
    by_key = {f["key"]: f for f in fields}
    notes: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    period = plan.get("period")
    items = entries
    if period:
        items = [e for e in items if period["from"] <= e["at"] < period["to"] + DAY]
        filters.append({"kind": "period", "label": "period", "value": period["label"]})
    else:
        notes.append({"code": "period_default"})
    if plan.get("status"):
        items = [e for e in items if e.get("status") == plan["status"]]
        filters.append({"kind": "status", "label": "status", "value": plan["status"]})
    rows = items
    answer = plan.get("answer")
    if answer and answer["field_key"] in by_key:
        field = by_key[answer["field_key"]]
        option = next((o for o in field.get("options") or [] if o.get("value") == answer["value"]), None)

        def holds(row: dict[str, Any]) -> bool:
            value = row["data"].get(field["key"])
            return answer["value"] in (value if isinstance(value, list) else [value])
        rows = [r for r in rows if holds(r)]
        filters.append({"kind": "answer", "label": field["label"], "value": option["label"] if option else js.to_string(answer["value"])})
    shown = {"from": iso_day(period["from"]), "to": iso_day(period["to"])} if period else None
    field = by_key.get(plan.get("field_key") or "")
    kind = plan["kind"]

    if kind == "trend":
        def bucket(at: int) -> str:
            if plan.get("bucket") == "month":
                return iso_day(at)[:7]
            if plan.get("bucket") == "week":
                return iso_day(at - datetime.fromtimestamp(at / 1000, UTC).weekday() * DAY)
            return iso_day(at)
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            groups.setdefault(bucket(row["at"]), []).append(row)
        out = []
        for key in sorted(groups, key=js.utf16_key):
            value = (average(groups[key], field) or 0) if field else len(groups[key])
            out.append({"label": key, "count": value, "share": 0})
        top = max([1, *[r["count"] for r in out]])
        return {"kind": "trend", "value": None, "field": {"key": field["key"], "label": field["label"]} if field else None,
                "rows": [{**r, "share": int(js.math_round(r["count"] / top * 100))} for r in out], "filters": filters,
                "period": shown, "notes": notes}
    if kind == "average":
        if not field:
            return {"kind": "average", "value": None, "field": None, "rows": [], "filters": filters, "period": shown,
                    "notes": [*notes, {"code": "no_field"}]}
        if plan.get("guessed"):
            notes.append({"code": "field_guess", "params": {"label": field["label"]}})
        return {"kind": "average", "value": average(rows, field), "field": {"key": field["key"], "label": field["label"]},
                "rows": [], "filters": filters, "period": shown, "notes": notes}
    if kind == "top" and field:
        if plan.get("guessed"):
            notes.append({"code": "field_guess", "params": {"label": field["label"]}})
        counts: dict[str, int] = {}
        answered = 0
        for row in rows:
            value = row["data"].get(field["key"])
            if value is None or value == "":
                continue
            answered += 1
            for item in value if isinstance(value, list) else [value]:
                label = label_of(field, item)
                counts[label] = counts.get(label, 0) + 1
        top_rows = [{"label": label, "count": count, "share": int(js.math_round(count / answered * 100)) if answered else 0}
                    for label, count in sorted(counts.items(), key=lambda kv: -kv[1])[:10]]
        if not top_rows:
            notes.append({"code": "no_answers"})
        return {"kind": "top", "value": answered, "field": {"key": field["key"], "label": field["label"]}, "rows": top_rows,
                "filters": filters, "period": shown, "notes": notes}
    if kind == "top":
        notes.append({"code": "no_field"})
    return {"kind": "count", "value": len(rows), "field": None, "rows": [], "filters": filters, "period": shown,
            "notes": notes}


def ask(schema: dict[str, Any] | None, entries: list[dict[str, Any]], question: str, now: int) -> dict[str, Any]:
    fields = [f for f in fields_of(schema) if f["type"] != "hidden"]
    return run_question(plan_question(question, fields, now), fields, entries)


# ── One response ──────────────────────────────────────────────────────────────

_LEFT_OUT = {"hidden", "calculated", "signature", "consent", "file_upload", "image_upload"}
_PERSONAL = {"full_name", "email", "phone", "address"}
_PERSONAL_LABEL = rx(r"\b(name|email|phone|address)\b", I)


def summary_fields(schema: dict[str, Any] | None, data: dict[str, Any]) -> list[dict[str, Any]]:
    """The answers a summary may show (who the respondent is stays in the response itself), most telling first."""
    fields = [f for f in all_fields(schema) if is_input(f["type"]) and f["type"] not in _LEFT_OUT]

    def rank(f: dict[str, Any]) -> int:
        return 0 if f["type"] in RATING else 1 if f["type"] in CHOICE else \
            2 if f["type"] in ("number", "currency", "date", "datetime") else 3 if f["type"] == "long_text" else 4
    kept = [f for f in fields if data.get(f["key"]) is not None and data.get(f["key"]) != ""
            and f["type"] not in _PERSONAL
            and not (f["type"] == "short_text" and _PERSONAL_LABEL.search(f.get("label") or ""))]
    kept.sort(key=rank)
    return kept


def point_text(field: dict[str, Any], value: Any) -> str:
    if field["type"] in RATING:
        return f"{js.to_string(value)} / {js.to_string(max_of(field))}"
    if isinstance(value, list):
        return ", ".join(label_of(field, item) for item in value)
    if isinstance(value, dict):
        return ", ".join(js.to_string(v) for v in value.values() if v)
    if field["type"] == "long_text":
        return re.split(r"(?<=[.!?])\s", js.to_string(value))[0]
    return label_of(field, value)


def summarise(schema: dict[str, Any] | None, data: dict[str, Any], mask: Callable[[str], str],
              labels: Labels = word_labels) -> dict[str, Any]:
    """One response in a few lines: the answers that say most, its tone and themes."""
    shown = summary_fields(schema, data)[:6]
    points = [{"label": f["label"], "value": mask(point_text(f, data[f["key"]]))} for f in shown]
    fields = [f for f in all_fields(schema) if is_input(f["type"]) and f["type"] not in _LEFT_OUT]
    texts = text_of(fields, data)
    if not texts:
        return {"points": points, "sentiment": None, "themes": []}
    mood, keys = labels(" ".join(texts))
    return {"points": points, "sentiment": mood, "themes": [k for k in keys if k != "other"]}

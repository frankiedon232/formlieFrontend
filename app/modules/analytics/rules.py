"""Form analytics rules (F18), ported from server/mock/routes/analytics.ts with parity tests
(scripts/dump_dashboard_rules.py → tests/vectors/dashboard_rules.json):

- `period_of`: `from` / `to` as days (default the last 30 days, never past today, at most a year),
- `days_of`: one form's days: completions from its responses; starts and views estimated around them,
- `totals_of`: views, starts, completions, completion rate and the median time to fill in,
- `funnel_of`: where people stop, page by page and question by question.

Views and starts are the mock's estimates, the same for a form and a day every time (`seeded` on the form's id and
the day): Formalie does not record the fill-in page's own events yet (no table for them; DATABASE-DESIGN keeps a
place for `form_events`). Completions, their days, channels and times are real.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core import js
from app.modules.dashboard.rules import iso_day, parse_day

DISPLAY_ONLY = frozenset({"section", "paragraph", "divider", "image", "html", "spacer"})
# How much a question type makes people stop, and how long it takes (seconds)
WEIGHT = {"long_text": 2.2, "file": 2.8, "signature": 2.1, "address": 1.8, "phone": 1.4, "email": 1.3, "matrix": 1.9,
          "ranking": 1.6}
SECONDS = {"long_text": 38, "file": 24, "signature": 14, "address": 22, "matrix": 26, "ranking": 18, "short_text": 7,
           "email": 8, "phone": 9, "full_name": 9, "number": 5, "date": 6}
_M = 0xFFFFFFFF


def jround(x: float) -> int:
    return int(js.math_round(x))


def seeded(text: str) -> Callable[[], float]:
    """The mock's repeatable random numbers for a text (FNV-1a, then a murmur-style mix), 0 ≤ n < 1."""
    h = 2166136261
    for char in text:
        code = ord(char)
        if code > 0xFFFF:  # charCodeAt(0) of a code point outside the BMP: its high surrogate
            code = 0xD800 + ((code - 0x10000) >> 10)
        h = ((h ^ code) * 16777619) & _M
    state = [h]

    def next_number() -> float:
        h = state[0]
        h = ((h ^ (h >> 15)) * 2246822507) & _M
        h = ((h ^ (h >> 13)) * 3266489909) & _M
        h ^= h >> 16
        state[0] = h
        return h / 4294967296

    return next_number


@dataclass(frozen=True)
class Period:
    start: int
    end: int
    days: int

    def before(self) -> Period:
        return Period(self.start - self.days, self.start - 1, self.days)


def period_of(query: dict[str, Any], today: int) -> Period:
    """periodOf(): `from` and `to` as days (default the last 30 days, at most a year)."""
    end = parse_day(query.get("to"))
    start = parse_day(query.get("from"))
    if end is None or end > today:
        end = today
    if start is None or start > end:
        start = end - 29
    start = max(start, end - 365)
    return Period(start, end, end - start + 1)


def rate_of(completion_rate: int | None) -> float:
    """The share of starters who finish, from the form's completion rate (68 % when it has none), 0.2 to 0.95."""
    return min(0.95, max(0.2, (completion_rate or 68) / 100))


def days_of(form_id: str, status: str, completion_rate: int | None, completions: dict[int, int],
            period: Period) -> list[dict[str, Any]]:
    """daysOf(): one form's days; `completions` = responses per day."""
    rate = rate_of(completion_rate)
    is_open = status == "published"
    daily = []
    for i in range(period.days):
        day = iso_day(period.start + i)
        done = completions.get(period.start + i, 0)
        starts = views = 0
        if done or is_open:
            random = seeded(f"{form_id}:{day}")
            wandering = math.floor(random() * 3) if is_open else 0
            starts = max(done, jround((done / rate) * (0.85 + random() * 0.3))) if done else wandering
            views = jround(starts * (1.3 + random() * 0.8)) if starts else (math.floor(random() * 4) if is_open else 0)
        daily.append({"date": day, "views": views, "starts": starts, "completions": done})
    return daily


def median_of(times: list[int]) -> int | None:
    values = sorted(times)
    if not values:
        return None
    mid = len(values) // 2
    return jround(values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2)


def rate(part: int, whole: int) -> float:
    """Of 100, one decimal (0 when there is nothing to compare with)."""
    return js.math_round(part / whole * 1000) / 10 if whole else 0


def totals_of(daily: list[dict[str, Any]], median_seconds: int | None) -> dict[str, Any]:
    views = sum(d["views"] for d in daily)
    starts = sum(d["starts"] for d in daily)
    completions = sum(d["completions"] for d in daily)
    return {"views": views, "starts": starts, "completions": completions, "completion_rate": rate(completions, starts),
            "median_seconds": median_seconds}


def funnel_of(form_id: str, schema: dict[str, Any] | None, totals: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """funnelOf(): the form's starters walk its questions in order; leavers spread by how hard each question is."""
    if not schema:
        return [], []
    questions = [(f, index) for index, page in enumerate(schema.get("pages") or [])
                 for row in page.get("rows") or [] for f in row.get("fields") or [] if f.get("type") not in DISPLAY_ONLY]
    random = seeded(f"{form_id}:funnel")
    weights = [(0.35 + random()) * WEIGHT.get(f.get("type"), 1) * (1.3 if f.get("required") else 0.6) * (1.6 if i == 0 else 1)
               for i, (f, _) in enumerate(questions)]
    total = sum(weights) or 1
    leavers = max(0, totals["starts"] - totals["completions"])
    reached, given = totals["starts"], 0
    fields: list[dict[str, Any]] = []
    for i, (f, page) in enumerate(questions):
        left = leavers - given if i == len(questions) - 1 else min(reached, jround(leavers * weights[i] / total))
        given += left
        stayed = reached - left
        answered = stayed if f.get("required") else jround(stayed * (0.55 + random() * 0.35))
        fields.append({"key": f.get("key"), "label": f.get("label", ""), "type": f.get("type"), "page": page,
                       "required": bool(f.get("required")), "reached": reached, "answered": answered, "left": left,
                       "seconds": jround(SECONDS.get(f.get("type"), 5) * (0.7 + random() * 0.6))})
        reached = stayed
    carried = totals["starts"]
    pages = []
    for index, page in enumerate(schema.get("pages") or []):
        own = [f for f in fields if f["page"] == index]
        first = own[0]["reached"] if own else carried
        left = sum(f["left"] for f in own)
        carried = first - left
        pages.append({"index": index, "title": page.get("title") or None, "reached": first, "left": left})
    return pages, fields


def drop_off_of(pages: list[dict], fields: list[dict], starts: int) -> dict[str, Any] | None:
    """The question most people left on (the first of equals), as a share of starters."""
    worst = None
    for f in fields:
        if worst is None or f["left"] > worst["left"]:
            worst = f
    if not worst or not worst["left"] or not starts:
        return None
    page = pages[worst["page"]] if worst["page"] < len(pages) else None
    return {"page": worst["page"], "page_title": page["title"] if page else None, "field": worst["key"],
            "field_label": worst["label"], "rate": rate(worst["left"], starts)}

"""Responses as the app sees them (mock: data/responseData.ts, responseInsights.ts; shared/types/responses.ts): rows
for the lists, the detail panel, titles made only from what the form collected, and insights.

Only real responses: the mock's sample responses for its demo forms are not made here.
"""

from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import js
from app.core.errors import FrmError
from app.modules.forms import access
from app.modules.forms.access import Viewer
from app.modules.forms.models import Form, FormVersion
from app.modules.forms.service import iso
from app.modules.links.seo import published_schema
from app.modules.public.rules import identity_of
from app.modules.public.submit import all_fields, is_input_field
from app.modules.responses.answers import answer_text, keep_answered
from app.modules.responses.models import Response, ResponseChange, ResponseNote

DAY = timedelta(days=1)
_SCORES = {"rating", "scale", "nps", "slider", "number", "currency", "percentage", "ranking", "toggle"}
_NOT_A_TITLE = {"hidden", "calculated", "payment", "signature", "file_upload", "image_upload", "long_text", "rich_text",
                "matrix"}
_FILE_FIELDS = ("file_upload", "image_upload")
STATUS_ORDER = {"new": 0, "reviewed": 1, "approved": 2, "rejected": 3}


def require_responses(form: Form, viewer: Viewer, action: str) -> None:
    """Allowed, else refused: responses they can't see stay "not found"."""
    if not access.responses_allowed(form, viewer, "view"):
        raise FrmError("FRM-GEN-1004")
    if not access.responses_allowed(form, viewer, action):
        raise FrmError("FRM-PERM-1001")


async def response_schema(db: AsyncSession, form: Form) -> dict[str, Any] | None:
    """What respondents fill in: the published version, else the draft (with lists kept on the server filled)."""
    from app.modules.lists.service import full_schema

    return await full_schema(db, form.tenant_id, await published_schema(db, form) or form.draft_schema)


async def version_schema(db: AsyncSession, form: Form, number: int | None) -> dict[str, Any] | None:
    """The version a respondent filled in (questions in its order), else the form's current one."""
    from app.modules.lists.service import full_schema

    if number is not None:
        version = (await db.execute(select(FormVersion).where(
            FormVersion.tenant_id == form.tenant_id, FormVersion.form_id == form.id,
            FormVersion.number == number))).scalar_one_or_none()
        if version is not None:
            return await full_schema(db, form.tenant_id, version.schema)
    return await response_schema(db, form)


def questions_of(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Questions a respondent can answer (no headings, hidden or calculated fields)."""
    return [f for f in all_fields(schema or {"pages": []})
            if is_input_field(f["type"]) and f["type"] not in ("hidden", "calculated", "payment")]


def _filled(value: Any) -> bool:
    return not (js.nullish(value) or value == "" or value is False or (isinstance(value, list) and not value))


# ── Who sent it, and what names it ──────────────────────────────────────────────

def respondent_from(schema: dict[str, Any] | None, data: dict[str, Any], response: Response) -> dict[str, Any]:
    """An invitation or member when the form knows them, else the name and email the form asked for."""
    if response.respondent_kind:
        return {"name": response.respondent_name, "email": response.respondent_email, "kind": response.respondent_kind}
    if not schema:
        return {"name": None, "email": None, "kind": "anonymous"}
    fields = all_fields(schema)
    email_key = identity_of(schema)["email"] or next((f["key"] for f in fields if f.get("type") == "email"), None)
    email = data.get(email_key) if email_key and isinstance(data.get(email_key), str) else None
    full = next((f for f in fields if f.get("type") == "full_name"), None)
    name_value = data.get(full["key"]) if full else None
    name_value = name_value if isinstance(name_value, dict) else {}

    def label(f: dict[str, Any]) -> str:
        return js.to_string(f.get("label") or "")
    first = next((f for f in fields if f.get("type") == "short_text" and re.search(r"first|given", label(f), re.I)), None)
    last = next((f for f in fields if f.get("type") == "short_text" and re.search(r"last|family|surname", label(f), re.I)), None)
    plain = next((f for f in fields if f.get("type") == "short_text"
                  and re.fullmatch(r"\s*(your\s+)?(full\s+)?name\s*", label(f), re.I)), None)
    name = " ".join(js.to_string(v) for v in (name_value.get("first"), name_value.get("last")) if v) \
        or " ".join(v for v in ((data.get(first["key"]) if first else None), (data.get(last["key"]) if last else None))
                    if isinstance(v, str) and v) \
        or (data.get(plain["key"]) if plain and isinstance(data.get(plain["key"]), str) else "")
    if name or email:
        return {"name": name or None, "email": email, "kind": "answer"}
    return {"name": None, "email": None, "kind": "anonymous"}


def title_of(schema: dict[str, Any] | None, respondent: dict[str, Any], data: dict[str, Any]) -> str | None:
    """The name or email the form asked for, else its first two short answers in form order; never a made-up
    word such as "Anonymous"."""
    if respondent.get("name") or respondent.get("email"):
        return respondent.get("name") or respondent.get("email")
    if not schema:
        return None
    usable = [f for f in all_fields(schema) if is_input_field(f["type"]) and f["type"] not in _NOT_A_TITLE]

    def pick(fields: list[dict[str, Any]]) -> list[str]:
        texts = [js.trim(answer_text(f, data.get(f["key"]))) for f in fields]
        return [t if len(t) <= 60 else f"{t[:57]}…" for t in texts if t][:2]
    parts = pick([f for f in usable if f["type"] not in _SCORES])
    chosen = parts or pick(usable)
    return " · ".join(chosen) if chosen else None


# ── Rows and detail ─────────────────────────────────────────────────────────────

class Entry:
    """A response with its form, the schema it is read with, and its notes count."""

    def __init__(self, response: Response, form: Form, schema: dict[str, Any] | None, notes: int = 0) -> None:
        self.response, self.form, self.schema, self.notes = response, form, schema, notes
        self.respondent = respondent_from(schema, response.data or {}, response)
        self.title = title_of(schema, self.respondent, response.data or {})


def row_of(entry: Entry, with_answers: bool) -> dict[str, Any]:
    r, data = entry.response, entry.response.data or {}
    questions = questions_of(entry.schema)
    return {
        "id": str(r.id), "number": r.number, "form": {"id": str(entry.form.id), "name": entry.form.name},
        "submitted_at": iso(r.submitted_at), "status": r.status, "tags": list(r.tags or []),
        "respondent": {**entry.respondent, "title": entry.title}, "channel": r.channel, "language": r.language,
        "duration_seconds": r.duration_seconds, "answers": data if with_answers else {}, "notes_count": entry.notes,
        "answered": sum(1 for f in questions if _filled(data.get(f["key"]))), "questions": len(questions),
        "files_count": sum(len(data[f["key"]]) for f in questions
                           if f["type"] in _FILE_FIELDS and isinstance(data.get(f["key"]), list)),
        "edited": r.edited,
        "possible_duplicate": None if r.duplicate_cleared else r.possible_duplicate,
    }


def _device(user_agent: str | None) -> str:
    ua = user_agent or ""
    return "Phone" if re.search(r"mobile|android|iphone", ua, re.I) else "Tablet" if re.search(r"ipad|tablet", ua, re.I) \
        else "Desktop"


async def detail_of(db: AsyncSession, entry: Entry, viewer: Viewer) -> dict[str, Any]:
    r = entry.response
    notes = (await db.execute(select(ResponseNote).where(
        ResponseNote.tenant_id == r.tenant_id, ResponseNote.response_id == r.id, ResponseNote.deleted_at.is_(None))
        .order_by(ResponseNote.created_at.desc(), ResponseNote.id.desc()))).scalars().all()
    history = (await db.execute(select(ResponseChange).where(
        ResponseChange.tenant_id == r.tenant_id, ResponseChange.response_id == r.id)
        .order_by(ResponseChange.at.desc(), ResponseChange.id.desc()).limit(200))).scalars().all()
    actions = access.response_actions_of(entry.form, viewer)
    version = await version_schema(db, entry.form, r.form_version_no)
    entry.notes = len(notes)
    return {
        **row_of(entry, False), "data": r.data or {}, "form_version": r.form_version_no,
        "schema": keep_answered(version, [r.data or {}]),
        "meta": {"device": _device(r.user_agent), "country": r.country},
        "notes": [{"id": str(n.id), "author": {"id": str(n.author_id) if n.author_id else "", "name": n.author_name},
                   "text": n.text, "created_at": iso(n.created_at)} for n in notes],
        "history": [{"id": str(c.id), "at": iso(c.at), "by": {"id": str(c.by_id) if c.by_id else "", "name": c.by_name},
                     "field": c.field, "before": c.before, "after": c.after} for c in history],
        "can": {k: actions[k] for k in ("review", "edit", "delete", "export")},
    }


async def notes_counts(db: AsyncSession, tenant_id: uuid.UUID, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = await db.execute(select(ResponseNote.response_id, func.count()).where(
        ResponseNote.tenant_id == tenant_id, ResponseNote.response_id.in_(ids), ResponseNote.deleted_at.is_(None))
        .group_by(ResponseNote.response_id))
    return dict(rows.all())  # type: ignore[arg-type]


async def responses_of(db: AsyncSession, tenant_id: uuid.UUID, form_ids: list[uuid.UUID]) -> list[Response]:
    """The forms' responses that still exist, newest first."""
    if not form_ids:
        return []
    return list((await db.execute(select(Response).where(
        Response.tenant_id == tenant_id, Response.form_id.in_(form_ids), Response.deleted_at.is_(None))
        .order_by(Response.submitted_at.desc(), Response.id.desc()))).scalars())


# ── Insights ────────────────────────────────────────────────────────────────────

_CHOICE = {"radio", "dropdown", "checkbox", "multi_select", "toggle", "country", "language", "currency_code"}
_RATING = {"rating", "scale", "slider"}
_NUMBER = {"number", "currency", "percentage"}
_TEXT = {"short_text", "long_text"}


def period_of(query: dict[str, str]) -> tuple[date, date]:
    """The period asked for (`from` / `to`), else the last 30 days up to today."""
    def day(value: str | None) -> date | None:
        try:
            return date.fromisoformat(value[:10]) if value else None
        except ValueError:
            return None
    today = datetime.now(UTC).date()
    end = day(query.get("to")) or today
    start = day(query.get("from")) or end - timedelta(days=29)
    return min(start, end), max(start, end)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _round(n: float, digits: int = 1) -> float:
    return js.math_round(n * 10 ** digits) / 10 ** digits


def question_insight(fld: dict[str, Any], rows: list[Entry]) -> dict[str, Any]:
    base = {"key": fld["key"], "label": js.trim(fld.get("label") or "") or fld["key"], "type": fld["type"]}
    values = [(e, (e.response.data or {}).get(fld["key"])) for e in rows]
    values = [(e, v) for e, v in values if not (js.nullish(v) or v == "" or (isinstance(v, list) and not v))]
    answered = len(values)
    calculated = fld["type"] == "calculated"
    numeric = calculated and bool(values) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for _, v in values)
    if fld["type"] in _CHOICE or (calculated and not numeric):
        counts: dict[str, int] = {}
        for _, v in values:
            for one in v if isinstance(v, list) else [v]:
                counts[js.to_string(one)] = counts.get(js.to_string(one), 0) + 1
        large = bool(fld.get("options_large"))
        known = [] if large else [{"value": "true", "label": ""}, {"value": "false", "label": ""}] if fld["type"] == "toggle" \
            else [{"value": o["value"], "label": o.get("label")} for o in fld.get("options") or []]
        labels = {o["value"]: o.get("label") for o in fld.get("options") or [] if o["value"] in counts} if large else {}
        if known:
            options = [{**o, "count": counts.get(o["value"], 0)} for o in known]
        else:
            options = sorted(({"value": v, "label": labels.get(v, v), "count": c} for v, c in counts.items()),
                             key=lambda o: -o["count"])[:8]
        return {**base, "answered": answered, "kind": "choice",
                "multiple": fld["type"] in ("checkbox", "multi_select"), "options": options}
    if fld["type"] in _RATING:
        numbers = [n for n in (js.to_number(v) for _, v in values) if not js.is_nan(n)]
        props = fld.get("props") or {}
        low = 1.0 if fld["type"] == "rating" else js.to_number(0 if js.nullish(props.get("min", js.UNDEFINED)) else props["min"])
        default_max = 5 if fld["type"] == "rating" else 10 if fld["type"] == "scale" else 100
        high = js.to_number(default_max if js.nullish(props.get("max", js.UNDEFINED)) else props["max"])
        step = max(1.0, float(math.ceil((high - low + 1) / 10))) if fld["type"] == "slider" and math.isfinite(high - low) else 1.0
        distribution = []
        value = low
        while value <= high and len(distribution) < 1000:
            distribution.append({"value": value, "count": sum(1 for n in numbers if value <= n < value + step)})
            value += step
        return {**base, "answered": answered, "kind": "rating",
                "average": _round(sum(numbers) / len(numbers)) if numbers else 0, "min": low, "max": high,
                "distribution": distribution}
    if fld["type"] in _NUMBER or numeric:
        numbers = [n for n in (js.to_number(v) for _, v in values) if not js.is_nan(n)]
        if not numbers:
            return {**base, "answered": answered, "kind": "other"}
        return {**base, "answered": answered, "kind": "number", "average": _round(sum(numbers) / len(numbers), 2),
                "min": min(numbers), "max": max(numbers), "median": _median(numbers)}
    if fld["type"] in _TEXT:
        latest = [{"id": str(e.response.id), "value": v[:280], "at": iso(e.response.submitted_at)}
                  for e, v in values if isinstance(v, str)][:5]
        return {**base, "answered": answered, "kind": "text", "latest": latest}
    return {**base, "answered": answered, "kind": "other"}


def insights_of(entries: list[Entry], query: dict[str, str], form: Form | None = None,
                schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Insights for responses (newest first). With `form`: completion and a summary per question; without, the inbox
    with the busiest forms instead."""
    start, end = period_of(query)
    span = (end - start).days + 1
    begin = datetime.combine(start, datetime.min.time(), UTC)
    finish = begin + timedelta(days=span)
    before = begin - timedelta(days=span)
    in_period = [e for e in entries if begin <= e.response.submitted_at < finish]
    previous = sum(1 for e in entries if before <= e.response.submitted_at < begin)
    daily = [{"date": (start + timedelta(days=i)).isoformat(), "count": 0} for i in range(span)]
    for e in in_period:
        daily[(e.response.submitted_at.astimezone(UTC).date() - start).days]["count"] += 1
    status = {"new": 0, "reviewed": 0, "approved": 0, "rejected": 0}
    channels = {"link": 0, "embed": 0, "api": 0}
    languages: dict[str, int] = {}
    for e in entries:
        status[e.response.status] += 1
    for e in in_period:
        channels[e.response.channel] += 1
        languages[e.response.language] = languages.get(e.response.language, 0) + 1
    questions: list[dict[str, Any]] = []
    if form is not None and schema:
        questions = [question_insight(f, in_period) for f in all_fields(schema)
                     if is_input_field(f["type"]) and f["type"] not in ("hidden", "payment")]
    busiest: dict[uuid.UUID, dict[str, Any]] = {}
    if form is None:
        for e in in_period:
            item = busiest.setdefault(e.form.id, {"id": str(e.form.id), "name": e.form.name, "count": 0})
            item["count"] += 1
    return {
        "total": len(entries), "new": status["new"],
        "period": {"from": start.isoformat(), "to": end.isoformat(), "count": len(in_period), "previous": previous},
        "daily": daily, "status": status, "channels": channels,
        "languages": [{"code": c, "count": n} for c, n in sorted(languages.items(), key=lambda kv: -kv[1])][:6],
        "median_seconds": _median([e.response.duration_seconds for e in in_period if e.response.duration_seconds is not None]),
        "completion_rate": (form.completion_rate or None) if form is not None else None,
        "last_at": iso(entries[0].response.submitted_at) if entries else None,
        "questions": questions,
        "top_forms": sorted(busiest.values(), key=lambda b: -b["count"])[:5],
        "schema": keep_answered(schema, [e.response.data or {} for e in entries]) if form is not None else None,
    }

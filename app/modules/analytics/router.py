"""Form analytics (F18; mock: routes/analytics.ts; API-CONTRACT → Analytics). Needs `analytics.view` (require_auth).

    GET /analytics/overview?from&to&form     totals with the period before, per day, channels, active forms
    GET /analytics/forms?from&to&q&sort&page one row per form (views … drop-off, sparkline); drafts without views left out
    GET /analytics/forms/{id}/funnel?from&to pages and questions: reached, answered, left

Counts cover the forms whose responses the person may see (role, sharing, folder access). Completions, their days,
channels and times are counted in the database (read replica); views and starts are the mock's repeatable estimates
around them (app/modules/analytics/rules.py). Nothing names a respondent.
"""

from __future__ import annotations

import functools
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.analytics import rules as A
from app.modules.auth.sessions import Principal, require_auth
from app.modules.dashboard import common as C
from app.modules.dashboard.rules import iso_day
from app.modules.forms import access
from app.modules.forms.access import viewer_for
from app.modules.forms.models import Form

router = APIRouter(tags=["analytics"])


def _form_id(value: Any) -> uuid.UUID | None:
    """A form id that came in as a reference, else None."""
    ctx = get_context()
    if not isinstance(value, str) or ctx is None or value.lower() not in {i.lower() for i in ctx.ref_ids}:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _one(forms: list[Form], form_id: uuid.UUID | None, viewer: Any) -> Form:
    """A form this person may see the responses of; any other is "not found"."""
    form = next((f for f in forms if f.id == form_id), None) if form_id else None
    if form is None or not access.responses_allowed(form, viewer, "view"):
        raise FrmError("FRM-GEN-1004")
    return form


def _daily(form: Form, per_day: dict[int, int], period: A.Period) -> list[dict[str, Any]]:
    return A.days_of(str(form.id), form.status, form.completion_rate, per_day, period)


@router.get("/analytics/overview", dependencies=[rate_limit("analytics", per_minute=120)])
async def analytics_overview(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **C.scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        clock = await C.clock_of(db, principal.tenant.id)
        period = A.period_of(query, clock.today())
        before = period.before()
        forms = C.with_responses(await C.visible_forms(db, viewer, principal.tenant.id), viewer)
        if query.get("form"):
            forms = [_one(forms, _form_id(query["form"]), viewer)]
        ids = [f.id for f in forms]
        counts = await C.responses_per_day(db, principal.tenant.id, ids, clock, before.start, period.end)
        channels = await C.channels(db, principal.tenant.id, ids, clock, period.start, period.end)
        now_median = await C.median_seconds(db, principal.tenant.id, ids, clock, period.start, period.end)
        then_median = await C.median_seconds(db, principal.tenant.id, ids, clock, before.start, before.end)

    def summed(target: A.Period) -> tuple[list[dict[str, Any]], int]:
        daily = [{"date": iso_day(target.start + i), "views": 0, "starts": 0, "completions": 0} for i in range(target.days)]
        active = 0
        for form in forms:
            own = _daily(form, counts.get(form.id, {}), target)
            for total, day in zip(daily, own, strict=True):
                total["views"] += day["views"]
                total["starts"] += day["starts"]
                total["completions"] += day["completions"]
            active += any(day["views"] for day in own)
        return daily, active

    now_daily, active = summed(period)
    then_daily, _ = summed(before)
    median = lambda found: A.jround(found[None]) if None in found else None  # noqa: E731
    return ok({
        "from": iso_day(period.start), "to": iso_day(period.end),
        "totals": A.totals_of(now_daily, median(now_median)), "previous": A.totals_of(then_daily, median(then_median)),
        "daily": now_daily, "channels": channels, "active_forms": active,
    })


def _compare(key: str, a: dict[str, Any], b: dict[str, Any]) -> int:
    """The mock's sort: numbers by value, empty last, everything else as text with numbers in order."""
    from app.modules.forms.router import _natural

    x, y = a.get(key), b.get(key)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
        return (x > y) - (x < y)
    if x is None:
        return 1
    if y is None:
        return -1
    kx, ky = _natural(str(x)), _natural(str(y))
    return (kx > ky) - (kx < ky)


# The columns a list may be sorted by (the contract's, plus status and change); another key keeps the order
SORT_KEYS = ("name", "status", "views", "starts", "completions", "completion_rate", "median_seconds", "change")


@router.get("/analytics/forms", dependencies=[rate_limit("analytics", per_minute=120)])
async def analytics_forms(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.responses.service import response_schema

    query = dict(request.query_params)
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    async with db_session("read", **C.scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        clock = await C.clock_of(db, principal.tenant.id)
        period = A.period_of(query, clock.today())
        before = period.before()
        forms = C.with_responses(await C.visible_forms(db, viewer, principal.tenant.id), viewer)
        ids = [f.id for f in forms]
        counts = await C.responses_per_day(db, principal.tenant.id, ids, clock, before.start, period.end)
        medians = await C.median_seconds(db, principal.tenant.id, ids, clock, period.start, period.end, per_form=True)
        rows: list[tuple[dict[str, Any], Form]] = []
        for form in forms:
            per_day = counts.get(form.id, {})
            now = _daily(form, per_day, period)
            totals = A.totals_of(now, A.jround(medians[form.id]) if form.id in medians else None)
            if form.status == "draft" and not totals["views"]:
                continue
            previous = sum(n for day, n in per_day.items() if before.start <= day <= before.end)
            rows.append(({"id": str(form.id), "name": form.name, "status": form.status, **totals,
                          "change": A.jround((totals["completions"] - previous) / previous * 100) if previous else None,
                          "trend": [day["completions"] for day in now], "drop_off": None}, form))
        sort = query.get("sort") or "-completions"
        desc, key = sort.startswith("-"), sort.lstrip("-")
        if key in SORT_KEYS:
            order = functools.cmp_to_key(lambda a, b: _compare(key, a[0], b[0]) * (-1 if desc else 1))
            rows.sort(key=order)
        q = (query.get("q") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in r[0]["name"].lower()]
        page = rows[params.offset:params.offset + params.page_size]
        # Where people stop: only for the rows shown (it reads each form's questions)
        for row, form in page:
            pages, fields = A.funnel_of(str(form.id), await response_schema(db, form), row)
            row["drop_off"] = A.drop_off_of(pages, fields, row["starts"])
    return ok([row for row, _ in page], params.meta(len(rows)))


@router.get("/analytics/forms/{form_id}/funnel", dependencies=[rate_limit("analytics", per_minute=120)])
async def form_funnel(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.responses.service import response_schema

    query = dict(request.query_params)
    async with db_session("read", **C.scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        try:
            wanted = uuid.UUID(form_id)
        except ValueError:
            wanted = None
        form = _one(await C.visible_forms(db, viewer, principal.tenant.id), wanted, viewer)
        clock = await C.clock_of(db, principal.tenant.id)
        period = A.period_of(query, clock.today())
        counts = await C.responses_per_day(db, principal.tenant.id, [form.id], clock, period.start, period.end)
        medians = await C.median_seconds(db, principal.tenant.id, [form.id], clock, period.start, period.end)
        totals = A.totals_of(_daily(form, counts.get(form.id, {}), period),
                             A.jround(medians[None]) if None in medians else None)
        pages, fields = A.funnel_of(str(form.id), await response_schema(db, form), totals)
    return ok({"form": {"id": str(form.id), "name": form.name, "status": form.status}, "totals": totals,
               "pages": pages, "fields": fields})

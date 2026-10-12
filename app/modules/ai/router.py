"""AI assistant: settings, usage and the history of requests (mock: routes/ai.ts; API-CONTRACT → AI assistant).
Permissions come from the route (rbac/permissions.py, as the mock's permissionFor):

    GET    /ai/settings             the workspace's settings with its brand colour (ai.use)
    PATCH  /ai/settings             { enabled?, sources?, mask_personal?, keep_days? } (ai.settings)
    GET    /ai/usage                this month's credits, by day and kind (ai.use)
    GET    /ai/requests             list (q, sort, from, to, filter[kind|status|person]); yours, or everyone's with
                                    ai.settings (ai.history)
    GET    /ai/requests/insights    counts for the two chart cards (same reach as the list)
    GET    /ai/requests/{id}        one, with the prompt and the result
    DELETE /ai/requests/{id}        yours, or any with ai.settings; audited ai.request_deleted
"""

from __future__ import annotations

import functools
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.ai import service as A
from app.modules.ai.kinds import AI_KEEP_DAYS, AI_KINDS, AI_SOURCES, AI_STATUSES
from app.modules.ai.models import AiRequest, AiSettings
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth

router = APIRouter(tags=["ai"])
DAY = timedelta(days=1)


def scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _day(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%d")


def _last_days(count: int, value: Any) -> list[dict[str, Any]]:
    today = datetime.now(UTC).date()
    return [{"date": (today - timedelta(days=count - 1 - i)).isoformat(),
             "count": value((today - timedelta(days=count - 1 - i)).isoformat())} for i in range(count)]


async def _with_brand(db: Any, tenant_id: uuid.UUID) -> dict[str, Any]:
    from app.modules.settings.service import get_section

    branding = await get_section(db, tenant_id, "branding")
    return {**await A.settings_of(db, tenant_id), "brand_color": branding.get("brand_color")}


@router.get("/ai/settings", dependencies=[rate_limit("ai-settings", per_minute=120)])
async def get_ai_settings(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        return ok(await _with_brand(db, principal.tenant.id))


settings_input = z.obj(
    enabled=z.boolean().optional(),
    sources=z.obj(forms=z.boolean().optional(), responses=z.boolean().optional(), data=z.boolean().optional()).optional(),
    mask_personal=z.boolean().optional(),
    keep_days=z.literals(list(AI_KEEP_DAYS)).optional(),
)


def _js(value: Any) -> str:
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


@router.patch("/ai/settings", dependencies=[rate_limit("ai-settings-update", per_minute=30)])
async def update_ai_settings(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    values = settings_input.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        row = await A.settings_row(db, principal.tenant.id)
        before = A.settings_view(row)
        if row is None:
            base = A.defaults()
            row = AiSettings(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                             enabled=base["enabled"], sources=dict(base["sources"]), mask_personal=base["mask_personal"],
                             keep_days=base["keep_days"], monthly_credits=base["monthly_credits"],
                             created_by=principal.user.id)
            db.add(row)
        if values.get("enabled") is not None:
            row.enabled = values["enabled"]
        if values.get("sources"):
            row.sources = {**before["sources"], **{k: v for k, v in values["sources"].items() if v is not None}}
        if values.get("mask_personal") is not None:
            row.mask_personal = values["mask_personal"]
        if values.get("keep_days") is not None:
            row.keep_days = values["keep_days"]
        row.updated_at, row.updated_by = datetime.now(UTC), principal.user.id
        row.updated_by_name = f"{principal.user.first_name} {principal.user.last_name}".strip()
        await db.flush()
        after = A.settings_view(row)
        changed = {key: f"{_js(before[key])} → {_js(after[key])}" for key in ("enabled", "mask_personal", "keep_days")
                   if before[key] != after[key]}
        for source in AI_SOURCES:
            if before["sources"][source] != after["sources"][source]:
                changed[f"reads_{source}"] = f"{_js(before['sources'][source])} → {_js(after['sources'][source])}"
        action = ("ai.enabled" if after["enabled"] else "ai.disabled") if before["enabled"] != after["enabled"] \
            else "ai.settings_updated"
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                     actor=Actor.user(principal.user), resource={"type": "setting", "id": "ai", "name": "AI assistant"},
                     metadata=changed)
        if after["keep_days"] < before["keep_days"]:
            await A.expire(db, principal.tenant.id, after["keep_days"])
        return ok(await _with_brand(db, principal.tenant.id))


@router.get("/ai/usage", dependencies=[rate_limit("ai-usage", per_minute=120)])
async def get_ai_usage(principal: Principal = Depends(require_auth)) -> Any:
    now = datetime.now(UTC)
    start = A.month_start(now)
    start_at = datetime(start.year, start.month, 1, tzinfo=UTC)
    end = (date(start.year + (start.month == 12), start.month % 12 + 1, 1) - DAY)
    prev_at = datetime(start.year - (start.month == 1), (start.month - 2) % 12 + 1, 1, tzinfo=UTC)
    elapsed = now - start_at
    async with db_session("read", **scope(principal)) as db:
        settings = await A.settings_of(db, principal.tenant.id)
        rows = await A.all_rows(db, principal.tenant.id, min(prev_at, now - 30 * DAY))
        used = await A.credits_used(db, principal.tenant.id)
    month = [r for r in rows if r.created_at >= start_at]
    by_kind = dict.fromkeys(AI_KINDS, 0)
    for r in month:
        by_kind[r.kind] += r.credits
    daily: dict[str, int] = {}
    for r in rows:
        daily[_day(r.created_at)] = daily.get(_day(r.created_at), 0) + r.credits
    return ok({
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "used": used, "limit": A.allowance_of(principal.tenant.plan_id, settings),
        "previous": sum(r.credits for r in rows if prev_at <= r.created_at < prev_at + elapsed),
        "requests": len(month), "people": len({r.by_id for r in month}),
        "daily": _last_days(30, lambda d: daily.get(d, 0)),
        "by_kind": by_kind,
    })


def _natural_cmp(a: str, b: str) -> int:
    from app.modules.forms.router import _natural

    x, y = _natural(a), _natural(b)
    return (x > y) - (x < y)


@router.get("/ai/requests", dependencies=[rate_limit("ai-requests", per_minute=240)])
async def list_ai_requests(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        settings = await A.settings_of(db, principal.tenant.id)
        rows = await A.kept_requests(db, principal, settings)

    def wanted(key: str) -> list[str] | None:
        raw = query.get(f"filter[{key}]")
        return [v for v in raw.split(",") if v] if raw else None
    for key, attr in (("kind", "kind"), ("status", "status")):
        if wanted(key):
            rows = [r for r in rows if getattr(r, attr) in wanted(key)]  # type: ignore[operator]
    if wanted("person"):
        people = {p.lower() for p in wanted("person") or []}
        rows = [r for r in rows if str(r.by_id) in people]
    if query.get("from"):
        rows = [r for r in rows if _day(r.created_at) >= query["from"]]
    if query.get("to"):
        rows = [r for r in rows if _day(r.created_at) <= query["to"]]
    sort = query.get("sort") or "-created_at"
    desc, key = sort.startswith("-"), sort.lstrip("-")

    def compare(a: AiRequest, b: AiRequest) -> int:
        if key == "credits":
            order = a.credits - b.credits
        elif key == "created_at":
            order = (a.created_at > b.created_at) - (a.created_at < b.created_at)
        else:
            order = _natural_cmp(str(getattr(a, key, "") or ""), str(getattr(b, key, "") or ""))
        return -order if desc else order
    if key in ("created_at", "credits", "title"):
        rows.sort(key=functools.cmp_to_key(compare))
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in f"{r.title} {r.by_name} {(r.target or {}).get('name') or ''}".lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    page = rows[params.offset:params.offset + params.page_size]
    return ok([A.to_row(r, principal) for r in page], params.meta(len(rows)))


@router.get("/ai/requests/insights", dependencies=[rate_limit("ai-requests", per_minute=240)])
async def ai_request_insights(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.settings_of(db, principal.tenant.id)
        rows = await A.kept_requests(db, principal, settings)
    since = datetime.now(UTC) - 30 * DAY
    recent = [r for r in rows if r.created_at >= since]
    by_status = dict.fromkeys(AI_STATUSES, 0)
    by_kind = dict.fromkeys(AI_KINDS, 0)
    for r in rows:
        by_status[r.status] += 1
        by_kind[r.kind] += 1
    per_day: dict[str, int] = {}
    for r in rows:
        per_day[_day(r.created_at)] = per_day.get(_day(r.created_at), 0) + 1
    return ok({
        "total": len(recent),
        "previous": sum(1 for r in rows if since - 30 * DAY <= r.created_at < since),
        "daily": _last_days(30, lambda d: per_day.get(d, 0)),
        "by_status": by_status, "by_kind": by_kind,
        "people": len({r.by_id for r in recent}),
        "credits": sum(r.credits for r in recent),
    })


async def find_visible(db: Any, principal: Principal, settings: dict[str, Any], request_id: str) -> AiRequest:
    try:
        wanted = uuid.UUID(request_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    found = next((r for r in await A.kept_requests(db, principal, settings) if r.id == wanted), None)
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


@router.get("/ai/requests/{request_id}", dependencies=[rate_limit("ai-requests", per_minute=240)])
async def get_ai_request(request_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.settings_of(db, principal.tenant.id)
        found = await find_visible(db, principal, settings, request_id)
        return ok(A.to_detail(found, principal, settings))


@router.delete("/ai/requests/{request_id}", dependencies=[rate_limit("ai-requests-delete", per_minute=60)])
async def delete_ai_request(request_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        settings = await A.settings_of(db, principal.tenant.id)
        found = await find_visible(db, principal, settings, request_id)
        title, kind, by = found.title, found.kind, found.by_name
        A.emptied(found, principal.user.id)
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="ai.request_deleted", actor=Actor.user(principal.user),
                     resource={"type": "ai_request", "id": str(found.id), "name": title}, metadata={"kind": kind, "by": by})
        return ok({"deleted": True})

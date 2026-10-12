"""API traffic (mock: routes/apiTraffic.ts; API-CONTRACT → API service, request logs and analytics). Admins only.

    GET /api-logs                 the log (from, to, q, sort, filter[endpoint|class|method|token|mode], page)
    GET /api-logs/insights        30 days: calls, errors, by status class, answer time
    GET /api-logs/settings · PUT  keep request / response bodies (personal answers masked) for 1, 7 or 30 days
    GET /api-logs/{id}            one call, with its headers (secrets masked) and kept bodies
    GET /api-analytics?period     7d | 30d: totals with the period before, per day, endpoints, tokens, countries, methods

The log is written by the public gateway (traffic.record_call); these routes only read it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.api_service import service as S
from app.modules.api_service import traffic as TR
from app.modules.api_service.models import ApiRequestLog
from app.modules.api_service.router import audit, scope
from app.modules.auth.sessions import Principal, require_admin

router = APIRouter(tags=["api service"])

LOG_DAYS = (1, 7, 30)
settings_schema = z.obj(keep_bodies=z.boolean(), days=z.number().int().refine(lambda n: n in LOG_DAYS))


@router.get("/api-logs", dependencies=[rate_limit("api-logs", per_minute=120)])
async def list_api_logs(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    async with db_session("read", **scope(principal)) as db:
        rows, total = await TR.list_logs(db, principal.tenant.id, query, params.offset, params.page_size)
    return ok(rows, params.meta(total))


@router.get("/api-logs/insights", dependencies=[rate_limit("api-logs", per_minute=60)])
async def api_log_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        return ok(await TR.log_insights(db, principal.tenant.id))


@router.get("/api-logs/settings", dependencies=[rate_limit("api-logs", per_minute=120)])
async def get_api_log_settings(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        return ok(TR.log_settings_view(await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)))


@router.put("/api-logs/settings", dependencies=[rate_limit("api-logs-write", per_minute=30)])
async def update_api_log_settings(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = settings_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        row = await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)
        before = TR.log_settings_view(row)
        row.log_keep_bodies, row.log_days, row.updated_by = values["keep_bodies"], int(values["days"]), principal.user.id
        changes = [{"field": "keep_bodies", "before": before["keep_bodies"], "after": values["keep_bodies"]}]
        if before["days"] != values["days"]:
            changes.append({"field": "days", "before": before["days"], "after": int(values["days"])})
        await audit(db, principal, "api.logging_changed", {"type": "api_service", "id": None, "name": "Request log"},
                    changes=changes)
        await db.flush()
        return ok(TR.log_settings_view(row))


@router.get("/api-logs/{log_id}", dependencies=[rate_limit("api-logs", per_minute=240)])
async def get_api_log(log_id: str, principal: Principal = Depends(require_admin)) -> Any:
    wanted = S.path_uuid(log_id)
    if wanted is None:
        raise FrmError("FRM-GEN-1004")
    async with db_session("read", **scope(principal)) as db:
        found = (await db.execute(select(ApiRequestLog).where(
            ApiRequestLog.tenant_id == principal.tenant.id, ApiRequestLog.id == wanted))).scalars().first()
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return ok(TR.detail_view(found))


@router.get("/api-analytics", dependencies=[rate_limit("api-analytics", per_minute=60)])
async def api_analytics(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False, traffic=False)
        return ok(await TR.analytics(db, principal.tenant.id, request.query_params.get("period"), store.services,
                                     store.endpoints, store.tokens))

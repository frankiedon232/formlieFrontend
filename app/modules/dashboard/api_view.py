"""Dashboard, API service view (F21 M4; mock: routes/dashboardApi.ts): the API service at work. Needs `api.view`
(else FRM-PERM-1001). Calls are counted in the request log (`api_request_logs`, B10 step 2) with grouped queries;
errors are answers with status 400 or above; webhook test deliveries are left out.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.modules.analytics.rules import jround
from app.modules.auth.sessions import Principal
from app.modules.dashboard import common as C
from app.modules.dashboard.rules import iso_day, period_from
from app.modules.forms.service import iso


def _within(clock: C.Clock, column: Any, start: int, end: int) -> Any:
    return and_(column >= clock.starts(start), column < clock.starts(end + 1))


async def calls_per_day(db: AsyncSession, tenant_id: uuid.UUID, clock: C.Clock, start: int,
                        end: int) -> list[tuple[int, int, int, int, int]]:
    """Calls per day: (day, calls, errors (400 and above), total answer time in ms, server errors (500 and above))."""
    from app.modules.api_service.models import ApiRequestLog as L
    from app.modules.dashboard.rules import day_of

    day = clock.sql_day(L.at)
    rows = (await db.execute(select(
        day, func.count(), func.count().filter(L.status >= 400), func.coalesce(func.sum(L.duration_ms), 0),
        func.count().filter(L.status >= 500)).where(L.tenant_id == tenant_id, _within(clock, L.at, start, end))
        .group_by(day))).all()
    return [(day_of(on), calls, bad, int(ms), server) for on, calls, bad, ms, server in rows]


async def api_view(principal: Principal, query: dict[str, Any]) -> dict[str, Any]:
    from app.modules.api_service.models import ApiRequestLog as L
    from app.modules.api_service.models import ApiToken
    from app.modules.webhooks.models import Webhook, WebhookDelivery

    if not principal.can("api.view"):
        raise FrmError("FRM-PERM-1001")
    tenant_id = principal.tenant.id
    async with db_session("read", **C.scope(principal)) as db:
        clock = await C.clock_of(db, tenant_id)
        p = period_from(query, clock.today())
        series = [{"start": start, "calls": 0, "errors": 0} for start in p.buckets]
        calls = before = errors = errors_before = duration = duration_before = 0
        statuses = {"ok": 0, "client": 0, "server": 0}
        for day, total, bad, ms, server in await calls_per_day(db, tenant_id, clock, p.prev_start, p.end):
            if day < p.start:
                before, errors_before, duration_before = before + total, errors_before + bad, duration_before + ms
                continue
            calls, errors, duration = calls + total, errors + bad, duration + ms
            statuses["server"] += server
            statuses["client"] += bad - server
            statuses["ok"] += total - bad
            i = p.bucket_of(day)
            if i is not None:
                series[i]["calls"] += total
                series[i]["errors"] += bad
        in_period = (L.tenant_id == tenant_id, _within(clock, L.at, p.start, p.end))

        # Endpoints (names as they were at the latest call), busiest first
        latest = lambda column: func.array_agg(aggregate_order_by(column, L.at.desc()))[1]  # noqa: E731
        endpoints = [{"id": str(endpoint_id), "name": name or "", "service": service, "calls": total, "errors": bad,
                      "latency_ms": jround(ms / total) if total else 0}
                     for endpoint_id, name, service, total, bad, ms in (await db.execute(select(
                         L.endpoint_id, latest(L.endpoint_name), latest(L.service_name), func.count(),
                         func.count().filter(L.status >= 400), func.coalesce(func.sum(L.duration_ms), 0))
                         .where(*in_period, L.endpoint_id.is_not(None)).group_by(L.endpoint_id)
                         .order_by(func.count().desc(), func.min(L.at)).limit(8))).all()]

        # Tokens still working, busiest first
        used = {token_id: (total, last) for token_id, total, last in (await db.execute(select(
            L.token_id, func.count(), func.max(L.at)).where(*in_period, L.token_id.is_not(None))
            .group_by(L.token_id))).all()}
        now = datetime.now(UTC)
        tokens = []
        for token in (await db.execute(select(ApiToken).where(
                ApiToken.tenant_id == tenant_id, ApiToken.deleted_at.is_(None), ApiToken.revoked_at.is_(None),
                or_(ApiToken.expires_at.is_(None), ApiToken.expires_at > now)).order_by(ApiToken.created_at))).scalars():
            total, last = used.get(token.id, (0, None))
            moments = [m for m in (last, token.last_used_at) if m is not None]
            tokens.append({"id": str(token.id), "name": token.name, "mode": token.mode, "calls": total,
                           "last_used_at": iso(max(moments)) if moments else None, "expires_at": iso(token.expires_at)})
        tokens.sort(key=lambda t: -t["calls"])

        # Webhooks and their deliveries (tests left out)
        hooks = {"active": 0, "failing": 0, "paused": 0, "delivered": 0, "failed": 0}
        for enabled, failures in (await db.execute(select(Webhook.enabled, Webhook.consecutive_failures).where(
                Webhook.tenant_id == tenant_id, Webhook.deleted_at.is_(None)))).all():
            hooks["paused" if not enabled else "failing" if failures > 0 else "active"] += 1
        D = WebhookDelivery
        current = _within(clock, D.at, p.start, p.end)
        delivered_now, failed_now, delivered_before = (await db.execute(select(
            func.count().filter(current, D.status == "delivered"), func.count().filter(current, D.status == "failed"),
            func.count().filter(_within(clock, D.at, p.prev_start, p.start - 1), D.status == "delivered"))
            .join(Webhook, and_(Webhook.tenant_id == D.tenant_id, Webhook.id == D.webhook_id))
            .where(D.tenant_id == tenant_id, D.test.is_(False), Webhook.deleted_at.is_(None),
                   _within(clock, D.at, p.prev_start, p.end)))).one()
        hooks["delivered"], hooks["failed"] = delivered_now, failed_now

        # The latest calls that went wrong
        failed = [{"id": str(row.id), "at": iso(row.at), "method": row.method, "path": row.path, "status": row.status,
                   "code": row.code} for row in (await db.execute(select(
                       L.id, L.at, L.method, L.path, L.status, L.code).where(*in_period, L.status >= 400)
                       .order_by(L.at.desc()).limit(6))).all()]

    def success(good: int, total: int) -> float:
        return jround(good / total * 1000) / 10 if total else 100

    return {
        "from": iso_day(p.start), "to": iso_day(p.end), "group": p.group,
        "kpis": {
            "calls": {"value": calls, "previous": before},
            "success_rate": {"value": success(calls - errors, calls),
                             "previous": success(before - errors_before, before) if before else None},
            "latency": {"value": jround(duration / calls) if calls else 0,
                        "previous": jround(duration_before / before) if before else None},
            "errors": {"value": errors, "previous": errors_before},
            "deliveries": {"value": hooks["delivered"], "previous": delivered_before},
        },
        "series": series,
        "endpoints": endpoints,
        "statuses": statuses,
        "tokens": tokens[:6],
        "webhooks": hooks,
        "errors": failed,
    }


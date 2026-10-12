"""Dashboard, Workspace view (F21 M1; mock: routes/dashboard.ts): every area at a glance and what needs attention.

Any member; every number follows the person's role and folder access: responses only of forms whose responses they
may see; data sources with `data.view`, the API service with `api.view`, the plan with `settings.view`. `folder` and
`owner` narrow the forms counted (data sources, the API service and the plan stay workspace-wide).

Until subscriptions arrive (B15) the plan is the workspace's `plan_id`: no payment due, card or renewal items yet;
AI credits used read 0 until the assistant (B13).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.db.session import db_session
from app.modules.analytics.rules import jround, rate, rate_of
from app.modules.auth.sessions import Principal
from app.modules.dashboard import common as C
from app.modules.dashboard.rules import iso_day, period_from
from app.modules.forms.access import viewer_for
from app.modules.forms.service import iso

RANK = {"payment_due": 0, "connection_failing": 1, "webhook_failing": 2, "form_full": 3, "plan_forms": 4,
        "form_closing": 5, "card_expiring": 6, "connection_attention": 7, "to_review": 8}


async def workspace_view(principal: Principal, query: dict[str, Any]) -> dict[str, Any]:
    tenant_id = principal.tenant.id
    async with db_session("read", **C.scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        clock = await C.clock_of(db, tenant_id)
        p = period_from(query, clock.today())
        series = [{"start": start, "responses": 0, "starts": 0, "api_calls": 0} for start in p.buckets]

        # Forms and their responses (only forms whose responses this person may see count)
        everything = await C.visible_forms(db, viewer, tenant_id)
        scope = C.filter_of(query)
        forms = [f for f in everything if scope.matches(C.form_folder(f, viewer), str(f.owner_id))]
        counted = C.with_responses(forms, viewer)
        ids = [f.id for f in counted]
        per_day = await C.responses_per_day(db, tenant_id, ids, clock, p.prev_start, p.end)
        new = await C.to_review(db, tenant_id, ids)

        responses = previous = starts = prev_starts = review = active = prev_active = 0
        top: list[dict[str, Any]] = []
        for form in counted:
            r = rate_of(form.completion_rate)
            trend = [0] * len(p.buckets)
            own = own_prev = 0
            for day, count in per_day.get(form.id, {}).items():
                if p.start <= day <= p.end:
                    own += count
                    i = p.bucket_of(day)
                    if i is not None:
                        series[i]["responses"] += count
                        trend[i] += count
                elif p.prev_start <= day < p.start:
                    own_prev += count
            own_new = new.get(form.id, 0)
            responses += own
            previous += own_prev
            starts += jround(own / r)
            prev_starts += jround(own_prev / r)
            review += own_new
            active += bool(own)
            prev_active += bool(own_prev)
            for i, n in enumerate(trend):
                series[i]["starts"] += jround(n / r)
            if own or own_new:
                top.append({"id": str(form.id), "name": form.name, "status": form.status, "responses": own,
                            "previous": own_prev, "completion_rate": jround(r * 1000) / 10, "to_review": own_new,
                            "trend": trend})
        top.sort(key=lambda t: (-t["responses"], -t["to_review"]))

        # What needs attention, most urgent first
        attention: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for form in forms:
            if form.status != "published":
                continue
            if form.closes_at and now < form.closes_at < now + timedelta(days=7):
                attention.append({"kind": "form_closing", "name": form.name, "count": None, "at": iso(form.closes_at),
                                  "link": f"/forms/{form.id}/share"})
            if form.response_limit and form.responses_count >= form.response_limit * 0.9:
                attention.append({"kind": "form_full", "name": form.name, "count": form.response_limit, "at": None,
                                  "link": f"/forms/{form.id}/share"})
        data_area = None
        if principal.can("data.view"):
            from app.modules.data_sources import service as sources

            found = await sources.sources_of(db, tenant_id)
            facts = await sources.Facts().load(db, tenant_id, found)
            statuses = [sources.status_of_source(s, facts.test_of(s)) for s in found]
            for source, status in zip(found, statuses, strict=True):
                if status in ("failing", "attention"):
                    attention.append({"kind": f"connection_{status}", "name": source.name, "count": None, "at": None,
                                      "link": f"/data-sources/connections/{source.id}"})
            data_area = {"connections": len(found), "connected": statuses.count("connected"),
                         "failing": statuses.count("failing")}
        api_area = None
        if principal.can("api.view"):
            from app.modules.api_service.models import ApiService
            from app.modules.dashboard.api_view import calls_per_day
            from app.modules.webhooks.models import Webhook

            for hook in (await db.execute(select(Webhook).where(
                    Webhook.tenant_id == tenant_id, Webhook.deleted_at.is_(None)).order_by(Webhook.created_at))).scalars():
                if hook.enabled and hook.consecutive_failures > 0:
                    attention.append({"kind": "webhook_failing", "name": hook.name, "count": hook.consecutive_failures,
                                      "at": None, "link": "/api-service/webhooks"})
            calls = before = errors = 0
            for day, total, bad, _slow, _server in await calls_per_day(db, tenant_id, clock, p.prev_start, p.end):
                if day >= p.start:
                    calls += total
                    errors += bad
                    i = p.bucket_of(day)
                    if i is not None:
                        series[i]["api_calls"] += total
                else:
                    before += total
            services = (await db.execute(select(func.count()).select_from(ApiService).where(
                ApiService.tenant_id == tenant_id, ApiService.deleted_at.is_(None)))).scalar_one()
            api_area = {"calls": calls, "previous": before, "errors": errors, "services": services}
        plan_area = None
        if principal.can("settings.view"):
            from app.modules.billing.service import plan_of
            from app.modules.forms.models import Form

            plan = plan_of(principal.tenant.plan_id)
            all_forms = (await db.execute(select(func.count()).select_from(Form).where(
                Form.tenant_id == tenant_id, Form.deleted_at.is_(None), Form.purged_at.is_(None)))).scalar_one()
            limit = plan["limits"]["forms"]
            if limit is not None and all_forms >= limit * 0.8:
                attention.append({"kind": "plan_forms", "name": None, "count": limit, "at": None, "link": "/settings/plans"})
            plan_area = {"plan": plan["id"], "forms": all_forms, "forms_limit": limit, "ai_used": 0,
                         "ai_limit": plan["limits"]["ai_credits"]}
    attention.sort(key=lambda item: RANK[item["kind"]])
    if review:
        attention.append({"kind": "to_review", "name": None, "count": review, "at": None, "link": "/responses?review=new"})

    # What is coming up (the next 60 days)
    timeline: list[dict[str, Any]] = []
    soon = now + timedelta(days=60)
    for form in forms:
        if form.opens_at and now < form.opens_at < soon:
            timeline.append({"kind": "opens", "name": form.name, "at": iso(form.opens_at), "link": f"/forms/{form.id}",
                             "_at": form.opens_at})
        if form.status == "published" and form.closes_at and now < form.closes_at < soon:
            timeline.append({"kind": "closes", "name": form.name, "at": iso(form.closes_at), "link": f"/forms/{form.id}",
                             "_at": form.closes_at})
    timeline.sort(key=lambda item: item["_at"])

    def by_status(status: str) -> int:
        return sum(1 for f in forms if f.status == status)

    return {
        "from": iso_day(p.start), "to": iso_day(p.end), "group": p.group,
        "new_workspace": not everything and not scope.filtered,
        "kpis": {
            "responses": {"value": responses, "previous": previous},
            "completion_rate": {"value": rate(responses, starts), "previous": rate(previous, prev_starts) if prev_starts else None},
            "active_forms": {"value": active, "previous": prev_active},
            "to_review": {"value": review, "previous": None},
            "attention": {"value": sum(1 for a in attention if a["kind"] != "to_review"), "previous": None},
        },
        "series": series,
        "top_forms": top[:6],
        "attention": attention[:8],
        "timeline": [{k: v for k, v in item.items() if k != "_at"} for item in timeline[:6]],
        "areas": {
            "forms": {"total": len(forms), "published": by_status("published"), "drafts": by_status("draft"),
                      "closed": by_status("closed")},
            "data": data_area, "api": api_area, "plan": plan_area,
        },
    }

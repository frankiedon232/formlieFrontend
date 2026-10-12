"""Dashboard, Data sources view (F21 M3; mock: routes/dashboardData.ts; moved here from B9): the connections at
work. Needs `data.view` (else FRM-PERM-1001). Operations come from the daily counts per connection
(`datasource_ops_daily`, kept by UTC day), stored responses from `destination_deliveries`, what people did from the
audit trail's data area. Failing connections first in the health list.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, select

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.modules.analytics.rules import jround
from app.modules.auth.sessions import Principal
from app.modules.dashboard import common as C
from app.modules.dashboard.rules import date_of, day_of, iso_day, period_from
from app.modules.forms.service import iso


async def data_view(principal: Principal, query: dict[str, Any]) -> dict[str, Any]:
    from app.modules.audit.models import AuditLog
    from app.modules.data_sources import service as sources
    from app.modules.data_sources.activity import ACTIVITY_KINDS, kind_of_action
    from app.modules.data_sources.models import DataSourceOpsDaily as Ops
    from app.modules.destinations.models import DestinationDelivery as Delivery
    from app.modules.destinations.models import ResponseDestination as Destination
    from app.modules.forms.models import Form

    if not principal.can("data.view"):
        raise FrmError("FRM-PERM-1001")
    tenant_id = principal.tenant.id
    async with db_session("read", **C.scope(principal)) as db:
        clock = await C.clock_of(db, tenant_id)
        p = period_from(query, clock.today())
        series = [{"start": start, "operations": 0, "deliveries": 0} for start in p.buckets]
        found = await sources.sources_of(db, tenant_id)
        facts = await sources.Facts().load(db, tenant_id, found)

        # Operations per day on each connection
        ops: dict[Any, int] = {}
        operations = operations_before = 0
        for source_id, on, count in (await db.execute(select(Ops.datasource_id, Ops.day, Ops.count).where(
                Ops.tenant_id == tenant_id, Ops.day >= date_of(p.prev_start), Ops.day <= date_of(p.end)))).all():
            day = day_of(on)
            if day >= p.start:
                operations += count
                ops[source_id] = ops.get(source_id, 0) + count
                i = p.bucket_of(day)
                if i is not None:
                    series[i]["operations"] += count
            else:
                operations_before += count
        connections, latencies, failing = [], [], 0
        for source in found:
            test = facts.test_of(source)
            status = sources.status_of_source(source, test)
            failing += status == "failing"
            checks = facts.checks.get(source.id, [])
            latency = checks[0].latency_ms if checks else (test.latency_ms if test and test.status != "running" else None)
            checked = iso(checks[0].at) if checks else (iso(test.finished_at) if test else None)
            if latency is not None:
                latencies.append(latency)
            connections.append({"id": str(source.id), "name": source.name, "engine": source.engine, "status": status,
                                "latency_ms": latency, "last_checked_at": checked, "operations": ops.get(source.id, 0)})
        connections.sort(key=lambda c: (c["status"] != "failing", -c["operations"]))

        # Responses stored in the workspace's databases (forms that still exist)
        live = and_(Destination.tenant_id == tenant_id, Destination.deleted_at.is_(None), Form.deleted_at.is_(None))
        stored_forms = (await db.execute(select(func.count()).select_from(Destination).join(
            Form, and_(Form.tenant_id == Destination.tenant_id, Form.id == Destination.form_id)).where(live))).scalar_one()
        storage = {"forms": stored_forms, "sent": 0, "pending": 0, "failed": 0}
        sent_at = func.coalesce(Delivery.sent_at, Delivery.at)
        day = clock.sql_day(sent_at)
        deliveries_before = 0
        base = (select(Delivery.status, day, func.count())
                .join(Destination, and_(Destination.tenant_id == Delivery.tenant_id, Destination.id == Delivery.destination_id))
                .join(Form, and_(Form.tenant_id == Destination.tenant_id, Form.id == Destination.form_id))
                .where(live, Delivery.tenant_id == tenant_id))
        for status, on, count in (await db.execute(base.where(
                (Delivery.status != "sent") | and_(sent_at >= clock.starts(p.prev_start), sent_at < clock.starts(p.end + 1)))
                .group_by(Delivery.status, day))).all():
            if status in ("pending", "held"):
                storage["pending"] += count
            elif status == "failed":
                storage["failed"] += count
            elif status == "sent" and on is not None:
                at = day_of(on)
                if at >= p.start:
                    storage["sent"] += count
                    i = p.bucket_of(at)
                    if i is not None:
                        series[i]["deliveries"] += count
                else:
                    deliveries_before += count

        # What people did (the audit trail's data area)
        kinds = dict.fromkeys(ACTIVITY_KINDS, 0)
        for action, count in (await db.execute(select(AuditLog.action, func.count()).where(
                AuditLog.tenant_id == tenant_id, AuditLog.area == "data",
                AuditLog.occurred_at >= clock.starts(p.start), AuditLog.occurred_at < clock.starts(p.end + 1))
                .group_by(AuditLog.action))).all():
            kind = kind_of_action(action)
            if kind:
                kinds[kind] += count
        recent = [{"id": str(row.id), "action": row.action, "actor": row.actor_name or "", "resource": row.resource_name,
                   "at": iso(row.occurred_at)} for row in (await db.execute(select(
                       AuditLog.id, AuditLog.action, AuditLog.actor_name, AuditLog.resource_name, AuditLog.occurred_at)
                       .where(AuditLog.tenant_id == tenant_id, AuditLog.area == "data")
                       .order_by(AuditLog.occurred_at.desc()).limit(6))).all()]

    return {
        "from": iso_day(p.start), "to": iso_day(p.end), "group": p.group,
        "kpis": {
            "connections": {"value": len(found), "previous": None},
            "operations": {"value": operations, "previous": operations_before},
            "deliveries": {"value": storage["sent"], "previous": deliveries_before},
            "failing": {"value": failing, "previous": None},
            "latency": {"value": jround(sum(latencies) / len(latencies)) if latencies else 0, "previous": None},
        },
        "series": series,
        "connections": connections[:8],
        "kinds": kinds,
        "storage": storage,
        "recent": recent,
    }

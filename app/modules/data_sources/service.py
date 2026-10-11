"""Data sources as the app sees them (mock: data/dataSourceStore.ts): rows, the detail, status, uptime from real
health checks, operations per day, and the encrypted secrets. Secrets never leave the server; only which are set.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.modules.data_sources.connect import Target
from app.modules.data_sources.engines import address_of, database_name_of
from app.modules.data_sources.models import DataSource, DataSourceCheck, DataSourceOpsDaily, DataSourceTest
from app.modules.data_sources.probe import TEST_STEPS, status_of

DAY = timedelta(days=1)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def seal_secrets(secrets: dict[str, str]) -> str | None:
    return encrypt_secret(json.dumps(secrets)) if secrets else None


def open_secrets(sealed: str | None) -> dict[str, str]:
    return json.loads(decrypt_secret(sealed)) if sealed else {}


def target_of(source: DataSource) -> Target:
    return Target(source.engine, source.settings, open_secrets(source.secrets_enc))


def json_safe(settings: dict[str, Any]) -> dict[str, Any]:
    """As JSON.stringify writes it: NaN and infinities become null."""
    return {k: None if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))) else v
            for k, v in settings.items()}


# ── Tests ───────────────────────────────────────────────────────────────────────

def test_view(test: DataSourceTest) -> dict[str, Any]:
    """ConnectionTest (shared/types/datasources.ts)."""
    running = test.status == "running"
    return {
        "id": str(test.id), "status": test.status, "started_at": iso(test.started_at), "finished_at": iso(test.finished_at),
        "steps": test.steps, "server_version": None if running else test.server_version,
        "latency_ms": None if running else test.latency_ms, "permissions": [] if running else test.permissions,
        "findings": [] if running else test.findings, "schemas": [] if running else test.schemas,
        "tables_count": None if running else test.tables_count,
    }


def new_test(tenant_id: uuid.UUID, organisation_id: uuid.UUID, user_id: uuid.UUID, datasource_id: uuid.UUID | None,
             label: str, engine: str, settings: dict[str, Any], access: dict[str, Any], secrets: dict[str, str]) -> DataSourceTest:
    config = {"engine": engine, "settings": json_safe(settings), "access": access, "secrets": secrets}
    return DataSourceTest(tenant_id=tenant_id, organisation_id=organisation_id, datasource_id=datasource_id, label=label[:300],
                          status="running", steps=[{"key": k, "status": "pending", "duration_ms": None, "error_code": None}
                                                   for k in TEST_STEPS],
                          config_enc=encrypt_secret(json.dumps(config)), started_at=datetime.now(UTC), created_by=user_id)


def finished_status(test: DataSourceTest) -> str:
    return status_of(test.steps, test.findings)


# ── Rows and detail ─────────────────────────────────────────────────────────────

def status_of_source(source: DataSource, test: DataSourceTest | None) -> str:
    if not source.enabled:
        return "disabled"
    if test is None or test.status == "running":
        return "untested"
    return {"failed": "failing", "warning": "attention"}.get(test.status, "connected")


async def count_op(db: AsyncSession, source: DataSource, n: int = 1) -> None:
    """Formalie's operations on this connection today (reads, writes, checks)."""
    from sqlalchemy.dialects.postgresql import insert

    await db.execute(insert(DataSourceOpsDaily).values(
        id=uuid.uuid4(), tenant_id=source.tenant_id, organisation_id=source.organisation_id, datasource_id=source.id,
        day=datetime.now(UTC).date(), count=n).on_conflict_do_update(
        index_elements=["tenant_id", "datasource_id", "day"], set_={"count": DataSourceOpsDaily.count + n}))


class Facts:
    """What a list of connections needs, read once: last tests, recent checks, operations, forms storing there."""

    def __init__(self) -> None:
        self.tests: dict[uuid.UUID, DataSourceTest] = {}
        self.checks: dict[uuid.UUID, list[DataSourceCheck]] = {}
        self.ops: dict[uuid.UUID, dict[date, int]] = {}
        self.forms: dict[uuid.UUID, list[dict[str, str]]] = {}

    async def load(self, db: AsyncSession, tenant_id: uuid.UUID, sources: list[DataSource]) -> Facts:
        ids = [s.id for s in sources]
        if not ids:
            return self
        test_ids = [s.last_test_id for s in sources if s.last_test_id]
        if test_ids:
            for t in (await db.execute(select(DataSourceTest).where(DataSourceTest.tenant_id == tenant_id,
                                                                    DataSourceTest.id.in_(test_ids)))).scalars():
                self.tests[t.id] = t
        since = datetime.now(UTC) - 30 * DAY
        for c in (await db.execute(select(DataSourceCheck).where(
                DataSourceCheck.tenant_id == tenant_id, DataSourceCheck.datasource_id.in_(ids), DataSourceCheck.at >= since)
                .order_by(DataSourceCheck.at.desc()))).scalars():
            self.checks.setdefault(c.datasource_id, []).append(c)
        start = datetime.now(UTC).date() - timedelta(days=59)
        for o in (await db.execute(select(DataSourceOpsDaily).where(
                DataSourceOpsDaily.tenant_id == tenant_id, DataSourceOpsDaily.datasource_id.in_(ids),
                DataSourceOpsDaily.day >= start))).scalars():
            self.ops.setdefault(o.datasource_id, {})[o.day] = o.count
        from app.modules.data_sources.storage import forms_on_connections

        self.forms = await forms_on_connections(db, tenant_id, ids)
        return self

    def test_of(self, source: DataSource) -> DataSourceTest | None:
        return self.tests.get(source.last_test_id) if source.last_test_id else None


def _uptime_daily(source: DataSource, checks: list[DataSourceCheck]) -> list[dict[str, Any]]:
    today = datetime.now(UTC).date()
    by_day: dict[date, list[DataSourceCheck]] = {}
    for c in checks:
        by_day.setdefault(c.at.astimezone(UTC).date(), []).append(c)
    out = []
    for i in range(30):
        day = today - timedelta(days=29 - i)
        items = by_day.get(day)
        uptime = round(100 * sum(1 for c in items if c.status != "failed") / len(items)) if items else None
        out.append({"date": day.isoformat(), "uptime": uptime})
    return out


def row_of(source: DataSource, facts: Facts, names: Any) -> dict[str, Any]:
    """DataSourceRow (shared/types/datasources.ts)."""
    test = facts.test_of(source)
    checks = facts.checks.get(source.id, [])
    ops = facts.ops.get(source.id, {})
    today = datetime.now(UTC).date()
    daily = [{"date": (today - timedelta(days=29 - i)).isoformat(), "count": ops.get(today - timedelta(days=29 - i), 0)}
             for i in range(30)]
    days = [d["uptime"] for d in _uptime_daily(source, checks) if d["uptime"] is not None]
    latest = checks[0] if checks else None
    return {
        "id": str(source.id), "name": source.name, "engine": source.engine,
        "address": address_of(source.engine, source.settings), "database": database_name_of(source.engine, source.settings),
        "access": source.access, "status": status_of_source(source, test), "enabled": source.enabled,
        "server_version": test.server_version if test else None,
        "latency_ms": latest.latency_ms if latest else (test.latency_ms if test and test.status != "running" else None),
        "last_checked_at": iso(latest.at) if latest else (iso(test.finished_at) if test else None),
        "uptime_30d": round(sum(days) / len(days) * 10) / 10 if days else None,
        "operations_30d": sum(d["count"] for d in daily), "daily": daily,
        "forms_count": len(facts.forms.get(source.id, [])),
        "missing_permissions": sum(1 for p in (test.permissions if test else []) if p.get("status") == "missing"),
        "created_by": names.ref(source.created_by) or {"id": "", "name": ""}, "created_at": iso(source.created_at),
        "updated_at": iso(source.updated_at),
    }


def previous_ops(source: DataSource, facts: Facts) -> int:
    today = datetime.now(UTC).date()
    ops = facts.ops.get(source.id, {})
    return sum(ops.get(today - timedelta(days=n), 0) for n in range(30, 60))


def detail_of(source: DataSource, facts: Facts, names: Any) -> dict[str, Any]:
    test = facts.test_of(source)
    checks = facts.checks.get(source.id, [])
    return {
        **row_of(source, facts, names), "settings": source.settings, "secrets_set": list(source.secrets_set or []),
        "secrets_changed_at": iso(source.secrets_changed_at), "last_test": test_view(test) if test else None,
        "checks": [{"at": iso(c.at), "status": c.status, "latency_ms": c.latency_ms, "error_code": c.error_code}
                   for c in checks[:12]],
        "uptime_daily": _uptime_daily(source, checks), "forms": facts.forms.get(source.id, []),
    }


async def sources_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[DataSource]:
    return list((await db.execute(select(DataSource).where(DataSource.tenant_id == tenant_id,
                                                           DataSource.deleted_at.is_(None)).order_by(DataSource.name))).scalars())


async def name_taken(db: AsyncSession, tenant_id: uuid.UUID, name: str, except_id: uuid.UUID | None = None) -> bool:
    found = (await db.execute(select(func.count()).select_from(DataSource).where(
        DataSource.tenant_id == tenant_id, DataSource.deleted_at.is_(None), func.lower(DataSource.name) == name.lower(),
        DataSource.id != (except_id or uuid.UUID(int=0))))).scalar_one()
    return bool(found)

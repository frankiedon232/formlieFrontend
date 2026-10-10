"""Tenant isolation in the database itself (CLAUDE.md rules 1 and 6). Runs against the migrated test database.

The first tests are the CI guard: they fail as soon as a migration adds a tenant table without RLS forced,
an isolation policy, or with a DELETE grant or an ON DELETE CASCADE.
"""

from __future__ import annotations

import psycopg
import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.ids import uuid7
from tests.db.conftest import Workspace

pytestmark = pytest.mark.db

S = get_settings().db_schema

TENANT_TABLES = """
    SELECT c.oid, n.nspname, c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity, c.relispartition
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'tenant_id' AND NOT a.attisdropped
     WHERE c.relkind IN ('r', 'p') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
"""


def test_every_tenant_table_has_rls_enabled_forced_and_a_policy(owner: psycopg.Connection) -> None:
    rows = owner.execute(TENANT_TABLES).fetchall()
    names = {f"{r[1]}.{r[2]}" for r in rows}
    assert f"{S}.organisations" in names and f"{S}.event_outbox" in names
    assert not any(name.startswith("public.") for name in names), "nothing of Formalie lives in public"
    problems = []
    for oid, schema, table, _kind, enabled, forced, is_partition in rows:
        if schema == "platform":
            continue  # the tenant directory: not readable by formalie_app at all (see below)
        if not (enabled and forced):
            problems.append(f"{schema}.{table}: RLS enabled={enabled} forced={forced}")
        if not is_partition:
            policies = owner.execute("SELECT count(*) FROM pg_policy WHERE polrelid = %s", (oid,)).fetchone()[0]
            if not policies:
                problems.append(f"{schema}.{table}: no isolation policy")
    assert not problems, "\n".join(problems)


def test_runtime_roles_cannot_bypass_rls(owner: psycopg.Connection) -> None:
    rows = dict(owner.execute(
        "SELECT rolname, rolbypassrls OR rolsuper FROM pg_roles WHERE rolname IN ('formalie_app', 'formalie_readonly')"
    ).fetchall())
    assert rows == {"formalie_app": False, "formalie_readonly": False}


def test_app_cannot_hard_delete_anything(owner: psycopg.Connection) -> None:
    rows = owner.execute("""
        SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r', 'p') AND n.nspname IN (%s, 'platform')
           AND (has_table_privilege('formalie_app', c.oid, 'DELETE')
             OR has_table_privilege('formalie_app', c.oid, 'TRUNCATE'))
    """, (S,)).fetchall()
    assert rows == [], f"formalie_app may delete from {rows} (soft delete only)"


def test_no_foreign_key_cascades(owner: psycopg.Connection) -> None:
    rows = owner.execute("SELECT conname FROM pg_constraint WHERE contype = 'f' AND confdeltype IN ('c', 'n', 'd')"
                         " AND connamespace IN (SELECT oid FROM pg_namespace WHERE nspname IN (%s, 'platform'))",
                         (S,)).fetchall()
    assert rows == []


def test_partitions_exist_for_the_next_months_with_rls_forced(owner: psycopg.Connection) -> None:
    rows = owner.execute("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_inherits i
          JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = %s::regclass
    """, (f"{S}.event_outbox",)).fetchall()
    assert len(rows) >= 4
    assert all(enabled and forced for _, enabled, forced in rows)


# ── Cross-tenant: what formalie_app can and cannot reach ──────────────────────

async def _org_names(ws: Workspace | None) -> list[str]:
    async with db_session("write", tenant_id=ws.tenant_id if ws else None,
                          organisation_id=ws.organisation_id if ws else None) as session:
        return list((await session.execute(text("SELECT name FROM organisations"))).scalars())


async def test_a_workspace_sees_only_its_own_rows(engines, two_workspaces) -> None:  # noqa: ANN001
    a, b = two_workspaces
    assert await _org_names(a) == [f"Org {a.subdomain}"]
    assert await _org_names(b) == [f"Org {b.subdomain}"]


async def test_without_tenant_context_nothing_is_visible(engines, two_workspaces) -> None:  # noqa: ANN001
    assert await _org_names(None) == []


async def test_other_workspaces_rows_can_not_be_read_or_changed(engines, two_workspaces) -> None:  # noqa: ANN001
    a, b = two_workspaces
    async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
        found = (await session.execute(text("SELECT count(*) FROM organisations WHERE id = :id"),
                                       {"id": b.organisation_id})).scalar_one()
        assert found == 0
        changed = await session.execute(text("UPDATE organisations SET name = 'taken' WHERE id = :id"),
                                        {"id": b.organisation_id})
        assert changed.rowcount == 0
    assert await _org_names(b) == [f"Org {b.subdomain}"]


async def test_rows_can_not_be_written_into_another_workspace(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    a, b = two_workspaces
    with pytest.raises(DBAPIError, match="row-level security"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await session.execute(text(
                "INSERT INTO organisations (id, tenant_id, organisation_id, name) VALUES (:id, :t, :id, 'x')"
            ), {"id": uuid7(), "t": b.tenant_id})


async def test_moving_a_row_to_another_workspace_is_refused(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    a, b = two_workspaces
    with pytest.raises(DBAPIError, match="row-level security"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await session.execute(text("UPDATE organisations SET tenant_id = :t WHERE id = :id"),
                                  {"t": b.tenant_id, "id": a.organisation_id})


async def test_app_can_not_delete_even_its_own_rows(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    a, _ = two_workspaces
    with pytest.raises(DBAPIError, match="permission denied"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await session.execute(text("DELETE FROM organisations WHERE id = :id"), {"id": a.organisation_id})


# ── Tenant directory ──────────────────────────────────────────────────────────

async def test_app_can_not_list_tenants(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError, match="permission denied"):
        async with db_session("read") as session:
            await session.execute(text("SELECT count(*) FROM platform.tenants"))


async def test_resolve_tenant_by_current_and_old_subdomain(engines, owner) -> None:  # noqa: ANN001
    from tests.db.conftest import make_workspace

    old = f"old{uuid7().hex[-10:]}"
    ws = make_workspace(owner, status="suspended", old_subdomain=old)
    async with db_session("read") as session:
        current = (await session.execute(text("SELECT * FROM platform.resolve_tenant(:s)"),
                                         {"s": ws.subdomain.upper()})).mappings().one()
        previous = (await session.execute(text("SELECT * FROM platform.resolve_tenant(:s)"), {"s": old})).mappings().one()
        missing = (await session.execute(text("SELECT * FROM platform.resolve_tenant('nobody-here')"))).first()
    assert current["id"] == ws.tenant_id and current["status"] == "suspended"
    assert current["organisation_id"] == ws.organisation_id
    assert previous["subdomain"] == ws.subdomain
    assert missing is None


async def test_tenant_directory_resolves_through_the_cache(engines, two_workspaces) -> None:  # noqa: ANN001
    from app.modules.tenants.service import TenantDirectory

    a, _ = two_workspaces
    directory = TenantDirectory()
    info = await directory.by_subdomain(a.subdomain)
    assert info is not None and info.id == a.tenant_id and info.organisation_id == a.organisation_id
    assert await directory.by_subdomain("nobody-here") is None
    assert (await directory.by_subdomain(a.subdomain)) == info  # from L1 now


# ── Outbox ────────────────────────────────────────────────────────────────────

async def test_app_can_add_events_but_not_read_them(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    from app.core.events.outbox import record_event

    a, b = two_workspaces
    async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
        await record_event(session, "test.happened", {"ref": "x"}, tenant_id=a.tenant_id,
                           organisation_id=a.organisation_id)
    with pytest.raises(DBAPIError, match="permission denied"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await session.execute(text("SELECT count(*) FROM event_outbox"))
    with pytest.raises(DBAPIError, match="row-level security"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await record_event(session, "test.happened", tenant_id=b.tenant_id, organisation_id=b.organisation_id)


async def test_relay_publishes_committed_events_once(engines, two_workspaces, worker_dsn) -> None:  # noqa: ANN001
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.events.outbox import record_event
    from app.core.events.tasks import relay_once
    from app.workers.db import _sync_url

    a, _ = two_workspaces
    async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
        event_id = await record_event(session, "test.relayed", {"n": 1}, tenant_id=a.tenant_id,
                                      organisation_id=a.organisation_id)

    class FakeBus:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def publish(self, event) -> None:  # noqa: ANN001
            self.sent.append(str(event.event_id))

    bus = FakeBus()
    engine = create_engine(_sync_url(worker_dsn))
    try:
        for _ in range(3):
            with Session(engine) as session, session.begin():
                while relay_once(session, bus, 500):
                    pass
    finally:
        engine.dispose()
    assert bus.sent.count(str(event_id)) == 1

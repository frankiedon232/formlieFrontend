"""The request_logs table: written in batches, read per workspace, never changed, bodies hidden from the platform."""

from __future__ import annotations

import psycopg
import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.ids import uuid7
from app.modules.logs.service import write_batch_async

pytestmark = pytest.mark.db

S = get_settings().db_schema


def _record(tenant=None, org=None, **extra):  # noqa: ANN001, ANN003, ANN202
    trace = str(uuid7())
    return {"id": trace, "trace_id": trace, "occurred_at": "2026-10-11T09:00:00+00:00", "method": "POST",
            "path": "/api/v1/forms", "status": 201, "client_ip": "81.2.69.160", "proxy_trusted": False,
            "tenant_id": str(tenant) if tenant else None, "organisation_id": str(org) if org else None,
            "request_headers": {"content-type": "application/json"}, "request_body": {"name": "Survey"},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36", **extra}


async def test_batches_are_written_and_each_workspace_reads_only_its_own(engines, two_workspaces, owner, monkeypatch, tmp_path) -> None:  # noqa: ANN001, E501
    from app.core.logging.geo import GeoLookup

    monkeypatch.setattr("app.modules.logs.service.get_geo", lambda: GeoLookup(tmp_path))  # no MaxMind files: the same on every machine
    a, b = two_workspaces
    records = [_record(a.tenant_id, a.organisation_id), _record(b.tenant_id, b.organisation_id), _record()]
    assert await write_batch_async(records) == 3
    assert await write_batch_async(records[:1]) == 1  # a replay is skipped, not duplicated

    # The app may only add rows. Reading (later: the workspace's own security pages) is per workspace, under RLS.
    with owner.transaction():
        owner.execute("SELECT set_config('app.tenant_id', %s, true), set_config('app.organisation_id', %s, true)",
                      (str(a.tenant_id), str(a.organisation_id)))
        rows = owner.execute(f"SELECT trace_id, browser, geo_source, request_body FROM {S}.request_logs "
                             "WHERE trace_id = ANY(%s)", ([r["trace_id"] for r in records],)).fetchall()
    assert [r[0] for r in rows] == [records[0]["trace_id"]]
    assert rows[0][1] == "Chrome" and rows[0][2] == "none" and rows[0][3] == {"name": "Survey"}


async def test_the_app_can_not_read_request_logs(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    a, _ = two_workspaces
    with pytest.raises(DBAPIError, match="permission denied"):
        async with db_session("read", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
            await session.execute(text("SELECT count(*) FROM request_logs"))


async def test_request_logs_can_not_be_changed_or_deleted(engines, two_workspaces) -> None:  # noqa: ANN001
    from sqlalchemy.exc import DBAPIError

    a, _ = two_workspaces
    record = _record(a.tenant_id, a.organisation_id)
    await write_batch_async([record])
    for statement in ("UPDATE request_logs SET status = 200 WHERE trace_id = :t",
                      "DELETE FROM request_logs WHERE trace_id = :t"):
        with pytest.raises(DBAPIError, match="permission denied"):
            async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as session:
                await session.execute(text(statement), {"t": record["trace_id"]})


def test_platform_reader_sees_everything_but_the_bodies(owner: psycopg.Connection) -> None:
    def can(column: str) -> bool:
        return owner.execute("SELECT has_column_privilege('platform_reader', %s, %s, 'SELECT')",
                             (f"{S}.request_logs", column)).fetchone()[0]

    assert can("client_ip") and can("city") and can("request_headers") and can("route")
    assert not can("request_body") and not can("request_body_text") and not can("response_body")


def test_request_logs_are_partitioned_by_month(owner: psycopg.Connection) -> None:
    count = owner.execute("SELECT count(*) FROM pg_inherits WHERE inhparent = %s::regclass",
                          (f"{S}.request_logs",)).fetchone()[0]
    assert count >= 4

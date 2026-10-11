"""Data sources (B9) against a real "customer" PostgreSQL database (scripts/setup_customer_pg.py): the plan's
engines, field checks, a connection test step by step in the worker, create with that test, the detail without
secrets, changing settings, credentials and access, enable / disable, test now, duplicate, delete, health checks,
the audit trail and another workspace."""

from __future__ import annotations

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.modules.data_sources import tasks
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def customer() -> dict:
    url = get_settings().test_postgres_url
    if url is None:
        pytest.skip("TEST_POSTGRES_URL not set (scripts/setup_customer_pg.py)")
    u = make_url(url.get_secret_value())
    return {"settings": {"host": u.host, "port": u.port, "database": u.database, "username": u.username,
                         "ssl_mode": "prefer", "connect_timeout": 5}, "secrets": {"password": u.password}}


async def on_plan(owner_dsn: str, sub: str, plan: str) -> None:
    conn = await asyncpg.connect(owner_dsn.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        await conn.execute("UPDATE platform.tenants SET plan_id = $1 WHERE subdomain = $2", plan, sub)
    finally:
        await conn.close()


@pytest.fixture
def tests_run(monkeypatch: pytest.MonkeyPatch) -> list:
    queued: list = []
    monkeypatch.setattr(tasks, "dispatch_test", queued.append)
    monkeypatch.setattr(get_settings(), "datasources_allow_local", True)
    return queued


async def run(queued: list) -> None:
    while queued:
        test = queued.pop(0)
        await tasks.run_connection_test(test.id, test.tenant_id, test.organisation_id)


async def test_data_sources_from_start_to_finish(app, owner_dsn, tests_run) -> None:  # noqa: ANN001
    db = customer()
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        access = {"table_prefix": "formalie_", "tables_schema": "", "other": "read_write", "schemas": []}

        # Field checks and the plan's engines
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": {**db["settings"], "host": "localhost", "port": 99999}, "access": access})
        assert {d["field"]: d["message"] for d in reply["error"]["details"]} == {
            "host": "host_blocked", "port": "port", "password": "required"}
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "oracle", "settings": {}, "access": access})
        assert reply["success"] or reply["error"]["code"] == "FRM-GEN-1002"

        # A test, step by step, in the worker
        status, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": db["settings"], "access": access, "secrets": db["secrets"]})
        assert status == 201, reply
        test_id = reply["data"]["id"]
        _, reply = await owner.request("GET", f"/datasources/tests/{test_id}")
        assert reply["data"]["status"] == "running" and reply["data"]["server_version"] is None
        await run(tests_run)
        _, reply = await owner.request("GET", f"/datasources/tests/{test_id}")
        test = reply["data"]
        assert [s["status"] for s in test["steps"]] == ["passed", "skipped", "warning", "passed", "passed", "passed"]
        assert test["status"] == "warning" and test["findings"] == ["tls_off"]  # TLS off: worth a look
        assert test["server_version"] and test["latency_ms"] is not None and "public" in test["schemas"]
        assert {p["operation"]: p["status"] for p in test["permissions"]}["create_table"] == "granted"

        # Create with that test; no secret ever comes back
        status, reply = await owner.request("POST", "/datasources", body={
            "name": "Cases", "engine": "postgresql", "settings": db["settings"], "access": access,
            "secrets": db["secrets"], "test_id": test_id})
        assert status == 201, reply
        source = reply["data"]
        assert source["status"] == "attention" and source["secrets_set"] == ["password"] and source["last_test"]["id"] == test_id
        assert db["secrets"]["password"] not in str(reply) and source["can"] == {"edit": True, "delete": True}
        assert source["address"] == f"{db['settings']['host']}:{db['settings']['port']}"
        _, reply = await owner.request("POST", "/datasources", body={
            "name": "cases", "engine": "postgresql", "settings": db["settings"], "access": access, "secrets": db["secrets"]})
        assert reply["error"]["code"] == "FRM-DEST-1007"

        # A wrong password: the test fails at sign-in
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": db["settings"], "access": access, "secrets": {"password": "wrong"},
            "datasource_id": source["id"]})
        await run(tests_run)
        _, reply = await owner.request("GET", f"/datasources/tests/{reply['data']['id']}")
        assert reply["data"]["status"] == "failed"
        assert next(s for s in reply["data"]["steps"] if s["key"] == "sign_in")["error_code"] == "FRM-DEST-1002"

        # Change the access (needs a new test), test now, disable
        _, reply = await owner.request("PATCH", f"/datasources/{source['id']}", body={"access": {**access, "other": "none"}})
        assert reply["data"]["status"] == "untested" and reply["data"]["access"]["other"] == "none"
        _, reply = await owner.request("POST", f"/datasources/{source['id']}/test", body={})
        await run(tests_run)
        _, reply = await owner.request("GET", f"/datasources/{source['id']}")
        assert reply["data"]["status"] == "attention" and reply["data"]["operations_30d"] >= 1
        _, reply = await owner.request("PATCH", f"/datasources/{source['id']}", body={"enabled": False})
        assert reply["data"]["status"] == "disabled"
        _, reply = await owner.request("POST", f"/datasources/{source['id']}/test", body={})
        assert reply["error"]["code"] == "FRM-DEST-1009"
        await owner.request("PATCH", f"/datasources/{source['id']}", body={"enabled": True})

        # Health checks (Beat): one passed check for this connection
        await tasks.check_all()
        _, reply = await owner.request("GET", f"/datasources/{source['id']}")
        assert reply["data"]["checks"] and reply["data"]["checks"][0]["status"] == "passed"
        assert reply["data"]["uptime_daily"][-1]["uptime"] == 100 and reply["data"]["uptime_30d"] == 100

        # List, insights, duplicate, credentials, delete
        _, reply = await owner.request("GET", "/datasources", query={"filter[engine]": "postgresql"})
        assert [r["name"] for r in reply["data"]] == ["Cases"]
        _, reply = await owner.request("GET", "/datasources/insights")
        assert reply["data"]["total"] == 1 and reply["data"]["by_status"]["attention"] == 1
        _, reply = await owner.request("POST", f"/datasources/{source['id']}/duplicate", body={})
        copy = reply["data"]
        assert copy["name"] == "Cases (copy)" and copy["status"] == "untested" and copy["secrets_set"] == ["password"]
        _, reply = await owner.request("PATCH", f"/datasources/{copy['id']}", body={"secrets": {"password": "new-one"}})
        assert reply["success"] and reply["data"]["secrets_changed_at"]
        _, reply = await owner.request("DELETE", f"/datasources/{copy['id']}")
        assert reply["data"] == {"deleted": True}

        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100"})
        actions = {row["action"] for row in trail["data"]}
        assert {"data.connection_created", "data.connection_tested", "data.connection_updated", "data.connection_disabled",
                "data.credentials_changed", "data.connection_duplicated", "data.connection_deleted"} <= actions

    # A workspace whose plan has no PostgreSQL; and another workspace sees nothing
    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": db["settings"], "access": access, "secrets": db["secrets"]})
        assert reply["error"]["code"] in ("FRM-PLAN-1002", "FRM-PERM-1001")
        _, reply = await stranger.request("GET", f"/datasources/{source['id']}")
        assert reply["error"]["code"] in ("FRM-GEN-1004", "FRM-PERM-1001")

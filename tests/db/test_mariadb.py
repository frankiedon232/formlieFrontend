"""Data sources on MariaDB (B9), live, once `scripts/wsl/setup-mariadb.sh` has run and TEST_MYSQL_URL is in .env:
a connection test, a response table Formalie creates with a response written to it, the explorer's rows and a
Query editor run with a parameter. Skipped until then."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.modules.data_sources import tables as T
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import on_plan, run, tests_run  # noqa: F401  (fixture)
from tests.db.test_destinations import build, queued, send, submit  # noqa: F401  (fixture)
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db
ACCESS = {"table_prefix": "formalie_", "tables_schema": "", "other": "read_write", "schemas": []}


def mariadb() -> dict:
    url = get_settings().test_mysql_url
    if url is None:
        pytest.skip("TEST_MYSQL_URL not set (scripts/wsl/setup-mariadb.sh)")
    u = make_url(url.get_secret_value())
    return {"settings": {"host": u.host, "port": u.port or 3306, "database": u.database, "username": u.username,
                         "ssl_mode": "disabled", "connect_timeout": 5}, "secrets": {"password": u.password}}


async def test_mariadb_from_start_to_finish(app, owner_dsn, tests_run, queued) -> None:  # noqa: ANN001, F811
    db = mariadb()
    suffix = uuid.uuid4().hex[:8]
    table = f"formalie_signups_{suffix}"
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # A connection test, step by step
        status, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "mariadb", "settings": db["settings"], "access": ACCESS, "secrets": db["secrets"]})
        assert status == 201, reply
        await run(tests_run)
        _, reply = await owner.request("GET", f"/datasources/tests/{reply['data']['id']}")
        assert reply["data"]["status"] in ("passed", "warning"), reply["data"]["steps"]
        status, reply = await owner.request("POST", "/datasources", body={
            "name": "Maria", "engine": "mariadb", "settings": db["settings"], "access": ACCESS, "secrets": db["secrets"]})
        assert status == 201, reply
        sid = reply["data"]["id"]

        # A response table Formalie creates, and a response written to it
        form = await publish(owner, "Signups", build)
        _, reply = await owner.request("GET", f"/forms/{form['id']}/storage")
        fields = [{"key": f["key"], "type": f["type"]} for f in reply["data"]["fields"]]
        settings = {"write_mode": "upsert", "key_column": "response_id", "multi_value": "json", "choices": "value"}
        status, reply = await owner.request("POST", "/destinations", body={
            "form_id": form["id"], "datasource_id": sid, "settings": settings,
            "columns": T.columns_for_form("mariadb", fields, settings),
            "table": {"mode": "create", "schema": db["settings"]["database"], "name": table}})
        assert status == 201, reply
        assert {c["column"]: c["type"] for c in reply["data"]["columns"]}["fruit"] == "LONGTEXT"
        await submit(http, form["public_key"], {"full_name": "Ana Silva", "plan": "pro", "fruit": ["a"], "agree": True})
        await send(queued)
        _, reply = await owner.request("GET", f"/destinations/{reply['data']['id']}/deliveries")
        assert [d["status"] for d in reply["data"]] == ["sent"], reply["data"]

        # The explorer reads it; the Query editor runs a statement with a parameter
        _, reply = await owner.request("GET", f"/datasources/{sid}/explorer/rows",
                                       query={"schema": db["settings"]["database"], "table": table})
        assert reply["meta"]["total"] == 1 and reply["data"][0]["full_name"] == "Ana Silva" and reply["data"][0]["agree"] == 1
        _, reply = await owner.request("POST", f"/datasources/{sid}/query", body={
            "sql": f"SELECT full_name FROM `{table}` WHERE plan = :plan AND full_name LIKE '%Silva'", "params": {"plan": "pro"}})
        assert reply["data"]["rows"] == [["Ana Silva"]], reply
        _, reply = await owner.request("POST", f"/datasources/{sid}/query", body={
            "sql": f"DROP TABLE `{table}`", "confirm": True})
        assert reply["error"]["code"] == "FRM-DEST-1019"

"""Response storage (B9) against the real "customer" PostgreSQL database (scripts/setup_customer_pg.py): a form's
storage, the connection's tables, a table Formalie creates (rows written by the worker, edits updating the row,
pause and resume, a failing connection and retries, a backfill of earlier responses, a column added later), an
existing table of theirs mapped by name, the lists and insights, removing, the audit trail and another workspace."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.modules.data_sources import tables as T
from app.modules.destinations import tasks
from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_data_sources import customer, on_plan, run, tests_run  # noqa: F401  (fixture)
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db
ACCESS = {"table_prefix": "formalie_", "tables_schema": "", "other": "read_write", "schemas": []}
TAGS = [{"value": "a", "label": "Apple"}, {"value": "b", "label": "Banana"}]


def build(schema: dict) -> dict:
    out = with_field(schema, "full_name", "Full name", required=True)
    out = with_field(out, "email", "Email", type="email")
    out = with_field(out, "plan", "Plan", type="radio", options=[{"value": "basic", "label": "Basic"},
                                                                  {"value": "pro", "label": "Pro"}])
    out = with_field(out, "score", "Score", type="rating")
    out = with_field(out, "fruit", "Fruit", type="checkbox", options=TAGS)
    out = with_field(out, "agree", "I agree", type="consent")
    return out


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """No Celery here: deliveries and backfills wait until the test runs them."""
    jobs: dict[str, list] = {"deliveries": [], "backfills": []}
    monkeypatch.setattr(tasks, "dispatch_delivery", lambda t, o, d, s: jobs["deliveries"].append((t, o, d, s)))
    monkeypatch.setattr(tasks, "dispatch_backfill", lambda t, o, j, s: jobs["backfills"].append((t, o, j, s)))
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    return jobs


async def send(jobs: dict[str, list]) -> None:
    while jobs["deliveries"]:
        t, o, d, s = jobs["deliveries"].pop(0)
        await tasks.deliver(t, o, [d], s)


async def customer_db() -> asyncpg.Connection:
    url = make_url(get_settings().test_postgres_url.get_secret_value())
    return await asyncpg.connect(host=url.host, port=url.port, user=url.username, password=url.password, database=url.database)


def real(ref: str) -> uuid.UUID:
    """The id behind a reference (ids leave the server encrypted)."""
    from app.core.security.refs import get_codec

    return uuid.UUID(get_codec().decode_id(ref))


async def submit(http, key: str, data: dict) -> str:  # noqa: ANN001
    visitor = SecureClient(http)
    status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
        "data": data, "challenge": await solved(visitor, key)}, headers=session())
    assert status == 201, reply
    return reply["data"]["response_id"]


async def test_response_storage_from_start_to_finish(app, owner_dsn, tests_run, queued) -> None:  # noqa: ANN001, F811
    db = customer()
    suffix = uuid.uuid4().hex[:8]
    table, theirs = f"formalie_signups_{suffix}", f"leads_{suffix}"
    raw = await customer_db()
    await raw.execute(f'CREATE TABLE public."{theirs}" (submission_id VARCHAR(64) PRIMARY KEY, "Full_Name" VARCHAR(200), '
                      f'email VARCHAR(320), received_at TIMESTAMPTZ NOT NULL DEFAULT now(), extra INT NOT NULL)')
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    try:
        async with client_for(app, host=f"{sub}.formalie.dev") as http:
            owner = SecureClient(http)
            await sign_in(owner, email, PASSWORD)
            status, reply = await owner.request("POST", "/datasources", body={
                "name": "Cases", "engine": "postgresql", "settings": db["settings"], "access": ACCESS, "secrets": db["secrets"]})
            assert status == 201, reply
            source = reply["data"]
            form = await publish(owner, "Signups", build)
            key = form["public_key"]
            first = await submit(http, key, {"full_name": "Ana Silva", "email": "ana@example.org", "plan": "basic"})

            # The form's storage: Formalie's own until a table is set up; the connection's tables
            _, reply = await owner.request("GET", f"/forms/{form['id']}/storage")
            storage = reply["data"]
            assert storage["mode"] == "formalie" and storage["destination"] is None and storage["connections"] == 1
            assert [f["key"] for f in storage["fields"]] == ["full_name", "email", "plan", "score", "fruit", "agree"]
            assert storage["can_manage"] is True
            _, reply = await owner.request("GET", f"/datasources/{source['id']}/tables")
            found = next(t for t in reply["data"] if t["name"] == theirs)
            assert found["schema"] == "public" and found["formalie"] is False
            assert [(c["name"], c["primary"], c["nullable"]) for c in found["columns"]][:2] == [
                ("submission_id", True, False), ("Full_Name", False, True)]

            # A table Formalie creates: the name checked, the types its own, one row per response
            fields = [{"key": f["key"], "type": f["type"]} for f in storage["fields"]]
            settings = {"write_mode": "insert", "key_column": "response_id", "multi_value": "json", "choices": "value"}
            columns = [{**c, "type": "TEXT"} for c in T.columns_for_form("postgresql", fields, settings)]
            body = {"form_id": form["id"], "datasource_id": source["id"], "columns": columns, "settings": settings,
                    "table": {"mode": "create", "schema": "public", "name": "formalie_ab"}}
            _, reply = await owner.request("POST", "/destinations", body=body)
            assert reply["error"]["code"] == "FRM-GEN-1002" and reply["error"]["details"][0]["message"] == "short"
            status, reply = await owner.request("POST", "/destinations", body={**body, "table": {**body["table"], "name": table}})
            assert status == 201, reply
            dest = reply["data"]
            assert dest["table"] == {"schema": "public", "name": table, "created": True}
            assert dest["settings"]["write_mode"] == "upsert" and dest["settings"]["key_column"] == "response_id"
            assert {c["column"]: c["type"] for c in dest["columns"]}["score"] == "INTEGER"
            assert dest["not_sent"] == 1 and dest["status"] == "active" and dest["new_fields"] == 0
            _, reply = await owner.request("POST", "/destinations", body={**body, "table": {**body["table"], "name": table}})
            assert reply["error"]["code"] == "FRM-DEST-1015"

            # A new response goes to the table (the worker writes it); an edit changes the same row
            second = await submit(http, key, {"full_name": "Ben Okoro", "plan": "pro", "score": 4, "fruit": ["a", "b"],
                                              "agree": True})
            assert len(queued["deliveries"]) == 1
            await send(queued)
            row = await raw.fetchrow(f'SELECT * FROM public."{table}" WHERE response_id = $1', real(second))
            assert (row["full_name"], row["plan"], row["score"], row["agree"]) == ("Ben Okoro", "pro", 4, True)
            assert row["fruit"] == '["a","b"]' or row["fruit"] == '["a", "b"]'
            _, reply = await owner.request("PATCH", f"/responses/{second}", body={"status": "approved"})
            assert reply["success"], reply
            await send(queued)
            assert await raw.fetchval(f'SELECT count(*) FROM public."{table}"') == 1  # the same row, updated
            _, reply = await owner.request("PATCH", f"/responses/{second}", body={"data": {"full_name": "Ben Okafor"}})
            await send(queued)
            assert await raw.fetchval(f'SELECT full_name FROM public."{table}" WHERE response_id = $1', real(second)) == "Ben Okafor"

            # Earlier responses: a backfill sends them, with progress
            today = datetime.now(UTC).date().isoformat()
            status, reply = await owner.request("POST", f"/destinations/{dest['id']}/backfill", body={"from": "2020-01-01", "to": today})
            assert status == 201 and reply["data"]["backfill"]["status"] == "running" and reply["data"]["backfill"]["total"] == 1
            _, again = await owner.request("POST", f"/destinations/{dest['id']}/backfill", body={"from": "2020-01-01", "to": today})
            assert again["error"]["code"] == "FRM-DEST-1017"
            t, o, job, s = queued["backfills"].pop()
            await tasks.run_backfill(t, o, job, s)
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}")
            assert reply["data"]["backfill"]["status"] == "done" and reply["data"]["backfill"]["done"] == 1
            assert reply["data"]["not_sent"] == 0 and reply["data"]["covers_from"].startswith("2020-01-01")
            assert await raw.fetchval(f'SELECT count(*) FROM public."{table}"') == 2

            # Paused: new responses are held; resumed, they go out
            _, reply = await owner.request("PATCH", f"/destinations/{dest['id']}", body={"paused": True})
            assert reply["data"]["status"] == "paused"
            third = await submit(http, key, {"full_name": "Cara Diaz"})
            assert not queued["deliveries"]
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}/deliveries", query={"filter[status]": "held"})
            assert [d["response_id"] for d in reply["data"]] == [third]
            await owner.request("PATCH", f"/destinations/{dest['id']}", body={"paused": False})
            await send(queued)
            assert await raw.fetchval(f'SELECT count(*) FROM public."{table}"') == 3

            # The connection fails: the delivery fails with its code and waits; a retry sends it
            await owner.request("PATCH", f"/datasources/{source['id']}", body={"enabled": False})
            fourth = await submit(http, key, {"full_name": "Dev Patel"})
            await send(queued)
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}/deliveries", query={"filter[status]": "failed"})
            failed = reply["data"]
            assert [d["response_id"] for d in failed] == [fourth] and failed[0]["error_code"] == "FRM-DEST-1009"
            assert failed[0]["attempts"] == 1 and failed[0]["next_retry_at"]
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}")
            assert reply["data"]["status"] == "failing" and reply["data"]["failed"] == 1
            await owner.request("PATCH", f"/datasources/{source['id']}", body={"enabled": True})
            _, reply = await owner.request("POST", f"/destinations/{dest['id']}/retry", body={"response_ids": [fourth]})
            assert reply["data"] == {"retried": 1}
            await send(queued)
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}/deliveries")
            assert {d["status"] for d in reply["data"]} == {"sent"} and len(reply["data"]) == 4
            assert reply["data"][0]["number"] == 4 and reply["data"][0]["respondent"] == "Dev Patel"

            # A field added to the form later: a new column (ALTER TABLE … ADD)
            _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
            version = 3  # created 1, draft 2, published 3
            schema = with_field(builder["data"]["schema"], "city", "City")
            _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": version, "schema": schema})
            assert reply["success"], reply
            _, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": version + 1})
            assert reply["success"], reply
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}")
            assert reply["data"]["new_fields"] == 1 and reply["data"]["unmapped_fields"] == [
                {"key": "city", "label": "City", "column": "city", "type": "VARCHAR(1000)"}]
            _, reply = await owner.request("POST", f"/destinations/{dest['id']}/columns", body={"keys": ["city"]})
            assert reply["data"]["new_fields"] == 0 and reply["data"]["columns"][-1]["column"] == "city"
            fifth = await submit(http, key, {"full_name": "Eve Adams", "city": "Leeds"})
            await send(queued)
            assert await raw.fetchval(f'SELECT city FROM public."{table}" WHERE response_id = $1', real(fifth)) == "Leeds"

            # An existing table of theirs: Full access, every required column filled
            other = await publish(owner, "Leads", build)
            _, reply = await owner.request("GET", f"/datasources/{source['id']}/tables")
            existing = next(t for t in reply["data"] if t["name"] == theirs)
            lead_fields = [{"key": f, "label": label, "type": "short_text"} for f, label in (("full_name", "Full name"), ("email", "Email"))]
            mapped = T.match_columns(existing["columns"], lead_fields)
            lead = {"form_id": other["id"], "datasource_id": source["id"], "columns": mapped,
                    "settings": {**settings, "write_mode": "upsert", "key_column": "submission_id"},
                    "table": {"mode": "existing", "schema": "public", "name": theirs}}
            _, reply = await owner.request("POST", "/destinations", body=lead)
            assert reply["error"]["code"] == "FRM-DEST-1016" and reply["error"]["details"] == [
                {"field": "extra", "message": "required_unmapped"}]
            await raw.execute(f'ALTER TABLE public."{theirs}" ALTER COLUMN extra DROP NOT NULL')
            _, reply = await owner.request("GET", f"/datasources/{source['id']}/tables")
            mapped = T.match_columns(next(t for t in reply["data"] if t["name"] == theirs)["columns"], lead_fields)
            status, reply = await owner.request("POST", "/destinations", body={**lead, "columns": mapped})
            assert status == 201, reply
            assert reply["data"]["table"]["created"] is False
            lead_id = await submit(http, other["public_key"], {"full_name": "Fay Wong", "email": "fay@example.org"})
            await send(queued)
            row = await raw.fetchrow(f'SELECT * FROM public."{theirs}" WHERE submission_id = $1', str(real(lead_id)))
            assert (row["Full_Name"], row["email"]) == ("Fay Wong", "fay@example.org")

            # Lists, marks, insights; the connection lists its forms and can't be deleted
            _, reply = await owner.request("GET", "/destinations", query={"filter[table]": "created"})
            assert [r["form"]["name"] for r in reply["data"]] == ["Signups"] and reply["data"][0]["sent_30d"] == 5
            _, reply = await owner.request("GET", "/destinations/insights")
            assert reply["data"]["total"] == 2 and reply["data"]["by_status"]["active"] == 2
            assert reply["data"]["deliveries"]["sent"] == 6 and reply["data"]["sent_30d"] == 6
            _, reply = await owner.request("GET", "/navigation/counts")
            assert reply["data"]["destinations"] == {"total": 2, "failing": 0}
            assert reply["data"]["datasources"]["total"] == 1 and reply["data"]["datasources"]["untested"] == 1
            _, reply = await owner.request("GET", "/forms")
            marks = {r["name"]: r["storage"] for r in reply["data"]}
            assert marks["Signups"] == {"mode": "database", "datasource": "Cases", "engine": "postgresql"}
            _, reply = await owner.request("GET", "/responses/forms")
            assert {r["name"]: r["storage"]["mode"] for r in reply["data"]}["Leads"] == "database"
            _, reply = await owner.request("GET", f"/datasources/{source['id']}")
            assert sorted(f["name"] for f in reply["data"]["forms"]) == ["Leads", "Signups"] and reply["data"]["forms_count"] == 2
            _, reply = await owner.request("DELETE", f"/datasources/{source['id']}")
            assert reply["error"]["code"] == "FRM-DEST-1010"

            # Removed: back to Formalie's storage, the table stays
            _, reply = await owner.request("DELETE", f"/destinations/{dest['id']}")
            assert reply["data"] == {"removed": True}
            _, reply = await owner.request("GET", f"/forms/{form['id']}/storage")
            assert reply["data"]["mode"] == "formalie"
            assert await raw.fetchval(f'SELECT count(*) FROM public."{table}"') == 5

            # The sweep (Beat) finds nothing left to send for this workspace
            assert await tasks.sweep() >= 0
            _, reply = await owner.request("GET", f"/destinations/{dest['id']}")
            assert reply["error"]["code"] == "FRM-GEN-1004"

            _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100"})
            actions = {row["action"] for row in trail["data"]}
            assert {"data.table_created", "data.destination_created", "data.backfill_started", "data.destination_paused",
                    "data.destination_resumed", "data.deliveries_retried", "data.column_added",
                    "data.destination_removed"} <= actions

        # Another workspace sees none of it
        stranger_sub, stranger_email = await new_workspace(app)
        async with client_for(app, host=f"{stranger_sub}.formalie.dev") as http:
            stranger = SecureClient(http)
            await sign_in(stranger, stranger_email, PASSWORD)
            _, reply = await stranger.request("GET", "/destinations")
            assert reply["data"] == []
            _, reply = await stranger.request("GET", f"/datasources/{source['id']}/tables")
            assert reply["error"]["code"] == "FRM-GEN-1004"
            _, reply = await stranger.request("GET", f"/forms/{form['id']}/storage")
            assert reply["error"]["code"] == "FRM-GEN-1004"
    finally:
        await raw.execute(f'DROP TABLE IF EXISTS public."{table}"')
        await raw.execute(f'DROP TABLE IF EXISTS public."{theirs}"')
        await raw.close()

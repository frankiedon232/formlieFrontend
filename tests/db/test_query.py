"""The Query editor, exports and saved queries (B9) against the real "customer" PostgreSQL database: reading with
typed parameters, paging and the count, the database's own errors with their position, one statement at a time,
changing statements (a dry-run estimate, the confirm, Full access, never response tables), the history, exports of
a table and of results (CSV, Excel, JSON, SQL) through one-time links, saved queries, the Activity numbers and
another workspace."""

from __future__ import annotations

import json
import uuid

import pytest

from app.modules.exports import service as exports
from app.modules.exports.models import ExportJob
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import customer, on_plan, tests_run  # noqa: F401  (fixture)
from tests.db.test_destinations import customer_db
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db
ACCESS = {"table_prefix": "formalie_", "tables_schema": "", "other": "read_write", "schemas": []}


@pytest.fixture
def jobs(monkeypatch: pytest.MonkeyPatch) -> list[ExportJob]:
    queued: list[ExportJob] = []
    monkeypatch.setattr(exports, "dispatch", queued.append)
    return queued


async def built(queued: list[ExportJob]) -> None:
    while queued:
        job = queued.pop(0)
        await exports.build(job.id, job.tenant_id, job.organisation_id)


async def test_query_editor_from_start_to_finish(app, owner_dsn, tests_run, jobs) -> None:  # noqa: ANN001, F811
    db = customer()
    s = uuid.uuid4().hex[:8]
    people, own = f"people_{s}", f"formalie_answers_{s}"
    raw = await customer_db()
    await raw.execute(f'CREATE TABLE public."{people}" (id INT PRIMARY KEY, full_name VARCHAR(100), team VARCHAR(20), '
                      'score NUMERIC(6,2), meta JSONB, joined DATE)')
    for i in range(1, 31):
        await raw.execute(f'INSERT INTO public."{people}" VALUES ($1, $2, $3, $4, $5, $6)', i, f"Person {i:02d}",
                          ("Finance", "Support")[i % 2], i / 2, json.dumps({"n": i}), __import__("datetime").date(2026, 1, 1 + i % 28))
    await raw.execute(f'CREATE TABLE public."{own}" (response_id UUID PRIMARY KEY)')
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    try:
        async with client_for(app, host=f"{sub}.formalie.dev") as http:
            owner = SecureClient(http)
            await sign_in(owner, email, PASSWORD)
            _, reply = await owner.request("POST", "/datasources", body={
                "name": "Cases", "engine": "postgresql", "settings": db["settings"], "access": ACCESS, "secrets": db["secrets"]})
            sid = reply["data"]["id"]
            run = f"/datasources/{sid}/query"

            # Reading: typed parameters, a page of the result, the count
            status, reply = await owner.request("POST", run, body={
                "sql": f'SELECT id, full_name, score, meta, joined FROM public."{people}" WHERE id > :from AND team = :team ORDER BY id',
                "params": {"from": "4", "team": "Finance"}, "page_size": 5, "page": 2})
            assert status == 200, reply
            result = reply["data"]
            assert result["kind"] == "read" and result["total"] == 13 and result["capped"] is False and len(result["rows"]) == 5
            assert [c["name"] for c in result["columns"]] == ["id", "full_name", "score", "meta", "joined"]
            assert result["columns"][0]["type"] == "int4" and result["rows"][0][0] == 16 and result["rows"][0][2] == 8
            assert result["rows"][0][4] == "2026-01-17"
            _, reply = await owner.request("POST", run, body={"sql": "SELECT :missing"})
            assert reply["error"]["code"] == "FRM-DEST-1025" and reply["error"]["details"][0]["message"] == "there is no value for parameter :missing"
            _, reply = await owner.request("POST", run, body={"sql": f'SELECT nope FROM public."{people}"'})
            details = {d["field"]: d["message"] for d in reply["error"]["details"]}
            assert reply["error"]["code"] == "FRM-DEST-1025" and "nope" in details["message"] and details["position"] == "7"
            _, reply = await owner.request("POST", run, body={"sql": "SELECT 1; SELECT 2"})
            assert reply["error"]["code"] == "FRM-DEST-1026" and reply["error"]["details"][0]["message"] == "2"
            _, reply = await owner.request("POST", run, body={"sql": "SELECT pg_sleep(6)"})
            assert reply["error"]["code"] == "FRM-DEST-1011"

            # Changing: a dry run says how many rows, then the confirm runs it
            change = {"sql": f'UPDATE public."{people}" SET team = :team WHERE score >= 10', "params": {"team": "Ops"}}
            _, reply = await owner.request("POST", run, body=change)
            assert reply["error"]["code"] == "FRM-DEST-1023"
            assert {d["field"]: d["message"] for d in reply["error"]["details"]} == {
                "kind": "update", "tables": f"public.{people}", "estimate": "11"}
            assert await raw.fetchval(f'SELECT count(*) FROM public."{people}" WHERE team = \'Ops\'') == 0
            _, reply = await owner.request("POST", run, body={**change, "confirm": True})
            assert reply["data"]["rows_affected"] == 11 and reply["data"]["total"] is None
            assert await raw.fetchval(f'SELECT count(*) FROM public."{people}" WHERE team = \'Ops\'') == 11
            _, reply = await owner.request("POST", run, body={"sql": f'DELETE FROM public."{own}"', "confirm": True})
            assert reply["error"]["code"] == "FRM-DEST-1019" and reply["error"]["details"][0]["message"] == "response_table"
            _, reply = await owner.request("POST", run, body={"sql": f"CREATE TABLE public.extra_{s} (a int)", "confirm": True})
            assert reply["data"]["kind"] == "structure" and reply["data"]["rows_affected"] == 0
            await raw.execute(f"DROP TABLE public.extra_{s}")

            # The history: newest first, with problems (a confirm request isn't a run)
            _, reply = await owner.request("GET", f"/datasources/{sid}/query-history")
            history = reply["data"]
            assert history[0]["kind"] == "structure" and history[0]["ok"] is True
            assert sum(1 for h in history if not h["ok"]) == 4 and len(history) == 7  # several statements: not a run
            assert next(h for h in history if h["error_code"] == "FRM-DEST-1011")["kind"] == "read"
            _, reply = await owner.request("DELETE", f"/datasources/{sid}/query-history", query={"id": history[0]["id"]})
            _, reply = await owner.request("GET", f"/datasources/{sid}/query-history")
            assert len(reply["data"]) == 6
            await owner.request("DELETE", f"/datasources/{sid}/query-history")
            _, reply = await owner.request("GET", f"/datasources/{sid}/query-history")
            assert reply["data"] == []

            # Exports: a table (filtered, as SQL) and results (as JSON), through one-time links
            status, reply = await owner.request("POST", f"/datasources/{sid}/explorer/exports", body={
                "schema": "public", "table": people, "format": "sql", "scope": "all", "filter": {"team": "Ops"}, "sort": "id"})
            assert status == 201 and reply["data"]["status"] == "running" and reply["data"]["total"] == 11, reply
            export_id = reply["data"]["id"]
            _, reply = await owner.request("POST", f"/explorer-exports/{export_id}/link")
            assert reply["error"]["code"] == "FRM-GEN-1002"
            await built(jobs)
            _, reply = await owner.request("GET", f"/explorer-exports/{export_id}")
            assert reply["data"]["status"] == "ready" and reply["data"]["rows"] == 11 and reply["data"]["size"] > 0
            _, reply = await owner.request("POST", f"/explorer-exports/{export_id}/link")
            url = reply["data"]["url"]
            file = await http.get(url)
            assert file.status_code == 200 and file.headers["content-disposition"].startswith(f'attachment; filename="{people}.sql";')
            text = file.text
            assert text.startswith(f"-- public.{people}: 11 row(s)") and text.count("INSERT INTO") == 11 and text.rstrip().endswith("COMMIT;")
            assert (await http.get(url)).status_code == 410  # one use
            status, reply = await owner.request("POST", f"{run}/export", body={
                "sql": f'SELECT id, meta FROM public."{people}" WHERE id <= :n ORDER BY id', "params": {"n": "3"}, "format": "json", "scope": "all"})
            assert status == 201, reply
            await built(jobs)
            _, reply = await owner.request("GET", f"/explorer-exports/{reply['data']['id']}")
            assert reply["data"]["total"] == 3 and reply["data"]["capped"] is False
            _, link = await owner.request("POST", f"/explorer-exports/{reply['data']['id']}/link")
            got = json.loads((await http.get(link["data"]["url"])).text)
            assert got == [{"id": 1, "meta": {"n": 1}}, {"id": 2, "meta": {"n": 2}}, {"id": 3, "meta": {"n": 3}}]
            _, reply = await owner.request("POST", f"{run}/export", body={"sql": f'DELETE FROM public."{people}"', "format": "csv"})
            assert reply["error"]["details"] == [{"field": "sql", "message": "read_only"}]

            # Saved queries: mine or shared, runs counted, changed only by their owner
            status, reply = await owner.request("POST", "/saved-queries", body={
                "name": "Finance people", "sql": f'SELECT * FROM public."{people}" WHERE team = :team;\nSELECT 1;',
                "datasource_id": sid, "shared": True})
            assert status == 201, reply
            saved = reply["data"]
            assert saved["kind"] == "read" and saved["mine"] is True and saved["run_count"] == 0
            await owner.request("POST", run, body={"sql": f'SELECT * FROM public."{people}" WHERE team = :team',
                                                   "params": {"team": "Finance"}, "saved_id": saved["id"]})
            _, reply = await owner.request("GET", f"/saved-queries/{saved['id']}")
            assert reply["data"]["run_count"] == 1 and reply["data"]["last_run_at"] and reply["data"]["daily"][-1]["count"] == 1
            _, reply = await owner.request("POST", "/saved-queries", body={"name": "Tidy", "sql": f'DELETE FROM public."{people}" WHERE id > 100',
                                                                       "datasource_id": sid})
            _, reply = await owner.request("GET", "/saved-queries", query={"filter[kind]": "change"})
            assert [r["name"] for r in reply["data"]] == ["Tidy"]
            _, reply = await owner.request("GET", "/saved-queries/insights")
            assert reply["data"]["total"] == 2 and reply["data"]["shared"] == 1 and reply["data"]["runs_30d"] == 1
            assert reply["data"]["by_kind"] == {"read": 1, "change": 1}
            _, reply = await owner.request("PATCH", f"/saved-queries/{saved['id']}", body={"name": "Finance team", "shared": False})
            assert reply["data"]["name"] == "Finance team" and reply["data"]["shared"] is False
            _, reply = await owner.request("POST", "/saved-queries", body={"name": "x", "sql": " -- nothing ", "datasource_id": sid})
            assert reply["error"]["details"] == [{"field": "sql", "message": "required"}]

            # Activity: what happened on the connections
            _, reply = await owner.request("GET", "/datasources/activity/insights")
            insights = reply["data"]
            assert insights["by_kind"]["queries"] >= 5 and insights["by_kind"]["exports"] == 2
            assert insights["by_connection"][0]["name"] == "Cases" and insights["daily"][-1]["count"] == insights["total_30d"]

            # Read only: reading still works, changing doesn't
            await owner.request("PATCH", f"/datasources/{sid}", body={"access": {**ACCESS, "other": "read"}})
            _, reply = await owner.request("POST", run, body={**change, "confirm": True})
            assert reply["error"]["code"] == "FRM-DEST-1024"

        stranger_sub, stranger_email = await new_workspace(app)
        async with client_for(app, host=f"{stranger_sub}.formalie.dev") as http:
            stranger = SecureClient(http)
            await sign_in(stranger, stranger_email, PASSWORD)
            _, reply = await stranger.request("POST", run, body={"sql": "SELECT 1"})
            assert reply["error"]["code"] == "FRM-GEN-1004"
            _, reply = await stranger.request("GET", f"/saved-queries/{saved['id']}")
            assert reply["error"]["code"] == "FRM-GEN-1004"
            _, reply = await stranger.request("GET", f"/explorer-exports/{export_id}")
            assert reply["error"]["code"] == "FRM-EXP-1001"
    finally:
        await raw.execute(f'DROP TABLE IF EXISTS public."{people}"')
        await raw.execute(f'DROP TABLE IF EXISTS public."{own}"')
        await raw.close()

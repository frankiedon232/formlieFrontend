"""The audit trail (B2) against the seeded test database, through the encrypted channel: list, filters, search,
facets, one entry, permissions, other workspaces, and the export (job → file → one-time link)."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

import openpyxl
import pytest

from app.core.config import get_settings
from app.modules.audit import queries
from app.modules.exports import service as exports
from app.modules.exports.models import ExportJob
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


@pytest.fixture
def jobs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> list[ExportJob]:  # noqa: ANN001
    """Exports are not sent to Celery: the test runs them; files go to a temporary folder."""
    queued: list[ExportJob] = []
    settings = get_settings().model_copy(update={"storage_dir": tmp_path})
    monkeypatch.setattr("app.core.storage.get_settings", lambda: settings)
    monkeypatch.setattr(exports, "dispatch", queued.append)
    return queued


async def run_jobs(queued: list[ExportJob]) -> None:
    while queued:
        job = queued.pop(0)
        await exports.build(job.id, job.tenant_id, job.organisation_id)


async def admin_client(http) -> SecureClient:  # noqa: ANN001
    client = SecureClient(http)
    await sign_in(client, "admin@remedylegal.test")
    return client


async def test_list_filters_search_and_one_entry(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        client = await admin_client(http)
        status, reply = await client.request("GET", "/audit-logs", query={"page_size": 5})
        assert status == 200, reply
        events, meta = reply["data"], reply["meta"]
        assert meta["page"] == 1 and meta["page_size"] == 5 and meta["total"] >= 2 and len(events) <= 5
        newest = events[0]
        assert newest["action"] == "auth.login.succeeded" and newest["area"] == "auth"
        assert newest["actor"]["email"] == "admin@remedylegal.test" and len(newest["actor"]["id"]) == 27  # a reference
        assert len(newest["id"]) == 27 and newest["organisation"]["name"] == "Remedy Legal"
        assert newest["metadata"]["method"] == "password" and newest["device"]["type"] in ("desktop", "unknown")
        assert newest["occurred_at"].endswith("Z") and newest["request_id"]
        times = [e["occurred_at"] for e in events]
        assert times == sorted(times, reverse=True)

        _, oldest_first = await client.request("GET", "/audit-logs", query={"sort": "occurred_at", "page_size": 100})
        times = [e["occurred_at"] for e in oldest_first["data"]]
        assert times == sorted(times)

        actor = newest["actor"]["id"]
        _, mine = await client.request("GET", "/audit-logs", query={"filter[actor_id]": actor, "page_size": 100})
        assert mine["data"] and {e["actor"]["email"] for e in mine["data"]} == {"admin@remedylegal.test"}

        _, sent = await client.request("GET", "/audit-logs", query={"filter[action]": "auth.otp.sent,auth.logout"})
        assert sent["data"] and {e["action"] for e in sent["data"]} <= {"auth.otp.sent", "auth.logout"}

        _, failed = await client.request("GET", "/audit-logs", query={"filter[outcome]": "failure,blocked",
                                                                       "filter[area]": "auth"})
        assert all(e["outcome"] in ("failure", "blocked") for e in failed["data"])

        _, found = await client.request("GET", "/audit-logs", query={"q": "ADMIN@REMEDY"})
        assert found["meta"]["total"] >= 2
        _, none = await client.request("GET", "/audit-logs", query={"q": "100%_nothing"})
        assert none["meta"]["total"] == 0

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        _, dated = await client.request("GET", "/audit-logs", query={"from": today, "to": today})
        assert dated["meta"]["total"] >= 2
        _, before = await client.request("GET", "/audit-logs", query={"to": "2020-01-01"})
        assert before["meta"]["total"] == 0

        status, one = await client.request("GET", f"/audit-logs/{newest['id']}")
        assert status == 200 and one["data"] == newest
        _, raw = await client.request("GET", f"/audit-logs/{uuid.uuid4()}")
        assert raw["error"]["code"] == "FRM-GEN-1004"  # a typed-in id never matches

        _, facets = await client.request("GET", "/audit-logs/facets")
        names = [a["name"] for a in facets["data"]["actors"]]
        assert "Frankie Don" in names and names == sorted(names, key=str.casefold)
        assert isinstance(facets["data"]["countries"], list)


async def test_members_and_other_workspaces_see_nothing(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        client = await admin_client(http)
        _, reply = await client.request("GET", "/audit-logs", query={"page_size": 1})
        entry = reply["data"][0]["id"]
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        for path in ("/audit-logs", "/audit-logs/facets", f"/audit-logs/{entry}"):
            _, refused = await member.request("GET", path)
            assert refused["error"]["code"] == "FRM-PERM-1001", path
        _, refused = await member.request("POST", "/audit-logs/export", body={"format": "csv"})
        assert refused["error"]["code"] == "FRM-PERM-1001"
    async with client_for(app, host="samathtax.formalie.dev") as http:
        other = SecureClient(http)
        await sign_in(other, "admin@samathtax.test")
        _, reply = await other.request("GET", f"/audit-logs/{entry}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await other.request("GET", "/audit-logs", query={"page_size": 100})
        assert all(e["organisation"]["name"] == "Samath Tax" for e in reply["data"])
        assert "admin@remedylegal.test" not in {e["actor"]["email"] for e in reply["data"]}


async def test_export_job_file_and_one_time_link(app, jobs) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        client = await admin_client(http)
        status, reply = await client.request("POST", "/audit-logs/export", body={
            "format": "csv", "filters": {"filter[area]": "auth"}})
        assert status == 202, reply
        job = reply["data"]
        assert job["status"] == "queued" and job["download_url"] is None and job["rows"] >= 2
        assert job["file_name"] == f"audit-trail-remedylegal-{datetime.now(UTC):%Y-%m-%d}.csv"
        await run_jobs(jobs)

        _, polled = await client.request("GET", f"/exports/{job['id']}")
        done = polled["data"]
        assert done["status"] == "done" and done["progress"] == 100 and done["expires_at"]
        url = done["download_url"]
        assert url.startswith("/api/v1/downloads/")

        # Another workspace can't use the link
        async with client_for(app, host="samathtax.formalie.dev") as elsewhere:
            assert (await elsewhere.get(url)).status_code == 410

        response = await http.get(url)  # plain: a browser download
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["content-disposition"] == f'attachment; filename="{job["file_name"]}"'
        text = response.content.decode("utf-8")
        assert text.startswith("﻿Time (UTC),Action,Outcome,Person,Email,Item type,Item,Changes,")
        lines = text.strip("\r\n").split("\r\n")
        assert len(lines) == job["rows"] + 1 and all(",auth." in line for line in lines[1:])

        again = await http.get(url)
        assert (again.status_code, again.text) == (410, "This download link has expired. Start a new export.")

        # The export is in the trail itself
        _, trail = await client.request("GET", "/audit-logs", query={"filter[action]": "audit.exported"})
        assert trail["data"][0]["resource"]["name"] == job["file_name"]
        assert trail["data"][0]["metadata"] == {"format": "csv", "rows": str(job["rows"])}

        # Excel: the same rows, every cell text
        _, reply = await client.request("POST", "/audit-logs/export", body={"format": "xlsx"})
        await run_jobs(jobs)
        _, polled = await client.request("GET", f"/exports/{reply['data']['id']}")
        workbook = openpyxl.load_workbook(io.BytesIO((await http.get(polled["data"]["download_url"])).content))
        sheet = workbook["Audit trail"]
        assert [c.value for c in sheet[1]][:3] == ["Time (UTC)", "Action", "Outcome"]
        assert sheet.max_row == polled["data"]["rows"] + 1  # counted again when the file is made

        # Someone else in the workspace without settings.manage can't follow the job
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        _, refused = await member.request("GET", f"/exports/{job['id']}")
        assert refused["error"]["code"] == "FRM-PERM-1001"


def test_csv_cells_and_values_like_the_mock() -> None:
    assert queries.csv_cell("=SUM(A1)") == "'=SUM(A1)"
    assert queries.csv_cell("-1") == "'-1" and queries.csv_cell("@x") == "'@x"
    assert queries.csv_cell('say "hi", ok') == '"say ""hi"", ok"'
    assert queries.csv_cell("plain") == "plain"
    assert [queries.js_string(v) for v in (True, False, 2.0, 1.5, 3, None, "x")] == \
        ["true", "false", "2", "1.5", "3", "", "x"]
    event = {"occurred_at": "2026-10-11T10:00:00.000Z", "action": "settings.updated", "outcome": "success",
             "actor": {"name": "Ada", "email": "ada@example.test"}, "resource": None,
             "changes": [{"field": "require_2fa", "before": False, "after": True},
                         {"field": "name", "before": None, "after": "New"}],
             "location": {"ip": "203.0.113.7", "city": None, "country": "GB"},
             "device": {"browser": "Chrome", "os": "Windows"}, "reason": None, "request_id": "r-1"}
    row = queries.rows_of([event])[1]
    assert row[7] == "require_2fa: false → true; name: - → New" and row[11] == "Chrome / Windows"
    assert row[5] == "" and row[12] == ""

"""Analytics and the dashboard (B12) end to end: the mock's shapes key by key, numbers from real responses, API
calls and audit entries, the forms filter (folder, `none`, owner), a member who may see only some forms, the
permissions of the Data sources and API service views, and another workspace seeing none of it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.db.session import db_session
from app.modules.api_service import traffic as TR
from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_destinations import submit
from tests.db.test_forms import member_of
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

TOTALS = {"views", "starts", "completions", "completion_rate", "median_seconds"}
KPI = {"value", "previous"}


def build(schema: dict) -> dict:
    out = with_field(schema, "full_name", "Full name", required=True)
    out = with_field(out, "email", "Email", type="email")
    return with_field(out, "notes", "Notes", type="long_text")


async def publish_in(owner: SecureClient, name: str, folder_id: str) -> dict:
    """A published form made in a folder."""
    _, reply = await owner.request("POST", "/forms", body={"name": name, "folder_id": folder_id})
    form = reply["data"]
    _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
    _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": build(builder["data"]["schema"])})
    assert reply["success"], reply
    status, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 2})
    assert status == 200, reply
    return form


def workspace_keys(data: dict) -> None:
    assert set(data) == {"from", "to", "group", "new_workspace", "kpis", "series", "top_forms", "attention", "timeline", "areas"}
    assert set(data["kpis"]) == {"responses", "completion_rate", "active_forms", "to_review", "attention"}
    assert all(set(k) == KPI for k in data["kpis"].values())
    assert all(set(p) == {"start", "responses", "starts", "api_calls"} for p in data["series"])
    assert all(set(t) == {"id", "name", "status", "responses", "previous", "completion_rate", "to_review", "trend"}
               for t in data["top_forms"])
    assert all(set(a) == {"kind", "name", "count", "at", "link"} for a in data["attention"])
    assert all(set(t) == {"kind", "name", "at", "link"} for t in data["timeline"])
    assert set(data["areas"]) == {"forms", "data", "api", "plan"}
    assert set(data["areas"]["forms"]) == {"total", "published", "drafts", "closed"}


def forms_keys(data: dict) -> None:
    assert set(data) == {"from", "to", "group", "new_workspace", "kpis", "by_status", "created", "channels", "top",
                         "folders", "owners", "work"}
    assert set(data["kpis"]) == {"published", "created", "per_form", "silent", "unpublished"}
    assert set(data["by_status"]) == {"draft", "published", "closed", "archived"}
    assert set(data["channels"]) == {"link", "embed", "api"}
    assert all(set(c) == {"start", "count"} for c in data["created"])
    assert all(set(t) == {"id", "name", "status", "responses", "previous", "completion_rate"} for t in data["top"])
    assert all(set(f) == {"id", "name", "forms", "responses"} for f in data["folders"])
    assert all(set(o) == {"id", "name", "forms", "responses"} for o in data["owners"])
    assert all(set(w) == {"kind", "form", "at", "count"} and set(w["form"]) == {"id", "name"} for w in data["work"])


async def test_analytics_and_dashboard(app, superuser, monkeypatch) -> None:  # noqa: ANN001, F811
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    tenant = superuser.execute("SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s",
                               (sub,)).fetchone()
    today = datetime.now(UTC).date()
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # A new workspace: real zeros and the first steps
        _, reply = await owner.request("GET", "/dashboard")
        data = reply["data"]
        workspace_keys(data)
        assert data["new_workspace"] is True and data["group"] == "day" and len(data["series"]) == 30
        assert data["to"] == today.isoformat() and data["from"] == (today - timedelta(days=29)).isoformat()
        assert data["areas"]["plan"]["plan"] == "starter" and data["areas"]["plan"]["ai_used"] == 0
        assert data["areas"]["data"] == {"connections": 0, "connected": 0, "failing": 0}
        assert data["areas"]["api"] == {"calls": 0, "previous": 0, "errors": 0, "services": 0}

        # Forms: one in a folder with three responses, one outside with one, a draft
        _, reply = await owner.request("POST", "/folders", body={"name": "Clients"})
        folder = reply["data"]
        survey = await publish_in(owner, "Client survey", folder["id"])
        contact = await publish(owner, "Contact", build)
        _, reply = await owner.request("POST", "/forms", body={"name": "Ideas"})
        draft = reply["data"]
        for name in ("Ana Silva", "Ben Okoro", "Cara Diaz"):
            await submit(http, survey["public_key"], {"full_name": name, "notes": "Fine"})
        await submit(http, contact["public_key"], {"full_name": "Dee Lee"})

        # A member who sees only their own form (the folder is closed to them, the others not shared)
        member, member_id = await member_of(http, owner, sub)
        _, reply = await owner.request("PUT", f"/folders/{folder['id']}/access", body={"restricted": True, "roles": ["admin"]})
        assert reply["success"], reply
        for form in (contact, draft):
            _, reply = await owner.request("PUT", f"/forms/{form['id']}/share",
                                           body={"people": {"team_access": "none", "grants": []}})
            assert reply["success"], reply
        own = await publish(member, "Team lunch", build)
        await submit(http, own["public_key"], {"full_name": "Eve Ng"})

        _, reply = await owner.request("GET", "/dashboard")
        data = reply["data"]
        workspace_keys(data)
        assert data["new_workspace"] is False
        assert data["kpis"]["responses"] == {"value": 5, "previous": 0}
        assert data["kpis"]["active_forms"] == {"value": 3, "previous": 0}
        assert data["kpis"]["to_review"] == {"value": 5, "previous": None}
        assert data["series"][-1]["responses"] == 5 and sum(p["responses"] for p in data["series"]) == 5
        assert data["top_forms"][0]["name"] == "Client survey" and data["top_forms"][0]["responses"] == 3
        assert data["top_forms"][0]["trend"][-1] == 3 and data["top_forms"][0]["completion_rate"] == 68
        assert data["attention"][-1] == {"kind": "to_review", "name": None, "count": 5, "at": None,
                                         "link": "/responses?review=new"}
        assert data["areas"]["forms"] == {"total": 4, "published": 3, "drafts": 1, "closed": 0}

        # The forms filter: a folder, no folder, a person; never a raw id
        for query, names in [({"folder": folder["id"]}, ["Client survey"]), ({"folder": "none"}, ["Contact", "Team lunch"]),
                             ({"owner": member_id}, ["Team lunch"]), ({"folder": str(uuid.uuid4())}, [])]:
            _, reply = await owner.request("GET", "/dashboard", query=query)
            assert sorted(t["name"] for t in reply["data"]["top_forms"]) == names, query
            assert reply["data"]["new_workspace"] is False
        _, reply = await owner.request("GET", "/dashboard", query={"from": "2026-01-01", "to": "2026-12-31", "group": "month"})
        assert reply["data"]["group"] == "month" and [p["start"][5:] for p in reply["data"]["series"]][:2] == ["01-01", "02-01"]
        _, reply = await owner.request("GET", "/dashboard", query={"from": "2025-01-01", "to": "2026-01-01"})
        assert reply["data"]["group"] == "week" and reply["data"]["series"][0]["start"] == "2024-12-30"

        # Forms view
        _, reply = await owner.request("GET", "/dashboard/forms")
        data = reply["data"]
        forms_keys(data)
        assert data["by_status"] == {"draft": 1, "published": 3, "closed": 0, "archived": 0}
        assert data["kpis"]["created"] == {"value": 4, "previous": 0} and data["kpis"]["per_form"]["value"] == 2
        assert data["channels"]["link"] == 5 and data["created"][-1]["count"] == 4
        assert [t["name"] for t in data["top"]][0] == "Client survey" and len(data["top"]) == 3
        assert {f["name"]: (f["forms"], f["responses"]) for f in data["folders"]} == {"Clients": (1, 3), None: (3, 2)}
        assert {o["name"]: o["forms"] for o in data["owners"]} == {"Olu Ade": 3, "Mia Member": 1}
        _, reply = await owner.request("GET", "/dashboard/forms", query={"folder": folder["id"]})
        assert reply["data"]["by_status"]["published"] == 1 and reply["data"]["new_workspace"] is False

        # Data sources and API service views: the shapes, real calls from the request log
        _, reply = await owner.request("GET", "/dashboard/data")
        data = reply["data"]
        assert set(data) == {"from", "to", "group", "kpis", "series", "connections", "kinds", "storage", "recent"}
        assert set(data["kpis"]) == {"connections", "operations", "deliveries", "failing", "latency"}
        assert set(data["kinds"]) == {"queries", "rows", "structure", "exports", "storage", "connections"}
        assert data["storage"] == {"forms": 0, "sent": 0, "pending": 0, "failed": 0}
        assert all(set(p) == {"start", "operations", "deliveries"} for p in data["series"])
        now = datetime.now(UTC)
        async with db_session("write", tenant_id=tenant[0], organisation_id=tenant[1]) as db:
            from app.modules.audit.service import Actor, record

            await record(db, tenant_id=tenant[0], organisation_id=tenant[1], action="data.query_run",
                         actor=Actor.system("Olu Ade"), resource={"type": "data_source", "id": str(uuid.uuid4()), "name": "Sales"})
            for status, ms, back in ((201, 40, 0), (404, 10, 0), (500, 90, 0), (201, 60, 35)):
                await TR.record_call(db, tenant[0], tenant[1], TR.ApiCall(
                    method="POST", path="/k/apply", status=status, duration_ms=ms, ip="203.0.113.9",
                    request_id=f"req-{status}-{back}", code="FRM-GEN-1004" if status == 404 else None,
                    at=now - timedelta(days=back, minutes=1)))
        _, reply = await owner.request("GET", "/dashboard/data")
        assert reply["data"]["kinds"]["queries"] == 1 and reply["data"]["recent"][0]["action"] == "data.query_run"
        assert set(reply["data"]["recent"][0]) == {"id", "action", "actor", "resource", "at"}
        assert reply["data"]["recent"][0]["resource"] == "Sales"
        _, reply = await owner.request("GET", "/dashboard/api")
        data = reply["data"]
        assert set(data) == {"from", "to", "group", "kpis", "series", "endpoints", "statuses", "tokens", "webhooks", "errors"}
        assert data["kpis"]["calls"] == {"value": 3, "previous": 1}
        assert data["kpis"]["errors"] == {"value": 2, "previous": 0}
        assert data["kpis"]["success_rate"] == {"value": 33.3, "previous": 100}
        assert data["kpis"]["latency"] == {"value": 47, "previous": 60}
        assert data["statuses"] == {"ok": 1, "client": 1, "server": 1}
        assert data["webhooks"] == {"active": 0, "failing": 0, "paused": 0, "delivered": 0, "failed": 0}
        assert [e["status"] for e in data["errors"]] == [500, 404] or [e["status"] for e in data["errors"]] == [404, 500]
        assert set(data["errors"][0]) == {"id", "at", "method", "path", "status", "code"}
        assert data["series"][-1] == {"start": today.isoformat(), "calls": 3, "errors": 2}
        _, reply = await owner.request("GET", "/dashboard")
        assert reply["data"]["areas"]["api"] == {"calls": 3, "previous": 1, "errors": 2, "services": 0}
        assert reply["data"]["series"][-1]["api_calls"] == 3

        # Analytics: completions are real, views and starts estimated around them
        _, reply = await owner.request("GET", "/analytics/overview")
        data = reply["data"]
        assert set(data) == {"from", "to", "totals", "previous", "daily", "channels", "active_forms"}
        assert set(data["totals"]) == TOTALS and set(data["previous"]) == TOTALS and len(data["daily"]) == 30
        assert data["totals"]["completions"] == 5 and data["totals"]["starts"] >= 5 and data["channels"]["link"] == 5
        assert data["daily"][-1]["completions"] == 5 and data["previous"]["completions"] == 0
        _, again = await owner.request("GET", "/analytics/overview")
        assert again["data"] == data  # the same estimates every time
        _, reply = await owner.request("GET", "/analytics/overview", query={"form": survey["id"]})
        assert reply["data"]["totals"]["completions"] == 3
        _, reply = await owner.request("GET", "/analytics/forms", query={"sort": "name"})
        rows = reply["data"]
        assert [r["name"] for r in rows] == ["Client survey", "Contact", "Team lunch"]  # the draft without views is left out
        assert set(rows[0]) == TOTALS | {"id", "name", "status", "change", "trend", "drop_off"} and reply["meta"]["total"] == 3
        assert rows[0]["completions"] == 3 and rows[0]["change"] is None and rows[0]["trend"][-1] == 3
        if rows[0]["drop_off"]:
            assert set(rows[0]["drop_off"]) == {"page", "page_title", "field", "field_label", "rate"}
        _, reply = await owner.request("GET", "/analytics/forms", query={"q": "CONTACT", "page_size": "1"})
        assert [r["name"] for r in reply["data"]] == ["Contact"]
        _, reply = await owner.request("GET", "/analytics/forms", query={"sort": "-completions", "page": "2", "page_size": "2"})
        assert len(reply["data"]) == 1 and reply["data"][0]["completions"] == 1 and reply["meta"]["total_pages"] == 2
        _, reply = await owner.request("GET", f"/analytics/forms/{survey['id']}/funnel")
        data = reply["data"]
        assert set(data) == {"form", "totals", "pages", "fields"} and data["form"]["name"] == "Client survey"
        assert [f["key"] for f in data["fields"]] == ["full_name", "email", "notes"]
        assert set(data["fields"][0]) == {"key", "label", "type", "page", "required", "reached", "answered", "left", "seconds"}
        assert set(data["pages"][0]) == {"index", "title", "reached", "left"}
        assert data["fields"][0]["reached"] == data["totals"]["starts"]
        _, reply = await owner.request("GET", f"/analytics/forms/{draft['id']}/funnel")
        assert reply["success"] and reply["data"]["totals"]["completions"] == 0

        # The member: only their own form counts; no data sources, API service or plan
        _, reply = await member.request("GET", "/dashboard")
        data = reply["data"]
        workspace_keys(data)
        assert data["kpis"]["responses"]["value"] == 1 and [t["name"] for t in data["top_forms"]] == ["Team lunch"]
        assert data["areas"]["data"] is None and data["areas"]["api"] is None and data["areas"]["plan"] is None
        assert data["areas"]["forms"]["total"] == 1 and data["series"][-1]["api_calls"] == 0
        _, reply = await member.request("GET", "/dashboard/forms")
        assert [t["name"] for t in reply["data"]["top"]] == ["Team lunch"] and reply["data"]["owners"][0]["name"] == "Mia Member"
        for path in ("/dashboard/data", "/dashboard/api"):
            status, reply = await member.request("GET", path)
            assert status == 403 and reply["error"]["code"] == "FRM-PERM-1001", path
        _, reply = await member.request("GET", "/analytics/overview")
        assert reply["data"]["totals"]["completions"] == 1
        _, reply = await member.request("GET", "/analytics/forms")
        assert [r["name"] for r in reply["data"]] == ["Team lunch"]
        for path, query in ((f"/analytics/forms/{survey['id']}/funnel", None), ("/analytics/overview", {"form": survey["id"]})):
            status, reply = await member.request("GET", path, query=query)
            assert reply["error"]["code"] == "FRM-GEN-1004", path

    # Another workspace sees none of it
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other_sub}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", "/dashboard")
        assert reply["data"]["new_workspace"] is True and reply["data"]["kpis"]["responses"]["value"] == 0
        assert reply["data"]["areas"]["api"]["calls"] == 0
        _, reply = await stranger.request("GET", "/dashboard/api")
        assert reply["data"]["kpis"]["calls"]["value"] == 0 and reply["data"]["errors"] == []
        _, reply = await stranger.request("GET", "/analytics/forms")
        assert reply["data"] == []
        _, reply = await stranger.request("GET", f"/analytics/forms/{survey['id']}/funnel")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("GET", "/analytics/overview", query={"form": survey["id"]})
        assert reply["error"]["code"] == "FRM-GEN-1004"


async def test_days_follow_the_workspace_time_zone() -> None:
    from app.modules.dashboard.common import Clock
    from app.modules.dashboard.rules import iso_day

    late = datetime(2026, 10, 12, 23, 30, tzinfo=UTC)
    assert iso_day(Clock("UTC").day_of(late)) == "2026-10-12"
    assert iso_day(Clock("Pacific/Auckland").day_of(late)) == "2026-10-13"
    assert iso_day(Clock("America/Los_Angeles").day_of(late)) == "2026-10-12"
    assert Clock("Nowhere/Else").name == "UTC"
    assert Clock("Asia/Tokyo").starts(20738) == datetime(2026, 10, 11, 15, 0, tzinfo=UTC)

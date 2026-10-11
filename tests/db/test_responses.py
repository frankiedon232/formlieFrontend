"""Responses (B8) on a new workspace: lists with filters and search, tags, insights, the inbox, the page grouped by
form, the detail, review (status, tags, duplicate flag), edited answers checked and kept in the history, notes,
bulk changes, deleting, permissions and another workspace."""

from __future__ import annotations

import pytest

from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_forms import member_of
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def build(schema: dict) -> dict:
    out = with_field(schema, "full_name", "Full name", required=True)
    out = with_field(out, "email", "Email", type="email")
    out = with_field(out, "plan", "Plan", type="radio", options=[{"value": "basic", "label": "Basic"},
                                                                  {"value": "pro", "label": "Pro"}])
    out = with_field(out, "score", "Score", type="rating")
    out = with_field(out, "notes", "Notes", type="long_text")
    out["settings"] = {**out["settings"], "identity": {"email": "email", "verify": False}}
    return out


async def test_responses_from_start_to_finish(app, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Signups", build)
        key = form["public_key"]
        people = [("Ana Silva", "ana@example.org", "basic", 5, "Great"), ("Ben Okoro", "ben@example.org", "pro", 3, "Fine"),
                  ("Cara Diaz", "cara@example.org", "pro", 4, "Love the pro plan")]
        ids = []
        for name, mail, plan, score, notes in people:
            visitor = SecureClient(http)
            status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
                "data": {"full_name": name, "email": mail, "plan": plan, "score": score, "notes": notes},
                "challenge": await solved(visitor, key)}, headers=session())
            assert status == 201, reply
            ids.append(reply["data"]["response_id"])

        # One form's list: newest first, numbered, titled by the name it collected
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses")
        rows = reply["data"]
        assert reply["meta"]["total"] == 3 and [r["number"] for r in rows] == [3, 2, 1]
        assert rows[0]["respondent"] == {"name": "Cara Diaz", "email": "cara@example.org", "kind": "answer", "title": "Cara Diaz"}
        assert rows[0]["answered"] == 5 and rows[0]["questions"] == 5 and rows[0]["answers"]["plan"] == "pro"
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses", query={"filter[a_plan]": "pro", "sort": "number"})
        assert [r["number"] for r in reply["data"]] == [2, 3]
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses", query={"q": "pro plan"})
        assert [r["number"] for r in reply["data"]] == [3]
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses", query={"q": "#1"})
        assert [r["respondent"]["name"] for r in reply["data"]] == ["Ana Silva"]

        # Detail, review, tags, the duplicate flag, notes
        status, reply = await owner.request("GET", f"/responses/{ids[0]}")
        assert status == 200 and reply["data"]["data"]["full_name"] == "Ana Silva"
        assert reply["data"]["can"] == {"review": True, "edit": True, "delete": True, "export": True}
        assert reply["data"]["meta"]["device"] in ("Desktop", "Phone", "Tablet") and reply["data"]["history"] == []
        _, reply = await owner.request("PATCH", f"/responses/{ids[0]}", body={"status": "approved", "tags": ["vip", "vip", "follow-up"]})
        detail = reply["data"]
        assert detail["status"] == "approved" and detail["tags"] == ["vip", "follow-up"]
        assert [h["field"] for h in detail["history"]] == ["status", "tags"] or {h["field"] for h in detail["history"]} == {"status", "tags"}

        # Edited answers: checked like a submission, the original kept in the history
        _, reply = await owner.request("PATCH", f"/responses/{ids[0]}", body={"data": {"email": "not an email", "nope": 1}})
        assert {d["field"]: d["message"] for d in reply["error"]["details"]} == {
            "email": "email", "nope": "This answer can not be edited."}
        _, reply = await owner.request("PATCH", f"/responses/{ids[0]}", body={"data": {"full_name": "Ana Souza"}})
        assert reply["data"]["edited"] is True and reply["data"]["data"]["full_name"] == "Ana Souza"
        change = next(h for h in reply["data"]["history"] if h["field"] == "answer:full_name")
        assert change["before"] == "Ana Silva" and change["after"] == "Ana Souza" and change["by"]["name"] == "Olu Ade"
        _, reply = await owner.request("POST", f"/responses/{ids[0]}/notes", body={"text": "  Called her back  "})
        assert reply["data"]["notes"][0]["text"] == "Called her back" and reply["data"]["notes_count"] == 1
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses/tags")
        assert reply["data"] == [{"value": "follow-up", "count": 1}, {"value": "vip", "count": 1}]

        # Insights, the inbox, the page grouped by form
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses/insights")
        insights = reply["data"]
        assert insights["total"] == 3 and insights["new"] == 2 and insights["period"]["count"] == 3
        plan = next(q for q in insights["questions"] if q["key"] == "plan")
        assert plan["options"] == [{"value": "basic", "label": "Basic", "count": 1}, {"value": "pro", "label": "Pro", "count": 2}]
        score = next(q for q in insights["questions"] if q["key"] == "score")
        assert score["kind"] == "rating" and score["average"] == 4 and len(score["distribution"]) == 5
        _, reply = await owner.request("GET", "/responses", query={"filter[status]": "new"})
        assert reply["meta"]["total"] == 2 and reply["data"][0]["answers"] == {}
        _, reply = await owner.request("GET", "/responses/insights")
        assert reply["data"]["top_forms"] == [{"id": form["id"], "name": "Signups", "count": 3}]
        _, reply = await owner.request("GET", "/responses/forms")
        row = reply["data"][0]
        assert row["total"] == 3 and row["status_counts"] == {"new": 2, "reviewed": 0, "approved": 1, "rejected": 0}
        assert row["daily"][-1] == 3

        # The form overview and the sidebar agree with the responses
        _, reply = await owner.request("GET", f"/forms/{form['id']}/overview")
        assert reply["data"]["stats"]["responses"] == 3 and reply["data"]["daily"][-1]["count"] == 3
        assert reply["data"]["stats"]["last_response_at"] is not None
        _, reply = await owner.request("GET", "/navigation/counts")
        assert reply["data"]["responses"] == {"all": 3, "new": 2, "reviewed": 0, "approved": 1, "rejected": 0}

        # Bulk: status for all, a tag; delete one
        _, reply = await owner.request("POST", "/responses/bulk", body={"ids": [*ids, form["id"]], "action": "status", "value": "reviewed"})
        assert reply["data"] == {"done": 3, "skipped": 1}
        _, reply = await owner.request("POST", "/responses/bulk", body={"ids": ids, "action": "nope"})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("DELETE", f"/responses/{ids[2]}")
        assert reply["data"] == {"deleted": 1}
        _, reply = await owner.request("GET", f"/responses/{ids[2]}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("GET", f"/forms/{form['id']}")
        assert reply["data"]["responses_count"] == 2

        # A member with the form shared as "view": reads, but can't change answers or delete
        member, member_id = await member_of(http, owner, sub)
        await owner.request("PUT", f"/forms/{form['id']}/share", body={"people": {"team_access": "none",
                                                                                  "grants": [{"user_id": member_id, "level": "view"}]}})
        _, reply = await member.request("GET", f"/responses/{ids[0]}")
        assert reply["success"], reply
        _, reply = await member.request("PATCH", f"/responses/{ids[0]}", body={"data": {"full_name": "X"}})
        assert reply["error"]["code"] in ("FRM-PERM-1001", "FRM-GEN-1004")

        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100"})
        actions = [row["action"] for row in trail["data"]]
        assert "responses.updated" in actions and "responses.deleted" in actions

    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", f"/responses/{ids[0]}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("GET", "/responses")
        assert reply["meta"]["total"] == 0

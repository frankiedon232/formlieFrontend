"""After a response (B8): the form's response emails (team with a link, outside addresses masked and without a link,
the respondent's copy) and notifications (in the app, by email, the daily summary, an export that is ready)."""

from __future__ import annotations

import pytest

from app.modules.emails.service import SENT
from app.modules.public import router as public_router
from tests.after_queue import AFTER_SUBMIT, run_after_submit
from tests.conftest import client_for
from tests.db.test_audit_trail import jobs, run_jobs  # noqa: F401  (fixture)
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_response_emails_and_notifications(app, jobs, monkeypatch) -> None:  # noqa: ANN001, F811
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, me = await owner.request("GET", "/me")
        owner_id = me["data"]["id"]

        def build(schema: dict) -> dict:
            out = with_field(schema, "full_name", "Full name", type="full_name")
            out = with_field(out, "email", "Email", type="email")
            out = with_field(out, "colour", "Favourite colour")
            out["settings"] = {**out["settings"], "identity": {"email": "email", "verify": False},
                               "emails": {"team": [owner_id], "others": ["boss@outside.example"], "others_personal": False,
                                          "receipt_field": "email"}}
            return out
        form = await publish(owner, "Feedback", build)
        key = form["public_key"]

        before = len(SENT)
        visitor = SecureClient(http)
        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {"full_name": {"first": "Ana", "last": "Silva"}, "email": "ana@example.org", "colour": "Teal"},
            "challenge": await solved(visitor, key)}, headers=session())
        assert status == 201, reply
        assert len(AFTER_SUBMIT) == 1 and len(SENT) == before  # nothing sent during the request
        await run_after_submit()
        mails = {m["to"]: m for m in SENT[before:]}

        team = mails[email]
        assert team["key"] == "response_notification" and "Feedback" in team["subject"]
        assert "Ana Silva" in team["text"] and "Teal" in team["text"] and f"https://{sub}.formalie.dev" in team["text"]
        assert team["from_name"]  # the workspace's name
        outside = mails["boss@outside.example"]
        assert "Teal" in outside["text"] and "Ana Silva" not in outside["text"] and "A•••a" in outside["text"]
        assert f"{sub}.formalie.dev" not in outside["text"]  # no link into the portal
        receipt = mails["ana@example.org"]
        assert receipt["key"] == "response_receipt" and "Teal" in receipt["text"]

        # In the app: "new response" for everyone
        _, reply = await owner.request("GET", "/notifications")
        feed = reply["data"]
        assert feed["unread"] == 1 and feed["items"][0]["event"] == "response_new"
        assert feed["items"][0]["params"] == {"form": "Feedback"} and "/responses?response=" in feed["items"][0]["link"]
        _, reply = await owner.request("POST", "/notifications/read", body={"all": True})
        assert reply["data"]["unread"] == 0
        _, reply = await owner.request("DELETE", "/notifications/read")
        assert reply["data"]["items"] == []

        # An export that is ready tells only whoever asked for it
        await owner.request("POST", f"/forms/{form['id']}/responses/export", body={"format": "csv", "scope": "all"})
        await run_jobs(jobs)
        _, reply = await owner.request("GET", "/notifications")
        assert [i["event"] for i in reply["data"]["items"]] == ["export_ready"]

        # By email in the daily summary: new responses go to the summary, sent on demand
        _, settings = await owner.request("GET", "/settings/notifications")
        rules = settings["data"]
        rules["events"]["response_new"] = {**rules["events"]["response_new"], "email": True}
        rules["digest"] = {"enabled": True, "hour": 23}
        _, reply = await owner.request("PATCH", "/settings/notifications", body=rules)
        assert reply["success"], reply
        second = SecureClient(http)
        await second.request("POST", f"/public/forms/{key}/submit", body={
            "data": {"email": "ben@example.org", "colour": "Red"}, "challenge": await solved(second, key)}, headers=session())
        before = len(SENT)
        await run_after_submit()
        assert all(m["key"] != "notification" for m in SENT[before:])  # waiting for the summary
        _, reply = await owner.request("POST", "/notifications/digest/send", body={})
        assert reply["data"]["sent"] == 1
        digest = next(m for m in SENT[before:] if m["key"] == "daily_digest")
        assert digest["to"] == email and "Feedback" in digest["text"]

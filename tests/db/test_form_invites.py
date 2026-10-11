"""Invite-only forms (B7): invitations emailed with personal links, skipped when already invited, resent (the old
link stops working), revoked, taken off the list; member passes for organisation-only forms; the audit trail and
another workspace."""

from __future__ import annotations

import pytest

from app.modules.emails.service import SENT
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_invitations_and_passes(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/forms", body={"name": "Board survey"})
        form = reply["data"]

        sent_before = len(SENT)
        status, reply = await owner.request("POST", f"/forms/{form['id']}/invites", body={"people": [
            {"email": "Ana@Example.org", "name": " Ana "}, {"email": "ben@example.org"}]})
        assert status == 201, reply
        assert reply["data"]["created"] == 2 and reply["data"]["skipped"] == []
        assert [i["status"] for i in reply["data"]["invitations"]] == ["invited", "invited"]
        links = {link["email"]: link["url"] for link in reply["meta"]["dev_links"]}
        assert links["ana@example.org"].startswith(f"https://{sub}.formalie.dev")
        assert f"/{form['public_key']}/fill?invite=" in links["ana@example.org"]
        mails = SENT[sent_before:]
        assert {m["to"] for m in mails} == {"ana@example.org", "ben@example.org"}
        assert any(links["ana@example.org"] in m["text"] and "Hello Ana" in m["text"] for m in mails)

        _, reply = await owner.request("POST", f"/forms/{form['id']}/invites", body={"people": [{"email": "ana@example.org"}]})
        assert reply["data"]["created"] == 0 and reply["data"]["skipped"] == ["ana@example.org"]
        _, reply = await owner.request("POST", f"/forms/{form['id']}/invites", body={"people": [{"email": "not-an-email"}]})
        assert reply["error"]["code"] == "FRM-GEN-1002"

        _, reply = await owner.request("GET", f"/forms/{form['id']}/invites")
        ana = next(i for i in reply["data"] if i["email"] == "ana@example.org")
        assert ana["name"] == "Ana"

        # Resend: a new link; revoke; resend refused; take it off the list
        _, reply = await owner.request("POST", f"/forms/{form['id']}/invites/{ana['id']}/resend", body={})
        assert reply["meta"]["dev_links"][0]["url"] != links["ana@example.org"]
        _, reply = await owner.request("DELETE", f"/forms/{form['id']}/invites/{ana['id']}", query={"remove": "1"})
        assert reply["error"]["code"] == "FRM-FORM-1007"
        _, reply = await owner.request("DELETE", f"/forms/{form['id']}/invites/{ana['id']}")
        assert next(i for i in reply["data"]["invitations"] if i["id"] == ana["id"])["status"] == "revoked"
        _, reply = await owner.request("POST", f"/forms/{form['id']}/invites/{ana['id']}/resend", body={})
        assert reply["error"]["code"] == "FRM-FORM-1007"
        _, reply = await owner.request("DELETE", f"/forms/{form['id']}/invites/{ana['id']}", query={"remove": "1"})
        assert [i["email"] for i in reply["data"]["invitations"]] == ["ben@example.org"]
        # Invited again after being revoked: a new invitation
        _, reply = await owner.request("POST", f"/forms/{form['id']}/invites", body={"people": [{"email": "ana@example.org"}]})
        assert reply["data"]["created"] == 1

        # A sign-in pass for the form's address
        _, reply = await owner.request("POST", "/forms/pass", body={"key": form["public_key"]})
        assert reply["data"]["url"].startswith(f"https://{sub}.formalie.dev") and "?pass=" in reply["data"]["url"]
        _, reply = await owner.request("POST", "/forms/pass", body={"key": "AbCdEfGhJk"})
        assert reply["error"]["code"] == "FRM-PERM-1001"

        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100", "filter[action]": "forms.shared"})
        fields = {c["field"] for row in trail["data"] for c in row.get("changes", [])}
        assert {"invitations", "invitation_resent", "invitation_revoked", "invitation_removed"} <= fields

    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", f"/forms/{form['id']}/invites")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("POST", "/forms/pass", body={"key": form["public_key"]})
        assert reply["error"]["code"] == "FRM-PERM-1001"

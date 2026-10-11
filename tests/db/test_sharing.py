"""Sharing a form (B7) on a new workspace: where people answer, access and password, response limit, custom links
with suggestions, embed websites, people access, search & link preview, short links (created once, retired for
good), who can see the form, the audit trail, and another workspace seeing none of it."""

from __future__ import annotations

import pytest

from app.core.db.session import db_session
from app.modules.links import directory
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_forms import member_of
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_sharing_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/forms", body={"name": "Feedback"})
        form = reply["data"]
        _, reply = await owner.request("POST", "/forms", body={"name": "Other"})
        other = reply["data"]

        # The shared forms host finds a new form by its key
        async with db_session("read") as db:
            found = await directory.resolve_form_key(db, form["public_key"])
        assert found is not None and found.subdomain == sub

        status, reply = await owner.request("GET", f"/forms/{form['id']}/share")
        assert status == 200, reply
        share = reply["data"]
        assert share["channels"] == ["link", "embed", "api"] and share["access"] == "public"
        assert share["has_password"] is False and share["short_link"] is None
        assert share["seo"]["default_title"] == "Feedback" and share["people"]["team_access"] == "edit"
        assert [a["reason"] for a in share["people"]["always"]] == ["workspace_admin"]

        # Password access needs a password; a password is never returned
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"access": "password"})
        assert reply["error"]["details"] == [{"field": "password", "message": "Set a password for this form."}]
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={
            "row_version": share["row_version"], "access": "password", "password": "open-sesame-1", "response_limit": 50,
            "channels": ["embed", "link"], "embed_domains": ["https://www.Example.com/contact", "example.com", "*.shop.example"],
            "seo": {"title": "  Tell us  ", "description": None, "image_upload_id": None, "noindex": True}})
        assert reply["success"], reply
        saved = reply["data"]
        assert saved["has_password"] and saved["access"] == "password" and saved["response_limit"] == 50
        assert saved["channels"] == ["link", "embed"] and saved["embed_domains"] == ["example.com", "*.shop.example"]
        assert saved["seo"]["title"] == "Tell us" and saved["seo"]["noindex"] is True
        assert "open-sesame-1" not in str(reply) and "password_hash" not in str(reply)
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"row_version": share["row_version"]})
        assert reply["error"]["code"] == "FRM-GEN-1009"
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"embed_domains": ["not a site"]})
        assert reply["error"]["details"] == [{"field": "embed_domains", "message": "invalid"}]

        # Custom links: free, taken (with suggestions), reserved, unreadable
        _, reply = await owner.request("PUT", f"/forms/{other['id']}/share", body={"custom_link": "feedback"})
        assert reply["data"]["custom_link"] == "feedback"
        _, reply = await owner.request("GET", f"/forms/{form['id']}/share/link-check", query={"value": "feedback"})
        check = reply["data"]
        assert check["available"] is False and check["reason"] == "taken" and len(check["suggestions"]) == 3
        assert check["taken_by"] == {"id": other["id"], "name": "Other", "status": "draft", "link": True}
        assert check["suggestions"][0] == f"{sub}-feedback"[:len(check["suggestions"][0])]
        _, reply = await owner.request("GET", f"/forms/{form['id']}/share/link-check", query={"value": "admin"})
        assert reply["data"]["reason"] == "reserved" and reply["data"]["taken_by"] is None
        _, reply = await owner.request("GET", f"/forms/{form['id']}/share/link-check", query={"value": "No Good"})
        assert reply["data"] == {"value": "No Good", "available": False, "reason": "invalid", "suggestions": [], "taken_by": None}
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"custom_link": "feedback"})
        assert reply["error"]["code"] == "FRM-FORM-1006"
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"custom_link": "help"})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={"custom_link": "tell-us"})
        assert reply["data"]["custom_link"] == "tell-us"

        # People access: a member gets view on this form, everyone else none
        member, member_id = await member_of(http, owner, sub)
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={
            "people": {"team_access": "none", "grants": [{"user_id": member_id, "level": "responses"},
                                                         {"user_id": member_id, "level": "view"}]}})
        assert reply["data"]["people"]["grants"] == [{"user": {"id": member_id, "name": "Mia Member",
                                                               "email": f"mia@{sub}.test"}, "level": "view"}]
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/share", body={
            "people": {"team_access": "none", "grants": [{"user_id": form["id"], "level": "view"}]}})
        assert reply["error"]["details"] == [{"field": "people", "message": "Unknown person."}]
        _, reply = await member.request("GET", f"/forms/{form['id']}")
        assert reply["success"], reply
        _, reply = await owner.request("PUT", f"/forms/{other['id']}/share", body={"people": {"team_access": "none", "grants": []}})
        _, reply = await member.request("GET", f"/forms/{other['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("PUT", f"/forms/{other['id']}/share", body={"people": {"team_access": "edit", "grants": []}})
        _, reply = await member.request("PUT", f"/forms/{form['id']}/share", body={"response_limit": None})
        assert reply["error"]["code"] == "FRM-PERM-1001"

        # Who can see it
        _, reply = await owner.request("GET", f"/forms/{form['id']}/access")
        rows = {p["user"]["email"]: p for p in reply["data"]["people"]}
        assert rows[email]["level"] == "edit" and rows[email]["reason"] == "workspace_owner"
        assert rows[f"mia@{sub}.test"]["level"] == "view" and rows[f"mia@{sub}.test"]["reason"] == "own_grant"
        assert reply["data"]["folder"] is None or reply["data"]["folder"]["restricted"] is False
        _, reply = await owner.request("GET", f"/forms/{other['id']}/access")
        rows = {p["user"]["email"]: p for p in reply["data"]["people"]}
        assert rows[f"mia@{sub}.test"]["reason"] == "team_default" and rows[f"mia@{sub}.test"]["level"] == "edit"

        # Short link: made once, the same afterwards, removed for good
        status, reply = await owner.request("POST", f"/forms/{form['id']}/short-link", body={})
        assert status == 201, reply
        code = reply["data"]["short_link"]["code"]
        status, reply = await owner.request("POST", f"/forms/{form['id']}/short-link", body={})
        assert status == 200 and reply["data"]["short_link"]["code"] == code
        async with db_session("read") as db:
            assert (await directory.resolve_short_code(db, code)).form_id is not None  # type: ignore[union-attr]
        _, reply = await owner.request("DELETE", f"/forms/{form['id']}/short-link")
        assert reply["data"]["short_link"] is None
        async with db_session("read") as db:
            assert await directory.resolve_short_code(db, code) is None

        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100", "filter[action]": "forms.shared"})
        fields = {c["field"] for row in trail["data"] for c in row.get("changes", [])}
        assert {"password", "access", "custom_link", "people_access", "short_link", "embed_domains", "seo_noindex"} <= fields
        assert all(c["after"] in (None, "changed") for row in trail["data"] for c in row.get("changes", [])
                   if c["field"] == "password")

    # Another workspace sees none of it
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other_sub}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        for path in (f"/forms/{form['id']}/share", f"/forms/{form['id']}/access"):
            _, reply = await stranger.request("GET", path)
            assert reply["error"]["code"] == "FRM-GEN-1004"

"""Onboarding (B3) on a new workspace made through the real sign-up: steps saved into the workspace settings,
skipped, invitations recorded, finished; the seeded workspaces count as set up."""

from __future__ import annotations

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_steps_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("GET", "/onboarding")
        state = reply["data"]
        assert state["status"] == "not_started" and state["current_step"] == "company"
        assert state["steps"] == {"company": "todo", "branding": "todo", "localisation": "todo", "team": "todo",
                                  "first_form": "todo"}
        assert state["company"]["name"] == "Settings Co" and "form_languages" not in state["localisation"]

        company = {"name": "  Acme Labs ", "industry": "legal", "size": "11-50", "country": "GB",
                   "website": " https://acme.example "}
        status, reply = await owner.request("PATCH", "/onboarding", body={"step": "company", "action": "save", "data": company})
        assert status == 200, reply
        state = reply["data"]
        assert state["status"] == "in_progress" and state["current_step"] == "branding" and state["steps"]["company"] == "done"
        assert state["company"] == {"name": "Acme Labs", "industry": "legal", "size": "11-50", "country": "GB",
                                    "website": "https://acme.example"}
        _, settings = await owner.request("GET", "/settings/company")
        assert settings["data"]["display_name"] == "Acme Labs" and settings["data"]["address"]["country"] == "GB"

        _, reply = await owner.request("PATCH", "/onboarding", body={
            "step": "company", "action": "save", "data": {**company, "website": "javascript:alert(1)"}})
        assert reply["error"]["details"] == [{"field": "website", "message": "Invalid URL"}]

        _, reply = await owner.request("PATCH", "/onboarding", body={"step": "branding", "action": "skip"})
        assert reply["data"]["steps"]["branding"] == "skipped" and reply["data"]["current_step"] == "localisation"

        localisation = {"language": "fr", "timezone": "Europe/Paris", "currency": "EUR", "date_format": "DD/MM/YYYY",
                        "number_format": "1 234,56", "week_start": "monday"}
        _, reply = await owner.request("PATCH", "/onboarding", body={"step": "localisation", "action": "save",
                                                                     "data": localisation})
        assert reply["data"]["localisation"] == localisation
        _, settings = await owner.request("GET", "/settings/localisation")
        assert settings["data"]["currency"] == "EUR" and len(settings["data"]["form_languages"]) == 20

        _, reply = await owner.request("PATCH", "/onboarding", body={"step": "team", "action": "save", "data": {
            "invites": [{"email": email, "role": "admin"}]}})
        assert reply["error"]["details"] == [{"field": "invites", "message": f"{email} is already in this workspace."}]
        invites = [{"email": "ada@lovelace.test", "role": "member"}, {"email": "grace@hopper.test", "role": "admin"}]
        _, reply = await owner.request("PATCH", "/onboarding", body={"step": "team", "action": "save",
                                                                     "data": {"invites": invites}})
        assert reply["data"]["invites"] == invites
        _, reply = await owner.request("PATCH", "/onboarding", body={"step": "first_form", "action": "save", "data": {
            "choice": "template", "template_key": "customer_feedback"}})
        assert reply["data"]["first_form"] == {"choice": "template", "template_key": "customer_feedback"}
        assert reply["data"]["current_step"] == "first_form"

        status, reply = await owner.request("POST", "/onboarding/finish")
        assert status == 200 and reply["data"]["status"] == "completed"
        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": 100})
        actions = [e["action"] for e in trail["data"]]
        assert actions.count("users.invited") == 2 and "workspace.setup_completed" in actions
        assert "workspace.updated" in actions and actions.count("settings.updated") == 1  # localisation
        done = next(e for e in trail["data"] if e["action"] == "workspace.setup_completed")
        assert done["metadata"] == {"done": "4", "skipped": "1"}
        updated = next(e for e in trail["data"] if e["action"] == "workspace.updated")
        assert {"field": "name", "before": "Settings Co", "after": "Acme Labs"} in updated["changes"]
        assert updated["metadata"] == {"source": "onboarding"}


async def test_seeded_workspaces_are_set_up_and_members_cannot(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, "admin@remedylegal.test")
        _, reply = await owner.request("GET", "/onboarding")
        assert reply["data"]["status"] == "completed" and set(reply["data"]["steps"].values()) == {"done"}
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        for method, path in (("GET", "/onboarding"), ("PATCH", "/onboarding"), ("POST", "/onboarding/finish")):
            _, reply = await member.request(method, path, body={"step": "company", "action": "skip"} if method == "PATCH" else None)
            assert reply["error"]["code"] == "FRM-PERM-1001", path

"""People (B4) on a new workspace: profiles with activation, personal sign-up links with approval, the shared link
with domains, rejection, withdrawing; managing people with the owner guards; the list, insights and detail."""

from __future__ import annotations

import pytest

from app.modules.emails.service import SENT
from tests.conftest import client_for
from tests.db.test_auth_flows import app, audit_actions, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

NEW_PASSWORD = "Another-Pass-77"


def last_link(email: str) -> str:
    for message in reversed(SENT):
        if message["to"] == email and "link" in message["values"]:
            return str(message["values"]["link"])
    raise AssertionError(f"no link sent to {email}")


def token_of(link: str) -> str:
    return link.rsplit("/auth/join/", 1)[1]


async def join(http, link: str, **body) -> dict:  # noqa: ANN001
    """The sign-up page: preview, then accept."""
    page = SecureClient(http)
    _, preview = await page.request("GET", f"/public/invites/{token_of(link)}")
    _, accepted = await page.request("POST", f"/public/invites/{token_of(link)}/accept",
                                     body={"first_name": "Ada", "last_name": "Byron", "password": NEW_PASSWORD, **body})
    return {"preview": preview, "accepted": accepted}


async def test_ways_in(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    host = f"{sub}.formalie.dev"
    async with client_for(app, host=host) as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # A profile made by an admin: activation email, set a password, signed in
        status, reply = await owner.request("POST", "/people", body={
            "first_name": "Ada", "last_name": "Byron", "email": f"Ada@{sub}.test", "phone": "+44 7700 900123",
            "role": "admin", "department_ids": [], "job_title_ids": [], "manager_id": None})
        assert status == 201, reply
        ada = reply["data"]
        assert ada["status"] == "not_activated" and ada["role"] == "admin" and ada["phone"] == "+447700900123"
        assert ada["invite"]["kind"] == "activation" and not ada["invite"]["expired"]
        _, reply = await owner.request("POST", "/people", body={
            "first_name": "A", "last_name": "B", "email": f"ada@{sub}.test", "role": "member"})
        assert reply["error"]["code"] == "FRM-USER-1011"
        _, reply = await owner.request("POST", "/people", body={
            "first_name": "A", "last_name": "B", "email": f"x@{sub}.test", "role": "owner"})
        assert reply["error"]["code"] == "FRM-USER-1009"

        link = last_link(f"ada@{sub}.test")
        assert link.startswith(f"https://{host}/auth/join/")
        joined = await join(http, link)
        assert joined["preview"]["data"]["kind"] == "activation" and joined["preview"]["data"]["inviter"] == "Olu Ade"
        assert joined["accepted"]["data"] == {"email": f"ada@{sub}.test", "status": "active"}
        again = await join(http, link)
        assert again["preview"]["error"]["code"] == "FRM-USER-1002"  # used
        admin = SecureClient(http)
        await sign_in(admin, f"ada@{sub}.test", NEW_PASSWORD)

        # A personal sign-up link: they sign up, then wait for approval
        _, reply = await owner.request("POST", "/people/invites", body={
            "emails": [f"grace@{sub}.test", f"GRACE@{sub}.test", email], "role": "member", "message": "Welcome!"})
        assert reply["data"] == {"invited": 1, "skipped": [{"email": email, "reason": "member"}]}
        joined = await join(http, last_link(f"grace@{sub}.test"), first_name="Grace", last_name="Hopper")
        assert joined["preview"]["data"]["message"] == "Welcome!"
        assert joined["accepted"]["data"]["status"] == "pending"
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": f"grace@{sub}.test",
                                                                                 "password": NEW_PASSWORD})
        assert reply["error"]["code"] == "FRM-USER-1010"
        _, people = await owner.request("GET", "/people", query={"filter[status]": "pending"})
        grace = people["data"][0]
        assert grace["name"] == "Grace Hopper" and grace["request"]["via"] == "invite"
        _, reply = await owner.request("POST", f"/people/{grace['id']}/approve", body={"role": "member", "manager_id": ada["id"]})
        assert reply["data"]["status"] == "active" and reply["data"]["manager"]["name"] == "Ada Byron"
        await sign_in(SecureClient(http), f"grace@{sub}.test", NEW_PASSWORD)

        # The shared link, with a domain
        _, reply = await owner.request("PUT", "/people/signup-link", body={"enabled": True, "domains": [f"{sub}.test"]})
        shared = reply["data"]["link"]
        assert reply["data"]["enabled"] and reply["data"]["domains"] == [f"{sub}.test"]
        wrong = await join(http, shared, email="someone@elsewhere.test")
        assert wrong["accepted"]["error"]["code"] == "FRM-USER-1012"
        joined = await join(http, shared, email=f"lin@{sub}.test", first_name="Lin")
        assert joined["preview"]["data"]["kind"] == "link" and joined["accepted"]["data"]["status"] == "pending"
        _, people = await owner.request("GET", "/people", query={"filter[status]": "pending"})
        lin = people["data"][0]
        assert lin["request"]["via"] == "link"
        _, reply = await owner.request("POST", f"/people/{lin['id']}/reject", body={"reason": "Not ours"})
        assert reply["data"] == {"id": lin["id"]}
        _, reply = await owner.request("GET", f"/people/{lin['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, renewed = await owner.request("POST", "/people/signup-link/new")
        assert renewed["data"]["link"] != shared
        stale = await join(http, shared, email=f"late@{sub}.test")
        assert stale["preview"]["error"]["code"] == "FRM-USER-1002"

        # Withdrawing an invitation
        _, reply = await owner.request("POST", "/people/invites", body={"emails": [f"tom@{sub}.test"], "role": "member"})
        _, people = await owner.request("GET", "/people", query={"filter[status]": "invited"})
        tom = people["data"][0]
        _, reply = await owner.request("POST", f"/people/{tom['id']}/invite/link")
        assert reply["data"]["link"].startswith(f"https://{host}/auth/join/")
        _, reply = await owner.request("DELETE", f"/people/{tom['id']}/invite")
        assert reply["data"] == {"id": tom["id"]}
        assert (await join(http, last_link(f"tom@{sub}.test")))["preview"]["error"]["code"] == "FRM-USER-1002"

        actions = set(audit_actions(superuser, email))
        assert {"users.profile_created", "users.invited", "users.approved", "users.rejected", "users.signup_link_changed",
                "users.invite_link", "users.invite_revoked"} <= actions
        assert "users.joined" in audit_actions(superuser, f"ada@{sub}.test")


async def test_managing_people(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        tokens = await sign_in(owner, email, PASSWORD)
        me = tokens["user"]["id"]
        made = {}
        for name, role in (("ada", "admin"), ("bob", "member")):
            _, reply = await owner.request("POST", "/people", body={"first_name": name.title(), "last_name": "Test",
                                                                    "email": f"{name}@{sub}.test", "role": role})
            made[name] = reply["data"]["id"]
            await join(http, last_link(f"{name}@{sub}.test"), first_name=name.title(), last_name="Test")
        admin = SecureClient(http)
        await sign_in(admin, f"ada@{sub}.test", NEW_PASSWORD)
        bob = SecureClient(http)
        await sign_in(bob, f"bob@{sub}.test", NEW_PASSWORD)

        # Owners are changed only by owners; nobody disables themselves; the last owner stays one
        _, reply = await admin.request("POST", f"/people/{me}/disable")
        assert reply["error"]["code"] == "FRM-USER-1006"
        _, reply = await admin.request("PATCH", f"/people/{made['bob']}", body={"role": "owner"})
        assert reply["error"]["code"] == "FRM-USER-1006"
        _, reply = await owner.request("POST", f"/people/{me}/disable")
        assert reply["error"]["code"] == "FRM-USER-1005"
        _, reply = await owner.request("PATCH", f"/people/{me}", body={"role": "admin"})
        assert reply["error"]["code"] == "FRM-USER-1003"

        # Departments, manager, no loops
        _, dept = await owner.request("POST", "/org/departments", body={"name": "Ops", "code": None, "description": None,
                                                                        "member_ids": []})
        status, reply = await owner.request("PATCH", f"/people/{made['bob']}", body={
            "role": "admin", "department_ids": [dept["data"]["id"]], "manager_id": made["ada"]})
        assert status == 200 and reply["data"]["role"] == "admin" and reply["data"]["departments"] == [
            {"id": dept["data"]["id"], "name": "Ops"}] and reply["data"]["manager"]["id"] == made["ada"]
        _, reply = await owner.request("PATCH", f"/people/{made['ada']}", body={"manager_id": made["bob"]})
        assert reply["error"]["code"] == "FRM-USER-1004"

        # Disable ends their sessions; enable; a new password at the next sign-in
        _, reply = await owner.request("POST", f"/people/{made['bob']}/disable")
        assert reply["data"]["status"] == "disabled"
        _, reply = await bob.request("GET", "/me")
        assert reply["error"]["code"] == "FRM-AUTH-1011"
        _, reply = await owner.request("POST", f"/people/{made['bob']}/enable")
        assert reply["data"]["status"] == "active"
        _, reply = await owner.request("POST", f"/people/{made['bob']}/password")
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": f"bob@{sub}.test",
                                                                                 "password": NEW_PASSWORD})
        assert reply["error"]["code"] == "FRM-AUTH-1015"
        _, reply = await owner.request("POST", f"/people/{made['ada']}/sign-out")
        _, reply = await admin.request("GET", "/me")
        assert reply["error"]["code"] == "FRM-AUTH-1011"

        _, reply = await owner.request("POST", "/people/bulk", body={"ids": [made["ada"], made["bob"], me],
                                                                     "action": "role", "value": "member"})
        assert reply["data"] == {"done": 2, "skipped": 1}  # the only owner stays one

        _, people = await owner.request("GET", "/people", query={"sort": "role"})
        assert [p["role"] for p in people["data"]] == ["owner", "member", "member"]
        _, found = await owner.request("GET", "/people", query={"q": "ops"})
        assert [p["email"] for p in found["data"]] == [f"bob@{sub}.test"]
        _, insights = await owner.request("GET", "/people/insights")
        data = insights["data"]
        assert data["total"] == 3 and data["by_role"] == {"owner": 1, "admin": 0, "member": 2}
        assert data["joined"] == 3 and len(data["daily"]) == 30 and data["daily"][-1]["count"] >= 3
        _, detail = await owner.request("GET", f"/people/{made['ada']}")
        assert detail["data"]["reports"] == [{"id": made["bob"], "name": "Bob Test"}]
        assert detail["data"]["sign_ins_30d"] == 1 and detail["data"]["last_sign_in"]["at"]


async def test_members_cannot_manage_people(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        for method, path in (("GET", "/people"), ("POST", "/people/invites"), ("GET", "/people/signup-link")):
            _, reply = await member.request(method, path, body={} if method == "POST" else None)
            assert reply["error"]["code"] == "FRM-PERM-1001", path

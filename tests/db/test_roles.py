"""Roles & access (B4) on a new workspace: built-in roles by their key, create, copy, unique names, grants completed
by withNeeds, audit lines, duplicate, Owner locked, delete only when nobody holds it; members refused."""

from __future__ import annotations

import pytest

from app.modules.rbac.permissions import with_needs
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_roles_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        status, reply = await owner.request("GET", "/roles")
        assert status == 200, reply
        assert [(r["id"], r["built_in"]) for r in reply["data"]] == [("owner", "owner"), ("admin", "admin"),
                                                                      ("member", "member")]
        assert reply["data"][0]["people_count"] == 1 and reply["data"][0]["people"][0]["name"] == "Olu Ade"

        status, reply = await owner.request("POST", "/roles", body={
            "name": " Reviewers ", "description": "Look at answers", "grants": {"responses.view": "all"}})
        assert status == 201, reply
        reviewers = reply["data"]
        assert len(reviewers["id"]) == 27 and reviewers["built_in"] is None and reviewers["name"] == "Reviewers"
        assert reviewers["grants"] == with_needs({"responses.view": "all"})
        _, reply = await owner.request("POST", "/roles", body={"name": "admin"})
        assert reply["error"]["code"] == "FRM-ORG-1001"
        _, reply = await owner.request("POST", "/roles", body={"name": "Like members", "copy_of": "member"})
        assert reply["data"]["grants"] == with_needs((await owner.request("GET", "/roles/member"))[1]["data"]["grants"])
        _, reply = await owner.request("POST", "/roles", body={"name": "Bad", "grants": {"not.a.permission": "all"}})
        assert reply["error"]["code"] == "FRM-GEN-1002"

        status, reply = await owner.request("PATCH", f"/roles/{reviewers['id']}", body={
            "name": "Answer reviewers", "grants": {"responses.view": "own", "forms.view": "all"}})
        assert status == 200 and reply["data"]["name"] == "Answer reviewers"
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "users.role_updated"})
        fields = {c["field"] for c in trail["data"][0]["changes"]}
        assert {"name", "permissions_scope"} <= fields

        _, reply = await owner.request("POST", f"/roles/{reviewers['id']}/duplicate")
        assert reply["data"]["name"] == "Answer reviewers (copy)"
        _, reply = await owner.request("POST", f"/roles/{reviewers['id']}/duplicate")
        assert reply["data"]["name"] == "Answer reviewers (copy 2)"

        for method, path in (("PATCH", "/roles/owner"), ("DELETE", "/roles/owner"), ("DELETE", "/roles/admin")):
            _, reply = await owner.request(method, path, body={"name": "x"} if method == "PATCH" else None)
            assert reply["error"]["code"] == "FRM-USER-1007", path
        _, reply = await owner.request("DELETE", f"/roles/{reviewers['id']}")
        assert reply["data"] == {"id": reviewers["id"]}
        _, reply = await owner.request("GET", f"/roles/{reviewers['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        _, insights = await owner.request("GET", "/roles/insights")
        data = insights["data"]
        assert data["total"] == 6 and data["custom"] == 3 and data["people"] == 1
        assert next(r for r in data["reach"] if r["id"] == "owner")["share"] == 1
        _, page = await owner.request("GET", "/roles", query={"page": 1, "filter[kind]": "own", "sort": "name"})
        assert [r["name"] for r in page["data"]] == ["Answer reviewers (copy 2)", "Answer reviewers (copy)", "Like members"]
        assert page["meta"]["total"] == 3


async def test_a_held_role_stays_and_members_cannot_change_roles(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, "admin@remedylegal.test")
        _, reply = await owner.request("DELETE", "/roles/member")
        assert reply["error"]["code"] == "FRM-USER-1007"
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        _, reply = await member.request("POST", "/roles", body={"name": "Mine"})
        assert reply["error"]["code"] == "FRM-PERM-1001"

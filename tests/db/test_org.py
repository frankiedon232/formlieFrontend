"""Organisation data and navigation counts (B3) on a new workspace: create, unique names, people, list filters,
insights, archive and restore, merge, import, delete; the seeded samples; members refused."""

from __future__ import annotations

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_departments_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        tokens = await sign_in(owner, email, PASSWORD)
        me = tokens["user"]["id"]
        _, reply = await owner.request("GET", "/org/departments")
        assert reply["data"] == [] and reply["meta"]["total"] == 0

        status, reply = await owner.request("POST", "/org/departments", body={
            "name": "  Finance ", "code": " FIN ", "description": "", "member_ids": [me, me, "not-a-person"]})
        assert status == 201, reply
        finance = reply["data"]
        assert (finance["name"], finance["code"], finance["description"], finance["status"]) == ("Finance", "FIN", None, "active")
        assert [m["email"] for m in finance["members"]] == [email] and finance["forms_count"] == 0
        _, reply = await owner.request("POST", "/org/departments", body={"name": "FINANCE", "code": None,
                                                                         "description": None, "member_ids": []})
        assert reply["error"]["code"] == "FRM-ORG-1001" and reply["error"]["details"] == [{"field": "name", "message": "taken"}]
        _, reply = await owner.request("POST", "/org/job_titles", body={"name": "Finance", "code": None,
                                                                        "description": None, "member_ids": []})
        assert reply["success"]  # names are unique per kind

        _, sales = await owner.request("POST", "/org/departments", body={"name": "Sales", "code": None, "description": None,
                                                                         "member_ids": []})
        sales = sales["data"]
        _, reply = await owner.request("GET", "/org/departments", query={"filter[status]": "empty"})
        assert [r["name"] for r in reply["data"]] == ["Sales"]
        _, reply = await owner.request("GET", "/org/departments", query={"sort": "-name", "q": "a"})
        assert [r["name"] for r in reply["data"]] == ["Sales", "Finance"]

        status, reply = await owner.request("PATCH", f"/org/departments/{finance['id']}", body={
            "name": "Finance and Legal", "code": "FIN", "description": "Money", "member_ids": []})
        assert status == 200 and reply["data"]["members"] == []
        _, insights = await owner.request("GET", "/org/departments/insights")
        assert insights["data"]["total"] == 2 and insights["data"]["empty"] == 2 and insights["data"]["people"] == 1

        _, reply = await owner.request("POST", f"/org/departments/{sales['id']}/archive")
        assert reply["data"]["status"] == "archived" and reply["data"]["archived_at"]
        _, reply = await owner.request("GET", "/org/departments", query={"filter[status]": "archived"})
        assert [r["name"] for r in reply["data"]] == ["Sales"]
        _, reply = await owner.request("POST", f"/org/departments/{sales['id']}/restore")
        assert reply["data"]["status"] == "active"

        await owner.request("PATCH", f"/org/departments/{sales['id']}", body={"name": "Sales", "code": None,
                                                                               "description": None, "member_ids": [me]})
        status, reply = await owner.request("POST", "/org/departments/merge", body={"from": [sales["id"]],
                                                                                     "into": finance["id"]})
        assert status == 200 and [m["id"] for m in reply["data"]["members"]] == [me]
        _, reply = await owner.request("GET", f"/org/departments/{sales['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"  # merged away
        _, reply = await owner.request("POST", "/org/departments/merge", body={"from": [finance["id"]], "into": finance["id"]})
        assert reply["error"]["details"] == [{"field": "from", "message": "required"}]

        _, reply = await owner.request("POST", "/org/departments/import", body={
            "names": ["Support", " ", "support", "finance and legal", "x" * 81, "People"]})
        assert reply["data"] == {"created": 2, "skipped": [
            {"name": "support", "reason": "duplicate"}, {"name": "finance and legal", "reason": "duplicate"},
            {"name": "x" * 80, "reason": "too_long"}]}

        _, usage = await owner.request("GET", f"/org/departments/{finance['id']}/usage")
        assert usage["data"] == []
        status, reply = await owner.request("DELETE", f"/org/departments/{finance['id']}")
        assert status == 200 and reply["data"] == {"deleted": True}
        _, reply = await owner.request("GET", "/org/departments")
        assert sorted(r["name"] for r in reply["data"]) == ["People", "Support"]
        _, reply = await owner.request("GET", "/org/teams")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[area]": "settings", "page_size": 100})
        actions = {e["action"] for e in trail["data"]}
        assert {"settings.org_created", "settings.org_updated", "settings.org_archived", "settings.org_restored",
                "settings.org_merged", "settings.org_imported", "settings.org_deleted"} <= actions

        _, counts = await owner.request("GET", "/navigation/counts")
        assert counts["data"]["people"] == {"total": 1, "active": 1, "invited": 0, "pending": 0, "not_activated": 0,
                                            "disabled": 0, "departments": 2, "job_titles": 1}
        assert counts["data"]["templates"]["total"] == 84 and counts["data"]["themes"]["system"] == 22
        assert counts["data"]["forms"]["all"] == 0 and counts["data"]["folders"] == []


async def test_seeded_samples_and_members(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, "admin@remedylegal.test")
        _, reply = await owner.request("GET", "/org/departments", query={"page_size": 100})
        names = [r["name"] for r in reply["data"]]
        assert names == sorted(names) and {"Finance", "Compliance", "Legal"} <= set(names)
        assert all(not r["members"] for r in reply["data"] if r["name"] in ("Legal", "Compliance"))
        member = SecureClient(http)
        await sign_in(member, "staff@remedylegal.test")
        _, reply = await member.request("GET", "/org/departments")
        assert reply["error"]["code"] == "FRM-PERM-1001"
        _, counts = await member.request("GET", "/navigation/counts")
        assert counts["data"]["people"]["total"] == 0  # members without people.view see zeros

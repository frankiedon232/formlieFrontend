"""The form builder (B5) on a new workspace: autosave with row_version, the publish checks, versions, discard,
restore, preview; the live version stays while the draft changes."""

from __future__ import annotations

import copy

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def with_field(schema: dict, key: str, label: str, **extra) -> dict:  # noqa: ANN003
    out = copy.deepcopy(schema)
    out["pages"][0]["rows"].append({"id": f"row_{key}", "fields": [
        {"id": f"fld_{key}", "key": key, "label": label, **{"type": "short_text", **extra}}]})
    return out


async def test_draft_publish_versions(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/forms", body={"name": "Contact"})
        form = reply["data"]

        status, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
        assert status == 200 and builder["data"]["published_version"] is None and builder["data"]["live_fields"] == []
        schema = builder["data"]["schema"]

        # Nothing to answer yet: publishing says why
        _, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 1})
        assert reply["error"]["code"] == "FRM-FORM-1004" and reply["error"]["details"] == [
            {"field": "form", "message": "no_inputs"}]

        draft = with_field(schema, "full_name", "Full name", required=True, readonly=True)
        status, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": draft})
        assert status == 200 and reply["data"]["row_version"] == 2 and reply["data"]["has_unpublished_changes"] is False
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": draft})
        assert reply["error"]["code"] == "FRM-GEN-1009"
        _, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 2})
        assert reply["error"]["details"] == [{"field": "fld_full_name", "message": "locked_required"}]

        draft = with_field(schema, "full_name", "Full name", required=True)
        await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 2, "schema": draft})
        status, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 3})
        assert status == 200, reply
        assert reply["data"]["form"]["status"] == "published" and reply["data"]["version"]["number"] == 1
        assert reply["data"]["version"]["fields_count"] == 1 and reply["data"]["version"]["published_by"]["name"] == "Olu Ade"

        # Editing the published form changes only the draft
        changed = with_field(draft, "email", "Email")
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 4, "schema": changed})
        assert reply["data"]["has_unpublished_changes"] is True
        _, preview = await owner.request("GET", f"/forms/{form['id']}/preview")
        assert len(preview["data"]["draft"]["pages"][0]["rows"]) == 2 and len(preview["data"]["live"]["pages"][0]["rows"]) == 1
        _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
        assert builder["data"]["published_keys"] == ["full_name"]
        assert builder["data"]["live_fields"] == [{"key": "full_name", "label": "Full name", "required": True,
                                                   "type": "short_text"}]
        _, reply = await owner.request("POST", f"/forms/{form['id']}/discard")
        assert len(reply["data"]["schema"]["pages"][0]["rows"]) == 1 and not reply["data"]["form"]["has_unpublished_changes"]

        row_version = reply["data"]["form"]["row_version"]
        await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": row_version, "schema": changed})
        _, reply = await owner.request("POST", f"/forms/{form['id']}/publish", body={
            "row_version": row_version + 1, "change_summary": "  Added email  "})
        assert reply["data"]["version"] == {**reply["data"]["version"], "number": 2, "change_summary": "Added email"}

        _, versions = await owner.request("GET", f"/forms/{form['id']}/versions")
        assert [v["number"] for v in versions["data"]] == [2, 1]
        first = versions["data"][1]
        _, reply = await owner.request("GET", f"/forms/{form['id']}/versions/{first['id']}")
        assert len(reply["data"]["schema"]["pages"][0]["rows"]) == 1
        _, reply = await owner.request("POST", f"/forms/{form['id']}/versions/{first['id']}/restore")
        assert reply["data"]["form"]["has_unpublished_changes"] is True
        assert len(reply["data"]["schema"]["pages"][0]["rows"]) == 1

        # A closed form can't be published; the lifecycle routes still answer
        _, reply = await owner.request("POST", f"/forms/{form['id']}/close")
        assert reply["data"]["status"] == "closed"
        _, reply = await owner.request("POST", f"/forms/{form['id']}/publish",
                                       body={"row_version": reply["data"]["row_version"]})
        assert reply["error"]["code"] == "FRM-FORM-1007"

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[resource_id]": form["id"], "page_size": 100})
        actions = [e["action"] for e in trail["data"]]
        assert actions.count("forms.published") == 2
        changes = [e["metadata"].get("change") for e in trail["data"] if e["action"] == "forms.updated"]
        assert {"draft_edited", "draft_discarded", "version_restored"} <= set(changes)
        assert changes.count("draft_edited") == 1  # one per form and person per 10 minutes


async def test_overview_folders_and_directory(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, folder = await owner.request("POST", "/folders", body={"name": "Sales"})
        _, form = await owner.request("POST", "/forms", body={"name": "Leads", "folder_id": folder["data"]["id"]})
        form = form["data"]
        _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
        draft = with_field(builder["data"]["schema"], "company", "Company")
        draft = with_field(draft, "secret", "Secret", type="hidden")
        await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": draft})
        await owner.request("POST", f"/forms/{form['id']}/publish", body={"row_version": 2})

        status, reply = await owner.request("GET", f"/forms/{form['id']}/overview")
        assert status == 200, reply
        data = reply["data"]
        assert data["structure"] == {"pages": 1, "fields": 1, "logic": 0, "calculations": 0}
        assert data["preview"] == ["Company"] and len(data["daily"]) == 30 and data["stats"]["responses"] == 0
        assert [v["number"] for v in data["versions"]] == [1] and "change_summary" not in data["versions"][0]

        _, reply = await owner.request("GET", "/folders/overview")
        row = reply["data"][0]
        assert (row["name"], row["forms_count"], row["status_counts"]["published"]) == ("Sales", 1, 1)
        assert row["owners"] == [{"id": form["owner"]["id"], "name": "Olu Ade"}] and row["completion_rate"] == 0
        _, reply = await owner.request("GET", f"/folders/{folder['data']['id']}")
        assert reply["data"]["name"] == "Sales"

        await owner.request("POST", "/org/departments", body={"name": "Ops", "code": "OP", "description": None,
                                                              "member_ids": []})
        _, reply = await owner.request("GET", "/directory")
        data = reply["data"]
        assert data["departments"] == [{"id": data["departments"][0]["id"], "name": "Ops", "detail": "OP"}]
        assert [r["id"] for r in data["roles"]] == ["owner", "admin", "member"]
        assert data["users"] == [{"id": form["owner"]["id"], "name": "Olu Ade", "detail": email}]

        _, counts = await owner.request("GET", "/navigation/counts")
        assert counts["data"]["forms"] == {"all": 1, "draft": 0, "published": 1, "closed": 0, "archived": 0, "trash": 0}
        assert [(f["name"], f["count"]) for f in counts["data"]["folders"]] == [("Sales", 1)]

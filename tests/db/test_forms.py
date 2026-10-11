"""Forms and folders (B5) on a new workspace: create (blank in a language, import, copy), list with filters and
search, edit with row_version, lifecycle, Trash and purge, bulk, folders with access, members' view."""

from __future__ import annotations

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_people import NEW_PASSWORD, join, last_link
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def member_of(http, owner: SecureClient, sub: str, name: str = "mia") -> tuple[SecureClient, str]:  # noqa: ANN001
    _, reply = await owner.request("POST", "/people", body={"first_name": name.title(), "last_name": "Member",
                                                            "email": f"{name}@{sub}.test", "role": "member"})
    await join(http, last_link(f"{name}@{sub}.test"), first_name=name.title(), last_name="Member")
    member = SecureClient(http)
    await sign_in(member, f"{name}@{sub}.test", NEW_PASSWORD)
    return member, reply["data"]["id"]


async def test_forms_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        status, reply = await owner.request("POST", "/folders", body={"name": "Clients", "color": "#112233"})
        assert status == 201, reply
        folder = reply["data"]
        assert folder["can"] == {"edit": True, "delete": True, "access": True} and folder["forms_count"] == 0
        _, reply = await owner.request("POST", "/folders", body={"name": "clients"})
        assert reply["error"]["code"] == "FRM-FORM-1008"

        status, reply = await owner.request("POST", "/forms", body={"name": "  Café survey ", "folder_id": folder["id"],
                                                                    "language": "fr", "label_position": "left"})
        assert status == 201, reply
        form = reply["data"]
        assert (form["name"], form["slug"], form["status"], form["row_version"]) == ("Café survey", "cafe-survey", "draft", 1)
        assert len(form["public_key"]) == 10 and form["folder"]["name"] == "Clients" and form["owner"]["name"] == "Olu Ade"
        assert form["can"]["purge"] and form["my_access"] == "edit" and form["responses_can"]["export"]
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        schema = full["data"]["schema"]
        assert schema["settings"]["language"] == "fr" and schema["settings"]["label_position"] == "left"
        assert schema["thank_you"]["title"] == "Merci !" and schema["pages"][0]["id"].startswith("pg_")
        _, reply = await owner.request("POST", "/forms", body={"name": "From a template", "template_key": "customer_feedback"})
        assert reply["error"]["details"] == [{"field": "template_key", "message": "Choose a template from the gallery."}]

        _, reply = await owner.request("POST", "/forms/import", body={"name": "Imported", "schema": schema})
        imported = reply["data"]
        assert imported["slug"] == "imported"
        _, reply = await owner.request("POST", "/forms/import", body={"name": "Bad", "schema": {"schema_version": 2}})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("POST", f"/forms/{form['id']}/duplicate")
        copied = reply["data"]
        assert copied["name"] == "Café survey (copy)" and copied["slug"] == "cafe-survey-copy"
        _, reply = await owner.request("POST", "/forms", body={"name": "Café survey"})
        assert reply["data"]["slug"] == "cafe-survey-2"

        # Changes, each checked; a stale version refused
        status, reply = await owner.request("PATCH", f"/forms/{form['id']}", body={
            "row_version": 1, "name": "Café feedback", "tags": ["VIP", "vip", "q4"], "folder_id": None,
            "opens_at": "2026-11-01T09:00:00Z", "closes_at": "2026-12-01T09:00:00+01:00"})
        assert status == 200, reply
        assert reply["data"]["tags"] == ["q4", "vip"] and reply["data"]["folder"] is None and reply["data"]["row_version"] == 2
        _, reply = await owner.request("PATCH", f"/forms/{form['id']}", body={"row_version": 1, "name": "Old"})
        assert reply["error"]["code"] == "FRM-GEN-1009"
        _, reply = await owner.request("PATCH", f"/forms/{form['id']}", body={
            "row_version": 2, "opens_at": "2026-12-05T00:00:00Z"})
        assert reply["error"]["details"] == [{"field": "closes_at", "message": "Choose an end after the start."}]
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "forms.updated"})
        fields = {c["field"] for c in trail["data"][0]["changes"]}
        assert {"name", "tags", "folder", "opens_at", "closes_at"} <= fields

        # The list: search, filters, archived hidden unless asked
        _, reply = await owner.request("GET", "/forms", query={"q": "cafe"})
        assert {r["name"] for r in reply["data"]} == {"Café feedback", "Café survey (copy)", "Café survey"}
        _, reply = await owner.request("GET", "/forms", query={"filter[tag]": "vip"})
        assert [r["name"] for r in reply["data"]] == ["Café feedback"]
        assert reply["data"][0]["storage"] == {"mode": "formalie", "datasource": None, "engine": None}
        _, reply = await owner.request("GET", "/forms", query={"filter[folder_id]": folder["id"]})
        assert [r["name"] for r in reply["data"]] == ["Café survey (copy)"]
        _, reply = await owner.request("POST", f"/forms/{imported['id']}/archive", body={"row_version": 1})
        assert reply["data"]["status"] == "archived"
        _, reply = await owner.request("POST", f"/forms/{imported['id']}/close")
        assert reply["error"]["code"] == "FRM-FORM-1007"
        _, reply = await owner.request("GET", "/forms")
        assert "Imported" not in {r["name"] for r in reply["data"]}
        _, reply = await owner.request("GET", "/forms", query={"filter[status]": "archived"})
        assert [r["name"] for r in reply["data"]] == ["Imported"]
        _, reply = await owner.request("POST", f"/forms/{imported['id']}/unarchive")
        assert reply["data"]["status"] == "draft"

        # Trash, restore, purge
        _, reply = await owner.request("DELETE", f"/forms/{imported['id']}")
        assert reply["data"]["deleted_at"]
        _, reply = await owner.request("GET", "/forms", query={"filter[trash]": "1"})
        assert [r["name"] for r in reply["data"]] == ["Imported"]
        _, reply = await owner.request("POST", f"/forms/{imported['id']}/restore")
        assert reply["data"]["deleted_at"] is None
        await owner.request("DELETE", f"/forms/{imported['id']}")
        _, reply = await owner.request("DELETE", f"/forms/{imported['id']}", query={"permanent": "1"})
        assert reply["data"] == {"deleted": True}
        _, reply = await owner.request("GET", f"/forms/{imported['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        _, reply = await owner.request("POST", "/forms/bulk", body={"action": "delete", "ids": [copied["id"], "nope"]})
        assert reply["data"] == {"updated": 1, "failed": [{"id": "nope", "code": "FRM-GEN-1004"}]}
        _, reply = await owner.request("DELETE", "/forms/trash")
        assert reply["data"] == {"deleted": 1, "skipped": 0}

        # Folders: rename, only empty ones go
        _, reply = await owner.request("PATCH", f"/folders/{folder['id']}", body={"name": "Customers", "color": "teal"})
        assert reply["data"]["name"] == "Customers" and reply["data"]["color"] == "teal"
        await owner.request("PATCH", f"/forms/{form['id']}", body={"row_version": 2, "folder_id": folder["id"]})
        _, reply = await owner.request("DELETE", f"/folders/{folder['id']}")
        assert reply["error"]["code"] == "FRM-FORM-1013"
        _, reply = await owner.request("GET", "/folders")
        assert [(f["name"], f["forms_count"]) for f in reply["data"]] == [("Customers", 1)]

        _, facets = await owner.request("GET", "/forms/facets")
        assert facets["data"]["owners"][0]["name"] == "Olu Ade" and facets["data"]["tags"] == ["q4", "vip"]

        # A restricted folder hides its forms from a member; opening it makes them visible again
        member, _ = await member_of(http, owner, sub)
        _, reply = await member.request("GET", "/forms")
        assert form["id"] in {r["id"] for r in reply["data"]}
        await owner.request("PUT", f"/folders/{folder['id']}/access", body={"restricted": True, "roles": ["admin"]})
        _, reply = await member.request("GET", "/forms")
        assert form["id"] not in {r["id"] for r in reply["data"]}
        _, reply = await member.request("GET", f"/forms/{form['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await member.request("GET", "/folders")
        assert reply["data"] == []
        await owner.request("PUT", f"/folders/{folder['id']}/access", body={"restricted": True, "roles": ["member"]})
        _, reply = await member.request("GET", "/folders")
        assert reply["data"][0]["access"] == {"restricted": True, "roles": [], "departments": [], "people": []}

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[area]": "forms", "page_size": 100})
        actions = {e["action"] for e in trail["data"]}
        assert {"forms.created", "forms.updated", "forms.archived", "forms.unarchived", "forms.deleted", "forms.restored",
                "forms.purged", "forms.folder_created", "forms.folder_renamed", "forms.folder_access_changed"} <= actions

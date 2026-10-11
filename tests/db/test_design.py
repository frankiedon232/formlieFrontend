"""Themes, page designs and saved fields (B6) on a new workspace: Formalie's designs built over the workspace's
brand colour, create, change, duplicate, delete, usage counts, a default theme for new forms."""

from __future__ import annotations

import pytest

from app.modules.design.theme import default_theme, system_pages
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_themes_page_designs_and_saved_fields(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        await owner.request("PATCH", "/settings/branding", body={"brand_color": "#0055ff", "signin_message": None})

        status, reply = await owner.request("GET", "/themes", query={"filter[source]": "system", "page_size": 100})
        assert status == 200 and reply["meta"]["total"] == 22
        clean = reply["data"][0]
        assert clean["source"] == "system" and clean["can"] == {"edit": False, "delete": False}
        assert clean["created_by"] == {"id": "system", "name": "Formalie"}
        assert any(t["tokens"]["colors"]["primary"] == "#0055FF" for t in reply["data"])  # the workspace's colour
        _, reply = await owner.request("PATCH", f"/themes/{clean['id']}", body={"name": "Mine"})
        assert reply["error"]["code"] == "FRM-FORM-1014"

        status, reply = await owner.request("POST", "/themes", body={"name": "Calm", "tokens": default_theme(), "source": "created"})
        assert status == 201, reply
        calm = reply["data"]
        assert calm["source"] == "created" and calm["can"] == {"edit": True, "delete": True} and len(calm["id"]) == 27
        _, reply = await owner.request("POST", "/themes", body={"name": "calm", "tokens": default_theme()})
        assert reply["error"]["code"] == "FRM-FORM-1010"
        _, reply = await owner.request("POST", "/themes", body={"name": "Bad", "tokens": {**default_theme(), "layout": "grid"}})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("POST", f"/themes/{clean['id']}/duplicate")
        assert reply["data"]["source"] == "created" and reply["data"]["name"].endswith("(copy)")
        _, reply = await owner.request("PATCH", f"/themes/{calm['id']}", body={"name": "Calm blue"})
        assert reply["data"]["name"] == "Calm blue"

        # A default theme for new forms; a form keeps its copy when the theme goes
        _, defaults = await owner.request("GET", "/settings/form_defaults")
        _, reply = await owner.request("PATCH", "/settings/form_defaults", body={**defaults["data"], "theme_id": calm["id"]})
        assert reply["success"], reply
        _, reply = await owner.request("PATCH", "/settings/form_defaults", body={**defaults["data"], "theme_id": "sys_nope"})
        assert reply["error"]["details"] == [{"field": "theme_id", "message": "theme"}]
        _, form = await owner.request("POST", "/forms", body={"name": "Styled"})
        _, full = await owner.request("GET", f"/forms/{form['data']['id']}")
        assert full["data"]["schema"]["theme_id"] == calm["id"] and full["data"]["schema"]["theme"]["layout"] == "card"
        _, reply = await owner.request("GET", f"/themes/{calm['id']}")
        assert reply["data"]["forms_count"] == 1
        _, insights = await owner.request("GET", "/themes/insights")
        assert insights["data"]["by_source"] == {"system": 22, "saved": 0, "created": 2}
        assert insights["data"]["forms_styled"] == 1 and insights["data"]["top"][0]["id"] == calm["id"]
        _, reply = await owner.request("DELETE", f"/themes/{calm['id']}")
        assert reply["data"] == {"id": calm["id"]}
        _, full = await owner.request("GET", f"/forms/{form['data']['id']}")
        assert full["data"]["schema"]["theme_id"] == calm["id"]  # the form keeps its design

        # Page designs: the same library
        _, reply = await owner.request("GET", "/page-designs", query={"page_size": 100})
        assert reply["meta"]["total"] == len(system_pages(None, None))
        first = reply["data"][0]
        assert first["name_key"].startswith("pages.preset.")
        _, reply = await owner.request("POST", f"/page-designs/{first['id']}/duplicate", body={"name": "Our page"})
        page = reply["data"]
        assert page["name"] == "Our page" and page["tokens"] == first["tokens"]
        _, insights = await owner.request("GET", "/page-designs/insights")
        assert insights["data"]["by_source"]["created"] == 1 and "top" not in insights["data"]

        # Saved fields
        field = {"key": "full_name", "type": "short_text", "label": "Full name", "required": True}
        status, reply = await owner.request("POST", "/field-library", body={"name": "Name", "field": field})
        assert status == 201 and reply["data"]["field"] == field and reply["data"]["can"] == {"edit": False, "delete": True}
        _, reply = await owner.request("GET", "/field-library")
        assert [f["name"] for f in reply["data"]] == ["Name"]
        _, reply = await owner.request("DELETE", f"/field-library/{reply['data'][0]['id']}")
        _, reply = await owner.request("GET", "/field-library")
        assert reply["data"] == []

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[area]": "forms", "page_size": 100})
        actions = {e["action"] for e in trail["data"]}
        assert {"forms.theme_created", "forms.theme_updated", "forms.theme_deleted", "forms.page_design_created",
                "forms.field_saved", "forms.field_removed"} <= actions

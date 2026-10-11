"""Templates (B6) on a new workspace: the gallery in the person's language, a form from a Formalie template and from
the workspace's own, saving a form as a template, edit, update from its form, duplicate, delete, insights, the
audit trail, and another workspace seeing none of it."""

from __future__ import annotations

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_forms import member_of
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_templates_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # The gallery: Formalie's catalogue, use-only
        _, reply = await owner.request("GET", "/templates", query={"page_size": "100"})
        assert reply["meta"]["total"] == 84
        first = reply["data"][0]
        assert first["source"] == "system" and first["can"] == {"edit": False, "delete": False}
        assert first["created_by"] == {"id": "system", "name": "Formalie"} and first["fields_count"] > 0
        _, reply = await owner.request("GET", "/templates/customer_feedback", query={"lang": "fr"})
        feedback_fr = reply["data"]
        assert feedback_fr["schema"]["settings"]["language"] == "fr" and feedback_fr["name"]
        _, reply = await owner.request("GET", "/templates", query={"q": "feedback", "filter[category]": "business"})
        assert any(t["key"] == "customer_feedback" for t in reply["data"])
        _, reply = await owner.request("GET", "/templates/nothing_here")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("PATCH", "/templates/customer_feedback", body={"name": "Mine"})
        assert reply["error"]["code"] == "FRM-FORM-1011"

        # A form from a Formalie template, in French
        status, reply = await owner.request("POST", "/forms", body={"name": "Avis", "template_key": "customer_feedback",
                                                                     "language": "fr"})
        assert status == 201, reply
        form = reply["data"]
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        assert full["data"]["template_key"] == "customer_feedback"
        assert full["data"]["schema"]["settings"]["language"] == "fr"
        _, reply = await owner.request("POST", "/forms", body={"name": "X", "template_key": "ws_000000000000"})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("GET", "/templates", query={"filter[source]": "system", "sort": "-forms_count"})
        assert reply["data"][0]["key"] == "customer_feedback" and reply["data"][0]["forms_count"] == 1

        # Save the form as a workspace template, then make a form from it
        status, reply = await owner.request("POST", "/templates", body={"form_id": form["id"], "name": "Our feedback",
                                                                         "category": "business"})
        assert status == 201, reply
        own = reply["data"]
        assert own["key"] != "customer_feedback" and own["source"] == "workspace" and own["source_form_id"] == form["id"]
        assert own["can"] == {"edit": True, "delete": True} and own["description"] == ""
        _, reply = await owner.request("POST", "/templates", body={"form_id": form["id"], "name": "our FEEDBACK",
                                                                    "category": "business"})
        assert reply["error"]["code"] == "FRM-FORM-1012"
        _, reply = await owner.request("POST", "/forms", body={"name": "From ours", "template_key": own["key"]})
        assert reply["success"], reply
        _, reply = await owner.request("GET", "/templates", query={"filter[form]": form["id"]})
        assert [t["key"] for t in reply["data"]] == [own["key"]] and reply["data"][0]["forms_count"] == 1

        # Edit, update from its form, duplicate
        _, reply = await owner.request("PATCH", f"/templates/{own['key']}", body={"description": "Quarterly survey",
                                                                                  "category": "hr"})
        assert reply["data"]["description"] == "Quarterly survey" and reply["data"]["category"] == "hr"
        _, reply = await owner.request("POST", f"/templates/{own['key']}/sync", body={})
        assert reply["data"]["name"] == "Our feedback"
        _, reply = await owner.request("POST", "/templates/customer_feedback/duplicate", body={})
        copy_ = reply["data"]
        assert copy_["source"] == "workspace" and copy_["name"].endswith("(copy)")
        _, reply = await owner.request("POST", "/templates/customer_feedback/duplicate", body={})
        assert reply["data"]["name"].endswith("(copy 2)")

        # Categories, facets, insights, translation
        _, reply = await owner.request("GET", "/templates/categories", query={"page_size": "100"})
        business = next(c for c in reply["data"] if c["key"] == "business")
        assert business["forms_count"] == 1 and len(business["examples"]) == 3
        _, reply = await owner.request("GET", "/templates/facets")
        assert reply["data"]["total"] == 87 and reply["data"]["workspace"] == 3
        _, reply = await owner.request("GET", "/templates/insights")
        assert reply["data"]["forms_total"] == 2 and reply["data"]["period"]["count"] == 2
        assert len(reply["data"]["daily"]) == 30
        _, reply = await owner.request("POST", "/templates/translate-content",
                                       body={"schema": feedback_fr["schema"], "from": "fr", "to": "en"})
        assert reply["data"]["translated"] > 0
        _, reply = await owner.request("POST", "/templates/translate-content",
                                       body={"schema": feedback_fr["schema"], "from": "fr", "to": "xx"})
        assert reply["error"]["code"] == "FRM-GEN-1002"

        # A member: Formalie's and others' templates are use-only for them
        member, _ = await member_of(http, owner, sub)
        _, reply = await member.request("GET", f"/templates/{own['key']}")
        assert reply["success"], reply
        _, reply = await member.request("DELETE", f"/templates/{own['key']}")
        assert reply["error"]["code"].startswith("FRM-PERM")

        # Facets of the forms list, the form's overview, the sidebar
        _, reply = await owner.request("GET", "/forms/facets")
        assert [t["name"] for t in reply["data"]["templates"]] == ["Customer Feedback", "Our feedback"]
        _, reply = await owner.request("GET", f"/forms/{form['id']}/overview")
        assert reply["data"]["template"] == {"key": "customer_feedback", "name": "Customer Feedback"}
        _, reply = await owner.request("GET", "/navigation/counts")
        assert reply["data"]["templates"]["mine"] == 3 and reply["data"]["templates"]["total"] == 84
        assert reply["data"]["templates"]["categories"][0]["key"] == "business"

        # Delete: forms made from it keep their content
        _, reply = await owner.request("DELETE", f"/templates/{copy_['key']}")
        assert reply["data"] == {"deleted": True}
        _, reply = await owner.request("GET", f"/templates/{copy_['key']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        _, trail = await owner.request("GET", "/audit-logs", query={"page_size": "100"})
        actions = {row["action"] for row in trail["data"]}
        assert {"forms.template_created", "forms.template_updated", "forms.template_duplicated",
                "forms.template_deleted"} <= actions

    # Another workspace sees none of it
    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", f"/templates/{own['key']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("GET", "/templates/facets")
        assert reply["data"]["workspace"] == 0

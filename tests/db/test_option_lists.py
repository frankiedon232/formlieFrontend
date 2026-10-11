"""Option lists (B6) on a new workspace: plain, with levels, with details, kept on the server (more than 20
options); fields from lists, usage, Update forms, lookups as people type, forms following a list."""

from __future__ import annotations

import copy

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def list_field(schema: dict, key: str, list_id: str, options: list, **extra) -> dict:  # noqa: ANN003
    out = copy.deepcopy(schema)
    out["pages"][0]["rows"].append({"id": f"row_{key}", "fields": [
        {"id": f"fld_{key}", "key": key, "type": "dropdown", "label": key.title(), "option_set_id": list_id,
         "options": options, **extra}]})
    return out


async def test_option_lists_from_start_to_finish(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        options = [{"value": "low", "label": "Low", "translations": {"fr": "Faible", "de": " "}},
                   {"value": "high", "label": "High", "score": 2}]
        status, reply = await owner.request("POST", "/option-lists", body={"name": "Priority", "options": options})
        assert status == 201, reply
        priority = reply["data"]
        assert priority["options"] == [{"value": "low", "label": "Low", "translations": {"fr": "Faible"}},
                                       {"value": "high", "label": "High", "score": 2}]
        _, reply = await owner.request("POST", "/option-lists", body={"name": "priority", "options": options})
        assert reply["error"]["code"] == "FRM-FORM-1009"
        _, reply = await owner.request("POST", "/option-lists", body={"name": "Twice", "options": [
            {"value": "a", "label": "A"}, {"value": "A", "label": "B"}]})
        assert reply["error"]["details"] == [{"field": "options", "message": "A"}] and reply["error"]["code"] == "FRM-FORM-1020"
        _, reply = await owner.request("POST", "/option-lists", body={
            "name": "Places", "levels": [{"key": "country", "label": "Country"}, {"key": "city", "label": "City"}],
            "options": [{"value": "fr", "label": "France"}, {"value": "paris", "label": "Paris", "level": 1, "parent": "xx"}]})
        assert reply["error"]["code"] == "FRM-FORM-1021"

        # A form uses the list; the list changes; Update forms brings it back in step
        _, form = await owner.request("POST", "/forms", body={"name": "Tickets", "language": "en"})
        form = form["data"]
        _, builder = await owner.request("GET", f"/forms/{form['id']}/builder")
        schema = builder["data"]["schema"]
        schema["settings"]["languages"] = ["fr"]
        draft = list_field(schema, "priority", priority["id"], [{"value": "low", "label": "Low"},
                                                                 {"value": "high", "label": "High", "score": 2}])
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft", body={"row_version": 1, "schema": draft})
        assert reply["success"], reply
        _, usage = await owner.request("GET", f"/option-lists/{priority['id']}/usage")
        assert usage["data"][0]["fields"] == [{"id": "fld_priority", "key": "priority", "label": "Priority", "in_sync": True}]

        changed = [{**options[0], "label": "Low priority"}, options[1], {"value": "mid", "label": "Medium", "active": False}]
        _, reply = await owner.request("PATCH", f"/option-lists/{priority['id']}", body={"options": changed})
        assert reply["data"]["items_count"] == 2 and reply["data"]["retired_count"] == 1 and reply["data"]["forms_count"] == 1
        _, usage = await owner.request("GET", f"/option-lists/{priority['id']}/usage")
        assert usage["data"][0]["fields"][0]["in_sync"] is False
        _, reply = await owner.request("POST", f"/option-lists/{priority['id']}/sync", body={})
        assert reply["data"] == {"forms": 1, "fields": 1, "published": 0}
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        field = full["data"]["schema"]["pages"][0]["rows"][0]["fields"][0]
        assert field["options"][0]["label"] == "Low priority"
        assert full["data"]["schema"]["translations"]["fr"]["field.fld_priority.option.low"] == "Faible"

        # More than 20 options: kept on the server, fields carry none of them, lookups as people type
        many = [{"value": f"city_{i}", "label": f"City {i}"} for i in range(25)] + [{"value": "sao", "label": "São Paulo"}]
        _, reply = await owner.request("POST", "/option-lists", body={"name": "Cities", "options": many})
        cities = reply["data"]
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        draft = list_field(full["data"]["schema"], "city", cities["id"], [], type="radio")
        _, reply = await owner.request("PUT", f"/forms/{form['id']}/draft",
                                       body={"row_version": full["data"]["row_version"], "schema": draft})
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        city = full["data"]["schema"]["pages"][0]["rows"][1]["fields"][0]
        assert city["options"] == [] and city["options_large"] == {"total": 26} and city["type"] == "dropdown"
        _, reply = await owner.request("GET", f"/option-lists/{cities['id']}/options", query={"q": "SAO"})
        assert reply["data"] == {"items": [{"value": "sao", "label": "São Paulo"}], "total": 1}
        _, reply = await owner.request("GET", f"/option-lists/{cities['id']}/options", query={"values": "city_3,nope"})
        assert reply["data"] == {"items": [{"value": "city_3", "label": "City 3"}], "total": 2}
        _, builder_lists = await owner.request("GET", "/option-lists")
        kept = next(item for item in builder_lists["data"] if item["id"] == cities["id"])
        assert kept["options"] == [] and kept["level_counts"] == [26]

        # The form follows the list at once
        await owner.request("PATCH", f"/option-lists/{cities['id']}", body={"options": [*many, {"value": "x", "label": "X"}]})
        _, full = await owner.request("GET", f"/forms/{form['id']}")
        assert full["data"]["schema"]["pages"][0]["rows"][1]["fields"][0]["options_large"] == {"total": 27}

        _, reply = await owner.request("GET", "/option-lists", query={"page": 1, "sort": "-items_count"})
        assert [r["name"] for r in reply["data"]] == ["Cities", "Priority"] and len(reply["data"][0]["options"]) == 20
        _, insights = await owner.request("GET", "/option-lists/insights")
        assert insights["data"]["total"] == 2 and insights["data"]["in_use"] == 2 and insights["data"]["retired"] == 1

        _, reply = await owner.request("POST", f"/option-lists/{priority['id']}/duplicate")
        assert reply["data"]["name"] == "Priority (copy)" and len(reply["data"]["options"]) == 3
        _, reply = await owner.request("DELETE", f"/option-lists/{reply['data']['id']}")
        assert reply["success"]

        _, trail = await owner.request("GET", "/audit-logs", query={"filter[area]": "forms", "page_size": 100})
        actions = {e["action"] for e in trail["data"]}
        assert {"forms.list_created", "forms.list_updated", "forms.list_synced", "forms.list_deleted"} <= actions

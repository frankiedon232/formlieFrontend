"""A public form with a list kept on the server (more than 20 options): the page gets no options, only their
count; lookups as people type come from the list; a chosen option is stored and its detail fills a formula."""

from __future__ import annotations

import pytest

from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_long_list_on_a_public_form(app, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        options = [{"value": f"city_{i}", "label": f"City {i}", "attrs": {"fee": i}} for i in range(24)] + [
            {"value": "sao", "label": "São Paulo", "attrs": {"fee": 100}}]
        _, reply = await owner.request("POST", "/option-lists", body={
            "name": "Cities", "options": options, "columns": [{"key": "fee", "label": "Fee"}]})
        cities = reply["data"]

        def build(schema: dict) -> dict:
            out = with_field(schema, "city", "City", type="dropdown", option_set_id=cities["id"], options=[], required=True)
            return with_field(out, "fee", "Fee", type="calculated", props={"formula": "{city.fee} * 2"})
        form = await publish(owner, "Trip", build)
        key = form["public_key"]

        visitor = SecureClient(http)
        _, reply = await visitor.request("GET", f"/public/forms/{key}")
        city = reply["data"]["schema"]["pages"][0]["rows"][0]["fields"][0]
        assert city["options"] == [] and city["options_remote"] == {"total": 25}
        _, reply = await visitor.request("GET", f"/public/forms/{key}/options", query={"field": "city", "q": "sao"})
        assert reply["data"]["total"] == 1 and reply["data"]["items"][0] == {"value": "sao", "label": "São Paulo",
                                                                            "attrs": {"fee": 100}}
        _, reply = await visitor.request("GET", f"/public/forms/{key}/options", query={"field": "city", "values": "city_3"})
        assert reply["data"]["items"][0]["label"] == "City 3"

        status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
            "data": {"city": "sao"}, "challenge": await solved(visitor, key)}, headers=session())
        assert status == 201, reply
        response_id = reply["data"]["response_id"]
        _, reply = await owner.request("GET", f"/responses/{response_id}")
        assert reply["data"]["data"]["city"] == "sao" and reply["data"]["data"]["fee"] == 200
        # The response's form carries only the option that was answered
        city = reply["data"]["schema"]["pages"][0]["rows"][0]["fields"][0]
        assert city["options"] == [{"value": "sao", "label": "São Paulo", "attrs": {"fee": 100}}]
        assert city["options_large"] == {"total": 25, "partial": True}

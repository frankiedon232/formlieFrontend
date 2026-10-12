"""Security review B17, H2: a saved connection's stored secrets are reused only by someone who may edit it, only for
the same server and account, and never with weaker encryption than the connection already had."""

from __future__ import annotations

import pytest

from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import customer, on_plan, run, tests_run  # noqa: F401  (fixtures)
from tests.db.test_people import NEW_PASSWORD, join, last_link
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

ACCESS = {"table_prefix": "formalie_", "tables_schema": "", "other": "read_write", "schemas": []}


def problems(reply: dict) -> tuple[str, dict[str, str]]:
    return reply["error"]["code"], {d["field"]: d["message"] for d in reply["error"].get("details") or []}


async def test_stored_secrets_stay_with_their_server(app, owner_dsn, tests_run) -> None:  # noqa: ANN001, F811
    db = customer()
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        status, reply = await owner.request("POST", "/datasources", body={
            "name": "Production", "engine": "postgresql", "settings": db["settings"], "access": ACCESS,
            "secrets": db["secrets"]})
        assert status == 201, reply
        source = reply["data"]
        moved = {**db["settings"], "host": "db.attacker.example"}

        # Another server: the stored password is not reused, it must be typed again
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": moved, "access": ACCESS, "secrets": {}, "datasource_id": source["id"]})
        assert problems(reply) == ("FRM-GEN-1002", {"password": "required"})
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": {**db["settings"], "username": "someone_else"}, "access": ACCESS,
            "secrets": {}, "datasource_id": source["id"]})
        assert problems(reply) == ("FRM-GEN-1002", {"password": "required"})
        _, reply = await owner.request("PATCH", f"/datasources/{source['id']}", body={"settings": moved})
        assert problems(reply) == ("FRM-GEN-1002", {"password": "required"})

        # The same server with weaker encryption than the saved connection: refused while the secret is reused
        _, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": {**db["settings"], "ssl_mode": "disable"}, "access": ACCESS,
            "secrets": {}, "datasource_id": source["id"]})
        assert problems(reply) == ("FRM-DEST-1003", {"ssl_mode": "tls_required_with_saved_secrets"})
        _, reply = await owner.request("PATCH", f"/datasources/{source['id']}", body={
            "settings": {**db["settings"], "ssl_mode": "allow"}})
        assert problems(reply) == ("FRM-DEST-1003", {"ssl_mode": "tls_required_with_saved_secrets"})
        # ... typed again, it is the person's own choice
        status, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": {**db["settings"], "ssl_mode": "disable"}, "access": ACCESS,
            "secrets": db["secrets"], "datasource_id": source["id"]})
        assert status == 201, reply

        # The same server and account as saved: the stored secret is reused
        status, reply = await owner.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": db["settings"], "access": ACCESS, "secrets": {},
            "datasource_id": source["id"]})
        assert status == 201, reply
        await run(tests_run)
        _, reply = await owner.request("GET", f"/datasources/tests/{reply['data']['id']}")
        assert next(s for s in reply["data"]["steps"] if s["key"] == "sign_in")["status"] == "passed"

        # Someone who may only look at connections can't test one with its stored secrets
        status, reply = await owner.request("POST", "/roles", body={"name": "Analysts", "grants": {"data.view": "all"}})
        assert status == 201, reply
        role = reply["data"]["id"]
        status, reply = await owner.request("POST", "/people", body={
            "first_name": "Ana", "last_name": "Lyst", "email": f"ana@{sub}.test", "role": role})
        assert status == 201, reply
        joined = await join(http, last_link(f"ana@{sub}.test"))
        assert joined["accepted"]["data"]["status"] == "active", joined
        analyst = SecureClient(http)
        await sign_in(analyst, f"ana@{sub}.test", NEW_PASSWORD)
        _, reply = await analyst.request("GET", f"/datasources/{source['id']}")
        assert reply["data"]["can"] == {"edit": False, "delete": False}
        _, reply = await analyst.request("POST", "/datasources/test", body={
            "engine": "postgresql", "settings": db["settings"], "access": ACCESS, "secrets": {},
            "datasource_id": source["id"]})
        assert reply["error"]["code"] == "FRM-PERM-1001"

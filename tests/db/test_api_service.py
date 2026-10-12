"""API service management (B10 step 1) end to end: the address handle and its rotation (with the tenant directory),
services, endpoints on a published form, field choices and API names, tokens (secrets once, only hashes looked up,
reveal after the password, rotate, revoke, delete), access rules and the access test, rate limits, connections, the
audit trail, and another workspace seeing none of it."""

from __future__ import annotations

import hashlib

import pytest

from app.core.config import get_settings
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_public_forms import publish
from scripts.seed_dev import MOCK_PASSWORD
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def job_form(schema: dict) -> dict:
    out = with_field(schema, "first_name", "First name", required=True)
    out = with_field(out, "email", "Email", type="email")
    return with_field(out, "reference", "Reference", readonly=True)


def errors(reply: dict) -> tuple[str, dict[str, str]]:
    return reply["error"]["code"], {d["field"]: d["message"] for d in reply["error"].get("details") or []}


async def test_api_service_from_start_to_finish(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    base = f"https://api.{get_settings().root_domain}"
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)

        # The address handle, made at sign-up and registered in the tenant directory
        _, reply = await owner.request("GET", "/api-service/settings")
        settings = reply["data"]
        key = settings["api_key"]
        assert len(key) == 10 and settings["base_url"] == base and settings["previous_key"] is None
        tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
        assert superuser.execute("SELECT tenant_id, current FROM platform.resolve_api_key(%s)", (key,)).fetchone() == (tenant_id, True)
        _, reply = await owner.request("GET", "/api-service/setup")
        assert reply["data"] == {"services": 0, "endpoints": 0, "endpoints_live": 0, "tokens_live": 0, "tokens_test": 0, "rules": 0}

        # Services
        _, reply = await owner.request("POST", "/api-services", body={"name": "Website", "allowed_origins": ["ftp://x.example"]})
        assert errors(reply) == ("FRM-GEN-1002", {"allowed_origins": "ftp://x.example"})
        status, reply = await owner.request("POST", "/api-services", body={
            "name": "Website", "description": "Sign-ups", "allowed_origins": ["Shop.Example.com/", "https://shop.example.com"]})
        assert status == 201, reply
        service = reply["data"]
        assert service["allowed_origins"] == ["https://shop.example.com"] and service["status"] == "active"
        assert service["endpoints_count"] == 0 and service["calls_30d"] == 0 and len(service["daily"]) == 30
        _, reply = await owner.request("POST", "/api-services", body={"name": "website"})
        assert reply["error"]["code"] == "FRM-API-1003"
        _, reply = await owner.request("GET", f"/api-services/{service['id']}")
        assert reply["data"]["can"] == {"edit": True, "delete": True} and reply["data"]["created_by"]["name"] == "Olu Ade"

        # Endpoints on a published form open to the API
        form = await publish(owner, "Job application", job_form)
        _, reply = await owner.request("GET", "/api-endpoints/form-fields", query={"form_id": form["id"]})
        fields = reply["data"]["fields"]
        assert reply["data"]["versions"] == [1]
        assert [(f["key"], f["name"], f["accept"], f["required"]) for f in fields] == [
            ("first_name", "first_name", True, True), ("email", "email", True, False), ("reference", "reference", False, False)]
        choices = [{"key": f["key"], "accept": f["accept"], "required": f["required"], "returned": True, "filter": False}
                   for f in fields]
        body = {"name": "apply", "service_id": service["id"], "form_id": form["id"], "version": None,
                "methods": ["POST", "GET"], "fields": choices, "page_size": 50}
        _, reply = await owner.request("POST", "/api-endpoints", body={**body, "name": "ab"})
        assert errors(reply) == ("FRM-GEN-1002", {"name": "pattern"})
        _, reply = await owner.request("POST", "/api-endpoints", body={**body, "fields": [{**choices[1], "name": "id"}]})
        assert errors(reply) == ("FRM-GEN-1002", {"fields.email.name": "reserved"})
        status, reply = await owner.request("POST", "/api-endpoints", body=body)
        assert status == 201, reply
        endpoint = reply["data"]
        assert endpoint["url"] == f"{base}/{key}/apply" and endpoint["status"] == "disabled"
        assert endpoint["methods"] == ["GET", "POST"] and endpoint["fields_accepted"] == 2 and endpoint["fields_returned"] == 3
        assert endpoint["form"] == {"id": form["id"], "name": "Job application", "status": "published"}
        assert endpoint["setup"] == {"service_active": True, "form_published": True, "form_api": True, "tokens_live": 0,
                                     "tokens_test": 0, "tokens_all_live": 0, "tokens_all_test": 0, "signing_tokens": 0,
                                     "rules": 0, "live": False}
        assert endpoint["versions"] == [1] and endpoint["headers"] == [] and endpoint["page_size"] == 50
        _, reply = await owner.request("POST", "/api-endpoints", body=body)
        assert errors(reply) == ("FRM-API-1001", {"name": "taken"})
        draft = (await owner.request("POST", "/forms", body={"name": "Draft"}))[1]["data"]
        _, reply = await owner.request("POST", "/api-endpoints", body={**body, "name": "draft-one", "form_id": draft["id"]})
        assert errors(reply) == ("FRM-API-1002", {"form_id": "not_published"})
        closed = await publish(owner, "Web only", job_form)
        _, reply = await owner.request("PUT", f"/forms/{closed['id']}/share", body={"channels": ["link"]})
        assert reply["success"], reply
        _, reply = await owner.request("POST", "/api-endpoints", body={**body, "name": "web-only", "form_id": closed["id"]})
        assert errors(reply) == ("FRM-API-1019", {"form_id": "not_for_api"})

        # Go live, then rename a field for apps
        _, reply = await owner.request("PATCH", f"/api-endpoints/{endpoint['id']}", body={"status": "active"})
        assert reply["data"]["status"] == "active" and reply["data"]["setup"]["live"] is True
        renamed = [{**c, "name": "given_name"} if c["key"] == "first_name" else c for c in choices]
        _, reply = await owner.request("PATCH", f"/api-endpoints/{endpoint['id']}", body={**body, "name": "applications",
                                                                                          "fields": renamed})
        assert reply["data"]["name"] == "applications" and reply["data"]["status"] == "active"
        assert reply["data"]["fields"][0]["name"] == "given_name" and reply["data"]["url"].endswith("/applications")
        _, reply = await owner.request("GET", "/api-endpoints", query={"filter[service]": service["id"], "filter[method]": "GET"})
        assert [r["name"] for r in reply["data"]] == ["applications"] and reply["meta"]["total"] == 1
        _, reply = await owner.request("GET", "/api-endpoints/insights")
        assert reply["data"]["total"] == 1 and reply["data"]["by_method"] == {"GET": 1, "POST": 1, "PUT": 0, "DELETE": 0}
        _, reply = await owner.request("GET", "/api-services/insights")
        assert reply["data"]["by_status"] == {"active": 1, "disabled": 0} and reply["data"]["by_method"]["POST"] == 1

        # Tokens: secrets once, only a hash looked up
        scopes = {"services": [service["id"]], "endpoints": [], "methods": []}
        _, reply = await owner.request("POST", "/api-tokens", body={"name": "Old", "kind": "static", "mode": "live",
                                                                    "scopes": scopes, "expires_at": "2020-01-01T00:00:00Z"})
        assert errors(reply) == ("FRM-GEN-1002", {"expires_at": "range"})
        status, reply = await owner.request("POST", "/api-tokens", body={"name": "Website sign-ups", "kind": "static",
                                                                         "mode": "live", "scopes": scopes, "expires_at": None})
        assert status == 201, reply
        live, secret = reply["data"]["token"], reply["data"]["secrets"]["token"]
        assert secret.startswith("formalie_live_") and live["preview"] == f"formalie_live_…{secret[-4:]}"
        assert live["scope_names"] == {"services": ["Website"], "endpoints": []} and live["viewable"] is True
        row = superuser.execute("SELECT secret_hash, secret_enc FROM formaly.api_tokens WHERE tenant_id = %s "
                                "AND name = 'Website sign-ups'", (tenant_id,)).fetchone()
        assert row[0] == hashlib.sha256(secret.encode()).hexdigest() and secret not in row[1]
        _, reply = await owner.request("POST", "/api-tokens", body={"name": "Partner", "kind": "client", "mode": "test",
                                                                    "scopes": {"services": [], "endpoints": [], "methods": []},
                                                                    "expires_at": None, "lifetime_minutes": 30})
        client = reply["data"]["token"]
        assert client["preview"] == client["client_id"] and client["client_id"].startswith("formalie_client_test_")
        assert reply["data"]["secrets"]["client_secret"].startswith("formalie_secret_test_") and client["lifetime_minutes"] == 30
        _, reply = await owner.request("POST", "/api-tokens", body={"name": "Hook", "kind": "webhook", "mode": "test",
                                                                    "scopes": scopes, "expires_at": None})
        hook = reply["data"]["token"]
        assert hook["mode"] == "live" and hook["scopes"] == {"services": [], "endpoints": [], "methods": []}
        _, reply = await owner.request("GET", "/api-tokens", query={"filter[kind]": "client,static"})
        assert [r["name"] for r in reply["data"]] == ["Partner", "Website sign-ups"]
        _, reply = await owner.request("GET", "/api-tokens/insights")
        assert reply["data"]["total"] == 3 and reply["data"]["by_mode"] == {"live": 2, "test": 1} and reply["data"]["unused_90d"] == 0
        _, reply = await owner.request("GET", f"/api-endpoints/{endpoint['id']}")
        setup = reply["data"]["setup"]
        assert (setup["tokens_live"], setup["tokens_test"], setup["tokens_all_live"], setup["tokens_all_test"]) == (1, 0, 0, 1)

        # Rotate, reveal after the password, revoke, delete
        _, reply = await owner.request("POST", f"/api-tokens/{live['id']}/rotate", body={"grace_hours": 24})
        rotated = reply["data"]["secrets"]["token"]
        assert rotated != secret and reply["data"]["token"]["rotating_until"]
        _, reply = await owner.request("POST", f"/api-tokens/{live['id']}/reveal", body={"password": "wrong-one"})
        assert errors(reply) == ("FRM-AUTH-1013", {"password": "4"})
        _, reply = await owner.request("POST", f"/api-tokens/{live['id']}/reveal", body={"password": PASSWORD})
        assert reply["data"] == {"token": rotated}
        _, reply = await owner.request("DELETE", f"/api-tokens/{live['id']}")
        assert reply["error"]["code"] == "FRM-API-1005"
        _, reply = await owner.request("POST", f"/api-tokens/{hook['id']}/revoke", body={})
        assert reply["data"]["status"] == "revoked" and reply["data"]["viewable"] is False
        _, reply = await owner.request("PATCH", f"/api-tokens/{hook['id']}", body={"name": "Renamed"})
        assert reply["error"]["code"] == "FRM-API-1004"
        _, reply = await owner.request("DELETE", f"/api-tokens/{hook['id']}")
        assert reply["data"] == {"deleted": True}
        _, reply = await owner.request("PATCH", f"/api-tokens/{live['id']}", body={"name": "Website"})
        assert reply["data"]["name"] == "Website"

        # Access rules and the access test
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "ip", "values": ["192.0.2.66", "not-an-ip"], "scope": {"type": "all", "id": None}})
        assert errors(reply) == ("FRM-GEN-1002", {"values.1": "ip"})
        status, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "ip", "values": ["192.0.2.66", " 192.0.2.66 ", "198.51.100.0/28"],
            "scope": {"type": "endpoint", "id": endpoint["id"]}, "note": "Scraping"})
        assert status == 201, reply
        block = reply["data"]
        assert block["values"] == ["192.0.2.66", "198.51.100.0/28"] and block["scope"]["name"] == "applications"
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "allow", "kind": "domain", "values": ["*.Example.com"], "scope": {"type": "service", "id": service["id"]}})
        allow = reply["data"]
        test = {"endpoint_id": endpoint["id"], "ip": "198.51.100.7", "origin": "https://shop.example.com", "country": "gb"}
        _, reply = await owner.request("POST", "/api-access-rules/test", body=test)
        assert reply["data"]["allowed"] is False and reply["data"]["reason"] == "blocked"
        assert reply["data"]["rule"]["value"] == "198.51.100.0/28" and reply["data"]["checked"] == 2 and reply["data"]["region"] == "EU"
        _, reply = await owner.request("POST", "/api-access-rules/test", body={**test, "ip": "203.0.113.9"})
        assert reply["data"]["allowed"] is True and reply["data"]["rule"]["id"] == allow["id"]
        _, reply = await owner.request("POST", "/api-access-rules/test", body={**test, "ip": "203.0.113.9", "origin": "other.org"})
        assert reply["data"]["reason"] == "not_allowed"
        _, reply = await owner.request("PATCH", f"/api-access-rules/{allow['id']}", body={"enabled": False})
        assert reply["data"]["enabled"] is False
        _, reply = await owner.request("GET", "/api-access-rules", query={"filter[state]": "off"})
        assert [r["id"] for r in reply["data"]] == [allow["id"]]
        _, reply = await owner.request("GET", "/api-access-rules/insights")
        assert reply["data"]["by_kind"]["ip"] == 1 and reply["data"]["by_action"] == {"allow": 1, "block": 1}

        # Rate limits
        _, reply = await owner.request("GET", "/api-service/limits")
        assert reply["data"] == {"per_token": 600, "per_ip": 120, "per_endpoint": 1200, "updated_at": None}
        _, reply = await owner.request("PUT", "/api-service/limits", body={"per_token": 300, "per_ip": 120, "per_endpoint": None})
        assert reply["data"]["per_token"] == 300 and reply["data"]["per_endpoint"] is None and reply["data"]["updated_at"]

        # Connections
        _, reply = await owner.request("GET", "/api-service/connections", query={"type": "service", "id": service["id"]})
        links = reply["data"]
        assert [e["name"] for e in links["endpoints"]] == ["applications"]
        assert {(t["name"], t["reach"]) for t in links["tokens"]} == {("Website", "service"), ("Partner", "all")}
        assert {(r["action"], r["reach"]) for r in links["rules"]} == {("block", "endpoint"), ("allow", "service")}
        _, reply = await owner.request("GET", "/api-service/connections", query={"type": "token", "id": live["id"]})
        assert reply["data"]["service"]["name"] == "Website" and [e["name"] for e in reply["data"]["endpoints"]] == ["applications"]
        _, reply = await owner.request("GET", "/api-service/connections", query={"type": "endpoint", "id": endpoint["id"]})
        assert reply["data"]["form"]["name"] == "Job application" and reply["data"]["service"]["id"] == service["id"]

        # A new address handle: the old one keeps answering for the grace period
        _, reply = await owner.request("POST", "/api-service/key/rotate", body={"grace_hours": 24})
        assert reply["data"]["previous_key"] == key and reply["data"]["api_key"] != key and reply["data"]["rotated_at"]
        assert superuser.execute("SELECT current FROM platform.resolve_api_key(%s)", (key,)).fetchone() == (False,)
        new_key = reply["data"]["api_key"]
        _, reply = await owner.request("POST", "/api-service/key/rotate", body={"grace_hours": 0})
        assert reply["data"]["previous_key"] is None
        assert superuser.execute("SELECT count(*) FROM platform.resolve_api_key(%s)", (new_key,)).fetchone() == (0,)
        assert superuser.execute("SELECT count(*) FROM platform.resolve_api_key(%s)", (key,)).fetchone() == (0,)

        # Duplicate a service, then delete the original (its endpoints and rules go too; tokens keep the gone scope)
        status, reply = await owner.request("POST", f"/api-services/{service['id']}/duplicate", body={})
        assert status == 201 and reply["data"]["name"] == "Website (copy)" and reply["data"]["status"] == "disabled"
        assert reply["data"]["endpoints_count"] == 1
        _, reply = await owner.request("GET", "/api-endpoints", query={"sort": "name"})
        assert [(r["name"], r["status"]) for r in reply["data"]] == [("applications", "active"), ("applications-copy", "disabled")]
        _, reply = await owner.request("DELETE", f"/api-services/{service['id']}")
        assert reply["data"] == {"deleted": True, "endpoints": 1}
        _, reply = await owner.request("GET", f"/api-endpoints/{endpoint['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("GET", "/api-access-rules")
        assert reply["data"] == []
        _, reply = await owner.request("GET", f"/api-tokens/{live['id']}")
        assert reply["data"]["scope_gone"] == 1 and reply["data"]["scope_names"]["services"] == []

    actions = {r[0] for r in superuser.execute(
        "SELECT action FROM formaly.audit_logs WHERE tenant_id = %s AND action LIKE 'api.%%'", (tenant_id,)).fetchall()}
    assert actions == {"api.service_created", "api.endpoint_created", "api.endpoint_enabled", "api.endpoint_updated",
                       "api.token_created", "api.token_rotated", "api.token_revealed", "api.token_revoked", "api.token_deleted",
                       "api.token_updated", "api.rule_created", "api.rule_disabled", "api.limits_changed", "api.key_rotated",
                       "api.service_deleted"}

    # Another workspace sees none of it, even with the references
    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        for path in (f"/api-services/{service['id']}", f"/api-tokens/{live['id']}", f"/api-access-rules/{block['id']}"):
            _, reply = await stranger.request("GET", path)
            assert reply["error"]["code"] == "FRM-GEN-1004", path
        _, reply = await stranger.request("GET", "/api-tokens")
        assert reply["data"] == []
        _, reply = await stranger.request("PATCH", f"/api-tokens/{live['id']}", body={"name": "Mine"})
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("POST", "/api-endpoints", body={**body, "name": "steal", "service_id": service["id"]})
        assert errors(reply) == ("FRM-GEN-1002", {"service_id": "required"})
        _, reply = await stranger.request("GET", "/api-endpoints/form-fields", query={"form_id": form["id"]})
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await stranger.request("GET", "/api-service/settings")
        assert reply["data"]["api_key"] not in (key, new_key)


async def test_ids_must_arrive_as_references(app) -> None:  # noqa: ANN001
    """A raw id typed into a body is refused (SECURITY-PROTOCOL §10)."""
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/api-services", body={"name": "One"})
        service = reply["data"]
        raw = "0190d8b0-0000-7000-8000-000000000000"
        _, reply = await owner.request("POST", "/api-tokens", body={"name": "T", "kind": "static", "mode": "live",
                                                                    "scopes": {"services": [raw], "endpoints": [], "methods": []},
                                                                    "expires_at": None})
        assert errors(reply) == ("FRM-GEN-1002", {"scopes": "services"})
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "country", "values": ["gb"], "scope": {"type": "service", "id": service["id"]}})
        assert reply["data"]["values"] == ["GB"] and reply["data"]["scope"]["name"] == "One"


async def test_seeded_workspace_has_the_mock_samples(app) -> None:  # noqa: ANN001
    """scripts/seed_dev.py gives the seeded workspaces the mock's sample API service (data/apiStore.ts)."""
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        admin = SecureClient(http)
        await sign_in(admin, "admin@remedylegal.test", MOCK_PASSWORD)
        _, reply = await admin.request("GET", "/api-services", query={"sort": "name"})
        assert [(s["name"], s["status"]) for s in reply["data"]] == [
            ("Customer onboarding", "active"), ("Internal tools", "disabled"), ("Partner bookings", "active")]
        _, reply = await admin.request("GET", "/api-tokens", query={"sort": "name"})
        tokens = {t["name"]: t for t in reply["data"]}
        assert {n: t["status"] for n, t in tokens.items() if n != "Mobile app"} == {
            "Old import script": "revoked", "Partner sandbox": "active", "Website sign-ups": "active"}
        assert tokens["Mobile app"]["status"] in ("expiring", "expired")  # 9 days from when the test database was seeded
        assert tokens["Website sign-ups"]["scope_names"]["services"] == ["Customer onboarding"] and tokens["Website sign-ups"]["viewable"]
        assert tokens["Partner sandbox"]["preview"].startswith("formalie_client_test_")
        _, reply = await admin.request("GET", "/api-access-rules/insights")
        assert reply["data"]["total"] == 3 and reply["data"]["by_action"] == {"allow": 1, "block": 2}
        _, reply = await admin.request("GET", "/api-service/limits")
        assert (reply["data"]["per_token"], reply["data"]["per_ip"], reply["data"]["per_endpoint"]) == (600, 120, 1200)


async def test_settings_are_made_once_even_when_asked_at_once(engines, two_workspaces) -> None:  # noqa: ANN001
    """A workspace made before the API service gets its handle on the first visit; visits at the same time agree."""
    import asyncio

    from app.core.db.session import db_session
    from app.modules.api_service.service import ensure_settings

    ws = two_workspaces[0]

    async def first_visit() -> str:
        async with db_session("write", tenant_id=ws.tenant_id, organisation_id=ws.organisation_id) as db:
            return (await ensure_settings(db, ws.tenant_id, ws.organisation_id)).api_key

    keys = await asyncio.gather(*(first_visit() for _ in range(4)))
    assert len(set(keys)) == 1 and len(keys[0]) == 10

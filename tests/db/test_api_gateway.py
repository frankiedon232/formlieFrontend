"""The public API service gateway (B10 step 3) end to end, through api.formalie.dev: every check in the mock's order,
CORS preflights, static tokens and client credentials, signed calls and replays, the Formalie-Key replay, rate limits
with Retry-After, test tokens storing nothing, a real POST reaching the portal's responses, the API log and the audit
trail, PUT and DELETE, files, Try it, the gateway as its own app, and one workspace's token or address never reaching
another's data."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest

from app.core.security.fernet_tokens import encrypt_secret
from tests.conftest import MemoryShipper, client_for
from tests.db.test_api_service import errors, job_form
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_destinations import real
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

API = "api.formalie.dev"


def key() -> dict[str, str]:
    return {"Formalie-Key": str(uuid.uuid4())}


def cv_form(schema: dict) -> dict:
    out = job_form(schema)
    return with_field(out, "cv", "CV", type="file_upload", props={"accept": ".pdf,.txt"})


async def setup(owner: SecureClient, *, methods: list[str] | None = None, build=job_form,  # noqa: ANN001
                origins: list[str] | None = None) -> dict:
    """A service, a live endpoint on a published form, a live static token, a test token, a client and a webhook token."""
    _, reply = await owner.request("POST", "/api-services", body={"name": f"Website {uuid.uuid4().hex[:6]}",
                                                                  "allowed_origins": origins or ["https://shop.example.com"]})
    service = reply["data"]
    form = await publish(owner, "Job application", build)
    _, reply = await owner.request("GET", "/api-endpoints/form-fields", query={"form_id": form["id"]})
    choices = [{"key": f["key"], "accept": f["accept"], "required": f["required"], "returned": True,
                "filter": f["key"] == "email"} for f in reply["data"]["fields"]]
    name = f"apply-{uuid.uuid4().hex[:6]}"
    _, reply = await owner.request("POST", "/api-endpoints", body={
        "name": name, "service_id": service["id"], "form_id": form["id"], "version": None,
        "methods": methods or ["GET", "POST", "PUT", "DELETE"], "fields": choices, "page_size": 50, "status": "active"})
    assert reply["success"], reply
    endpoint = reply["data"]
    made = {"service": service, "form": form, "endpoint": endpoint}
    for label, kind, mode in (("live", "static", "live"), ("test", "static", "test"), ("client", "client", "live"),
                              ("hook", "webhook", "live")):
        _, reply = await owner.request("POST", "/api-tokens", body={
            "name": f"{label} token", "kind": kind, "mode": mode, "expires_at": None,
            "scopes": {"services": [], "endpoints": [], "methods": []}})
        assert reply["success"], reply
        made[label] = reply["data"]["token"]
        made[f"{label}_secret"] = reply["data"]["secrets"].get("token") or reply["data"]["secrets"].get("client_secret")
    _, reply = await owner.request("GET", "/api-service/settings")
    made["api_key"] = reply["data"]["api_key"]
    made["path"] = f"/{made['api_key']}/{name}"
    return made


def bearer(secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


async def call(api, method: str, path: str, *, token: str | None = None, body=None, headers=None, **kwargs):  # noqa: ANN001, ANN003
    sent = {**(bearer(token) if token else {}), **(headers or {})}
    if body is not None:
        kwargs["content"] = body if isinstance(body, (bytes, str)) else json.dumps(body)
    response = await api.request(method, path, headers=sent, **kwargs)
    return response.status_code, (response.json() if response.content else None), response


async def test_order_of_checks_cors_and_tokens(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, client_for(app, host=API) as api, \
            client_for(app, host=API, peer="192.0.2.66") as blocked:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
        path, live, test_token = made["path"], made["live_secret"], made["test_secret"]

        # Address key, path, endpoint
        status, reply, _ = await call(api, "GET", "/nokey1234/apply", token=live)
        assert (status, errors(reply)) == (404, ("FRM-API-1006", {"address_key": "unknown"}))
        _, reply, _ = await call(api, "GET", f"{path}/a/b", token=live)
        assert errors(reply) == ("FRM-API-1006", {"path": "too_long"})
        _, reply, _ = await call(api, "GET", f"/{made['api_key']}/nowhere", token=live)
        assert errors(reply) == ("FRM-API-1006", {"endpoint": "unknown"})

        # Access rules come before the token: a blocked address is refused even without one
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "ip", "values": ["192.0.2.66"], "scope": {"type": "all", "id": None}})
        rule = reply["data"]
        status, reply, _ = await call(blocked, "GET", path)
        assert (status, errors(reply)) == (403, ("FRM-API-1015", {"blocked": "192.0.2.66"}))
        _, reply, _ = await call(api, "GET", path, token=live, headers={"X-Debug-Country": "gb"})
        assert reply["data"] == []
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "country", "values": ["BR"], "scope": {"type": "endpoint", "id": made["endpoint"]["id"]}})
        country_rule = reply["data"]
        _, reply, _ = await call(api, "GET", path, token=live, headers={"X-Debug-Country": "br"})
        assert errors(reply) == ("FRM-API-1015", {"blocked": "BR"})
        _, reply = await owner.request("POST", "/api-access-rules", body={
            "action": "block", "kind": "network", "values": ["tor"], "scope": {"type": "all", "id": None}})
        _, reply, _ = await call(api, "GET", path, token=live, headers={"X-Debug-Network": "tor, nothing"})
        assert errors(reply) == ("FRM-API-1015", {"blocked": "tor"})
        await owner.request("DELETE", f"/api-access-rules/{country_rule['id']}")

        # Tokens: none, a wrong one, a webhook token, a client id sent as Bearer
        status, reply, _ = await call(api, "GET", path)
        assert (status, reply["error"]["code"]) == (401, "FRM-API-1010")
        _, reply, _ = await call(api, "GET", path, token="formalie_live_wrong")
        assert reply["error"]["code"] == "FRM-API-1010"
        _, reply, _ = await call(api, "GET", path, token=made["hook_secret"])
        assert errors(reply)[1]["Authorization"].startswith("webhook_token")
        _, reply, _ = await call(api, "GET", path, token=made["client"]["client_id"])
        assert errors(reply)[1]["Authorization"].startswith("client_credentials")

        # Client credentials: /token gives a short-lived token that works until its client stops
        status, reply, _ = await call(api, "GET", f"/{made['api_key']}/token")
        assert (status, reply["error"]["code"]) == (405, "FRM-API-1008")
        _, reply, _ = await call(api, "POST", f"/{made['api_key']}/token", body={"client_id": made["client"]["client_id"],
                                                                                  "client_secret": "nope"})
        assert reply["error"]["code"] == "FRM-API-1010"
        _, reply, _ = await call(api, "POST", f"/{made['api_key']}/token", body={"client_id": live})
        assert errors(reply)[1]["token"].startswith("bearer_token")
        status, reply, _ = await call(api, "POST", f"/{made['api_key']}/token", body={
            "client_id": made["client"]["client_id"], "client_secret": made["client_secret"]})
        assert status == 200 and reply["token_type"] == "Bearer" and reply["expires_in"] == 900
        access = reply["access_token"]
        assert access.startswith("formalie_access_live_")
        status, reply, response = await call(api, "GET", path, token=access)
        assert status == 200 and response.headers["formalie-token-expires"] == "never"
        assert reply["meta"]["token_expires_at"] is None and reply["meta"]["token_expires_in_days"] is None
        assert response.headers["x-ratelimit-limit"] == "600"
        await owner.request("POST", f"/api-tokens/{made['client']['id']}/revoke")
        _, reply, _ = await call(api, "GET", path, token=access)
        assert reply["error"]["code"] == "FRM-API-1010"

        # Switched on, live, method, scope, Formalie-Key
        await owner.request("PATCH", f"/api-services/{made['service']['id']}", body={"status": "disabled"})
        _, reply, _ = await call(api, "GET", path, token=live)
        assert errors(reply) == ("FRM-API-1007", {"service": "switched_off"})
        await owner.request("PATCH", f"/api-services/{made['service']['id']}", body={"status": "active"})
        await owner.request("PATCH", f"/api-endpoints/{made['endpoint']['id']}", body={"status": "disabled"})
        status, reply, _ = await call(api, "GET", path, token=live)
        assert (status, errors(reply)) == (503, ("FRM-API-1007", {"endpoint": "not_live"}))
        status, reply, _ = await call(api, "GET", path, token=test_token)
        assert status == 200 and reply["meta"]["test"] is True and len(reply["data"]) == 1
        await owner.request("PATCH", f"/api-endpoints/{made['endpoint']['id']}", body={"status": "active"})
        status, reply, _ = await call(api, "PATCH", path, token=live)
        assert (status, reply["error"]["code"]) == (405, "FRM-API-1008")
        _, reply, _ = await call(api, "POST", f"{path}/abc", token=live, body={})
        assert reply["error"]["code"] == "FRM-API-1008"
        _, reply = await owner.request("POST", "/api-tokens", body={
            "name": "Read only", "kind": "static", "mode": "live", "expires_at": None,
            "scopes": {"services": [], "endpoints": [], "methods": ["GET"]}})
        read_only = reply["data"]["secrets"]["token"]
        status, reply, _ = await call(api, "POST", path, token=read_only, body={}, headers=key())
        assert (status, errors(reply)) == (403, ("FRM-API-1009", {"method": "not_allowed_for_token"}))
        status, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Ana"})
        assert (status, errors(reply)) == (400, ("FRM-API-1011", {"Formalie-Key": "missing"}))
        _, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Ana"},
                                 headers={"Formalie-Key": "1111111111111111"})
        assert errors(reply) == ("FRM-API-1011", {"Formalie-Key": "weak"})
        _, reply, _ = await call(api, "GET", path, token=live, headers={"Formalie-Key": "short"})
        assert errors(reply) == ("FRM-API-1011", {"Formalie-Key": "short"})

        # Bodies: JSON objects of 1 MB at most; only accepted questions; the form's rules, named by API names
        status, reply, _ = await call(api, "POST", path, token=live, body="[1]", headers=key())
        assert (status, errors(reply)) == (400, ("FRM-GEN-1001", {"body": "Send a JSON object."}))
        status, reply, _ = await call(api, "POST", path, token=live, body="x" * 1_000_001, headers=key())
        assert (status, errors(reply)) == (413, ("FRM-API-1018", {"body": "1 MB"}))
        status, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Ana", "reference": "R1",
                                                                          "nickname": "x"}, headers=key())
        assert (status, errors(reply)) == (422, ("FRM-API-1014", {"nickname": "not_accepted", "reference": "not_accepted"}))
        _, reply, _ = await call(api, "POST", path, token=live, body={"email": "ana@example.org"}, headers=key())
        assert errors(reply) == ("FRM-RESP-1001", {"first_name": "required"})
        _, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Ana", "email": "nope"}, headers=key())
        assert errors(reply) == ("FRM-RESP-1001", {"email": "email"})

        # Browsers: allowed websites only, never *
        status, _, response = await call(api, "OPTIONS", path, headers={"Origin": "https://shop.example.com",
                                                                         "Access-Control-Request-Method": "POST"})
        assert status == 204 and response.headers["access-control-allow-origin"] == "https://shop.example.com"
        assert response.headers["vary"] == "Origin" and response.headers["access-control-max-age"] == "600"
        assert response.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE, OPTIONS"
        assert "Formalie-Key" in response.headers["access-control-allow-headers"]
        status, reply, response = await call(api, "OPTIONS", path, headers={"Origin": "https://evil.example.net"})
        assert (status, errors(reply)) == (403, ("FRM-API-1015", {"origin": "not an allowed website"}))
        assert "access-control-allow-origin" not in response.headers
        _, _, response = await call(api, "GET", path, token=live, headers={"Origin": "https://shop.example.com"})
        assert response.headers["access-control-allow-origin"] == "https://shop.example.com"
        _, _, response = await call(api, "GET", path, token=live, headers={"Origin": "https://evil.example.net"})
        assert "access-control-allow-origin" not in response.headers

        # Every call is in the API log (not the preflights), with the deciding rule; never the token itself
        tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
        rows = superuser.execute("SELECT method, status, code, rule_id, request_headers FROM formaly.api_request_logs "
                                 "WHERE tenant_id = %s ORDER BY at", (tenant_id,)).fetchall()
        assert all(r[0] != "OPTIONS" for r in rows) and len(rows) >= 20
        assert any(r[2] == "FRM-API-1015" and str(r[3]) == str(real(rule["id"])) for r in rows)
        assert not any(live in json.dumps(r[4]) for r in rows)


async def test_rate_limits_signing_and_cross_tenant(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, client_for(app, host=API) as api, \
            client_for(app, host=f"{other_sub}.formalie.dev") as other_http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
        other = SecureClient(other_http)
        await sign_in(other, other_email, PASSWORD)
        theirs = await setup(other)
        path, live = made["path"], made["live_secret"]

        # A token or address of one workspace never reaches another's data
        _, reply, _ = await call(api, "GET", theirs["path"], token=live)
        assert reply["error"]["code"] == "FRM-API-1010"
        _, reply, _ = await call(api, "GET", f"/{theirs['api_key']}/{made['endpoint']['name']}", token=live)
        assert errors(reply) == ("FRM-API-1006", {"endpoint": "unknown"})
        status, reply, _ = await call(api, "POST", theirs["path"], token=theirs["live_secret"],
                                      body={"first_name": "Lin"}, headers=key())
        assert status == 201
        their_record = reply["data"]["id"]
        _, reply, _ = await call(api, "POST", theirs["path"], token=theirs["live_secret"], body={"first_name": "Lin"},
                                 headers=key())
        assert errors(reply) == ("FRM-RESP-1005", {"body": "same_answers"})
        _, reply, _ = await call(api, "GET", f"{path}/{their_record}", token=live)
        assert reply["error"]["code"] == "FRM-API-1013"
        _, reply, _ = await call(api, "GET", f"{path}/{real(their_record)}", token=live)
        assert reply["error"]["code"] == "FRM-API-1013"  # a raw id is never accepted
        _, reply, _ = await call(api, "POST", f"/{theirs['api_key']}/token", body={
            "client_id": theirs["client"]["client_id"], "client_secret": theirs["client_secret"]})
        their_access = reply["access_token"]
        assert (await call(api, "GET", theirs["path"], token=their_access))[0] == 200
        _, reply, _ = await call(api, "GET", path, token=their_access)
        assert reply["error"]["code"] == "FRM-API-1010"
        _, reply, _ = await call(api, "POST", f"/{made['api_key']}/token", body={
            "client_id": theirs["client"]["client_id"], "client_secret": theirs["client_secret"]})
        assert reply["error"]["code"] == "FRM-API-1010"

        # Rate limits: per token, with Retry-After and the X-RateLimit headers
        _, reply = await owner.request("POST", "/api-tokens", body={
            "name": "Limited", "kind": "static", "mode": "live", "expires_at": None,
            "scopes": {"services": [], "endpoints": [], "methods": []}})
        limited = reply["data"]["secrets"]["token"]
        await owner.request("PUT", "/api-service/limits", body={"per_token": 3, "per_ip": 100, "per_endpoint": 100})
        for left in ("2", "1", "0"):
            status, _, response = await call(api, "GET", path, token=limited)
            assert status == 200 and response.headers["x-ratelimit-remaining"] == left
        status, reply, response = await call(api, "GET", path, token=limited)
        assert (status, errors(reply)) == (429, ("FRM-GEN-1029", {"token": "limit 3 per minute"}))
        assert 1 <= int(response.headers["retry-after"]) <= 60 and response.headers["x-ratelimit-remaining"] == "0"
        assert int(response.headers["x-ratelimit-reset"]) >= int(time.time())
        await owner.request("PUT", "/api-service/limits", body={"per_token": None, "per_ip": 2, "per_endpoint": None})
        async with client_for(app, host=API, peer="198.51.100.20") as fresh:
            assert (await call(fresh, "GET", path))[1]["error"]["code"] == "FRM-API-1010"
            assert (await call(fresh, "GET", path))[1]["error"]["code"] == "FRM-API-1010"
            assert errors((await call(fresh, "GET", path))[1]) == ("FRM-GEN-1029", {"ip": "limit 2 per minute"})
        _, reply = await owner.request("GET", "/api-logs/insights")
        assert reply["success"]
        tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
        assert superuser.execute("SELECT count(*) FROM formaly.api_request_logs WHERE tenant_id = %s AND rate_limited",
                                 (tenant_id,)).fetchone()[0] == 2
        await owner.request("PUT", "/api-service/limits", body={"per_token": None, "per_ip": None, "per_endpoint": None})

        # Signed calls: only for a token with signing on (none can switch it on in the portal since 2026-10-06)
        secret = "formalie_sign_live_" + "k" * 40
        superuser.execute("UPDATE formaly.api_tokens SET signing = true, signing_secret_enc = %s WHERE id = %s",
                          (encrypt_secret(secret), real(made["live"]["id"])))
        _, reply, _ = await call(api, "GET", path, token=live)
        assert errors(reply) == ("FRM-API-1012", {"X-Formalie-Signature": "missing"})

        def signed(stamp: int, body: bytes = b"", method: str = "GET") -> dict[str, str]:
            mac = hmac.new(secret.encode(), f"{stamp}.{method}.{path}.".encode() + body, hashlib.sha256).hexdigest()
            return {"X-Formalie-Timestamp": str(stamp), "X-Formalie-Signature": f"sha256={mac}"}
        now = int(time.time())
        status, _, _ = await call(api, "GET", path, token=live, headers=signed(now))
        assert status == 200
        _, reply, _ = await call(api, "GET", path, token=live, headers=signed(now))
        assert errors(reply) == ("FRM-API-1012", {"X-Formalie-Signature": "replayed"})
        _, reply, _ = await call(api, "GET", path, token=live, headers=signed(now - 301))
        assert errors(reply) == ("FRM-API-1012", {"X-Formalie-Timestamp": "too_old"})
        _, reply, _ = await call(api, "GET", path, token=live, headers={**signed(now + 1), "X-Formalie-Timestamp": str(now + 2)})
        assert errors(reply) == ("FRM-API-1012", {"X-Formalie-Signature": "wrong"})
        body = json.dumps({"first_name": "Signed"}).encode()
        status, reply, _ = await call(api, "POST", path, token=live, body=body,
                                      headers={**signed(now + 3, body, "POST"), **key()})
        assert status == 201, reply


async def test_records_test_tokens_replays_files_and_try(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, client_for(app, host=API) as api:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner, build=cv_form)
        path, live, test_token = made["path"], made["live_secret"], made["test_secret"]
        form_id = real(made["form"]["id"])
        count = "SELECT count(*) FROM formaly.responses WHERE form_id = %s AND deleted_at IS NULL"

        # Test tokens: checked and answered, nothing stored
        status, reply, _ = await call(api, "POST", path, token=test_token, body={"first_name": "Test"}, headers=key())
        assert status == 201 and reply["meta"]["test"] is True and reply["data"]["data"]["first_name"] == "Test"
        _, reply, _ = await call(api, "POST", path, token=test_token, body={}, headers=key())
        assert errors(reply) == ("FRM-RESP-1001", {"first_name": "required"})
        _, reply, _ = await call(api, "PUT", f"{path}/anything", token=test_token, body={"first_name": "T"})
        assert reply["meta"]["test"] is True
        _, reply, _ = await call(api, "DELETE", f"{path}/anything", token=test_token)
        assert reply["data"] == {"id": "anything", "deleted": True} and reply["meta"]["test"] is True
        status, reply, _ = await call(api, "POST", f"{path}/files", token=test_token, params={"field": "cv"},
                                      files={"file": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")}, headers=key())
        assert status == 201 and reply["meta"]["test"] is True and reply["data"]["name"] == "cv.pdf"
        assert superuser.execute(count, (form_id,)).fetchone()[0] == 0
        assert superuser.execute("SELECT count(*) FROM formaly.uploads WHERE form_id = %s", (form_id,)).fetchone()[0] == 0

        # Files, then a real POST with the file's id
        _, reply, _ = await call(api, "POST", f"{path}/files", token=live, params={"field": "email"},
                                 files={"file": ("cv.pdf", b"%PDF", "application/pdf")}, headers=key())
        assert errors(reply) == ("FRM-API-1014", {"email": "not_accepted"})
        _, reply, _ = await call(api, "POST", f"{path}/files", token=live, params={"field": "cv"},
                                 files={"file": ("cv.exe", b"MZ...", "application/octet-stream")}, headers=key())
        assert errors(reply) == ("FRM-RESP-1001", {"cv": "file_type"})
        _, reply, _ = await call(api, "POST", f"{path}/files", token=live, params={"field": "cv"}, body={}, headers=key())
        assert reply["error"]["code"] == "FRM-GEN-1001"
        status, reply, _ = await call(api, "POST", f"{path}/files", token=live, params={"field": "cv"},
                                      files={"file": ("cv.pdf", b"%PDF-1.4 real", "application/pdf")}, headers=key())
        assert status == 201, reply
        file_ref = reply["data"]["id"]
        assert reply["data"]["size"] == len(b"%PDF-1.4 real") and real(file_ref)

        call_key = key()
        sent = {"first_name": "Ana", "email": "ana@example.org", "cv": [file_ref]}
        status, reply, response = await call(api, "POST", path, token=live, body=sent, headers=call_key)
        assert status == 201, reply
        record = reply["data"]
        assert record["status"] == "new" and record["data"]["first_name"] == "Ana"
        assert record["data"]["cv"][0]["id"] == file_ref and record["data"]["reference"] is None
        assert response.headers["formalie-token-expires"] == "never"
        assert superuser.execute(count, (form_id,)).fetchone()[0] == 1
        row = superuser.execute("SELECT channel, api_token_id FROM formaly.responses WHERE id = %s",
                                (real(record["id"]),)).fetchone()
        assert row == ("api", real(made["live"]["id"]))
        assert superuser.execute("SELECT response_id FROM formaly.uploads WHERE id = %s",
                                 (real(file_ref),)).fetchone()[0] == real(record["id"])

        # The same key and body: the first record again; another body: refused; the same email with a new key: refused
        status, reply, _ = await call(api, "POST", path, token=live, body=sent, headers=call_key)
        assert status == 200 and reply["data"]["id"] == record["id"] and reply["meta"]["replayed"] is True
        _, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Bo"}, headers=call_key)
        assert errors(reply) == ("FRM-API-1020", {"Formalie-Key": "used_for_another_body"})
        _, reply, _ = await call(api, "POST", path, token=live, body={"first_name": "Ana", "email": "ana@example.org"},
                                 headers=key())
        assert reply["error"]["code"] == "FRM-RESP-1006"
        detail = reply["error"]["details"][0]
        assert detail["field"] == "email" and detail["message"] == "already_submitted"
        assert detail["submitted_at"] == record["submitted_at"] and detail["email"] != "ana@example.org"
        # Keys answer for 24 hours, then Beat retires them
        from app.modules.api_service.tasks import expire_call_keys

        superuser.execute("UPDATE formaly.api_idempotency SET at = now() - interval '25 hours' WHERE formalie_key = %s",
                          (call_key["Formalie-Key"],))
        assert await expire_call_keys() >= 1
        assert superuser.execute("SELECT deleted_at IS NOT NULL FROM formaly.api_idempotency WHERE formalie_key = %s",
                                 (call_key["Formalie-Key"],)).fetchone()[0] is True
        assert superuser.execute(count, (form_id,)).fetchone()[0] == 1

        # In the portal: the responses list (channel api), the API log as the token, the audit trail as the token
        _, reply = await owner.request("GET", f"/forms/{made['form']['id']}/responses")
        assert [(r["channel"], r["id"]) for r in reply["data"]] == [("api", record["id"])]
        _, reply = await owner.request("GET", "/api-logs", query={"filter[mode]": "live"})
        assert any(r["status"] == 201 and r["token"]["name"] == "live token" and r["method"] == "POST" for r in reply["data"])
        audit = superuser.execute("SELECT actor_type, actor_name FROM formaly.audit_logs WHERE tenant_id = "
                                  "(SELECT tenant_id FROM formaly.forms WHERE id = %s) AND action = 'responses.submitted'",
                                  (form_id,)).fetchall()
        assert audit == [("api_key", "API: live token")]

        # GET one and the list (filters by API name, choices as labels)
        _, reply, _ = await call(api, "GET", f"{path}/{record['id']}", token=live)
        assert reply["data"]["id"] == record["id"]
        _, reply, _ = await call(api, "GET", path, token=live, params={"email": "nobody@example.org"})
        assert reply["data"] == [] and reply["meta"]["total"] == 0
        _, reply, _ = await call(api, "GET", path, token=live, params={"email": "ana@example.org", "per_page": "500"})
        assert reply["meta"] == {"page": 1, "per_page": 50, "total": 1, "total_pages": 1,
                                 "token_expires_at": None, "token_expires_in_days": None}

        # PUT changes the answers sent (checked like an edit); DELETE removes it
        _, reply, _ = await call(api, "PUT", f"{path}/{record['id']}", token=live, body={"email": "nope"})
        assert errors(reply) == ("FRM-RESP-1001", {"email": "email"})
        status, reply, _ = await call(api, "PUT", f"{path}/{record['id']}", token=live, body={"first_name": "Ana Maria"})
        assert status == 200 and reply["data"]["data"]["first_name"] == "Ana Maria"
        _, reply = await owner.request("GET", f"/responses/{record['id']}")
        assert reply["data"]["data"]["first_name"] == "Ana Maria" and reply["data"]["edited"] is True
        assert reply["data"]["history"][0]["by"]["name"] == "API: live token"
        status, reply, _ = await call(api, "DELETE", f"{path}/{record['id']}", token=live)
        assert status == 200 and reply["data"] == {"id": record["id"], "deleted": True}
        _, reply, _ = await call(api, "GET", f"{path}/{record['id']}", token=live)
        assert reply["error"]["code"] == "FRM-API-1013"
        assert superuser.execute(count, (form_id,)).fetchone()[0] == 0
        actions = {r[0] for r in superuser.execute(
            "SELECT action FROM formaly.audit_logs WHERE actor_type = 'api_key' AND tenant_id = "
            "(SELECT tenant_id FROM formaly.forms WHERE id = %s)", (form_id,)).fetchall()}
        assert actions == {"responses.submitted", "responses.updated", "responses.deleted"}

        # Try it: a real call through the gateway with the console's test token (nothing stored)
        status, reply = await owner.request("POST", f"/api-endpoints/{made['endpoint']['id']}/try", body={
            "method": "POST", "body": {"first_name": "Console"}})
        assert status == 200, reply
        result = reply["data"]
        assert result["status"] == 201 and result["body"]["meta"]["test"] is True
        assert "formalie-token-expires" not in result["headers"] and result["headers"]["content-type"].startswith("application/json")
        _, reply = await owner.request("POST", f"/api-endpoints/{made['endpoint']['id']}/try", body={"method": "GET"})
        assert reply["data"]["status"] == 200 and reply["data"]["body"]["meta"]["test"] is True
        assert superuser.execute(count, (form_id,)).fetchone()[0] == 0
        _, reply = await owner.request("GET", "/api-logs", query={"filter[mode]": "test"})
        assert any(r["token"]["name"] == "Docs console" for r in reply["data"])
        _, reply = await owner.request("POST", f"/api-endpoints/{made['service']['id']}/try", body={"method": "GET"})
        assert reply["error"]["code"] == "FRM-GEN-1004"


async def test_gateway_runs_as_its_own_app(app, db_settings, superuser) -> None:  # noqa: ANN001, F811
    from app.gateway import create_gateway_app

    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
    shipper = MemoryShipper()
    gateway = create_gateway_app(db_settings, request_log_shipper=shipper, configure=False)
    async with client_for(gateway, host="api.formalie.dev:5005") as api:
        status, reply, response = await call(api, "POST", made["path"], token=made["live_secret"],
                                             body={"first_name": "Own app"}, headers=key())
        assert status == 201, reply
        assert response.headers["strict-transport-security"].startswith("max-age=")
        assert response.headers["cache-control"] == "no-store" and response.headers["x-trace-id"]
    record = shipper.records[-1]
    assert record["status"] == 201 and record["request_body"] is None and record["response_body"] is None
    assert record["request_headers"]["authorization"] != f"Bearer {made['live_secret']}"

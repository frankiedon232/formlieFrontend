"""The request pipeline end to end (no DB): context, headers, errors, rate limit, tenant and envelope gate."""

from __future__ import annotations

import base64
import json

import fakeredis
import pytest
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import FrmError
from app.core.middleware.envelope import ENVELOPE_CONTENT_TYPE, ENVELOPE_HEADER
from tests.conftest import build_app, client_for


def _b64(n: int) -> str:
    return base64.b64encode(b"\x01" * n).decode()


def _envelope(kid: str = "0190f0b2-0000-7000-8000-000000000001") -> dict[str, object]:
    return {"kid": kid, "iv": _b64(12), "ts": 1790000000000, "nonce": _b64(16), "ct": _b64(48)}


def _header(env: dict[str, object]) -> str:
    return base64.urlsafe_b64encode(json.dumps(env).encode()).decode().rstrip("=")


# ── Context, headers, health ──────────────────────────────────────────────────

async def test_health_is_plaintext_and_matches_the_mock_shape(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True and body["meta"] == {}
    assert body["data"]["status"] == "ok" and body["data"]["mock"] is False
    assert body["data"]["time"].endswith("Z")


async def test_every_response_has_a_trace_id_and_security_headers(client) -> None:
    response = await client.get("/api/v1/health")
    trace = response.headers["x-trace-id"]
    assert len(trace) == 36 and trace[14] == "7"  # UUIDv7
    assert "max-age=" in response.headers["strict-transport-security"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


async def test_error_bodies_carry_the_trace_id(client) -> None:
    response = await client.get("/api/v1/forms")
    assert response.json()["error"]["trace_id"] == response.headers["x-trace-id"]


# ── Errors ─────────────────────────────────────────────────────────────────────

class Payload(BaseModel):
    name: str
    count: int


def _app_with_routes(settings: Settings) -> FastAPI:
    app = build_app(settings)
    router = APIRouter()

    @router.post("/boom/validate")
    async def validate(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    @router.get("/boom/frm")
    async def frm() -> None:
        raise FrmError("FRM-GEN-1009", [{"field": "row_version", "message": "3"}])

    @router.get("/boom/crash")
    async def crash() -> None:
        raise RuntimeError("password=hunter2 in an internal message")

    app.include_router(router, prefix="/internal")  # /internal/* is outside /api: no envelope, no tenant
    return app


@pytest.fixture
async def boom(settings, redis):
    async with client_for(_app_with_routes(settings)) as c:
        yield c


async def test_frm_error_shape(boom) -> None:
    response = await boom.get("/internal/boom/frm")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "FRM-GEN-1009"
    assert error["message"] == "This item was changed by someone else. Reload and try again."
    assert error["details"] == [{"field": "row_version", "message": "3"}]
    assert response.json()["success"] is False


async def test_validation_errors_become_frm_gen_1002_with_fields(boom) -> None:
    response = await boom.post("/internal/boom/validate", json={"name": "x"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "FRM-GEN-1002"
    assert [d["field"] for d in error["details"]] == ["count"]


async def test_unhandled_errors_never_leak_internals(boom) -> None:
    response = await boom.get("/internal/boom/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "FRM-GEN-5000"
    assert "hunter2" not in response.text


async def test_unknown_route_outside_api_is_frm_404(client) -> None:
    response = await client.get("/nothing-here")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FRM-GEN-1004"


# ── Rate limit ─────────────────────────────────────────────────────────────────

async def test_ip_rate_limit_answers_429_with_retry_after(settings, redis) -> None:
    app = build_app(settings, rate_limit_ip_per_minute=3)
    async with client_for(app) as c:
        statuses = [(await c.get("/api/v1/health")).status_code for _ in range(4)]
        assert statuses == [200, 200, 200, 429]
        last = await c.get("/api/v1/health")
        assert last.json()["error"]["code"] == "FRM-GEN-1029"
        assert int(last.headers["retry-after"]) >= 1
    async with client_for(app, peer="198.51.100.9") as other:  # another IP has its own window
        assert (await other.get("/api/v1/health")).status_code == 200


async def test_rate_limit_fails_open_or_closed_when_redis_is_down(settings, redis) -> None:
    from app.core.cache.redis import set_redis

    class Down(fakeredis.FakeAsyncRedis):
        def pipeline(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError("down")

    set_redis(Down(decode_responses=True))
    async with client_for(build_app(settings, rate_limit_fail_open=True)) as c:
        assert (await c.get("/api/v1/health")).status_code == 200
    async with client_for(build_app(settings, rate_limit_fail_open=False)) as c:
        response = await c.get("/api/v1/health")
        assert response.status_code == 503 and response.json()["error"]["code"] == "FRM-GEN-5003"


# ── Forwarded headers ──────────────────────────────────────────────────────────

async def test_forwarded_headers_are_ignored_from_untrusted_peers(settings, redis) -> None:
    app = build_app(settings, rate_limit_ip_per_minute=1)
    async with client_for(app, peer="203.0.113.50") as c:
        assert (await c.get("/api/v1/health", headers={"x-forwarded-for": "1.1.1.1"})).status_code == 200
        # Spoofing another address does not get a fresh window.
        assert (await c.get("/api/v1/health", headers={"x-forwarded-for": "2.2.2.2"})).status_code == 429
        # Nor does a forged host pick a workspace.
        response = await c.get("/api/v1/forms", headers={"x-forwarded-host": "acme.formalie.dev"})
        assert response.status_code == 429


async def test_forwarded_headers_are_used_from_the_trusted_proxy(settings, redis) -> None:
    app = build_app(settings, rate_limit_ip_per_minute=1)
    async with client_for(app, host="formalie.dev", peer="127.0.0.1") as proxy:
        a = await proxy.get("/api/v1/health", headers={"x-forwarded-for": "1.1.1.1"})
        b = await proxy.get("/api/v1/health", headers={"x-forwarded-for": "2.2.2.2"})
        assert (a.status_code, b.status_code) == (200, 200)
        response = await proxy.get("/api/v1/forms", headers={"x-forwarded-for": "3.3.3.3",
                                                            "x-forwarded-host": "nobody.formalie.dev"})
        assert response.json()["error"]["code"] == "FRM-TEN-1001"


# ── Tenant ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("host", ["nobody.formalie.dev", "a.b.formalie.dev", "shop.example.com"])
async def test_unknown_or_invalid_workspace_hosts_are_frm_ten_1001(app, host: str) -> None:
    async with client_for(app, host=host) as c:
        response = await c.get("/api/v1/forms")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FRM-TEN-1001"
        assert (await c.get("/api/v1/health")).status_code == 200  # health answers on any host


@pytest.mark.parametrize("host", ["api.formalie.dev", "API.formalie.dev:5004"])
async def test_the_api_host_is_the_public_api_service(app, host: str) -> None:
    """api.<root> goes to the API service's own app (app/gateway.py): no envelope, its own error shape."""
    async with client_for(app, host=host) as c:
        response = await c.get("/api/v1/forms")
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "FRM-API-1006", "message": "There is no endpoint at this address.",
                                              "details": [{"field": "address_key", "message": "unknown"}]}}
        assert response.headers["cache-control"] == "no-store" and response.headers["x-trace-id"]
    async with client_for(app, host="formalie.dev", peer="127.0.0.1") as proxy:  # the dev proxy's X-Forwarded-Host
        response = await proxy.get("/x/y", headers={"x-forwarded-host": "api.formalie.dev"})
        assert response.json()["error"]["code"] == "FRM-API-1006"


@pytest.mark.parametrize("host", ["acme.formalie.dev", "oldco.formalie.dev", "manage.formalie.dev",
                                  "forms.formalie.dev", "localhost:5004"])
async def test_known_workspaces_and_formalie_hosts_reach_the_envelope_gate(app, host: str) -> None:
    async with client_for(app, host=host) as c:
        response = await c.get("/api/v1/forms")
        assert response.json()["error"]["code"] == "FRM-SEC-1001"  # past the tenant layer


async def test_dev_tenant_override_header_only_on_local_hosts(app) -> None:
    async with client_for(app, host="localhost:5004") as c:
        response = await c.get("/api/v1/forms", headers={"x-formalie-dev-tenant": "nobody"})
        assert response.json()["error"]["code"] == "FRM-TEN-1001"
    async with client_for(app, host="manage.formalie.dev") as c:
        response = await c.get("/api/v1/forms", headers={"x-formalie-dev-tenant": "nobody"})
        assert response.json()["error"]["code"] == "FRM-SEC-1001"  # ignored on a real host


async def test_dev_tenant_override_is_off_in_production(settings, redis) -> None:
    app = build_app(settings, app_env="production")
    async with client_for(app, host="localhost") as c:
        response = await c.get("/api/v1/forms", headers={"x-formalie-dev-tenant": "nobody"})
        assert response.json()["error"]["code"] == "FRM-SEC-1001"


def test_require_tenant_refuses_suspended_and_missing() -> None:
    import time

    from app.core.context import RequestContext, reset_context, set_context
    from app.core.middleware.tenant import require_tenant
    from tests.conftest import ACME, OLDCO

    for tenant, expected in ((None, "FRM-TEN-1001"), (OLDCO, "FRM-TEN-1002"), (ACME, None)):
        token = set_context(RequestContext(trace_id="t", started_at=time.perf_counter(), tenant=tenant))
        try:
            if expected is None:
                assert require_tenant() is ACME
            else:
                with pytest.raises(FrmError) as caught:
                    require_tenant()
                assert caught.value.code == expected
        finally:
            reset_context(token)


# ── Envelope gate ──────────────────────────────────────────────────────────────

async def test_plain_requests_need_the_secure_channel(client) -> None:
    for method in ("get", "delete"):
        response = await getattr(client, method)("/api/v1/forms")
        assert (response.status_code, response.json()["error"]["code"]) == (400, "FRM-SEC-1001")
    response = await client.post("/api/v1/forms", json={"name": "plain"})
    assert response.json()["error"]["code"] == "FRM-SEC-1001"


async def test_malformed_envelopes_are_refused(client) -> None:
    bad = _envelope()
    bad["iv"] = _b64(8)
    for value in (_header(bad), "%%%not-base64", _header({"kid": "x"})):
        response = await client.get("/api/v1/forms", headers={ENVELOPE_HEADER: value})
        assert response.json()["error"]["code"] == "FRM-SEC-1001"
    response = await client.post("/api/v1/forms", content=b"{not json", headers={"content-type": ENVELOPE_CONTENT_TYPE})
    assert response.json()["error"]["code"] == "FRM-SEC-1001"


async def test_unknown_session_key_asks_for_a_new_handshake(client) -> None:
    response = await client.get("/api/v1/forms", headers={ENVELOPE_HEADER: _header(_envelope())})
    assert (response.status_code, response.json()["error"]["code"]) == (401, "FRM-SEC-1004")
    response = await client.post("/api/v1/forms", content=json.dumps(_envelope()),
                                 headers={"content-type": ENVELOPE_CONTENT_TYPE})
    assert response.json()["error"]["code"] == "FRM-SEC-1004"


@pytest.mark.parametrize("path", [
    "/api/v1/crypto/handshake", "/api/v1/auth/oauth/google/start", "/api/v1/auth/oauth/google/callback",
    "/api/v1/auth/sso/start",
    "/api/v1/downloads/tok", "/api/v1/response-exports/tok", "/api/v1/response-files/tok",
    "/api/v1/datasource-exports/tok", "/api/v1/billing/webhooks/payoneer", "/api/v1/internal/public-forms/abc",
])
async def test_documented_plaintext_exceptions_pass_the_gate(client, path: str) -> None:
    response = await client.get(path)
    if response.status_code in (301, 302, 303, 307):  # a browser redirect (OAuth start)
        return
    if response.headers.get("content-type", "").startswith("text/plain"):  # a download link's plain answer
        return
    assert response.json()["error"]["code"] != "FRM-SEC-1001"  # reaches routing (404 until the route exists)

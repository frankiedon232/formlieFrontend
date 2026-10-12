"""Edge trust (2026-10-12): the Worker in front of every portal host proxies /api/* to the services host with
X-Formalie-Edge. The right secret makes the forwarded host, scheme and visitor address count; a wrong or missing
one is ignored like an untrusted peer; the secret is never logged; the services host has no workspace; the edge
routes look absent without the secret; a closed workspace is refused like a suspended one."""

from __future__ import annotations

import json
import logging
import uuid

import pytest
from pydantic import SecretStr

from app.core.context import RequestContext, TenantInfo, reset_context, set_context
from app.core.errors import FrmError
from app.core.middleware.request_context import TrustedProxies
from app.core.middleware.tenant import require_tenant
from app.modules.logs.capture import mask_headers
from tests.conftest import MemoryShipper, build_app, client_for

EDGE = "edge-secret-for-tests-0123456789abcdef"
VISITOR = "198.51.100.23"


@pytest.fixture
def shipper() -> MemoryShipper:
    return MemoryShipper()


@pytest.fixture
def edge_app(settings, redis, shipper):  # noqa: ANN001
    return build_app(settings, shipper, edge_secret=SecretStr(EDGE))


def through_edge(secret: str | None, host: str = "acme.formalie.dev") -> dict[str, str]:
    headers = {"x-forwarded-host": host, "x-forwarded-proto": "https", "x-forwarded-for": VISITOR}
    if secret is not None:
        headers["x-formalie-edge"] = secret
    return headers


async def test_the_right_secret_makes_the_forwarded_host_decide_the_workspace(edge_app, shipper) -> None:  # noqa: ANN001
    async with client_for(edge_app, host="services.formalie.dev", peer="127.0.0.1") as http:
        await http.get("/api/v1/forms", headers=through_edge(EDGE))
        await http.get("/api/v1/forms", headers=through_edge(EDGE, host="nosuch.formalie.dev"))
    acme, unknown = shipper.records
    assert acme["host"] == "acme.formalie.dev" and acme["subdomain"] == "acme" and acme["tenant_id"] is not None
    assert acme["client_ip"] == VISITOR and acme["peer_ip"] == "127.0.0.1" and acme["scheme"] == "https"
    assert unknown["status"] == 404 and unknown["error_code"] == "FRM-TEN-1001"


@pytest.mark.parametrize("secret", [None, "", "wrong", EDGE[:-1], EDGE + "x"])
async def test_a_wrong_or_missing_secret_is_ignored(edge_app, shipper, secret) -> None:  # noqa: ANN001
    # From an untrusted peer and from a trusted one (Nginx passes the headers through): the forwarded host never counts
    for peer in ("203.0.113.7", "127.0.0.1"):
        async with client_for(edge_app, host="services.formalie.dev", peer=peer) as http:
            response = await http.get("/api/v1/forms", headers=through_edge(secret))
        record = shipper.records[-1]
        assert record["host"] == "services.formalie.dev" and record["tenant_id"] is None
        assert record["host_kind"] == "manage" and response.json().get("error", {}).get("code") != "FRM-TEN-1001"
    assert shipper.records[0]["client_ip"] == "203.0.113.7"


async def test_without_an_edge_secret_trusted_proxies_work_as_before(settings, redis, shipper) -> None:  # noqa: ANN001
    app = build_app(settings, shipper)
    async with client_for(app, host="services.formalie.dev", peer="127.0.0.1") as http:
        await http.get("/api/v1/forms", headers=through_edge(EDGE))  # the header means nothing when it is off
    assert shipper.records[0]["host"] == "acme.formalie.dev" and shipper.records[0]["tenant_id"] is not None
    proxies = TrustedProxies(["127.0.0.1/32"], "")
    scope = {"type": "http", "headers": [(b"x-formalie-edge", b""), (b"x-forwarded-host", b"acme.formalie.dev")]}
    assert proxies.edge(scope) is False and proxies.host("203.0.113.7", scope) is None


async def test_the_secret_is_never_logged(edge_app, shipper, caplog) -> None:  # noqa: ANN001
    caplog.set_level(logging.DEBUG)
    async with client_for(edge_app, host="services.formalie.dev", peer="127.0.0.1") as http:
        response = await http.get("/api/v1/health", headers=through_edge(EDGE))
        await http.get("/api/v1/forms", headers=through_edge(EDGE + "-wrong"))
    assert EDGE not in json.dumps(dict(response.headers)) and EDGE not in response.text
    for record in shipper.records:
        assert "x-formalie-edge" not in record["request_headers"]
        assert EDGE not in json.dumps(record, default=str)
    assert EDGE not in caplog.text
    assert "x-formalie-edge" not in mask_headers([(b"X-Formalie-Edge", EDGE.encode()), (b"host", b"a")])


async def test_the_services_host_has_no_workspace(edge_app, shipper) -> None:  # noqa: ANN001
    async with client_for(edge_app, host="services.formalie.dev") as http:
        health = await http.get("/api/v1/health")
        other = await http.get("/api/v1/forms")
    assert health.status_code == 200
    assert other.json()["error"]["code"] != "FRM-TEN-1001"
    assert [r["host_kind"] for r in shipper.records] == ["manage", "manage"]


@pytest.mark.parametrize("path", ["/api/v1/edge/forms/AbCdEfGhJk/preview", "/api/v1/edge/links/abcde"])
@pytest.mark.parametrize("secret", [None, "wrong"])
async def test_edge_routes_look_absent_without_the_secret(edge_app, path, secret) -> None:  # noqa: ANN001
    async with client_for(edge_app, host="services.formalie.dev", peer="127.0.0.1") as http:
        response = await http.get(path, headers=through_edge(secret))
        missing = await http.get("/api/v1/edge/nothing-here", headers=through_edge(secret))
    assert response.status_code == missing.status_code == 404
    assert response.json()["error"]["code"] == missing.json()["error"]["code"] == "FRM-GEN-1004"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("status, details", [("suspended", None), ("closed", [{"field": "workspace", "message": "closed"}])])
def test_closed_workspaces_are_refused_like_suspended_ones(status, details) -> None:  # noqa: ANN001
    tenant = TenantInfo(id=uuid.uuid4(), subdomain="gone", name="Gone", status=status, organisation_id=uuid.uuid4())
    token = set_context(RequestContext(trace_id="t", started_at=0.0, tenant=tenant))
    try:
        with pytest.raises(FrmError) as refused:
            require_tenant()
    finally:
        reset_context(token)
    assert refused.value.code == "FRM-TEN-1002" and (refused.value.details or None) == details

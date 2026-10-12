"""Edge routes for the Worker (2026-10-12) and closing workspaces (B16 leftover), against the test database.

The preview answers on the forwarded host for a published public form and is absent for an unknown or private
one; the short link answers with where it leads; both are absent without the secret. A closing workspace past its
date becomes closed (nothing deleted), refuses sign-in and stops taking answers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from app.modules.links.urls import frame_ancestors
from app.modules.platform_bridge.closing import close_due
from tests.conftest import MemoryShipper, client_for
from tests.db.test_auth_flows import seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_builder import with_field
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

EDGE = "edge-secret-for-db-tests-0123456789"


@pytest.fixture
def app(db_settings, engines, seeded, redis):  # noqa: ANN001, F811
    from app.modules.tenants.service import TenantDirectory
    from app.run import create_app

    return create_app(db_settings.model_copy(update={"rate_limit_ip_per_minute": 10_000,
                                                      "edge_secret": SecretStr(EDGE)}),
                      tenant_resolver=TenantDirectory(), request_log_shipper=MemoryShipper())


def edge(host: str, secret: str | None = EDGE) -> dict[str, str]:
    headers = {"x-forwarded-host": host, "x-forwarded-proto": "https", "x-forwarded-for": "198.51.100.40"}
    if secret is not None:
        headers["x-formalie-edge"] = secret
    return headers


def question(schema: dict) -> dict:
    return with_field(schema, "full_name", "Full name", required=True)


async def test_form_preview_and_short_link_through_the_edge(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Volunteer sign-up", question)
        private = await publish(owner, "Staff survey", question)
        status, reply = await owner.request("PUT", f"/forms/{private['id']}/share", body={"access": "organisation"})
        assert status == 200, reply
        _, reply = await owner.request("POST", "/forms", body={"name": "Never published"})
        draft = reply["data"]
        _, reply = await owner.request("POST", f"/forms/{form['id']}/short-link", body={})
        code = reply["data"]["short_link"]["code"]
    key = form["public_key"]

    async with client_for(app, host="services.formalie.dev", peer="127.0.0.1") as http:
        # Published and public: the link preview, on the workspace host and on the shared forms host
        for host in (f"{sub}.formalie.com", f"{sub}.formalie.dev", "forms.formalie.dev"):
            response = await http.get(f"/api/v1/edge/forms/{key}/preview", headers=edge(host))
            if host.endswith(".com"):  # another domain: not a Formalie host, so not this workspace
                assert response.status_code == 404
                continue
            assert response.status_code == 200, response.text
            assert response.json() == {"title": "Volunteer sign-up", "description": None, "image_url": None,
                                       "language": "en", "indexable": True, "site_name": "Settings Co",
                                       "embed_ancestors": "*"}
            assert response.headers["cache-control"] == "public, max-age=60"
            assert EDGE not in response.text and "x-formalie-edge" not in response.headers

        # Websites allowed to embed the form: the embed page's frame-ancestors, as the public form gives them
        async with client_for(app, host=f"{sub}.formalie.dev") as owner_http:
            owner = SecureClient(owner_http)
            await sign_in(owner, email, PASSWORD)
            status, reply = await owner.request("PUT", f"/forms/{form['id']}/share",
                                                body={"embed_domains": ["example.com", "localhost:3000"]})
            assert status == 200, reply
            _, page = await SecureClient(owner_http).request("GET", f"/public/forms/{key}")
        response = await http.get(f"/api/v1/edge/forms/{key}/preview", headers=edge(f"{sub}.formalie.dev"))
        ancestors = response.json()["embed_ancestors"]
        assert ancestors == page["data"]["embed_ancestors"] == frame_ancestors(["example.com", "localhost:3000"],
                                                                                  "formalie.dev")
        assert "https://example.com" in ancestors and "http://localhost:3000" in ancestors

        # Unknown, private (members only) and never published forms look absent
        for missing in ("AbCdEfGhJk", private["public_key"], draft["public_key"]):
            response = await http.get(f"/api/v1/edge/forms/{missing}/preview", headers=edge(f"{sub}.formalie.dev"))
            assert response.status_code == 404 and response.json() == {"error": {"code": "FRM-FORM-1001"}}

        # Another workspace's host does not show this workspace's form
        other, _ = await new_workspace(app)
        response = await http.get(f"/api/v1/edge/forms/{key}/preview", headers=edge(f"{other}.formalie.dev"))
        assert response.status_code == 404

        # Short link: hit and miss
        response = await http.get(f"/api/v1/edge/links/{code}", headers=edge("forms.formalie.dev"))
        assert response.status_code == 200
        location = response.json()["location"]
        assert location.startswith(f"https://{sub}.formalie.dev") and location.endswith(f"/{key}/fill")
        response = await http.get("/api/v1/edge/links/zzzzz", headers=edge("forms.formalie.dev"))
        assert response.status_code == 404 and response.json() == {"error": {"code": "FRM-FORM-1001"}}

        # No secret, or a wrong one: absent, like any route that does not exist
        for secret in (None, "wrong"):
            for path in (f"/api/v1/edge/forms/{key}/preview", f"/api/v1/edge/links/{code}"):
                response = await http.get(path, headers=edge(f"{sub}.formalie.dev", secret))
                assert response.status_code == 404 and response.json()["error"]["code"] == "FRM-GEN-1004"


async def test_closing_workspaces_close_after_their_date(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    later, _ = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Open day", question)
    key = form["public_key"]
    past, future = datetime.now(UTC) - timedelta(minutes=5), datetime.now(UTC) + timedelta(days=3)
    superuser.execute("UPDATE platform.tenants SET status = 'closing', close_at = %s, suspended_reason = %s "
                      "WHERE subdomain = %s", (past, "Closed at the customer's request", sub))
    superuser.execute("UPDATE platform.tenants SET status = 'closing', close_at = %s WHERE subdomain = %s",
                      (future, later))
    forms_before = superuser.execute("SELECT count(*) FROM formaly.forms f JOIN platform.tenants t ON t.id = f.tenant_id "
                                     "WHERE t.subdomain = %s AND f.deleted_at IS NULL", (sub,)).fetchone()[0]

    assert await close_due() >= 1
    rows = dict(superuser.execute("SELECT subdomain, status FROM platform.tenants WHERE subdomain IN (%s, %s)",
                                  (sub, later)).fetchall())
    assert rows == {sub: "closed", later: "closing"}
    tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
    audit = superuser.execute("SELECT action, changes FROM formaly.audit_logs WHERE tenant_id = %s "
                              "AND action = 'workspace.updated' ORDER BY occurred_at DESC LIMIT 1", (tenant_id,)).fetchone()
    assert audit is not None and audit[1][0] == {"field": "status", "before": "closing", "after": "closed"}
    # Nothing deleted: the workspace and its forms are all still there
    assert superuser.execute("SELECT deleted_at FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0] is None
    assert superuser.execute("SELECT count(*) FROM formaly.forms WHERE tenant_id = %s AND deleted_at IS NULL",
                             (tenant_id,)).fetchone()[0] == forms_before
    await close_due()  # running again changes nothing for these two
    assert superuser.execute("SELECT status FROM platform.tenants WHERE subdomain = %s", (later,)).fetchone()[0] == "closing"

    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        visitor = SecureClient(http)
        status, reply = await visitor.request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
        assert status == 403 and reply["error"]["code"] == "FRM-TEN-1002"
        assert reply["error"]["details"] == [{"field": "workspace", "message": "closed"}]
        _, reply = await visitor.request("GET", f"/public/forms/{key}")
        assert reply["error"]["code"] == "FRM-FORM-1001"  # its public forms take no more answers
        _, reply = await visitor.request("GET", "/tenants/public")
        assert reply["data"]["status"] == "suspended" and reply["data"]["closed"] is True
        assert reply["data"]["status_reason"] == "Closed at the customer's request"

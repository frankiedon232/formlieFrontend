"""The platform admin bridge (B16) end to end on the test database:

- the internal admin API's gate: private network, mutual TLS (production), HMAC signature with timestamp window and
  nonce, staff headers; idempotency keys (replay, conflict); every change in the workspace's audit trail as Formalie
  support under the signed staff name;
- workspaces (suspend with the reason on the sign-in page, restore, read only, close, cancel, subdomain with the
  90 days rule and the platform's reserved list, plan, limits, trial, full export to the Owners), accounts
  (sign out, two-step reset, password reset, disable, enable, unlock), billing (not yet), messages, caches, health;
- support access: consent, Formalie's request and the admins' answer, the one-time ticket, the read-only session and
  its banner, a write session audited as Formalie support, turning it off, expiry, other workspaces;
- global tables read by the portal (legal links, outgoing addresses, announcements, switches) and dropped from the
  cache on `platform.published`;
- events on the outbox with personal data stripped.
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import psycopg
import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.core.events.outbox import EventOutbox
from app.modules.emails.service import SENT
from app.modules.exports import service as exports
from app.modules.exports.models import ExportJob
from app.modules.platform_bridge import globals as G
from app.modules.platform_bridge import signing as sg
from app.modules.platform_bridge import support as SUP
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

KEY_ID = "plat1"
SECRET = "platform-test-secret-" + "z" * 32
STAFF_ID = "0199a000-0000-7000-8000-00000000staf"
STAFF = "Amara Okafor-Lindqvist"
BASE = "/internal/admin/v1"


@pytest.fixture(autouse=True)
def platform_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "platform_admin_keys", [SecretStr(f"{KEY_ID}:{SECRET}")])
    monkeypatch.setattr(settings, "platform_admin_require_mtls", False)


@pytest.fixture
def jobs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> list[ExportJob]:  # noqa: ANN001
    queued: list[ExportJob] = []
    settings = get_settings().model_copy(update={"storage_dir": tmp_path})
    monkeypatch.setattr("app.core.storage.get_settings", lambda: settings)
    monkeypatch.setattr(exports, "dispatch", queued.append)
    return queued


def platform(app, peer: str = "127.0.0.1"):  # noqa: ANN001, ANN201
    """The platform admin's server, on Formalie's private network."""
    return client_for(app, host="formalie.dev", peer=peer)


async def call(http, method: str, path: str, body: Any = None, *, staff: bool = True, key: str | None = None,  # noqa: ANN001
               reason: str = "Ticket 4471: the customer asked", sign: dict[str, Any] | None = None,
               raw: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict, Any]:
    content = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    extra: dict[str, str] = {}
    if staff:
        extra = {"X-Platform-Staff-Id": STAFF_ID[:36], "X-Platform-Staff-Name": quote(STAFF), "X-Platform-Reason": quote(reason),
                 "X-Platform-Approval-Id": "appr-77", "Idempotency-Key": key or f"idem-{uuid.uuid4().hex}"}
    signed = sg.sign_headers(KEY_ID, SECRET, method, f"{BASE}{path}", content, extra, **(sign or {}))
    response = await http.request(method, f"{BASE}{path}", content=content,
                                  headers={**signed, "content-type": "application/json", **(headers or {})})
    return response.status_code, response.json(), response.headers


def tenant_of(superuser: psycopg.Connection, sub: str) -> tuple[uuid.UUID, uuid.UUID]:
    row = superuser.execute("SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()
    return row[0], row[1]


def audit_rows(superuser: psycopg.Connection, tenant_id: uuid.UUID, action: str) -> list[tuple]:
    return superuser.execute(
        "SELECT actor_type, actor_name, staff_id, staff_name, approval_id, metadata, changes FROM formaly.audit_logs "
        "WHERE tenant_id = %s AND action = %s ORDER BY occurred_at", (tenant_id, action)).fetchall()


async def owner_of(app, sub: str, email: str) -> SecureClient:  # noqa: ANN001
    """The workspace's Owner, signed in (the client stays open for the test)."""
    owner = SecureClient(client_for(app, host=f"{sub}.formalie.dev"))
    await sign_in(owner, email, PASSWORD)
    return owner


# ── The gate ─────────────────────────────────────────────────────────────────────────

async def test_only_signed_calls_from_the_private_network_pass(app, monkeypatch) -> None:  # noqa: ANN001, F811
    settings = get_settings()
    async with platform(app) as http:
        status, reply, _ = await call(http, "GET", "/health/services", staff=False)
        assert status == 200 and reply["success"] and reply["data"]["status"] in ("ok", "degraded", "down")
        names = {s["name"] for s in reply["data"]["services"]}
        assert {"database_primary", "redis", "rabbitmq", "event_outbox"} <= names
        assert next(s for s in reply["data"]["services"] if s["name"] == "database_primary")["status"] == "ok"
        assert "password" not in json.dumps(reply).lower()

        # Unsigned, unknown key, tampered body, wrong secret, late, replayed
        response = await http.get(f"{BASE}/health/services")
        assert response.status_code == 400 and response.json()["error"]["code"] == "FRM-SEC-1005"
        headers = sg.sign_headers("nobody", SECRET, "GET", f"{BASE}/health/services")
        assert (await http.get(f"{BASE}/health/services", headers=headers)).json()["error"]["code"] == "FRM-SEC-1007"
        headers = sg.sign_headers(KEY_ID, SECRET, "POST", f"{BASE}/cache/invalidate", b'{"table":"plans"}')
        response = await http.post(f"{BASE}/cache/invalidate", content=b'{"table":"plans","x":1}', headers=headers)
        assert response.json()["error"]["code"] == "FRM-SEC-1005"
        headers = sg.sign_headers(KEY_ID, "wrong-" + "q" * 40, "GET", f"{BASE}/health/services")
        assert (await http.get(f"{BASE}/health/services", headers=headers)).json()["error"]["code"] == "FRM-SEC-1005"
        status, reply, _ = await call(http, "GET", "/health/services", staff=False,
                                      sign={"timestamp": int(datetime.now(UTC).timestamp()) - 301})
        assert status == 400 and reply["error"]["code"] == "FRM-SEC-1002"
        headers = sg.sign_headers(KEY_ID, SECRET, "GET", f"{BASE}/health/services", nonce="same-nonce-" + "x" * 10)
        assert (await http.get(f"{BASE}/health/services", headers=headers)).status_code == 200
        replay = await http.get(f"{BASE}/health/services", headers=headers)
        assert replay.status_code == 400 and replay.json()["error"]["code"] == "FRM-SEC-1003"
        # A change must say who and why, with an idempotency key
        status, reply, _ = await call(http, "POST", "/cache/invalidate", {"table": "plans"}, staff=False)
        assert status == 422 and {d["field"] for d in reply["error"]["details"]} == {
            "X-Platform-Staff-Id", "X-Platform-Staff-Name", "X-Platform-Reason", "Idempotency-Key"}
        # Unknown routes answer only after the signature (no probing)
        assert (await http.post(f"{BASE}/nothing/here")).json()["error"]["code"] == "FRM-SEC-1005"
        status, reply, _ = await call(http, "POST", "/nothing/here", {})
        assert status == 404 and reply["error"]["code"] == "FRM-GEN-1004"

    async with platform(app, peer="203.0.113.7") as http:  # not Formalie's private network
        status, reply, _ = await call(http, "GET", "/health/services", staff=False)
        assert status == 403 and reply["error"]["code"] == "FRM-SEC-1007"

    # Production: mutual TLS through Nginx, a known client certificate
    fingerprint = "AA:BB:" + "11" * 30
    monkeypatch.setattr(settings, "platform_admin_require_mtls", True)
    monkeypatch.setattr(settings, "platform_admin_cert_fingerprints", [fingerprint])
    async with platform(app) as http:
        status, reply, _ = await call(http, "GET", "/health/services", staff=False)
        assert status == 403 and reply["error"]["code"] == "FRM-SEC-1007"
        status, _, _ = await call(http, "GET", "/health/services", staff=False,
                                  headers={"x-client-verify": "SUCCESS", "x-client-cert-fingerprint": "ff" * 32})
        assert status == 403
        status, _, _ = await call(http, "GET", "/health/services", staff=False,
                                  headers={"x-client-verify": "SUCCESS", "x-client-cert-fingerprint": fingerprint})
        assert status == 200
    async with platform(app, peer="10.1.2.3") as http:  # on the network, but not through the trusted proxy
        status, _, _ = await call(http, "GET", "/health/services", staff=False,
                                  headers={"x-client-verify": "SUCCESS", "x-client-cert-fingerprint": fingerprint})
        assert status == 403
    monkeypatch.setattr(settings, "platform_admin_keys", [])
    async with platform(app) as http:
        status, reply, _ = await call(http, "GET", "/health/services", staff=False)
        assert status == 403 and reply["error"]["code"] == "FRM-SEC-1007"


# ── Workspaces ───────────────────────────────────────────────────────────────────────

async def test_suspend_restore_read_only_close_with_idempotency_audit_and_events(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    other_sub, _ = await new_workspace(app)
    other_id, _ = tenant_of(superuser, other_sub)
    suspend_key = f"suspend-{uuid.uuid4().hex}"
    owner = await owner_of(app, sub, email)
    async with platform(app) as admin:
        status, reply, headers = await call(admin, "POST", f"/tenants/{tenant_id}/suspend",
                                            {"reason": "Unpaid invoice INV-2201"}, key=suspend_key)
        assert status == 200, reply
        view = reply["data"]
        assert view["status"] == "suspended" and view["status_reason"] == "Unpaid invoice INV-2201"
        assert set(view) == {"id", "subdomain", "name", "status", "status_reason", "plan_id", "plan_limits",
                             "trial_ends_at", "close_at", "data_region", "setup_completed_at", "created_at"}
        assert "Idempotent-Replayed" not in headers
        # The same key again: the same answer, nothing done twice
        status, again, headers = await call(admin, "POST", f"/tenants/{tenant_id}/suspend",
                                            {"reason": "Unpaid invoice INV-2201"}, key=suspend_key)
        assert status == 200 and again == reply and headers["Idempotent-Replayed"] == "true"
        status, conflict, _ = await call(admin, "POST", f"/tenants/{tenant_id}/suspend", {"reason": "Something else"},
                                         key=suspend_key)
        assert status == 409 and conflict["error"]["code"] == "FRM-BILL-1005"
        assert len(audit_rows(superuser, tenant_id, "workspace.updated")) == 1

        # The workspace: refused, with the reason on its sign-in page
        status, reply = await owner.request("GET", "/forms")
        assert status == 403 and reply["error"]["code"] == "FRM-TEN-1002"
        async with client_for(app, host=f"{sub}.formalie.dev") as anon:
            _, profile = await SecureClient(anon).request("GET", "/tenants/public")
        assert profile["data"]["status"] == "suspended" and profile["data"]["status_reason"] == "Unpaid invoice INV-2201"

        # Audit: Formalie support, the signed name, the approval and the reason
        actor_type, actor_name, staff_id, staff_name, approval, metadata, changes = \
            audit_rows(superuser, tenant_id, "workspace.updated")[0]
        assert (actor_type, staff_name, approval) == ("platform_support", STAFF, "appr-77")
        assert actor_name == f"Formalie support ({STAFF})" and staff_id == STAFF_ID[:36]
        assert metadata["staff_reason"] == "Ticket 4471: the customer asked" and metadata["via"] == "platform_admin"
        assert changes == [{"field": "status", "before": "active", "after": "suspended"}]
        assert not audit_rows(superuser, other_id, "workspace.updated")  # nothing in another workspace

        # Restore, then read only: looking works, changing doesn't
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/restore")
        assert status == 200 and reply["data"]["status"] == "active" and reply["data"]["status_reason"] is None
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/read-only", {"reason": "Billing review"})
        assert reply["data"]["status"] == "read_only"
        assert (await owner.request("GET", "/forms"))[0] == 200
        status, reply = await owner.request("POST", "/forms", body={"name": "Blocked"})
        assert status == 403 and reply["error"]["details"] == [{"field": "workspace", "message": "read_only"}]
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/cancel-close")
        assert status == 409 and reply["error"]["code"] == "FRM-GEN-1009"

        # Close in a month, then change our mind
        close_at = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/close", {"reason": "Owner asked", "close_at": close_at})
        assert status == 200 and reply["data"]["status"] == "closing" and reply["data"]["close_at"]
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/close",
                                      {"reason": "Too soon", "close_at": datetime.now(UTC).isoformat()})
        assert status == 422
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/cancel-close")
        assert reply["data"]["status"] == "active" and reply["data"]["close_at"] is None
        assert (await owner.request("POST", "/forms", body={"name": "Allowed again"}))[0] == 201

        status, reply, _ = await call(admin, "POST", f"/tenants/{uuid.uuid4()}/suspend", {"reason": "x"})
        assert status == 404 and reply["error"]["code"] == "FRM-GEN-1004"

    # Events: suspended and closed, no personal data; the call log has every change
    events = superuser.execute("SELECT type, payload FROM formaly.event_outbox WHERE tenant_id = %s AND type LIKE 'tenant.%%'",
                               (tenant_id,)).fetchall()
    types = [t for t, _ in events]
    assert "tenant.suspended" in types and "tenant.closed" in types and "tenant.signed_up" in types
    calls = superuser.execute("SELECT method, status_code, staff_name FROM platform.admin_calls WHERE tenant_id = %s",
                              (tenant_id,)).fetchall()
    assert len(calls) == 5 and all(name == STAFF and code == 200 for _, code, name in calls)


async def test_subdomain_plan_and_reserved_names_through_the_cache(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    new_sub = f"moved{uuid.uuid4().hex[:6]}"
    async with platform(app) as admin:
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/subdomain", {"subdomain": new_sub.upper()})
        assert status == 200 and reply["data"]["subdomain"] == new_sub
        until = superuser.execute("SELECT until FROM platform.tenant_subdomain_history WHERE tenant_id = %s AND subdomain = %s",
                                  (tenant_id, sub)).fetchone()[0]
        assert timedelta(days=89) < until - datetime.now(UTC) <= timedelta(days=90)
        async with client_for(app, host=f"{sub}.formalie.dev") as old:  # the old address still leads here
            _, profile = await SecureClient(old).request("GET", "/tenants/public")
        assert profile["data"]["subdomain"] == new_sub
        assert audit_rows(superuser, tenant_id, "settings.updated")[-1][6] == [
            {"field": "subdomain", "before": sub, "after": new_sub}]
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/subdomain", {"subdomain": "api"})
        assert status == 409 and reply["error"]["details"][0]["message"] == "invalid"

        # The Formalie team reserves a name: once the cache is dropped, nobody can take it
        reserved = f"brand{uuid.uuid4().hex[:6]}"
        async with client_for(app, host="manage.formalie.dev") as manage:
            client = SecureClient(manage)
            _, reply = await client.request("GET", "/tenants/subdomain-availability", query={"subdomain": reserved})
            assert reply["data"] == {"available": True, "reason": None}
            with superuser.transaction():
                superuser.execute("SET LOCAL ROLE platform_writer")
                superuser.execute("INSERT INTO platform.reserved_subdomains (subdomain, reason, published_by_staff_id) "
                                  "VALUES (%s, 'Partner brand', %s)", (reserved, uuid.uuid4()))
            _, reply = await client.request("GET", "/tenants/subdomain-availability", query={"subdomain": reserved})
            assert reply["data"]["available"]  # still cached
            status, reply, _ = await call(admin, "POST", "/cache/invalidate", {"table": "reserved_subdomains", "version": 3})
            assert status == 200 and reply["data"]["tables"] == ["reserved_subdomains"]
            _, reply = await client.request("GET", "/tenants/subdomain-availability", query={"subdomain": reserved})
            assert reply["data"] == {"available": False, "reason": "reserved"}
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/subdomain", {"subdomain": reserved})
        assert status == 409 and reply["error"]["details"][0]["message"] == "reserved"

        # Plan, limits and trial
        trial = (datetime.now(UTC) + timedelta(days=14)).replace(microsecond=0)
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/plan", {
            "plan_id": "business", "limits": {"forms": 500, "ai_credits": 5000}, "trial_ends_at": trial.isoformat()})
        assert status == 200, reply
        assert reply["data"]["plan_id"] == "business" and reply["data"]["plan_limits"] == {"forms": 500, "ai_credits": 5000}
        assert reply["data"]["trial_ends_at"].startswith(trial.strftime("%Y-%m-%dT%H:%M"))
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/plan", {"limits": None})
        assert reply["data"]["plan_limits"] is None and reply["data"]["plan_id"] == "business"
        for bad in ({"plan_id": "platinum"}, {"limits": {"rockets": 1}}, {}):
            status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/plan", bad)
            assert status == 422, bad
        changes = audit_rows(superuser, tenant_id, "workspace.updated")[0][6]
        assert {c["field"] for c in changes} == {"plan", "plan_limits", "trial_ends_at"}


async def test_full_export_goes_to_the_owners(app, superuser, jobs) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, org_id = tenant_of(superuser, sub)
    owner = await owner_of(app, sub, email)
    async with platform(app) as admin:
        await owner.request("POST", "/forms", body={"name": "Exported form"})
        status, reply, _ = await call(admin, "POST", f"/tenants/{tenant_id}/export")
        assert status == 200 and reply["data"]["status"] == "queued" and reply["data"]["file_name"].endswith(".zip")
        assert len(jobs) == 1
        job = jobs.pop()
        await exports.build(job.id, job.tenant_id, job.organisation_id)
        _, feed = await owner.request("GET", "/notifications")
        notice = next(n for n in feed["data"]["items"] if n["event"] == "export_ready")
        link = notice["link"]
        assert link.startswith("/api/v1/downloads/")
        response = await owner.http.get(link)
        assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        people = json.loads(archive.read("people.json"))
        assert people[0]["email"] == email and "password_hash" not in people[0]
        assert json.loads(archive.read("forms.json"))[0]["name"] == "Exported form"
        assert (await owner.http.get(link)).status_code == 410  # once
    assert audit_rows(superuser, tenant_id, "settings.data_exported")[0][0] == "platform_support"
    assert superuser.execute("SELECT count(*) FROM formaly.event_outbox WHERE tenant_id = %s AND type = 'export.completed'",
                             (tenant_id,)).fetchone()[0] == 1
    _ = org_id


# ── Accounts ─────────────────────────────────────────────────────────────────────────

async def test_account_actions(app, superuser, redis) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    user_id = superuser.execute("SELECT id FROM formaly.users WHERE tenant_id = %s", (tenant_id,)).fetchone()[0]
    owner = await owner_of(app, sub, email)
    async with platform(app) as admin:
        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/sign-out")
        assert status == 200 and reply["data"]["sessions_ended"] == 1
        status, reply = await owner.request("GET", "/forms")
        assert status == 401 and reply["error"]["code"] == "FRM-AUTH-1011"
        await sign_in(owner, email, PASSWORD)

        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/password-reset")
        assert reply["data"]["must_change_password"] is True and reply["data"]["sessions_ended"] == 1
        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/two-step/reset")
        assert status == 200
        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/disable")
        assert reply["data"]["status"] == "disabled" and reply["data"]["changed"]
        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/enable")
        assert reply["data"]["status"] == "active"

        import hashlib

        digest = hashlib.sha256(email.encode()).hexdigest()[:32]
        await redis.zadd(f"fm:v1:rl:route:login:v:{digest}", {"1:a": 1})
        status, reply, _ = await call(admin, "POST", f"/users/{user_id}/unlock")
        assert reply["data"]["changed"] and not await redis.exists(f"fm:v1:rl:route:login:v:{digest}")

        status, reply, _ = await call(admin, "POST", f"/users/{uuid.uuid4()}/disable")
        assert status == 404
        for path in ("/subscriptions/x/activate", "/subscriptions/x/extend", "/subscriptions/x/credit",
                     "/subscriptions/x/cancel", "/payments/x/refund"):
            status, reply, _ = await call(admin, "POST", path, {"amount_cents": 100})
            assert status == 404 and reply["error"]["details"][0]["message"] == "billing_not_available_yet", path
    actions = [r[0] for r in superuser.execute(
        "SELECT action FROM formaly.audit_logs WHERE tenant_id = %s AND actor_type = 'platform_support' ORDER BY occurred_at",
        (tenant_id,)).fetchall()]
    assert actions == ["users.signed_out", "users.password_requested", "users.disabled", "users.enabled", "users.updated"]


async def test_messages_to_workspaces(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    before = len(SENT)
    async with platform(app) as admin:
        status, reply, _ = await call(admin, "POST", "/communications/send", {
            "tenant_ids": [str(tenant_id)], "subject": {"en": "Planned maintenance", "fr": "Maintenance prévue"},
            "body": {"en": "Formalie is down for 10 minutes on Sunday."}, "essential": True})
        assert status == 200 and reply["data"] == {"workspaces": 1, "emails": 1, "notices": 1}
        status, reply, _ = await call(admin, "POST", "/communications/send", {"tenant_ids": [str(tenant_id)],
                                                                              "subject": {"fr": "x"}, "body": {"fr": "y"}})
        assert status == 422
    assert any(m["to"] == email and m["values"]["title"] == "Planned maintenance" for m in SENT[before:])
    notice = superuser.execute("SELECT event, params FROM formaly.notifications WHERE tenant_id = %s AND event = 'platform_message'",
                               (tenant_id,)).fetchone()
    assert notice[1]["title"] == "Planned maintenance"


# ── Support access ───────────────────────────────────────────────────────────────────

async def test_support_access_with_consent_from_request_to_expiry(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    other_sub, other_email = await new_workspace(app)
    owner = await owner_of(app, sub, email)
    other_owner = await owner_of(app, other_sub, other_email)
    async with platform(app) as admin:
        _, reply = await owner.request("GET", "/settings/security/support-access")
        assert reply["data"] == {"grant": None, "requests": [], "sessions": [], "hours": [1, 24, 168], "modes": ["read", "write"]}

        # Formalie asks; the admins see it
        status, reply, _ = await call(admin, "POST", "/support-access/requests",
                                      {"tenant_id": str(tenant_id), "reason": "Your import keeps failing", "hours": 24})
        assert status == 200 and reply["data"]["status"] == "pending"
        _, feed = await owner.request("GET", "/notifications")
        assert any(n["event"] == "support_request" for n in feed["data"]["items"])
        _, state = await owner.request("GET", "/settings/security/support-access")
        asked = state["data"]["requests"][0]
        assert asked["staff_name"] == STAFF and asked["reason"] == "Your import keeps failing" and asked["hours"] == 24
        # No session without a grant
        status, _, _ = await call(admin, "POST", f"/support-access/{uuid.uuid4()}/session", {"mode": "read"})
        assert status == 404
        # Another workspace can't answer it
        status, _ = await other_owner.request("POST", f"/settings/security/support-access/requests/{asked['id']}/decline")
        assert status in (404, 422)

        # The owner approves, read only for 24 hours
        status, state = await owner.request("POST", "/settings/security/support-access",
                                            body={"hours": 24, "mode": "read", "request_id": asked["id"]})
        assert status == 200, state
        grant = state["data"]["grant"]
        assert grant["mode"] == "read" and grant["hours"] == 24 and not state["data"]["requests"]
        grant_id = superuser.execute("SELECT id FROM formaly.support_access_grants WHERE tenant_id = %s", (tenant_id,)).fetchone()[0]

        # A session: never write on a read grant; a one-time ticket
        status, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {"mode": "write"})
        assert status == 403 and reply["error"]["details"][0]["message"] == "grant_read_only"
        status, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {"mode": "read"})
        assert status == 200, reply
        started = reply["data"]
        assert started["redeem_url"].startswith(f"https://{sub}.formalie.dev") and "#ticket=" in started["redeem_url"]
        assert started["mode"] == "read" and started["tenant"]["subdomain"] == sub

        # Another workspace's address doesn't take the ticket; this one does, once
        async with client_for(app, host=f"{other_sub}.formalie.dev") as wrong:
            status, reply = await SecureClient(wrong).request("POST", "/auth/support/redeem", body={"ticket": started["ticket"]})
            assert status == 401 and reply["error"]["code"] == "FRM-AUTH-1010"
        staff_http = client_for(app, host=f"{sub}.formalie.dev")
        staff = SecureClient(staff_http)
        status, reply = await staff.request("POST", "/auth/support/redeem", body={"ticket": started["ticket"]})
        assert status == 200, reply
        tokens = reply["data"]
        assert tokens["support"]["mode"] == "read" and tokens["support"]["staff_name"] == STAFF
        assert tokens["user"]["support"] is True and tokens["user"]["role"] == "owner"
        staff.access_token = tokens["access_token"]
        status, reply = await SecureClient(staff_http).request("POST", "/auth/support/redeem", body={"ticket": started["ticket"]})
        assert status == 401

        # Read only: looking works, changing doesn't; never the profile or the consent
        assert (await staff.request("GET", "/forms"))[0] == 200
        status, reply = await staff.request("POST", "/forms", body={"name": "By support"})
        assert status == 403 and reply["error"]["details"] == [{"field": "support", "message": "read_only"}]
        assert (await staff.request("GET", "/me/profile"))[0] == 403
        assert (await staff.request("GET", "/settings/security/support-access"))[0] == 403
        _, me = await staff.request("GET", "/me")
        assert me["data"]["is_support"] is True and me["data"]["last_name"] == STAFF

        # Everyone in the workspace sees the banner; the other workspace doesn't
        _, me = await owner.request("GET", "/me")
        assert me["data"]["support_session"]["active"] and me["data"]["support_session"]["staff_name"] == STAFF
        assert me["data"]["is_support"] is False
        _, banner = await owner.request("GET", "/support-access/status")
        assert banner["data"]["mode"] == "read"
        _, banner = await other_owner.request("GET", "/support-access/status")
        assert banner["data"] is None
        # A support token on another workspace's address
        other_staff = SecureClient(client_for(app, host=f"{other_sub}.formalie.dev"))
        other_staff.access_token = tokens["access_token"]
        status, reply = await other_staff.request("GET", "/forms")
        assert status == 403 and reply["error"]["code"] == "FRM-TEN-1003"
        await other_staff.http.aclose()

        # The owner turns it off: the session ends at once
        status, state = await owner.request("DELETE", "/settings/security/support-access")
        assert status == 200 and state["data"]["grant"] is None and state["data"]["sessions"][0]["ended_reason"] == "access_ended"
        status, reply = await staff.request("GET", "/forms")
        assert status == 401 and reply["error"]["code"] == "FRM-AUTH-1011"
        _, banner = await owner.request("GET", "/support-access/status")
        assert banner["data"] is None
        await staff_http.aclose()

        # Expiry: a grant past its end stops the session and is closed by the sweep; unused tickets too
        await owner.request("POST", "/settings/security/support-access", body={"hours": 1, "mode": "read"})
        grant_id = superuser.execute("SELECT id FROM formaly.support_access_grants WHERE tenant_id = %s AND revoked_at IS NULL",
                                     (tenant_id,)).fetchone()[0]
        _, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {})
        unused = reply["data"]
        _, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {})
        staff_http = client_for(app, host=f"{sub}.formalie.dev")
        staff = SecureClient(staff_http)
        _, tokens = await staff.request("POST", "/auth/support/redeem", body={"ticket": reply["data"]["ticket"]})
        staff.access_token = tokens["data"]["access_token"]
        assert (await staff.request("GET", "/forms"))[0] == 200
        superuser.execute("UPDATE formaly.support_access_grants SET expires_at = now() - interval '1 minute' WHERE id = %s",
                          (grant_id,))
        superuser.execute("UPDATE formaly.support_sessions SET ticket_expires_at = now() - interval '1 minute' "
                          "WHERE id = %s", (uuid.UUID(unused["session_id"]),))
        status, reply = await staff.request("GET", "/forms")
        assert status == 401 and reply["error"]["code"] == "FRM-AUTH-1001"
        status, _ = await SecureClient(staff_http).request("POST", "/auth/support/redeem", body={"ticket": unused["ticket"]})
        assert status == 401
        await staff_http.aclose()
        assert await SUP.expire_due() >= 2
        grant_row = superuser.execute("SELECT revoked_reason FROM formaly.support_access_grants WHERE id = %s", (grant_id,)).fetchone()
        assert grant_row[0] == "expired"
        reasons = dict(superuser.execute("SELECT id, ended_reason FROM formaly.support_sessions WHERE grant_id = %s",
                                         (grant_id,)).fetchall())
        assert reasons[uuid.UUID(unused["session_id"])] == "not_used"
        status, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {})
        assert status == 403 and reply["error"]["details"][0]["message"] == "not_active"

    # Audit: the consent by the owner, the request and sessions by Formalie support, the sign-in as support
    trail = superuser.execute("SELECT action, actor_type, staff_name FROM formaly.audit_logs WHERE tenant_id = %s "
                              "ORDER BY occurred_at", (tenant_id,)).fetchall()
    assert ("auth.login.succeeded", "platform_support", STAFF) in trail
    assert ("workspace.updated", "platform_support", STAFF) in trail
    assert ("settings.updated", "user", None) in trail and ("settings.updated", "system", None) in trail
    # A support sign-in is not a customer sign-in for the platform's analytics
    signed_in = superuser.execute("SELECT count(*) FROM formaly.event_outbox WHERE tenant_id = %s AND type = 'auth.signed_in'",
                                  (tenant_id,)).fetchone()[0]
    assert signed_in == 1


async def test_a_write_session_changes_as_formalie_support(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    owner = await owner_of(app, sub, email)
    async with platform(app) as admin:
        await owner.request("POST", "/settings/security/support-access", body={"hours": 1, "mode": "write"})
        grant_id = superuser.execute("SELECT id FROM formaly.support_access_grants WHERE tenant_id = %s", (tenant_id,)).fetchone()[0]
        _, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {"mode": "write"})
        async with client_for(app, host=f"{sub}.formalie.dev") as staff_http:
            staff = SecureClient(staff_http)
            _, tokens = await staff.request("POST", "/auth/support/redeem", body={"ticket": reply["data"]["ticket"]})
            staff.access_token = tokens["data"]["access_token"]
            status, reply = await staff.request("POST", "/forms", body={"name": "Fixed by support"})
            assert status == 201, reply
            assert (await staff.request("POST", "/me/password", body={"current": "x", "password": "y"}))[0] == 403
            status, _ = await staff.request("POST", "/auth/support/end")
            assert status == 200
            assert (await staff.request("GET", "/forms"))[0] == 401
    row = superuser.execute("SELECT actor_type, actor_name, staff_name FROM formaly.audit_logs WHERE tenant_id = %s "
                            "AND action = 'forms.created'", (tenant_id,)).fetchone()
    assert row == ("platform_support", f"Formalie support ({STAFF})", STAFF)
    # It belongs to the workspace's Owner; no account was made for Formalie support
    owner_id = superuser.execute("SELECT owner_id FROM formaly.forms WHERE tenant_id = %s AND name = 'Fixed by support'",
                                 (tenant_id,)).fetchone()[0]
    assert superuser.execute("SELECT email FROM formaly.users WHERE id = %s", (owner_id,)).fetchone()[0] == email
    assert superuser.execute("SELECT count(*) FROM formaly.users WHERE tenant_id = %s", (tenant_id,)).fetchone()[0] == 1
    # In the owner's audit list it shows as Formalie, under the staff member's name
    async with client_for(app, host=f"{sub}.formalie.dev") as http2:
        owner2 = SecureClient(http2)
        await sign_in(owner2, email, PASSWORD)
        _, entries = await owner2.request("GET", "/audit-logs", query={"page_size": 100})
    created = next(e for e in entries["data"] if e["action"] == "forms.created")
    assert created["actor"]["type"] == "system" and created["actor"]["name"] == STAFF


# ── Global tables in the portal ──────────────────────────────────────────────────────

async def test_published_settings_announcements_and_switches(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    staff = uuid.uuid4()
    for table in ("platform_settings", "announcements", "feature_flags"):
        await G.invalidate([table])
    assert await G.legal_links() == {"terms_url": get_settings().legal_terms_url,
                                     "privacy_url": get_settings().legal_privacy_url}
    owner = await owner_of(app, sub, email)
    if owner:
        _, meta = await owner.request("GET", "/datasources/meta")
        assert meta["data"]["egress_ips"] == list(get_settings().egress_ips)
        key = f"switch_{uuid.uuid4().hex[:6]}"
        announcement = uuid.uuid4()
        with superuser.transaction():
            superuser.execute("SET LOCAL ROLE platform_writer")
            superuser.execute("UPDATE platform.platform_settings SET value = %s, published_by_staff_id = %s WHERE key = 'legal'",
                              (json.dumps({"terms_url": "https://formalie.com/legal/terms-2027"}), staff))
            superuser.execute("UPDATE platform.platform_settings SET value = %s, published_by_staff_id = %s "
                              "WHERE key = 'egress_ips'", (json.dumps(["198.51.100.20"]), staff))
            superuser.execute("INSERT INTO platform.feature_flags (key, enabled, tenant_ids, rollout_percent, "
                              "published_by_staff_id) VALUES (%s, true, %s, 0, %s)", (key, [tenant_id], staff))
            superuser.execute("INSERT INTO platform.announcements (id, kind, tone, audience, tenant_ids, starts_at, "
                              "published_by_staff_id) VALUES (%s, 'maintenance', 'warning', 'tenants', %s, now() - "
                              "interval '1 hour', %s)", (announcement, [tenant_id], staff))
            for language, title in (("en", "Maintenance on Sunday"), ("fr", "Maintenance dimanche")):
                superuser.execute("INSERT INTO platform.announcement_translations (announcement_id, language, title, "
                                  "body, published_by_staff_id) VALUES (%s, %s, %s, 'Ten minutes.', %s)",
                                  (announcement, language, title, staff))
        try:
            # Cached until the platform says it published
            assert (await G.legal_links())["terms_url"] == get_settings().legal_terms_url
            done = await G.on_published({"type": "platform.published", "properties": {
                "tables": ["platform_settings", "feature_flags", "announcements", "announcement_translations",
                           "help_articles"], "version": 9}})
            assert "platform_settings" in done and "announcements" in done
            legal = await G.legal_links()
            assert legal == {"terms_url": "https://formalie.com/legal/terms-2027",
                             "privacy_url": get_settings().legal_privacy_url}
            _, meta = await owner.request("GET", "/datasources/meta")
            assert meta["data"]["egress_ips"] == ["198.51.100.20"]
            _, flags = await owner.request("GET", "/platform/feature-flags")
            assert flags["data"][key] is True
            _, items = await owner.request("GET", "/platform/announcements", query={"lang": "fr"})
            assert [i["title"] for i in items["data"]] == ["Maintenance dimanche"]
            assert items["data"][0]["kind"] == "maintenance" and items["data"][0]["tone"] == "warning"
            other_sub, other_email = await new_workspace(app)
            other_owner = await owner_of(app, other_sub, other_email)
            if other_owner:
                _, items = await other_owner.request("GET", "/platform/announcements")
                _, flags = await other_owner.request("GET", "/platform/feature-flags")
            assert items["data"] == [] and flags["data"][key] is False
        finally:
            with superuser.transaction():
                superuser.execute("UPDATE platform.platform_settings SET published_by_staff_id = NULL, value = %s "
                                  "WHERE key = 'legal'", (json.dumps({"terms_url": get_settings().legal_terms_url,
                                                                      "privacy_url": get_settings().legal_privacy_url}),))
                superuser.execute("UPDATE platform.platform_settings SET published_by_staff_id = NULL, value = '[]' "
                                  "WHERE key = 'egress_ips'")
                superuser.execute("UPDATE platform.announcements SET retired_at = now() WHERE id = %s", (announcement,))
            for table in ("platform_settings", "announcements", "feature_flags"):
                await G.invalidate([table])


# ── Events ───────────────────────────────────────────────────────────────────────────

async def test_events_on_the_bus_carry_no_personal_data(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    owner = await owner_of(app, sub, email)
    if owner:
        _, form = await owner.request("POST", "/forms", body={"name": "Visitor sign-in"})
        await owner.request("POST", "/people", body={"first_name": "Zanele", "last_name": "Moreau",
                                                     "email": f"zanele@{sub}.test", "role": "member"})
        await owner.request("POST", "/auth/logout")
        async with client_for(app, host=f"{sub}.formalie.dev") as wrong_http:
            await SecureClient(wrong_http).request("POST", "/auth/login", body={"email": email, "password": "Wrong-Pass-1"})
    rows = superuser.execute("SELECT * FROM formaly.event_outbox WHERE tenant_id = %s ORDER BY created_at",
                             (tenant_id,)).fetchall()
    columns = [c.name for c in superuser.execute("SELECT * FROM formaly.event_outbox LIMIT 0").description]
    wires = [EventOutbox(**dict(zip(columns, row))).envelope().wire() for row in rows]
    types = [w["type"] for w in wires]
    for expected in ("tenant.signed_up", "auth.signed_in", "auth.two_step_used", "form.created", "user.invited",
                     "auth.signed_out", "auth.sign_in_failed"):
        assert expected in types, (expected, types)
    dumped = json.dumps(wires)
    for personal in (email, "Olu", "Ade", "Zanele", "Moreau", "zanele@", "Visitor sign-in", "Wrong-Pass-1", "@"):
        assert personal not in dumped, personal
    signed_up = next(w for w in wires if w["type"] == "tenant.signed_up")
    assert signed_up["properties"] == {"plan": "starter", "method": "password"} and signed_up["source"] == "portal"
    assert signed_up["tenant_ref"] == str(tenant_id) and signed_up["plan"] == "starter"
    created = next(w for w in wires if w["type"] == "form.created")
    assert created["properties"] == {"form_id": created["properties"]["form_id"]} and created["actor_ref"]
    failed = next(w for w in wires if w["type"] == "auth.sign_in_failed")
    assert failed["properties"] == {"method": "password", "reason": "FRM-AUTH-1002", "outcome": "failure"}
    _ = form

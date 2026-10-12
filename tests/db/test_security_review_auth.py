"""Security review fixes (B17, 2026-10-12) end to end on the test database:

- H3: with the workspace's own mail server working, reset and sign-in codes still leave through Formalie's relay in
  Formalie's wording; other workspace emails keep the workspace's server;
- M2: an account with an authenticator app is offered the app only, can't switch to an email code, and still gets
  in with a recovery code; an app code works once (L5);
- M3: "forgot password" ends every session of that person, audited;
- M4: a write-mode support session can't create people, invitations, links or tokens, or touch the sending address,
  and never sees the shared sign-up link;
- L2: an account without a password is checked against the dummy hash; L4: a code is re-sent only on its workspace.
"""

from __future__ import annotations

import uuid

import pyotp
import pytest

from app.core.security.passwords import DUMMY_HASH
from app.modules.emails.service import SENT
from tests.conftest import client_for
from tests.db.test_auth_flows import PASSWORD as SEED_PASSWORD
from tests.db.test_auth_flows import _new_workspace, app, last_code, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import on_plan
from tests.db.test_email_settings import smtp  # noqa: F401  (fixture)
from tests.db.test_platform_bridge import call, owner_of, platform, platform_keys, tenant_of  # noqa: F401
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

NEW = "Fresh-Password-42"


def _mails(since: int, email: str, key: str) -> list[dict]:
    return [m for m in SENT[since:] if m["to"] == email and m["key"] == key]


# ── H3 ───────────────────────────────────────────────────────────────────────────

async def test_codes_skip_the_workspaces_own_mail_server(app, owner_dsn, smtp) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        server = {"host": "127.0.0.1", "port": smtp.port, "security": "none", "username": "mailer",
                  "password": "s3cret-pass", "from_address": "team@acme.test"}
        await owner.request("PUT", "/settings/emails/sending/smtp", body=server)
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["status"] == "working", reply
        _, reply = await owner.request("POST", "/settings/emails/sending/mode", body={"mode": "smtp"})
        assert reply["data"]["mode"] == "smtp"
        # The workspace's own wording for the reset email, with the code in an image address on its server
        _, section = await owner.request("GET", "/settings/emails")
        custom = {"password_reset": {"en": {"subject": "Reset", "body": "![x](https://mail.acme.test/{{code}}.png)"}}}
        status, reply = await owner.request("PATCH", "/settings/emails", body={**section["data"], "custom": custom})
        assert status == 200, reply

        since = len(SENT)
        await owner.request("POST", "/settings/emails/test", body={
            "key": "notification", "language": "en", "subject": "Through yours", "body": "Body"})
        assert SENT[since]["route"]["mode"] == "smtp"  # everything else: the workspace's choice

    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        since = len(SENT)
        await SecureClient(http).request("POST", "/auth/password/forgot", body={"email": email})
        await SecureClient(http).request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
    for key in ("password_reset", "signin_code"):
        [mail] = _mails(since, email, key)
        assert "route" not in mail, key  # Formalie's relay and address
    [reset] = _mails(since, email, "password_reset")
    assert "mail.acme.test" not in reset["html"] and reset["values"]["code"] in reset["text"]


# ── M2 and L5 ──────────────────────────────────────────────────────────────────

async def test_an_authenticator_app_is_the_only_second_step(app) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        me = SecureClient(http)
        await sign_in(me, email, PASSWORD)
        _, reply = await me.request("POST", "/me/two-step/app")
        secret = reply["data"]["secret"]
        _, reply = await me.request("POST", "/me/two-step/app/confirm", body={"code": pyotp.TOTP(secret).now()})
        recovery = reply["data"]["recovery_codes"]

    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        client = SecureClient(http)
        since = len(SENT)
        _, reply = await client.request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
        challenge = reply["data"]
        assert challenge["channels"] == ["totp"] and challenge["channel"] == "totp"
        assert set(challenge) == {"challenge_id", "channels", "channel", "masked_destination", "resend_after", "expires_at"}
        status, reply = await client.request("POST", "/auth/otp/resend", body={
            "challenge_id": challenge["challenge_id"], "channel": "email"})
        assert (status, reply["error"]["code"]) == (400, "FRM-AUTH-1008")
        assert not _mails(since, email, "signin_code")  # no email code was sent
        code = pyotp.TOTP(secret).now()
        status, reply = await client.request("POST", "/auth/otp/verify", body={
            "challenge_id": challenge["challenge_id"], "code": code})
        assert status == 200, reply

        # The same app code again: refused (one use per 30-second step); a recovery code still gets in
        _, reply = await client.request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
        challenge_id = reply["data"]["challenge_id"]
        _, reply = await client.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": code})
        assert reply["error"]["code"] == "FRM-AUTH-1003"
        status, reply = await client.request("POST", "/auth/otp/verify", body={
            "challenge_id": challenge_id, "code": recovery[0]})
        assert status == 200, reply
        # A recovery code works once
        _, reply = await client.request("POST", "/auth/login", body={"email": email, "password": PASSWORD})
        _, reply = await client.request("POST", "/auth/otp/verify", body={
            "challenge_id": reply["data"]["challenge_id"], "code": recovery[0]})
        assert reply["error"]["code"] == "FRM-AUTH-1003"


# ── M3 ───────────────────────────────────────────────────────────────────────────

async def test_forgot_password_ends_every_session(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as stolen_http, \
            client_for(app, host=f"{sub}.formalie.dev") as http:
        stolen = SecureClient(stolen_http)
        await sign_in(stolen, email, PASSWORD)
        client = SecureClient(http)
        _, reply = await client.request("POST", "/auth/password/forgot", body={"email": email})
        _, reply = await client.request("POST", "/auth/password/reset", body={
            "challenge_id": reply["data"]["challenge_id"], "code": last_code(email), "password": NEW})
        assert reply["data"] == {"reset": True}
        _, reply = await stolen.request("GET", "/me")
        assert reply["error"]["code"] == "FRM-AUTH-1011"
        status, reply = await stolen.request("POST", "/auth/refresh")
        assert status == 401  # the refresh cookie is no use either
        await sign_in(client, email, NEW)
    tenant_id, _ = tenant_of(superuser, sub)
    rows = superuser.execute(
        "SELECT action, metadata FROM formaly.audit_logs WHERE tenant_id = %s AND action IN "
        "('auth.password.reset', 'auth.session.revoked') ORDER BY occurred_at", (tenant_id,)).fetchall()
    assert rows[0][0] == "auth.password.reset" and rows[0][1]["sessions_ended"] == "1"
    assert ("auth.session.revoked", {"sessions": "1", "cause": "password_reset"}) in [(a, m) for a, m in rows]
    ended = superuser.execute("SELECT count(*) FROM formaly.user_sessions WHERE tenant_id = %s AND "
                              "revoked_reason = 'password_reset'", (tenant_id,)).fetchone()[0]
    assert ended == 1


# ── M4 and H3: support sessions ─────────────────────────────────────────────────────

async def test_a_write_support_session_cannot_give_lasting_access(app, superuser, platform_keys) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id, _ = tenant_of(superuser, sub)
    owner = await owner_of(app, sub, email)
    _, link = await owner.request("GET", "/people/signup-link")
    assert link["data"]["link"]
    async with platform(app) as admin:
        await owner.request("POST", "/settings/security/support-access", body={"hours": 1, "mode": "write"})
        grant_id = superuser.execute("SELECT id FROM formaly.support_access_grants WHERE tenant_id = %s",
                                     (tenant_id,)).fetchone()[0]
        _, reply, _ = await call(admin, "POST", f"/support-access/{grant_id}/session", {"mode": "write"})
        async with client_for(app, host=f"{sub}.formalie.dev") as staff_http:
            staff = SecureClient(staff_http)
            _, tokens = await staff.request("POST", "/auth/support/redeem", body={"ticket": reply["data"]["ticket"]})
            staff.access_token = tokens["data"]["access_token"]
            refused = [{"field": "support", "message": "not_in_support_sessions"}]
            for method, path, body in (
                    ("POST", "/people", {"first_name": "Eve", "last_name": "Mallory", "email": "eve@example.org"}),
                    ("PUT", "/people/signup-link", {"enabled": True}),
                    ("POST", "/people/signup-link/new", None),
                    ("POST", "/api-tokens", {"name": "Mine"}),
                    ("POST", "/webhooks", {"name": "Mine", "url": "https://example.org/hook"}),
                    ("GET", "/settings/emails/sending", None),
                    ("PUT", "/settings/emails/sending/smtp", {"host": "mail.example.org"}),
                    ("PATCH", "/settings/security", {})):
                status, reply = await staff.request(method, path, body=body)
                assert (status, reply["error"]["details"]) == (403, refused), path
            status, reply = await staff.request("GET", "/people/signup-link")
            assert status == 200 and reply["data"]["link"] == "" and "enabled" in reply["data"]
            status, reply = await staff.request("POST", "/forms", body={"name": "Fixed by support"})
            assert status == 201, reply  # ordinary work still goes
            await staff.request("POST", "/auth/support/end")
    assert superuser.execute("SELECT count(*) FROM formaly.users WHERE tenant_id = %s", (tenant_id,)).fetchone()[0] == 1


# ── L2 and L4 ─────────────────────────────────────────────────────────────────────

async def test_an_account_without_a_password_costs_the_same(app, superuser, monkeypatch) -> None:  # noqa: ANN001
    from app.modules.auth import router as auth_router

    email = f"social-{uuid.uuid4().hex[:8]}@example.test"
    sub = await _new_workspace(app, email)
    superuser.execute("UPDATE formaly.users SET password_hash = NULL WHERE email = %s", (email,))
    checked: list[str | None] = []
    real = auth_router.verify_password
    monkeypatch.setattr(auth_router, "verify_password", lambda stored, value: checked.append(stored) or real(stored, value))
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": email, "password": DUMMY_HASH[:20]})
    assert reply["error"]["code"] == "FRM-AUTH-1002"
    assert checked == [DUMMY_HASH]  # the full hashing work, as for an unknown address


async def test_a_code_is_resent_only_on_its_own_workspace(app) -> None:  # noqa: ANN001
    email = "james.carter@carterpartners.test"  # an account in both seeded workspaces
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": email, "password": SEED_PASSWORD})
    challenge_id = reply["data"]["challenge_id"]
    since = len(SENT)
    async with client_for(app, host="samathtax.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/auth/otp/resend", body={"challenge_id": challenge_id})
    assert reply["error"]["code"] == "FRM-AUTH-1003"
    assert not _mails(since, email, "signin_code")

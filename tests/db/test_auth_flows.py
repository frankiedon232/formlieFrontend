"""Sign-in end to end against the seeded test database, through the encrypted channel, like the frontend does:
public profile, login → code → tokens, refresh rotation and reuse, logout, /me and permissions, lockouts,
sign-up → new workspace → ticket hand-off, forgotten password, find my workspace, cross-workspace refusals."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import psycopg
import pytest

from app.modules.emails.service import SENT
from tests.conftest import MemoryShipper, client_for
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

PASSWORD = "Formalie!2026"  # the mock's test password (seed)


@pytest.fixture(scope="session")
def seeded(migrated: None) -> None:  # noqa: ARG001
    import asyncio
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "seed_dev.py"), "--test"], check=True, cwd=root,
                   capture_output=True)
    _ = asyncio


@pytest.fixture
def app(db_settings, engines, seeded, redis):  # noqa: ANN001
    from app.modules.tenants.service import TenantDirectory
    from app.run import create_app

    return create_app(db_settings.model_copy(update={"rate_limit_ip_per_minute": 10_000}),
                      tenant_resolver=TenantDirectory(), request_log_shipper=MemoryShipper())


@pytest.fixture
async def remedy(app) -> AsyncIterator[SecureClient]:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        yield SecureClient(http)


def last_code(email: str) -> str:
    for message in reversed(SENT):
        if message["to"] == email:
            return str(message["values"]["code"])
    raise AssertionError(f"no email to {email}")


async def sign_in(client: SecureClient, email: str, password: str = PASSWORD) -> dict:
    status, reply = await client.request("POST", "/auth/login", body={"email": email, "password": password})
    assert status == 200, reply
    challenge = reply["data"]
    status, reply = await client.request("POST", "/auth/otp/verify",
                                         body={"challenge_id": challenge["challenge_id"], "code": last_code(email)})
    assert status == 200, reply
    client.access_token = reply["data"]["access_token"]
    return reply["data"]


def audit_actions(superuser: psycopg.Connection, email: str) -> list[str]:
    return [r[0] for r in superuser.execute(
        "SELECT action FROM formaly.audit_logs WHERE actor_email = %s ORDER BY occurred_at", (email,)).fetchall()]


# ── Public profile and subdomains ─────────────────────────────────────────────

async def test_public_profiles(app) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/tenants/public")
    profile = reply["data"]
    assert profile["mode"] == "tenant" and profile["name"] == "Remedy Legal" and profile["subdomain"] == "remedylegal"
    # Always email and password, Google, Facebook (owner, 2026-10-12), whatever the plan or an old saved `methods`
    assert profile["auth_providers"] == ["password", "google", "facebook"]
    assert profile["password_policy"] == {"min_length": 10, "lower": True, "upper": True, "number": True, "symbol": False}
    assert profile["website"] == "https://www.remedylegal.example" and profile["status"] == "active"
    async with client_for(app, host="samathtax.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/tenants/public")
    assert reply["data"]["auth_providers"] == ["password", "google", "facebook"]  # Starter too
    async with client_for(app, host="manage.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/tenants/public")
    assert reply["data"]["mode"] == "manage"
    assert reply["data"]["auth_providers"] == ["password", "google", "facebook"]  # sign-up: no Apple, no Microsoft
    async with client_for(app, host="oldco.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/tenants/public")
    assert reply["data"]["status"] == "suspended"


async def test_subdomain_availability(app) -> None:  # noqa: ANN001
    async with client_for(app, host="manage.formalie.dev") as http:
        client = SecureClient(http)
        for value, expected in (("remedylegal", "taken"), ("api", "reserved"), ("ab", "invalid"),
                                ("Bad_Name", "invalid"), ("brand-new-co", None)):
            _, reply = await client.request("GET", "/tenants/subdomain-availability", query={"subdomain": value})
            assert reply["data"] == {"available": expected is None, "reason": expected}, value


# ── Login, tokens, refresh, logout ────────────────────────────────────────────

async def test_login_refresh_reuse_and_logout(remedy: SecureClient, superuser) -> None:  # noqa: ANN001
    tokens = await sign_in(remedy, "admin@remedylegal.test")
    user = tokens["user"]
    assert user["role"] == "owner" and user["role_name"] == "Owner" and user["email"] == "admin@remedylegal.test"
    assert "settings.manage" in user["permissions"] and user["grants"]["forms.view"] == "all"
    assert tokens["tenant"]["subdomain"] == "remedylegal" and tokens["expires_in"] == 900
    assert len(tokens["tenant"]["id"]) == 27  # ids leave as references
    assert remedy.http.cookies.get("formalie_rt")

    status, me = await remedy.request("GET", "/me")
    assert status == 200 and me["data"]["email"] == "admin@remedylegal.test"

    old_cookie = remedy.http.cookies.get("formalie_rt")
    status, refreshed = await remedy.request("POST", "/auth/refresh")
    assert status == 200 and refreshed["data"]["access_token"] != tokens["access_token"]
    assert remedy.http.cookies.get("formalie_rt") != old_cookie

    # The old refresh token used again: the whole session ends
    remedy.http.cookies.set("formalie_rt", old_cookie, domain="remedylegal.formalie.dev", path="/api/v1/auth")
    status, reply = await remedy.request("POST", "/auth/refresh")
    assert (status, reply["error"]["code"]) == (401, "FRM-AUTH-1012")
    remedy.access_token = refreshed["data"]["access_token"]
    status, reply = await remedy.request("GET", "/me")
    assert reply["error"]["code"] == "FRM-AUTH-1011"
    assert {"auth.otp.sent", "auth.login.succeeded", "auth.session.revoked"} <= set(audit_actions(superuser, "admin@remedylegal.test"))

    await sign_in(remedy, "admin@remedylegal.test")
    status, reply = await remedy.request("POST", "/auth/logout")
    assert status == 200 and reply["data"] == {"signed_out": True}
    status, reply = await remedy.request("GET", "/me")
    assert reply["error"]["code"] == "FRM-AUTH-1011"


async def test_without_a_token_the_client_is_told_to_refresh(remedy: SecureClient) -> None:
    status, reply = await remedy.request("GET", "/me")
    assert (status, reply["error"]["code"]) == (401, "FRM-AUTH-1001")


async def test_member_holds_the_member_role(remedy: SecureClient) -> None:
    tokens = await sign_in(remedy, "staff@remedylegal.test")
    user = tokens["user"]
    assert user["role"] == "member" and "settings.manage" not in user["permissions"]
    assert user["grants"]["forms.edit"] == "own_shared" and "forms.view" in user["permissions"]


async def test_wrong_password_disabled_account_and_suspended_workspace(remedy: SecureClient, app, superuser) -> None:  # noqa: ANN001
    status, reply = await remedy.request("POST", "/auth/login", body={"email": "admin@remedylegal.test", "password": "nope"})
    assert (status, reply["error"]["code"]) == (401, "FRM-AUTH-1002")
    _, reply = await remedy.request("POST", "/auth/login", body={"email": "nobody@remedylegal.test", "password": "x"})
    assert reply["error"]["code"] == "FRM-AUTH-1002"  # the same answer for an unknown address
    _, reply = await remedy.request("POST", "/auth/login", body={"email": "marcus.reid@remedylegal.test", "password": PASSWORD})
    assert reply["error"]["code"] == "FRM-AUTH-1005"
    assert "auth.login.failed" in audit_actions(superuser, "admin@remedylegal.test")  # kept although the request failed
    assert "auth.login.blocked" in audit_actions(superuser, "marcus.reid@remedylegal.test")
    async with client_for(app, host="oldco.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": "a@b.test", "password": "x"})
    assert reply["error"]["code"] == "FRM-TEN-1002"


async def test_wrong_codes_count_down_then_lock(remedy: SecureClient, superuser) -> None:  # noqa: ANN001
    _, reply = await remedy.request("POST", "/auth/login", body={"email": "admin@samathtax.test", "password": PASSWORD})
    assert reply["error"]["code"] == "FRM-AUTH-1002"  # not an account of this workspace
    _, reply = await remedy.request("POST", "/auth/login", body={"email": "james.carter@carterpartners.test", "password": PASSWORD})
    challenge_id = reply["data"]["challenge_id"]
    for left in (4, 3, 2, 1):
        _, reply = await remedy.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": "000000"})
        assert reply["error"]["code"] == "FRM-AUTH-1003" and reply["error"]["details"] == [
            {"field": "attempts_left", "message": str(left)}]
    _, reply = await remedy.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": "000000"})
    assert reply["error"]["code"] == "FRM-AUTH-1004"
    actions = audit_actions(superuser, "james.carter@carterpartners.test")
    assert actions.count("auth.otp.failed") >= 4 and "auth.otp.locked" in actions


async def test_a_token_from_one_workspace_is_refused_on_another(remedy: SecureClient, app) -> None:  # noqa: ANN001
    await sign_in(remedy, "james.carter@carterpartners.test")
    async with client_for(app, host="samathtax.formalie.dev") as http:
        other = SecureClient(http)
        other.access_token = remedy.access_token
        status, reply = await other.request("GET", "/me")
    assert (status, reply["error"]["code"]) == (403, "FRM-TEN-1003")


# ── Sign-up, ticket hand-off, find my workspace ───────────────────────────────

async def test_signup_creates_a_workspace_and_hands_off_with_a_ticket(app, superuser) -> None:  # noqa: ANN001
    import uuid

    sub = f"acme{uuid.uuid4().hex[:8]}"
    email = f"founder@{sub}.test"
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        manage = SecureClient(http)
        status, reply = await manage.request("POST", "/auth/signup", body={
            "first_name": " Ada ", "last_name": "Lovelace", "email": email, "password": "Correct-Horse-9"})
        assert status == 200, reply
        challenge_id = reply["data"]["challenge_id"]
        _, reply = await manage.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": last_code(email)})
        assert reply["data"] == {"verified": True}
        _, reply = await manage.request("POST", "/auth/signup/complete", body={
            "challenge_id": challenge_id, "company_name": "Acme Labs", "subdomain": sub})
        url = reply["data"]["redirect_url"]
    assert url.startswith(f"https://{sub}.formalie.dev:2202/auth/welcome?ticket=")
    ticket = re.search(r"ticket=([^&]+)", url).group(1)  # type: ignore[union-attr]
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        fresh = SecureClient(http)
        status, reply = await fresh.request("POST", "/auth/exchange-ticket", body={"ticket": ticket})
        assert status == 200, reply
        assert reply["data"]["user"]["first_name"] == "Ada" and reply["data"]["user"]["role"] == "owner"
        _, again = await fresh.request("POST", "/auth/exchange-ticket", body={"ticket": ticket})
        assert again["error"]["code"] == "FRM-AUTH-1010"  # single use
    assert "workspace.created" in audit_actions(superuser, email)
    async with client_for(app, host="manage.formalie.dev") as http:
        manage = SecureClient(http)
        _, reply = await manage.request("GET", "/tenants/subdomain-availability", query={"subdomain": sub})
        assert reply["data"]["reason"] == "taken"


async def test_signup_only_on_manage(remedy: SecureClient) -> None:
    _, reply = await remedy.request("POST", "/auth/signup", body={
        "first_name": "A", "last_name": "B", "email": "a@b.test", "password": "Correct-Horse-9"})
    assert reply["error"]["code"] == "FRM-PERM-1001"


async def test_find_my_workspace(app) -> None:  # noqa: ANN001
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        manage = SecureClient(http)
        email = "james.carter@carterpartners.test"
        _, reply = await manage.request("POST", "/tenants/find-workspace", body={"email": email})
        assert reply["data"]["masked_destination"].endswith("@carterpartners.test")
        _, reply = await manage.request("POST", "/tenants/find-workspace/verify", body={
            "challenge_id": reply["data"]["challenge_id"], "code": last_code(email)})
    assert [w["subdomain"] for w in reply["data"]] == ["remedylegal", "samathtax"]
    assert reply["data"][0]["url"] == ("https://remedylegal.formalie.dev:2202/auth/login?email="
                                       "james.carter%40carterpartners.test")


# ── Forgotten password ─────────────────────────────────────────────────────────

async def test_forgot_and_reset_password(app) -> None:  # noqa: ANN001
    async with client_for(app, host="samathtax.formalie.dev") as http:
        client = SecureClient(http)
        email = "admin@samathtax.test"
        _, reply = await client.request("POST", "/auth/password/forgot", body={"email": email})
        challenge_id = reply["data"]["challenge_id"]
        code = last_code(email)
        _, weak = await client.request("POST", "/auth/password/reset", body={"challenge_id": challenge_id, "code": code,
                                                                            "password": "short"})
        assert weak["error"]["code"] == "FRM-AUTH-1007"
        assert {"field": "password", "message": "min_length:10"} in weak["error"]["details"]
        _, reply = await client.request("POST", "/auth/password/reset", body={"challenge_id": challenge_id, "code": code,
                                                                             "password": "New-Password-77"})
        assert reply["data"] == {"reset": True}
        await sign_in(client, email, "New-Password-77")
        _, reply = await client.request("POST", "/auth/password/forgot", body={"email": "ghost@samathtax.test"})
        assert "challenge_id" in reply["data"]  # the same answer for an unknown address
    # Back to the seed password for the other tests
    async with client_for(app, host="samathtax.formalie.dev") as http:
        client = SecureClient(http)
        _, reply = await client.request("POST", "/auth/password/forgot", body={"email": email})
        await client.request("POST", "/auth/password/reset", body={
            "challenge_id": reply["data"]["challenge_id"], "code": last_code(email), "password": PASSWORD})


async def test_login_is_rate_limited(remedy: SecureClient) -> None:
    statuses = []
    for _ in range(11):
        status, _ = await remedy.request("POST", "/auth/login", body={"email": "nobody@x.test", "password": "x"})
        statuses.append(status)
    assert statuses[-1] == 429


# ── Sign-up: the workspaces an email already has; a password tried on a social account (owner, 2026-10-12) ─────

async def _new_workspace(app, email: str, password: str = "Correct-Horse-9") -> str:  # noqa: ANN001
    """Signs up a fresh workspace for this email → its subdomain."""
    import uuid

    sub = f"ws{uuid.uuid4().hex[:8]}"
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        manage = SecureClient(http)
        _, reply = await manage.request("POST", "/auth/signup", body={
            "first_name": "Ada", "last_name": "Lovelace", "email": email, "password": password})
        challenge_id = reply["data"]["challenge_id"]
        await manage.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": last_code(email)})
        _, reply = await manage.request("POST", "/auth/signup/complete", body={
            "challenge_id": challenge_id, "company_name": "Social Co", "subdomain": sub})
        assert "redirect_url" in reply["data"], reply
    return sub


async def test_signup_lists_the_emails_workspaces_only_once_verified(app, remedy: SecureClient) -> None:  # noqa: ANN001
    email = "james.carter@carterpartners.test"  # has remedylegal and samathtax
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        manage = SecureClient(http)
        _, reply = await manage.request("POST", "/auth/signup", body={
            "first_name": "James", "last_name": "Carter", "email": email, "password": "Correct-Horse-9"})
        challenge_id = reply["data"]["challenge_id"]
        _, before = await manage.request("GET", "/auth/signup/workspaces", query={"challenge_id": challenge_id})
        assert before["error"]["code"] == "FRM-AUTH-1003"  # not before the code: no discovery for strangers
        await manage.request("POST", "/auth/otp/verify", body={"challenge_id": challenge_id, "code": last_code(email)})
        status, reply = await manage.request("GET", "/auth/signup/workspaces", query={"challenge_id": challenge_id})
        assert status == 200, reply
        assert [w["subdomain"] for w in reply["data"]] == ["remedylegal", "samathtax"]
        assert reply["data"][0]["url"].endswith("/auth/login?email=james.carter%40carterpartners.test")
        _, unknown = await manage.request("GET", "/auth/signup/workspaces", query={"challenge_id": "nope"})
        assert unknown["error"]["code"] == "FRM-AUTH-1003"
    _, elsewhere = await remedy.request("GET", "/auth/signup/workspaces", query={"challenge_id": challenge_id})
    assert elsewhere["error"]["code"] == "FRM-AUTH-1003"  # manage.* only


async def test_password_tried_on_a_social_account_answers_the_same_and_emails_the_owner(app, superuser) -> None:  # noqa: ANN001
    import uuid

    email = f"social-{uuid.uuid4().hex[:8]}@example.test"
    sub = await _new_workspace(app, email)
    # This account came in with Facebook: no password, one linked identity
    superuser.execute("UPDATE formaly.users SET password_hash = NULL WHERE email = %s", (email,))
    superuser.execute(
        "INSERT INTO formaly.user_identities (id, tenant_id, organisation_id, user_id, provider, provider_user_id, email,"
        " created_by) SELECT gen_random_uuid(), tenant_id, organisation_id, id, 'facebook', %s, email, id"
        " FROM formaly.users WHERE email = %s", (f"fb-{uuid.uuid4().hex}", email))
    sent_before = len(SENT)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        client = SecureClient(http)
        status, reply = await client.request("POST", "/auth/login", body={"email": email, "password": "Guess-123"})
        assert (status, reply["error"]["code"]) == (401, "FRM-AUTH-1002")  # the same answer as any wrong password
        _, again = await client.request("POST", "/auth/login", body={"email": email, "password": "Guess-456"})
        assert again["error"]["code"] == "FRM-AUTH-1002"
    notices = [m for m in SENT[sent_before:] if m["to"] == email and m["values"].get("reason") == "password_social"]
    assert len(notices) == 1  # at most once an hour
    assert "Facebook" in notices[0]["text"] and "Guess-123" not in notices[0]["text"]
    assert f"https://{sub}.formalie.dev" in notices[0]["text"]  # the way back to the sign-in page
    assert "auth.login.failed" in audit_actions(superuser, email)


async def test_no_notice_for_a_wrong_password_on_an_account_that_has_one(app) -> None:  # noqa: ANN001
    import uuid

    email = f"plain-{uuid.uuid4().hex[:8]}@example.test"
    sub = await _new_workspace(app, email)
    sent_before = len(SENT)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/auth/login", body={"email": email, "password": "Guess-123"})
    assert reply["error"]["code"] == "FRM-AUTH-1002"
    assert not [m for m in SENT[sent_before:] if m["values"].get("reason") == "password_social"]

"""Social sign-in end to end (Google, Facebook) against the seeded test database. The providers are an
httpx.MockTransport: nothing leaves the machine, and the keys are fixed test values, never the ones in .env."""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.modules.auth import oauth
from tests.conftest import client_for
from tests.db.test_auth_flows import app, audit_actions, last_code, seeded  # noqa: F401  (fixtures)
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

TEST_KEYS = {
    "oauth_google_client_id": "test-google-client.apps.example", "oauth_google_client_secret": SecretStr("g-secret"),
    "oauth_facebook_client_id": "1000000000000001", "oauth_facebook_client_secret": SecretStr("f-secret"),
    "oauth_redirect_base": None,
}


class FakeProviders:
    """Answers the token and profile calls like the providers do; `profile` is who signs in next."""

    def __init__(self) -> None:
        self.profile: dict[str, Any] = {}
        self.id_token: dict[str, Any] | None = None
        self.fail = False
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.fail:
            return httpx.Response(500, json={"error": "server_error"})
        if request.method == "POST":
            body = {"access_token": "at-123", "token_type": "Bearer"}
            if self.id_token is not None:
                payload = base64.urlsafe_b64encode(json.dumps(self.id_token).encode()).rstrip(b"=").decode()
                body["id_token"] = f"eyJhbGciOiJub25lIn0.{payload}.sig"
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=self.profile)


@pytest.fixture
def providers(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeProviders]:
    fake = FakeProviders()
    settings = get_settings().model_copy(update=TEST_KEYS)
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth, "transport", httpx.MockTransport(fake))
    yield fake


async def start(http: httpx.AsyncClient, provider: str, intent: str = "login") -> httpx.Response:
    return await http.get(f"/api/v1/auth/oauth/{provider}/start", params={"intent": intent})


async def round_trip(app: Any, http: httpx.AsyncClient, provider: str, intent: str = "login",
                     **callback: str) -> dict[str, list[str]] | str:
    """start → (the provider) → callback on manage.*; returns where the browser is sent at the end."""
    response = await start(http, provider, intent)
    assert response.status_code == 302
    location = response.headers["location"]
    if urlsplit(location).netloc.endswith("formalie.dev") or not location.startswith("https://"):
        return location  # refused before reaching the provider
    state = parse_qs(urlsplit(location).query)["state"][0]
    async with client_for(app, host="manage.formalie.dev") as manage:
        back = await manage.get(f"/api/v1/auth/oauth/{provider}/callback",
                                params={"state": state, **({"code": "c-1"} | callback)})
    assert back.status_code == 302
    return back.headers["location"]


def query(location: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(location).query).items()}


# ── Start ──────────────────────────────────────────────────────────────────────

async def test_start_sends_the_browser_to_the_provider(app, providers) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        response = await start(http, "google")
    url = urlsplit(response.headers["location"])
    params = query(response.headers["location"])
    assert (url.netloc, url.path) == ("accounts.google.com", "/o/oauth2/v2/auth")
    assert params["client_id"] == "test-google-client.apps.example" and params["response_type"] == "code"
    assert params["redirect_uri"] == "https://manage.formalie.dev/api/v1/auth/oauth/google/callback"
    assert params["code_challenge_method"] == "S256" and len(params["state"]) >= 40
    assert "client_secret" not in params
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        response = await start(http, "facebook", "signup")
    params = query(response.headers["location"])
    assert params["redirect_uri"] == "https://manage.formalie.dev:2202/api/v1/auth/oauth/facebook/callback"
    assert "code_challenge" not in params and params["scope"] == "email public_profile"


async def test_start_refusals(app, providers, monkeypatch) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        # Google and Facebook in every workspace (owner, 2026-10-12), whatever its old saved methods
        assert urlsplit((await start(http, "facebook")).headers["location"]).netloc == "www.facebook.com"
        # Sign-up only on manage.*
        assert (await start(http, "google", "signup")).headers["location"] == \
            "/auth/signup?oauth=error&provider=google&code=FRM-PERM-1001"
        # Microsoft is no button any more: its accounts come through the workspace's single sign-on
        assert (await start(http, "microsoft")).headers["location"] == \
            "/auth/login?oauth=unavailable&provider=microsoft"
    async with client_for(app, host="manage.formalie.dev") as http:
        assert (await start(http, "microsoft", "signup")).headers["location"] == \
            "/auth/signup?oauth=unavailable&provider=microsoft"
    async with client_for(app, host="samathtax.formalie.dev") as http:
        # Starter: Google too (no plan feature for it any more)
        assert urlsplit((await start(http, "google")).headers["location"]).netloc == "accounts.google.com"
    async with client_for(app, host="oldco.formalie.dev") as http:
        assert query((await start(http, "google")).headers["location"])["code"] == "FRM-TEN-1002"
    settings = get_settings().model_copy(update={**TEST_KEYS, "oauth_google_client_id": None})
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        assert (await start(http, "google")).headers["location"] == "/auth/login?oauth=unavailable&provider=google"
        assert (await start(http, "apple")).headers["location"] == "/auth/login?oauth=unavailable&provider=apple"


# ── Sign-in ────────────────────────────────────────────────────────────────────

async def test_google_sign_in_still_asks_for_the_code(app, providers, superuser) -> None:  # noqa: ANN001
    email = "admin@remedylegal.test"
    subject = f"g-{uuid.uuid4().hex}"
    providers.profile = {"sub": subject, "email": email.upper(), "email_verified": True, "given_name": "Ada"}
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        location = await round_trip(app, http, "google")
        assert isinstance(location, str) and location.startswith("https://remedylegal.formalie.dev/auth/login?")
        params = query(location)
        assert params["provider"] == "google" and len(params["oauth_challenge"]) == 27  # a reference, not the id

        client = SecureClient(http)
        status, reply = await client.request("GET", "/auth/oauth/challenge", query={"challenge_id": params["oauth_challenge"]})
        assert status == 200, reply
        data = reply["data"]
        assert (data["purpose"], data["provider"], data["email"]) == ("login", "google", email)
        assert data["challenge"]["challenge_id"] == params["oauth_challenge"] and data["challenge"]["channel"] == "email"

        status, reply = await client.request("POST", "/auth/otp/verify", body={
            "challenge_id": params["oauth_challenge"], "code": last_code(email)})
        assert status == 200, reply
        assert reply["data"]["user"]["email"] == email
    method = superuser.execute("SELECT method FROM formaly.user_sessions s JOIN formaly.users u ON u.id = s.user_id "
                               "WHERE u.email = %s ORDER BY s.started_at DESC LIMIT 1", (email,)).fetchone()
    assert method == ("google",)
    linked = superuser.execute("SELECT i.email FROM formaly.user_identities i WHERE i.provider = 'google' "
                               "AND i.provider_user_id = %s AND i.deleted_at IS NULL", (subject,)).fetchall()
    assert linked == [(email,)]
    assert {"auth.otp.sent", "auth.login.succeeded"} <= set(audit_actions(superuser, email))

    # Next time the linked Google account is enough, even after its address changed at Google
    providers.profile = {"sub": subject, "email": "ada.new@elsewhere.example", "email_verified": True}
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        location = await round_trip(app, http, "google")
    assert "oauth_challenge" in query(location)  # type: ignore[arg-type]


async def test_sign_in_refusals(app, providers, superuser) -> None:  # noqa: ANN001
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        stranger = f"nobody-{uuid.uuid4().hex[:6]}@example.test"
        providers.profile = {"sub": "g-stranger", "email": stranger, "email_verified": True}
        location = await round_trip(app, http, "google")
        assert location == ("https://remedylegal.formalie.dev/auth/login?oauth=error&provider=google&code=FRM-AUTH-1022")
        assert audit_actions(superuser, stranger) == ["auth.login.failed"]  # recorded, though refused

        providers.profile = {"sub": "g-unverified", "email": "admin@remedylegal.test", "email_verified": False}
        assert query(await round_trip(app, http, "google"))["code"] == "FRM-AUTH-1021"  # type: ignore[arg-type]

        providers.profile = {"sub": "g-disabled", "email": "marcus.reid@remedylegal.test", "email_verified": True}
        assert query(await round_trip(app, http, "google"))["code"] == "FRM-AUTH-1005"  # type: ignore[arg-type]

        providers.fail = True
        assert query(await round_trip(app, http, "google"))["code"] == "FRM-AUTH-1023"  # type: ignore[arg-type]
        providers.fail = False

        location = await round_trip(app, http, "google", error="access_denied")
        assert location == "https://remedylegal.formalie.dev/auth/login?oauth=cancelled&provider=google"

    async with client_for(app, host="manage.formalie.dev") as manage:
        # A made-up or used state: nothing to go back to
        back = await manage.get("/api/v1/auth/oauth/google/callback", params={"state": "made-up", "code": "c"})
    assert back.headers["location"] == "/auth/login?oauth=error&provider=google&code=FRM-AUTH-1023"


async def test_a_challenge_stays_on_its_workspace(app, providers) -> None:  # noqa: ANN001
    providers.profile = {"sub": f"g-{uuid.uuid4().hex}", "email": "staff@remedylegal.test", "email_verified": True}
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        ref = query(await round_trip(app, http, "google"))["oauth_challenge"]  # type: ignore[arg-type]
    for host in ("samathtax.formalie.dev", "manage.formalie.dev"):
        async with client_for(app, host=host) as http:
            _, reply = await SecureClient(http).request("GET", "/auth/oauth/challenge", query={"challenge_id": ref})
        assert reply["error"]["code"] == "FRM-AUTH-1003", host
    async with client_for(app, host="remedylegal.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/auth/oauth/challenge", query={
            "challenge_id": str(uuid.uuid4())})  # a raw id is not a reference
    assert reply["success"] is False


# ── Sign-up ────────────────────────────────────────────────────────────────────

async def test_facebook_sign_up_skips_the_code_and_links_the_owner(app, providers, superuser) -> None:  # noqa: ANN001
    sub = f"fb{uuid.uuid4().hex[:8]}"
    email = f"founder@{sub}.test"
    providers.profile = {"id": "1234567890", "email": email, "first_name": "Grace", "last_name": "Hopper"}
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        location = await round_trip(app, http, "facebook", "signup")
        assert isinstance(location, str) and location.startswith("https://manage.formalie.dev:2202/auth/signup?")
        ref = query(location)["oauth_challenge"]
        manage = SecureClient(http)
        _, reply = await manage.request("GET", "/auth/oauth/challenge", query={"challenge_id": ref})
        assert {k: reply["data"][k] for k in ("purpose", "provider", "email", "first_name", "last_name")} == {
            "purpose": "signup", "provider": "facebook", "email": email, "first_name": "Grace", "last_name": "Hopper"}
        status, reply = await manage.request("POST", "/auth/signup/complete", body={
            "challenge_id": ref, "company_name": "Hopper Labs", "subdomain": sub})
        assert status == 200, reply
        assert reply["data"]["redirect_url"].startswith(f"https://{sub}.formalie.dev:2202/auth/welcome?ticket=")
    # Facebook's profile call carries the app secret proof, never the secret
    profile_call = next(c for c in providers.calls if c.method == "GET")
    assert "appsecret_proof" in profile_call.url.params and "f-secret" not in str(profile_call.url)

    row = superuser.execute("SELECT u.password_hash, i.provider, i.provider_user_id FROM formaly.users u "
                            "JOIN formaly.user_identities i ON i.user_id = u.id WHERE u.email = %s", (email,)).fetchone()
    assert row == (None, "facebook", "1234567890")
    # A new workspace saves no ways in (owner, 2026-10-12): every sign-in page offers them all
    methods = superuser.execute("SELECT s.value ? 'methods' FROM formaly.workspace_settings s "
                                "JOIN platform.tenants t ON t.id = s.tenant_id WHERE t.subdomain = %s "
                                "AND s.section = 'signin'", (sub,)).fetchone()
    assert methods == (False,)


# ── Microsoft: no social sign-in any more ─────────────────────────────────────

async def test_a_microsoft_callback_is_refused(app, providers, redis) -> None:  # noqa: ANN001
    """Even with a state saved for Microsoft (before the change), the callback never reaches a provider."""
    import hashlib

    key = "s" * 43
    await redis.set(oauth.STATE_PREFIX + hashlib.sha256(key.encode()).hexdigest(), json.dumps(
        {"provider": "microsoft", "intent": "login", "host": "remedylegal.formalie.dev", "verifier": None,
         "subdomain": "remedylegal"}), ex=60)
    async with client_for(app, host="manage.formalie.dev") as manage:
        back = await manage.get("/api/v1/auth/oauth/microsoft/callback", params={"state": key, "code": "c"})
    assert back.headers["location"] == "/auth/login?oauth=error&provider=microsoft&code=FRM-AUTH-1023"
    assert providers.calls == [] and "microsoft" not in oauth.PROVIDERS


def test_redirect_uri(monkeypatch) -> None:  # noqa: ANN001
    settings = get_settings().model_copy(update={"oauth_redirect_base": "https://login.formalie.example/"})
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)
    assert oauth.redirect_uri("google", "acme.formalie.dev", "tenant") == \
        "https://login.formalie.example/api/v1/auth/oauth/google/callback"




async def test_social_sign_in_in_every_plan(app, providers, superuser) -> None:  # noqa: ANN001
    """Owner, 2026-10-12: Google and Facebook in every plan. On Starter the Owner who signed up with Facebook keeps
    using it, and someone else with an account there signs in with Facebook too (their account gets linked)."""
    sub = f"st{uuid.uuid4().hex[:8]}"
    email = f"founder@{sub}.test"
    providers.profile = {"id": "fb-founder-" + sub, "email": email, "first_name": "Kay", "last_name": "Lee"}
    async with client_for(app, host="manage.formalie.dev") as http:
        ref = query(await round_trip(app, http, "facebook", "signup"))["oauth_challenge"]  # type: ignore[arg-type]
        _, reply = await SecureClient(http).request("POST", "/auth/signup/complete", body={
            "challenge_id": ref, "company_name": "Starter Co", "subdomain": sub})
        assert reply["success"], reply
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        client = SecureClient(http)
        _, profile = await client.request("GET", "/tenants/public")
        assert profile["data"]["auth_providers"] == ["password", "google", "facebook"]
        location = await round_trip(app, http, "facebook")
        ref = query(location)["oauth_challenge"]  # type: ignore[arg-type]
        await client.request("GET", "/auth/oauth/challenge", query={"challenge_id": ref})
        status, reply = await client.request("POST", "/auth/otp/verify", body={"challenge_id": ref,
                                                                                "code": last_code(email)})
        assert status == 200 and reply["data"]["user"]["role"] == "owner"

        # Someone else whose address matches and who never linked Facebook: in as well, on Starter
        tenant = superuser.execute("SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s",
                                   (sub,)).fetchone()
        superuser.execute("SELECT set_config('app.tenant_id', %s, false), set_config('app.organisation_id', %s, false)",
                          (str(tenant[0]), str(tenant[1])))
        role = superuser.execute("SELECT id FROM formaly.roles WHERE tenant_id = %s AND built_in = 'member'",
                                 (tenant[0],)).fetchone()[0]
        superuser.execute("INSERT INTO formaly.users (id, tenant_id, organisation_id, email, first_name, last_name, "
                          "status, role_id) VALUES (%s, %s, %s, %s, 'Mo', 'Ng', 'active', %s)",
                          (uuid.uuid4(), tenant[0], tenant[1], f"mo@{sub}.test", role))
        providers.profile = {"id": "fb-mo-" + sub, "email": f"mo@{sub}.test", "first_name": "Mo"}
        assert "oauth_challenge" in query(await round_trip(app, http, "facebook"))  # type: ignore[arg-type]
    linked = superuser.execute("SELECT count(*) FROM formaly.user_identities WHERE provider = 'facebook' "
                               "AND provider_user_id = %s", ("fb-mo-" + sub,)).fetchone()
    assert linked == (1,)


async def test_an_old_saved_methods_list_changes_nothing(app, providers, superuser) -> None:  # noqa: ANN001
    """A workspace whose stored sign-in settings still say `methods: ['password']` (saved before 2026-10-12) offers
    Google and Facebook, takes a Google sign-in for an existing account and a password sign-in, never FRM-AUTH-1008;
    its settings answer without `methods`."""
    sub = f"old{uuid.uuid4().hex[:8]}"
    email = f"owner@{sub}.test"
    password = "Correct-Horse-9"
    async with client_for(app, host="manage.formalie.dev") as http:
        manage = SecureClient(http)
        _, reply = await manage.request("POST", "/auth/signup", body={
            "first_name": "Ola", "last_name": "Nwosu", "email": email, "password": password})
        challenge = reply["data"]["challenge_id"]
        await manage.request("POST", "/auth/otp/verify", body={"challenge_id": challenge, "code": last_code(email)})
        _, reply = await manage.request("POST", "/auth/signup/complete", body={
            "challenge_id": challenge, "company_name": "Old Settings Co", "subdomain": sub})
        assert reply["success"], reply
    superuser.execute("UPDATE formaly.workspace_settings s SET value = s.value || %s::jsonb FROM platform.tenants t "
                      "WHERE t.id = s.tenant_id AND t.subdomain = %s AND s.section = 'signin'",
                      ('{"methods": ["password"]}', sub))
    stored = superuser.execute("SELECT s.value -> 'methods' FROM formaly.workspace_settings s JOIN platform.tenants t "
                               "ON t.id = s.tenant_id WHERE t.subdomain = %s AND s.section = 'signin'", (sub,)).fetchone()
    assert stored == (["password"],)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        client = SecureClient(http)
        _, profile = await client.request("GET", "/tenants/public")
        assert profile["data"]["auth_providers"] == ["password", "google", "facebook"]
        status, reply = await client.request("POST", "/auth/login", body={"email": email, "password": password})
        assert status == 200 and reply["data"]["challenge_id"], reply  # never FRM-AUTH-1008
        status, reply = await client.request("POST", "/auth/otp/verify", body={
            "challenge_id": reply["data"]["challenge_id"], "code": last_code(email)})
        assert status == 200, reply
        client.access_token = reply["data"]["access_token"]
        _, reply = await client.request("GET", "/settings/signin")
        assert "methods" not in reply["data"] and reply["data"]["code"]["expiry_minutes"] == 5
        _, reply = await client.request("GET", "/settings")
        assert "methods" not in reply["data"]["signin"]

        providers.profile = {"sub": f"g-{sub}", "email": email, "email_verified": True, "given_name": "Ola"}
        ref = query(await round_trip(app, http, "google"))["oauth_challenge"]  # type: ignore[arg-type]
        await client.request("GET", "/auth/oauth/challenge", query={"challenge_id": ref})
        status, reply = await client.request("POST", "/auth/otp/verify", body={"challenge_id": ref,
                                                                                "code": last_code(email)})
        assert status == 200 and reply["data"]["user"]["email"] == email, reply


def test_redirect_uri_is_always_the_registered_manage_address(monkeypatch) -> None:  # noqa: ANN001
    """Starting on the bare root domain (or www, or a workspace) still sends the provider to manage.* (owner,
    2026-10-12: a sign-up started on https://formalie.dev:2202 got Google's Error 400 redirect_uri_mismatch)."""
    settings = get_settings().model_copy(update={"oauth_redirect_base": None, "root_domain": "formalie.dev"})
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth, "host_port", lambda: ":2202")
    for host, kind in (("formalie.dev:2202", "manage"), ("www.formalie.dev:2202", "manage"),
                       ("manage.formalie.dev:2202", "manage"), ("acme.formalie.dev:2202", "tenant")):
        assert oauth.redirect_uri("google", host, kind) == \
            "https://manage.formalie.dev:2202/api/v1/auth/oauth/google/callback", host

"""Social sign-in (Google, Facebook) through Formalie's own app at each provider (03-DECISIONS 2026-10-11).

Microsoft is not a social button (owner, 2026-10-12): Microsoft accounts come in only through a workspace's single
sign-on (Entra ID, app/modules/sso). /auth/oauth/microsoft/start answers like any unknown provider.

The browser goes to /auth/oauth/{provider}/start, then to the provider, which sends it back to one fixed address,
/auth/oauth/{provider}/callback on manage.* (providers don't take wildcard subdomains). What the start knew (the
provider, sign-up or sign-in, the workspace, the page to go back to, the PKCE verifier) waits in Redis under the
random `state`, read once. The callback swaps the code for the person's profile here, server to server: only a
verified email address is accepted. Social sign-in proves who someone is; it never skips the 6-digit code (owner).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from urllib.parse import urlencode

import httpx

from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.errors import FrmError
from app.modules.tenants.router import host_port

log = logging.getLogger("formalie.auth.oauth")

STATE_PREFIX = "fm:v1:auth:oauth:"
STATE_TTL_S = 600
TIMEOUT_S = 10.0

# Tests swap in an httpx.MockTransport here; never set in the running app.
transport: httpx.AsyncBaseTransport | None = None


@dataclass(frozen=True, slots=True)
class Provider:
    authorize_url: str
    token_url: str
    profile_url: str
    scope: str
    pkce: bool


PROVIDERS: dict[str, Provider] = {
    "google": Provider("https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token",
                       "https://openidconnect.googleapis.com/v1/userinfo", "openid email profile", True),
    "facebook": Provider("https://www.facebook.com/dialog/oauth", "https://graph.facebook.com/oauth/access_token",
                         "https://graph.facebook.com/me", "email public_profile", False),
}


@dataclass(slots=True)
class OAuthState:
    provider: str
    intent: str  # login · signup
    host: str  # the host (and port) the browser came from: the page to go back to
    verifier: str | None = None
    subdomain: str | None = None  # sign-in: the workspace


@dataclass(frozen=True, slots=True)
class Profile:
    subject: str
    email: str
    first_name: str
    last_name: str


def credentials(provider: str) -> tuple[str, str] | None:
    """Formalie's client id and secret for this provider, or None when it isn't set up (the button is unavailable)."""
    if provider not in PROVIDERS:
        return None
    settings = get_settings()
    client_id = getattr(settings, f"oauth_{provider}_client_id") or ""
    secret = getattr(settings, f"oauth_{provider}_client_secret")
    value = secret.get_secret_value() if secret is not None else ""
    return (client_id.strip(), value.strip()) if client_id.strip() and value.strip() else None


def redirect_uri(provider: str, host: str | None, host_kind: str | None) -> str:
    """The callback address registered at the provider."""
    settings = get_settings()
    base = (settings.oauth_redirect_base or "").rstrip("/")
    if not base:
        # Always manage.*, the one address registered at the providers, whichever host the person started on
        # (also the bare root domain or www, which open the manage pages too: owner, 2026-10-12, a sign-up started on
        # https://formalie.dev:2202 sent Google an unregistered address, Error 400 redirect_uri_mismatch)
        base = f"https://{settings.manage_subdomain}.{settings.root_domain}{host_port()}"
    return f"{base}{settings.api_prefix}/auth/oauth/{provider}/callback"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


async def begin(state: OAuthState, uri: str) -> str:
    """Saves the state and returns the provider's sign-in address."""
    client_id, _ = credentials(state.provider) or ("", "")
    provider = PROVIDERS[state.provider]
    key = secrets.token_urlsafe(32)
    params = {"client_id": client_id, "redirect_uri": uri, "response_type": "code", "scope": provider.scope, "state": key}
    if provider.pkce:
        state.verifier = secrets.token_urlsafe(48)
        params |= {"code_challenge": _b64(hashlib.sha256(state.verifier.encode()).digest()),
                   "code_challenge_method": "S256"}
    if state.provider == "google":
        params["prompt"] = "select_account"  # someone signed in to two accounts picks one
    await get_redis().set(STATE_PREFIX + hashlib.sha256(key.encode()).hexdigest(), json.dumps(asdict(state)),
                          ex=STATE_TTL_S)
    return f"{provider.authorize_url}?{urlencode(params)}"


async def take_state(key: str | None) -> OAuthState | None:
    """Single use: read and removed at once (GETDEL)."""
    if not key or len(key) > 128:
        return None
    raw = await get_redis().getdel(STATE_PREFIX + hashlib.sha256(key.encode()).hexdigest())
    return OAuthState(**json.loads(raw)) if raw else None


async def fetch_profile(provider_name: str, code: str, state: OAuthState, uri: str) -> Profile:
    """Code → tokens → the person. FRM-AUTH-1023 when the provider fails; FRM-AUTH-1021 without a verified email."""
    provider = PROVIDERS[provider_name]
    client_id, secret = credentials(provider_name) or ("", "")
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": uri,
            "client_id": client_id, "client_secret": secret}
    if state.verifier:
        form["code_verifier"] = state.verifier
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S, transport=transport) as http:
            token_reply = await http.post(provider.token_url, data=form, headers={"accept": "application/json"})
            token_reply.raise_for_status()
            tokens = token_reply.json()
            access = tokens["access_token"]
            if provider_name == "facebook":
                proof = hmac.new(secret.encode(), access.encode(), hashlib.sha256).hexdigest()
                reply = await http.get(provider.profile_url, params={
                    "fields": "id,email,first_name,last_name", "access_token": access, "appsecret_proof": proof})
            else:
                reply = await http.get(provider.profile_url, headers={"authorization": f"Bearer {access}"})
            reply.raise_for_status()
            info = reply.json()
    except (httpx.HTTPError, KeyError, ValueError) as error:
        # Never the reply itself: it can hold tokens
        log.warning("oauth exchange failed", extra={"provider": provider_name, "error": type(error).__name__})
        raise FrmError("FRM-AUTH-1023") from None
    finally:
        form.pop("client_secret", None)

    if provider_name == "facebook":
        # Facebook only shares an address the person confirmed
        subject, email, verified = str(info.get("id") or ""), info.get("email"), bool(info.get("email"))
    else:
        subject, email, verified = str(info.get("sub") or ""), info.get("email"), info.get("email_verified") is True
    if not subject:
        raise FrmError("FRM-AUTH-1023")
    if not email or not verified or "@" not in str(email):
        raise FrmError("FRM-AUTH-1021")
    first = str(info.get("given_name") or info.get("first_name") or "").strip()[:60]
    last = str(info.get("family_name") or info.get("last_name") or "").strip()[:60]
    return Profile(subject=subject[:255], email=str(email).strip().lower(), first_name=first, last_name=last)

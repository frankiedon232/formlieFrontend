"""The two single sign-on flows (B11): SAML 2.0 with python3-saml (xmlsec) and OpenID Connect with Authlib.

Start: what the start knew (the workspace, the host the browser came from, the SAML request id or the OIDC PKCE
verifier and nonce) waits in Redis under a random key (`RelayState` for SAML, `state` for OIDC), read once (GETDEL),
for 10 minutes. The answer is checked strictly:
- SAML: python3-saml in strict mode (signature over the response or the assertion with the provider's certificate,
  audience = this workspace's entity id, destination = this workspace's ACS address, the time window, InResponseTo =
  the request we sent). Deprecated algorithms (SHA-1) are refused.
- OIDC: the code is exchanged server to server (PKCE, the client secret), the ID token's signature is checked with the
  provider's published keys (RSA / ECDSA only), with issuer, audience, nonce and expiry.
The address comes from the provider; app/modules/auth/router.py `sso_login` decides who may come in.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import TenantInfo
from app.core.errors import FrmError
from app.core.security.fernet_tokens import decrypt_secret
from app.modules.auth.oauth import Profile
from app.modules.sso import service as sso
from app.modules.sso.models import SsoConnection

log = logging.getLogger("formalie.sso")

STATE_PREFIX = "fm:v1:auth:sso:"
STATE_TTL_S = 600
ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"]
SAML_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
SAML_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
NAMEID_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
EMAIL_ATTRIBUTES = ("email", "mail", "emailAddress", "Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                    "urn:oid:0.9.2342.19200300.100.1.3")
FIRST_ATTRIBUTES = ("firstName", "givenName", "first_name", "given_name",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname", "urn:oid:2.5.4.42")
LAST_ATTRIBUTES = ("lastName", "surname", "sn", "last_name", "family_name",
                   "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname", "urn:oid:2.5.4.4")


@dataclass(slots=True)
class SsoState:
    protocol: str
    tenant_id: str
    subdomain: str
    host: str
    request_id: str | None = None
    verifier: str | None = None
    nonce: str | None = None


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


async def _save(key: str, state: SsoState) -> None:
    await get_redis().set(STATE_PREFIX + hashlib.sha256(key.encode()).hexdigest(), json.dumps(asdict(state)),
                          ex=STATE_TTL_S)


async def take_state(key: str | None) -> SsoState | None:
    """Single use: read and removed at once."""
    if not key or len(key) > 128:
        return None
    raw = await get_redis().getdel(STATE_PREFIX + hashlib.sha256(key.encode()).hexdigest())
    return SsoState(**json.loads(raw)) if raw else None


# ── SAML ──────────────────────────────────────────────────────────────────────────

def _pem_body(value: str | None) -> str:
    return "".join(line for line in (value or "").splitlines() if "-----" not in line).strip()


def saml_settings(subdomain: str, idp: dict[str, Any] | None) -> dict[str, Any]:
    settings = get_settings()
    sp = sso.service_provider(subdomain)
    cert = settings.saml_sp_cert.get_secret_value() if settings.saml_sp_cert else ""
    key = settings.saml_sp_key.get_secret_value() if settings.saml_sp_key else ""
    signed = bool(cert and key)
    out: dict[str, Any] = {
        "strict": True,
        "debug": False,
        "sp": {"entityId": sp["entity_id"],
               "assertionConsumerService": {"url": sp["acs_url"], "binding": SAML_POST},
               "NameIDFormat": NAMEID_EMAIL,
               "x509cert": _pem_body(cert) if signed else "", "privateKey": key if signed else ""},
        "security": {"authnRequestsSigned": signed, "wantAssertionsSigned": False, "wantMessagesSigned": False,
                     "wantNameId": False, "requestedAuthnContext": False, "rejectDeprecatedAlgorithm": True,
                     "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                     "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"},
    }
    if idp:
        certs = list(idp.get("certs") or [])
        out["idp"] = {"entityId": idp["entity_id"],
                      "singleSignOnService": {"url": idp["sso_url"], "binding": SAML_REDIRECT},
                      **({"x509certMulti": {"signing": certs}} if len(certs) > 1 else {"x509cert": certs[0] if certs else ""})}
    return out


def sp_metadata(subdomain: str) -> str:
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    metadata = OneLogin_Saml2_Settings(saml_settings(subdomain, None), sp_validation_only=True).get_sp_metadata()
    return metadata.decode() if isinstance(metadata, bytes) else str(metadata)


def _request_data(host: str, path: str, get: dict[str, str] | None = None,
                  post: dict[str, str] | None = None) -> dict[str, Any]:
    """What python3-saml reads the current address from: https, the host and port the browser used, the path."""
    name, _, port = host.rpartition(":") if host.count(":") == 1 else (host, "", "")
    data: dict[str, Any] = {"https": "on", "http_host": name or host, "script_name": "", "path_info": path,
                            "get_data": get or {}, "post_data": post or {}}
    if port.isdigit():
        data["server_port"] = port
    return data


def _saml_auth(subdomain: str, idp: dict[str, Any], data: dict[str, Any]) -> Any:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    return OneLogin_Saml2_Auth(data, old_settings=saml_settings(subdomain, idp))


def _first(attributes: dict[str, list[str]], names: tuple[str, ...]) -> str:
    for name in names:
        values = attributes.get(name) or []
        if values and str(values[0]).strip():
            return str(values[0]).strip()
    return ""


def saml_profile(row: SsoConnection, state: SsoState, host: str, path: str, post: dict[str, str]) -> Profile:
    """The signed answer → the person. FRM-AUTH-1023 when it doesn't hold up, FRM-AUTH-1021 without an address."""
    if not row.idp:
        raise FrmError("FRM-AUTH-1023")
    auth = _saml_auth(state.subdomain, row.idp, _request_data(host, path, post=post))
    try:
        auth.process_response(request_id=state.request_id)
    except Exception as error:  # noqa: BLE001 (python3-saml raises its own errors for malformed answers)
        log.warning("saml answer refused", extra={"error": type(error).__name__})
        raise FrmError("FRM-AUTH-1023") from None
    if auth.get_errors() or not auth.is_authenticated():
        log.warning("saml answer refused", extra={"errors": ",".join(auth.get_errors())[:200],
                                                  "reason": (auth.get_last_error_reason() or "")[:200]})
        raise FrmError("FRM-AUTH-1023")
    attributes = auth.get_attributes() or {}
    name_id = str(auth.get_nameid() or "").strip()
    email = _first(attributes, EMAIL_ATTRIBUTES) or (name_id if "@" in name_id else "")
    if not email or "@" not in email or len(email) > 254:
        raise FrmError("FRM-AUTH-1021")
    return Profile(subject=(name_id or email)[:255], email=email.strip().lower(),
                   first_name=_first(attributes, FIRST_ATTRIBUTES)[:60], last_name=_first(attributes, LAST_ATTRIBUTES)[:60])


# ── OpenID Connect ────────────────────────────────────────────────────────────────

def _endpoint_ok(url: Any) -> bool:
    return isinstance(url, str) and (url.startswith("https://") or (sso.sso_allow_local() and url.startswith("http://")))


async def begin(tenant: TenantInfo, host: str, connection: dict[str, Any], hint: str | None) -> str:
    """The provider's sign-in address, with the state saved."""
    key = secrets.token_urlsafe(32)
    idp = connection["idp"] or {}
    state = SsoState(protocol=connection["protocol"], tenant_id=str(tenant.id), subdomain=tenant.subdomain, host=host)
    if connection["protocol"] == "saml":
        settings = get_settings()
        auth = _saml_auth(tenant.subdomain, idp, _request_data(host, f"{settings.api_prefix}/auth/sso/start"))
        url = auth.login(return_to=key)
        state.request_id = auth.get_last_request_id()
        await _save(key, state)
        return str(url)
    if not _endpoint_ok(idp.get("authorization_endpoint")):
        raise FrmError("FRM-AUTH-1023")
    state.verifier, state.nonce = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
    params = {"response_type": "code", "client_id": connection["oidc"].get("client_id") or "",
              "redirect_uri": sso.service_provider(tenant.subdomain)["redirect_uri"], "scope": "openid email profile",
              "state": key, "nonce": state.nonce,
              "code_challenge": _b64(hashlib.sha256(state.verifier.encode()).digest()), "code_challenge_method": "S256"}
    if hint:
        params["login_hint"] = hint
    await _save(key, state)
    separator = "&" if "?" in idp["authorization_endpoint"] else "?"
    return f"{idp['authorization_endpoint']}{separator}{urlencode(params)}"


async def oidc_profile(row: SsoConnection, state: SsoState, code: str) -> Profile:
    """Code → tokens → a checked ID token → the person."""
    from app.core import outbound

    idp = row.idp or {}
    oidc = row.oidc or {}
    client_id, secret = oidc.get("client_id") or "", decrypt_secret(row.client_secret_enc) if row.client_secret_enc else ""
    if not (_endpoint_ok(idp.get("token_endpoint")) and _endpoint_ok(idp.get("jwks_uri")) and client_id and secret):
        raise FrmError("FRM-AUTH-1023")
    form = {"grant_type": "authorization_code", "code": code, "code_verifier": state.verifier or "",
            "redirect_uri": sso.service_provider(state.subdomain)["redirect_uri"], "client_id": client_id}
    methods = idp.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
    headers = {"accept": "application/json"}
    if "client_secret_basic" in methods:
        headers["authorization"] = "Basic " + base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    else:
        form["client_secret"] = secret
    allow = sso.sso_allow_local()
    reply = await outbound.http("POST", idp["token_endpoint"], allow_local=allow, data=form, headers=headers)
    form.pop("client_secret", None)
    try:
        if reply is None or reply.status_code != 200:
            raise ValueError("token")
        id_token = str(reply.json()["id_token"])
        keys_reply = await outbound.http("GET", idp["jwks_uri"], allow_local=allow)
        if keys_reply is None or keys_reply.status_code != 200:
            raise ValueError("keys")
        jose = sso.quiet_jose()
        keys = jose.JsonWebKey.import_key_set(keys_reply.json())
        claims = jose.JsonWebToken(ID_TOKEN_ALGORITHMS).decode(id_token, keys, claims_options={
            "iss": {"essential": True, "value": idp.get("issuer") or oidc.get("issuer")},
            "aud": {"essential": True, "value": client_id},
            "exp": {"essential": True},
            "nonce": {"essential": True, "value": state.nonce},
        })
        claims.validate(leeway=120)
    except Exception as error:  # noqa: BLE001 (any failure here: the sign-in didn't finish)
        log.warning("oidc sign-in refused", extra={"error": type(error).__name__})
        raise FrmError("FRM-AUTH-1023") from None
    subject = str(claims.get("sub") or "")
    email = str(claims.get("email") or "")
    if not email:
        alternative = str(claims.get("preferred_username") or claims.get("upn") or "")
        email = alternative if "@" in alternative else ""
    if not subject:
        raise FrmError("FRM-AUTH-1023")
    if not email or "@" not in email or claims.get("email_verified") is False:
        raise FrmError("FRM-AUTH-1021")
    return Profile(subject=subject[:255], email=email.strip().lower(),
                   first_name=str(claims.get("given_name") or "").strip()[:60],
                   last_name=str(claims.get("family_name") or "").strip()[:60])

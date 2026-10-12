"""Single sign-on settings (port of the mock's routes/sso.ts and data/ssoStore.ts): the connection, what the identity
provider needs from Formalie, the real test (SAML metadata or OpenID Connect discovery, only from public HTTPS
addresses), and the answers the sign-in page and the login need (shown when active, required for its domains).
"""

from __future__ import annotations

import base64
import re
import uuid
import warnings
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import outbound
from app.core import zod as z
from app.core.config import get_settings
from app.core.context import TenantInfo
from app.modules.billing.service import has_feature
from app.modules.settings.schemas import is_email_domain
from app.modules.sso.models import SsoConnection

SSO_PROVIDERS = ("okta", "entra", "google_workspace", "onelogin", "saml", "oidc")
SSO_PROTOCOL = {"okta": "oidc", "entra": "oidc", "google_workspace": "saml", "onelogin": "saml", "saml": "saml",
                "oidc": "oidc"}
SAML_KEYS = ("metadata_url", "entity_id", "sso_url", "certificate")
METADATA_REFRESH_S = 24 * 3600


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def sso_allow_local() -> bool:
    return outbound.local_allowed(get_settings().sso_allow_local)


async def row_of(db: AsyncSession, tenant_id: uuid.UUID) -> SsoConnection | None:
    return (await db.execute(select(SsoConnection).where(SsoConnection.tenant_id == tenant_id,
                                                         SsoConnection.deleted_at.is_(None)))).scalar_one_or_none()


def service_provider(subdomain: str) -> dict[str, str]:
    """What the identity provider needs from Formalie (copied into Okta etc.), on the workspace's own address."""
    from app.modules.tenants.router import workspace_url

    def url(path: str) -> str:
        return workspace_url(subdomain, f"{get_settings().api_prefix}/auth/sso/{path}")
    return {"entity_id": url("saml/metadata"), "acs_url": url("saml/acs"), "metadata_url": url("saml/metadata"),
            "redirect_uri": url("oidc/callback"), "signout_url": url("signout")}


def connection_view(row: SsoConnection | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "provider": row.provider, "protocol": row.protocol, "label": row.label,
        "saml": {k: (row.saml or {}).get(k) for k in SAML_KEYS},
        "oidc": {"issuer": (row.oidc or {}).get("issuer"), "client_id": (row.oidc or {}).get("client_id"),
                 "has_secret": bool(row.client_secret_enc)},
        "domains": list(row.domains or []), "enforce": row.enforce, "auto_create": row.auto_create,
        "default_role": row.default_role, "status": row.status, "tested_at": iso(row.tested_at),
        "problem": row.problem, "updated_at": iso(row.updated_at),
    }


def view(row: SsoConnection | None, subdomain: str) -> dict[str, Any]:
    return {"connection": connection_view(row), "service_provider": service_provider(subdomain)}


# ── Validation (the mock's saveSchema) ───────────────────────────────────────────────

def _url() -> z.Schema:
    return z.string().trim().max(500).nullable().transform(lambda v: v or None).refine(
        lambda v: not v or bool(re.match(r"^https://[^\s]+$", v, re.IGNORECASE)), "https")


def _text(size: int) -> z.Schema:
    return z.string().trim().max(size).nullable().transform(lambda v: v or None)


save_schema = z.obj(
    provider=z.enum(list(SSO_PROVIDERS)),
    label=z.string().trim().min(1).max(40),
    saml=z.obj(metadata_url=_url().optional(), entity_id=_text(500).optional(), sso_url=_url().optional(),
               certificate=_text(10_000).optional()).optional(),
    oidc=z.obj(issuer=_url(), client_id=_text(300), client_secret=z.string().max(1000).nullable().optional()).optional(),
    domains=z.array(z.string().trim().lower().transform(lambda v: re.sub(r"^@", "", v)).refine(is_email_domain, "domain")
                    ).max(20),
    enforce=z.boolean(),
    auto_create=z.boolean(),
    default_role=z.string().min(1).max(100),
)


# ── The sign-in page and the login ───────────────────────────────────────────────────

def _domain(email: str) -> str:
    return email.strip().lower().rsplit("@", 1)[-1]


def domain_match(domains: list[str], email: str) -> bool:
    """Does the address belong to these domains (a subdomain counts too)?"""
    domain = _domain(email)
    return any(domain == item or domain.endswith(f".{item}") for item in domains)


async def public_of(db: AsyncSession, tenant: TenantInfo) -> dict[str, Any] | None:
    """SsoPublic on the sign-in profile: only while it is on and the plan has single sign-on."""
    if not has_feature(tenant.plan_id, "sso"):
        return None
    row = await row_of(db, tenant.id)
    if row is None or row.status != "active":
        return None
    return {"provider": row.provider, "label": row.label, "domains": list(row.domains or []), "enforce": row.enforce}


async def required_for(db: AsyncSession, tenant: TenantInfo, email: str) -> bool:
    """People of these domains may only sign in through the provider (the mock's ssoRequired)."""
    sso = await public_of(db, tenant)
    return bool(sso and sso["enforce"] and domain_match(sso["domains"], email))


# ── The test ─────────────────────────────────────────────────────────────────────────

def _trim_slash(value: str) -> str:
    return value.rstrip("/")


async def read(url: str) -> str | None:
    """A page from the provider (a few seconds at most), or None."""
    reply = await outbound.http("GET", url, allow_local=sso_allow_local(),
                                headers={"accept": "application/json, application/xml, text/xml"})
    if reply is None or not 200 <= reply.status_code < 300:
        return None
    return str(reply.text)


def parse_metadata(xml: str) -> dict[str, Any] | None:
    """The identity provider's entity id, sign-in address (HTTP-Redirect) and signing certificates, or None."""
    if "EntityDescriptor" not in xml or "SingleSignOnService" not in xml:
        return None
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    try:
        parsed = OneLogin_Saml2_IdPMetadataParser.parse(xml)
    except Exception:  # noqa: BLE001 (malformed XML)
        return None
    idp = parsed.get("idp") or {}
    sso_url = (idp.get("singleSignOnService") or {}).get("url")
    certs = list((idp.get("x509certMulti") or {}).get("signing") or []) or ([idp["x509cert"]] if idp.get("x509cert") else [])
    if not idp.get("entityId") or not sso_url or not certs:
        return None
    return {"entity_id": idp["entityId"], "sso_url": sso_url, "certs": certs}


def _certificate(value: str | None) -> str:
    return re.sub(r"-----(BEGIN|END) CERTIFICATE-----|\s", "", value or "")


def certificate_ok(value: str | None) -> bool:
    """The mock's check (base64, 200 characters at least), and it must really be an X.509 certificate."""
    body = _certificate(value)
    if not re.fullmatch(r"[A-Za-z0-9+/=]{200,}", body):
        return False
    from cryptography import x509

    try:
        x509.load_der_x509_certificate(base64.b64decode(body))
    except ValueError:
        return False
    return True


async def discover(issuer: str) -> tuple[dict[str, Any] | None, str | None]:
    """{issuer}/.well-known/openid-configuration → (what sign-in needs, problem)."""
    body = await read(f"{_trim_slash(issuer)}/.well-known/openid-configuration")
    if body is None:
        return None, "unreachable"
    import json

    try:
        discovery = json.loads(body)
    except ValueError:
        return None, "not_discovery"
    if not isinstance(discovery, dict) or not discovery.get("authorization_endpoint"):
        return None, "not_discovery"
    if _trim_slash(str(discovery.get("issuer") or "")) != _trim_slash(issuer):
        return None, "issuer_mismatch"
    keys = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "token_endpoint_auth_methods_supported")
    return {k: discovery.get(k) for k in keys}, None


async def problem_of(row: SsoConnection) -> tuple[str | None, dict[str, Any] | None]:
    """The mock's problemOf, for real → (problem or None, what the provider told us)."""
    if row.protocol == "oidc":
        oidc = row.oidc or {}
        if not oidc.get("issuer") or not oidc.get("client_id") or not row.client_secret_enc:
            return "incomplete", None
        idp, problem = await discover(oidc["issuer"])
        if idp is not None and not (idp.get("token_endpoint") and idp.get("jwks_uri")):
            return "not_discovery", None
        return problem, idp
    saml = row.saml or {}
    if saml.get("metadata_url"):
        body = await read(saml["metadata_url"])
        if body is None:
            return "unreachable", None
        idp = parse_metadata(body)
        if idp is None:
            return "not_metadata", None
        return None, {**idp, "fetched_at": datetime.now(UTC).isoformat()}
    if saml.get("entity_id") and saml.get("sso_url") and certificate_ok(saml.get("certificate")):
        return None, {"entity_id": saml["entity_id"], "sso_url": saml["sso_url"],
                      "certs": [_certificate(saml["certificate"])]}
    return "incomplete", None


async def fresh_idp(row: SsoConnection) -> dict[str, Any] | None:
    """SAML with a metadata address: read again once a day so rotated certificates are picked up (the last good copy
    stays when the provider can't be reached)."""
    idp = dict(row.idp or {})
    if row.protocol != "saml" or not (row.saml or {}).get("metadata_url"):
        return idp or None
    try:
        fetched = datetime.fromisoformat(str(idp.get("fetched_at")))
    except ValueError:
        fetched = None
    if fetched is not None and (datetime.now(UTC) - fetched).total_seconds() < METADATA_REFRESH_S:
        return idp
    body = await read(row.saml["metadata_url"])
    parsed = parse_metadata(body) if body else None
    if parsed is None:
        return idp or None
    row.idp = {**parsed, "fetched_at": datetime.now(UTC).isoformat()}
    return row.idp


def quiet_jose() -> Any:
    """authlib.jose (deprecated in favour of joserfc, still supported in Authlib 1.x)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from authlib import jose
    return jose

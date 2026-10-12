"""Single sign-on (port of the mock's routes/sso.ts; API-CONTRACT → Settings). Settings routes are for admins:

    GET    /settings/sso            the connection (secret never returned) and what the identity provider needs
    PUT    /settings/sso            SsoSaveRequest (a changed set-up must be tested again)
    POST   /settings/sso/test       SAML: reads the metadata address or checks the values given; OIDC: discovery
    POST   /settings/sso/status     { active } (on only after a passing test, else FRM-AUTH-1020)
    DELETE /settings/sso

and the browser's (plain, no envelope; SECURITY-PROTOCOL §4):

    GET    /auth/sso/start          → the identity provider (SAML AuthnRequest, or OIDC code flow with PKCE)
    POST   /auth/sso/saml/acs       the provider's signed answer
    GET    /auth/sso/saml/metadata  Formalie's service provider metadata for this workspace
    GET    /auth/sso/oidc/callback  the provider's code
    GET    /auth/sso/signout        back to the sign-in page

A sign-in through the provider still takes the workspace's usual second step (the 6-digit code or the authenticator
app): back on /auth/login with `oauth_challenge`, like social sign-in. Everything is in the audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.core import zod as z
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import require_tenant
from app.core.responses import ok
from app.core.security.fernet_tokens import encrypt_secret
from app.core.security.limits import rate_limit
from app.core.security.refs import get_codec
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.billing.service import has_feature, require_feature
from app.modules.rbac.service import find_role
from app.modules.sso import flows
from app.modules.sso import service as sso
from app.modules.sso.models import SsoConnection

router = APIRouter(tags=["sso"])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


async def _audit(db: Any, principal: Principal, field: str, before: Any, after: Any) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                 action="settings.updated", actor=Actor.user(principal.user),
                 resource={"type": "setting", "id": None, "name": "Single sign-on"},
                 changes=[{"field": field, "before": before, "after": after}])


async def _body(request: Request) -> Any:
    raw = await request.body()
    return (await request.json()) if raw else None


@router.get("/settings/sso", dependencies=[rate_limit("settings-sso", per_minute=120)])
async def get_sso(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(sso.view(await sso.row_of(db, principal.tenant.id), principal.tenant.subdomain))


@router.put("/settings/sso", dependencies=[rate_limit("settings-sso", per_minute=30)])
async def save_sso(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    require_feature(principal.tenant.plan_id, "sso")
    raw = await _body(request)
    body = sso.save_schema.parse(raw)
    async with db_session("write", **_scope(principal)) as db:
        role = await find_role(db, principal.tenant.id, body["default_role"])
        if body["default_role"] == "owner" or role is None or role.built_in == "owner":
            raise FrmError("FRM-GEN-1002", [{"field": "default_role", "message": "role"}])
        if body["enforce"] and not body["domains"]:
            raise FrmError("FRM-GEN-1002", [{"field": "domains", "message": "required"}])
        current = await sso.row_of(db, principal.tenant.id)
        given = body.get("saml") or {}
        saml = {k: given.get(k) for k in sso.SAML_KEYS}
        oidc_in = body.get("oidc") or {}
        secret_given = isinstance(raw.get("oidc"), dict) and "client_secret" in raw["oidc"]
        oidc = {"issuer": oidc_in.get("issuer"), "client_id": oidc_in.get("client_id")}
        # A different provider set-up must pass a new test before people use it
        changed = current is None or current.provider != body["provider"] or (current.saml or {}) != saml \
            or (current.oidc or {}).get("issuer") != oidc["issuer"] \
            or (current.oidc or {}).get("client_id") != oidc["client_id"] or secret_given
        before = f"{current.provider} ({current.status})" if current is not None else None
        row = current
        if row is None:
            row = SsoConnection(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                created_by=principal.user.id, provider=body["provider"], protocol="saml", label="",
                                default_role="member")
            db.add(row)
        if secret_given:
            row.client_secret_enc = encrypt_secret(oidc_in["client_secret"]) if oidc_in.get("client_secret") else None
        row.provider, row.protocol, row.label = body["provider"], sso.SSO_PROTOCOL[body["provider"]], body["label"]
        row.saml, row.oidc = saml, oidc
        row.domains = list(dict.fromkeys(body["domains"]))
        row.enforce, row.auto_create, row.default_role = body["enforce"], body["auto_create"], body["default_role"]
        if changed:
            row.status, row.tested_at, row.problem, row.idp = "draft", None, None, None
        row.updated_by, row.updated_at = principal.user.id, datetime.now(UTC)
        await db.flush()
        await _audit(db, principal, "sso", before, f"{row.provider} ({row.status})")
        await db.refresh(row)
        return ok(sso.view(row, principal.tenant.subdomain))


@router.post("/settings/sso/test", dependencies=[rate_limit("settings-sso-test", per_minute=20)])
async def test_sso(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        row = await sso.row_of(db, principal.tenant.id)
        if row is None:
            raise FrmError("FRM-GEN-1004")
        problem, idp = await sso.problem_of(row)  # reads the provider; nothing is written yet
    async with db_session("write", **_scope(principal)) as db:
        row = await sso.row_of(db, principal.tenant.id)
        if row is None:
            raise FrmError("FRM-GEN-1004")
        before = row.status
        # A passing test keeps an active connection active; a failing one turns it off so nobody gets stuck
        row.status = "draft" if problem else ("active" if row.status == "active" else "tested")
        row.problem = problem
        row.tested_at = None if problem else datetime.now(UTC)
        if not problem:
            row.idp = idp
        row.updated_by = principal.user.id
        await db.flush()
        await _audit(db, principal, "sso_test", before, problem or "passed")
        await db.refresh(row)
        return ok(sso.view(row, principal.tenant.subdomain))


status_schema = z.obj(active=z.boolean())


@router.post("/settings/sso/status", dependencies=[rate_limit("settings-sso", per_minute=30)])
async def set_sso_status(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    active = status_schema.parse(await _body(request))["active"]
    async with db_session("write", **_scope(principal)) as db:
        row = await sso.row_of(db, principal.tenant.id)
        if row is None:
            raise FrmError("FRM-GEN-1004")
        if active:
            require_feature(principal.tenant.plan_id, "sso")
        if active and row.status == "draft":
            raise FrmError("FRM-AUTH-1020")
        before = row.status
        row.status = "active" if active else "tested"
        if before != row.status:
            row.updated_by = principal.user.id
            await db.flush()
            await _audit(db, principal, "sso_status", before, row.status)
            await db.refresh(row)
        return ok(sso.view(row, principal.tenant.subdomain))


@router.delete("/settings/sso", dependencies=[rate_limit("settings-sso", per_minute=30)])
async def remove_sso(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        row = await sso.row_of(db, principal.tenant.id)
        if row is not None:
            row.soft_delete(principal.user.id)
            row.client_secret_enc = None
            await db.flush()
            await _audit(db, principal, "sso", row.provider, None)
        return ok(sso.view(None, principal.tenant.subdomain))


# ── The browser's side ──────────────────────────────────────────────────────────────

def _login(query: dict[str, str], host: str | None = None) -> RedirectResponse:
    target = f"/auth/login?{urlencode(query)}"
    return RedirectResponse(f"https://{host}{target}" if host else target, status_code=302)


def _refused(code: str, host: str | None = None) -> RedirectResponse:
    return _login({"oauth": "error", "provider": "sso", "code": code}, host)


@router.get("/auth/sso/start", dependencies=[rate_limit("sso-start", per_minute=20)])
async def sso_start(email: str | None = None) -> Any:
    """→ the identity provider. Not set up, not on, or not in the plan: back with sso=unavailable, like the mock."""
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    if tenant is None or tenant.status == "suspended" or not has_feature(tenant.plan_id, "sso"):
        return _login({"sso": "unavailable"})
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        row = await sso.row_of(db, tenant.id)
        if row is None or row.status != "active":
            return _login({"sso": "unavailable"})
        idp = await sso.fresh_idp(row)
        connection = {"protocol": row.protocol, "oidc": dict(row.oidc or {}), "idp": idp}
    if not idp:
        return _login({"sso": "unavailable"})
    hint = email.strip().lower() if email and "@" in email and len(email) <= 254 else None
    try:
        url = await flows.begin(tenant, (ctx.host if ctx else None) or "", connection, hint)
    except FrmError as refused:
        return _refused(refused.code)
    return RedirectResponse(url, status_code=302)


async def _finish(state: flows.SsoState | None, read: Any) -> RedirectResponse:
    """The provider's answer → the sign-in's second step, back on the sign-in page."""
    from app.modules.auth.router import sso_login
    from app.modules.tenants.service import TenantDirectory

    if state is None:
        return _refused("FRM-AUTH-1023")
    tenant = await TenantDirectory().by_subdomain(state.subdomain)
    if tenant is None or str(tenant.id) != state.tenant_id:
        return _refused("FRM-TEN-1001", state.host)
    try:
        async with db_session("read", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
            row = await sso.row_of(db, tenant.id)
        if row is None or row.status != "active" or not has_feature(tenant.plan_id, "sso"):
            return _login({"sso": "unavailable"}, state.host)
        profile = await read(row)
        challenge = await sso_login(tenant, profile, domains=list(row.domains or []), auto_create=row.auto_create,
                                    default_role=row.default_role)
    except FrmError as refused:
        return _refused(refused.code, state.host)
    return _login({"oauth_challenge": get_codec().encode_id(challenge.id), "provider": "sso"}, state.host)


@router.post("/auth/sso/saml/acs", dependencies=[rate_limit("sso-callback", per_minute=30)])
async def saml_acs(request: Request) -> Any:
    form = await request.form()
    relay = str(form.get("RelayState") or "")
    response = str(form.get("SAMLResponse") or "")
    state = await flows.take_state(relay)
    if state is None or state.protocol != "saml" or not response:
        return _refused("FRM-AUTH-1023", state.host if state else None)
    ctx = get_context()
    host = (ctx.host if ctx else None) or ""

    async def read(row: SsoConnection) -> Any:
        return flows.saml_profile(row, state, host, request.url.path, {"SAMLResponse": response, "RelayState": relay})
    return await _finish(state, read)


@router.get("/auth/sso/oidc/callback", dependencies=[rate_limit("sso-callback", per_minute=30)])
async def oidc_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> Any:
    saved = await flows.take_state(state)
    if saved is None or saved.protocol != "oidc":
        return _refused("FRM-AUTH-1023")
    if error or not code:
        return _login({"oauth": "cancelled", "provider": "sso"}, saved.host) if error == "access_denied" \
            else _refused("FRM-AUTH-1023", saved.host)

    async def read(row: SsoConnection) -> Any:
        return await flows.oidc_profile(row, saved, code)
    return await _finish(saved, read)


@router.get("/auth/sso/saml/metadata", dependencies=[rate_limit("sso-metadata", per_minute=60)])
async def saml_metadata() -> Any:
    """Formalie's service provider metadata for this workspace (what Okta and others can import)."""
    tenant = require_tenant()
    return Response(flows.sp_metadata(tenant.subdomain), media_type="application/samlmetadata+xml")


@router.get("/auth/sso/signout", dependencies=[rate_limit("sso-signout", per_minute=60)])
async def sso_signout() -> Any:
    """The identity provider's sign-out sends people here: the portal's own sign-out already ended the session."""
    return RedirectResponse("/auth/login", status_code=302)

"""Sign-in routes (mock: server/mock/routes/auth.ts), same checks in the same order, same audit actions.

login → code (email, or the authenticator app) → verify → tokens + refresh cookie; refresh (rotation, reuse
detection); logout; /me; sign-up on manage.* → code → complete (new workspace) → one-time ticket → exchange on the
new subdomain; forgot / reset password. A failed sign-in is answered with its code but its audit entry is kept
(FrmError commit=True). Codes are never returned (the mock's `meta.dev_code`): they arrive by email (Mailpit).
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import pyotp
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.events.outbox import record_event
from app.core.middleware.tenant import current_host_context, is_valid_subdomain, require_tenant
from app.core.responses import ok
from app.core.validation import Email
from app.core.security.fernet_tokens import decrypt_secret
from app.core.security.limits import per_value, rate_limit
from app.core.security.passwords import DUMMY_HASH, check_password, hash_password, meets_password_policy, verify_password
from app.modules.audit.service import Actor, record
from app.modules.auth import challenges
from app.modules.auth.sessions import (
    REFRESH_COOKIE, REFRESH_COOKIE_PATH, Principal, end_session, ip_allowed, refresh_cookie, require_auth,
    rotate_refresh, start_session,
)
from app.modules.emails import service as emails
from app.modules.settings.service import get_section
from app.modules.tenants.router import workspace_url
from app.modules.tenants.service import TenantDirectory
from app.modules.tenants.workspace import Founder, create_workspace
from app.modules.users.models import User, UserPasswordHistory, UserRecoveryCode, UserTwoStep

router = APIRouter(tags=["auth"])

CLEAR_REFRESH = (f"{REFRESH_COOKIE}=; Max-Age=0; Path={REFRESH_COOKIE_PATH}; HttpOnly; Secure; SameSite=Strict")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _scope(tenant: TenantInfo) -> dict[str, Any]:
    return {"tenant_id": tenant.id, "organisation_id": tenant.organisation_id}


def _tenant_dict(tenant: TenantInfo) -> dict[str, Any]:
    return {"id": tenant.id, "organisation_id": tenant.organisation_id, "name": tenant.name}


async def _audit(db: Any, tenant: TenantInfo, action: str, actor: Actor, **kwargs: Any) -> None:
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action=action, actor=actor, **kwargs)


async def _security_alert(db: Any, email: str, reason: str) -> None:
    """Settings → Notifications: a blocked sign-in tells the workspace's admins (the notifications module, B8,
    turns this event into the in-app notice and email)."""
    await record_event(db, "security.alert", {"email": email, "reason": reason,
                                              "link": "/audit?area=auth&outcome=failure,blocked"})


def _with_cookie(body: dict[str, Any], refresh: str) -> JSONResponse:
    response = JSONResponse(body)
    response.set_cookie(**refresh_cookie(refresh))
    return response


async def _language(db: Any, tenant: TenantInfo, user: User | None) -> str:
    if user is not None and user.language:
        return user.language
    return (await get_section(db, tenant.id, "localisation")).get("language") or "en"


def _hash_recovery(code: str) -> str:
    """hashRecovery(): trimmed, lower case, no spaces, SHA-256."""
    return hashlib.sha256(re.sub(r"\s+", "", code.strip().lower()).encode()).hexdigest()


async def _second_factor(db: Any, user_id: uuid.UUID, code: str) -> bool:
    """An authenticator code (30 s steps, one step either side) or an unused recovery code (used once)."""
    two_step = (await db.execute(select(UserTwoStep).where(UserTwoStep.user_id == user_id,
                                                           UserTwoStep.deleted_at.is_(None)))).scalar_one_or_none()
    if two_step is not None and two_step.totp_secret_enc and two_step.totp_confirmed_at and re.fullmatch(r"\d{6}", code):
        if pyotp.TOTP(decrypt_secret(two_step.totp_secret_enc)).verify(code, valid_window=1):
            return True
    if not re.fullmatch(r"[a-z0-9]{4}-?[a-z0-9]{4}", code.strip(), re.IGNORECASE):
        return False
    normal = code.strip() if "-" in code else f"{code.strip()[:4]}-{code.strip()[4:]}"
    row = (await db.execute(select(UserRecoveryCode).where(
        UserRecoveryCode.user_id == user_id, UserRecoveryCode.code_hash == _hash_recovery(normal),
        UserRecoveryCode.used_at.is_(None), UserRecoveryCode.deleted_at.is_(None)))).scalar_one_or_none()
    if row is None:
        return False
    row.used_at = datetime.now(UTC)
    return True


async def _send_code(db: Any, tenant: TenantInfo | None, challenge: challenges.Challenge, code: str | None,
                     user: User | None, template: str = "signin_code") -> None:
    if code is None or challenge.channel != "email":
        return  # the authenticator app: nothing to send. Text messages: no SMS provider yet (B11)
    language = await _language(db, tenant, user) if tenant is not None else None
    emails.send(challenge.email, template, language, {
        "workspace": tenant.name if tenant else "Formalie", "name": user.first_name if user else challenge.email.split("@")[0],
        "code": code, "minutes": challenge.ttl_ms // 60_000})


async def _find_user(db: Any, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email.strip().lower(),
                                                User.deleted_at.is_(None)))).scalar_one_or_none()


def _domain_allowed(signin: dict[str, Any], email: str) -> bool:
    domains = signin.get("allowed_domains") or []
    domain = email.rsplit("@", 1)[-1].lower()
    return not domains or any(domain == d or domain.endswith(f".{d}") for d in domains)


def _password_expired(security: dict[str, Any], user: User) -> bool:
    if user.must_change_password:
        return True
    days = security["password"].get("expiry_days") or 0
    return bool(days and user.password_changed_at and datetime.now(UTC) - user.password_changed_at > timedelta(days=days))


# ── Login and codes ──────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=200)


@router.post("/auth/login", dependencies=[rate_limit("login", per_minute=10)])
async def login(body: LoginBody) -> Any:
    """→ a code challenge, no tokens yet (SECURITY-PROTOCOL §7)."""
    tenant = require_tenant()
    email = str(body.email).lower()
    await per_value("login", email, limit=10, window_seconds=600)
    ctx = get_context()
    async with db_session("write", **_scope(tenant)) as db:
        signin = await get_section(db, tenant.id, "signin")
        security = await get_section(db, tenant.id, "security")
        if "password" not in signin["methods"]:
            raise FrmError("FRM-AUTH-1008")
        if not ip_allowed(security, ctx.client_ip if ctx else None):
            await _audit(db, tenant, "auth.login.blocked", Actor.anonymous(email), outcome="blocked",
                         reason="FRM-AUTH-1016", metadata={"method": "password", "cause": "ip_not_allowed"})
            await _security_alert(db, email, "ip_not_allowed")
            raise FrmError("FRM-AUTH-1016", commit=True)
        user = await _find_user(db, email)
        # The same work for an unknown address as for a known one (no account discovery by timing)
        password_ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password) and user is not None
        if user is None or not password_ok:
            await _audit(db, tenant, "auth.login.failed", Actor.user(user) if user else Actor.anonymous(email),
                         outcome="failure", reason="FRM-AUTH-1002",
                         metadata={"method": "password", **({} if user else {"account": "not_found"})})
            raise FrmError("FRM-AUTH-1002", commit=True)
        blocked = [("pending", "FRM-USER-1010", "awaiting_approval", False), ("disabled", "FRM-AUTH-1005", None, True)]
        for status, code, cause, alert in blocked:
            if user.status == status:
                await _audit(db, tenant, "auth.login.blocked", Actor.user(user), outcome="blocked", severity="notice",
                             reason=code, metadata={"method": "password", **({"cause": cause} if cause else {})})
                if alert:
                    await _security_alert(db, user.email, "account_disabled")
                raise FrmError(code, commit=True)
        if not _domain_allowed(signin, user.email):
            await _audit(db, tenant, "auth.login.blocked", Actor.user(user), outcome="blocked", severity="notice",
                         reason="FRM-AUTH-1014", metadata={"method": "password", "cause": "email_domain"})
            await _security_alert(db, user.email, "email_domain")
            raise FrmError("FRM-AUTH-1014", commit=True)
        if _password_expired(security, user):
            await _audit(db, tenant, "auth.login.blocked", Actor.user(user), outcome="blocked", severity="notice",
                         reason="FRM-AUTH-1015", metadata={"method": "password", "cause": "password_expired"})
            raise FrmError("FRM-AUTH-1015", commit=True)
        two_step = (await db.execute(select(UserTwoStep).where(UserTwoStep.user_id == user.id,
                                                               UserTwoStep.deleted_at.is_(None)))).scalar_one_or_none()
        has_app = bool(two_step and two_step.totp_secret_enc and two_step.totp_confirmed_at)
        channels = (["totp"] if has_app else []) + ["email"] + (["sms"] if user.phone and signin["code"].get("sms") else [])
        challenge, code = await challenges.create_challenge(
            purpose="login", email=user.email, channel="totp" if has_app else "email", channels=channels,
            tenant=_tenant_dict(tenant), user=user, code_rules=signin["code"], language=user.language)
        await _audit(db, tenant, "auth.otp.sent", Actor.user(user), metadata={"channel": challenge.channel})
        await _send_code(db, tenant, challenge, code, user)
    return ok(challenges.describe(challenge))


class VerifyBody(BaseModel):
    challenge_id: str = Field(max_length=64)
    # A recovery code ("k7q2-9xmd") also passes where an authenticator code is asked
    code: str = Field(max_length=16)

    @field_validator("code")
    @classmethod
    def _code_shape(cls, value: str) -> str:
        value = value.strip()
        if not (re.fullmatch(r"\d{6}", value) or re.fullmatch(r"[a-z0-9]{4}-?[a-z0-9]{4}", value, re.IGNORECASE)):
            raise ValueError("Enter the 6-digit code.")
        return value


@router.post("/auth/otp/verify", dependencies=[rate_limit("otp-verify", per_minute=20)])
async def verify_otp(body: VerifyBody) -> Any:
    """login → tokens + refresh cookie; signup → the email is verified."""
    pending = await challenges.get_challenge(body.challenge_id)
    if pending is not None and pending.purpose == "signup":
        await challenges.verify_code(body.challenge_id, body.code, "signup")
        return ok({"verified": True})
    tenant = require_tenant()
    if pending is not None and pending.tenant_id and pending.tenant_id != str(tenant.id):
        raise FrmError("FRM-AUTH-1003")
    async with db_session("write", **_scope(tenant)) as db:
        async def factor(ch: challenges.Challenge, code: str) -> bool:
            return await _second_factor(db, uuid.UUID(ch.user_id), code) if ch.user_id else False
        try:
            challenge = await challenges.verify_code(body.challenge_id, body.code, "login", second_factor=factor)
        except FrmError as error:
            if pending is not None and pending.tenant_id:
                user = await db.get(User, uuid.UUID(pending.user_id)) if pending.user_id else None
                locked = error.code == "FRM-AUTH-1004"
                await _audit(db, tenant, "auth.otp.locked" if locked else "auth.otp.failed",
                             Actor.user(user) if user else Actor.anonymous(pending.email),
                             outcome="blocked" if locked else "failure", reason=error.code,
                             metadata={"purpose": "login", "channel": pending.channel,
                                       **({"attempts_left": error.details[0]["message"]} if error.details else {})})
                if locked:
                    await _security_alert(db, pending.email, "code_locked")
            error.commit = True
            raise
        await challenges.consume(challenge.id)
        user = await db.get(User, uuid.UUID(challenge.user_id or ""))
        if user is None or user.deleted_at is not None:
            raise FrmError("FRM-AUTH-1003")
        await _audit(db, tenant, "auth.login.succeeded", Actor.user(user),
                     metadata={"method": "password", "channel": challenge.channel})
        tokens, refresh = await start_session(db, user, tenant, "password")
    return _with_cookie({"success": True, "data": tokens, "meta": {}}, refresh)


class ResendBody(BaseModel):
    challenge_id: str = Field(max_length=64)
    channel: str | None = Field(default=None, pattern=r"^(email|sms|totp)$")


@router.post("/auth/otp/resend", dependencies=[rate_limit("otp-resend", per_minute=10)])
async def resend_otp(body: ResendBody) -> Any:
    challenge, code = await challenges.resend(body.challenge_id, body.channel)
    if challenge.tenant_id:
        tenant = require_tenant()
        async with db_session("write", **_scope(tenant)) as db:
            user = await db.get(User, uuid.UUID(challenge.user_id)) if challenge.user_id else None
            await _audit(db, tenant, "auth.otp.sent", Actor.user(user) if user else Actor.anonymous(challenge.email),
                         metadata={"channel": challenge.channel, "resend": str(challenge.resends)})
            await _send_code(db, tenant, challenge, code, user,
                             "password_reset" if challenge.purpose == "reset" else "signin_code")
    else:
        await _send_code(None, None, challenge, code, None)
    return ok(challenges.describe(challenge))


# ── Tokens ───────────────────────────────────────────────────────────────────────

@router.post("/auth/refresh", dependencies=[rate_limit("refresh", per_minute=30)])
async def refresh(request: Request) -> Any:
    """Single use: a reused refresh token ends the session (FRM-AUTH-1012) and the cookie is cleared."""
    tenant = require_tenant()
    try:
        tokens, new_refresh = await rotate_refresh(request.cookies.get(REFRESH_COOKIE), tenant)
    except FrmError as error:
        if error.code == "FRM-AUTH-1012":
            error.headers["Set-Cookie"] = CLEAR_REFRESH
        raise
    return _with_cookie({"success": True, "data": tokens, "meta": {}}, new_refresh)


@router.post("/auth/logout")
async def logout(request: Request) -> Any:
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    if tenant is not None:
        header = request.headers.get("authorization", "")
        async with db_session("write", **_scope(tenant)) as db:
            ended = await end_session(db, request.cookies.get(REFRESH_COOKIE),
                                      header[7:] if header.lower().startswith("bearer ") else None)
            if ended is not None:
                await _audit(db, tenant, "auth.logout", Actor.user(ended[1]))
    response = JSONResponse({"success": True, "data": {"signed_out": True}, "meta": {}})
    response.headers.append("Set-Cookie", CLEAR_REFRESH)
    return response


@router.get("/me")
async def me(principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.rbac.service import permissions_of, role_key, role_name

    user = principal.user
    return ok({
        "id": str(user.id), "first_name": user.first_name, "last_name": user.last_name, "email": user.email,
        "avatar_url": None, "role": role_key(principal.role), "role_name": role_name(principal.role) or role_key(principal.role),
        "permissions": permissions_of(principal.grants), "grants": principal.grants,
        "language": user.language, "time_zone": user.time_zone, "date_format": user.date_format,
    })


# ── Sign-up (manage.*) ───────────────────────────────────────────────────────────

class SignupBody(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: Email
    password: str = Field(max_length=200)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _trim(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def _policy(cls, value: str) -> str:
        if not meets_password_policy(value):
            raise ValueError("Password does not meet the policy.")
        return value


@router.post("/auth/signup", dependencies=[rate_limit("signup", per_minute=5)])
async def signup(body: SignupBody) -> Any:
    """manage.* only → a code to verify the email."""
    host = current_host_context()
    if host is None or host.kind != "manage":
        raise FrmError("FRM-PERM-1001")
    await per_value("signup", str(body.email), limit=5, window_seconds=3600)
    challenge, code = await challenges.create_challenge(
        purpose="signup", email=str(body.email).lower(), channel="email", channels=["email"],
        signup={"first_name": body.first_name, "last_name": body.last_name, "password_hash": hash_password(body.password)})
    await _send_code(None, None, challenge, code, None)
    return ok(challenges.describe(challenge))


class CompleteBody(BaseModel):
    challenge_id: str = Field(max_length=64)
    company_name: str = Field(min_length=2, max_length=80)
    subdomain: str = Field(pattern=r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")

    @field_validator("company_name", mode="before")
    @classmethod
    def _trim(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("subdomain", mode="before")
    @classmethod
    def _lower(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value


@router.post("/auth/signup/complete", dependencies=[rate_limit("signup-complete", per_minute=5)])
async def signup_complete(body: CompleteBody) -> Any:
    """→ the workspace (tenant, organisation, Owner) and a one-time sign-in link on its new subdomain."""
    challenge = await challenges.get_challenge(body.challenge_id)
    if challenge is None or challenge.purpose != "signup" or not challenge.verified or not challenge.signup:
        raise FrmError("FRM-AUTH-1003")
    if not is_valid_subdomain(body.subdomain):
        raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "This subdomain is taken."}])
    async with db_session("write") as db:
        made = await create_workspace(db, name=body.company_name, subdomain=body.subdomain, founder=Founder(
            challenge.signup["first_name"], challenge.signup["last_name"], challenge.email, challenge.signup["password_hash"]))
        tenant = TenantInfo(id=made.tenant_id, subdomain=made.subdomain, name=made.name, status="active",
                            organisation_id=made.organisation_id)
        owner = await db.get(User, made.owner_id)
        await _audit(db, tenant, "workspace.created", Actor.user(owner),
                     resource={"type": "workspace", "id": str(tenant.id), "name": tenant.name},
                     metadata={"subdomain": tenant.subdomain})
        await record_event(db, "tenant.signed_up", {"subdomain": tenant.subdomain, "plan": "starter"},
                           tenant_id=tenant.id, organisation_id=tenant.organisation_id, actor_id=made.owner_id)
    await challenges.consume(challenge.id)
    await TenantDirectory().forget(made.subdomain)  # a lookup of the new host before now may be cached as unknown
    ticket = await challenges.issue_ticket(made.owner_id, made.tenant_id, made.organisation_id)  # type: ignore[arg-type]
    return ok({"redirect_url": workspace_url(made.subdomain, f"/auth/welcome?ticket={quote(ticket)}")})


class TicketBody(BaseModel):
    ticket: str = Field(min_length=10, max_length=200)


@router.post("/auth/exchange-ticket", dependencies=[rate_limit("exchange-ticket", per_minute=10)])
async def exchange_ticket(body: TicketBody) -> Any:
    """One-time hand-off from manage.* to the new subdomain → tokens + refresh cookie."""
    tenant = require_tenant()
    entry = await challenges.redeem_ticket(body.ticket)
    if entry is None:
        raise FrmError("FRM-AUTH-1010")
    if entry["tenant_id"] != str(tenant.id):
        raise FrmError("FRM-TEN-1003")
    async with db_session("write", **_scope(tenant)) as db:
        user = await db.get(User, uuid.UUID(entry["user_id"]))
        if user is None or user.deleted_at is not None:
            raise FrmError("FRM-AUTH-1010")
        tokens, refresh = await start_session(db, user, tenant, "signup_handoff")
        await _audit(db, tenant, "auth.login.succeeded", Actor.user(user), metadata={"method": "signup_handoff"})
    return _with_cookie({"success": True, "data": tokens, "meta": {}}, refresh)


# ── Forgotten password ───────────────────────────────────────────────────────────

class ForgotBody(BaseModel):
    email: Email


@router.post("/auth/password/forgot", dependencies=[rate_limit("password-forgot", per_minute=5)])
async def forgot_password(body: ForgotBody) -> Any:
    """Always answers the same (no account discovery); the code is only sent to a real account."""
    tenant = require_tenant()
    email = str(body.email).lower()
    await per_value("password-forgot", email, limit=5, window_seconds=3600)
    async with db_session("write", **_scope(tenant)) as db:
        user = await _find_user(db, email)
        challenge, code = await challenges.create_challenge(purpose="reset", email=email, channel="email",
                                                            channels=["email"], tenant=_tenant_dict(tenant), user=user)
        await _audit(db, tenant, "auth.password.reset_requested", Actor.user(user) if user else Actor.anonymous(email),
                     outcome="success" if user else "failure",
                     metadata={"channel": "email", **({} if user else {"account": "not_found"})})
        if user is not None:
            await _send_code(db, tenant, challenge, code, user, "password_reset")
    return ok(challenges.describe(challenge))


class ResetBody(BaseModel):
    challenge_id: str = Field(max_length=64)
    code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=1, max_length=200)


async def check_new_password(db: Any, tenant: TenantInfo, user: User | None, value: str) -> None:
    """The workspace's password rules: FRM-AUTH-1007 names what is missing; FRM-AUTH-1018 a recent password."""
    rules = (await get_section(db, tenant.id, "security"))["password"]
    if not meets_password_policy(value, rules):
        missing = [c for c in check_password(value, rules) if c["required"] and not c["passed"]]
        raise FrmError("FRM-AUTH-1007", [{"field": "password", "message": f"min_length:{rules['min_length']}"
                                          if c["key"] == "length" else c["key"]} for c in missing])
    reuse = int(rules.get("reuse_last") or 0)
    if user is not None and reuse:
        history = (await db.execute(select(UserPasswordHistory.password_hash).where(UserPasswordHistory.user_id == user.id)
                                    .order_by(UserPasswordHistory.created_at.desc()).limit(reuse - 1))).scalars().all()
        if any(verify_password(h, value) for h in [user.password_hash, *history] if h):
            raise FrmError("FRM-AUTH-1018", [{"field": "password", "message": f"last_{reuse}"}])


@router.post("/auth/password/reset", dependencies=[rate_limit("password-reset", per_minute=10)])
async def reset_password(body: ResetBody) -> Any:
    tenant = require_tenant()
    pending = await challenges.get_challenge(body.challenge_id)
    async with db_session("write", **_scope(tenant)) as db:
        user = await db.get(User, uuid.UUID(pending.user_id)) if pending and pending.user_id else None
        # The rules first, so a refused password doesn't use up the code
        if pending is not None and pending.purpose == "reset" and pending.tenant_id == str(tenant.id):
            await check_new_password(db, tenant, user, body.password)
        try:
            challenge = await challenges.verify_code(body.challenge_id, body.code, "reset")
        except FrmError as error:
            if pending is not None and pending.tenant_id == str(tenant.id):
                locked = error.code == "FRM-AUTH-1004"
                await _audit(db, tenant, "auth.otp.locked" if locked else "auth.otp.failed",
                             Actor.user(user) if user else Actor.anonymous(pending.email),
                             outcome="blocked" if locked else "failure", reason=error.code,
                             metadata={"purpose": "reset", "channel": pending.channel,
                                       **({"attempts_left": error.details[0]["message"]} if error.details else {})})
                if locked:
                    await _security_alert(db, pending.email, "code_locked")
            error.commit = True
            raise
        await challenges.consume(challenge.id)
        if user is not None and challenge.tenant_id == str(tenant.id):
            if user.password_hash:
                db.add(UserPasswordHistory(tenant_id=tenant.id, organisation_id=tenant.organisation_id, user_id=user.id,
                                           password_hash=user.password_hash))
            user.password_hash = hash_password(body.password)
            user.password_changed_at = datetime.now(UTC)
            user.must_change_password = False
            await _audit(db, tenant, "auth.password.reset", Actor.user(user))
    return ok({"reset": True})


# ── OAuth (plaintext browser redirect) ───────────────────────────────────────────

@router.get("/auth/oauth/{provider}/start")
async def oauth_start(provider: str, intent: str | None = None) -> Any:
    """No identity provider is configured yet: back to the page with oauth=unavailable, exactly like the mock.
    Google, Microsoft, Apple and Facebook sign-in need each provider's client id and secret (B1, last step)."""
    page = "/auth/signup" if intent == "signup" else "/auth/login"
    return RedirectResponse(f"{page}?oauth=unavailable&provider={quote(provider)}", status_code=302)

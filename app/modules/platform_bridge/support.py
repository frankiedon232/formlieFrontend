"""Formalie support access, with the workspace's consent (PLATFORM-ADMIN-INTEGRATION §3).

- The workspace allows it (Settings → Security → Formalie support access): for 1 hour, 24 hours or 7 days, read
  only by default or with changes allowed. That is a grant; turning it off revokes it and ends every support session.
- Formalie can ask first (the internal API's `/support-access/requests`): the workspace's admins get a notice and
  approve (a grant) or decline. A request nobody answers expires after SUPPORT_REQUEST_DAYS.
- The platform admin starts a session against an active grant and gets a one-time ticket (SUPPORT_TICKET_SECONDS);
  the staff member's browser redeems it on the workspace's address (`POST /auth/support/redeem`) and gets a support
  token. The session ends at the grant's end or after SUPPORT_SESSION_MINUTES, whichever is first.
- In a session: what the Owner can see; read only unless both the grant and the session allow changes. Never the
  staff member's own profile, the consent itself, privacy requests, single sign-on, the sending address, or revealing
  secrets; even in write mode, nothing that gives access beyond the consent (SUPPORT_NO_CHANGE: people, invitations,
  roles, API tokens and keys, webhooks, connections, sign-in and security settings).
- Everyone in the workspace sees a banner while a session is live (`GET /support-access/status`, also in `/me`).
- Audit: the consent and its changes (`settings.updated`), requests and sessions issued (`workspace.updated`, as
  Formalie support), the session's start and end (`auth.login.succeeded`, `auth.logout`, `auth.session.revoked`),
  and every change made in a write session, as Formalie support under the staff member's name. What a support
  session viewed is in the request log (its requests carry the support session's id).
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.tiers import RedisCache
from app.core.config import get_settings
from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.security.fernet_tokens import make_token, read_token
from app.modules.audit.service import Actor, record
from app.modules.platform_bridge.models import SupportAccessGrant, SupportAccessRequest, SupportSession

HOURS = (1, 24, 168)
MODES = ("read", "write")
CACHE_MODULE = "support_access"
TOUCH_EVERY_S = 60
SUPPORT_TOKEN_MAX_S = 24 * 3600  # Fernet's own age limit for support tokens; the session's end decides first
# Never in a support session, whatever the mode (paths without the /api/v1 prefix). The sending address too: its
# own mail server would carry sign-in and reset codes (security review H3)
SUPPORT_NEVER = re.compile(r"^/(me/|settings/security/support-access|privacy/|settings/sso|settings/emails/sending)"
                           r"|/(reveal|secret)(/|$)")
# Never changed in a support session, even in write mode: anything that would give access that outlives the consent
# (security review M4): people, invitations and their links, the shared sign-up link and approvals, roles, API
# tokens, keys, services and endpoints, webhooks, data source connections and destinations, sign-in and security
# settings, the workspace's address and subdomain.
SUPPORT_NO_CHANGE = re.compile(
    r"^/(people|roles|api-tokens|api-service|api-services|api-endpoints|api-access-rules|webhooks|tenants"
    r"|settings/(security|signin|address))(/|$)"
    r"|^/(datasources|destinations)(/[^/]+)?/?$"
    r"|^/(datasources|destinations)/[^/]+/duplicate/?$")
READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def support_refusal(path: str, method: str, mode: str) -> str | None:
    """Why a support session may not make this request (the error details' message), or None."""
    if SUPPORT_NEVER.search(path):
        return "not_in_support_sessions"
    if method.upper() not in READ_METHODS:
        if mode != "write":
            return "read_only"
        if SUPPORT_NO_CHANGE.search(path):
            return "not_in_support_sessions"
    return None
_cache = RedisCache()


def now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def ticket_hash(ticket: str) -> str:
    return hashlib.sha256(ticket.encode()).hexdigest()


# ── Views ────────────────────────────────────────────────────────────────────────

def grant_view(g: SupportAccessGrant | None) -> dict[str, Any] | None:
    if g is None:
        return None
    return {"id": str(g.id), "mode": g.mode, "hours": g.hours, "starts_at": iso(g.starts_at),
            "expires_at": iso(g.expires_at), "granted_by": {"id": str(g.created_by) if g.created_by else None,
                                                            "name": g.granted_by_name},
            "request_id": str(g.request_id) if g.request_id else None}


def request_view(r: SupportAccessRequest) -> dict[str, Any]:
    return {"id": str(r.id), "staff_name": r.staff_name, "reason": r.reason, "mode": r.mode, "hours": r.hours,
            "status": r.status, "created_at": iso(r.created_at), "expires_at": iso(r.expires_at),
            "decided_at": iso(r.decided_at), "decided_by_name": r.decided_by_name}


def session_view(s: SupportSession) -> dict[str, Any]:
    live = s.redeemed_at is not None and s.ended_at is None and s.ends_at > now()
    return {"id": str(s.id), "staff_name": s.staff_name, "mode": s.mode, "started_at": iso(s.redeemed_at),
            "ends_at": iso(s.ends_at), "ended_at": iso(s.ended_at), "ended_reason": s.ended_reason, "active": live}


# ── Reading ──────────────────────────────────────────────────────────────────────

async def active_grant(db: AsyncSession, tenant_id: uuid.UUID) -> SupportAccessGrant | None:
    return (await db.execute(select(SupportAccessGrant).where(
        SupportAccessGrant.tenant_id == tenant_id, SupportAccessGrant.deleted_at.is_(None),
        SupportAccessGrant.revoked_at.is_(None), SupportAccessGrant.expires_at > now())
        .order_by(SupportAccessGrant.created_at.desc()).limit(1))).scalar_one_or_none()


async def live_sessions(db: AsyncSession, tenant_id: uuid.UUID) -> list[SupportSession]:
    return list((await db.execute(select(SupportSession).where(
        SupportSession.tenant_id == tenant_id, SupportSession.deleted_at.is_(None),
        SupportSession.ended_at.is_(None), SupportSession.ends_at > now()))).scalars())


async def state(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """SupportAccessState: the consent, Formalie's open requests and the latest sessions."""
    grant = await active_grant(db, tenant_id)
    requests = (await db.execute(select(SupportAccessRequest).where(
        SupportAccessRequest.tenant_id == tenant_id, SupportAccessRequest.deleted_at.is_(None),
        SupportAccessRequest.status == "pending", SupportAccessRequest.expires_at > now())
        .order_by(SupportAccessRequest.created_at.desc()))).scalars()
    sessions = (await db.execute(select(SupportSession).where(
        SupportSession.tenant_id == tenant_id, SupportSession.deleted_at.is_(None),
        SupportSession.redeemed_at.isnot(None)).order_by(SupportSession.redeemed_at.desc()).limit(20))).scalars()
    return {"grant": grant_view(grant), "requests": [request_view(r) for r in requests],
            "sessions": [session_view(s) for s in sessions], "hours": list(HOURS), "modes": list(MODES)}


async def banner(tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> dict[str, Any] | None:
    """The live support session everyone in the workspace sees a banner for (cached; the end is checked here)."""
    async def load() -> dict[str, Any]:
        async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
            live = [s for s in await live_sessions(db, tenant_id) if s.redeemed_at is not None]
        if not live:
            return {"none": True}
        s = max(live, key=lambda x: x.ends_at)
        return {"staff_name": s.staff_name, "mode": s.mode, "ends_at": iso(s.ends_at), "started_at": iso(s.redeemed_at)}

    value = await _cache.get_or_set(tenant_id, CACHE_MODULE, "banner", load, ttl_seconds=60)
    if value.get("none") or datetime.fromisoformat(value["ends_at"].replace("Z", "+00:00")) <= now():
        return None
    return {"active": True, **value}


async def forget(tenant_id: uuid.UUID) -> None:
    await _cache.invalidate(tenant_id, CACHE_MODULE)


# ── Changing ─────────────────────────────────────────────────────────────────────

def _describe(g: SupportAccessGrant | None) -> str | None:
    return f"{g.mode} until {iso(g.expires_at)}" if g is not None else None


async def end_sessions(db: AsyncSession, tenant_id: uuid.UUID, reason: str,
                       only: uuid.UUID | None = None) -> list[SupportSession]:
    rows = [s for s in await live_sessions(db, tenant_id) if only is None or s.grant_id == only]
    for s in rows:
        s.ended_at, s.ended_reason, s.ticket_hash = now(), reason, None
    return rows


async def allow(db: AsyncSession, tenant: TenantInfo, user: Any, *, hours: int, mode: str,
                request_id: uuid.UUID | None) -> SupportAccessGrant:
    """Turns support access on (or changes it: the open grant is extended in place, its sessions go on)."""
    if hours not in HOURS or mode not in MODES:
        raise FrmError("FRM-GEN-1002", [{"field": "hours" if hours not in HOURS else "mode", "message": "invalid"}])
    asked: SupportAccessRequest | None = None
    if request_id is not None:
        asked = await db.get(SupportAccessRequest, request_id)
        if asked is None or asked.tenant_id != tenant.id or asked.deleted_at is not None:
            raise FrmError("FRM-GEN-1004")
        if asked.status != "pending" or asked.expires_at <= now():
            raise FrmError("FRM-GEN-1009", [{"field": "request_id", "message": asked.status}])
    name = f"{user.first_name} {user.last_name}".strip()
    grant = await active_grant(db, tenant.id)
    before = _describe(grant)
    if grant is None:
        grant = SupportAccessGrant(tenant_id=tenant.id, organisation_id=tenant.organisation_id, mode=mode, hours=hours,
                                   starts_at=now(), expires_at=now() + timedelta(hours=hours),
                                   granted_by_name=name, request_id=request_id, created_by=user.id)
        db.add(grant)
    else:
        grant.mode, grant.hours, grant.expires_at = mode, hours, now() + timedelta(hours=hours)
        grant.granted_by_name, grant.updated_by = name, user.id
        grant.request_id = request_id or grant.request_id
    await db.flush()
    if asked is not None:
        asked.status, asked.decided_at, asked.decided_by, asked.decided_by_name = "approved", now(), user.id, name
        asked.grant_id = grant.id
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.updated",
                 actor=Actor.user(user), resource={"type": "setting", "id": None, "name": "Formalie support access"},
                 changes=[{"field": "support_access", "before": before, "after": _describe(grant)}],
                 metadata={"mode": mode, "hours": hours, **({"request_id": str(request_id)} if request_id else {})})
    await forget(tenant.id)
    return grant


async def revoke(db: AsyncSession, tenant: TenantInfo, user: Any) -> None:
    grant = await active_grant(db, tenant.id)
    ended = await end_sessions(db, tenant.id, "access_ended")
    if grant is None and not ended:
        return
    if grant is not None:
        grant.revoked_at, grant.revoked_by, grant.revoked_reason = now(), user.id, "turned_off"
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.updated",
                 actor=Actor.user(user), resource={"type": "setting", "id": None, "name": "Formalie support access"},
                 changes=[{"field": "support_access", "before": _describe(grant), "after": None}],
                 metadata={"sessions_ended": len(ended)})
    await forget(tenant.id)


async def decline(db: AsyncSession, tenant: TenantInfo, user: Any, request_id: uuid.UUID) -> None:
    asked = await db.get(SupportAccessRequest, request_id)
    if asked is None or asked.tenant_id != tenant.id or asked.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    if asked.status != "pending":
        raise FrmError("FRM-GEN-1009", [{"field": "request_id", "message": asked.status}])
    name = f"{user.first_name} {user.last_name}".strip()
    asked.status, asked.decided_at, asked.decided_by, asked.decided_by_name = "declined", now(), user.id, name
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.updated",
                 actor=Actor.user(user), resource={"type": "setting", "id": None, "name": "Formalie support access"},
                 changes=[{"field": "support_access_request", "before": "pending", "after": "declined"}],
                 metadata={"request_id": str(asked.id), "staff_name": asked.staff_name})


# ── Sessions: the ticket, redeeming it, and every request it makes ────────────────

async def issue_session(db: AsyncSession, grant: SupportAccessGrant, *, staff_id: str, staff_name: str,
                        approval_id: str | None, mode: str) -> tuple[SupportSession, str]:
    settings = get_settings()
    if mode not in MODES:
        raise FrmError("FRM-GEN-1002", [{"field": "mode", "message": "invalid"}])
    if mode == "write" and grant.mode != "write":
        raise FrmError("FRM-PERM-1001", [{"field": "mode", "message": "grant_read_only"}])
    ticket = secrets.token_urlsafe(32)
    session = SupportSession(
        tenant_id=grant.tenant_id, organisation_id=grant.organisation_id, grant_id=grant.id, staff_id=staff_id,
        staff_name=staff_name, approval_id=approval_id, mode=mode, ticket_hash=ticket_hash(ticket),
        ticket_expires_at=now() + timedelta(seconds=settings.support_ticket_seconds),
        ends_at=min(grant.expires_at, now() + timedelta(minutes=settings.support_session_minutes)))
    db.add(session)
    await db.flush()
    return session, ticket


def support_user(session: SupportSession, owner_role: Any, owner_id: uuid.UUID | None, contact_email: str | None) -> Any:
    """The person a support session acts as: never stored, never in People. What it makes belongs to the workspace's
    Owner (its id, for the records' owners and makers); the audit trail says Formalie support, by name."""
    from app.modules.users.models import User

    user = User(id=owner_id or session.id, tenant_id=session.tenant_id, organisation_id=session.organisation_id,
                email=contact_email or "support@formalie.com", first_name="Formalie support",
                last_name=session.staff_name, status="active", role_id=owner_role.id if owner_role else session.id,
                language=None, time_zone=None, date_format=None)
    user.support_staff = {"staff_id": session.staff_id, "staff_name": session.staff_name,  # type: ignore[attr-defined]
                          "approval_id": session.approval_id, "session_id": str(session.id), "mode": session.mode}
    return user


async def _owner(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[Any, uuid.UUID | None]:
    """The Owner role and the first active Owner's id."""
    from app.modules.users.models import Role, User

    role = (await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.built_in == "owner",
                                                Role.deleted_at.is_(None)))).scalars().first()
    owner_id = (await db.execute(select(User.id).where(
        User.tenant_id == tenant_id, User.role_id == role.id, User.status == "active", User.deleted_at.is_(None))
        .order_by(User.created_at).limit(1))).scalar_one_or_none() if role is not None else None
    return role, owner_id


async def redeem(tenant: TenantInfo, ticket: str) -> dict[str, Any]:
    """POST /auth/support/redeem: the ticket (once, in time, against a grant still open) → a support token."""
    from app.modules.auth.sessions import session_user
    from app.modules.platform_bridge.globals import support_contact

    if not ticket or len(ticket) > 100:
        raise FrmError("FRM-AUTH-1010")
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        session = (await db.execute(select(SupportSession).where(
            SupportSession.tenant_id == tenant.id, SupportSession.ticket_hash == ticket_hash(ticket),
            SupportSession.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
        grant = await db.get(SupportAccessGrant, session.grant_id) if session is not None else None
        if session is None or session.redeemed_at is not None or session.ended_at is not None \
                or session.ticket_expires_at <= now() or grant is None or grant.revoked_at is not None \
                or grant.expires_at <= now():
            raise FrmError("FRM-AUTH-1010")
        session.redeemed_at, session.last_seen_at, session.ticket_hash = now(), now(), None
        role, owner_id = await _owner(db, tenant.id)
        user = support_user(session, role, owner_id, (await support_contact()).get("email"))
        ctx = get_context()
        if ctx is not None:
            ctx.user_id, ctx.session_id = user.id, session.id
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="auth.login.succeeded",
                     actor=Actor.user(user), metadata={"method": "support", "mode": session.mode,
                                                       "support_session": str(session.id)})
        access = make_token({"t": "support", "sub": str(session.id), "tid": str(tenant.id),
                             "oid": str(tenant.organisation_id), "sid": str(session.id), "jti": secrets.token_hex(8)})
        profile = await session_user(db, user) if role is not None else {}
        view = {"session_id": str(session.id), "mode": min(session.mode, grant.mode, key=MODES.index),
                "staff_name": session.staff_name, "ends_at": iso(session.ends_at)}
        expires_in = max(1, int((session.ends_at - now()).total_seconds()))
    await forget(tenant.id)
    return {"access_token": access, "expires_in": expires_in, "user": {**profile, "support": True},
            "tenant": {"id": str(tenant.id), "name": tenant.name, "subdomain": tenant.subdomain},
            "organisation": {"id": str(tenant.organisation_id), "name": tenant.name}, "support": view}


def read_support_token(token: str) -> dict[str, Any] | None:
    payload = read_token(token, SUPPORT_TOKEN_MAX_S) if token else None
    return payload if payload and payload.get("t") == "support" else None


async def support_principal(request: Request, tenant: TenantInfo, payload: dict[str, Any]) -> Any:
    """require_auth for a support token: the session open and within its grant, the path allowed, read only unless
    both allow changes. → a Principal acting as the Owner, audited as Formalie support."""
    from app.modules.auth.sessions import Principal
    from app.modules.platform_bridge.globals import support_contact
    from app.modules.rbac.service import grants_of

    if payload.get("tid") != str(tenant.id):
        raise FrmError("FRM-TEN-1003", log_context={"security_event": "token_tenant_mismatch",
                                                     "token_tenant": payload.get("tid")})
    prefix = get_settings().api_prefix
    path = request.url.path
    path = path[len(prefix):] if path.startswith(prefix) else path
    session_id = uuid.UUID(payload["sid"])
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                          user_id=session_id) as db:
        session = await db.get(SupportSession, session_id)
        grant = await db.get(SupportAccessGrant, session.grant_id) if session is not None else None
        error: str | None = None
        if session is None or session.tenant_id != tenant.id or session.redeemed_at is None \
                or session.ended_at is not None or session.deleted_at is not None:
            error = "FRM-AUTH-1011"
        elif grant is None or grant.revoked_at is not None or grant.expires_at <= now() or session.ends_at <= now():
            session.ended_at, session.ended_reason = now(), "expired"
            error = "FRM-AUTH-1001"
        if error:
            await forget(tenant.id)
        else:
            assert session is not None and grant is not None
            if session.last_seen_at is None or (now() - session.last_seen_at).total_seconds() > TOUCH_EVERY_S:
                session.last_seen_at = now()
            role, owner_id = await _owner(db, tenant.id)
            user = support_user(session, role, owner_id, (await support_contact()).get("email"))
            mode = "write" if session.mode == "write" and grant.mode == "write" else "read"
    if error:
        raise FrmError(error, commit=True)
    refused = support_refusal(path, request.method, mode)
    if refused:
        raise FrmError("FRM-PERM-1001", [{"field": "support", "message": refused}])
    ctx = get_context()
    if ctx is not None:
        ctx.user_id, ctx.session_id = user.id, session_id
        ctx.extra["support_session"] = str(session_id)
    return Principal(user=user, role=role, tenant=tenant, session_id=session_id, grants=grants_of(role))


async def end_by_token(tenant: TenantInfo, token: str) -> bool:
    """POST /auth/support/end: the staff member leaves the workspace."""
    payload = read_support_token(token)
    if payload is None or payload.get("tid") != str(tenant.id):
        return False
    session_id = uuid.UUID(payload["sid"])
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                          user_id=session_id) as db:
        session = await db.get(SupportSession, session_id)
        if session is None or session.ended_at is not None:
            return False
        session.ended_at, session.ended_reason = now(), "signed_out"
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="auth.logout",
                     actor=Actor.support(session.staff_id, session.staff_name, session.approval_id),
                     metadata={"support_session": str(session.id)})
    await forget(tenant.id)
    return True


# ── Expiry (Beat, every minute) ──────────────────────────────────────────────────

async def expire_due() -> int:
    """Closes what ran out: grants past their end, sessions past theirs (or tickets never used), requests nobody
    answered. Access already stops at the end on its own; this keeps the records and the audit trail right."""
    async with db_session("write") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.support_due()"))).all()
    closed = 0
    for tenant_id, organisation_id in due:
        async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
            at = now()
            for g in (await db.execute(select(SupportAccessGrant).where(
                    SupportAccessGrant.tenant_id == tenant_id, SupportAccessGrant.revoked_at.is_(None),
                    SupportAccessGrant.deleted_at.is_(None), SupportAccessGrant.expires_at <= at))).scalars():
                g.revoked_at, g.revoked_reason = at, "expired"
                await record(db, tenant_id=tenant_id, organisation_id=organisation_id, action="settings.updated",
                             actor=Actor.system(), resource={"type": "setting", "id": None,
                                                             "name": "Formalie support access"},
                             changes=[{"field": "support_access", "before": _describe(g), "after": None}],
                             metadata={"cause": "expired"})
                closed += 1
            for s in (await db.execute(select(SupportSession).where(
                    SupportSession.tenant_id == tenant_id, SupportSession.ended_at.is_(None),
                    SupportSession.deleted_at.is_(None)))).scalars():
                unused = s.redeemed_at is None and s.ticket_expires_at <= at
                if s.ends_at > at and not unused:
                    continue
                s.ended_at, s.ended_reason, s.ticket_hash = at, "not_used" if unused else "expired", None
                if not unused:
                    await record(db, tenant_id=tenant_id, organisation_id=organisation_id,
                                 action="auth.session.revoked", actor=Actor.system(),
                                 metadata={"cause": "support_session_ended", "support_session": str(s.id),
                                           "staff_name": s.staff_name})
                closed += 1
            result = await db.execute(update(SupportAccessRequest).where(
                SupportAccessRequest.tenant_id == tenant_id, SupportAccessRequest.status == "pending",
                SupportAccessRequest.expires_at <= at).values(status="expired", updated_at=at))
            closed += result.rowcount or 0
        await forget(tenant_id)
    return closed

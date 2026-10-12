"""Sessions and tokens (SECURITY-PROTOCOL §5; port of the mock's core/auth.ts sessions part).

- Access token: Fernet {t, sub, tid, oid, sid, jti, mfa}, 15 minutes, never stored. Unknown or expired:
  FRM-AUTH-1001 (the client tries the refresh cookie first).
- Refresh token: random, single use, rotated on every refresh, kept as SHA-256 in `refresh_tokens`, one family per
  session; using one twice revokes the session (FRM-AUTH-1012, audited). Cookie `formalie_rt`, HttpOnly, Secure,
  SameSite=Strict, Path=/api/v1/auth, 7 days.
- The session ends after the workspace's idle time (sliding: every request and refresh counts) or its maximum length
  (Settings → Security): FRM-AUTH-1001, and the client shows sign-in with "Your session expired".
"""

from __future__ import annotations

import hashlib
import ipaddress
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.logging.geo import get_geo
from app.core.middleware.tenant import require_tenant
from app.core.security.fernet_tokens import make_token, read_token
from app.modules.audit.service import Actor, device_from, record
from app.modules.auth.models import RefreshToken, UserSession
from app.modules.rbac.permissions import permission_for
from app.modules.rbac.service import grants_of, permissions_of, role_key, role_name
from app.modules.settings.service import get_section
from app.modules.users.models import Role, User

ACCESS_TTL_S = 15 * 60
REFRESH_TTL_S = 7 * 24 * 60 * 60
REFRESH_COOKIE = "formalie_rt"
REFRESH_COOKIE_PATH = "/api/v1/auth"
TOUCH_EVERY_S = 60


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def refresh_cookie(token: str) -> dict[str, Any]:
    """Keyword arguments for Response.set_cookie."""
    return {"key": REFRESH_COOKIE, "value": token, "httponly": True, "secure": True, "samesite": "strict",
            "path": REFRESH_COOKIE_PATH, "max_age": REFRESH_TTL_S}


async def session_user(db: AsyncSession, user: User) -> dict[str, Any]:
    """SessionUser (shared/types/auth.ts): the person, their role and what it allows."""
    role = await db.get(Role, user.role_id)
    grants = grants_of(role)
    return {
        "id": str(user.id), "first_name": user.first_name, "last_name": user.last_name, "email": user.email,
        "avatar_url": None,  # profile photos arrive with uploads (B3)
        "role": role_key(role), "role_name": role_name(role) or role_key(role),
        "permissions": permissions_of(grants), "grants": grants,
        "language": user.language, "time_zone": user.time_zone, "date_format": user.date_format,
    }


async def _tokens(db: AsyncSession, user: User, tenant: TenantInfo, session: UserSession,
                  family_id: uuid.UUID) -> tuple[dict[str, Any], str]:
    refresh = secrets.token_urlsafe(32)
    row = RefreshToken(tenant_id=tenant.id, organisation_id=tenant.organisation_id, session_id=session.id,
                       family_id=family_id, token_hash=_hash(refresh), expires_at=_now() + timedelta(seconds=REFRESH_TTL_S))
    db.add(row)
    access = make_token({"t": "access", "sub": str(user.id), "tid": str(tenant.id), "oid": str(tenant.organisation_id),
                         "sid": str(session.id), "jti": secrets.token_hex(8), "mfa": True})
    session.last_active_at = _now()
    user.last_active_at = _now()
    await db.flush()
    tokens = {
        "access_token": access, "expires_in": ACCESS_TTL_S, "user": await session_user(db, user),
        "tenant": {"id": str(tenant.id), "name": tenant.name, "subdomain": tenant.subdomain},
        "organisation": {"id": str(tenant.organisation_id), "name": tenant.name},
    }
    return tokens, refresh


async def start_session(db: AsyncSession, user: User, tenant: TenantInfo, method: str) -> tuple[dict[str, Any], str]:
    """A new signed-in session: AuthTokens and the refresh token for the cookie."""
    ctx = get_context()
    ip = ctx.client_ip if ctx else None
    geo = get_geo().lookup(ip) if ip else {}
    session = UserSession(tenant_id=tenant.id, organisation_id=tenant.organisation_id, user_id=user.id,
                          ip=ip if ip and ip != "unknown" else None, device=device_from(ctx.user_agent if ctx else None),
                          city=geo.get("city"), country=geo.get("country"), method=method)
    db.add(session)
    await db.flush()
    return await _tokens(db, user, tenant, session, family_id=session.id)


async def _limits(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[timedelta, timedelta]:
    sessions = (await get_section(db, tenant_id, "security"))["sessions"]
    return timedelta(minutes=sessions["idle_minutes"]), timedelta(hours=sessions["max_hours"])


async def _expired(db: AsyncSession, session: UserSession) -> bool:
    """True (and the session ends) after the idle time without activity, or at the maximum length."""
    idle, longest = await _limits(db, session.tenant_id)
    now = _now()
    if now - session.last_active_at <= idle and now - session.started_at <= longest:
        return False
    session.revoked_at, session.revoked_reason = now, "expired"
    return True


async def rotate_refresh(token: str | None, tenant: TenantInfo) -> tuple[dict[str, Any], str]:
    """POST /auth/refresh: single use. Reusing an old token revokes the whole session (FRM-AUTH-1012).
    Runs its own transaction, so a revocation is saved even though the request then fails."""
    error: str | None = None
    result: tuple[dict[str, Any], str] | None = None
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(token)))).scalar_one_or_none()             if token else None
        session = await db.get(UserSession, row.session_id) if row is not None else None
        user = await db.get(User, session.user_id) if session is not None else None
        if row is None or row.expires_at < _now():
            error = "FRM-AUTH-1010"
        elif session is None or session.revoked_at is not None or session.deleted_at is not None or user is None:
            error = "FRM-AUTH-1011"
        elif await _expired(db, session):
            error = "FRM-AUTH-1001"
        elif row.used_at is not None or row.revoked_at is not None:
            session.revoked_at, session.revoked_reason = _now(), "refresh_reuse"
            await db.execute(update(RefreshToken).where(RefreshToken.family_id == row.family_id,
                                                        RefreshToken.revoked_at.is_(None)).values(revoked_at=_now()))
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="auth.session.revoked",
                         actor=Actor.user(user), outcome="blocked", reason="FRM-AUTH-1012",
                         metadata={"cause": "refresh_token_reuse"})
            error = "FRM-AUTH-1012"
        else:
            row.used_at = _now()
            tokens, refresh = await _tokens(db, user, tenant, session, family_id=row.family_id)
            row.replaced_by = (await db.execute(
                select(RefreshToken.id).where(RefreshToken.token_hash == _hash(refresh)))).scalar_one()
            result = (tokens, refresh)
    if error:
        raise FrmError(error)
    assert result is not None
    return result


async def end_session(db: AsyncSession, refresh: str | None, access: str | None) -> tuple[UserSession, User] | None:
    """Revokes the session behind the refresh cookie and / or the bearer; returns it (for the audit trail)."""
    ids: list[uuid.UUID] = []
    if refresh:
        row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(refresh)))).scalar_one_or_none()
        if row is not None:
            ids.append(row.session_id)
    payload = read_token(access, ACCESS_TTL_S) if access else None
    if payload and payload.get("t") == "access":
        ids.append(uuid.UUID(payload["sid"]))
    ended: tuple[UserSession, User] | None = None
    for sid in ids:
        session = await db.get(UserSession, sid)
        if session is not None and session.revoked_at is None:
            session.revoked_at, session.revoked_reason = _now(), "signed_out"
            await db.execute(update(RefreshToken).where(RefreshToken.session_id == sid, RefreshToken.revoked_at.is_(None))
                             .values(revoked_at=_now()))
            user = await db.get(User, session.user_id)
            if user is not None:
                ended = (session, user)
    return ended


def ip_allowed(security: dict[str, Any], ip: str | None) -> bool:
    """Settings → Security: no allowlist, or the address is on it (ipAllowed)."""
    allow = security.get("ip_allowlist") or {}
    if not allow.get("enabled"):
        return True
    try:
        address = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    for entry in allow.get("entries", []):
        try:
            if address in ipaddress.ip_network(str(entry.get("value", "")), strict=False):
                return True
        except ValueError:
            continue
    return False


@dataclass
class Principal:
    """The signed-in person behind a request."""

    user: User
    role: Role | None
    tenant: TenantInfo
    session_id: uuid.UUID
    grants: dict[str, str] = field(default_factory=dict)

    @property
    def permissions(self) -> set[str]:
        return set(self.grants)

    def can(self, permission: str) -> bool:
        return permission in self.grants


async def require_auth(request: Request) -> Principal:
    """Protected routes (requireAuth): a valid bearer for this host's workspace, an open session within its limits,
    from an allowed network, and the permission the address needs (Roles & access)."""
    tenant = require_tenant()
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else ""
    payload = read_token(token, ACCESS_TTL_S) if token else None
    if not payload or payload.get("t") != "access":
        from app.modules.platform_bridge.support import read_support_token, support_principal

        support = read_support_token(token)
        if support is not None:  # Formalie support, with the workspace's consent (B16)
            return _writable(request, tenant, await support_principal(request, tenant, support))
        raise FrmError("FRM-AUTH-1001")
    if payload.get("tid") != str(tenant.id):
        # A token of another workspace on this host: refused and logged as a security event
        raise FrmError("FRM-TEN-1003", log_context={"security_event": "token_tenant_mismatch",
                                                     "token_tenant": payload.get("tid")})
    ctx = get_context()
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                          user_id=uuid.UUID(payload["sub"])) as db:
        error: str | None = None
        principal: Principal | None = None
        session = await db.get(UserSession, uuid.UUID(payload["sid"]))
        user = await db.get(User, session.user_id) if session is not None else None
        if session is None or session.revoked_at is not None or session.deleted_at is not None                 or user is None or user.deleted_at is not None:
            error = "FRM-AUTH-1011"
        elif await _expired(db, session):  # the session ends (saved: the error is raised after the commit)
            error = "FRM-AUTH-1001"
        elif not ip_allowed(await get_section(db, tenant.id, "security"), ctx.client_ip if ctx else None):
            error = "FRM-AUTH-1016"
        else:
            if (_now() - session.last_active_at).total_seconds() > TOUCH_EVERY_S:
                session.last_active_at = _now()
                user.last_active_at = _now()
            role = await db.get(Role, user.role_id)
            principal = Principal(user=user, role=role, tenant=tenant, session_id=session.id, grants=grants_of(role))
    if error:
        raise FrmError(error)
    assert principal is not None and user is not None and session is not None
    path = request.url.path
    prefix = get_settings().api_prefix
    needed = permission_for(request.method, path[len(prefix):] if path.startswith(prefix) else path)
    if needed and not principal.can(needed):
        raise FrmError("FRM-PERM-1001")
    if ctx is not None:
        ctx.user_id, ctx.session_id = user.id, session.id
    return _writable(request, tenant, principal)


# A read-only or closing workspace (set by the platform admin, B16) still lets people sign in, look, export and
# manage their own profile, billing and Formalie's support access; nothing else changes.
_READ_ONLY_ALLOWED = ("/me", "/auth/", "/billing", "/settings/security/support-access", "/notifications")


def _writable(request: Request, tenant: TenantInfo, principal: Principal) -> Principal:
    if tenant.status in ("read_only", "closing") and request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
        prefix = get_settings().api_prefix
        path = request.url.path[len(prefix):] if request.url.path.startswith(prefix) else request.url.path
        exports = path.endswith("/export") or path.endswith("/exports") or "/exports/" in path
        if not path.startswith(_READ_ONLY_ALLOWED) and not exports:
            raise FrmError("FRM-PERM-1001", [{"field": "workspace", "message": tenant.status}])
    return principal


async def require_admin(request: Request) -> Principal:
    """requireAdmin(): the route's own permission when it has one (checked by require_auth), otherwise someone who
    manages the workspace (`settings.manage`)."""
    principal = await require_auth(request)
    path = request.url.path
    prefix = get_settings().api_prefix
    if permission_for(request.method, path[len(prefix):] if path.startswith(prefix) else path) is None \
            and not principal.can("settings.manage"):
        raise FrmError("FRM-PERM-1001")
    return principal


async def active_sessions(db: AsyncSession, tenant_id: uuid.UUID, current: uuid.UUID | None) -> list[dict[str, Any]]:
    """activeSessions(): the workspace's open sessions within its limits, most recently active first."""
    idle, longest = await _limits(db, tenant_id)
    now = _now()
    rows = (await db.execute(
        select(UserSession, User).join(User, (User.id == UserSession.user_id) & (User.tenant_id == UserSession.tenant_id))
        .where(UserSession.tenant_id == tenant_id, UserSession.revoked_at.is_(None), UserSession.deleted_at.is_(None),
               UserSession.last_active_at >= now - idle, UserSession.started_at >= now - longest)
        .order_by(UserSession.last_active_at.desc()))).all()

    def iso(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    return [{
        "id": str(s.id), "user": {"name": f"{u.first_name} {u.last_name}".strip(), "email": u.email},
        "current": s.id == current, "started_at": iso(s.started_at), "last_active_at": iso(s.last_active_at),
        "ip": str(s.ip) if s.ip else "unknown", "device": s.device or {"type": "unknown", "browser": None, "os": None},
    } for s, u in rows]


async def revoke_sessions(db: AsyncSession, tenant_id: uuid.UUID, *, ids: list[uuid.UUID] | None,
                          keep: uuid.UUID | None, reason: str = "signed_out_by_admin",
                          user_id: uuid.UUID | None = None) -> list[tuple[UserSession, User]]:
    """revokeSessions(): the chosen open sessions (or all, or all of one person) of the workspace, never `keep`."""
    query = (select(UserSession, User)
             .join(User, (User.id == UserSession.user_id) & (User.tenant_id == UserSession.tenant_id))
             .where(UserSession.tenant_id == tenant_id, UserSession.revoked_at.is_(None),
                    UserSession.deleted_at.is_(None)))
    if keep is not None:
        query = query.where(UserSession.id != keep)
    if ids is not None:
        query = query.where(UserSession.id.in_(ids))
    if user_id is not None:
        query = query.where(UserSession.user_id == user_id)
    ended = [(row[0], row[1]) for row in (await db.execute(query)).all()]
    now = _now()
    for session, _ in ended:
        session.revoked_at, session.revoked_reason = now, reason
    if ended:
        await db.execute(update(RefreshToken).where(RefreshToken.session_id.in_([s.id for s, _ in ended]),
                                                    RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
    return ended

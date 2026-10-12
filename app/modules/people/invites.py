"""Ways into a workspace (mock: routes/invites.ts, owner 2026-10-09; API-CONTRACT → People).

- User profiles: an admin makes the full profile; the person gets an activation email, sets a password and signs in
  (not_activated → active).
- Personal sign-up links: the person signs up, then waits for approval (invited → pending).
- The workspace's shared link: anyone with it asks to join (domains optional), then waits for approval (pending).
- Approval completes the profile (role, departments, job titles, manager); rejection removes the request.
Personal links work 7 days and are kept as hashes; the shared one works until it is turned off or renewed.
Removing someone (a withdrawn invitation, a rejected request) is a soft delete.

    POST   /people                          a user profile (activation email)
    POST   /people/invites                  personal sign-up links
    POST   /people/{id}/invite/resend · /invite/link · DELETE /people/{id}/invite
    GET · PUT /people/signup-link · POST /people/signup-link/new
    POST   /people/{id}/approve · /reject
    GET    /public/invites/{token}          what the sign-up page shows
    POST   /public/invites/{token}/accept   { first_name, last_name, email?, phone?, password }
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.core import zod as z
from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import require_tenant
from app.core.responses import ok
from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.core.security.limits import rate_limit
from app.core.security.passwords import hash_password
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.emails import workspace as workspace_mail
from app.modules.org import service as org
from app.modules.people import service
from app.modules.people.models import SignupLink, UserInvite
from app.modules.people.router import Manager, _person
from app.modules.rbac.service import find_role, role_key
from app.modules.settings.service import get_section
from app.modules.users.models import Role, User

router = APIRouter(tags=["invites"])

DAYS = 7
_PHONE = r"^\+[1-9][\d\s-]{6,18}$"
_ids = z.array(z.string().max(64)).max(20)


def _default(value: Any) -> Any:
    return [] if value is z.MISSING else value


profile_schema = z.obj(
    first_name=z.string().trim().min(1).max(60), last_name=z.string().trim().min(1).max(60),
    email=z.string().email().max(200), phone=z.string().trim().regex(_PHONE).nullable().optional(),
    role=z.string().min(1).max(64), department_ids=_ids.optional(), job_title_ids=_ids.optional(),
    manager_id=z.string().max(64).nullable().optional(),
)
invite_schema = z.obj(
    emails=z.array(z.string().email().max(200)).min(1).max(50), role=z.string().min(1).max(64),
    department_ids=_ids.optional(), job_title_ids=_ids.optional(),
    message=z.string().trim().max(500).nullable().optional(),
)
link_schema = z.obj(enabled=z.boolean().optional(),
                    domains=z.array(z.string().trim().lower().regex(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")).max(20).optional())
approve_schema = z.obj(role=z.string().min(1).max(64), department_ids=_ids.optional(), job_title_ids=_ids.optional(),
                       manager_id=z.string().max(64).nullable().optional())
reject_schema = z.obj(reason=z.string().trim().max(500).nullable().optional())
accept_schema = z.obj(
    first_name=z.string().trim().min(1).max(60), last_name=z.string().trim().min(1).max(60),
    email=z.string().email().max(200).optional(), phone=z.string().trim().regex(_PHONE).nullable().optional(),
    password=z.string().min(1).max(200),
)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _link(token: str) -> str:
    """The workspace's own address (the host this request came to)."""
    ctx = get_context()
    return f"https://{(ctx.host if ctx else None) or ''}/auth/join/{token}"


def _phone(value: str | None) -> str | None:
    return re.sub(r"[\s-]", "", value) if value else None


async def _language(db: Any, tenant_id: uuid.UUID) -> str:
    return (await get_section(db, tenant_id, "localisation")).get("language") or "en"


async def _assignable_role(db: Any, tenant_id: uuid.UUID, key: str) -> Role:
    """Any role but Owner (FRM-USER-1009)."""
    role = await find_role(db, tenant_id, key)
    if role is None or role.built_in == "owner":
        raise FrmError("FRM-USER-1009")
    return role


async def _email_taken(db: Any, tenant_id: uuid.UUID, email: str) -> User | None:
    return (await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                func.lower(User.email) == email.lower()))).scalar_one_or_none()


async def _fresh_link(db: Any, principal: Principal, user: User, message: str | None) -> tuple[str, UserInvite]:
    """A new personal link (activation or sign-up); the old one stops working."""
    now = datetime.now(UTC)
    for old in (await db.execute(select(UserInvite).where(UserInvite.tenant_id == user.tenant_id,
                                                          UserInvite.user_id == user.id,
                                                          UserInvite.revoked_at.is_(None)))).scalars():
        old.revoked_at = now
    token = secrets.token_urlsafe(24)
    invite = UserInvite(tenant_id=user.tenant_id, organisation_id=user.organisation_id, user_id=user.id,
                        kind="activation" if user.status == "not_activated" else "invite", token_hash=_hash(token),
                        sent_at=now, expires_at=now + timedelta(days=DAYS), invited_by=principal.user.id,
                        invited_by_name=service.name_of(principal.user), message=message, created_by=principal.user.id)
    db.add(invite)
    await db.flush()
    return _link(token), invite


async def _mail(db: Any, principal: Principal, user: User, link: str) -> None:
    """A profile the organisation made: activate it; a sign-up link: the invitation email."""
    tenant, by = principal.tenant, service.name_of(principal.user)
    language = await _language(db, tenant.id)
    # The workspace's look and wording, its sending address and sent log (the personal link shows as dots there)
    if user.status == "not_activated":
        await workspace_mail.send(db, tenant.id, tenant.name, to=user.email, key="account_activation", language=language,
                                  values={"name": user.first_name or user.email, "inviter": by, "link": link,
                                          "days": DAYS}, reason="invitation", hidden=("link",))
    else:
        await workspace_mail.send(db, tenant.id, tenant.name, to=user.email, key="invitation", language=language,
                                  values={"name": user.first_name or user.email, "inviter": by, "link": link},
                                  reason="invitation", hidden=("link",))


async def _audit(db: Any, principal: Principal, action: str, user: User, metadata: dict[str, str] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), metadata=metadata or {},
                 resource={"type": "user", "id": str(user.id), "name": service.name_of(user)})


async def _join_org(db: Any, principal: Principal, user: User, departments: list[str], jobs: list[str]) -> None:
    tenant = principal.tenant
    for kind, ids in (("departments", departments), ("job_titles", jobs)):
        await org.set_person_units(db, tenant.id, tenant.organisation_id, user.id, kind, ids, principal.user.id)


# ── User profiles ───────────────────────────────────────────────────────────────

@router.post("/people", status_code=201, dependencies=[rate_limit("people-create", per_minute=30)])
async def create_profile(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = profile_schema.parse(await request.json())
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        role = await _assignable_role(db, tenant.id, body["role"])
        email = body["email"].strip().lower()
        if await _email_taken(db, tenant.id, email):
            raise FrmError("FRM-USER-1011")
        manager = None
        if body.get("manager_id"):
            try:
                manager = await _person(db, tenant.id, body["manager_id"])
            except FrmError:
                manager = None
        user = User(tenant_id=tenant.id, organisation_id=tenant.organisation_id, email=email,
                    first_name=body["first_name"], last_name=body["last_name"], phone=_phone(body.get("phone")),
                    status="not_activated", role_id=role.id, manager_id=manager.id if manager else None,
                    joined_at=datetime.now(UTC), created_by=principal.user.id)
        db.add(user)
        await db.flush()
        await _join_org(db, principal, user, _default(body.get("department_ids", z.MISSING)),
                        _default(body.get("job_title_ids", z.MISSING)))
        link, _ = await _fresh_link(db, principal, user, None)
        await _mail(db, principal, user, link)
        await _audit(db, principal, "users.profile_created", user, {"role": role_key(role)})
        return ok(await service.detail_of(db, tenant.id, user.id))


# ── Personal sign-up links ──────────────────────────────────────────────────────

@router.post("/people/invites", status_code=201, dependencies=[rate_limit("people-invite", per_minute=20)])
async def invite_people(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = invite_schema.parse(await request.json())
    tenant = principal.tenant
    result: dict[str, Any] = {"invited": 0, "skipped": []}
    async with db_session("write", **_scope(principal)) as db:
        role = await _assignable_role(db, tenant.id, body["role"])
        for email in dict.fromkeys(e.strip().lower() for e in body["emails"]):
            existing = await _email_taken(db, tenant.id, email)
            if existing:
                result["skipped"].append({"email": email, "reason": "invited" if existing.status == "invited" else "member"})
                continue
            # The role, departments and job titles are a starting point: confirmed when approved
            user = User(tenant_id=tenant.id, organisation_id=tenant.organisation_id, email=email, first_name="",
                        last_name="", status="invited", role_id=role.id, joined_at=datetime.now(UTC),
                        created_by=principal.user.id)
            db.add(user)
            await db.flush()
            await _join_org(db, principal, user, body.get("department_ids") or [], body.get("job_title_ids") or [])
            link, _ = await _fresh_link(db, principal, user, body.get("message"))
            await _mail(db, principal, user, link)
            await _audit(db, principal, "users.invited", user, {"role": role_key(role)})
            result["invited"] += 1
    return ok(result)


async def _link_out(db: Any, tenant_id: uuid.UUID, person_id: str) -> User:
    user = await _person(db, tenant_id, person_id, invited=True)
    if user.status not in ("invited", "not_activated"):
        raise FrmError("FRM-GEN-1004")
    return user


async def _open_invite(db: Any, user: User) -> UserInvite | None:
    return (await service.current_invites(db, user.tenant_id)).get(user.id)


@router.post("/people/{person_id}/invite/resend", dependencies=[rate_limit("people-invite", per_minute=20)])
async def resend_invite(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        user = await _link_out(db, principal.tenant.id, person_id)
        previous = await _open_invite(db, user)
        link, invite = await _fresh_link(db, principal, user, previous.message if previous else None)
        await _mail(db, principal, user, link)
        await _audit(db, principal, "users.invite_resent", user)
        return ok({"expires_at": service.iso(invite.expires_at)})


@router.post("/people/{person_id}/invite/link", dependencies=[rate_limit("people-invite", per_minute=20)])
async def invite_link(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        user = await _link_out(db, principal.tenant.id, person_id)
        previous = await _open_invite(db, user)
        link, invite = await _fresh_link(db, principal, user, previous.message if previous else None)
        await _audit(db, principal, "users.invite_link", user)
        return ok({"link": link, "expires_at": service.iso(invite.expires_at)})


async def _remove(db: Any, principal: Principal, user: User) -> None:
    """Withdraws a person who never got in: their row and memberships keep deleted_at, their links stop."""
    now = datetime.now(UTC)
    user.deleted_at, user.deleted_by = now, principal.user.id
    await org.leave_all(db, user.tenant_id, user.id, principal.user.id)
    for invite in (await db.execute(select(UserInvite).where(UserInvite.tenant_id == user.tenant_id,
                                                             UserInvite.user_id == user.id,
                                                             UserInvite.revoked_at.is_(None)))).scalars():
        invite.revoked_at = now


@router.delete("/people/{person_id}/invite", dependencies=[rate_limit("people-invite", per_minute=30)])
async def revoke_invite(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        user = await _link_out(db, principal.tenant.id, person_id)
        await _remove(db, principal, user)
        await _audit(db, principal, "users.invite_revoked", user)
        return ok({"id": str(user.id)})


# ── The workspace's shared link ─────────────────────────────────────────────────

async def _signup_link(db: Any, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> SignupLink:
    """The link (made the first time, off until an admin turns it on)."""
    link = (await db.execute(select(SignupLink).where(SignupLink.tenant_id == tenant_id,
                                                      SignupLink.deleted_at.is_(None)))).scalar_one_or_none()
    if link is None:
        token = f"w{secrets.token_urlsafe(18)}"
        link = SignupLink(tenant_id=tenant_id, organisation_id=organisation_id, enabled=False,
                          token_enc=encrypt_secret(token), token_hash=_hash(token), domains=[])
        db.add(link)
        await db.flush()
    return link


async def _link_view(db: Any, tenant_id: uuid.UUID, link: SignupLink) -> dict[str, Any]:
    pending = (await db.execute(select(func.count()).select_from(User).where(
        User.tenant_id == tenant_id, User.status == "pending", User.deleted_at.is_(None)))).scalar_one()
    return {"enabled": link.enabled, "link": _link(decrypt_secret(link.token_enc)), "domains": link.domains,
            "updated_at": service.iso(link.updated_at), "pending": int(pending)}


@router.get("/people/signup-link", dependencies=[rate_limit("signup-link", per_minute=60)])
async def get_signup_link(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        link = await _signup_link(db, principal.tenant.id, principal.tenant.organisation_id)
        view = await _link_view(db, principal.tenant.id, link)
    if getattr(principal.user, "support_staff", None) is not None:
        view["link"] = ""  # Formalie support sees whether it is on, never the link itself (security review M4)
    return ok(view)


@router.put("/people/signup-link", dependencies=[rate_limit("signup-link", per_minute=30)])
async def update_signup_link(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = link_schema.parse(await request.json())
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        link = await _signup_link(db, tenant.id, tenant.organisation_id)
        if "enabled" in body:
            link.enabled = body["enabled"]
        if "domains" in body:
            link.domains = list(dict.fromkeys(body["domains"]))
        link.updated_at, link.updated_by = datetime.now(UTC), principal.user.id
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="users.signup_link_changed",
                     actor=Actor.user(principal.user),
                     metadata={"enabled": "true" if link.enabled else "false", "domains": ", ".join(link.domains) or "any"})
        return ok(await _link_view(db, tenant.id, link))


@router.post("/people/signup-link/new", dependencies=[rate_limit("signup-link", per_minute=10)])
async def renew_signup_link(principal: Principal = Depends(require_admin)) -> Any:
    """A new link stops the old one."""
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        link = await _signup_link(db, tenant.id, tenant.organisation_id)
        token = f"w{secrets.token_urlsafe(18)}"
        link.token_enc, link.token_hash = encrypt_secret(token), _hash(token)
        link.updated_at, link.updated_by = datetime.now(UTC), principal.user.id
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="users.signup_link_changed",
                     actor=Actor.user(principal.user), metadata={"renewed": "true"})
        return ok(await _link_view(db, tenant.id, link))


# ── Approval ────────────────────────────────────────────────────────────────────

async def _pending(db: Any, tenant_id: uuid.UUID, person_id: str) -> User:
    user = await _person(db, tenant_id, person_id)
    if user.status != "pending":
        raise FrmError("FRM-GEN-1004")
    return user


@router.post("/people/{person_id}/approve", dependencies=[rate_limit("people-approve", per_minute=30)])
async def approve_person(person_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = approve_schema.parse(await request.json())
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        user = await _pending(db, tenant.id, person_id)
        role = await _assignable_role(db, tenant.id, body["role"])
        user.role_id, user.status, user.joined_at = role.id, "active", datetime.now(UTC)
        user.request_via, user.requested_at = None, None
        if body.get("manager_id"):
            await Manager(db, principal).set_manager(user, body["manager_id"])
        await _join_org(db, principal, user, body.get("department_ids") or [], body.get("job_title_ids") or [])
        ctx = get_context()
        await workspace_mail.send(db, tenant.id, tenant.name, to=user.email, key="account_approved",
                                  language=await _language(db, tenant.id), reason="approval", values={
                                      "name": user.first_name or user.email, "inviter": service.name_of(principal.user),
                                      "link": f"https://{(ctx.host if ctx else '') or ''}/auth/login"})
        await _audit(db, principal, "users.approved", user, {"role": role_key(role)})
        await db.flush()
        return ok(await service.detail_of(db, tenant.id, user.id))


@router.post("/people/{person_id}/reject", dependencies=[rate_limit("people-approve", per_minute=30)])
async def reject_person(person_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    raw = await request.body()
    body = reject_schema.parse((await request.json()) if raw else {})
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        user = await _pending(db, tenant.id, person_id)
        await _remove(db, principal, user)
        reason = body.get("reason")
        await workspace_mail.send(db, tenant.id, tenant.name, to=user.email, key="account_rejected",
                                  language=await _language(db, tenant.id), reason="approval",
                                  values={"name": user.first_name or user.email, "reason": reason or ""})
        await _audit(db, principal, "users.rejected", user, {"reason": reason} if reason else {})
        return ok({"id": str(user.id)})


# ── The sign-up page (public, on the workspace's own address) ───────────────────

async def _find_link(db: Any, tenant: TenantInfo, token: str) -> tuple[str, User | None, UserInvite | None, SignupLink | None]:
    """(kind, person, their invite, the shared link): FRM-USER-1001 expired, FRM-USER-1002 unknown or used."""
    if not token or len(token) > 100:
        raise FrmError("FRM-USER-1002")
    hashed = _hash(token)
    shared = (await db.execute(select(SignupLink).where(SignupLink.tenant_id == tenant.id, SignupLink.token_hash == hashed,
                                                        SignupLink.enabled.is_(True), SignupLink.deleted_at.is_(None))
                               )).scalar_one_or_none()
    if shared is not None:
        return "link", None, None, shared
    invite = (await db.execute(select(UserInvite).where(UserInvite.tenant_id == tenant.id, UserInvite.token_hash == hashed,
                                                        UserInvite.revoked_at.is_(None)))).scalar_one_or_none()
    user = await db.get(User, invite.user_id) if invite else None
    if invite is None or user is None or user.deleted_at is not None or user.status not in ("invited", "not_activated"):
        raise FrmError("FRM-USER-1002")
    if invite.expires_at < datetime.now(UTC):
        raise FrmError("FRM-USER-1001")
    return invite.kind, user, invite, None


@router.get("/public/invites/{token}", dependencies=[rate_limit("invite-preview", per_minute=30)])
async def preview_invite(token: str) -> Any:
    tenant = require_tenant()
    async with db_session("read", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        kind, user, invite, shared = await _find_link(db, tenant, token)
        role = await db.get(Role, user.role_id) if user else None
    return ok({
        "kind": kind, "workspace": tenant.name, "email": user.email if user else None,
        "first_name": user.first_name if user else "", "last_name": user.last_name if user else "",
        "inviter": invite.invited_by_name if invite else None, "role": role_key(role) if role else None,
        "role_name": role.name if role else None, "message": invite.message if invite else None,
        "domains": shared.domains if shared else [],
    })


@router.post("/public/invites/{token}/accept", dependencies=[rate_limit("invite-accept", per_minute=10)])
async def accept_invite(token: str, request: Request) -> Any:
    from app.modules.auth.router import check_new_password

    tenant = require_tenant()
    body = accept_schema.parse(await request.json())
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        kind, user, invite, shared = await _find_link(db, tenant, token)
        await check_new_password(db, tenant, None, body["password"])
        now = datetime.now(UTC)
        if user is None:
            # The shared link: a new person, with the email they typed (checked against the domains)
            email = (body.get("email") or "").strip().lower()
            if not email:
                raise FrmError("FRM-GEN-1002", [{"field": "email", "message": "required"}])
            if await _email_taken(db, tenant.id, email):
                raise FrmError("FRM-USER-1011")
            domains = shared.domains if shared else []
            if domains and email.rsplit("@", 1)[-1] not in domains:
                raise FrmError("FRM-USER-1012", [{"field": "email", "message": ", ".join(domains)}])
            member = await find_role(db, tenant.id, "member")
            user = User(tenant_id=tenant.id, organisation_id=tenant.organisation_id, email=email, first_name="",
                        last_name="", status="pending", role_id=member.id, joined_at=now)  # type: ignore[union-attr]
            db.add(user)
            await db.flush()
        activation = kind == "activation"
        user.first_name, user.last_name = body["first_name"], body["last_name"]
        user.phone = _phone(body.get("phone")) or user.phone
        user.password_hash, user.password_changed_at = hash_password(body["password"]), now
        if activation:
            user.status, user.joined_at = "active", now
        else:
            user.status, user.request_via, user.requested_at = "pending", "link" if kind == "link" else "invite", now
        if invite is not None:
            invite.revoked_at = now  # used: the link stops working
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                     action="users.joined" if activation else "users.requested", actor=Actor.user(user),
                     resource={"type": "user", "id": str(user.id), "name": service.name_of(user)},
                     metadata={"via": kind})
    return ok({"email": user.email, "status": user.status})

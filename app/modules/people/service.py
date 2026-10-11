"""People of a workspace (mock: data/peopleStore.ts): the People page's rows and one person's detail.

A person is their `users` row, whatever their status (active, not_activated, invited, pending, disabled).
Departments and job titles come from the organisation data, the role from Roles, activity from the audit trail and
the sign-in sessions, so every page agrees. Forms they own are counted once forms exist (B5).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.auth.models import UserSession
from app.modules.org.models import OrgUnit, OrgUnitMember
from app.modules.people.models import UserInvite
from app.modules.rbac.service import grants_of, role_key
from app.modules.settings.service import get_section
from app.modules.uploads.service import file_url
from app.modules.users.models import Role, User, UserTwoStep

PRIVILEGED = ("people.manage", "settings.manage", "roles.manage")
AWAY = ("invited", "not_activated", "pending")  # never signed in yet
VISIT_GAP = timedelta(minutes=30)
ONLINE = timedelta(minutes=5)
ACTIVITY_DAYS = 90


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def name_of(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


async def current_invites(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, UserInvite]:
    """Each person's open link (the newest one not withdrawn)."""
    rows = (await db.execute(select(UserInvite).where(
        UserInvite.tenant_id == tenant_id, UserInvite.revoked_at.is_(None), UserInvite.deleted_at.is_(None))
        .order_by(UserInvite.sent_at))).scalars()
    return {row.user_id: row for row in rows}


async def rows_of(db: AsyncSession, tenant_id: uuid.UUID, *, only: uuid.UUID | None = None) -> list[dict[str, Any]]:
    """PersonRow (shared/types/people.ts) for everyone, or for one person (`only`)."""
    now = datetime.now(UTC)
    users = list((await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
                                   .order_by(User.created_at, User.id))).scalars())
    by_id = {u.id: u for u in users}
    roles = {r.id: r for r in (await db.execute(select(Role).where(Role.tenant_id == tenant_id))).scalars()}

    units = {u.id: u for u in (await db.execute(select(OrgUnit).where(
        OrgUnit.tenant_id == tenant_id, OrgUnit.deleted_at.is_(None), OrgUnit.archived_at.is_(None))
        .order_by(OrgUnit.created_at, OrgUnit.id))).scalars()}
    memberships: dict[uuid.UUID, dict[str, list[dict[str, str]]]] = {}
    for unit_id, user_id in (await db.execute(select(OrgUnitMember.org_unit_id, OrgUnitMember.user_id).where(
            OrgUnitMember.tenant_id == tenant_id, OrgUnitMember.deleted_at.is_(None)))).all():
        unit = units.get(unit_id)
        if unit is not None:
            memberships.setdefault(user_id, {}).setdefault(unit.kind, []).append(unit)  # type: ignore[arg-type]
    order = {uid: i for i, uid in enumerate(units)}

    two_step = {row.user_id for row in (await db.execute(select(UserTwoStep).where(
        UserTwoStep.tenant_id == tenant_id, UserTwoStep.deleted_at.is_(None)))).scalars()
        if row.totp_confirmed_at or row.sms_confirmed_at}
    invites = await current_invites(db, tenant_id)

    # Activity: the newest visit from the audit trail (actions less than 30 minutes apart), then the sessions
    events = (await db.execute(select(AuditLog.actor_id, AuditLog.occurred_at).where(
        AuditLog.tenant_id == tenant_id, AuditLog.actor_id.is_not(None), AuditLog.outcome == "success",
        AuditLog.occurred_at >= now - timedelta(days=ACTIVITY_DAYS))
        .order_by(AuditLog.occurred_at.desc()))).all()
    last_seen: dict[uuid.UUID, datetime] = {}
    visits: dict[uuid.UUID, dict[str, Any]] = {}
    for actor, at in events:
        last_seen.setdefault(actor, at)
        visit = visits.get(actor)
        if visit is None:
            visits[actor] = {"start": at, "end": at, "done": False}
        elif not visit["done"]:
            if visit["start"] - at < VISIT_GAP:
                visit["start"] = at
            else:
                visit["done"] = True
    idle = timedelta(minutes=(await get_section(db, tenant_id, "security"))["sessions"]["idle_minutes"])
    sessions: dict[uuid.UUID, UserSession] = {}
    for session in (await db.execute(select(UserSession).where(UserSession.tenant_id == tenant_id)
                                     .order_by(UserSession.last_active_at))).scalars():
        sessions[session.user_id] = session

    def visit_of(user_id: uuid.UUID) -> dict[str, Any] | None:
        session, trail = sessions.get(user_id), visits.get(user_id)
        if session is not None and (trail is None or session.last_active_at >= trail["end"]):
            is_open = session.revoked_at is None and now - session.last_active_at < idle
            end = max(session.last_active_at, trail["end"]) if trail else session.last_active_at
            return {"started_at": iso(session.started_at), "ended_at": iso(end),
                    "online": is_open and now - session.last_active_at < ONLINE}
        return {"started_at": iso(trail["start"]), "ended_at": iso(trail["end"]), "online": False} if trail else None

    def refs(user_id: uuid.UUID, kind: str) -> list[dict[str, str]]:
        found = sorted(memberships.get(user_id, {}).get(kind, []), key=lambda u: order[u.id])  # type: ignore[arg-type]
        return [{"id": str(u.id), "name": u.name} for u in found]  # type: ignore[attr-defined]

    rows = []
    for user in users:
        if only is not None and user.id != only:
            continue
        role = roles.get(user.role_id)
        grants = grants_of(role)
        manager = by_id.get(user.manager_id) if user.manager_id else None
        away = user.status in AWAY
        visit = None if away else visit_of(user.id)
        invite = invites.get(user.id)
        rows.append({
            "id": str(user.id), "first_name": user.first_name, "last_name": user.last_name, "name": name_of(user),
            "email": user.email, "phone": user.phone,
            "photo": file_url(user.photo_upload_id) if user.photo_upload_id else None,
            "role": role_key(role), "role_name": role.name if role else "",
            "privileged": bool(role and (role.built_in == "owner" or any(grants.get(p) for p in PRIVILEGED))),
            "status": user.status,
            "departments": refs(user.id, "departments"), "job_titles": refs(user.id, "job_titles"),
            "manager": {"id": str(manager.id), "name": name_of(manager)} if manager else None,
            "two_step": user.id in two_step,
            "last_active_at": None if away else (visit["ended_at"] if visit else iso(last_seen.get(user.id))),
            "last_visit": visit,
            "joined_at": iso(user.joined_at or user.created_at),
            "forms_count": 0,  # forms: B5
            "request": ({"via": user.request_via, "at": iso(user.requested_at)}
                        if user.status == "pending" and user.request_via else None),
            "invite": ({"kind": invite.kind, "expires_at": iso(invite.expires_at), "sent_at": iso(invite.sent_at),
                        "invited_by": invite.invited_by_name or "", "expired": invite.expires_at < now}
                       if invite is not None and user.status in ("invited", "not_activated") else None),
        })
    return rows


async def detail_of(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any] | None:
    """PersonDetail: the row, the last sign-in, 30 days of activity and who reports to them."""
    rows = await rows_of(db, tenant_id)
    row = next((r for r in rows if r["id"] == str(user_id)), None)
    if row is None:
        return None
    since = datetime.now(UTC) - timedelta(days=30)
    mine = list((await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.actor_id == user_id)
                                  .order_by(AuditLog.occurred_at.desc()))).scalars())
    sign_in = next((e for e in mine if e.action == "auth.login.succeeded"), None)
    recent = [e for e in mine if e.occurred_at >= since]
    return {
        **row,
        "last_sign_in": ({"at": iso(sign_in.occurred_at), "city": sign_in.city, "country": sign_in.country,
                          "browser": (sign_in.device or {}).get("browser"), "os": (sign_in.device or {}).get("os")}
                         if sign_in else None),
        "sign_ins_30d": sum(1 for e in recent if e.action == "auth.login.succeeded"),
        "actions_30d": len(recent),
        "reports": [{"id": r["id"], "name": r["name"]} for r in rows if r["manager"] and r["manager"]["id"] == row["id"]],
        "forms": [],  # their latest forms: B5
    }

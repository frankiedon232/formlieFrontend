"""People (mock: routes/people.ts and routes/peopleManage.ts, API-CONTRACT → People).

    GET   /people                 rows: q (name, email, departments, job titles), filter[status|role|department|
                                  job_title] (comma lists), sort, page, page_size
    GET   /people/insights        the two cards on top
    GET   /people/{id}            one person's detail
    PATCH /people/{id}            { role?, department_ids?, job_title_ids?, manager_id? }
    POST  /people/{id}/disable · /enable · /sign-out · /password · /two-step/reset
    POST  /people/bulk            { ids, action: role|department|job_title|disable|enable, value? } → { done, skipped }

Guards: a workspace keeps at least one active owner; only owners make or change owners; nobody disables or demotes
themselves here; a manager can't be the person or someone who reports to them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.models import AuditLog
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin, revoke_sessions
from app.modules.org import service as org
from app.modules.people import service
from app.modules.rbac.service import find_role, role_key
from app.modules.users.models import Role, User, UserRecoveryCode, UserTwoStep

router = APIRouter(tags=["people"])

ROLE_ORDER = {"owner": 0, "admin": 1, "member": 2}
STATUSES = ("active", "not_activated", "invited", "pending", "disabled")
_ids = z.array(z.string().max(64)).max(20)
patch_schema = z.obj(role=z.string().min(1).max(64).optional(), department_ids=_ids.optional(),
                     job_title_ids=_ids.optional(), manager_id=z.string().max(64).nullable().optional())
bulk_schema = z.obj(ids=z.array(z.string().max(64)).min(1).max(200),
                    action=z.enum(["role", "department", "job_title", "disable", "enable"]),
                    value=z.string().max(64).optional())


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _list(value: str | None) -> list[str] | None:
    return value.split(",") if value else None


@router.get("/people", dependencies=[rate_limit("people-list", per_minute=120)])
async def list_people(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        rows = await service.rows_of(db, principal.tenant.id)
    status, role = _list(query.get("filter[status]")), _list(query.get("filter[role]"))
    department, job = _list(query.get("filter[department]")), _list(query.get("filter[job_title]"))
    rows = [r for r in rows if (not status or r["status"] in status) and (not role or r["role"] in role)
            and (not department or any(d["id"] in department for d in r["departments"]))
            and (not job or any(j["id"] in job for j in r["job_titles"]))]
    sort = query.get("sort") or "name"
    key, desc = sort.lstrip("-"), sort.startswith("-")

    def value(row: dict[str, Any]) -> Any:
        if key == "role":
            return ROLE_ORDER.get(row["role"], 3)
        if key == "last_active_at":
            return row["last_active_at"] or ""
        if key == "joined_at":
            return row["joined_at"]
        return row["name"].lower()
    rows.sort(key=lambda r: (value(r), r["name"].casefold()), reverse=desc)
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in " ".join([r["name"], r["email"], *(d["name"] for d in r["departments"]),
                                                  *(j["name"] for j in r["job_titles"])]).lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/people/insights", dependencies=[rate_limit("people-insights", per_minute=60)])
async def people_insights(principal: Principal = Depends(require_admin)) -> Any:
    tenant_id = principal.tenant.id
    now = datetime.now(UTC)
    today = now.date()
    async with db_session("read", **_scope(principal)) as db:
        rows = await service.rows_of(db, tenant_id)
        ids = [uuid.UUID(r["id"]) for r in rows]
        sign_ins = (await db.execute(select(func.date(AuditLog.occurred_at), func.count()).where(
            AuditLog.tenant_id == tenant_id, AuditLog.action == "auth.login.succeeded", AuditLog.actor_id.in_(ids),
            AuditLog.occurred_at >= datetime.combine(today - timedelta(days=29), datetime.min.time(), UTC))
            .group_by(func.date(AuditLog.occurred_at)))).all()
    per_day = {day.isoformat(): count for day, count in sign_ins}
    joined_days = [(now - datetime.fromisoformat(r["joined_at"].replace("Z", "+00:00"))).total_seconds() / 86_400
                   for r in rows]
    return ok({
        "total": len(rows),
        "joined": sum(1 for d in joined_days if d < 30),
        "joined_previous": sum(1 for d in joined_days if 30 <= d < 60),
        "two_step": sum(1 for r in rows if r["two_step"]),
        "by_status": {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES},
        "by_role": {k: sum(1 for r in rows if r["role"] == k) for k in ("owner", "admin", "member")},
        "daily": [{"date": (today - timedelta(days=29 - i)).isoformat(),
                   "count": per_day.get((today - timedelta(days=29 - i)).isoformat(), 0)} for i in range(30)],
    })


async def _person(db: Any, tenant_id: uuid.UUID, person_id: str, *, invited: bool = False) -> User:
    """A person to act on; invitations can be edited (role, departments …) but not disabled or signed out."""
    try:
        wanted = uuid.UUID(person_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    user = await db.get(User, wanted)
    if user is None or user.tenant_id != tenant_id or user.deleted_at is not None \
            or (user.status == "invited" and not invited):
        raise FrmError("FRM-GEN-1004")
    return user


async def _detail(db: Any, principal: Principal, user: User) -> Any:
    return ok(await service.detail_of(db, principal.tenant.id, user.id))


@router.get("/people/{person_id}", dependencies=[rate_limit("people-get", per_minute=120)])
async def get_person(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        user = await _person(db, principal.tenant.id, person_id, invited=True)
        return await _detail(db, principal, user)


# ── Managing ────────────────────────────────────────────────────────────────────

class Manager:
    """The rules every change goes through (mock: peopleManage.ts guardOwner, setRole, setManager …)."""

    def __init__(self, db: Any, principal: Principal) -> None:
        self.db, self.principal = db, principal
        self.tenant = principal.tenant
        self.me_owner = role_key(principal.role) == "owner"

    async def role_of(self, user: User) -> str:
        return role_key(await self.db.get(Role, user.role_id))

    async def active_owners(self) -> int:
        owner = await find_role(self.db, self.tenant.id, "owner")
        return int((await self.db.execute(select(func.count()).select_from(User).where(
            User.tenant_id == self.tenant.id, User.role_id == owner.id, User.status == "active",
            User.deleted_at.is_(None)))).scalar_one()) if owner else 0

    async def guard_owner(self, user: User, losing: bool) -> None:
        """Owners are changed only by owners, and the last active owner stays one."""
        if await self.role_of(user) == "owner":
            if not self.me_owner:
                raise FrmError("FRM-USER-1006")
            if losing and user.status == "active" and await self.active_owners() <= 1:
                raise FrmError("FRM-USER-1003")

    async def audit(self, action: str, user: User, changes: list[dict[str, Any]] | None = None) -> None:
        await record(self.db, tenant_id=self.tenant.id, organisation_id=self.tenant.organisation_id, action=action,
                     actor=Actor.user(self.principal.user), changes=changes or [],
                     resource={"type": "user", "id": str(user.id), "name": service.name_of(user)})

    async def set_role(self, user: User, key: str) -> dict[str, Any] | None:
        current = await self.role_of(user)
        if key == current:
            return None
        role = await find_role(self.db, self.tenant.id, key)
        if role is None:
            raise FrmError("FRM-USER-1009")
        if role.built_in == "owner" and not self.me_owner:
            raise FrmError("FRM-USER-1006")
        if user.id == self.principal.user.id and current == "owner" and await self.active_owners() <= 1:
            raise FrmError("FRM-USER-1003")
        await self.guard_owner(user, True)
        user.role_id = role.id
        return {"field": "role", "before": current, "after": role_key(role)}

    async def set_manager(self, user: User, manager_id: str | None) -> dict[str, Any] | None:
        current = str(user.manager_id) if user.manager_id else None
        if manager_id == current:
            return None
        manager = None
        if manager_id:
            manager = await _person(self.db, self.tenant.id, manager_id)
            at, steps = manager, 0
            while at is not None and steps < 50:  # walking up from the new manager must never reach the person
                if at.id == user.id:
                    raise FrmError("FRM-USER-1004")
                at = await self.db.get(User, at.manager_id) if at.manager_id else None
                steps += 1
        before = await self.db.get(User, user.manager_id) if user.manager_id else None
        user.manager_id = manager.id if manager else None
        return {"field": "manager", "before": service.name_of(before) if before else None,
                "after": service.name_of(manager) if manager else None}

    async def units(self, user: User, kind: str, ids: list[str]) -> dict[str, Any] | None:
        return await org.set_person_units(self.db, self.tenant.id, self.tenant.organisation_id, user.id, kind, ids,
                                          self.principal.user.id)

    async def sign_out(self, user: User) -> None:
        await revoke_sessions(self.db, self.tenant.id, ids=None, keep=None, user_id=user.id, reason="signed_out_by_admin")

    async def disable(self, user: User) -> bool:
        if user.id == self.principal.user.id:
            raise FrmError("FRM-USER-1005")
        if user.status == "disabled":
            return False
        await self.guard_owner(user, True)
        user.status = "disabled"
        await self.sign_out(user)
        return True

    async def enable(self, user: User) -> bool:
        if user.status != "disabled":
            return False
        await self.guard_owner(user, False)
        user.status = "active"
        return True


@router.patch("/people/{person_id}", dependencies=[rate_limit("people-update", per_minute=60)])
async def update_person(person_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        m = Manager(db, principal)
        user = await _person(db, principal.tenant.id, person_id, invited=True)
        body = patch_schema.parse(await request.json())
        role = await m.set_role(user, body["role"]) if body.get("role") else None
        changes = [c for c in [
            await m.units(user, "departments", body["department_ids"]) if "department_ids" in body else None,
            await m.units(user, "job_titles", body["job_title_ids"]) if "job_title_ids" in body else None,
            await m.set_manager(user, body["manager_id"]) if "manager_id" in body else None,
        ] if c]
        if role:
            await m.audit("users.role_changed", user, [role])
        if changes:
            await m.audit("users.updated", user, changes)
        await db.flush()
        return await _detail(db, principal, user)


async def _one(person_id: str, principal: Principal, action: str, work: Any) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        m = Manager(db, principal)
        user = await _person(db, principal.tenant.id, person_id)
        if await work(m, user):
            await m.audit(action, user)
        await db.flush()
        return await _detail(db, principal, user)


@router.post("/people/{person_id}/disable", dependencies=[rate_limit("people-action", per_minute=60)])
async def disable_person(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    return await _one(person_id, principal, "users.disabled", lambda m, u: m.disable(u))


@router.post("/people/{person_id}/enable", dependencies=[rate_limit("people-action", per_minute=60)])
async def enable_person(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    return await _one(person_id, principal, "users.enabled", lambda m, u: m.enable(u))


@router.post("/people/{person_id}/sign-out", dependencies=[rate_limit("people-action", per_minute=60)])
async def sign_out_person(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async def work(m: Manager, user: User) -> bool:
        await m.guard_owner(user, False)
        await m.sign_out(user)
        return True
    return await _one(person_id, principal, "users.signed_out", work)


@router.post("/people/{person_id}/password", dependencies=[rate_limit("people-action", per_minute=60)])
async def request_password(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    """A new password at the next sign-in (and signed out now)."""
    async def work(m: Manager, user: User) -> bool:
        if user.id == principal.user.id:
            raise FrmError("FRM-USER-1005")
        await m.guard_owner(user, False)
        user.must_change_password = True
        await m.sign_out(user)
        return True
    return await _one(person_id, principal, "users.password_requested", work)


@router.post("/people/{person_id}/two-step/reset", dependencies=[rate_limit("people-action", per_minute=60)])
async def reset_two_step(person_id: str, principal: Principal = Depends(require_admin)) -> Any:
    """The authenticator app, text-message phone and recovery codes go (their rows keep deleted_at)."""
    async def work(m: Manager, user: User) -> bool:
        await m.guard_owner(user, False)
        now = datetime.now(UTC)
        found = False
        for model in (UserTwoStep, UserRecoveryCode):
            for row in (await m.db.execute(select(model).where(model.tenant_id == user.tenant_id,
                                                               model.user_id == user.id,
                                                               model.deleted_at.is_(None)))).scalars():
                if model is UserTwoStep and (row.totp_confirmed_at or row.sms_confirmed_at):
                    found = True
                row.deleted_at, row.deleted_by = now, principal.user.id
        return found
    return await _one(person_id, principal, "users.two_step_reset", work)


@router.post("/people/bulk", dependencies=[rate_limit("people-bulk", per_minute=20)])
async def bulk_people(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = bulk_schema.parse(await request.json())
    done = skipped = 0
    async with db_session("write", **_scope(principal)) as db:
        m = Manager(db, principal)
        for person_id in body["ids"]:
            try:
                async with db.begin_nested():  # one person's refusal undoes only their change
                    user = await _person(db, principal.tenant.id, person_id)
                    action, changed = "users.updated", None
                    if body["action"] == "role":
                        changed = await m.set_role(user, z.string().min(1).max(64).parse(body.get("value")))
                        action = "users.role_changed"
                    elif body["action"] in ("department", "job_title"):  # adds one, keeps the others
                        kind = "departments" if body["action"] == "department" else "job_titles"
                        current = [r["id"] for r in (await service.rows_of(db, principal.tenant.id, only=user.id))[0][kind]]
                        changed = await m.units(user, kind, [*current, body.get("value") or ""])
                    elif body["action"] == "disable":
                        changed, action = await m.disable(user), "users.disabled"
                    else:
                        changed, action = await m.enable(user), "users.enabled"
                    if changed:
                        await m.audit(action, user, [changed] if isinstance(changed, dict) else [])
                        done += 1
                    else:
                        skipped += 1
            except FrmError:
                skipped += 1
    return ok({"done": done, "skipped": skipped})

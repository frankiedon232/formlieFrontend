"""The internal admin API (PLATFORM-ADMIN-INTEGRATION §2): what the platform admin may change in Formalie.

Base /internal/admin/v1, plain JSON, signed (internal.py), every change idempotent and in the workspace's audit trail
as Formalie support under the staff member's name. Ids are Formalie's own (the platform reads the same ones from
the replica). Answers never carry secrets or respondents' answers.

    POST /tenants/{id}/suspend          { reason }                     suspended (people can't sign in; the reason
    POST /tenants/{id}/restore                                          shows on the workspace's sign-in page)
    POST /tenants/{id}/subdomain        { subdomain }                  the old one keeps working for 90 days
    POST /tenants/{id}/read-only        { reason }                     people can look and export, not change
    POST /tenants/{id}/close            { reason, close_at }           closing: read only until the date
    POST /tenants/{id}/cancel-close                                    back to active
    POST /tenants/{id}/plan             { plan_id?, limits?, trial_ends_at? }
    POST /tenants/{id}/export                                          full export, the Owners get the link
    POST /users/{id}/sign-out · /two-step/reset · /password-reset · /disable · /enable · /unlock
    POST /subscriptions/{id}/activate · /extend · /credit · /cancel     (B15: no subscriptions yet → not found)
    POST /payments/{id}/refund                                          (B15)
    POST /support-access/requests       { tenant_id, reason, mode, hours }
    POST /support-access/{grant_id}/session   { mode? }  → a one-time ticket for the support view
    POST /communications/send           { tenant_ids? | plans?, to, channels, subject, body, link_url?, essential }
    POST /cache/invalidate              { table | tables }
    GET  /health/services
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.ids import uuid7
from app.modules.platform_bridge import support
from app.modules.platform_bridge.events import emit
from app.modules.platform_bridge.internal import PREFIX, PlatformCall, audit, log_read, platform_call, run_change

router = APIRouter(prefix=PREFIX, include_in_schema=False)

STATUS_REASON_MAX = 500


def _parse(model: type[BaseModel], call: PlatformCall) -> Any:
    try:
        return model.model_validate(call.json())
    except ValidationError as exc:
        raise FrmError("FRM-GEN-1002", [{"field": ".".join(str(p) for p in e["loc"]) or "body", "message": e["type"]}
                                        for e in exc.errors()[:20]]) from None


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


# ── Workspaces ───────────────────────────────────────────────────────────────────

async def _tenant(tenant_id: uuid.UUID) -> dict[str, Any]:
    async with db_session("write") as db:
        row = (await db.execute(text("SELECT * FROM platform.admin_tenant(:id)"), {"id": tenant_id})).mappings().first()
    if row is None:
        raise FrmError("FRM-GEN-1004", [{"field": "tenant", "message": "not_found"}])
    return dict(row)


def _tenant_view(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(row["id"]), "subdomain": row["subdomain"], "name": row["name"], "status": row["status"],
            "status_reason": row["suspended_reason"], "plan_id": row["plan_id"], "plan_limits": row["plan_limits"],
            "trial_ends_at": _iso(row["trial_ends_at"]), "close_at": _iso(row["close_at"]),
            "data_region": row["data_region"], "setup_completed_at": _iso(row["setup_completed_at"]),
            "created_at": _iso(row["created_at"])}


def _scope(row: dict[str, Any]) -> dict[str, uuid.UUID]:
    return {"tenant_id": row["id"], "organisation_id": row["organisation_id"]}


async def _forget_host(*subdomains: str) -> None:
    from app.modules.tenants.service import TenantDirectory

    directory = TenantDirectory()
    for sub in subdomains:
        if sub:
            await directory.forget(sub)


class ReasonBody(BaseModel):
    reason: str = Field(min_length=1, max_length=STATUS_REASON_MAX)


class CloseBody(ReasonBody):
    close_at: datetime


async def _set_status(call: PlatformCall, tenant_id: str, status: str, *, reason: str | None = None,
                      close_at: datetime | None = None, only_from: tuple[str, ...] | None = None) -> JSONResponse:
    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        row = await _tenant(_uuid(tenant_id))
        if only_from is not None and row["status"] not in only_from:
            raise FrmError("FRM-GEN-1009", [{"field": "status", "message": row["status"]}])
        async with db_session("write", **_scope(row)) as db:
            before = (await db.execute(text("SELECT platform.admin_set_status(:s, :r, :c)"),
                                       {"s": status, "r": reason, "c": close_at})).scalar_one()
            changes = [{"field": "status", "before": before, "after": status}]
            if close_at is not None:
                changes.append({"field": "close_at", "before": _iso(row["close_at"]), "after": _iso(close_at)})
            await audit(db, call, row["id"], row["organisation_id"], "workspace.updated",
                        resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]}, changes=changes,
                        severity="warning" if status in ("suspended", "closing") else None,
                        metadata={"status_reason": reason or ""})
            if status == "suspended" and before != "suspended":
                await emit(db, "tenant.suspended", {"previous_status": before, "status": status},
                           tenant_id=row["id"], organisation_id=row["organisation_id"], source="worker")
            if status == "closing":
                await emit(db, "tenant.closed", {"previous_status": before, "close_at": _iso(close_at)},
                           tenant_id=row["id"], organisation_id=row["organisation_id"], source="worker")
            if status in ("suspended", "closing"):
                await support.end_sessions(db, row["id"], "access_ended")
        await _forget_host(row["subdomain"])
        await support.forget(row["id"])
        return _tenant_view(await _tenant(row["id"])), row["id"]

    return await run_change(call, work)


@router.post("/tenants/{tenant_id}/suspend")
async def suspend(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    body = _parse(ReasonBody, call)
    return await _set_status(call, tenant_id, "suspended", reason=body.reason)


@router.post("/tenants/{tenant_id}/restore")
async def restore(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    return await _set_status(call, tenant_id, "active", only_from=("suspended", "read_only", "closed"))


@router.post("/tenants/{tenant_id}/read-only")
async def read_only(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    body = _parse(ReasonBody, call)
    return await _set_status(call, tenant_id, "read_only", reason=body.reason, only_from=("active", "read_only"))


@router.post("/tenants/{tenant_id}/close")
async def close(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    body = _parse(CloseBody, call)
    at = body.close_at if body.close_at.tzinfo else body.close_at.replace(tzinfo=UTC)
    if at < datetime.now(UTC) + timedelta(days=1):
        raise FrmError("FRM-GEN-1002", [{"field": "close_at", "message": "at_least_one_day_ahead"}])
    return await _set_status(call, tenant_id, "closing", reason=body.reason, close_at=at,
                             only_from=("active", "read_only", "suspended"))


@router.post("/tenants/{tenant_id}/cancel-close")
async def cancel_close(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    return await _set_status(call, tenant_id, "active", only_from=("closing",))


class SubdomainBody(BaseModel):
    subdomain: str = Field(min_length=3, max_length=63)


@router.post("/tenants/{tenant_id}/subdomain")
async def change_subdomain(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.core.middleware.tenant import is_valid_subdomain
    from app.modules.platform_bridge.globals import is_reserved

    body = _parse(SubdomainBody, call)
    new = body.subdomain.strip().lower()

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        row = await _tenant(_uuid(tenant_id))
        if not is_valid_subdomain(new):
            raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "invalid"}])
        if await is_reserved(new):
            raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "reserved"}])
        if new == row["subdomain"]:
            return _tenant_view(row), row["id"]
        async with db_session("write", **_scope(row)) as db:
            try:
                async with db.begin_nested():  # the old one keeps leading here for 90 days (03-DECISIONS F14 M7)
                    await db.execute(text("SELECT platform.change_subdomain(:new, :id)"), {"new": new, "id": uuid7()})
            except DBAPIError:
                raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "taken"}]) from None
            await audit(db, call, row["id"], row["organisation_id"], "settings.updated",
                        resource={"type": "setting", "id": None, "name": "Address and domain"},
                        changes=[{"field": "subdomain", "before": row["subdomain"], "after": new}])
        await _forget_host(row["subdomain"], new)
        return _tenant_view(await _tenant(row["id"])), row["id"]

    return await run_change(call, work)


LIMIT_KEYS = ("forms", "responses_per_form", "databases", "sso", "custom_domains", "custom_email", "data_residency",
              "ai_credits", "languages")


class PlanBody(BaseModel):
    plan_id: str | None = Field(default=None, max_length=40)
    limits: dict[str, Any] | None = None  # null: back to the plan's own limits
    trial_ends_at: datetime | None = None  # null: no trial


@router.post("/tenants/{tenant_id}/plan")
async def change_plan(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.billing.plans import PLANS

    raw = call.json()
    body = _parse(PlanBody, call)
    if body.plan_id is not None and body.plan_id not in {p["id"] for p in PLANS}:
        raise FrmError("FRM-GEN-1002", [{"field": "plan_id", "message": "unknown_plan"}])
    unknown = sorted(set(body.limits or {}) - set(LIMIT_KEYS))
    if unknown:
        raise FrmError("FRM-GEN-1002", [{"field": f"limits.{k}", "message": "unknown_limit"} for k in unknown])
    if body.plan_id is None and "limits" not in raw and "trial_ends_at" not in raw:
        raise FrmError("FRM-GEN-1002", [{"field": "body", "message": "nothing_to_change"}])

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        import json as _json

        row = await _tenant(_uuid(tenant_id))
        async with db_session("write", **_scope(row)) as db:
            before = (await db.execute(text("SELECT platform.admin_set_plan(:p, CAST(:l AS jsonb), :t, :sl, :st)"), {
                "p": body.plan_id, "l": _json.dumps(body.limits) if body.limits is not None else None,
                "t": body.trial_ends_at, "sl": "limits" in raw, "st": "trial_ends_at" in raw})).scalar_one()
            changes = []
            if body.plan_id is not None and body.plan_id != before.get("plan_id"):
                changes.append({"field": "plan", "before": before.get("plan_id"), "after": body.plan_id})
            if "limits" in raw:
                changes.append({"field": "plan_limits", "before": before.get("plan_limits"), "after": body.limits})
            if "trial_ends_at" in raw:
                changes.append({"field": "trial_ends_at", "before": before.get("trial_ends_at"),
                                "after": _iso(body.trial_ends_at)})
            await audit(db, call, row["id"], row["organisation_id"], "workspace.updated",
                        resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]}, changes=changes)
        await _forget_host(row["subdomain"])
        return _tenant_view(await _tenant(row["id"])), row["id"]

    return await run_change(call, work)


@router.post("/tenants/{tenant_id}/export")
async def export_workspace(tenant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.exports import service as jobs
    from app.modules.platform_bridge import workspace_export

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        row = await _tenant(_uuid(tenant_id))
        async with db_session("write", **_scope(row)) as db:
            stamp = datetime.now(UTC).strftime("%Y-%m-%d")
            job = await jobs.create(db, tenant_id=row["id"], organisation_id=row["organisation_id"], user_id=None,  # type: ignore[arg-type]
                                    kind=workspace_export.KIND, format="zip",
                                    file_name=f"{row['subdomain']}-export-{stamp}.zip", rows=0,
                                    params={"workspace": {"name": row["name"], "subdomain": row["subdomain"]}})
            await audit(db, call, row["id"], row["organisation_id"], "settings.data_exported",
                        resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]},
                        metadata={"export_id": str(job.id)})
            view = {"export_id": str(job.id), "status": job.status, "file_name": job.file_name}
        jobs.dispatch(job)
        return view, row["id"]

    return await run_change(call, work)


# ── People's accounts ─────────────────────────────────────────────────────────────

async def _user_scope(user_id: uuid.UUID) -> dict[str, Any]:
    async with db_session("write") as db:
        row = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.user_workspace(:id)"),
                                {"id": user_id})).first()
    if row is None:
        raise FrmError("FRM-GEN-1004", [{"field": "user", "message": "not_found"}])
    return {"tenant_id": row[0], "organisation_id": row[1]}


AUDIT_OF = {"sign-out": "users.signed_out", "two-step/reset": "users.two_step_reset",
            "password-reset": "users.password_requested", "disable": "users.disabled", "enable": "users.enabled",
            "unlock": "users.updated"}


async def _account(call: PlatformCall, user_id: str, action: str) -> JSONResponse:
    from app.core.cache.redis import get_redis
    from app.core.middleware.rate_limit import KEY_PREFIX
    from app.modules.auth.sessions import revoke_sessions
    from app.modules.users.models import User, UserRecoveryCode, UserTwoStep

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        wanted = _uuid(user_id)
        scope = await _user_scope(wanted)
        async with db_session("write", **scope) as db:
            user = await db.get(User, wanted)
            if user is None or user.deleted_at is not None or user.tenant_id != scope["tenant_id"]:
                raise FrmError("FRM-GEN-1004", [{"field": "user", "message": "not_found"}])
            changed, ended, changes = True, 0, None
            if action in ("sign-out", "password-reset", "disable"):
                if action == "password-reset":
                    user.must_change_password = True
                if action == "disable":
                    changed = user.status != "disabled"
                    if user.status not in ("active", "disabled"):
                        raise FrmError("FRM-GEN-1009", [{"field": "status", "message": user.status}])
                    changes = [{"field": "status", "before": user.status, "after": "disabled"}]
                    user.status = "disabled"
                ended = len(await revoke_sessions(db, scope["tenant_id"], ids=None, keep=None,
                                                  reason="signed_out_by_formalie", user_id=user.id))
            elif action == "enable":
                changed = user.status == "disabled"
                changes = [{"field": "status", "before": user.status, "after": "active"}]
                if changed:
                    user.status = "active"
            elif action == "two-step/reset":
                now = datetime.now(UTC)
                changed = False
                for model in (UserTwoStep, UserRecoveryCode):
                    for row in (await db.execute(select(model).where(
                            model.tenant_id == user.tenant_id, model.user_id == user.id,
                            model.deleted_at.is_(None)))).scalars():
                        changed = True
                        row.deleted_at = now
            elif action == "unlock":
                import hashlib

                digest = hashlib.sha256(user.email.strip().lower().encode()).hexdigest()[:32]
                keys = [f"{KEY_PREFIX}:route:{name}:v:{digest}" for name in ("login", "password-forgot")]
                changed = bool(await get_redis().delete(*keys))
                changes = [{"field": "sign_in_lock", "before": "locked" if changed else "open", "after": "open"}]
            if changed or action in ("sign-out", "password-reset", "unlock"):
                await audit(db, call, user.tenant_id, user.organisation_id, AUDIT_OF[action],
                            resource={"type": "user", "id": str(user.id),
                                      "name": f"{user.first_name} {user.last_name}".strip()},
                            changes=changes, metadata={"sessions_ended": ended})
            view = {"id": str(user.id), "tenant_id": str(user.tenant_id), "status": user.status,
                    "must_change_password": user.must_change_password, "sessions_ended": ended, "changed": changed}
        return view, scope["tenant_id"]

    return await run_change(call, work)


def _account_route(path: str, action: str) -> None:
    async def handler(user_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
        return await _account(call, user_id, action)

    handler.__name__ = f"account_{action.replace('/', '_').replace('-', '_')}"
    router.post(f"/users/{{user_id}}/{path}")(handler)


for _action in ("sign-out", "two-step/reset", "password-reset", "disable", "enable", "unlock"):
    _account_route(_action, _action)


# ── Subscriptions and payments (B15: Formalie has no subscriptions yet) ─────────────

async def _no_billing(call: PlatformCall, kind: str) -> JSONResponse:
    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        raise FrmError("FRM-GEN-1004", [{"field": kind, "message": "billing_not_available_yet"}])

    return await run_change(call, work)


for _path, _kind in (("/subscriptions/{item_id}/activate", "subscription"), ("/subscriptions/{item_id}/extend", "subscription"),
                     ("/subscriptions/{item_id}/credit", "subscription"), ("/subscriptions/{item_id}/cancel", "subscription"),
                     ("/payments/{item_id}/refund", "payment")):
    def _billing_route(kind: str = _kind) -> Any:
        async def handler(item_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
            return await _no_billing(call, kind)
        return handler

    _handler = _billing_route()
    _handler.__name__ = "billing_" + _path.strip("/").replace("/", "_").replace("{item_id}", "x").replace("-", "_")
    router.post(_path)(_handler)


# ── Support access ─────────────────────────────────────────────────────────────────

class SupportRequestBody(BaseModel):
    tenant_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=1000)  # shown to the workspace's admins
    mode: Literal["read", "write"] = "read"
    hours: Literal[1, 24, 168] = 24


@router.post("/support-access/requests")
async def request_support_access(call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.platform_bridge.models import SupportAccessRequest

    body = _parse(SupportRequestBody, call)

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        row = await _tenant(body.tenant_id)
        async with db_session("write", **_scope(row)) as db:
            asked = SupportAccessRequest(
                tenant_id=row["id"], organisation_id=row["organisation_id"], staff_id=call.staff_id or "",
                staff_name=call.staff_name or "", reason=body.reason, mode=body.mode, hours=body.hours,
                approval_id=call.approval_id,
                expires_at=datetime.now(UTC) + timedelta(days=get_settings().support_request_days))
            db.add(asked)
            await db.flush()
            await audit(db, call, row["id"], row["organisation_id"], "workspace.updated",
                        resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]},
                        changes=[{"field": "support_access_request", "before": None, "after": "pending"}],
                        metadata={"request_id": str(asked.id), "mode": body.mode, "hours": body.hours})
            await _tell_admins(db, row, asked)
            view = {"request_id": str(asked.id), "status": asked.status, "expires_at": _iso(asked.expires_at)}
        return view, row["id"]

    return await run_change(call, work)


async def _tell_admins(db: Any, row: dict[str, Any], asked: Any) -> None:
    """In-app notice to the people who manage the workspace (event `support_request`)."""
    from app.modules.notifications.models import Notification
    from app.modules.rbac.service import grants_of, roles_of
    from app.modules.users.models import User

    roles = {r.id: r for r in await roles_of(db, row["id"])}
    for user in (await db.execute(select(User).where(User.tenant_id == row["id"], User.deleted_at.is_(None),
                                                     User.status == "active"))).scalars():
        if grants_of(roles.get(user.role_id)).get("settings.manage"):
            db.add(Notification(tenant_id=row["id"], organisation_id=row["organisation_id"], user_id=user.id,
                                event="support_request", link="/settings/security",
                                params={"staff": asked.staff_name, "mode": asked.mode, "hours": asked.hours,
                                        "request_id": str(asked.id)}))


class SessionBody(BaseModel):
    mode: Literal["read", "write"] = "read"


@router.post("/support-access/{grant_id}/session")
async def start_support_session(grant_id: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.platform_bridge.models import SupportAccessGrant
    from app.modules.tenants.router import host_port

    body = _parse(SessionBody, call)

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        wanted = _uuid(grant_id)
        async with db_session("write") as db:
            found = (await db.execute(text("SELECT tenant_id, organisation_id FROM platform.support_grant_workspace(:g)"),
                                      {"g": wanted})).first()
        if found is None:
            raise FrmError("FRM-GEN-1004", [{"field": "grant", "message": "not_found"}])
        row = await _tenant(found[0])
        async with db_session("write", **_scope(row)) as db:
            grant = await db.get(SupportAccessGrant, wanted)
            if grant is None or grant.revoked_at is not None or grant.expires_at <= datetime.now(UTC):
                raise FrmError("FRM-PERM-1001", [{"field": "grant", "message": "not_active"}])
            session, ticket = await support.issue_session(db, grant, staff_id=call.staff_id or "",
                                                          staff_name=call.staff_name or "",
                                                          approval_id=call.approval_id, mode=body.mode)
            await audit(db, call, row["id"], row["organisation_id"], "workspace.updated",
                        resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]},
                        changes=[{"field": "support_session", "before": None, "after": body.mode}],
                        metadata={"support_session": str(session.id), "grant_id": str(grant.id)})
            view = {"session_id": str(session.id), "ticket": ticket, "mode": session.mode,
                    "ticket_expires_at": _iso(session.ticket_expires_at), "ends_at": _iso(session.ends_at),
                    "tenant": {"id": str(row["id"]), "subdomain": row["subdomain"]},
                    "redeem_url": f"https://{row['subdomain']}.{get_settings().root_domain}{host_port()}"
                                  f"/support#ticket={ticket}"}
        return view, row["id"]

    return await run_change(call, work)


# ── Messages to workspaces ────────────────────────────────────────────────────────

MAX_WORKSPACES = 500


class MessageBody(BaseModel):
    tenant_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_WORKSPACES)
    plans: list[str] = Field(default_factory=list, max_length=10)
    to: Literal["owners", "admins"] = "owners"
    channels: list[Literal["email", "in_app"]] = Field(default_factory=lambda: ["email", "in_app"], min_length=1)
    subject: dict[str, str]  # language → text; English required
    body: dict[str, str]
    link_url: str | None = Field(default=None, max_length=500, pattern=r"^https://")
    essential: bool = False  # essential messages ignore "unsubscribe" (service and security notices only)


@router.post("/communications/send")
async def send_message(call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    body = _parse(MessageBody, call)
    if "en" not in body.subject or "en" not in body.body:
        raise FrmError("FRM-GEN-1002", [{"field": "subject.en", "message": "required"}])
    if any(len(v) > 200 for v in body.subject.values()) or any(len(v) > 5000 for v in body.body.values()):
        raise FrmError("FRM-GEN-1002", [{"field": "body", "message": "too_long"}])

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        async with db_session("write") as db:
            rows = [dict(r) for r in (await db.execute(
                text("SELECT * FROM platform.communication_workspaces(CAST(:p AS text[]), CAST(:t AS uuid[]))"),
                {"p": body.plans, "t": body.tenant_ids})).mappings().all()]
        if len(rows) > MAX_WORKSPACES:
            raise FrmError("FRM-GEN-1002", [{"field": "tenant_ids", "message": f"at_most_{MAX_WORKSPACES}"}])
        totals = {"workspaces": 0, "emails": 0, "notices": 0}
        for row in rows:
            sent = await _deliver(call, body, row)
            totals["workspaces"] += 1
            totals["emails"] += sent[0]
            totals["notices"] += sent[1]
        return totals, rows[0]["id"] if len(rows) == 1 else None

    return await run_change(call, work)


async def _deliver(call: PlatformCall, body: MessageBody, row: dict[str, Any]) -> tuple[int, int]:
    from app.modules.emails import unsubscribe as unsub
    from app.modules.emails import workspace as mail
    from app.modules.notifications.models import Notification
    from app.modules.notifications.service import workspace_url
    from app.modules.rbac.service import grants_of, roles_of
    from app.modules.users.models import User

    emails = notices = 0
    async with db_session("write", tenant_id=row["id"], organisation_id=row["organisation_id"]) as db:
        roles = {r.id: r for r in await roles_of(db, row["id"])}
        people = [u for u in (await db.execute(select(User).where(
            User.tenant_id == row["id"], User.deleted_at.is_(None), User.status == "active"))).scalars()
            if (roles.get(u.role_id) is not None and roles[u.role_id].built_in == "owner")
            or (body.to == "admins" and grants_of(roles.get(u.role_id)).get("settings.manage"))]
        default_language = await mail.email_language(db, row["id"])
        for person in people:
            language = person.language if person.language in body.subject else default_language
            subject = body.subject.get(language) or body.subject["en"]
            message = body.body.get(language) or body.body["en"]
            if "in_app" in body.channels:
                db.add(Notification(tenant_id=row["id"], organisation_id=row["organisation_id"], user_id=person.id,
                                    event="platform_message", link=body.link_url,
                                    params={"title": subject, "message": message}))
                notices += 1
            if "email" in body.channels:
                link = None
                if not body.essential:
                    link = await unsub.prepare(db, tenant_id=row["id"], subdomain=row["subdomain"],
                                               email=person.email, kind="notification", ref="platform_message")
                    if link is None:
                        continue  # they stopped messages from Formalie
                if await mail.send(db, row["id"], row["name"], to=person.email, key="notification",
                                   reason="platform_message", language=language, unsubscribe=link,
                                   values={"title": subject, "message": message,
                                           "link": body.link_url or workspace_url(row["subdomain"], "/")}):
                    emails += 1
        await audit(db, call, row["id"], row["organisation_id"], "workspace.updated",
                    resource={"type": "workspace", "id": str(row["id"]), "name": row["name"]},
                    metadata={"message": body.subject["en"][:120], "recipients": len(people),
                              "channels": ",".join(body.channels)})
    return emails, notices


# ── Caches and health ──────────────────────────────────────────────────────────────

class InvalidateBody(BaseModel):
    table: str | None = Field(default=None, max_length=80)
    tables: list[str] = Field(default_factory=list, max_length=50)
    version: int | None = None


@router.post("/cache/invalidate")
async def invalidate_cache(call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.platform_bridge.globals import on_published

    body = _parse(InvalidateBody, call)

    async def work() -> tuple[dict[str, Any], uuid.UUID | None]:
        names = body.tables or ([body.table] if body.table else [])
        if not names:
            raise FrmError("FRM-GEN-1002", [{"field": "tables", "message": "required"}])
        return {"tables": await on_published({"tables": names, "version": body.version})}, None

    return await run_change(call, work)


@router.get("/health/services")
async def health_services(call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    from app.modules.platform_bridge.health import services

    report = await services()
    await log_read(call)
    return JSONResponse({"success": True, "data": report, "meta": {}})


# Anything else under the prefix: not found, after the signature check (no probing without the key)
@router.api_route("/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def unknown(rest: str, call: PlatformCall = Depends(platform_call)) -> JSONResponse:
    _ = rest, call
    raise FrmError("FRM-GEN-1004")


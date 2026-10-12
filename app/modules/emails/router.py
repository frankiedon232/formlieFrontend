"""Unsubscribe links (owner, 2026-10-12; port of the mock's routes/unsubscribe.ts), public, no sign-in:

    GET  /public/unsubscribe?t=          → UnsubscribeView (what the link stops; nothing changes yet)
    POST /public/unsubscribe { t }       → stop it (the page's button: mail scanners that open links change nothing)
    POST /public/unsubscribe/undo { t }  → start it again
    POST /email/one-click?t=             → plain, for mail apps' own Unsubscribe button (List-Unsubscribe-Post)

Each change is in the workspace's audit trail (`settings.email_unsubscribed` / `settings.email_resubscribed`).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.context import TenantInfo
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.emails import unsubscribe as unsub
from app.modules.forms.models import Form
from app.modules.public.rules import mask_email
from app.modules.tenants.service import TenantDirectory

router = APIRouter(tags=["emails"])


class TokenBody(BaseModel):
    t: str = Field(min_length=10, max_length=600)


async def _resolve(token: str | None) -> tuple[unsub.Target, TenantInfo]:
    target = unsub.read_token(token)
    tenant = await TenantDirectory().by_subdomain(target.subdomain) if target else None
    if target is None or tenant is None or tenant.id != target.tenant_id:
        raise FrmError("FRM-GEN-1004")
    return target, tenant


async def _view(db: Any, target: unsub.Target, tenant: TenantInfo) -> dict[str, Any]:
    subject: str | None = None
    if target.kind == "response_notification" and target.ref:
        try:
            subject = (await db.execute(select(Form.name).where(
                Form.tenant_id == tenant.id, Form.id == uuid.UUID(target.ref)))).scalar_one_or_none()
        except ValueError:
            subject = None
    elif target.kind == "notification":
        subject = target.ref or None
    return {"workspace": tenant.name, "email": mask_email(target.email), "kind": target.kind, "subject": subject,
            "unsubscribed": await unsub.is_stopped(db, target)}


async def _change(token: str | None, stop: bool) -> dict[str, Any]:
    target, tenant = await _resolve(token)
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        if await unsub.set_stopped(db, target, tenant.organisation_id, stop):
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                         action="settings.email_unsubscribed" if stop else "settings.email_resubscribed",
                         actor=Actor.anonymous(target.email),
                         metadata={"kind": target.kind, **({"ref": target.ref} if target.ref else {})})
        return await _view(db, target, tenant)


@router.get("/public/unsubscribe", dependencies=[rate_limit("unsubscribe-view", per_minute=60)])
async def get_unsubscribe(t: str) -> Any:
    target, tenant = await _resolve(t)
    async with db_session("read", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        return ok(await _view(db, target, tenant))


@router.post("/public/unsubscribe", dependencies=[rate_limit("unsubscribe", per_minute=30)])
async def unsubscribe(body: TokenBody) -> Any:
    return ok(await _change(body.t, True))


@router.post("/public/unsubscribe/undo", dependencies=[rate_limit("unsubscribe", per_minute=30)])
async def resubscribe(body: TokenBody) -> Any:
    return ok(await _change(body.t, False))


@router.post("/email/one-click", dependencies=[rate_limit("unsubscribe-one-click", per_minute=60)])
async def one_click(t: str) -> Any:
    """Mail apps post `List-Unsubscribe=One-Click` here (RFC 8058): plain, no envelope, a short answer."""
    await _change(t, True)
    return ok({"unsubscribed": True})

"""Portal routes of the platform bridge (B16), through the encrypted channel like every portal call.

    GET    /settings/security/support-access                    SupportAccessState (settings.view)
    POST   /settings/security/support-access                    { hours: 1 | 24 | 168, mode: read | write,
                                                                  request_id? } → SupportAccessState (settings.manage)
    DELETE /settings/security/support-access                    turn it off, end every support session → state
    POST   /settings/security/support-access/requests/{id}/decline   → SupportAccessState
    GET    /support-access/status                               SupportBanner | null (everyone signed in)
    POST   /auth/support/redeem                                 { ticket } → AuthTokens + support (no sign-in)
    POST   /auth/support/end                                    the staff member leaves (support token)
    GET    /platform/announcements                              banners for this workspace, in the reader's language
    GET    /platform/feature-flags                              { key: on } for this workspace

Shapes: docs/API-CONTRACT.md → Formalie support access, Platform announcements and switches.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import require_tenant
from app.core.refs_types import RefId
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_admin, require_auth
from app.modules.platform_bridge import globals as G
from app.modules.platform_bridge import support

router = APIRouter(tags=["platform bridge"])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


@router.get("/settings/security/support-access", dependencies=[rate_limit("support-access", per_minute=120)])
async def get_support_access(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await support.state(db, principal.tenant.id))


class AllowBody(BaseModel):
    hours: Literal[1, 24, 168]
    mode: Literal["read", "write"] = "read"
    request_id: RefId | None = None


@router.post("/settings/security/support-access", dependencies=[rate_limit("support-access-change", per_minute=30)])
async def allow_support_access(body: AllowBody, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        await support.allow(db, principal.tenant, principal.user, hours=body.hours, mode=body.mode,
                            request_id=body.request_id)
        return ok(await support.state(db, principal.tenant.id))


@router.delete("/settings/security/support-access", dependencies=[rate_limit("support-access-change", per_minute=30)])
async def revoke_support_access(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        await support.revoke(db, principal.tenant, principal.user)
        return ok(await support.state(db, principal.tenant.id))


@router.post("/settings/security/support-access/requests/{request_id}/decline",
             dependencies=[rate_limit("support-access-change", per_minute=30)])
async def decline_support_request(request_id: str, principal: Principal = Depends(require_admin)) -> Any:
    try:
        wanted = uuid.UUID(request_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("write", **_scope(principal)) as db:
        await support.decline(db, principal.tenant, principal.user, wanted)
        return ok(await support.state(db, principal.tenant.id))


@router.get("/support-access/status", dependencies=[rate_limit("support-access-status", per_minute=240)])
async def support_status(principal: Principal = Depends(require_auth)) -> Any:
    return ok(await support.banner(principal.tenant.id, principal.tenant.organisation_id))


class RedeemBody(BaseModel):
    ticket: str = Field(min_length=20, max_length=100)


@router.post("/auth/support/redeem", dependencies=[rate_limit("support-redeem", per_minute=10)])
async def redeem_support_ticket(body: RedeemBody) -> Any:
    return ok(await support.redeem(require_tenant(), body.ticket))


@router.post("/auth/support/end", dependencies=[rate_limit("support-end", per_minute=30)])
async def end_support_session(request: Request) -> Any:
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else ""
    return ok({"signed_out": await support.end_by_token(require_tenant(), token)})


@router.get("/platform/announcements", dependencies=[rate_limit("platform-announcements", per_minute=120)])
async def announcements(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    language = request.query_params.get("lang") or principal.user.language or "en"
    return ok(await G.announcements_for(principal.tenant, language))


@router.get("/platform/feature-flags", dependencies=[rate_limit("platform-flags", per_minute=120)])
async def feature_flags(principal: Principal = Depends(require_auth)) -> Any:
    return ok(await G.flags_for(principal.tenant))

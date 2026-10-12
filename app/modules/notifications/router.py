"""Notifications (mock: routes/notifications.ts; API-CONTRACT → Notifications): the signed-in person's feed.

    GET    /notifications                newest first (100), unread count (due events: Beat, tasks.py)
    POST   /notifications/read           { ids } or { all: true }
    DELETE /notifications/read           clears the ones already read
    POST   /notifications/digest/send    admins: send the waiting daily summaries now
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_admin, require_auth
from app.modules.notifications import service

router = APIRouter(tags=["notifications"])

read_schema = z.union([z.obj(ids=z.array(z.string().max(64)).min(1).max(200)), z.obj(all=z.literal(True))])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _workspace(principal: Principal) -> dict[str, str]:
    return {"name": principal.tenant.name, "subdomain": principal.tenant.subdomain}


@router.get("/notifications", dependencies=[rate_limit("notifications", per_minute=240)])
async def get_feed(principal: Principal = Depends(require_auth)) -> Any:
    # Only reads (query review Q11): due events are announced by Beat every minute (notifications.announce_due)
    async with db_session("read", **_scope(principal)) as db:
        return ok(await service.feed_of(db, principal.tenant.id, principal.user.id))


@router.post("/notifications/read", dependencies=[rate_limit("notifications-read", per_minute=120)])
async def read_notifications(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    data = read_schema.parse(await request.json())
    ids = None
    if "ids" in data:
        ids = []
        for raw in data["ids"]:
            try:
                ids.append(uuid.UUID(raw))
            except ValueError:
                continue
    async with db_session("write", **_scope(principal)) as db:
        await service.mark_read(db, principal.tenant.id, principal.user.id, ids)
        return ok(await service.feed_of(db, principal.tenant.id, principal.user.id))


@router.delete("/notifications/read", dependencies=[rate_limit("notifications-read", per_minute=60)])
async def clear_notifications(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        await service.clear_read(db, principal.tenant.id, principal.user.id)
        return ok(await service.feed_of(db, principal.tenant.id, principal.user.id))


@router.post("/notifications/digest/send", dependencies=[rate_limit("notifications-digest", per_minute=10)])
async def send_digest(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        sent = await service.flush_digest(db, principal.tenant.id, principal.tenant.organisation_id,
                                          _workspace(principal), force=True)
    return ok({"sent": sent})

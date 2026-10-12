"""Privacy and data (port of the mock's routes/dataPrivacy.ts and routes/dataRegion.ts). Admins, except the region.

    GET  /settings/privacy/retention-preview?days=   what that limit would remove now
    POST /privacy/requests/search   { email }               → DataRequestMatch
    POST /privacy/requests/export   { email }               → everything about that person (JSON)
    POST /privacy/requests/delete   { email, confirm }      → their data erased in place (confirm = the email again)
    GET  /settings/data-region                              → DataRegionInfo (settings.view)

Exports and deletions are in the audit trail with the address masked.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin, require_auth
from app.modules.billing.service import has_feature
from app.modules.privacy import service
from app.modules.settings.catalogues import RETENTION_DAYS

router = APIRouter(tags=["privacy"])

DATA_REGIONS = ("default", "eu", "uk", "us", "ca", "au", "in", "sg", "br")


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


async def _body(request: Request) -> Any:
    raw = await request.body()
    return (await request.json()) if raw else None


@router.get("/settings/privacy/retention-preview", dependencies=[rate_limit("privacy-preview", per_minute=60)])
async def retention_preview(days: str | None = None, principal: Principal = Depends(require_admin)) -> Any:
    try:
        # Number(): a missing value is NaN, an empty one 0
        value = float("nan") if days is None else float(days) if days.strip() else 0.0
    except ValueError:
        value = float("nan")
    if value not in RETENTION_DAYS:
        raise FrmError("FRM-GEN-1002", [{"field": "days", "message": "retention"}])
    async with db_session("read", **_scope(principal)) as db:
        return ok(await service.preview(db, principal.tenant.id, int(value)))


email_schema = z.obj(email=z.string().email().max(200))
delete_schema = z.obj(email=z.string().email().max(200), confirm=z.string().max(200))


@router.post("/privacy/requests/search", dependencies=[rate_limit("privacy-requests", per_minute=30)])
async def search_request(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    email = email_schema.parse(await _body(request))["email"]
    async with db_session("read", **_scope(principal)) as db:
        return ok(await service.search(db, principal.tenant.id, email))


@router.post("/privacy/requests/export", dependencies=[rate_limit("privacy-requests", per_minute=10)])
async def export_request(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    email = email_schema.parse(await _body(request))["email"]
    async with db_session("write", **_scope(principal)) as db:
        data = await service.export(db, principal.tenant.id, email)
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="settings.data_exported", actor=Actor.user(principal.user),
                     resource={"type": "person", "id": None, "name": service.masked(data["email"])},
                     metadata={"responses": str(len(data["responses"]))})
    return ok(data)


@router.post("/privacy/requests/delete", dependencies=[rate_limit("privacy-requests", per_minute=10)])
async def delete_request(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = delete_schema.parse(await _body(request))
    if service.normalise(body["confirm"]) != service.normalise(body["email"]):
        raise FrmError("FRM-GEN-1002", [{"field": "confirm", "message": "confirm"}])
    async with db_session("write", **_scope(principal)) as db:
        result = await service.erase_person(db, principal.tenant.id, body["email"], principal.user.id)
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="settings.data_deleted", actor=Actor.user(principal.user),
                     resource={"type": "person", "id": None, "name": service.masked(service.normalise(body["email"]))},
                     metadata={"responses": str(result["responses"]), "forms": str(result["forms"])})
    return ok(result)


@router.get("/settings/data-region", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_data_region(principal: Principal = Depends(require_auth)) -> Any:
    """Where the workspace's data lives: read only (another region is set up by the Formalie team, a migration)."""
    if not principal.can("settings.view"):
        raise FrmError("FRM-PERM-1001")
    async with db_session("read", **_scope(principal)) as db:
        region = (await db.execute(text("SELECT data_region FROM platform.tenant_profile()"))).scalar_one_or_none()
    return ok({"region": region if region in DATA_REGIONS else "default", "regions": list(DATA_REGIONS),
               "residency": has_feature(principal.tenant.plan_id, "data_residency")})

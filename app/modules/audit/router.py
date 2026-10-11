"""Audit trail routes (mock: routes/audit.ts): list, facets, one entry, export.

Permissions come from the route (Roles & access: `audit.view`, `audit.export`), checked by require_auth.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit import export as _export  # noqa: F401  (registers the export file)
from app.modules.audit import queries
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_auth
from app.modules.exports import service as exports

router = APIRouter(tags=["audit"])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _organisation(principal: Principal) -> dict[str, Any]:
    return {"id": str(principal.tenant.organisation_id), "name": principal.tenant.name}


@router.get("/audit-logs", dependencies=[rate_limit("audit-list", per_minute=120)])
async def list_audit_logs(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    async with db_session("read", **_scope(principal)) as db:
        rows, total = await queries.page(db, principal.tenant.id, query, offset=params.offset, limit=params.page_size)
    organisation = _organisation(principal)
    return ok([queries.view(row, organisation) for row in rows], params.meta(total))


@router.get("/audit-logs/facets", dependencies=[rate_limit("audit-facets", per_minute=60)])
async def audit_facets(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await queries.facets(db, principal.tenant.id))


@router.get("/audit-logs/{entry_id}", dependencies=[rate_limit("audit-get", per_minute=120)])
async def get_audit_log(entry_id: str, principal: Principal = Depends(require_auth)) -> Any:
    try:
        wanted = uuid.UUID(entry_id)  # a typed-in id arrives as "invalid-reference"
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("read", **_scope(principal)) as db:
        row = await queries.one(db, principal.tenant.id, wanted)
    if row is None:
        raise FrmError("FRM-GEN-1004")
    return ok(queries.view(row, _organisation(principal)))


class ExportBody(BaseModel):
    format: Literal["xlsx", "csv"]
    filters: dict[str, str | int | float] = Field(default_factory=dict)


@router.post("/audit-logs/export", status_code=202, dependencies=[rate_limit("audit-export", per_minute=5)])
async def export_audit_logs(body: ExportBody, principal: Principal = Depends(require_auth)) -> Any:
    """Same filters as the list; made in the background (poll GET /exports/{id}); recorded in the trail itself."""
    filters = {k: queries.js_string(v) for k, v in body.filters.items()}
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    async with db_session("write", **_scope(principal)) as db:
        rows = await queries.count(db, principal.tenant.id, filters)
        job = await exports.create(
            db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
            user_id=principal.user.id, kind="audit", format=body.format,
            file_name=f"audit-trail-{principal.tenant.subdomain}-{stamp}.{body.format}", rows=rows,
            params={"filters": filters, "organisation": _organisation(principal)})
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="audit.exported", actor=Actor.user(principal.user),
                     resource={"type": "export", "id": str(job.id), "name": job.file_name},
                     metadata={"format": body.format, "rows": str(rows)})
        reply = exports.view(job)
    exports.dispatch(job)
    return ok(reply)

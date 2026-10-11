"""Organisation data routes (mock: routes/org.ts, API-CONTRACT → Organisation data). Admins only; `kind` is
departments or job_titles.

    GET    /org/{kind}                 list (q, sort, filter[status], pages) · /insights · /{id} · /{id}/usage
    POST   /org/{kind}                 { name, code, description, member_ids } → the entry (names unique per kind)
    PATCH  /org/{kind}/{id}            the same
    POST   /org/{kind}/{id}/archive    archived entries stay on forms that use them, flagged · /restore
    POST   /org/{kind}/merge           { from: [ids], into: id }: people and forms move to `into`, the rest go
    POST   /org/{kind}/import          { names: [] } → { created, skipped }
    DELETE /org/{kind}/{id}            only when no form uses it (else FRM-ORG-1002)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.org import service
from app.modules.org.models import OrgUnit
from app.modules.settings.catalogues import ORG_KINDS

router = APIRouter(tags=["org"])


def _optional(size: int) -> z.Schema:
    return z.string().trim().max(size).nullable().transform(lambda v: v or None)


item_schema = z.obj(
    name=z.string().trim().min(1).max(80),
    code=_optional(20),
    description=_optional(200),
    member_ids=z.array(z.string().max(100)).max(1000),
)
merge_schema = z.obj({"from": z.array(z.string()).min(1).max(100), "into": z.string()})
import_schema = z.obj(names=z.array(z.string()).min(1).max(1000))


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _kind(value: str) -> str:
    if value not in ORG_KINDS:
        raise FrmError("FRM-GEN-1004")
    return value


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def _find(db: Any, tenant_id: uuid.UUID, kind: str, item_id: str) -> OrgUnit:
    wanted = _uuid(item_id)
    unit = await db.get(OrgUnit, wanted) if wanted else None
    if unit is None or unit.tenant_id != tenant_id or unit.kind != kind or unit.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return unit


def _resource(kind: str, unit: OrgUnit) -> dict[str, Any]:
    return {"type": kind.removesuffix("s"), "id": str(unit.id), "name": unit.name}


async def _checked(db: Any, tenant_id: uuid.UUID, kind: str, values: dict[str, Any],
                   except_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Names unique per kind (archived ones too); only people of the workspace, each once."""
    if any(u.id != except_id and u.name.lower() == values["name"].lower()
           for u in await service.units_of(db, tenant_id, kind)):
        raise FrmError("FRM-ORG-1001", [{"field": "name", "message": "taken"}])
    people = {p["id"] for p in await service.people_of(db, tenant_id)}
    members = list(dict.fromkeys(m for m in values["member_ids"] if (_uuid(m) and str(_uuid(m)) in people)))
    return {**values, "member_ids": [str(_uuid(m)) for m in members]}


async def _item(db: Any, tenant_id: uuid.UUID, kind: str, unit: OrgUnit) -> dict[str, Any]:
    members = await service.members_of(db, tenant_id, [unit.id])
    return service.to_item(kind, unit, members[unit.id], await service.people_of(db, tenant_id))


@router.get("/org/{kind}", dependencies=[rate_limit("org-list", per_minute=120)])
async def list_org(kind: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        units = await service.units_of(db, principal.tenant.id, kind)
        members = await service.members_of(db, principal.tenant.id, [u.id for u in units])
        people = await service.people_of(db, principal.tenant.id)
    rows = [service.to_item(kind, u, members[u.id], people) for u in units]
    # in_use: active with people · empty: active, nobody in it · archived
    status = query.get("filter[status]")
    if status:
        wanted = status.split(",")
        rows = [r for r in rows if ("archived" if r["status"] == "archived" else "in_use" if r["members"] else "empty")
                in wanted]
    sort = query.get("sort") or "name"
    desc, key = sort.startswith("-"), sort.lstrip("-")

    def value(row: dict[str, Any]) -> Any:
        if key == "members":
            return len(row["members"])
        if key == "forms":
            return row["forms_count"]
        if key in ("updated_at", "created_at"):
            return row[key]
        return row["name"].casefold()
    rows.sort(key=value, reverse=desc)
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in f"{r['name']} {r['code'] or ''} {r['description'] or ''}".lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/org/{kind}/insights", dependencies=[rate_limit("org-insights", per_minute=60)])
async def org_insights(kind: str, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    async with db_session("read", **_scope(principal)) as db:
        units = await service.units_of(db, principal.tenant.id, kind)
        members = await service.members_of(db, principal.tenant.id, [u.id for u in units])
        people = await service.people_of(db, principal.tenant.id)
    active = [u for u in units if not u.archived_at]
    assigned = {m for u in active for m in members[u.id]}
    largest = sorted(active, key=lambda u: len(members[u.id]), reverse=True)[:12]
    return ok({
        "total": len(units), "by_status": {"active": len(active), "archived": len(units) - len(active)},
        "people": len(people), "people_assigned": sum(1 for p in people if p["id"] in assigned),
        "empty": sum(1 for u in active if not members[u.id]),
        "largest": [{"id": str(u.id), "name": u.name, "count": len(members[u.id])} for u in largest],
    })


@router.post("/org/{kind}/merge", dependencies=[rate_limit("org-merge", per_minute=20)])
async def merge_org_items(kind: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    body = merge_schema.parse(await request.json())
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        target = await _find(db, tenant.id, kind, body["into"])
        sources = [await _find(db, tenant.id, kind, i) for i in dict.fromkeys(body["from"]) if _uuid(i) != target.id]
        if not sources:
            raise FrmError("FRM-GEN-1002", [{"field": "from", "message": "required"}])
        members = await service.members_of(db, tenant.id, [target.id, *(s.id for s in sources)])
        await service.set_members(db, target, [*members[target.id], *(m for s in sources for m in members[s.id])],
                                  principal.user.id)
        fields = service.move_audience(kind, [s.id for s in sources], target.id)
        now = datetime.now(UTC)
        for source in sources:
            source.deleted_at, source.deleted_by = now, principal.user.id
            await service.set_members(db, source, [], principal.user.id)
        target.updated_at = now
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.org_merged",
                     actor=Actor.user(principal.user), resource=_resource(kind, target),
                     metadata={"kind": service.LABEL[kind], "merged": ", ".join(s.name for s in sources),
                               "fields": str(fields)})
        return ok(await _item(db, tenant.id, kind, target))


@router.post("/org/{kind}/import", dependencies=[rate_limit("org-import", per_minute=10)])
async def import_org_items(kind: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    body = import_schema.parse(await request.json())
    tenant = principal.tenant
    result: dict[str, Any] = {"created": 0, "skipped": []}
    async with db_session("write", **_scope(principal)) as db:
        taken = {u.name.lower() for u in await service.units_of(db, tenant.id, kind)}
        for raw in body["names"]:
            name = raw.strip()
            if not name:
                continue
            if len(name) > 80:
                result["skipped"].append({"name": name[:80], "reason": "too_long"})
            elif name.lower() in taken:
                result["skipped"].append({"name": name, "reason": "duplicate"})
            else:
                taken.add(name.lower())
                db.add(OrgUnit(tenant_id=tenant.id, organisation_id=tenant.organisation_id, kind=kind, name=name,
                               created_by=principal.user.id))
                result["created"] += 1
        if result["created"]:
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.org_imported",
                         actor=Actor.user(principal.user), resource={"type": kind, "id": None, "name": service.LABEL[kind]},
                         metadata={"created": str(result["created"]), "skipped": str(len(result["skipped"]))})
    return ok(result)


@router.post("/org/{kind}", status_code=201, dependencies=[rate_limit("org-create", per_minute=60)])
async def create_org_item(kind: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        values = await _checked(db, tenant.id, kind, item_schema.parse(await request.json()))
        unit = OrgUnit(tenant_id=tenant.id, organisation_id=tenant.organisation_id, kind=kind, name=values["name"],
                       code=values["code"], description=values["description"], created_by=principal.user.id)
        db.add(unit)
        await db.flush()
        await service.set_members(db, unit, values["member_ids"], principal.user.id)
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.org_created",
                     actor=Actor.user(principal.user), resource=_resource(kind, unit),
                     metadata={"kind": service.LABEL[kind], "people": str(len(values["member_ids"]))})
        return ok(await _item(db, tenant.id, kind, unit))


@router.get("/org/{kind}/{item_id}", dependencies=[rate_limit("org-get", per_minute=120)])
async def get_org_item(kind: str, item_id: str, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    async with db_session("read", **_scope(principal)) as db:
        unit = await _find(db, principal.tenant.id, kind, item_id)
        return ok(await _item(db, principal.tenant.id, kind, unit))


@router.get("/org/{kind}/{item_id}/usage", dependencies=[rate_limit("org-usage", per_minute=60)])
async def org_usage(kind: str, item_id: str, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    async with db_session("read", **_scope(principal)) as db:
        unit = await _find(db, principal.tenant.id, kind, item_id)
    return ok(service.usage_of(kind, unit.id))


@router.patch("/org/{kind}/{item_id}", dependencies=[rate_limit("org-update", per_minute=60)])
async def update_org_item(kind: str, item_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    kind = _kind(kind)
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        unit = await _find(db, tenant.id, kind, item_id)
        values = await _checked(db, tenant.id, kind, item_schema.parse(await request.json()), unit.id)
        before_members = (await service.members_of(db, tenant.id, [unit.id]))[unit.id]
        before = {"name": unit.name, "code": unit.code, "description": unit.description, "people": str(len(before_members))}
        unit.name, unit.code, unit.description = values["name"], values["code"], values["description"]
        unit.updated_at = datetime.now(UTC)
        await service.set_members(db, unit, values["member_ids"], principal.user.id)
        after = {"name": unit.name, "code": unit.code, "description": unit.description,
                 "people": str(len(values["member_ids"]))}
        changes = [{"field": k, "before": before[k], "after": after[k]} for k in after if before[k] != after[k]]
        if changes:
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.org_updated",
                         actor=Actor.user(principal.user), resource=_resource(kind, unit), changes=changes,
                         metadata={"kind": service.LABEL[kind]})
        return ok(await _item(db, tenant.id, kind, unit))


async def _set_archived(kind: str, item_id: str, principal: Principal, archive: bool) -> Any:
    kind = _kind(kind)
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        unit = await _find(db, tenant.id, kind, item_id)
        if bool(unit.archived_at) != archive:
            now = datetime.now(UTC)
            unit.archived_at, unit.updated_at = (now if archive else None), now
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                         action="settings.org_archived" if archive else "settings.org_restored",
                         actor=Actor.user(principal.user), resource=_resource(kind, unit),
                         metadata={"kind": service.LABEL[kind]})
        return ok(await _item(db, tenant.id, kind, unit))


@router.post("/org/{kind}/{item_id}/archive", dependencies=[rate_limit("org-archive", per_minute=60)])
async def archive_org_item(kind: str, item_id: str, principal: Principal = Depends(require_admin)) -> Any:
    return await _set_archived(kind, item_id, principal, True)


@router.post("/org/{kind}/{item_id}/restore", dependencies=[rate_limit("org-archive", per_minute=60)])
async def restore_org_item(kind: str, item_id: str, principal: Principal = Depends(require_admin)) -> Any:
    return await _set_archived(kind, item_id, principal, False)


@router.delete("/org/{kind}/{item_id}", dependencies=[rate_limit("org-delete", per_minute=30)])
async def delete_org_item(kind: str, item_id: str, principal: Principal = Depends(require_admin)) -> Any:
    """Only when no form uses it; the entry and its people keep their rows, with deleted_at."""
    kind = _kind(kind)
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        unit = await _find(db, tenant.id, kind, item_id)
        usage = service.usage_of(kind, unit.id)
        if usage:
            raise FrmError("FRM-ORG-1002", [{"field": "form", "message": u["form"]["name"]} for u in usage[:5]])
        unit.deleted_at, unit.deleted_by = datetime.now(UTC), principal.user.id
        await service.set_members(db, unit, [], principal.user.id)
        await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.org_deleted",
                     actor=Actor.user(principal.user), resource=_resource(kind, unit),
                     metadata={"kind": service.LABEL[kind]})
    return ok({"deleted": True})


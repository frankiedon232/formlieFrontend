"""Roles & access (mock: routes/roles.ts, API-CONTRACT → Roles). Reading needs people.view, changing roles.manage
(the route permissions). Built-in roles are known by their key (owner · admin · member), the workspace's own by
their id. Owner can't be changed or deleted; a role somebody holds can't be deleted.

    GET    /roles · /roles/insights · /roles/{id}
    POST   /roles                 { name, description?, grants } (or `copy_of` a role)
    PATCH  /roles/{id}            { name?, description?, grants? }
    POST   /roles/{id}/duplicate
    DELETE /roles/{id}
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.rbac.catalogue import ALL_PERMISSIONS, SCOPES
from app.modules.rbac.permissions import OWNER_ROLE, reach_of, with_needs
from app.modules.rbac.service import find_role, grants_of, role_key, roles_of
from app.modules.uploads.service import file_url
from app.modules.users.models import Role, User

router = APIRouter(tags=["roles"])

_grants = z.partial_record(list(ALL_PERMISSIONS), z.enum(list(SCOPES)))
create_schema = z.obj(
    name=z.string().trim().min(1).max(60),
    description=z.string().trim().max(300).nullable().optional(),
    grants=_grants.optional(),
    copy_of=z.string().max(64).optional(),
)
patch_schema = z.obj(
    name=z.string().trim().min(1).max(60).optional(),
    description=z.string().trim().max(300).nullable().optional(),
    grants=_grants.optional(),
)


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def holders_by_role(db: Any, tenant_id: Any) -> dict[Any, list[User]]:
    """The people holding each role (disabled accounts don't count)."""
    users = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                 User.status != "disabled").order_by(User.created_at, User.id))).scalars()
    out: dict[Any, list[User]] = {}
    for user in users:
        out.setdefault(user.role_id, []).append(user)
    return out


def role_row(role: Role, holders: dict[Any, list[User]]) -> dict[str, Any]:
    """RoleRow (shared/types/people.ts)."""
    people = holders.get(role.id, [])
    return {
        "id": role_key(role), "name": role.name, "description": role.description, "grants": grants_of(role),
        "built_in": role.built_in, "people_count": len(people),
        "people": [{"id": str(p.id), "name": f"{p.first_name} {p.last_name}".strip() or p.email,
                    "photo": file_url(p.photo_upload_id) if p.photo_upload_id else None} for p in people[:5]],
        "created_at": _iso(role.created_at), "updated_at": _iso(role.updated_at),
    }


async def _find(db: Any, tenant_id: Any, key: str) -> Role:
    role = await find_role(db, tenant_id, key)
    if role is None:
        raise FrmError("FRM-GEN-1004")
    return role


async def _name_free(db: Any, tenant_id: Any, name: str, except_id: Any = None) -> None:
    if any(r.id != except_id and r.name.lower() == name.lower() for r in await roles_of(db, tenant_id)):
        raise FrmError("FRM-ORG-1001", [{"field": "name", "message": "taken"}])


async def _audit(db: Any, principal: Principal, action: str, role: Role,
                 changes: list[dict[str, Any]] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource={"type": "role", "id": role_key(role), "name": role.name},
                 changes=changes or [])


def _describe(grants: dict[str, str], keys: list[str]) -> str:
    """'forms.edit (own)' for the audit trail."""
    return ", ".join(f"{k} ({grants[k]})" for k in keys)


@router.get("/roles", dependencies=[rate_limit("roles-list", per_minute=120)])
async def list_roles(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        holders = await holders_by_role(db, principal.tenant.id)
        rows = [role_row(r, holders) for r in await roles_of(db, principal.tenant.id)]
    if "page" not in query:
        return ok(rows)
    kinds = query["filter[kind]"].split(",") if query.get("filter[kind]") else []
    if kinds:
        rows = [r for r in rows if ("builtin" if r["built_in"] else "own") in kinds]
    sort = query.get("sort") or "name"
    key = sort.lstrip("-")
    rows.sort(key=lambda r: r["people_count"] if key == "people_count" else str(r.get(key, r["name"])).casefold(),
              reverse=sort.startswith("-"))
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in f"{r['name']} {r['description'] or ''}".lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/roles/insights", dependencies=[rate_limit("roles-insights", per_minute=60)])
async def roles_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        holders = await holders_by_role(db, principal.tenant.id)
        rows = [role_row(r, holders) for r in await roles_of(db, principal.tenant.id)]
    return ok({
        "total": len(rows), "custom": sum(1 for r in rows if not r["built_in"]),
        "people": sum(r["people_count"] for r in rows),
        "by_role": [{"id": r["id"], "name": r["name"], "count": r["people_count"]}
                    for r in sorted(rows, key=lambda r: -r["people_count"])],
        "reach": [{"id": r["id"], "name": r["name"], "share": 1 if r["id"] == OWNER_ROLE else reach_of(r["grants"])}
                  for r in rows],
    })


@router.get("/roles/{role_id}", dependencies=[rate_limit("roles-get", per_minute=120)])
async def get_role(role_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        role = await _find(db, principal.tenant.id, role_id)
        return ok(role_row(role, await holders_by_role(db, principal.tenant.id)))


@router.post("/roles", status_code=201, dependencies=[rate_limit("roles-create", per_minute=30)])
async def create_role(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = create_schema.parse(await request.json())
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        await _name_free(db, tenant.id, body["name"])
        source = await _find(db, tenant.id, body["copy_of"]) if body.get("copy_of") else None
        description = body["description"] if "description" in body else (source.description if source else None)
        grants = body["grants"] if "grants" in body else (grants_of(source) if source else {})
        role = Role(tenant_id=tenant.id, organisation_id=tenant.organisation_id, name=body["name"],
                    description=description or None, built_in=None, grants=with_needs(grants or {}),
                    created_by=principal.user.id)
        db.add(role)
        await db.flush()
        await db.refresh(role)
        await _audit(db, principal, "users.role_created", role)
        return ok(role_row(role, {}))


@router.patch("/roles/{role_id}", dependencies=[rate_limit("roles-update", per_minute=60)])
async def update_role(role_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        role = await _find(db, tenant.id, role_id)
        if role.built_in == OWNER_ROLE:
            raise FrmError("FRM-USER-1007")
        body = patch_schema.parse(await request.json())
        if body.get("name"):
            await _name_free(db, tenant.id, body["name"], role.id)
        before = grants_of(role)
        after = with_needs(body["grants"]) if "grants" in body else before
        added = [k for k in after if not before.get(k)]
        removed = [k for k in before if not after.get(k)]
        rescoped = [k for k in after if before.get(k) and before[k] != after[k]]
        changes = []
        if body.get("name") and body["name"] != role.name:
            changes.append({"field": "name", "before": role.name, "after": body["name"]})
        if "description" in body and (body["description"] or None) != role.description:
            changes.append({"field": "description", "before": role.description, "after": body["description"] or None})
        if added:
            changes.append({"field": "permissions_added", "before": None, "after": _describe(after, added)})
        if removed:
            changes.append({"field": "permissions_removed", "before": _describe(before, removed), "after": None})
        if rescoped:
            changes.append({"field": "permissions_scope", "before": _describe(before, rescoped),
                            "after": _describe(after, rescoped)})
        if body.get("name"):
            role.name = body["name"]
        if "description" in body:
            role.description = body["description"] or None
        role.grants, role.row_version = after, role.row_version + 1
        role.updated_at, role.updated_by = datetime.now(UTC), principal.user.id
        if changes:
            await _audit(db, principal, "users.role_updated", role, changes)
        return ok(role_row(role, await holders_by_role(db, tenant.id)))


@router.post("/roles/{role_id}/duplicate", status_code=201, dependencies=[rate_limit("roles-create", per_minute=30)])
async def duplicate_role(role_id: str, principal: Principal = Depends(require_admin)) -> Any:
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        source = await _find(db, tenant.id, role_id)
        taken = {r.name.lower() for r in await roles_of(db, tenant.id)}
        name, n = f"{source.name} (copy)"[:60], 2
        while name.lower() in taken:
            name, n = f"{source.name} (copy {n})"[:60], n + 1
        role = Role(tenant_id=tenant.id, organisation_id=tenant.organisation_id, name=name,
                    description=source.description, built_in=None, grants=dict(grants_of(source)),
                    created_by=principal.user.id)
        db.add(role)
        await db.flush()
        await db.refresh(role)
        await _audit(db, principal, "users.role_created", role)
        return ok(role_row(role, {}))


@router.delete("/roles/{role_id}", dependencies=[rate_limit("roles-delete", per_minute=30)])
async def delete_role(role_id: str, principal: Principal = Depends(require_admin)) -> Any:
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        role = await _find(db, tenant.id, role_id)
        if role.built_in:
            raise FrmError("FRM-USER-1007")
        held = (await db.execute(select(User.id).where(User.tenant_id == tenant.id, User.role_id == role.id,
                                                       User.deleted_at.is_(None)).limit(1))).first()
        if held:
            raise FrmError("FRM-USER-1008")
        role.deleted_at, role.deleted_by = datetime.now(UTC), principal.user.id
        await _audit(db, principal, "users.role_deleted", role)
        return ok({"id": role_key(role)})

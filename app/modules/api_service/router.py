"""API service management (mock: routes/apiService.ts, apiConnections.ts; API-CONTRACT → API service (F13)).

    GET    /api-service/settings          the workspace's address handle and base address
    GET    /api-service/setup             how far the workspace is (guided setup)
    POST   /api-service/key/rotate        a new address handle; the old one answers for a grace period
    GET    /api-service/connections       what a service, endpoint, token or rule is connected to
    GET    /api-services                  list (q, sort, filter[status])        · /insights
    GET    /api-services/{id}             one                                  · POST · PATCH · DELETE
    POST   /api-services/{id}/duplicate   a copy with copies of its endpoints (switched off)
    GET    /api-endpoints                 list (q, sort, filter[service|form|method|status]) · /insights
    GET    /api-endpoints/form-fields     a form's questions as endpoint fields (the wizard)
    GET    /api-endpoints/{id}            one with its fields                  · POST · PATCH · DELETE

Endpoint names are unique in the workspace (FRM-API-1001: the name is the address); an endpoint needs a published
form (FRM-API-1002) that is open to the API (FRM-API-1019). The form's own rules decide which questions can be sent:
required questions are always accepted, read-only ones, signatures, payments and calculated values never.
Tokens (tokens.py) and access rules (access_router.py) have their own files.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text, update

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.api_service import service as S
from app.modules.api_service import traffic as TR
from app.modules.api_service.endpoints import API_PAGE_SIZE_MAX, check_api_name, check_endpoint_name, endpoint_fields_of
from app.modules.api_service.models import ApiAccessRule, ApiEndpoint, ApiService
from app.modules.api_service.origins import MAX_ALLOWED_ORIGINS, normalise_origin
from app.modules.api_service.tokens import ROTATION_GRACE_HOURS
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.forms.models import Form
from app.modules.rbac.resources import owned_reach

router = APIRouter(tags=["api service"])

STATUSES = ["active", "disabled"]
service_schema = z.obj(
    name=z.string().trim().min(1).max(80),
    description=z.string().trim().max(300).nullable().optional(),
    status=z.enum(STATUSES).optional(),
    allowed_origins=z.array(z.string().max(200)).max(MAX_ALLOWED_ORIGINS).optional(),
)
service_patch_schema = z.obj(
    name=z.string().trim().min(1).max(80).optional(),
    description=z.string().trim().max(300).nullable().optional(),
    status=z.enum(STATUSES).optional(),
    allowed_origins=z.array(z.string().max(200)).max(MAX_ALLOWED_ORIGINS).optional(),
)
endpoint_schema = z.obj(
    name=z.string().trim().max(64),
    description=z.string().trim().max(300).nullable().optional(),
    service_id=z.string(),
    form_id=z.string(),
    version=z.number().int().positive().nullable(),
    methods=z.array(z.enum(list(S.API_METHODS))).max(4),
    fields=z.array(z.obj(key=z.string().max(64), name=z.string().max(64).optional(), accept=z.boolean(),
                         required=z.boolean(), returned=z.boolean(), filter=z.boolean())).max(500),
    page_size=z.number().int().min(1).max(API_PAGE_SIZE_MAX),
    headers=z.array(z.obj(name=z.string().trim().max(64), value=z.string().max(200).nullable())).max(5).optional(),
    status=z.enum(STATUSES).optional(),
)
rotate_schema = z.obj(grace_hours=z.number().int().refine(lambda n: n in ROTATION_GRACE_HOURS))
connections_schema = z.obj(type=z.enum(["service", "endpoint", "token", "rule"]), id=z.string().min(1).max(64))


def scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


async def audit(db: Any, principal: Principal, action: str, resource: dict[str, Any], *,
                changes: list[dict[str, Any]] | None = None, metadata: dict[str, str] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource=resource, changes=changes or [], metadata=metadata or {})


async def load(db: Any, principal: Principal, *, forms: bool = True) -> S.Store:
    """Everything of the workspace's API service; its settings are made the first time (with a write session)."""
    store = await S.Store(principal.tenant.id).load(db, forms=forms)
    if store.settings is None:
        async with db_session("write", **scope(principal)) as w:
            store.settings = await S.ensure_settings(w, principal.tenant.id, principal.tenant.organisation_id)
    return store


def page(query: dict[str, str], rows: list[dict[str, Any]], search: Any) -> Any:
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if search(r, q)]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


def now() -> datetime:
    return datetime.now(UTC)


# ── Settings, setup, the address handle ────────────────────────────────────────

@router.get("/api-service/settings", dependencies=[rate_limit("api-settings", per_minute=120)])
async def api_settings(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        return ok(S.settings_view(await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)))


@router.post("/api-service/key/rotate", dependencies=[rate_limit("api-key-rotate", per_minute=10)])
async def rotate_api_key(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    """A new address handle; every endpoint's address changes, the old handle keeps answering for `grace_hours`."""
    grace = rotate_schema.parse(await request.json())["grace_hours"]
    async with db_session("write", **scope(principal)) as db:
        row = await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)
        moment = now()
        # A handle still in its grace period from an earlier rotation stops now
        if row.previous_key:
            await db.execute(text("SELECT platform.retire_api_key(:k, :u)"),
                             {"k": row.previous_key, "u": min(moment, row.previous_until or moment)})
        until = moment + timedelta(hours=grace)
        await db.execute(text("SELECT platform.retire_api_key(:k, :u)"), {"k": row.api_key, "u": until})
        row.previous_key = row.api_key if grace else None
        row.previous_until = until if grace else None
        row.api_key = await S.claim_handle(db)
        row.rotated_at = moment
        row.updated_by = principal.user.id
        await audit(db, principal, "api.key_rotated", {"type": "api_service", "id": None, "name": row.api_key},
                    metadata={"grace_hours": str(grace)})
        await db.flush()
        return ok(S.settings_view(row))


@router.get("/api-service/setup", dependencies=[rate_limit("api-setup", per_minute=120)])
async def api_setup(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False, traffic=False)
    tokens = [t for t in store.tokens if t.kind != "webhook" and t.revoked_at is None
              and (t.expires_at is None or t.expires_at > now())]
    return ok({"services": len(store.services), "endpoints": len(store.endpoints),
               "endpoints_live": sum(1 for e in store.endpoints if e.status == "active"),
               "tokens_live": sum(1 for t in tokens if t.mode == "live"),
               "tokens_test": sum(1 for t in tokens if t.mode == "test"),
               "rules": sum(1 for r in store.rules if r.enabled)})


@router.get("/api-service/connections", dependencies=[rate_limit("api-connections", per_minute=240)])
async def api_connections(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    """What an API item is connected to (owner 2026-10-08), for the Connections block of every detail panel."""
    values = connections_schema.parse(dict(request.query_params))
    kind, wanted = values["type"], S.path_uuid(values["id"])
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db)
    names = {s.id: s.name for s in store.services}
    able = S.callers(store)

    def endpoint_link(e: ApiEndpoint) -> dict[str, Any]:
        return {"id": str(e.id), "name": e.name, "status": e.status, "service": names.get(e.service_id, "")}

    def token_link(t: Any, reach: str) -> dict[str, Any]:
        return {"id": str(t.id), "name": t.name, "mode": t.mode, "status": S.token_status(t), "reach": reach}

    def rule_link(r: ApiAccessRule) -> dict[str, Any]:
        return {"id": str(r.id), "action": r.action, "kind": r.kind, "values": list(r.values)[:3], "enabled": r.enabled,
                "reach": r.scope_type}

    def best_reach(t: Any, endpoints: list[ApiEndpoint]) -> str:
        reaches = [S.reach_of(t, e) for e in endpoints if S.can_call(t, e)]
        return "endpoint" if "endpoint" in reaches else "service" if "service" in reaches else "all"

    def service_ref(s: ApiService) -> dict[str, Any]:
        return {"id": str(s.id), "name": s.name, "status": s.status}

    out: dict[str, Any] = {"service": None, "form": None, "endpoints": [], "tokens": [], "rules": []}
    if kind in ("service", "endpoint"):
        endpoint = store.endpoint(wanted) if kind == "endpoint" else None
        found = store.service(endpoint.service_id if endpoint else wanted)
        if found is None or (kind == "endpoint" and endpoint is None):
            raise FrmError("FRM-GEN-1004")
        endpoints = [endpoint] if endpoint else [e for e in store.endpoints if e.service_id == found.id]
        if endpoint:
            out["service"] = service_ref(found)
            form = store.forms.get(endpoint.form_id)
            out["form"] = {"id": str(form.id), "name": form.name, "status": form.status} if form else None
        else:
            out["endpoints"] = [endpoint_link(e) for e in endpoints]
        out["tokens"] = [token_link(t, best_reach(t, endpoints)) for t in able if any(S.can_call(t, e) for e in endpoints)]
        ids = {e.id for e in endpoints}
        applies = S.rules_on(store, endpoint) if endpoint else [
            r for r in store.rules if r.scope_type == "all" or (r.scope_type == "service" and r.scope_id == found.id)
            or (r.scope_type == "endpoint" and r.scope_id in ids)]
        out["rules"] = [rule_link(r) for r in applies]
    elif kind == "token":
        token = next((t for t in store.tokens if t.id == wanted), None)
        if token is None:
            raise FrmError("FRM-GEN-1004")
        reachable = [] if token.kind == "webhook" else [e for e in store.endpoints if S.can_call(token, e)]
        out["endpoints"] = [endpoint_link(e) for e in reachable]
        services = list(dict.fromkeys(e.service_id for e in reachable))
        named = token.scopes["services"]
        if len(named) == 1 and store.service(S.path_uuid(named[0])):
            out["service"] = service_ref(store.service(S.path_uuid(named[0])))  # type: ignore[arg-type]
        elif len(services) == 1:
            out["service"] = service_ref(store.service(services[0]))  # type: ignore[arg-type]
    else:
        rule = next((r for r in store.rules if r.id == wanted), None)
        if rule is None:
            raise FrmError("FRM-GEN-1004")
        if rule.scope_type == "service":
            found = store.service(rule.scope_id)
            if found:
                out["service"] = service_ref(found)
            out["endpoints"] = [endpoint_link(e) for e in store.endpoints if e.service_id == rule.scope_id]
        else:
            out["endpoints"] = [endpoint_link(e) for e in store.endpoints
                                if rule.scope_type == "all" or e.id == rule.scope_id]
    return ok(out)


# ── Services ────────────────────────────────────────────────────────────────────

def _can(principal: Principal, item: ApiService) -> dict[str, bool]:
    """What this person may do with it (F22 R2 M4: own · all)."""
    return {"edit": owned_reach("api.service_edit", item.created_by, principal),
            "delete": owned_reach("api.service_delete", item.created_by, principal)}


def _origins(values: list[str] | None) -> list[str] | None:
    """Allowed websites in their one form, each once; anything that isn't a website → FRM-GEN-1002 (leftovers L6)."""
    if values is None:
        return None
    out: list[str] = []
    for value in values:
        origin = normalise_origin(value)
        if not origin:
            raise FrmError("FRM-GEN-1002", [{"field": "allowed_origins", "message": value}])
        if origin not in out:
            out.append(origin)
    return out


def _find_service(store: S.Store, raw: str) -> ApiService:
    found = store.service(S.path_uuid(raw))
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


def _service_resource(item: ApiService) -> dict[str, Any]:
    return {"type": "api_service", "id": str(item.id), "name": item.name}


@router.get("/api-services", dependencies=[rate_limit("api-services", per_minute=120)])
async def list_api_services(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    rows = [{**S.service_view(store, s), "_item": s} for s in store.services]
    rows = [r for r in rows if S.in_list(query.get("filter[status]"), r["status"])]
    rows = S.sort_rows(rows, query.get("sort") or "name")
    rows = [{**{k: v for k, v in r.items() if k != "_item"}, "can": _can(principal, r["_item"])} for r in rows]
    return page(query, rows, lambda r, q: q in f"{r['name']} {r['description'] or ''}".lower())


@router.get("/api-services/insights", dependencies=[rate_limit("api-services", per_minute=60)])
async def api_service_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    views = [S.service_view(store, s) for s in store.services]
    return ok(S.insights_of([v["status"] for v in views], [v["methods"] for v in views],
                            TR.sum_usage([store.service_usage(s) for s in store.services])))


@router.get("/api-services/{service_id}", dependencies=[rate_limit("api-services", per_minute=240)])
async def get_api_service(service_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    item = _find_service(store, service_id)
    return ok({**S.service_view(store, item), "can": _can(principal, item)})


async def _name_taken(db: Any, tenant_id: uuid.UUID, name: str, except_id: uuid.UUID | None = None) -> bool:
    where = [ApiService.tenant_id == tenant_id, ApiService.deleted_at.is_(None)]
    rows = (await db.execute(select(ApiService.id, ApiService.name).where(*where))).all()
    return any(r.name.lower() == name.lower() and r.id != except_id for r in rows)


@router.post("/api-services", status_code=201, dependencies=[rate_limit("api-services-write", per_minute=30)])
async def create_api_service(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = service_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        if await _name_taken(db, principal.tenant.id, values["name"]):
            raise FrmError("FRM-API-1003")
        item = ApiService(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          name=values["name"], description=values.get("description") or None,
                          status=values.get("status") or "active", allowed_origins=_origins(values.get("allowed_origins")) or [],
                          created_by=principal.user.id, updated_by=principal.user.id)
        db.add(item)
        await db.flush()
        await audit(db, principal, "api.service_created", _service_resource(item))
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        return ok(S.service_view(store, store.service(item.id)))  # type: ignore[arg-type]


@router.patch("/api-services/{service_id}", dependencies=[rate_limit("api-services-write", per_minute=60)])
async def update_api_service(service_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        item = _find_service(store, service_id)
        if not owned_reach("api.service_edit", item.created_by, principal):
            raise FrmError("FRM-PERM-1001")
        values = service_patch_schema.parse(await request.json())
        if values.get("name") and await _name_taken(db, principal.tenant.id, values["name"], item.id):
            raise FrmError("FRM-API-1003")
        before = {"name": item.name, "status": item.status, "origins": ", ".join(item.allowed_origins or [])}
        origins = _origins(values.get("allowed_origins"))
        if origins is not None:
            item.allowed_origins = origins
        if "name" in values:
            item.name = values["name"]
        if "description" in values:
            item.description = values["description"] or None
        if "status" in values:
            item.status = values["status"]
        item.updated_at, item.updated_by = now(), principal.user.id
        resource = _service_resource(item)
        if "status" in values and values["status"] != before["status"]:
            await audit(db, principal, "api.service_enabled" if values["status"] == "active" else "api.service_disabled", resource)
        if ("name" in values and values["name"] != before["name"]) or "description" in values:
            changes = [{"field": "name", "before": before["name"], "after": item.name}] \
                if "name" in values and values["name"] != before["name"] else []
            await audit(db, principal, "api.service_updated", resource, changes=changes)
        if origins is not None and ", ".join(origins) != before["origins"]:
            await audit(db, principal, "api.service_updated", resource, changes=[
                {"field": "allowed_origins", "before": before["origins"] or None, "after": ", ".join(origins) or None}])
        await db.flush()
        return ok(S.service_view(store, item))


def free_name(taken: set[str], base: str) -> str:
    """A free endpoint name: `name-copy`, `name-copy-2`, …"""
    stem = f"{base}-copy"[:58]
    n = 1
    while True:
        name = stem if n == 1 else f"{stem}-{n}"
        if name not in taken:
            return name
        n += 1


@router.post("/api-services/{service_id}/duplicate", status_code=201, dependencies=[rate_limit("api-services-write", per_minute=20)])
async def duplicate_api_service(service_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        source = _find_service(store, service_id)
        name, n = f"{source.name} (copy)", 2
        while any(s.name.lower() == name.lower() for s in store.services):
            name, n = f"{source.name} (copy {n})", n + 1
        copy = ApiService(tenant_id=source.tenant_id, organisation_id=source.organisation_id, name=name[:80],
                          description=source.description, status="disabled", allowed_origins=list(source.allowed_origins or []),
                          created_by=principal.user.id, updated_by=principal.user.id)
        db.add(copy)
        await db.flush()
        taken = {e.name for e in store.endpoints}
        for e in [e for e in store.endpoints if e.service_id == source.id]:
            fresh = free_name(taken, e.name)
            taken.add(fresh)
            db.add(ApiEndpoint(tenant_id=e.tenant_id, organisation_id=e.organisation_id, service_id=copy.id, name=fresh,
                               description=e.description, form_id=e.form_id, version=e.version, methods=list(e.methods),
                               fields=[dict(f) for f in e.fields], page_size=e.page_size,
                               headers=[dict(h) for h in e.headers or []], status="disabled",
                               created_by=principal.user.id, updated_by=principal.user.id))
        await db.flush()
        await audit(db, principal, "api.service_created", _service_resource(copy), metadata={"copy_of": source.name})
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        return ok(S.service_view(store, store.service(copy.id)))  # type: ignore[arg-type]


@router.delete("/api-services/{service_id}", dependencies=[rate_limit("api-services-write", per_minute=30)])
async def delete_api_service(service_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        item = _find_service(store, service_id)
        if not owned_reach("api.service_delete", item.created_by, principal):
            raise FrmError("FRM-PERM-1001")
        moment, by = now(), principal.user.id
        gone = [e.id for e in store.endpoints if e.service_id == item.id]
        item.deleted_at, item.deleted_by = moment, by
        if gone:
            await db.execute(update(ApiEndpoint).where(ApiEndpoint.tenant_id == principal.tenant.id, ApiEndpoint.id.in_(gone))
                             .values(deleted_at=moment, deleted_by=by))
        # Rules made for it (or its endpoints) go too
        await db.execute(update(ApiAccessRule).where(
            ApiAccessRule.tenant_id == principal.tenant.id, ApiAccessRule.deleted_at.is_(None),
            ((ApiAccessRule.scope_type == "service") & (ApiAccessRule.scope_id == item.id))
            | ((ApiAccessRule.scope_type == "endpoint") & (ApiAccessRule.scope_id.in_(gone or [uuid.uuid4()]))))
            .values(deleted_at=moment, deleted_by=by))
        await audit(db, principal, "api.service_deleted", _service_resource(item), metadata={"endpoints": str(len(gone))})
    return ok({"deleted": True, "endpoints": len(gone)})


# ── Endpoints ───────────────────────────────────────────────────────────────────

def _find_endpoint(store: S.Store, raw: str) -> ApiEndpoint:
    found = store.endpoint(S.path_uuid(raw))
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


def _endpoint_resource(item: ApiEndpoint) -> dict[str, Any]:
    return {"type": "api_endpoint", "id": str(item.id), "name": item.name}


@router.get("/api-endpoints", dependencies=[rate_limit("api-endpoints", per_minute=120)])
async def list_api_endpoints(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        store = await load(db, principal)
    rows = [S.endpoint_view(store, e) for e in store.endpoints]
    rows = [r for r in rows if S.in_list(query.get("filter[service]"), r["service"]["id"])
            and S.in_list(query.get("filter[form]"), r["form"]["id"]) and S.in_list(query.get("filter[status]"), r["status"])
            and (not query.get("filter[method]") or any(m in r["methods"] for m in query["filter[method]"].split(",")))]
    rows = S.sort_rows(rows, query.get("sort") or "name")
    return page(query, rows, lambda r, q: q in f"{r['name']} {r['form']['name']} {r['service']['name']} {r['description'] or ''}".lower())


@router.get("/api-endpoints/insights", dependencies=[rate_limit("api-endpoints", per_minute=60)])
async def api_endpoint_insights(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    wanted = request.query_params.get("filter[service]")
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    endpoints = [e for e in store.endpoints if S.in_list(wanted, str(e.service_id))]
    return ok(S.insights_of([e.status for e in endpoints], [list(e.methods) for e in endpoints],
                            TR.sum_usage([store.endpoint_usage(e) for e in endpoints])))


@router.get("/api-endpoints/form-fields", dependencies=[rate_limit("api-endpoints", per_minute=120)])
async def api_endpoint_form_fields(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    """A form's questions as endpoint fields (the wizard, before saving) and its published versions."""
    form_id = S.ref_uuid(request.query_params.get("form_id"))
    raw_version = request.query_params.get("version")
    async with db_session("read", **scope(principal)) as db:
        form = await db.get(Form, form_id) if form_id else None
        if form is None or form.tenant_id != principal.tenant.id or form.deleted_at is not None or form.purged_at is not None:
            raise FrmError("FRM-GEN-1004")
        try:
            version = int(float(raw_version)) if raw_version else None
        except ValueError:
            version = None
        schema = await S.schema_of(db, principal.tenant.id, form, version)
        if schema is None or form.status != "published":
            raise FrmError("FRM-API-1002")
        store = S.Store(principal.tenant.id)
        await store.load_forms(db, {form.id})
    return ok({"fields": endpoint_fields_of(schema), "versions": store.forms[form.id].versions})


@router.get("/api-endpoints/{endpoint_id}", dependencies=[rate_limit("api-endpoints", per_minute=240)])
async def get_api_endpoint(endpoint_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await load(db, principal)
        return ok(await S.endpoint_detail(db, store, _find_endpoint(store, endpoint_id)))


async def checked(db: Any, principal: Principal, store: S.Store, values: dict[str, Any],
                  except_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Checks an endpoint as the mock does, in the same order, and keeps only what the form allows."""
    problem = check_endpoint_name(values["name"])
    if problem:
        raise FrmError("FRM-GEN-1002", [{"field": "name", "message": problem}])
    if any(e.id != except_id and e.name == values["name"] for e in store.endpoints):
        raise FrmError("FRM-API-1001", [{"field": "name", "message": "taken"}])
    service = store.service(S.ref_uuid(values["service_id"]))
    if service is None:
        raise FrmError("FRM-GEN-1002", [{"field": "service_id", "message": "required"}])
    form_id = S.ref_uuid(values["form_id"])
    form = await db.get(Form, form_id) if form_id else None
    if form is None or form.tenant_id != principal.tenant.id or form.deleted_at is not None or form.purged_at is not None:
        raise FrmError("FRM-GEN-1002", [{"field": "form_id", "message": "required"}])
    schema = await S.schema_of(db, principal.tenant.id, form, values["version"])
    if schema is None or form.status != "published":
        raise FrmError("FRM-API-1002", [{"field": "form_id", "message": "not_published"}])
    if "api" not in (list(form.channels) if form.channels else list(S.FORM_CHANNELS)):
        raise FrmError("FRM-API-1019", [{"field": "form_id", "message": "not_for_api"}])
    if not values["methods"]:
        raise FrmError("FRM-GEN-1002", [{"field": "methods", "message": "required"}])
    # API names: valid and unique (the saved names are what apps use)
    named = [f for f in values["fields"] if "name" in f]
    bad = next((f for f in named if check_api_name(f["name"])), None)
    if bad:
        raise FrmError("FRM-GEN-1002", [{"field": f"fields.{bad['key']}.name", "message": check_api_name(bad["name"])}])
    seen: set[str] = set()
    for f in named:
        if f["name"] in seen:
            raise FrmError("FRM-GEN-1002", [{"field": f"fields.{f['key']}.name", "message": "taken"}])
        seen.add(f["name"])
    fields = endpoint_fields_of(schema, values["fields"])
    if any(m in ("POST", "PUT") for m in values["methods"]) and not any(f["accept"] for f in fields):
        raise FrmError("FRM-GEN-1002", [{"field": "fields", "message": "accept"}])
    if "GET" in values["methods"] and not any(f["returned"] for f in fields):
        raise FrmError("FRM-GEN-1002", [{"field": "fields", "message": "returned"}])
    return {
        # No custom headers (owner, 2026-10-06): whatever is sent, an endpoint has none
        "headers": [],
        "service_id": service.id, "name": values["name"], "description": values.get("description") or None,
        "form_id": form.id, "version": values["version"],
        "methods": [m for m in S.API_METHODS if m in values["methods"]],
        "fields": [{k: f[k] for k in ("key", "name", "accept", "required", "returned", "filter")} for f in fields],
        "page_size": values["page_size"],
        # New endpoints start not live: test tokens can try them, live calls wait for Go live (owner, 2026-10-06)
        "status": values.get("status") or "disabled",
        "_form_name": form.name,
    }


@router.post("/api-endpoints", status_code=201, dependencies=[rate_limit("api-endpoints-write", per_minute=30)])
async def create_api_endpoint(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = endpoint_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        store = await load(db, principal)
        data = await checked(db, principal, store, values)
        form_name = data.pop("_form_name")
        item = ApiEndpoint(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, **data,
                           created_by=principal.user.id, updated_by=principal.user.id)
        db.add(item)
        await db.flush()
        await audit(db, principal, "api.endpoint_created", _endpoint_resource(item),
                    metadata={"methods": ", ".join(item.methods), "form": form_name})
        store.endpoints.append(item)
        await store.load_forms(db, {item.form_id})
        return ok(await S.endpoint_detail(db, store, item))


@router.patch("/api-endpoints/{endpoint_id}", dependencies=[rate_limit("api-endpoints-write", per_minute=60)])
async def update_api_endpoint(endpoint_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = await request.json()
    async with db_session("write", **scope(principal)) as db:
        store = await load(db, principal)
        item = _find_endpoint(store, endpoint_id)
        # Switching on / off alone
        if isinstance(body, dict) and set(body) == {"status"} and body["status"] in STATUSES:
            if body["status"] != item.status:
                item.status, item.updated_at, item.updated_by = body["status"], now(), principal.user.id
                await audit(db, principal, "api.endpoint_enabled" if item.status == "active" else "api.endpoint_disabled",
                            _endpoint_resource(item))
                await db.flush()
            return ok(await S.endpoint_detail(db, store, item))
        values = endpoint_schema.parse(body)
        before = item.name
        data = await checked(db, principal, store, {**values, "status": values.get("status") or item.status}, item.id)
        data.pop("_form_name")
        for key, value in data.items():
            setattr(item, key, value)
        item.updated_at, item.updated_by = now(), principal.user.id
        await audit(db, principal, "api.endpoint_updated", _endpoint_resource(item),
                    changes=[{"field": "name", "before": before, "after": item.name}] if before != item.name else [],
                    metadata={"methods": ", ".join(item.methods)})
        await db.flush()
        await store.load_forms(db, {item.form_id})
        return ok(await S.endpoint_detail(db, store, item))


@router.delete("/api-endpoints/{endpoint_id}", dependencies=[rate_limit("api-endpoints-write", per_minute=30)])
async def delete_api_endpoint(endpoint_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        item = _find_endpoint(store, endpoint_id)
        moment = now()
        item.deleted_at, item.deleted_by = moment, principal.user.id
        await db.execute(update(ApiAccessRule).where(
            ApiAccessRule.tenant_id == principal.tenant.id, ApiAccessRule.deleted_at.is_(None),
            ApiAccessRule.scope_type == "endpoint", ApiAccessRule.scope_id == item.id)
            .values(deleted_at=moment, deleted_by=principal.user.id))
        await audit(db, principal, "api.endpoint_deleted", _endpoint_resource(item))
    return ok({"deleted": True})

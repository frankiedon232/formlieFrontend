"""API access rules and rate limits (mock: routes/apiAccess.ts, F13 M3; API-CONTRACT → API service).

    GET    /api-access-rules              list (q, sort, filter[action|kind|scope|state]) · /insights · /{id}
    POST   /api-access-rules              { action, kind, values, scope, note?, enabled? } · PATCH · DELETE
    POST   /api-access-rules/test         would this caller get in (endpoint, IP, origin, country, networks)?
    GET    /api-service/limits            calls per minute per token, IP and endpoint · PUT

The rules themselves (values, matching, the decision) are app/modules/api_service/access.py, the frontend's own.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.api_service import access as A
from app.modules.api_service import service as S
from app.modules.api_service import traffic as TR
from app.modules.api_service.models import ApiAccessRule
from app.modules.api_service.origins import parse_url
from app.modules.api_service.router import audit, page, scope
from app.modules.auth.sessions import Principal, require_admin

router = APIRouter(tags=["api service"])

rule_schema = z.obj(
    action=z.enum(["allow", "block"]),
    kind=z.enum(list(A.API_RULE_KINDS)),
    values=z.array(z.string().trim().max(255)).min(1).max(50),
    scope=z.obj(type=z.enum(["all", "service", "endpoint"]), id=z.string().nullable()),
    note=z.string().trim().max(300).nullable().optional(),
    enabled=z.boolean().optional(),
)
_limit = z.number().int().min(1).max(100_000).nullable()
limits_schema = z.obj(per_token=_limit, per_ip=_limit, per_endpoint=_limit)
test_schema = z.obj(endpoint_id=z.string(), ip=z.string().trim().max(64), origin=z.string().trim().max(255).nullable().optional(),
                    country=z.string().trim().max(2).nullable().optional(),
                    networks=z.array(z.enum(list(A.API_NETWORKS))).max(4).optional())


def _resource(rule: ApiAccessRule) -> dict[str, Any]:
    return {"type": "api_rule", "id": str(rule.id), "name": f"{rule.action} {rule.kind}"}


def _checked(store: S.Store, values: dict[str, Any]) -> dict[str, Any]:
    """Values checked per kind (duplicates dropped), the scope naming a service or endpoint of this workspace."""
    problems = [{"field": f"values.{i}", "message": p} for i, v in enumerate(values["values"])
                if (p := A.check_rule_value(values["kind"], v))]
    if problems:
        raise FrmError("FRM-GEN-1002", problems)
    kind, target = values["scope"]["type"], None
    if kind == "service":
        target = S.ref_uuid(values["scope"]["id"])
        if store.service(target) is None:
            raise FrmError("FRM-GEN-1002", [{"field": "scope", "message": "service"}])
    if kind == "endpoint":
        target = S.ref_uuid(values["scope"]["id"])
        if store.endpoint(target) is None:
            raise FrmError("FRM-GEN-1002", [{"field": "scope", "message": "endpoint"}])
    normal = list(dict.fromkeys(A.normalise_rule_value(values["kind"], v) for v in values["values"]))
    return {"action": values["action"], "kind": values["kind"], "values": normal, "scope_type": kind,
            "scope_id": target, "note": values.get("note") or None}


def _find(store: S.Store, raw: str) -> ApiAccessRule:
    wanted = S.path_uuid(raw)
    found = next((r for r in store.rules if r.id == wanted), None)
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


@router.get("/api-access-rules", dependencies=[rate_limit("api-rules", per_minute=120)])
async def list_access_rules(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    rows = [S.rule_view(store, r) for r in store.rules]
    rows = [r for r in rows if S.in_list(query.get("filter[action]"), r["action"]) and S.in_list(query.get("filter[kind]"), r["kind"])
            and S.in_list(query.get("filter[scope]"), r["scope"]["type"])
            and S.in_list(query.get("filter[state]"), "on" if r["enabled"] else "off")]
    rows = S.sort_rows(rows, query.get("sort") or "-created_at")
    return page(query, rows, lambda r, q: q in f"{' '.join(r['values'])} {r['note'] or ''} {r['scope']['name'] or ''}".lower())


@router.get("/api-access-rules/insights", dependencies=[rate_limit("api-rules", per_minute=60)])
async def access_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    rules = store.rules
    refused = TR.sum_usage([TR.usage_view(store.traffic.rules.get(r.id)) for r in rules if r.action == "block"])
    return ok({
        "total": len(rules), "by_action": {a: sum(1 for r in rules if r.action == a) for a in ("allow", "block")},
        "by_kind": {k: sum(1 for r in rules if r.kind == k) for k in A.API_RULE_KINDS},
        # Calls refused by the block rules there are now (the 30 days before for the change), calls over a rate limit
        "refused_30d": refused["calls_30d"], "previous_30d": refused["previous_30d"], "daily": refused["daily"],
        "limited_30d": sum(store.traffic.limited.get(d, 0) for d in TR.days_back(30)),
    })


@router.post("/api-access-rules/test", dependencies=[rate_limit("api-rules-test", per_minute=60)])
async def test_access(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = test_schema.parse(await request.json())
    if A.check_rule_value("ip", values["ip"]) or "/" in values["ip"]:
        raise FrmError("FRM-GEN-1002", [{"field": "ip", "message": "ip"}])
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    endpoint = store.endpoint(S.ref_uuid(values["endpoint_id"]))
    if endpoint is None:
        raise FrmError("FRM-GEN-1002", [{"field": "endpoint_id", "message": "required"}])
    domain = None
    if values.get("origin"):
        origin = values["origin"]
        parsed = parse_url(origin if "://" in origin else f"https://{origin}")
        if parsed is None:
            raise FrmError("FRM-GEN-1002", [{"field": "origin", "message": "domain"}])
        domain = str(parsed["host"]).lower()
    country = values["country"].upper() if values.get("country") else None
    applies = S.rules_on(store, endpoint)
    caller = A.AccessCaller(ip=values["ip"], domain=domain, country=country, networks=values.get("networks") or [])
    decision = A.decide_access([{"id": str(r.id), "action": r.action, "kind": r.kind, "values": list(r.values),
                                 "enabled": r.enabled} for r in applies], caller)
    rule = None
    if decision["rule"]:
        found = next(r for r in applies if str(r.id) == decision["rule"]["id"])
        view = S.rule_view(store, found)
        rule = {"id": view["id"], "action": view["action"], "value": decision["rule"]["value"], "kind": view["kind"],
                "scope": view["scope"]}
    return ok({"allowed": decision["allowed"], "reason": decision["reason"], "rule": rule,
               "checked": sum(1 for r in applies if r.enabled), "region": A.region_of(country)})


@router.get("/api-access-rules/{rule_id}", dependencies=[rate_limit("api-rules", per_minute=240)])
async def get_access_rule(rule_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    return ok(S.rule_view(store, _find(store, rule_id)))


@router.post("/api-access-rules", status_code=201, dependencies=[rate_limit("api-rules-write", per_minute=30)])
async def create_access_rule(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = rule_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        rule = ApiAccessRule(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                             **_checked(store, values), enabled=values.get("enabled", True),
                             created_by=principal.user.id, updated_by=principal.user.id)
        db.add(rule)
        await db.flush()
        await audit(db, principal, "api.rule_created", _resource(rule),
                    metadata={"values": ", ".join(rule.values)[:300], "scope": rule.scope_type})
        return ok(S.rule_view(store, rule))


@router.patch("/api-access-rules/{rule_id}", dependencies=[rate_limit("api-rules-write", per_minute=60)])
async def update_access_rule(rule_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = await request.json()
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        rule = _find(store, rule_id)
        resource = _resource(rule)
        # Switching on / off alone
        if isinstance(body, dict) and set(body) == {"enabled"} and isinstance(body["enabled"], bool):
            if rule.enabled != body["enabled"]:
                rule.enabled, rule.updated_at, rule.updated_by = body["enabled"], datetime.now(UTC), principal.user.id
                await audit(db, principal, "api.rule_enabled" if rule.enabled else "api.rule_disabled", resource)
                await db.flush()
            return ok(S.rule_view(store, rule))
        values = rule_schema.parse(body)
        for key, value in _checked(store, values).items():
            setattr(rule, key, value)
        if "enabled" in values:
            rule.enabled = values["enabled"]
        rule.updated_at, rule.updated_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.rule_updated", resource,
                    metadata={"values": ", ".join(rule.values)[:300], "scope": rule.scope_type})
        await db.flush()
        return ok(S.rule_view(store, rule))


@router.delete("/api-access-rules/{rule_id}", dependencies=[rate_limit("api-rules-write", per_minute=30)])
async def delete_access_rule(rule_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        rule = _find(store, rule_id)
        rule.deleted_at, rule.deleted_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.rule_deleted", _resource(rule))
    return ok({"deleted": True})


# ── Rate limits ────────────────────────────────────────────────────────────────

@router.get("/api-service/limits", dependencies=[rate_limit("api-limits", per_minute=120)])
async def get_rate_limits(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        return ok(S.limits_view(await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)))


@router.put("/api-service/limits", dependencies=[rate_limit("api-limits-write", per_minute=30)])
async def update_rate_limits(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = limits_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        row = await S.ensure_settings(db, principal.tenant.id, principal.tenant.organisation_id)
        before = S.limits_view(row)
        row.rate_per_token, row.rate_per_ip, row.rate_per_endpoint = values["per_token"], values["per_ip"], values["per_endpoint"]
        row.limits_updated_at, row.updated_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.limits_changed", {"type": "api_service", "id": None, "name": "Rate limits"},
                    changes=[{"field": k, "before": before[k], "after": values[k]}
                             for k in ("per_token", "per_ip", "per_endpoint") if before[k] != values[k]])
        await db.flush()
        return ok(S.limits_view(row))

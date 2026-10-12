"""Data sources (mock: routes/dataSources.ts; API-CONTRACT → Data sources). Credentials are write-only: accepted on
create or change, kept encrypted, never in a reply.

    GET    /datasources            list (q, sort, filter[status|engine|access])
    GET    /datasources/insights   the two chart cards
    GET    /datasources/meta       Formalie's outgoing addresses to allow
    POST   /datasources/test       test a new or changed configuration → { id } (runs in the worker)
    GET    /datasources/tests/{id} the test so far (steps finish one after another)
    POST   /datasources            create (its status from `test_id` when given)
    GET    /datasources/{id}       detail (settings, which secrets are set, checks, uptime)
    PATCH  /datasources/{id}       name, settings, access, secrets (only those sent), enabled
    POST   /datasources/{id}/test  test the saved connection now → { id }
    POST   /datasources/{id}/duplicate
    DELETE /datasources/{id}       refused while forms store their responses there
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.billing.service import limits_of
from app.modules.data_sources import engines as E
from app.modules.data_sources import service, tasks
from app.modules.data_sources.models import DataSource, DataSourceTest
from app.modules.forms.router import _natural
from app.modules.forms.service import Names
from app.modules.rbac.resources import owned_reach

router = APIRouter(tags=["data sources"])

STATUSES = ("connected", "attention", "failing", "disabled", "untested")
access_schema = z.obj(
    table_prefix=z.enum(["formalie_", "fmly_", "form_"]).optional(),
    tables_schema=z.string().trim().max(128).optional(),
    other=z.enum(["none", "read", "read_write"]).optional(),
    schemas=z.array(z.string().trim().min(1).max(128)).max(20).optional(),
)
_settings = z.record(z.string(), z.union([z.string().max(4000), z.number(), z.boolean()]))
_secrets = z.record(z.string(), z.string().max(20_000))
config_schema = z.obj(engine=z.enum(list(E.DB_ENGINES)), settings=_settings, access=access_schema,
                      secrets=_secrets.optional(), datasource_id=z.string().optional())
save_schema = z.obj(engine=z.enum(list(E.DB_ENGINES)), settings=_settings, access=access_schema, secrets=_secrets.optional(),
                    name=z.string().trim().min(1).max(80), test_id=z.string().optional())
patch_schema = z.obj(name=z.string().trim().min(1).max(80).optional(), settings=_settings.optional(),
                     access=access_schema.optional(), secrets=_secrets.optional(), enabled=z.boolean().optional(),
                     test_id=z.string().optional())


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _access(engine: str, given: dict[str, Any]) -> dict[str, Any]:
    import re

    schema = (given.get("tables_schema") or "").strip()
    if schema and not re.fullmatch(r"[^\W\d][\w$]*", schema):
        raise FrmError("FRM-GEN-1002", [{"field": "access.tables_schema", "message": "Invalid string: must match pattern"}])
    return {"table_prefix": given.get("table_prefix") or "formalie_",
            "tables_schema": schema if E.has_tables_schema(engine) else "",
            "other": given.get("other") or "read_write", "schemas": list(given.get("schemas") or [])}


def _validate(engine: str, settings: dict[str, Any], secrets: dict[str, str], secrets_set: list[str] | None = None) -> None:
    problems = E.check_config(engine, settings, secrets, secrets_set or [])
    if problems:
        raise FrmError("FRM-GEN-1002", [{"field": k, "message": v} for k, v in problems.items()])


_IDENTITY = ("host", "port", "instance", "descriptor", "username", "ssh", "ssh_host", "ssh_port", "ssh_username")
_TLS_MODE = {"postgresql": "ssl_mode", "mysql": "ssl_mode", "mariadb": "ssl_mode", "sqlserver": "encrypt",
             "oracle": "protocol"}


def _identity(settings: dict[str, Any]) -> list[str]:
    return [str(settings.get(k) if settings.get(k) is not None else "").strip().lower() for k in _IDENTITY]


def reusable_secrets(engine: str, saved: DataSource | None, settings: dict[str, Any]) -> dict[str, str]:
    """Stored secrets a test or change may reuse (security review B17, H2): only for the same engine and the same
    server and account (host, port, instance, descriptor, user name, SSH server and user). Pointing a saved
    connection anywhere else needs its secrets typed again, so they can't be sent to another server."""
    if saved is None or saved.engine != engine or _identity(saved.settings) != _identity(settings):
        return {}
    return E.clean_secrets(engine, settings, service.open_secrets(saved.secrets_enc))


def refuse_tls_downgrade(engine: str, saved: DataSource, settings: dict[str, Any], reused: dict[str, str]) -> None:
    """While stored secrets are reused, the encryption can't be weakened (PostgreSQL disable / allow / prefer,
    MySQL disabled / preferred, SQL Server optional, Oracle plain TCP) unless the saved connection already used
    exactly that mode: otherwise a password could be sent in the clear to be read on the way."""
    if not reused or E.is_encrypted(engine, settings):
        return
    key = _TLS_MODE.get(engine, "ssl_mode")
    if str(settings.get(key) or "") != str(saved.settings.get(key) or ""):
        raise FrmError("FRM-DEST-1003", [{"field": key, "message": "tls_required_with_saved_secrets"}])


def _plan_allows(principal: Principal, engine: str) -> None:
    """Subscription: the databases the plan lets the workspace bring."""
    if engine not in (limits_of(principal.tenant.plan_id).get("databases") or []):
        raise FrmError("FRM-PLAN-1002", [{"field": "engine", "message": engine}])


async def _find(db: Any, principal: Principal, datasource_id: str) -> DataSource:
    try:
        source = await db.get(DataSource, uuid.UUID(datasource_id))
    except ValueError:
        source = None
    if source is None or source.tenant_id != principal.tenant.id or source.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return source


def _resource(source: DataSource) -> dict[str, Any]:
    return {"type": "data_source", "id": str(source.id), "name": source.name}


async def _audit(db: Any, principal: Principal, action: str, source: DataSource, *, changes: list[dict[str, Any]] | None = None,
                 metadata: dict[str, str] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource=_resource(source), changes=changes or [], metadata=metadata or {})


def _can(principal: Principal, source: DataSource) -> dict[str, bool]:
    return {"edit": owned_reach("data.edit", source.created_by, principal),
            "delete": owned_reach("data.delete", source.created_by, principal)}


def _require(principal: Principal, permission: str, source: DataSource) -> None:
    if not owned_reach(permission, source.created_by, principal):
        raise FrmError("FRM-PERM-1001")


async def _test_for_save(db: Any, principal: Principal, test_id: str | None) -> DataSourceTest | None:
    if not test_id:
        return None
    try:
        test = await db.get(DataSourceTest, uuid.UUID(test_id))
    except ValueError:
        test = None
    if test is None or test.tenant_id != principal.tenant.id:
        raise FrmError("FRM-DEST-1008")
    return test


async def _detail(db: Any, principal: Principal, source: DataSource) -> dict[str, Any]:
    facts = await service.Facts().load(db, principal.tenant.id, [source])
    names = await Names().load(db, principal.tenant.id)
    return {**service.detail_of(source, facts, names), "can": _can(principal, source)}


# ── Tests ───────────────────────────────────────────────────────────────────────

@router.post("/datasources/test", status_code=201, dependencies=[rate_limit("datasources-test", per_minute=20)])
async def start_connection_test(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = config_schema.parse(await request.json())
    engine = data["engine"]
    _plan_allows(principal, engine)
    async with db_session("write", **_scope(principal)) as db:
        saved = await _find(db, principal, data["datasource_id"]) if data.get("datasource_id") else None
        if saved is not None:
            _require(principal, "data.edit", saved)  # testing with a saved connection's secrets is editing it (H2)
        settings = E.clean_settings(engine, data["settings"])
        given = E.clean_secrets(engine, settings, data.get("secrets"))
        # Secrets left empty on a saved connection keep the stored ones, for the same server and account only
        kept = reusable_secrets(engine, saved, settings)
        _validate(engine, settings, given, list({**kept, **given}) if kept else [])
        if saved is not None:
            refuse_tls_downgrade(engine, saved, settings, {k: v for k, v in kept.items() if k not in given})
        label = saved.name if saved else E.address_of(engine, settings)
        test = service.new_test(principal.tenant.id, principal.tenant.organisation_id, principal.user.id,
                                saved.id if saved else None, label, engine, settings, _access(engine, data["access"]),
                                {**kept, **given}, host_key=saved.ssh_host_key if saved is not None else None)
        db.add(test)
        await db.flush()
        test_id = test.id
    tasks.dispatch_test(test)
    return ok({"id": str(test_id)})


@router.get("/datasources/tests/{test_id}", dependencies=[rate_limit("datasources-test-poll", per_minute=600)])
async def get_connection_test(test_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        test = await _test_for_save(db, principal, test_id)
        return ok(service.test_view(test))  # type: ignore[arg-type]


@router.post("/datasources/{datasource_id}/test", status_code=201, dependencies=[rate_limit("datasources-test", per_minute=20)])
async def test_saved_connection(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        source = await _find(db, principal, datasource_id)
        _require(principal, "data.edit", source)
        if not source.enabled:
            raise FrmError("FRM-DEST-1009")
        test = service.new_test(principal.tenant.id, principal.tenant.organisation_id, principal.user.id, source.id,
                                source.name, source.engine, source.settings, source.access,
                                service.open_secrets(source.secrets_enc), host_key=source.ssh_host_key)
        db.add(test)
        await db.flush()
        source.last_test_id = test.id  # "Test now" updates its status straight away
        test_id = test.id
    tasks.dispatch_test(test)
    return ok({"id": str(test_id)})


# ── List, insights, meta ────────────────────────────────────────────────────────

def _in(value: str | None, actual: str) -> bool:
    return not value or actual in value.split(",")


@router.get("/datasources", dependencies=[rate_limit("datasources-list", per_minute=120)])
async def list_data_sources(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        sources = await service.sources_of(db, principal.tenant.id)
        facts = await service.Facts().load(db, principal.tenant.id, sources)
        names = await Names().load(db, principal.tenant.id)
    rows = [{**service.row_of(s, facts, names), "_source": s} for s in sources]
    rows = [r for r in rows if _in(query.get("filter[status]"), r["status"]) and _in(query.get("filter[engine]"), r["engine"])
            and _in(query.get("filter[access]"), r["access"]["other"])]
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if any(q in str(r[k]).lower() for k in ("name", "address", "database", "engine"))]
    sort = query.get("sort") or "name"
    rows.sort(key=lambda r: _natural(r.get(sort.lstrip("-"))), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    page = rows[params.offset:params.offset + params.page_size]
    return ok([{**{k: v for k, v in r.items() if k != "_source"}, "can": _can(principal, r["_source"])} for r in page],
              params.meta(len(rows)))


@router.get("/datasources/insights", dependencies=[rate_limit("datasources-insights", per_minute=60)])
async def data_source_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        sources = await service.sources_of(db, principal.tenant.id)
        facts = await service.Facts().load(db, principal.tenant.id, sources)
        names = await Names().load(db, principal.tenant.id)
    rows = [service.row_of(s, facts, names) for s in sources]
    latencies = [r["latency_ms"] for r in rows if r["enabled"] and r["latency_ms"] is not None]
    daily = [{"date": d["date"], "count": sum(r["daily"][i]["count"] for r in rows)} for i, d in enumerate(rows[0]["daily"])] \
        if rows else []
    return ok({
        "total": len(rows), "by_status": {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES},
        "forms_sending": sum(r["forms_count"] for r in rows), "operations_30d": sum(r["operations_30d"] for r in rows),
        "previous_30d": sum(service.previous_ops(s, facts) for s in sources), "daily": daily,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "missing_permissions": sum(r["missing_permissions"] for r in rows),
    })


@router.get("/datasources/meta", dependencies=[rate_limit("datasources-meta", per_minute=60)])
async def data_source_meta(principal: Principal = Depends(require_admin)) -> Any:
    from app.modules.platform_bridge.globals import egress_ips

    return ok({"egress_ips": await egress_ips()})  # platform settings (B16), else the server's EGRESS_IPS


# ── Create, read, change, duplicate, delete ─────────────────────────────────────

@router.post("/datasources", status_code=201, dependencies=[rate_limit("datasources-create", per_minute=20)])
async def create_data_source(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = save_schema.parse(await request.json())
    engine = data["engine"]
    _plan_allows(principal, engine)
    settings = E.clean_settings(engine, data["settings"])
    secrets = E.clean_secrets(engine, settings, data.get("secrets"))
    _validate(engine, settings, secrets)
    async with db_session("write", **_scope(principal)) as db:
        if await service.name_taken(db, principal.tenant.id, data["name"]):
            raise FrmError("FRM-DEST-1007", [{"field": "name", "message": "taken"}])
        test = await _test_for_save(db, principal, data.get("test_id"))
        now = datetime.now(UTC)
        source = DataSource(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                            name=data["name"], engine=engine, settings=service.json_safe(settings),
                            secrets_enc=service.seal_secrets(secrets), secrets_set=sorted(secrets),
                            secrets_changed_at=now, access=_access(engine, data["access"]), enabled=True,
                            last_test_id=test.id if test else None, created_by=principal.user.id,
                            ssh_host_key=test.ssh_host_key if test is not None and test.status != "failed" else None)
        db.add(source)
        await db.flush()
        if test is not None:
            test.datasource_id = source.id
            if test.status != "running":
                await service.count_op(db, source)
        await _audit(db, principal, "data.connection_created", source, metadata={
            "engine": engine, "address": E.address_of(engine, settings), "access": source.access["other"],
            "prefix": source.access["table_prefix"], "status": service.status_of_source(source, test)})
        return ok(await _detail(db, principal, source))


@router.get("/datasources/{datasource_id}", dependencies=[rate_limit("datasources-get", per_minute=240)])
async def get_data_source(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await _detail(db, principal, await _find(db, principal, datasource_id)))


@router.patch("/datasources/{datasource_id}", dependencies=[rate_limit("datasources-update", per_minute=60)])
async def patch_data_source(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = patch_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        source = await _find(db, principal, datasource_id)
        _require(principal, "data.edit", source)
        changes: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        if "enabled" in data and data["enabled"] != source.enabled:
            source.enabled, source.updated_at = data["enabled"], now
            await _audit(db, principal, "data.connection_enabled" if data["enabled"] else "data.connection_disabled", source)
            if not any(k in data for k in ("name", "settings", "access", "secrets")):
                return ok(await _detail(db, principal, source))
        if data.get("name") and data["name"] != source.name:
            if await service.name_taken(db, principal.tenant.id, data["name"], source.id):
                raise FrmError("FRM-DEST-1007", [{"field": "name", "message": "taken"}])
            changes.append({"field": "name", "before": source.name, "after": data["name"]})
            source.name = data["name"]
        stored = service.open_secrets(source.secrets_enc)
        if "settings" in data or "access" in data:
            settings = E.clean_settings(source.engine, data.get("settings", source.settings))
            access = _access(source.engine, data.get("access", source.access))
            given = E.clean_secrets(source.engine, settings, data.get("secrets"))
            # Stored secrets stay only for the same server and account (H2); elsewhere they must be typed again
            kept = reusable_secrets(source.engine, source, settings)
            _validate(source.engine, settings, given, list(kept))
            refuse_tls_downgrade(source.engine, source, settings, {k: v for k, v in kept.items() if k not in given})
            before, after = E.address_of(source.engine, source.settings), E.address_of(source.engine, settings)
            if before != after:
                changes.append({"field": "host", "before": before, "after": after})
            if json.dumps(source.access, sort_keys=True) != json.dumps(access, sort_keys=True):
                changes.append({"field": "access", "before": source.access.get("other"), "after": access["other"]})
            if json.dumps(service.json_safe(settings), sort_keys=True) != json.dumps(source.settings, sort_keys=True) \
                    and before == after:
                changes.append({"field": "security", "before": None, "after": None})
            source.settings, source.access = service.json_safe(settings), access
            merged = {**kept, **given}
            source.secrets_enc, source.secrets_set = service.seal_secrets(merged), sorted(merged)
            if given:
                source.secrets_changed_at = now
                await _audit(db, principal, "data.credentials_changed", source, metadata={"fields": ", ".join(given)})
        elif data.get("secrets"):
            fresh = E.clean_secrets(source.engine, source.settings, data["secrets"])
            _validate(source.engine, source.settings, fresh, list(stored))
            merged = {**stored, **fresh}
            source.secrets_enc, source.secrets_set, source.secrets_changed_at = service.seal_secrets(merged), sorted(merged), now
            await _audit(db, principal, "data.credentials_changed", source, metadata={"fields": ", ".join(fresh)})
        # The test run for these changes becomes the connection's status; changes without one need a new test
        if data.get("test_id"):
            test = await _test_for_save(db, principal, data["test_id"])
            test.datasource_id, source.last_test_id = source.id, test.id  # type: ignore[union-attr]
        elif any(c["field"] != "name" for c in changes):
            source.last_test_id = None
        source.updated_at, source.updated_by, source.row_version = now, principal.user.id, source.row_version + 1
        if changes:
            await _audit(db, principal, "data.connection_updated", source, changes=changes)
        await db.flush()
        return ok(await _detail(db, principal, source))


@router.post("/datasources/{datasource_id}/duplicate", status_code=201, dependencies=[rate_limit("datasources-create", per_minute=20)])
async def duplicate_data_source(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        source = await _find(db, principal, datasource_id)
        name, n = f"{source.name} (copy)", 2
        while await service.name_taken(db, principal.tenant.id, name):
            name, n = f"{source.name} (copy {n})", n + 1
        copy = DataSource(tenant_id=source.tenant_id, organisation_id=source.organisation_id, name=name[:80],
                          engine=source.engine, settings=dict(source.settings), secrets_enc=source.secrets_enc,
                          secrets_set=list(source.secrets_set or []), secrets_changed_at=source.secrets_changed_at,
                          access=dict(source.access), enabled=source.enabled, created_by=principal.user.id,
                          ssh_host_key=source.ssh_host_key)
        db.add(copy)
        await db.flush()
        await _audit(db, principal, "data.connection_duplicated", copy, metadata={"from": source.name})
        return ok(await _detail(db, principal, copy))


@router.delete("/datasources/{datasource_id}", dependencies=[rate_limit("datasources-delete", per_minute=20)])
async def delete_data_source(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    from app.modules.data_sources.storage import forms_on_connections

    async with db_session("write", **_scope(principal)) as db:
        source = await _find(db, principal, datasource_id)
        _require(principal, "data.delete", source)
        if (await forms_on_connections(db, principal.tenant.id, [source.id])).get(source.id):
            raise FrmError("FRM-DEST-1010")
        source.deleted_at, source.deleted_by = datetime.now(UTC), principal.user.id
        await _audit(db, principal, "data.connection_deleted", source,
                     metadata={"engine": source.engine, "address": E.address_of(source.engine, source.settings)})
    return ok({"deleted": True})


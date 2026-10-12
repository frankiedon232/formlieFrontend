"""The Query editor, saved queries and Data sources → Activity (mock: routes/query.ts, savedQueries.ts,
dataActivity.ts; API-CONTRACT → Query editor, Data sources activity). Admins only, like connections.

    POST   /datasources/{id}/query            { sql, params?, page?, page_size?, confirm?, saved_id? } → QueryResult
    GET    /datasources/{id}/query-history    this person's last 50 statements on the connection
    DELETE /datasources/{id}/query-history    ?id= one, or all of them
    POST   /datasources/{id}/query/export     a reading statement's results as CSV / XLSX / JSON (a job)
    GET    /saved-queries · /saved-queries/insights · /saved-queries/{id}
    POST   /saved-queries · PATCH · DELETE /saved-queries/{id}   (changed only by the person who saved it)
    GET    /datasources/activity/insights     the Activity page's chart cards (from the audit trail)

One statement per run (FRM-DEST-1026). Reading: paged, counted up to 10,000. Changing rows or structure: the
`data.query_write` permission, Full access (FRM-DEST-1024), never Formalie's response tables (FRM-DEST-1019), and
only once confirmed (FRM-DEST-1023 says what it will do, with the rows it would touch from a dry run). Database
problems: FRM-DEST-1025 with the database's words and the position. Every run goes in the person's history; a
successful one in the audit trail (the statement, never its rows).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.data_sources import runner
from app.modules.data_sources.activity import ACTIVITY_KINDS, kind_of_action
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.service import iso
from app.modules.data_sources.sql import script_kind, split_statements, statement_kind, tables_in
from app.modules.data_sources.sql_guard import read_is_safe
from app.modules.explorer import service as X
from app.modules.explorer.router import opened, usable
from app.modules.forms.router import _natural
from app.modules.forms.service import Names
from app.modules.query.models import QueryHistory, SavedQuery, SavedQueryRunsDaily

router = APIRouter(tags=["query editor"])

COUNT_CAP = 10_000
HISTORY = 50
run_schema = z.obj(
    sql=z.string().max(100_000),
    params=z.record(z.string(), z.string()).optional(),
    page=z.number().int().min(1).optional(),
    page_size=z.number().int().min(1).max(100).optional(),
    confirm=z.boolean().optional(),
    saved_id=z.string().optional(),
)
export_schema = z.obj(
    sql=z.string().max(100_000),
    params=z.record(z.string(), z.string()).optional(),
    format=z.enum(["csv", "xlsx", "json"]),
    scope=z.enum(["page", "all"]).optional(),
    page=z.number().int().min(1).optional(),
    page_size=z.number().int().min(1).max(100).optional(),
)
saved_schema = z.obj(
    name=z.string().trim().min(1).max(120),
    description=z.string().trim().max(500).nullable().optional(),
    sql=z.string().min(1).max(100_000),
    datasource_id=z.string(),
    shared=z.boolean().optional(),
)
saved_patch_schema = z.obj(
    name=z.string().trim().min(1).max(120).optional(),
    description=z.string().trim().max(500).nullable().optional(),
    sql=z.string().min(1).max(100_000).optional(),
    shared=z.boolean().optional(),
)


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id, "user_id": principal.user.id}


async def _audit(principal: Principal, action: str, resource: dict[str, Any], metadata: dict[str, str]) -> None:
    async with db_session("write", **_scope(principal)) as db:
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                     actor=Actor.user(principal.user), resource=resource, metadata=metadata)


def _resource(source: DataSource) -> dict[str, Any]:
    return {"type": "data_source", "id": str(source.id), "name": source.name}


def _one_statement(sql: str) -> str:
    statements = split_statements(sql)
    if not statements:
        raise FrmError("FRM-GEN-1002", [{"field": "sql", "message": "required"}])
    if len(statements) > 1:
        raise FrmError("FRM-DEST-1026", [{"field": "sql", "message": str(len(statements))}])
    return statements[0].text


def _run_failed(error: runner.RunError) -> FrmError:
    if error.code == "FRM-DEST-1025":
        return FrmError("FRM-DEST-1025", [{"field": "message", "message": error.message},
                                          {"field": "position", "message": str(error.position)}])
    return FrmError(error.code)


def _resolve(tables: list[dict[str, Any]], written: str) -> dict[str, Any] | None:
    """`schema.table` or `table` (any schema the connection shows), case-insensitive."""
    parts = written.split(".")
    schema, name = (parts[0], parts[1]) if len(parts) > 1 else (None, parts[0])
    return next((t for t in tables if t["name"].lower() == name.lower() and (not schema or t["schema"].lower() == schema.lower())),
                None)


async def _history(principal: Principal, source: DataSource, sql: str, kind: str, *, ok_: bool, duration: int | None,
                   rows: int | None, code: str | None) -> None:
    async with db_session("write", **_scope(principal)) as db:
        db.add(QueryHistory(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                            user_id=principal.user.id, datasource_id=source.id, sql=sql, kind=kind, ran_at=datetime.now(UTC),
                            duration_ms=duration, rows=rows, ok=ok_, error_code=code, created_by=principal.user.id))


async def _count_saved(principal: Principal, saved_id: str) -> None:
    try:
        key = uuid.UUID(saved_id)
    except ValueError:
        return
    async with db_session("write", **_scope(principal)) as db:
        item = await db.get(SavedQuery, key)
        if item is None or item.tenant_id != principal.tenant.id or item.deleted_at is not None:
            return
        item.last_run_at = datetime.now(UTC)
        await db.execute(insert(SavedQueryRunsDaily).values(
            id=uuid.uuid4(), tenant_id=item.tenant_id, organisation_id=item.organisation_id, saved_query_id=item.id,
            day=datetime.now(UTC).date(), runs=1).on_conflict_do_update(
            index_elements=["tenant_id", "saved_query_id", "day"], set_={"runs": SavedQueryRunsDaily.runs + 1}))


# ── Running ─────────────────────────────────────────────────────────────────────

@router.post("/datasources/{datasource_id}/query", dependencies=[rate_limit("query-run", per_minute=120)])
async def run_query(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = run_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    sql = _one_statement(data["sql"])
    kind = statement_kind(sql)
    if kind == "read" and not read_is_safe(source.engine, sql):
        kind = "other"  # the engine would run more than a read: the change path's checks apply (B17, M7)
    params = data.get("params") or {}
    page, size = data.get("page") or 1, data.get("page_size") or 50
    engine = source.engine
    try:
        if kind == "read":
            async with opened(principal, source) as c:
                got = await runner.read(c, engine, sql, params, COUNT_CAP + 1)
            total = len(got["rows"])
            result = {"run_id": str(uuid.uuid4()), "kind": kind, "columns": got["columns"],
                      "rows": got["rows"][(page - 1) * size:page * size], "page": page, "page_size": size,
                      "total": min(total, COUNT_CAP), "capped": total > COUNT_CAP, "rows_affected": None,
                      "duration_ms": got["duration_ms"], "notice": None}
        else:
            # Running a changing statement is its own permission, next to the connection's access
            if not principal.grants.get("data.query_write"):
                raise FrmError("FRM-PERM-1001")
            if source.access.get("other") != "read_write":
                raise FrmError("FRM-DEST-1024", [{"field": "access", "message": str(source.access.get("other"))}])
            async with opened(principal, source) as c:
                tables = await X.tables_of(c, source)
                named = tables_in(sql)
                resolved = [_resolve(tables, name) for name in named]
                if any(t is not None and t["formalie"] for t in resolved):
                    raise FrmError("FRM-DEST-1019", [{"field": "table", "message": "response_table"}])
                if not data.get("confirm"):
                    estimate = None
                    if kind in ("insert", "update", "delete"):
                        estimate = (await runner.change(c, engine, sql, params, dry=True))["rows_affected"]
                    listed = [f"{t['schema']}.{t['name']}" if t else name for t, name in zip(resolved, named, strict=True)]
                    raise FrmError("FRM-DEST-1023", [{"field": "kind", "message": kind},
                                                     {"field": "tables", "message": ",".join(listed)},
                                                     {"field": "estimate", "message": "" if estimate is None else str(estimate)}])
                got = await runner.change(c, engine, sql, params, dry=False)
            result = {"run_id": str(uuid.uuid4()), "kind": kind, "columns": [], "rows": [], "page": 1, "page_size": size,
                      "total": None, "capped": False, "rows_affected": got["rows_affected"],
                      "duration_ms": got["duration_ms"], "notice": None}
    except runner.RunError as error:
        await _history(principal, source, sql, kind, ok_=False, duration=None, rows=None, code=error.code)
        raise _run_failed(error) from None
    except FrmError as error:
        # A confirm request isn't a run; everything else is kept in the history with its problem.
        if error.code != "FRM-DEST-1023":
            await _history(principal, source, sql, kind, ok_=False, duration=None, rows=None, code=error.code)
        raise
    rows = result["total"] if result["total"] is not None else result["rows_affected"]
    await _history(principal, source, sql, kind, ok_=True, duration=result["duration_ms"], rows=rows, code=None)
    if data.get("saved_id"):
        await _count_saved(principal, data["saved_id"])
    await _audit(principal, "data.query_run", _resource(source), {
        "kind": kind, "statement": sql[:300], "rows": str(rows or 0), "duration_ms": str(result["duration_ms"])})
    return ok(result)


@router.get("/datasources/{datasource_id}/query-history", dependencies=[rate_limit("query-history", per_minute=120)])
async def query_history(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    source = await usable(principal, datasource_id)
    async with db_session("read", **_scope(principal)) as db:
        items = (await db.execute(select(QueryHistory).where(
            QueryHistory.tenant_id == principal.tenant.id, QueryHistory.user_id == principal.user.id,
            QueryHistory.datasource_id == source.id, QueryHistory.deleted_at.is_(None))
            .order_by(QueryHistory.ran_at.desc()).limit(HISTORY))).scalars()
        return ok([{"id": str(h.id), "sql": h.sql, "kind": h.kind, "ran_at": iso(h.ran_at), "duration_ms": h.duration_ms,
                    "rows": h.rows, "ok": h.ok, "error_code": h.error_code} for h in items])


@router.delete("/datasources/{datasource_id}/query-history", dependencies=[rate_limit("query-history", per_minute=60)])
async def clear_query_history(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    source = await usable(principal, datasource_id)
    wanted = request.query_params.get("id")
    async with db_session("write", **_scope(principal)) as db:
        where = [QueryHistory.tenant_id == principal.tenant.id, QueryHistory.user_id == principal.user.id,
                 QueryHistory.datasource_id == source.id, QueryHistory.deleted_at.is_(None)]
        if wanted:
            try:
                where.append(QueryHistory.id == uuid.UUID(wanted))
            except ValueError:
                return ok({"cleared": True})
        await db.execute(update(QueryHistory).where(*where).values(deleted_at=datetime.now(UTC), deleted_by=principal.user.id))
    return ok({"cleared": True})


@router.post("/datasources/{datasource_id}/query/export", status_code=201, dependencies=[rate_limit("query-export", per_minute=20)])
async def export_query(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    from app.modules.explorer import exports

    data = export_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    statements = split_statements(data["sql"])
    if len(statements) != 1:
        raise FrmError("FRM-DEST-1026", [{"field": "sql", "message": str(len(statements))}])
    sql = statements[0].text
    if statement_kind(sql) != "read" or not read_is_safe(source.engine, sql):
        raise FrmError("FRM-GEN-1002", [{"field": "sql", "message": "read_only"}])
    return ok(await exports.start(principal, source, {
        "mode": "query", "sql": sql, "params": data.get("params") or {}, "format": data["format"],
        "scope": data.get("scope") or "page", "page": data.get("page") or 1, "page_size": data.get("page_size") or 50,
        "label": source.name, "total": 0, "capped": False}, f"query-results.{data['format']}", 0))


# ── Saved queries ───────────────────────────────────────────────────────────────

async def _sources(db: Any, tenant_id: uuid.UUID) -> dict[uuid.UUID, DataSource]:
    return {s.id: s for s in (await db.execute(select(DataSource).where(DataSource.tenant_id == tenant_id))).scalars()}


async def _visible(db: Any, principal: Principal) -> list[SavedQuery]:
    return list((await db.execute(select(SavedQuery).where(
        SavedQuery.tenant_id == principal.tenant.id, SavedQuery.deleted_at.is_(None),
        (SavedQuery.shared.is_(True)) | (SavedQuery.owner_id == principal.user.id))
        .order_by(SavedQuery.updated_at.desc()))).scalars())


async def _runs(db: Any, tenant_id: uuid.UUID, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[date, int]]:
    out: dict[uuid.UUID, dict[date, int]] = {}
    if ids:
        for r in (await db.execute(select(SavedQueryRunsDaily).where(
                SavedQueryRunsDaily.tenant_id == tenant_id, SavedQueryRunsDaily.saved_query_id.in_(ids)))).scalars():
            out.setdefault(r.saved_query_id, {})[r.day] = r.runs
    return out


def _view(item: SavedQuery, principal: Principal, sources: dict[uuid.UUID, DataSource], runs: dict[date, int],
          names: Names) -> dict[str, Any]:
    today = datetime.now(UTC).date()
    source = sources.get(item.datasource_id)
    daily = [{"date": (today - timedelta(days=29 - i)).isoformat(), "count": runs.get(today - timedelta(days=29 - i), 0)}
             for i in range(30)]
    return {
        "id": str(item.id), "name": item.name, "description": item.description, "sql": item.sql, "kind": script_kind(item.sql),
        "datasource": {"id": str(item.datasource_id), "name": source.name if source else "",
                       "engine": source.engine if source else "postgresql"},
        "shared": item.shared, "mine": item.owner_id == principal.user.id,
        "owner": names.ref(item.owner_id) or {"id": "", "name": ""}, "run_count": sum(runs.values()),
        "last_run_at": iso(item.last_run_at), "daily": daily, "created_at": iso(item.created_at),
        "updated_at": iso(item.updated_at),
    }


async def _views(db: Any, principal: Principal, items: list[SavedQuery]) -> list[dict[str, Any]]:
    sources = await _sources(db, principal.tenant.id)
    runs = await _runs(db, principal.tenant.id, [i.id for i in items])
    names = await Names().load(db, principal.tenant.id)
    return [_view(i, principal, sources, runs.get(i.id, {}), names) for i in items]


def _in(value: Any, actual: str) -> bool:
    return not value or actual in str(value).split(",")


@router.get("/saved-queries", dependencies=[rate_limit("saved-queries", per_minute=120)])
async def list_saved_queries(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        rows = await _views(db, principal, await _visible(db, principal))
    scope = query.get("filter[scope]")
    rows = [r for r in rows if _in(query.get("filter[datasource]"), r["datasource"]["id"])
            and (not scope or any((s == "mine" and r["mine"]) or (s == "shared" and r["shared"]) for s in scope.split(",")))
            and _in(query.get("filter[kind]"), "read" if r["kind"] == "read" else "change")]
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in f"{r['name']} {r['description'] or ''} {r['sql']} {r['datasource']['name']}".lower()]
    sort = query.get("sort") or "-updated_at"
    key = sort.lstrip("-")
    if key in ("name", "updated_at", "run_count", "last_run_at"):
        rows.sort(key=lambda r: _natural(r.get(key) if r.get(key) is not None else ""), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/saved-queries/insights", dependencies=[rate_limit("saved-queries", per_minute=60)])
async def saved_query_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        items = await _visible(db, principal)
        runs = await _runs(db, principal.tenant.id, [i.id for i in items])
    today = datetime.now(UTC).date()
    days = [today - timedelta(days=29 - i) for i in range(30)]
    daily = [{"date": d.isoformat(), "count": sum(r.get(d, 0) for r in runs.values())} for d in days]
    previous = sum(n for r in runs.values() for d, n in r.items() if today - timedelta(days=59) <= d < days[0])
    kinds = [script_kind(i.sql) for i in items]
    return ok({"total": len(items), "mine": sum(1 for i in items if i.owner_id == principal.user.id),
               "shared": sum(1 for i in items if i.shared), "runs_30d": sum(d["count"] for d in daily),
               "previous_30d": previous, "daily": daily,
               "by_kind": {"read": kinds.count("read"), "change": len(kinds) - kinds.count("read")}})


async def _find(db: Any, principal: Principal, saved_id: str) -> SavedQuery:
    try:
        item = await db.get(SavedQuery, uuid.UUID(saved_id))
    except ValueError:
        item = None
    if item is None or item.tenant_id != principal.tenant.id or item.deleted_at is not None or \
            not (item.shared or item.owner_id == principal.user.id):
        raise FrmError("FRM-GEN-1004")
    return item


@router.get("/saved-queries/{saved_id}", dependencies=[rate_limit("saved-queries", per_minute=240)])
async def get_saved_query(saved_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok((await _views(db, principal, [await _find(db, principal, saved_id)]))[0])


@router.post("/saved-queries", status_code=201, dependencies=[rate_limit("saved-queries-write", per_minute=30)])
async def create_saved_query(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = saved_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        try:
            source = await db.get(DataSource, uuid.UUID(data["datasource_id"]))
        except ValueError:
            source = None
        if source is None or source.tenant_id != principal.tenant.id or source.deleted_at is not None:
            raise FrmError("FRM-GEN-1002", [{"field": "datasource_id", "message": "required"}])
        # A saved query may hold a script (several statements); the editor runs one at a time
        if not split_statements(data["sql"]):
            raise FrmError("FRM-GEN-1002", [{"field": "sql", "message": "required"}])
        item = SavedQuery(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, name=data["name"],
                          description=data.get("description") or None, sql=data["sql"].strip(), datasource_id=source.id,
                          shared=bool(data.get("shared")), owner_id=principal.user.id, created_by=principal.user.id,
                          updated_by=principal.user.id)
        db.add(item)
        await db.flush()
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="data.saved_query_saved", actor=Actor.user(principal.user), resource=_resource(source),
                     metadata={"name": item.name, "kind": script_kind(item.sql), "shared": "true" if item.shared else "false"})
        return ok((await _views(db, principal, [item]))[0])


@router.patch("/saved-queries/{saved_id}", dependencies=[rate_limit("saved-queries-write", per_minute=60)])
async def update_saved_query(saved_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        item = await _find(db, principal, saved_id)
        if item.owner_id != principal.user.id:
            raise FrmError("FRM-DEST-1027")
        data = saved_patch_schema.parse(await request.json())
        if data.get("sql") is not None and not split_statements(data["sql"]):
            raise FrmError("FRM-GEN-1002", [{"field": "sql", "message": "required"}])
        if "name" in data:
            item.name = data["name"]
        if "description" in data:
            item.description = data["description"] or None
        if "sql" in data:
            item.sql = data["sql"].strip()
        if "shared" in data:
            item.shared = data["shared"]
        item.updated_at, item.updated_by = datetime.now(UTC), principal.user.id
        source = await db.get(DataSource, item.datasource_id)
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="data.saved_query_saved", actor=Actor.user(principal.user),
                     resource={"type": "data_source", "id": str(item.datasource_id), "name": source.name if source else ""},
                     metadata={"name": item.name, "kind": script_kind(item.sql), "shared": "true" if item.shared else "false"})
        await db.flush()
        return ok((await _views(db, principal, [item]))[0])


@router.delete("/saved-queries/{saved_id}", dependencies=[rate_limit("saved-queries-write", per_minute=60)])
async def delete_saved_query(saved_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        item = await _find(db, principal, saved_id)
        if item.owner_id != principal.user.id:
            raise FrmError("FRM-DEST-1027")
        item.deleted_at, item.deleted_by = datetime.now(UTC), principal.user.id
        source = await db.get(DataSource, item.datasource_id)
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                     action="data.saved_query_deleted", actor=Actor.user(principal.user),
                     resource={"type": "data_source", "id": str(item.datasource_id), "name": source.name if source else ""},
                     metadata={"name": item.name})
    return ok({"deleted": True})


# ── Activity ────────────────────────────────────────────────────────────────────

@router.get("/datasources/activity/insights", dependencies=[rate_limit("data-activity", per_minute=60)])
async def data_activity_insights(principal: Principal = Depends(require_admin)) -> Any:
    from app.modules.audit.models import AuditLog

    now = datetime.now(UTC)
    async with db_session("read", **_scope(principal)) as db:
        found = (await db.execute(select(AuditLog.occurred_at, AuditLog.action, AuditLog.outcome, AuditLog.resource_type,
                                         AuditLog.resource_id, AuditLog.resource_name).where(
            AuditLog.tenant_id == principal.tenant.id, AuditLog.area == "data",
            AuditLog.occurred_at >= now - timedelta(days=60)))).all()
    recent = [r for r in found if now - r.occurred_at < timedelta(days=30)]
    previous = len(found) - len(recent)
    days = [(now - timedelta(days=29 - i)).date() for i in range(30)]
    per_day: dict[date, int] = {}
    for r in recent:
        d = r.occurred_at.astimezone(UTC).date()
        per_day[d] = per_day.get(d, 0) + 1
    connections: dict[str, dict[str, Any]] = {}
    for r in recent:
        if r.resource_type != "data_source" or not r.resource_id:
            continue
        entry = connections.setdefault(r.resource_id, {"id": r.resource_id, "name": r.resource_name or "", "count": 0})
        entry["count"] += 1
    return ok({
        "total_30d": len(recent), "previous_30d": previous, "failed_30d": sum(1 for r in recent if r.outcome != "success"),
        "daily": [{"date": d.isoformat(), "count": per_day.get(d, 0)} for d in days],
        "by_kind": {k: sum(1 for r in recent if kind_of_action(r.action) == k) for k in ACTIVITY_KINDS},
        "by_connection": sorted(connections.values(), key=lambda e: -e["count"]),
    })



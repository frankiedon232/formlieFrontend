"""The database explorer (mock: routes/explorer.ts, explorerSchema.ts; API-CONTRACT → Database explorer). Admins
only, like connections. Everything runs on Formalie's servers through the connection; a connection that isn't
working answers with its error, a disabled one with FRM-DEST-1009.

    GET    /datasources/{id}/explorer/tables      the tree (columns=none: names only; q; up to 500)
    GET    /datasources/{id}/explorer/columns     one table's columns
    GET    /datasources/{id}/explorer/structure   columns, keys, indexes, definition
    GET    /datasources/{id}/explorer/rows        one page of rows (sorted, searched, filtered; count up to 10,000)
    GET    /datasources/{id}/explorer/facets      values of low-variety columns (filters)
    POST · PATCH · DELETE /datasources/{id}/explorer/rows   add, change, delete a row (Full access, their tables)
    POST   /datasources/{id}/explorer/tables      create a table (their own, Full access)
    POST   /datasources/{id}/explorer/changes     a structure change (add / change / delete a column, indexes, rename,
                                                  empty or delete the table)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
from app.modules.data_sources import ddl as D
from app.modules.data_sources import tables as T
from app.modules.data_sources.catalog import run
from app.modules.data_sources.connect import ConnectError, Connection, connect
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.service import count_op, target_of
from app.modules.explorer import service as X

router = APIRouter(tags=["database explorer"])

column_spec = z.obj(
    name=z.string().trim().max(128),
    kind=z.enum(list(D.COLUMN_KINDS)),
    length=z.number().int().min(1).max(8000).nullable().optional(),
    scale=z.number().int().min(0).max(30).nullable().optional(),
    nullable=z.boolean(),
    default=z.string().max(500).nullable().optional(),
    primary=z.boolean().optional(),
    auto=z.boolean().optional(),
)
change_schema = z.union([
    z.obj(op=z.literal("add_column"), column=column_spec),
    z.obj(op=z.literal("alter_column"), column=z.string(), to=column_spec),
    z.obj(op=z.literal("drop_column"), column=z.string()),
    z.obj(op=z.literal("rename_table"), name=z.string().trim().max(128)),
    z.obj(op=z.literal("add_index"), name=z.string().trim().max(128), columns=z.array(z.string()).min(1).max(16), unique=z.boolean()),
    z.obj(op=z.literal("drop_index"), name=z.string()),
    z.obj(op=z.literal("truncate")),
    z.obj(op=z.literal("drop_table")),
])
insert_schema = z.obj(schema=z.string(), table=z.string(), values=z.record(z.string(), z.unknown()))
update_schema = z.obj(schema=z.string(), table=z.string(), key=z.string(), values=z.record(z.string(), z.unknown()))
create_schema = z.obj(schema=z.string(), name=z.string().trim().max(128), columns=z.array(column_spec).min(1).max(200))
changes_schema = z.obj(schema=z.string(), table=z.string(), change=change_schema)


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id, "user_id": principal.user.id}


async def usable(principal: Principal, datasource_id: str) -> DataSource:
    """The connection, if it may be used now (FRM-DEST-1009 when disabled)."""
    try:
        key = uuid.UUID(datasource_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("read", **_scope(principal)) as db:
        source = await db.get(DataSource, key)
    if source is None or source.tenant_id != principal.tenant.id or source.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    if not source.enabled:
        raise FrmError("FRM-DEST-1009")
    return source


@asynccontextmanager
async def opened(principal: Principal, source: DataSource, ops: int = 1) -> AsyncIterator[Connection]:
    """Signed in to the connection with the explorer's time limit; the operation counted afterwards."""
    try:
        async with connect(target_of(source)) as c:
            await c.limit(X.LIMIT_S)
            yield c
    except ConnectError as error:
        raise FrmError(error.code, error.details()) from None
    async with db_session("write", **_scope(principal)) as db:
        await count_op(db, source, ops)


async def _audit(principal: Principal, action: str, source: DataSource, metadata: dict[str, str]) -> None:
    async with db_session("write", **_scope(principal)) as db:
        await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                     actor=Actor.user(principal.user), resource={"type": "data_source", "id": str(source.id), "name": source.name},
                     metadata=metadata)


async def _form_of(principal: Principal, source: DataSource, table: dict[str, Any]) -> tuple[Any, dict[str, str] | None]:
    """The destination (and its form) writing to this response table, if any."""
    if not table["formalie"]:
        return None, None
    from app.modules.destinations.models import ResponseDestination
    from app.modules.forms.models import Form

    async with db_session("read", **_scope(principal)) as db:
        found = (await db.execute(select(ResponseDestination, Form).join(
            Form, (Form.tenant_id == ResponseDestination.tenant_id) & (Form.id == ResponseDestination.form_id)).where(
            ResponseDestination.tenant_id == principal.tenant.id, ResponseDestination.datasource_id == source.id,
            ResponseDestination.table_created.is_(True), ResponseDestination.deleted_at.is_(None),
            ResponseDestination.table_schema == table["schema"], ResponseDestination.table_name == table["name"]))).first()
    return (found[0], {"id": str(found[1].id), "name": found[1].name}) if found else (None, None)


async def _structure(principal: Principal, source: DataSource, c: Connection, schema: Any, name: Any
                     ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tables = await X.tables_of(c, source)
    table = X.find_table(tables, schema, name)
    destination, form = await _form_of(principal, source, table)
    try:
        return tables, await X.structure(c, source, table, destination, form)
    except FrmError:
        raise
    except Exception as error:  # noqa: BLE001
        raise X._failed(error) from None


# ── Reading ─────────────────────────────────────────────────────────────────────

@router.get("/datasources/{datasource_id}/explorer/tables", dependencies=[rate_limit("explorer-tables", per_minute=120)])
async def explorer_tables(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        tables = await X.tables_of(c, source)
    q = (query.get("q") or "").strip().lower()
    found = [t for t in tables if not q or f"{t['schema']}.{t['name']}".lower().find(q) >= 0]
    try:
        size = int(query.get("page_size") or X.TREE_MAX)
    except ValueError:
        size = X.TREE_MAX
    size = min(X.TREE_MAX, max(1, size))
    listed = [{**t, "columns": []} if query.get("columns") == "none" else t for t in found[:size]]
    return ok(listed, {"page": 1, "page_size": size, "total": len(found), "total_pages": max(1, -(-len(found) // size))})


@router.get("/datasources/{datasource_id}/explorer/columns", dependencies=[rate_limit("explorer-columns", per_minute=240)])
async def table_columns(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        table = X.find_table(await X.tables_of(c, source), query.get("schema"), query.get("table"))
    return ok(table["columns"])


@router.get("/datasources/{datasource_id}/explorer/structure", dependencies=[rate_limit("explorer-structure", per_minute=240)])
async def table_structure(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, query.get("schema"), query.get("table"))
    return ok(struct)


@router.get("/datasources/{datasource_id}/explorer/rows", dependencies=[rate_limit("explorer-rows", per_minute=240)])
async def table_rows(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    size = min(100, params.page_size)
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, query.get("schema"), query.get("table"))
        found, total, capped = await X.rows(c, source.engine, struct, query, params.page, size)
    meta = {"page": params.page, "page_size": size, "total": total, "total_pages": max(1, -(-total // size))}
    return ok(found, {**meta, "total_capped": True} if capped else meta)


@router.get("/datasources/{datasource_id}/explorer/facets", dependencies=[rate_limit("explorer-facets", per_minute=120)])
async def table_facets(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, query.get("schema"), query.get("table"))
        found = await X.facets(c, source.engine, struct)
    return ok(found)


# ── Changing rows (Full access, the organisation's own tables only) ─────────────

def _writable(struct: dict[str, Any]) -> None:
    if struct["read_only"]:
        raise FrmError("FRM-DEST-1019", [{"field": "table", "message": struct["read_only"]}])


@router.post("/datasources/{datasource_id}/explorer/rows", status_code=201, dependencies=[rate_limit("explorer-row-write", per_minute=120)])
async def insert_row(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = insert_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, data["schema"], data["table"])
        _writable(struct)
        row = await X.insert_row(c, source.engine, struct, X.typed_row(struct, data["values"], False))
    await _audit(principal, "data.row_inserted", source, {"table": f"{struct['schema']}.{struct['name']}", "key": row["__key"]})
    return ok(row)


@router.patch("/datasources/{datasource_id}/explorer/rows", dependencies=[rate_limit("explorer-row-write", per_minute=120)])
async def update_row(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = update_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, data["schema"], data["table"])
        _writable(struct)
        row = await X.update_row(c, source.engine, struct, data["key"], X.typed_row(struct, data["values"], True))
    await _audit(principal, "data.row_updated", source, {"table": f"{struct['schema']}.{struct['name']}", "key": data["key"]})
    return ok(row)


@router.delete("/datasources/{datasource_id}/explorer/rows", dependencies=[rate_limit("explorer-row-write", per_minute=120)])
async def delete_row(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    source = await usable(principal, datasource_id)
    key = query.get("key") or ""
    async with opened(principal, source) as c:
        _, struct = await _structure(principal, source, c, query.get("schema"), query.get("table"))
        _writable(struct)
        await X.delete_row(c, source.engine, struct, key)
    await _audit(principal, "data.row_deleted", source, {"table": f"{struct['schema']}.{struct['name']}", "key": key})
    return ok({"deleted": True})


# ── Structure (their own tables, Full access; never response tables or views) ──

def _problem(field: str, message: str) -> FrmError:
    return FrmError("FRM-GEN-1002", [{"field": field, "message": message}])


def _check_column(engine: str, spec: dict[str, Any], field: str) -> None:
    name = D.check_name(engine, spec["name"], "column")
    if name:
        raise _problem(f"{field}.name", name)
    if spec.get("auto") and not (spec.get("primary") and spec["kind"] in ("integer", "big_integer")):
        raise _problem(f"{field}.auto", "auto")
    if spec.get("default"):
        parsed = T.parse_value({"type": D.type_for(engine, spec), "nullable": True, "has_default": False}, spec["default"])
        if "problem" in parsed:
            raise _problem(f"{field}.default", parsed["problem"])


async def _apply(c: Connection, statements: list[str]) -> None:
    for statement in statements:
        await run(c, statement if statement.endswith(";") else f"{statement};")


@router.post("/datasources/{datasource_id}/explorer/tables", status_code=201, dependencies=[rate_limit("explorer-schema", per_minute=30)])
async def create_table(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    source = await usable(principal, datasource_id)
    if source.access.get("other") != "read_write":
        raise FrmError("FRM-DEST-1019", [{"field": "table", "message": "read_access"}])
    data = create_schema.parse(await request.json())
    engine = source.engine
    async with opened(principal, source) as c:
        tables = await X.tables_of(c, source)
        schemas = list(dict.fromkeys([*(t["schema"] for t in tables if not t["formalie"]), *(source.access.get("schemas") or []),
                                      X.own_schema(source)]))
        if data["schema"] not in schemas:
            raise _problem("schema", "schema")
        problem = D.check_name(engine, data["name"], "table")
        if problem:
            raise _problem("name", problem)
        if any(t["schema"] == data["schema"] and t["name"].lower() == data["name"].lower() for t in tables):
            raise FrmError("FRM-DEST-1022", [{"field": "name", "message": "taken"}])
        seen: set[str] = set()
        for index, spec in enumerate(data["columns"]):
            _check_column(engine, spec, f"columns.{index}")
            if spec["name"].lower() in seen:
                raise _problem(f"columns.{index}.name", "taken")
            seen.add(spec["name"].lower())
        statements = D.create_table_statements(engine, data["schema"], data["name"], data["columns"])
        await _apply(c, statements)
    key = f"{data['schema']}.{data['name']}"
    await _audit(principal, "data.user_table_created", source, {"table": key, "columns": str(len(data["columns"]))})
    return ok({"statements": statements, "table": {"schema": data["schema"], "name": data["name"]}})


@router.post("/datasources/{datasource_id}/explorer/changes", dependencies=[rate_limit("explorer-schema", per_minute=30)])
async def change_table(datasource_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = changes_schema.parse(await request.json())
    source = await usable(principal, datasource_id)
    engine = source.engine
    step = data["change"]
    op = step["op"]
    result: dict[str, str] | None = None
    async with opened(principal, source) as c:
        tables, struct = await _structure(principal, source, c, data["schema"], data["table"])
        if not struct["alterable"]:
            raise FrmError("FRM-DEST-1019", [{"field": "table", "message": "response_table" if struct["formalie"] else "read_access"}])
        columns = {col["name"]: col for col in struct["columns"]}

        def taken(name: str, but: str | None = None) -> bool:
            return any(n.lower() == name.lower() and n != but for n in columns)
        result = {"schema": struct["schema"], "name": struct["name"]}
        if op == "add_column":
            spec = {**step["column"], "primary": False, "auto": False}
            _check_column(engine, spec, "column")
            if taken(spec["name"]):
                raise FrmError("FRM-DEST-1022", [{"field": "column.name", "message": "taken"}])
            if not spec["nullable"] and not spec.get("default") and (struct["rows_estimate"] or 0) > 0:
                raise _problem("column.default", "needs_default")
            statements = D.change_statements(engine, struct["schema"], struct["name"], {**step, "column": spec})
        elif op == "alter_column":
            column = columns.get(step["column"])
            if column is None:
                raise FrmError("FRM-GEN-1004")
            _check_column(engine, {**step["to"], "primary": column["primary"], "auto": False}, "to")
            if taken(step["to"]["name"], column["name"]):
                raise FrmError("FRM-DEST-1022", [{"field": "to.name", "message": "taken"}])
            if column["primary"] and (D.type_for(engine, step["to"]).upper() != column["type"].upper() or step["to"].get("default")):
                raise _problem("to.kind", "key_column")
            current = {"name": column["name"], "type": column["type"], "nullable": column["nullable"],
                       "default": None if column["primary"] else column["default"], "primary": column["primary"]}
            statements = D.change_statements(engine, struct["schema"], struct["name"], step, current)
        elif op == "drop_column":
            column = columns.get(step["column"])
            if column is None:
                raise FrmError("FRM-GEN-1004")
            if column["primary"]:
                raise _problem("column", "key_column")
            if len(columns) == 1:
                raise _problem("column", "last_column")
            statements = D.change_statements(engine, struct["schema"], struct["name"], step)
        elif op == "rename_table":
            problem = D.check_name(engine, step["name"], "table")
            if problem:
                raise _problem("name", problem)
            if any(t["schema"] == struct["schema"] and t["name"].lower() == step["name"].lower() for t in tables):
                raise FrmError("FRM-DEST-1022", [{"field": "name", "message": "taken"}])
            statements = D.change_statements(engine, struct["schema"], struct["name"], step)
            result = {"schema": struct["schema"], "name": step["name"]}
        elif op == "add_index":
            problem = D.check_name(engine, step["name"], "index")
            if problem:
                raise _problem("name", problem)
            if any(i["name"].lower() == step["name"].lower() for i in struct["indexes"]):
                raise FrmError("FRM-DEST-1022", [{"field": "name", "message": "taken"}])
            if any(n not in columns for n in step["columns"]):
                raise _problem("columns", "columns")
            statements = D.change_statements(engine, struct["schema"], struct["name"], step)
        elif op == "drop_index":
            index = next((i for i in struct["indexes"] if i["name"] == step["name"]), None)
            if index is None:
                raise FrmError("FRM-GEN-1004")
            if index["primary"]:
                raise _problem("name", "key_index")
            statements = D.change_statements(engine, struct["schema"], struct["name"], step)
        else:
            statements = D.change_statements(engine, struct["schema"], struct["name"], step)
            if op == "drop_table":
                result = None
        await _apply(c, statements)
    key = f"{struct['schema']}.{struct['name']}"
    action = "data.table_truncated" if op == "truncate" else "data.table_dropped" if op == "drop_table" else "data.table_altered"
    extra: dict[str, str] = {}
    if action == "data.table_altered":
        extra = {"change": op, **({"column": step["column"]} if isinstance(step.get("column"), str) else {}),
                 **({"name": step["name"]} if op == "rename_table" else {})}
    await _audit(principal, action, source, {"table": key, **extra})
    return ok({"statements": statements, "table": result})

"""Response storage (mock: routes/destinations.ts; API-CONTRACT → Response storage). Admins only, like connections.

    GET    /forms/{id}/storage                   where the form's responses are kept + its fields
    GET    /datasources/{id}/tables              tables Formalie may see on a connection (read from it)
    GET    /destinations                         every form that stores in a database
    GET    /destinations/insights                the two chart cards
    POST   /destinations                         set up (creates the table, or maps an existing one)
    GET    /destinations/{id}                    detail (columns, new fields, backfill)
    PATCH  /destinations/{id}                    settings, columns, pause / resume
    POST   /destinations/{id}/columns            add columns for fields added to the form (ALTER TABLE … ADD)
    GET    /destinations/{id}/deliveries         every response with its delivery (status filter)
    POST   /destinations/{id}/retry              retry failed deliveries (all, or some)
    POST   /destinations/{id}/backfill           send earlier responses (date range) with progress
    DELETE /destinations/{id}                    back to Formalie's storage (the table stays)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import after_commit, db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin, require_auth
from app.modules.data_sources import tables as T
from app.modules.data_sources.catalog import WriteError, list_tables, run
from app.modules.data_sources.connect import ConnectError, connect
from app.modules.data_sources.engines import tables_schema_of
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.service import count_op, target_of
from app.modules.destinations import service, tasks
from app.modules.destinations.models import DestinationBackfill, DestinationDelivery, ResponseDestination
from app.modules.forms.access import can_see, viewer_for
from app.modules.forms.models import Form
from app.modules.forms.router import _natural
from app.modules.forms.service import Names
from app.modules.responses.models import Response

router = APIRouter(tags=["response storage"])

META = list(T.META_COLUMNS)
column_schema = z.obj(
    column=z.string().trim().min(1).max(128),
    type=z.string().trim().min(1).max(64),
    source=z.union([z.obj(kind=z.literal("field"), key=z.string().min(1).max(128)),
                    z.obj(kind=z.literal("meta"), key=z.enum(META)), z.literal(None)]),
    nullable=z.boolean(),
    existing=z.boolean(),
)
settings_schema = z.obj(
    write_mode=z.enum(["insert", "upsert"]),
    key_column=z.string().trim().min(1).max(128),
    multi_value=z.enum(["json", "text"]),
    choices=z.enum(["value", "label"]),
)
create_schema = z.obj(
    form_id=z.string().min(1),
    datasource_id=z.string().min(1),
    table=z.obj(mode=z.enum(["create", "existing"]), schema=z.string().trim().max(128), name=z.string().trim().min(1).max(128)),
    columns=z.array(column_schema).min(1).max(500),
    settings=settings_schema,
)
patch_schema = z.obj(paused=z.boolean().optional(), settings=settings_schema.optional(),
                     columns=z.array(column_schema).max(500).optional())
columns_schema = z.obj(keys=z.array(z.string().min(1)).min(1).max(200))
retry_schema = z.obj(response_ids=z.array(z.string()).max(5000).optional())
backfill_schema = z.obj({"from": z.string().regex(r"^\d{4}-\d{2}-\d{2}$"), "to": z.string().regex(r"^\d{4}-\d{2}-\d{2}$")})


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _uuid(value: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def _form(db: Any, principal: Principal, form_id: str | None) -> Form:
    form = await db.get(Form, _uuid(form_id)) if _uuid(form_id) else None
    if form is None or form.tenant_id != principal.tenant.id or form.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return form


async def _source(db: Any, principal: Principal, datasource_id: str | None) -> DataSource:
    source = await db.get(DataSource, _uuid(datasource_id)) if _uuid(datasource_id) else None
    if source is None or source.tenant_id != principal.tenant.id or source.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return source


async def _find(db: Any, principal: Principal, destination_id: str) -> ResponseDestination:
    found = await db.get(ResponseDestination, _uuid(destination_id)) if _uuid(destination_id) else None
    if found is None or found.tenant_id != principal.tenant.id or found.deleted_at is not None:
        raise FrmError("FRM-GEN-1004")
    return found


def _resource(destination: ResponseDestination, form: Form | None) -> dict[str, Any]:
    return {"type": "destination", "id": str(destination.id),
            "name": f"{form.name if form else ''} → {destination.table_name}"}


async def _audit(db: Any, principal: Principal, action: str, resource: dict[str, Any],
                 metadata: dict[str, str] | None = None) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(principal.user), resource=resource, metadata=metadata or {})


def _check_columns(columns: list[dict[str, Any]], fields: list[dict[str, Any]], settings: dict[str, Any]) -> None:
    problems = T.blocking(T.check_mapping(columns, fields, settings))
    if problems:
        raise FrmError("FRM-DEST-1016", [{"field": p["column"] or "response_id", "message": p["code"]} for p in problems])


def _failed(error: ConnectError | WriteError) -> FrmError:
    return FrmError(error.code)


async def _detail(db: Any, principal: Principal, destination: ResponseDestination) -> dict[str, Any]:
    return await service.detail_of(db, destination, await Names().load(db, principal.tenant.id))


def _in(value: Any, actual: str) -> bool:
    return not isinstance(value, str) or not value or actual in value.split(",")


# ── A form's storage, a connection's tables ─────────────────────────────────────

@router.get("/forms/{form_id}/storage", dependencies=[rate_limit("form-storage", per_minute=240)])
async def form_storage(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        form = await _form(db, principal, form_id)
        if not can_see(form, await viewer_for(db, principal)):
            raise FrmError("FRM-GEN-1004")
        destination = await service.destination_of_form(db, principal.tenant.id, form.id)
        row = None
        if destination is not None:
            facts = await service.Facts().load(db, principal.tenant.id, [destination])
            row = service.row_of(destination, facts, await Names().load(db, principal.tenant.id))
        connections = sum(1 for s in (await db.execute(select(DataSource).where(
            DataSource.tenant_id == principal.tenant.id, DataSource.deleted_at.is_(None)))).scalars() if s.enabled)
        fields = await service.fields_of(db, form)
    return ok({
        "mode": "database" if destination else "formalie", "destination": row, "connections": connections,
        "fields": [{"key": f["key"], "label": f["key"] if f.get("label") is None else f["label"], "type": f["type"],
                    **({"options": [{"value": o.get("value"), "label": o.get("label")} for o in f["options"]]}
                       if f.get("options") is not None else {})} for f in fields],
        "can_manage": bool(principal.grants.get("data.storage")),
    })


@router.get("/datasources/{datasource_id}/tables", dependencies=[rate_limit("datasources-tables", per_minute=60)])
async def connection_tables(datasource_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        source = await _source(db, principal, datasource_id)
        target, engine, settings, access = target_of(source), source.engine, source.settings, source.access
    try:
        async with connect(target) as c:
            tables = await list_tables(c, engine, settings, access)
    except ConnectError as error:
        raise _failed(error) from None
    async with db_session("write", **_scope(principal)) as db:
        await count_op(db, source)
    return ok(tables)


# ── List, insights ──────────────────────────────────────────────────────────────

async def _rows(db: Any, principal: Principal) -> tuple[list[dict[str, Any]], service.Facts]:
    destinations = await service.destinations_of(db, principal.tenant.id)
    facts = await service.Facts().load(db, principal.tenant.id, destinations)
    names = await Names().load(db, principal.tenant.id)
    rows = [service.row_of(d, facts, names) for d in destinations]
    return [r for r in rows if r is not None], facts


@router.get("/destinations", dependencies=[rate_limit("destinations-list", per_minute=120)])
async def list_destinations(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        rows, _ = await _rows(db, principal)
    rows = [{**r, "form_name": r["form"]["name"]} for r in rows
            if _in(query.get("filter[status]"), r["status"]) and _in(query.get("filter[datasource]"), r["datasource"]["id"])
            and _in(query.get("filter[table]"), "created" if r["table"]["created"] else "existing")]
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if any(q in t.lower() for t in (r["form"]["name"], r["datasource"]["name"], r["table"]["name"]))]
    sort = query.get("sort") or "form_name"
    rows.sort(key=lambda r: _natural(r.get(sort.lstrip("-"))), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/destinations/insights", dependencies=[rate_limit("destinations-insights", per_minute=60)])
async def destination_insights(principal: Principal = Depends(require_admin)) -> Any:
    from sqlalchemy import func

    async with db_session("read", **_scope(principal)) as db:
        rows, facts = await _rows(db, principal)
        live = [_uuid(r["id"]) for r in rows]
        since = service.now() - 30 * service.DAY
        counts = {"sent": 0, "pending": 0, "failed": 0, "held": 0}
        for status, n in (await db.execute(select(DestinationDelivery.status, func.count()).where(
                DestinationDelivery.tenant_id == principal.tenant.id, DestinationDelivery.destination_id.in_(live),
                DestinationDelivery.response_submitted_at >= since).group_by(DestinationDelivery.status))).all():
            counts[status] = n
    daily = [{"date": d["date"], "count": sum(r["daily"][i]["count"] for r in rows)} for i, d in enumerate(rows[0]["daily"])] \
        if rows else []
    previous = sum(d["count"] for i in live for d in service.daily_of(facts, i, 30))
    return ok({
        "total": len(rows),
        "by_status": {s: sum(1 for r in rows if r["status"] == s) for s in ("active", "paused", "failing")},
        "sent_30d": sum(r["sent_30d"] for r in rows), "previous_30d": previous, "daily": daily, "deliveries": counts,
    })


# ── Set up, read, change, remove ────────────────────────────────────────────────

@router.post("/destinations", status_code=201, dependencies=[rate_limit("destinations-create", per_minute=20)])
async def create_destination(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = create_schema.parse(await request.json())
    async with db_session("read", **_scope(principal)) as db:
        form = await _form(db, principal, data["form_id"])
        if await service.destination_of_form(db, principal.tenant.id, form.id):
            raise FrmError("FRM-DEST-1015")
        source = await _source(db, principal, data["datasource_id"])
        if not source.enabled:
            raise FrmError("FRM-DEST-1009")
        fields = await service.fields_of(db, form)
        target = target_of(source)
    engine, settings = source.engine, data["settings"]
    try:
        async with connect(target) as c:
            tables = await list_tables(c, engine, source.settings, source.access)
            if data["table"]["mode"] == "existing":
                if source.access.get("other") != "read_write":
                    raise FrmError("FRM-DEST-1013")
                found = next((t for t in tables if t["schema"] == data["table"]["schema"] and t["name"] == data["table"]["name"]
                              and not t["formalie"]), None)
                if found is None:
                    raise FrmError("FRM-GEN-1004")
                table = {"schema": found["schema"], "name": found["name"], "created": False}
            else:
                schema = tables_schema_of(engine, source.settings, source.access)
                prefix = source.access.get("table_prefix") or "formalie_"
                prefix = prefix.upper() if engine == "oracle" else prefix
                name = data["table"]["name"].strip()
                problem = T.check_table_rest(engine, prefix, name[len(prefix):]) if name.startswith(prefix) else "required"
                if problem:
                    raise FrmError("FRM-GEN-1002", [{"field": "table", "message": problem}])
                if any(t["schema"] == schema and t["name"].lower() == name.lower() for t in tables):
                    raise FrmError("FRM-DEST-1014", [{"field": "table", "message": "taken"}])
                table = {"schema": schema, "name": name, "created": True}
            # Tables Formalie creates get their types from the engine and always follow its standard.
            columns = T.typed_for_engine(engine, data["columns"], fields, settings["multi_value"]) if table["created"] \
                else data["columns"]
            if table["created"]:
                settings = T.standard_settings(settings, columns)
            _check_columns(columns, fields, settings)
            if table["created"]:
                await run(c, T.create_table_sql(engine, table["schema"], table["name"], columns))
    except (ConnectError, WriteError) as error:
        raise _failed(error) from None
    async with db_session("write", **_scope(principal)) as db:
        now = service.now()
        destination = ResponseDestination(
            id=uuid.uuid4(), tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
            form_id=form.id, datasource_id=source.id, table_schema=table["schema"], table_name=table["name"],
            table_created=table["created"], columns=columns, settings=settings, covers_from=now, created_by=principal.user.id,
            updated_by=principal.user.id)
        db.add(destination)
        await db.flush()
        await count_op(db, source)
        where = f"{table['schema']}.{table['name']}"
        if table["created"]:
            await _audit(db, principal, "data.table_created", {"type": "data_source", "id": str(source.id), "name": source.name},
                         {"table": where, "columns": str(len(columns))})
        await _audit(db, principal, "data.destination_created", _resource(destination, form),
                     {"connection": source.name, "table": where, "mode": "created" if table["created"] else "existing"})
        return ok(await _detail(db, principal, destination))


@router.get("/destinations/{destination_id}", dependencies=[rate_limit("destinations-get", per_minute=240)])
async def get_destination(destination_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await _detail(db, principal, await _find(db, principal, destination_id)))


@router.patch("/destinations/{destination_id}", dependencies=[rate_limit("destinations-update", per_minute=60)])
async def patch_destination(destination_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = patch_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await _form(db, principal, str(destination.form_id))
        if "paused" in data and data["paused"] != (destination.paused_at is not None):
            if data["paused"]:
                destination.paused_at = service.now()
            else:
                # Held responses go out now.
                held = (await db.execute(select(DestinationDelivery).where(
                    DestinationDelivery.tenant_id == principal.tenant.id, DestinationDelivery.destination_id == destination.id,
                    DestinationDelivery.status == "held"))).scalars()
                for d in held:
                    d.status, d.attempts, d.next_attempt_at, d.error_code = "pending", 0, service.now() + service.LEASE, None
                    service.queue(db, d)
                destination.paused_at = None
            await _audit(db, principal, "data.destination_paused" if data["paused"] else "data.destination_resumed",
                         _resource(destination, form))
        if data.get("settings") or data.get("columns") is not None:
            source = await db.get(DataSource, destination.datasource_id)
            fields = await service.fields_of(db, form)
            given = data["columns"] if data.get("columns") is not None else destination.columns
            columns = T.typed_for_engine(source.engine, given, fields, destination.settings["multi_value"]) \
                if destination.table_created and source else given
            asked = data.get("settings") or destination.settings
            # How several values and choices are written is set when the table is set up.
            kept = {**asked, "multi_value": destination.settings["multi_value"], "choices": destination.settings["choices"]}
            settings = T.standard_settings(kept, columns) if destination.table_created else kept
            _check_columns(columns, fields, settings)
            destination.settings, destination.columns = settings, columns
            await _audit(db, principal, "data.destination_updated", _resource(destination, form))
        destination.updated_at, destination.updated_by = service.now(), principal.user.id
        await db.flush()
        return ok(await _detail(db, principal, destination))


@router.post("/destinations/{destination_id}/columns", dependencies=[rate_limit("destinations-columns", per_minute=30)])
async def add_columns(destination_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    keys = columns_schema.parse(await request.json())["keys"]
    async with db_session("read", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await _form(db, principal, str(destination.form_id))
        source = await _source(db, principal, str(destination.datasource_id))
        # Adding a column to a table of theirs needs Full access; Formalie's own tables always allow it.
        if not destination.table_created and source.access.get("other") != "read_write":
            raise FrmError("FRM-DEST-1013")
        fields = await service.fields_of(db, form)
        target = target_of(source)
    taken = {c["column"].lower() for c in destination.columns}
    mapped = {c["source"]["key"] for c in destination.columns if c.get("source") and c["source"]["kind"] == "field"}
    added = [{"column": T.column_name_for(source.engine, f["key"], taken),
              "type": T.column_type_for(source.engine, f, destination.settings["multi_value"]),
              "source": {"kind": "field", "key": f["key"]}, "nullable": True, "existing": False}
             for f in fields if f["key"] in keys and f["key"] not in mapped]
    if added:
        try:
            async with connect(target) as c:
                for column in added:
                    await run(c, T.add_column_sql(source.engine, destination.table_schema, destination.table_name, column))
        except (ConnectError, WriteError) as error:
            raise _failed(error) from None
    async with db_session("write", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        destination.columns = [*destination.columns, *added]
        destination.updated_at, destination.updated_by = service.now(), principal.user.id
        if added:
            await count_op(db, source, len(added))
            await _audit(db, principal, "data.column_added", _resource(destination, form),
                         {"columns": ", ".join(c["column"] for c in added)})
        await db.flush()
        return ok(await _detail(db, principal, destination))


@router.delete("/destinations/{destination_id}", dependencies=[rate_limit("destinations-delete", per_minute=20)])
async def remove_destination(destination_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await db.get(Form, destination.form_id)
        await _audit(db, principal, "data.destination_removed", _resource(destination, form),
                     {"table": f"{destination.table_schema}.{destination.table_name}"})
        destination.deleted_at, destination.deleted_by = datetime.now(UTC), principal.user.id
        await service.stop_deliveries(db, destination)
    return ok({"removed": True})


# ── Deliveries, retries, backfill ───────────────────────────────────────────────

@router.get("/destinations/{destination_id}/deliveries", dependencies=[rate_limit("destinations-deliveries", per_minute=240)])
async def list_deliveries(destination_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await _form(db, principal, str(destination.form_id))
        rows = await service.deliveries_of(db, destination, form)
    rows = [r for r in rows if _in(query.get("filter[status]"), r["status"])]
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q.replace("#", "") in str(r["number"]) or q in (r["respondent"] or "").lower()]
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.post("/destinations/{destination_id}/retry", dependencies=[rate_limit("destinations-retry", per_minute=20)])
async def retry_deliveries(destination_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    data = retry_schema.parse(await request.json())
    only = {i for i in (_uuid(r) for r in data.get("response_ids") or []) if i}
    async with db_session("write", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await db.get(Form, destination.form_id)
        failed = [d for d in (await db.execute(select(DestinationDelivery).where(
            DestinationDelivery.tenant_id == principal.tenant.id, DestinationDelivery.destination_id == destination.id,
            DestinationDelivery.status == "failed"))).scalars() if not only or d.response_id in only]
        for d in failed:
            d.status, d.next_attempt_at, d.updated_at = "pending", service.now() + service.LEASE, service.now()
            service.queue(db, d)
        await _audit(db, principal, "data.deliveries_retried", _resource(destination, form), {"count": str(len(failed))})
    return ok({"retried": len(failed)})


@router.post("/destinations/{destination_id}/backfill", status_code=201, dependencies=[rate_limit("destinations-backfill", per_minute=10)])
async def start_backfill(destination_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    from sqlalchemy import func

    data = backfill_schema.parse(await request.json())
    try:
        start = datetime.fromisoformat(f"{data['from']}T00:00:00+00:00")
        end = datetime.fromisoformat(f"{data['to']}T23:59:59+00:00")
    except ValueError:
        raise FrmError("FRM-GEN-1002", [{"field": "from", "message": "date"}]) from None
    async with db_session("write", **_scope(principal)) as db:
        destination = await _find(db, principal, destination_id)
        form = await _form(db, principal, str(destination.form_id))
        current = await service.latest_backfill(db, destination)
        if current is not None and current.status == "running":
            raise FrmError("FRM-DEST-1017")
        end = min(end, destination.covers_from)
        total = (await db.execute(select(func.count()).select_from(Response).where(
            Response.tenant_id == principal.tenant.id, Response.form_id == form.id, Response.deleted_at.is_(None),
            Response.submitted_at >= start, Response.submitted_at <= end,
            ~select(DestinationDelivery.id).where(
                DestinationDelivery.tenant_id == principal.tenant.id, DestinationDelivery.destination_id == destination.id,
                DestinationDelivery.response_id == Response.id).exists()))).scalar_one()
        job = DestinationBackfill(id=uuid.uuid4(), tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                  destination_id=destination.id, range_from=start, range_to=end, total=int(total), done=0,
                                  status="running", started_at=service.now(), created_by=principal.user.id)
        db.add(job)
        await db.flush()
        await _audit(db, principal, "data.backfill_started", _resource(destination, form),
                     {"from": data["from"], "to": data["to"], "count": str(total)})
        tenant_id, organisation_id, job_id = principal.tenant.id, principal.tenant.organisation_id, job.id
        subdomain = principal.tenant.subdomain
        after_commit(db, lambda: tasks.dispatch_backfill(tenant_id, organisation_id, job_id, subdomain))
        return ok(await _detail(db, principal, destination))

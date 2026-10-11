"""Reading the audit trail (mock: routes/audit.ts): filters, search, the AuditEvent shape, and the export file.

Filters (API-CONTRACT → Audit trail): `filter[area|action|outcome|actor_id|country|resource_type|resource_id]`,
comma = any of; `from` / `to` are days (UTC) on `occurred_at`; `q` searches person, email, item, IP, city, request id
and action. RLS keeps every query to the signed-in workspace; the queries also say so (defence in depth).
"""

from __future__ import annotations

import io
import math
import uuid
from datetime import UTC, datetime, time
from typing import Any

import xlsxwriter
from sqlalchemy import ColumnElement, String, and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog

FILTER_COLUMNS = {
    "area": AuditLog.area,
    "action": AuditLog.action,
    "outcome": AuditLog.outcome,
    "actor_id": AuditLog.actor_id,
    "country": AuditLog.country,
    "resource_type": AuditLog.resource_type,
    "resource_id": AuditLog.resource_id,
}
SORTS = {"occurred_at": AuditLog.occurred_at, "action": AuditLog.action, "outcome": AuditLog.outcome,
         "severity": AuditLog.severity, "area": AuditLog.area}


def _values(query: dict[str, Any], key: str) -> list[str] | None:
    value = query.get(f"filter[{key}]")
    if not isinstance(value, str) or not value:
        return None
    return [v for v in value.split(",") if v] or None


def _day(value: Any, end: bool) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        day = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(day, time(23, 59, 59) if end else time(0, 0, 0), tzinfo=UTC)


def _uuid_list(values: list[str]) -> list[uuid.UUID]:
    out = []
    for value in values:
        try:
            out.append(uuid.UUID(value))
        except ValueError:
            continue  # not an id: matches nothing
    return out


def conditions(tenant_id: uuid.UUID, query: dict[str, Any]) -> list[ColumnElement[bool]]:
    """filterEvents() and the search, as SQL."""
    where: list[ColumnElement[bool]] = [AuditLog.tenant_id == tenant_id]
    for key, column in FILTER_COLUMNS.items():
        values = _values(query, key)
        if values is None:
            continue
        if key == "actor_id":
            where.append(column.in_(_uuid_list(values)))
        elif key == "country":
            # an event without a country matches the empty value, as in the mock
            where.append(func.coalesce(column, "").in_(values))
        else:
            where.append(column.in_(values))
    start, end = _day(query.get("from"), False), _day(query.get("to"), True)
    if start is not None:
        where.append(AuditLog.occurred_at >= start)
    if end is not None:
        where.append(AuditLog.occurred_at <= end)
    q = query.get("q")
    if isinstance(q, str) and q.strip():
        pattern = "%" + q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        fields = (AuditLog.actor_name, AuditLog.actor_email, AuditLog.resource_name, func.host(AuditLog.ip),
                  AuditLog.city, AuditLog.request_id, AuditLog.action)
        where.append(or_(*(func.lower(cast(f, String)).like(pattern, escape="\\") for f in fields)))
    return where


def _order(sort: Any) -> list[Any]:
    key = sort if isinstance(sort, str) and sort else "-occurred_at"
    descending = key.startswith("-")
    column = SORTS.get(key.lstrip("-"), AuditLog.occurred_at)
    return [column.desc() if descending else column.asc(), AuditLog.id.desc() if descending else AuditLog.id.asc()]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def view(row: AuditLog, organisation: dict[str, Any] | None) -> dict[str, Any]:
    """AuditEvent (shared/types/audit.ts)."""
    # Formalie staff acting through the platform admin show as Formalie, under the staff member's name
    support = row.actor_type == "platform_support"
    actor_type = "system" if support else row.actor_type
    name = (row.staff_name if support else None) or row.actor_name or ""
    return {
        "id": str(row.id),
        "occurred_at": _iso(row.occurred_at),
        "action": row.action,
        "area": row.area,
        "outcome": row.outcome,
        "severity": row.severity,
        "actor": {"type": actor_type, "id": str(row.actor_id) if row.actor_id else None,
                  "name": name,
                  "email": row.actor_email},
        "resource": ({"type": row.resource_type, "id": row.resource_id, "name": row.resource_name}
                     if row.resource_type else None),
        "organisation": organisation,
        "location": {"ip": str(row.ip) if row.ip else "unknown", "city": row.city, "country": row.country},
        "device": row.device or {"type": "unknown", "browser": None, "os": None},
        "changes": row.changes or [],
        "metadata": row.metadata_ or {},
        "reason": row.reason,
        "request_id": row.request_id or "",
    }


async def page(db: AsyncSession, tenant_id: uuid.UUID, query: dict[str, Any], *, offset: int,
               limit: int) -> tuple[list[AuditLog], int]:
    where = conditions(tenant_id, query)
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(and_(*where)))).scalar_one()
    rows = (await db.execute(select(AuditLog).where(and_(*where)).order_by(*_order(query.get("sort")))
                             .offset(offset).limit(limit))).scalars().all()
    return list(rows), int(total)


async def one(db: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> AuditLog | None:
    return (await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id,
                                                    AuditLog.id == entry_id))).scalar_one_or_none()


async def count(db: AsyncSession, tenant_id: uuid.UUID, query: dict[str, Any]) -> int:
    where = conditions(tenant_id, query)
    return int((await db.execute(select(func.count()).select_from(AuditLog).where(and_(*where)))).scalar_one())


async def all_rows(db: AsyncSession, tenant_id: uuid.UUID, query: dict[str, Any], limit: int) -> list[AuditLog]:
    """For the export: newest first, like the mock's list."""
    where = conditions(tenant_id, query)
    return list((await db.execute(select(AuditLog).where(and_(*where))
                                  .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc()).limit(limit))).scalars())


async def facets(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """People and countries that appear in the trail (each person under their latest name)."""
    latest_name = aggregate_order_by(AuditLog.actor_name, AuditLog.occurred_at.desc())
    actors = (await db.execute(
        select(AuditLog.actor_id, func.array_agg(latest_name)[1])
        .where(AuditLog.tenant_id == tenant_id, AuditLog.actor_id.is_not(None))
        .group_by(AuditLog.actor_id))).all()
    countries = (await db.execute(select(AuditLog.country).where(AuditLog.tenant_id == tenant_id,
                                                                 AuditLog.country.is_not(None)).distinct())).scalars()
    people = sorted(({"id": str(a), "name": n or ""} for a, n in actors), key=lambda p: p["name"].casefold())
    return {"actors": people, "countries": sorted(c for c in countries if c)}


# ── Export file (same columns and cells as the mock's auditRows / toCsv / xlsx) ──

HEADER = ["Time (UTC)", "Action", "Outcome", "Person", "Email", "Item type", "Item", "Changes", "IP address", "City",
          "Country", "Device", "Reason", "Request ID"]


def js_string(value: Any) -> str:
    """String(value) as JavaScript writes it (true / false, 2 not 2.0)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


def _change(change: dict[str, Any]) -> str:
    before, after = change.get("before"), change.get("after")
    return (f"{change.get('field')}: {'-' if before is None else js_string(before)} → "
            f"{'-' if after is None else js_string(after)}")


def rows_of(events: list[dict[str, Any]]) -> list[list[str]]:
    out = [HEADER]
    for e in events:
        resource = e["resource"] or {}
        device = " / ".join(v for v in (e["device"].get("browser"), e["device"].get("os")) if v)
        out.append([js_string(v) for v in (
            e["occurred_at"], e["action"], e["outcome"], e["actor"]["name"], e["actor"]["email"], resource.get("type"),
            resource.get("name"), "; ".join(_change(c) for c in e["changes"]), e["location"]["ip"],
            e["location"]["city"], e["location"]["country"], device, e["reason"], e["request_id"])])
    return out


def csv_cell(text: str) -> str:
    """Leading = + - @ tab or CR would run as a formula in spreadsheet apps (CSV injection)."""
    safe = f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
    return f'"{safe.replace(chr(34), chr(34) * 2)}"' if any(ch in safe for ch in '",\n\r') else safe


def to_csv(rows: list[list[str]]) -> bytes:
    # Byte-order mark so spreadsheet apps open UTF-8 correctly
    return ("﻿" + "\r\n".join(",".join(csv_cell(c) for c in row) for row in rows) + "\r\n").encode("utf-8")


def to_xlsx(rows: list[list[str]], sheet: str = "Audit trail") -> bytes:
    buffer = io.BytesIO()
    book = xlsxwriter.Workbook(buffer, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    ws = book.add_worksheet(sheet)
    bold = book.add_format({"bold": True})
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            ws.write_string(r, c, cell, bold if r == 0 else None)  # always text, never a formula
    ws.freeze_panes(1, 0)
    book.close()
    return buffer.getvalue()


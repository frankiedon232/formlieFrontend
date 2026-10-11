"""Running one statement from the Query editor on a customer's database (API-CONTRACT → Query editor).

- `:name` parameters are bound by the database (never pasted into the SQL); on PostgreSQL the statement is prepared
  first so each value is typed the way the database expects it.
- Reading runs in a read-only transaction where the engine has one, and fetches at most `cap` rows.
- Changing runs for real only once confirmed; before that, a dry run inside a transaction that is rolled back
  tells how many rows it would touch.
- Problems come back with the database's own words and the character offset it points at.
"""

from __future__ import annotations

import asyncio
import re
import time as clock
import uuid
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core import js
from app.modules.data_sources.catalog import TIMED_OUT
from app.modules.data_sources.connect import Connection
from app.modules.data_sources.sql import parameter_spans


class RunError(Exception):
    """FRM-DEST-1025 (the database refused it: `message`, `position`) or FRM-DEST-1011 (over the time limit)."""

    def __init__(self, code: str, message: str = "", position: int = 0) -> None:
        super().__init__(message or code)
        self.code, self.message, self.position = code, message, position


def _problem(error: Exception, sql: str) -> RunError:
    text = str(error)
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)) or any(w in text.lower() for w in TIMED_OUT):
        return RunError("FRM-DEST-1011", text[:500])
    position = 0
    raw = getattr(error, "position", None)
    if raw:
        try:
            position = max(0, int(raw) - 1)
        except (TypeError, ValueError):
            position = 0
    else:
        line = re.search(r"at line (\d+)", text)
        if line:
            lines = sql.split("\n")
            position = sum(len(row) + 1 for row in lines[:max(0, int(line.group(1)) - 1)])
    return RunError("FRM-DEST-1025", text.strip()[:500] or "error", position)


def bind(engine: str, sql: str, params: dict[str, str]) -> tuple[str, list[Any], list[str]]:
    """The statement with each `:name` as the driver's placeholder, the values in order, and the names (in order of
    their placeholders). A name without a value answers like the database would."""
    spans = parameter_spans(sql)
    missing = next((name for _, _, name in spans if name not in params), None)
    if missing:
        at = next(start for start, _, name in spans if name == missing)
        raise RunError("FRM-DEST-1025", f"there is no value for parameter :{missing}", js.utf16_len(sql[:at]))
    if engine in ("mysql", "mariadb", "sqlserver") and spans:
        # These drivers format the statement with %: a % of the statement's own must be doubled.
        pieces, last = [], 0
        for start, end, _ in spans:
            pieces.append(sql[last:start].replace("%", "%%"))
            pieces.append("\0")
            last = end
        pieces.append(sql[last:].replace("%", "%%"))
        out = "".join(pieces)
        names = [name for _, _, name in spans]
        return out.replace("\0", "%s"), [params[n] for n in names], names
    order: list[str] = []
    out, last = [], 0
    for start, end, name in spans:
        out.append(sql[last:start])
        if engine == "postgresql":
            if name not in order:
                order.append(name)
            out.append(f"${order.index(name) + 1}")
        else:
            order.append(name)
            out.append(f":{len(order)}")
        last = end
    out.append(sql[last:])
    return "".join(out), [params[n] for n in order], order


# ── PostgreSQL: typed values for a prepared statement ───────────────────────────

_YES = {"true", "yes", "1", "y", "on", "t"}
_NO = {"false", "no", "0", "n", "off", "f"}


def _pg_value(type_name: str, text: str) -> Any:
    t = type_name.lower()
    try:
        if t in ("int2", "int4", "int8", "oid"):
            return int(text.strip())
        if t == "numeric":
            return Decimal(text.strip())
        if t in ("float4", "float8"):
            return float(text.strip())
        if t == "bool":
            word = text.strip().lower()
            if word in _YES or word in _NO:
                return word in _YES
            raise ValueError
        if t == "date":
            return date.fromisoformat(text.strip())
        if t in ("timestamp", "timestamptz"):
            moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
            return moment.replace(tzinfo=None) if t == "timestamp" and moment.tzinfo else moment
        if t in ("time", "timetz"):
            return time.fromisoformat(text.strip())
        if t == "uuid":
            return uuid.UUID(text.strip())
    except (ValueError, InvalidOperation):
        raise RunError("FRM-DEST-1025", f'invalid input syntax for type {type_name}: "{text}"') from None
    return text


async def _pg_prepared(c: Connection, sql: str, values: list[Any]) -> tuple[Any, list[Any]]:
    stmt = await c.raw.prepare(sql)
    types = [p.name for p in stmt.get_parameters()]
    return stmt, [_pg_value(types[i], v) if isinstance(v, str) else v for i, v in enumerate(values)]


def _type_name(engine: str, code: Any) -> str | None:
    if code is None:
        return None
    if engine in ("mysql", "mariadb"):
        from pymysql.constants import FIELD_TYPE

        names = {v: k for k, v in vars(FIELD_TYPE).items() if k.isupper()}
        return names.get(code, str(code))
    if engine == "sqlserver":
        return {1: "STRING", 2: "BINARY", 3: "NUMBER", 4: "DATETIME", 5: "DECIMAL"}.get(code, str(code))
    return getattr(code, "name", str(code))


def _plain(value: Any) -> Any:
    from app.modules.explorer.service import plain

    return plain(value)


# ── Reading ─────────────────────────────────────────────────────────────────────

_WRAPPABLE = re.compile(r"^\s*\(?\s*(SELECT|WITH|VALUES|TABLE)\b", re.I)


async def read(c: Connection, engine: str, sql: str, params: dict[str, str], cap: int) -> dict[str, Any]:
    """{ columns [{ name, type }], rows (lists, at most `cap`), duration_ms }."""
    started = clock.perf_counter()
    text, values, _ = bind(engine, sql, params)
    try:
        if engine == "postgresql":
            stmt, typed = await _pg_prepared(c, text, values)
            columns = [{"name": a.name, "type": a.type.name} for a in stmt.get_attributes()]
            async with c.raw.transaction(readonly=True):
                if columns:
                    cursor = await stmt.cursor(*typed)
                    found = await cursor.fetch(cap)
                else:
                    await stmt.fetch(*typed)
                    found = []
            rows = [[_plain(v) for v in r] for r in found]
        elif engine in ("mysql", "mariadb"):
            async with c.raw.cursor() as cursor:
                try:
                    await cursor.execute("START TRANSACTION READ ONLY")
                except Exception:  # noqa: BLE001 (older servers: the statement's kind was checked already)
                    pass
                body = f"SELECT * FROM ({text}) formalie_result LIMIT {cap}" if _WRAPPABLE.match(text) else text
                await cursor.execute(body, values or None)
                columns = [{"name": d[0], "type": _type_name(engine, d[1])} for d in cursor.description or []]
                rows = [[_plain(v) for v in r] for r in (await cursor.fetchmany(cap) if cursor.description else [])]
                await c.raw.rollback()
        elif engine == "sqlserver":
            def run() -> tuple[list[dict[str, Any]], list[list[Any]]]:
                cursor = c.raw.cursor()
                cursor.execute(text, tuple(values) if values else None)
                cols = [{"name": d[0], "type": _type_name(engine, d[1])} for d in cursor.description or []]
                got = [[_plain(v) for v in r] for r in (cursor.fetchmany(cap) if cursor.description else [])]
                try:
                    c.raw._conn.cancel()  # stop the rest of a large result
                except Exception:  # noqa: BLE001
                    pass
                c.raw.rollback()
                return cols, got
            columns, rows = await asyncio.to_thread(run)
        else:
            with c.raw.cursor() as cursor:
                await cursor.execute("SET TRANSACTION READ ONLY")
                await cursor.execute(text, values)
                columns = [{"name": d[0], "type": _type_name(engine, d[1])} for d in cursor.description or []]
                rows = [[_plain(v) for v in r] for r in (await cursor.fetchmany(cap) if cursor.description else [])]
            await c.raw.rollback()
    except RunError:
        raise
    except Exception as error:  # noqa: BLE001 (drivers raise many kinds)
        raise _problem(error, sql) from None
    return {"columns": columns, "rows": rows, "duration_ms": max(1, round((clock.perf_counter() - started) * 1000))}


# ── Changing ────────────────────────────────────────────────────────────────────

def _count(status: Any) -> int:
    try:
        return int(str(status).rsplit(" ", 1)[-1])
    except ValueError:
        return 0


async def change(c: Connection, engine: str, sql: str, params: dict[str, str], dry: bool) -> dict[str, Any]:
    """Runs a changing statement: for real (committed), or as a dry run (rolled back) → { rows_affected, duration_ms }."""
    started = clock.perf_counter()
    text, values, _ = bind(engine, sql, params)
    try:
        if engine == "postgresql":
            transaction = c.raw.transaction()
            await transaction.start()
            try:
                if values:
                    stmt, typed = await _pg_prepared(c, text, values)
                    await stmt.fetch(*typed)
                    affected = _count(stmt.get_statusmsg())
                else:
                    affected = _count(await c.raw.execute(text))
            except BaseException:
                await transaction.rollback()
                raise
            await (transaction.rollback() if dry else transaction.commit())
        elif engine in ("mysql", "mariadb"):
            async with c.raw.cursor() as cursor:
                affected = int(await cursor.execute(text, values or None) or 0)
            await (c.raw.rollback() if dry else c.raw.commit())
        elif engine == "sqlserver":
            def run() -> int:
                cursor = c.raw.cursor()
                cursor.execute(text, tuple(values) if values else None)
                count = int(cursor.rowcount or 0)
                c.raw.rollback() if dry else c.raw.commit()
                return max(0, count)
            affected = await asyncio.to_thread(run)
        else:
            with c.raw.cursor() as cursor:
                await cursor.execute(text, values)
                affected = int(cursor.rowcount or 0)
            await (c.raw.rollback() if dry else c.raw.commit())
    except RunError:
        raise
    except Exception as error:  # noqa: BLE001
        try:
            if engine != "postgresql":
                await asyncio.to_thread(c.raw.rollback) if engine == "sqlserver" else await c.raw.rollback()
        except Exception:  # noqa: BLE001
            pass
        raise _problem(error, sql) from None
    return {"rows_affected": max(0, affected), "duration_ms": max(1, round((clock.perf_counter() - started) * 1000))}

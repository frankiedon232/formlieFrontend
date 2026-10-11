"""What Formalie sees and changes on a customer's database: the tables it may see (its own, by the connection's
prefix in its tables schema, and the organisation's per the connection's access), statements it runs to create or
change its tables, and rows it writes (one per response).

Every engine is read through its own catalogue (pg_catalog, information_schema, sys, all_tab_columns); identifiers
are always quoted (tables.quote_name) and values always bound, never written into the SQL.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core import js
from app.modules.data_sources import tables as T
from app.modules.data_sources.connect import Connection
from app.modules.data_sources.engines import tables_schema_of
from app.modules.data_sources.probe import other_schemas

MAX_TABLES = 500


class WriteError(Exception):
    """The database refused a statement: `code` is FRM-DEST-1012 (no right to) or FRM-DEST-1025 (anything else)."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code, self.detail = code, detail


TIMED_OUT = ("statement timeout", "max_statement_time", "maximum statement execution time", "call timeout", "dpy-4024",
             "ora-03156", "query timeout", "timed out", "timeout expired")


def refused(error: Exception) -> WriteError:
    text = str(error).lower()
    if any(w in text for w in TIMED_OUT) or isinstance(error, TimeoutError):
        return WriteError("FRM-DEST-1011", str(error)[:300])
    denied = any(w in text for w in ("permission denied", "access denied", "command denied", "insufficient privileges",
                                     "ora-01031", "ora-01950", "1142", "permission was denied"))
    return WriteError("FRM-DEST-1012" if denied else "FRM-DEST-1025", str(error)[:300])


# ── Tables ──────────────────────────────────────────────────────────────────────

async def _columns(c: Connection, engine: str, schemas: list[str]) -> list[dict[str, Any]]:
    if engine == "postgresql":
        return await c.fetch("""
            SELECT n.nspname AS schema, c.relname AS name, c.reltuples::bigint AS rows, a.attname AS col,
                   upper(format_type(a.atttypid, a.atttypmod)) AS type, NOT a.attnotnull AS nullable,
                   a.atthasdef OR a.attidentity <> '' AS has_default,
                   EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisprimary AND a.attnum = ANY(i.indkey)) AS pk,
                   EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.oid AND i.indisunique AND i.indnatts = 1
                            AND i.indkey[0] = a.attnum) AS uq
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
             WHERE c.relkind IN ('r', 'p') AND n.nspname = ANY($1::text[]) AND NOT c.relispartition
             ORDER BY 1, 2, a.attnum""", [schemas])
    if engine in ("mysql", "mariadb"):
        marks = ", ".join(["%s"] * len(schemas))
        return await c.fetch(f"""
            SELECT c.TABLE_SCHEMA AS `schema`, c.TABLE_NAME AS name, t.TABLE_ROWS AS `rows`, c.COLUMN_NAME AS col,
                   upper(c.COLUMN_TYPE) AS type, c.IS_NULLABLE = 'YES' AS nullable,
                   c.COLUMN_DEFAULT IS NOT NULL OR c.EXTRA LIKE '%%auto_increment%%' AS has_default,
                   c.COLUMN_KEY = 'PRI' AS pk, c.COLUMN_KEY IN ('PRI', 'UNI') AS uq
              FROM information_schema.COLUMNS c
              JOIN information_schema.TABLES t ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
             WHERE t.TABLE_TYPE = 'BASE TABLE' AND c.TABLE_SCHEMA IN ({marks})
             ORDER BY 1, 2, c.ORDINAL_POSITION""", schemas)
    if engine == "sqlserver":
        marks = ", ".join(["%s"] * len(schemas))
        return await c.fetch(f"""
            SELECT s.name AS [schema], t.name AS name,
                   (SELECT SUM(p.rows) FROM sys.partitions p WHERE p.object_id = t.object_id AND p.index_id IN (0, 1)) AS rows,
                   col.name AS col,
                   UPPER(ty.name) + CASE WHEN ty.name IN ('varchar', 'char', 'varbinary', 'binary')
                        THEN '(' + CASE WHEN col.max_length = -1 THEN 'MAX' ELSE CAST(col.max_length AS varchar(10)) END + ')'
                        WHEN ty.name IN ('nvarchar', 'nchar')
                        THEN '(' + CASE WHEN col.max_length = -1 THEN 'MAX' ELSE CAST(col.max_length / 2 AS varchar(10)) END + ')'
                        WHEN ty.name IN ('decimal', 'numeric')
                        THEN '(' + CAST(col.precision AS varchar(5)) + ',' + CAST(col.scale AS varchar(5)) + ')' ELSE '' END AS type,
                   col.is_nullable AS nullable, CAST(CASE WHEN col.default_object_id <> 0 OR col.is_identity = 1 THEN 1 ELSE 0 END AS bit) AS has_default,
                   CAST(CASE WHEN EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                        WHERE ic.object_id = t.object_id AND ic.column_id = col.column_id AND i.is_primary_key = 1) THEN 1 ELSE 0 END AS bit) AS pk,
                   CAST(CASE WHEN EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                        WHERE ic.object_id = t.object_id AND ic.column_id = col.column_id AND i.is_unique = 1) THEN 1 ELSE 0 END AS bit) AS uq
              FROM sys.tables t JOIN sys.schemas s ON s.schema_id = t.schema_id
              JOIN sys.columns col ON col.object_id = t.object_id JOIN sys.types ty ON ty.user_type_id = col.user_type_id
             WHERE s.name IN ({marks})
             ORDER BY 1, 2, col.column_id""", schemas)
    marks = ", ".join(c.p(i + 1) for i in range(len(schemas)))
    return await c.fetch(f"""
        SELECT col.owner AS "schema", col.table_name AS name, t.num_rows AS "rows", col.column_name AS col,
               col.data_type || CASE WHEN col.data_type IN ('VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR')
                    THEN '(' || col.char_length || CASE WHEN col.char_used = 'C' THEN ' CHAR' ELSE '' END || ')'
                    WHEN col.data_type = 'NUMBER' AND col.data_precision IS NOT NULL
                    THEN '(' || col.data_precision || CASE WHEN col.data_scale > 0 THEN ',' || col.data_scale ELSE '' END || ')'
                    ELSE '' END AS type,
               CASE WHEN col.nullable = 'Y' THEN 1 ELSE 0 END AS nullable,
               CASE WHEN col.data_default IS NOT NULL OR col.identity_column = 'YES' THEN 1 ELSE 0 END AS has_default,
               CASE WHEN EXISTS (SELECT 1 FROM all_cons_columns cc JOIN all_constraints k ON k.owner = cc.owner
                    AND k.constraint_name = cc.constraint_name WHERE k.constraint_type = 'P' AND cc.owner = col.owner
                    AND cc.table_name = col.table_name AND cc.column_name = col.column_name) THEN 1 ELSE 0 END AS pk,
               CASE WHEN EXISTS (SELECT 1 FROM all_cons_columns cc JOIN all_constraints k ON k.owner = cc.owner
                    AND k.constraint_name = cc.constraint_name WHERE k.constraint_type IN ('P', 'U') AND cc.owner = col.owner
                    AND cc.table_name = col.table_name AND cc.column_name = col.column_name) THEN 1 ELSE 0 END AS uq
          FROM all_tab_columns col JOIN all_tables t ON t.owner = col.owner AND t.table_name = col.table_name
         WHERE col.owner IN ({marks})
         ORDER BY 1, 2, col.column_id""", schemas)


async def list_tables(c: Connection, engine: str, settings: dict[str, Any], access: dict[str, Any]) -> list[dict[str, Any]]:
    """DatabaseTable[] (shared/types/destinations.ts): Formalie's own (prefix, in its tables schema) first, then the
    organisation's when the access lets Formalie see them; by schema and name."""
    own_schema = tables_schema_of(engine, settings, access)
    prefix = access.get("table_prefix") or "formalie_"
    prefix = prefix.upper() if engine == "oracle" else prefix
    others = other_schemas(engine, settings, access) if access.get("other") != "none" else []
    schemas = list(dict.fromkeys([s for s in (own_schema, *others) if s]))
    if not schemas:
        return []
    tables: dict[tuple[str, str], dict[str, Any]] = {}
    for r in await _columns(c, engine, schemas):
        schema, name = str(r["schema"]), str(r["name"])
        own = schema == own_schema and name.startswith(prefix)
        if not own and schema not in others:
            continue
        key = (schema, name)
        if key not in tables:
            if len(tables) >= MAX_TABLES:
                continue
            rows = r.get("rows")
            tables[key] = {"schema": schema, "name": name, "columns": [],
                           "rows_estimate": int(rows) if rows is not None and int(rows) >= 0 else None, "formalie": own}
        tables[key]["columns"].append({"name": str(r["col"]), "type": str(r["type"]), "nullable": bool(r["nullable"]),
                                       "has_default": bool(r["has_default"]), "primary": bool(r["pk"]), "unique": bool(r["uq"])})
    return sorted(tables.values(), key=lambda t: (not t["formalie"], t["schema"], t["name"]))


def statements_of(sql: str) -> list[str]:
    """The statements tables.py writes, one per line ending in `;` (run one at a time, without the `;`)."""
    return [s.strip().rstrip(";") for s in re.split(r";\n", sql.strip()) if s.strip().rstrip(";")]


async def run(c: Connection, sql: str) -> None:
    for statement in statements_of(sql):
        try:
            await c.execute(statement)
        except Exception as error:  # noqa: BLE001 (drivers raise many kinds)
            raise refused(error) from None


# ── Rows ────────────────────────────────────────────────────────────────────────

def _aware(type_: str) -> bool:
    t = type_.upper()
    return "TIME ZONE" in t and "WITHOUT" not in t or t in ("TIMESTAMPTZ", "DATETIMEOFFSET")


def bound(engine: str, type_: str, value: Any) -> Any:
    """A value from tables.row_for as this driver takes it for a column of this type."""
    if value is None:
        return None
    kind = T.kind_of_type(type_)
    try:
        if kind == "integer" and not isinstance(value, bool):
            number = js.to_number(value)
            return int(number) if number == number and number == int(number) else value
        if kind == "decimal" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return Decimal(js.number_to_string(value))
        if kind == "boolean":
            flag = value is True or (isinstance(value, (int, float)) and value == 1) or value in ("true", "yes", "1")
            return int(flag) if engine in ("oracle", "mysql", "mariadb") else flag
        if kind == "datetime" and isinstance(value, str):
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            moment = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
            return moment if _aware(type_) and engine != "mysql" and engine != "mariadb" else \
                moment.astimezone(UTC).replace(tzinfo=None)
        if kind == "date" and isinstance(value, str):
            return date.fromisoformat(value[:10])
        if kind == "time" and isinstance(value, str):
            return time.fromisoformat(value)
    except (ValueError, OverflowError, InvalidOperation):
        raise WriteError("FRM-DEST-1025", f"value for {type_}") from None
    if isinstance(value, bool) or kind in ("integer", "decimal", "boolean"):
        return value
    return value if isinstance(value, str) else js.to_string(value)


async def write_row(c: Connection, engine: str, schema: str, table: str, columns: list[dict[str, Any]],
                    row: dict[str, Any], settings: dict[str, Any]) -> str:
    """Writes one response: added, or (update-or-insert) changed when a row with its key is there. → inserted · updated"""
    types = {col["column"]: col["type"] for col in columns}
    names = [name for name in row if name in types]
    values = [bound(engine, types[n], row[n]) for n in names]
    target = T.qualified(engine, schema, table)
    q = T.quote_name
    try:
        key = settings.get("key_column")
        if settings.get("write_mode") == "upsert" and key in row and row[key] is not None:
            key_value = bound(engine, types[key], row[key])
            found = await c.fetch(f"SELECT count(*) AS n FROM {target} WHERE {q(engine, key)} = {c.p(1)}", [key_value])
            if found and int(found[0]["n"]) > 0:
                rest = [n for n in names if n != key]
                if rest:
                    sets = ", ".join(f"{q(engine, n)} = {c.p(i + 1)}" for i, n in enumerate(rest))
                    await c.execute(f"UPDATE {target} SET {sets} WHERE {q(engine, key)} = {c.p(len(rest) + 1)}",
                                    [values[names.index(n)] for n in rest] + [key_value])
                return "updated"
        marks = ", ".join(c.p(i + 1) for i in range(len(names)))
        await c.execute(f"INSERT INTO {target} ({', '.join(q(engine, n) for n in names)}) VALUES ({marks})", values)
        return "inserted"
    except WriteError:
        raise
    except Exception as error:  # noqa: BLE001 (drivers raise many kinds)
        raise refused(error) from None

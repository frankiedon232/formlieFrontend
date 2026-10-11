"""Connection tests and health checks (the real version of the mock's data/dataSourceSim.ts). A test connects from
Formalie's servers step by step (network, SSH, TLS, sign-in, database, permissions) and checks every permission the
connection needs through the engine's own catalogue (PostgreSQL has_*_privilege, MySQL / MariaDB
information_schema privileges, SQL Server HAS_PERMS_BY_NAME, Oracle SESSION_PRIVS). A test never changes data.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.modules.data_sources.connect import Connection, ConnectError, Target, connect, reach, tunnel
from app.modules.data_sources.engines import default_schema_of, is_encrypted, operations_for, tables_schema_of

TEST_STEPS = ("network", "ssh", "tls", "sign_in", "database", "permissions")
_SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast", "mysql", "performance_schema", "sys", "guest",
                   "INFORMATION_SCHEMA", "db_owner", "db_accessadmin", "db_securityadmin", "db_ddladmin",
                   "db_backupoperator", "db_datareader", "db_datawriter", "db_denydatareader", "db_denydatawriter"}

Report = Callable[[dict[str, Any]], Awaitable[None]]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def other_schemas(engine: str, settings: dict[str, Any], access: dict[str, Any]) -> list[str]:
    listed = [s for s in access.get("schemas") or [] if s]
    return listed or [default_schema_of(engine, settings) or ("dbo" if engine == "sqlserver" else "public")]


# ── Permissions per engine ──────────────────────────────────────────────────────

async def _postgres(c: Connection, own: str, others: list[str]) -> dict[str, bool]:
    row = (await c.fetch("""
        SELECT has_schema_privilege(current_user, n.oid, 'CREATE') AND has_schema_privilege(current_user, n.oid, 'USAGE')
               AS create_table
          FROM pg_namespace n WHERE n.nspname = $1""", [own]) or [{"create_table": False}])[0]
    tables = await c.fetch("""
        SELECT coalesce(bool_and(has_schema_privilege(current_user, n.oid, 'USAGE')), false) AS read_schema,
               coalesce(bool_and(has_schema_privilege(current_user, n.oid, 'CREATE')), false) AS other_structure
          FROM pg_namespace n WHERE n.nspname = ANY($1::text[])""", [others])
    rights = await c.fetch("""
        SELECT coalesce(bool_and(has_table_privilege(current_user, c.oid, 'SELECT')), true) AS read_rows,
               coalesce(bool_and(has_table_privilege(current_user, c.oid, 'INSERT')), true) AS insert,
               coalesce(bool_and(has_table_privilege(current_user, c.oid, 'UPDATE')), true) AS update,
               coalesce(bool_and(has_table_privilege(current_user, c.oid, 'DELETE')), true) AS delete
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = ANY($1::text[]) AND c.relkind IN ('r', 'p', 'v', 'm')""", [others])
    sequences = await c.fetch("""
        SELECT coalesce(bool_and(has_sequence_privilege(current_user, c.oid, 'USAGE')), true) AS sequences
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = ANY($1::text[]) AND c.relkind = 'S'""", [others])
    own_ok = bool(row["create_table"])
    found = tables[0] if tables else {}
    return {"connect": True, "create_table": own_ok, "own_rows": own_ok, "alter_table": own_ok, "create_index": own_ok,
            "cancel": True, "read_schema": bool(found.get("read_schema")), "row_counts": True,
            **{k: bool(v) and bool(found.get("read_schema")) for k, v in rights[0].items()},
            "sequences": bool(sequences[0]["sequences"]), "other_structure": bool(found.get("other_structure"))}


async def _mysql(c: Connection, own: str, others: list[str]) -> dict[str, bool]:
    who = (await c.fetch("SELECT CURRENT_USER() AS u"))[0]["u"]
    user, _, host = str(who).rpartition("@")
    grantee = f"'{user}'@'{host}'"
    held: dict[str, set[str]] = {"*": set()}
    for row in await c.fetch("SELECT PRIVILEGE_TYPE AS p FROM information_schema.USER_PRIVILEGES WHERE GRANTEE = %s", [grantee]):
        held["*"].add(str(row["p"]).upper())
    for row in await c.fetch("SELECT TABLE_SCHEMA AS s, PRIVILEGE_TYPE AS p FROM information_schema.SCHEMA_PRIVILEGES "
                             "WHERE GRANTEE = %s", [grantee]):
        held.setdefault(str(row["s"]).replace("\\_", "_"), set()).add(str(row["p"]).upper())

    def has(privilege: str, schemas: list[str]) -> bool:
        return all(privilege in held["*"] or privilege in held.get(s, set()) for s in schemas)
    return {"connect": True, "create_table": has("CREATE", [own]),
            "own_rows": all(has(p, [own]) for p in ("SELECT", "INSERT", "UPDATE", "DELETE")),
            "alter_table": has("ALTER", [own]), "create_index": has("INDEX", [own]), "cancel": True,
            "read_schema": has("SELECT", others), "row_counts": has("SELECT", others), "read_rows": has("SELECT", others),
            "insert": has("INSERT", others), "update": has("UPDATE", others), "delete": has("DELETE", others),
            "other_structure": all(has(p, others) for p in ("CREATE", "ALTER", "INDEX", "DROP"))}


async def _sqlserver(c: Connection, own: str, others: list[str]) -> dict[str, bool]:
    def perm(schema: str | None, permission: str) -> str:
        return (f"HAS_PERMS_BY_NAME('{schema.replace(chr(39), chr(39) * 2)}', 'SCHEMA', '{permission}')" if schema
                else f"HAS_PERMS_BY_NAME(NULL, 'DATABASE', '{permission}')")
    columns = [f"{perm(None, 'CREATE TABLE')} AS create_table", f"{perm(own, 'ALTER')} AS own_alter",
               f"{perm(None, 'VIEW DATABASE STATE')} AS row_counts"]
    for i, schema in enumerate(others):
        columns += [f"{perm(schema, 'SELECT')} AS s{i}_select", f"{perm(schema, 'VIEW DEFINITION')} AS s{i}_view",
                    f"{perm(schema, 'INSERT')} AS s{i}_insert", f"{perm(schema, 'UPDATE')} AS s{i}_update",
                    f"{perm(schema, 'DELETE')} AS s{i}_delete", f"{perm(schema, 'ALTER')} AS s{i}_alter"]
    row = (await c.fetch("SELECT " + ", ".join(columns)))[0]

    def every(kind: str) -> bool:
        return all(row.get(f"s{i}_{kind}") == 1 for i in range(len(others)))
    own_ok = row.get("create_table") == 1 and row.get("own_alter") == 1
    return {"connect": True, "create_table": own_ok, "own_rows": own_ok, "alter_table": own_ok, "create_index": own_ok,
            "cancel": True, "read_schema": every("view"), "row_counts": row.get("row_counts") == 1,
            "read_rows": every("select"), "insert": every("insert"), "update": every("update"),
            "delete": every("delete"), "other_structure": every("alter") and row.get("create_table") == 1}


async def _oracle(c: Connection, own: str, others: list[str]) -> dict[str, bool]:
    privileges = {str(r["privilege"]).upper() for r in await c.fetch("SELECT privilege FROM session_privs")}
    quota = await c.fetch("SELECT count(*) AS n FROM user_ts_quotas WHERE max_bytes <> 0")
    own_ok = "CREATE TABLE" in privileges and (bool(quota and quota[0]["n"]) or "UNLIMITED TABLESPACE" in privileges)

    async def on_tables(privilege: str) -> bool:
        if f"{privilege} ANY TABLE" in privileges:
            return True
        upper = [o.upper() for o in others]
        rows = await c.fetch("SELECT count(*) AS n FROM all_tables t WHERE t.owner IN (SELECT column_value FROM "
                             "TABLE(sys.odcivarchar2list(" + ", ".join(f":{i + 1}" for i in range(len(upper))) + "))) "
                             "AND NOT EXISTS (SELECT 1 FROM all_tab_privs p WHERE p.table_schema = t.owner AND "
                             f"p.table_name = t.table_name AND p.privilege = '{privilege}')", upper)
        return not rows or int(rows[0]["n"]) == 0
    read = await on_tables("SELECT")
    return {"connect": True, "create_table": own_ok, "own_rows": own_ok, "alter_table": own_ok, "create_index": own_ok,
            "cancel": True, "read_schema": read, "row_counts": read, "read_rows": read,
            "insert": await on_tables("INSERT"), "update": await on_tables("UPDATE"),
            "delete": await on_tables("DELETE"), "sequences": "SELECT ANY SEQUENCE" in privileges or read,
            "other_structure": "CREATE ANY TABLE" in privileges and "ALTER ANY TABLE" in privileges}


async def permissions_of(c: Connection, engine: str, settings: dict[str, Any], access: dict[str, Any]) -> dict[str, bool]:
    own, others = tables_schema_of(engine, settings, access), other_schemas(engine, settings, access)
    check = {"postgresql": _postgres, "mysql": _mysql, "mariadb": _mysql, "sqlserver": _sqlserver, "oracle": _oracle}[engine]
    return await check(c, own, others)


async def schemas_and_tables(c: Connection, engine: str) -> tuple[list[str], int | None]:
    if engine == "postgresql":
        schemas = [r["s"] for r in await c.fetch(
            "SELECT nspname AS s FROM pg_namespace WHERE has_schema_privilege(current_user, oid, 'USAGE') "
            "AND nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema' ORDER BY 1")]
        count = await c.fetch("SELECT count(*) AS n FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                              "WHERE c.relkind IN ('r', 'p') AND n.nspname = ANY($1::text[])", [schemas])
    elif engine in ("mysql", "mariadb"):
        schemas = [r["s"] for r in await c.fetch("SELECT SCHEMA_NAME AS s FROM information_schema.SCHEMATA ORDER BY 1")]
        count = await c.fetch("SELECT count(*) AS n FROM information_schema.TABLES WHERE TABLE_TYPE = 'BASE TABLE' "
                              "AND TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')")
    elif engine == "sqlserver":
        schemas = [r["s"] for r in await c.fetch("SELECT name AS s FROM sys.schemas ORDER BY 1")]
        count = await c.fetch("SELECT count(*) AS n FROM sys.tables")
    else:
        schemas = [r["s"] for r in await c.fetch("SELECT DISTINCT owner AS s FROM all_tables ORDER BY 1")]
        count = await c.fetch("SELECT count(*) AS n FROM all_tables")
    return [s for s in schemas if s not in _SYSTEM_SCHEMAS], (int(count[0]["n"]) if count else None)


# ── A connection test ───────────────────────────────────────────────────────────

def fresh_steps(settings: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"key": k, "status": "pending", "duration_ms": None, "error_code": None} for k in TEST_STEPS]


async def run_test(target: Target, access: dict[str, Any], report: Report) -> dict[str, Any]:
    """Runs every step, calling `report` with the test so far after each one; returns the finished result."""
    s = target.settings
    steps = fresh_steps(s)
    by = {step["key"]: step for step in steps}
    result: dict[str, Any] = {"server_version": None, "latency_ms": None, "permissions": [], "findings": [],
                              "schemas": [], "tables_count": None}
    encrypted = is_encrypted(target.engine, s)

    async def mark(key: str, status: str, started: float | None = None, code: str | None = None) -> None:
        by[key].update(status=status, error_code=code,
                       duration_ms=round((time.perf_counter() - started) * 1000) if started is not None else None)
        await report({"steps": steps, **result})

    def fail_rest(after: str) -> None:
        for step in steps[TEST_STEPS.index(after) + 1:]:
            step["status"] = "skipped"

    # Network: the database, or the SSH server in front of it
    started = time.perf_counter()
    by["network"]["status"] = "running"
    await report({"steps": steps, **result})
    try:
        first_host, first_port = (str(s.get("ssh_host")), int(s.get("ssh_port") or 22)) if s.get("ssh") else \
            (str(s.get("host") or ""), int(s.get("port") or 0))
        if target.engine == "oracle" and s.get("connect_by") == "descriptor" and not s.get("ssh"):
            from app.modules.data_sources.engines import address_of

            address = address_of("oracle", s)
            first_host, _, port_text = address.rpartition(":")
            first_host, first_port = (first_host or address), int(port_text or 1521) if port_text.isdigit() else 1521
        result["latency_ms"] = round(await reach(first_host, first_port, target.timeout))
        await mark("network", "passed", started)
    except ConnectError as error:
        fail_rest("network")
        await mark("network", "failed", started, error.code)
        return result
    # SSH, TLS, sign-in and the database in one connection
    if not s.get("ssh"):
        by["ssh"]["status"] = "skipped"
    started = time.perf_counter()
    try:
        async with connect(target) as c:
            if s.get("ssh"):
                await mark("ssh", "passed", started)
            await mark("tls", "passed" if encrypted else "warning", started)
            await mark("sign_in", "passed", started)
            started = time.perf_counter()
            result["server_version"] = await c.version()
            await c.fetch("SELECT 1 AS one" + (" FROM dual" if target.engine == "oracle" else ""))
            await mark("database", "passed", started)
            started = time.perf_counter()
            by["permissions"]["status"] = "running"
            granted = await permissions_of(c, target.engine, s, access)
            result["schemas"], result["tables_count"] = await schemas_and_tables(c, target.engine)
    except ConnectError as error:
        failed_at = {"ssh": "ssh", "tls": "tls", "network": "ssh" if s.get("ssh") else "network"}.get(error.step, "sign_in")
        if error.code == "FRM-DEST-1005":
            failed_at = "database"
        if error.code == "FRM-DEST-1003":
            failed_at = "tls"
        for key in TEST_STEPS[TEST_STEPS.index("ssh"):TEST_STEPS.index(failed_at)]:
            if by[key]["status"] == "pending":
                by[key]["status"] = "passed" if key != "tls" or encrypted else "warning"
        fail_rest(failed_at)
        await mark(failed_at, "failed", started, error.code)
        return result
    except Exception as error:  # noqa: BLE001 (a permission query the server refused)
        fail_rest("permissions")
        await mark("permissions", "failed", started, "FRM-DEST-1012" if "permission" in str(error).lower() else "FRM-DEST-1001")
        return result
    operations = operations_for(target.engine, access)
    result["permissions"] = [{"operation": o["key"], "status": "not_needed" if not o["needed"]
                              else "granted" if granted.get(o["key"], False) else "missing"} for o in operations]
    own_missing = any(o["level"] == "own" and o["needed"] and not granted.get(o["key"], False) for o in operations)
    findings = []
    if not own_missing and any(p["status"] == "missing" for p in result["permissions"]):
        findings.append("missing_permissions")
    if not encrypted:
        findings.append("tls_off")
    if target.engine == "sqlserver" and s.get("trust_server_certificate"):
        findings.append("trust_certificate")
    result["findings"] = findings
    if own_missing:
        await mark("permissions", "failed", started, "FRM-DEST-1012")
    elif "missing_permissions" in findings:
        await mark("permissions", "warning", started, "FRM-DEST-1006")
    else:
        await mark("permissions", "passed", started)
    return result


def status_of(steps: list[dict[str, Any]], findings: list[str], running: bool = False) -> str:
    if running:
        return "running"
    if any(s["status"] == "failed" for s in steps):
        return "failed"
    if any(s["status"] == "warning" and s["key"] == "permissions" for s in steps) or any(f != "trust_certificate" for f in findings):
        return "warning"
    return "passed"


async def health_check(target: Target) -> dict[str, Any]:
    """A light check: sign in and run SELECT 1 → {status, latency_ms, error_code}."""
    started = time.perf_counter()
    try:
        async with tunnel(target):
            pass
        async with connect(target) as c:
            await c.fetch("SELECT 1 AS one" + (" FROM dual" if target.engine == "oracle" else ""))
        return {"status": "passed", "latency_ms": round((time.perf_counter() - started) * 1000), "error_code": None}
    except ConnectError as error:
        return {"status": "failed", "latency_ms": None, "error_code": error.code}


__all__ = ["TEST_STEPS", "fresh_steps", "health_check", "run_test", "status_of", "_now"]

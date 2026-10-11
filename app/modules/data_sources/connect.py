"""Connecting to a customer's own database (B9): one small interface over the drivers, from Formalie's servers.

    PostgreSQL       asyncpg              ssl modes disable → verify-full, client certificate
    MySQL / MariaDB  aiomysql             ssl modes disabled → verify_identity, client certificate
    SQL Server       pymssql (in a thread) SQL sign-in; Microsoft Entra sign-in is not available yet
    Oracle           oracledb, thin mode  TCPS with the server's certificate; native network encryption
                                           needs the Oracle client and is not available yet
    every engine     an SSH tunnel (asyncssh) when switched on; a connect time-out

The host check (no loopback, link-local, cloud metadata: engines.is_blocked_host) is repeated on every address the
name resolves to, so a name can't point Formalie at itself. Development and tests may allow local addresses
(DATASOURCES_ALLOW_LOCAL), which production refuses.

Every error leaves as a ConnectError with its FRM-DEST code; driver messages are never shown to people (they can
carry host names and accounts), only logged.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import ssl
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from app.core.config import get_settings
from app.modules.data_sources.engines import database_name_of, is_blocked_host

log = logging.getLogger("formalie.datasources")


class ConnectError(Exception):
    def __init__(self, code: str, step: str, detail: str = "") -> None:
        super().__init__(f"{code} at {step}: {detail[:300]}")
        self.code, self.step, self.detail = code, step, detail


@dataclass
class Target:
    engine: str
    settings: dict[str, Any]
    secrets: dict[str, str] = field(default_factory=dict)

    @property
    def timeout(self) -> float:
        try:
            return max(1.0, min(120.0, float(self.settings.get("connect_timeout") or 10)))
        except (TypeError, ValueError):
            return 10.0


# ── Addresses ───────────────────────────────────────────────────────────────────

def _blocked_ip(ip: str) -> bool:
    address = ipaddress.ip_address(ip.split("%")[0])
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified \
        or address.is_reserved or (isinstance(address, ipaddress.IPv4Address) and address in ipaddress.ip_network("100.64.0.0/10"))


async def resolve(host: str, port: int, step: str = "network") -> str:
    """The address to connect to; refused when the name (or what it resolves to) is one Formalie never reaches."""
    allow_local = get_settings().datasources_allow_local and not get_settings().is_production
    name = host.strip().strip("[]").rstrip(".")
    if is_blocked_host(name) and not allow_local:
        raise ConnectError("FRM-DEST-1001", step, "blocked host")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(name, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ConnectError("FRM-DEST-1001", step, f"name not found: {error}") from None
    addresses = [info[4][0] for info in infos]
    if not allow_local and any(_blocked_ip(a) for a in addresses):
        raise ConnectError("FRM-DEST-1001", step, "resolves to a blocked address")
    return addresses[0]


async def reach(host: str, port: int, timeout: float, step: str = "network") -> float:
    """A TCP connection to the address → milliseconds it took."""
    address = await resolve(host, port, step)
    started = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(address, port), timeout)
    except TimeoutError:
        raise ConnectError("FRM-DEST-1011", step, "connect timed out") from None
    except OSError as error:
        raise ConnectError("FRM-DEST-1001", step, str(error)) from None
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return (time.perf_counter() - started) * 1000


# ── SSH tunnel ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def tunnel(target: Target) -> AsyncIterator[tuple[str, int]]:
    """The (host, port) to connect the driver to: the database itself, or the local end of an SSH tunnel."""
    s = target.settings
    if not s.get("ssh"):
        yield str(s.get("host") or ""), int(s.get("port") or 0)
        return
    import asyncssh

    ssh_host, ssh_port = str(s.get("ssh_host") or ""), int(s.get("ssh_port") or 22)
    await resolve(ssh_host, ssh_port, "ssh")
    try:
        key = asyncssh.import_private_key(target.secrets.get("ssh_private_key", ""), target.secrets.get("ssh_passphrase") or None)
        connection = await asyncio.wait_for(asyncssh.connect(
            ssh_host, ssh_port, username=str(s.get("ssh_username") or ""), client_keys=[key],
            known_hosts=None), target.timeout)  # host key pinning: see PROGRESS.md
    except TimeoutError:
        raise ConnectError("FRM-DEST-1004", "ssh", "ssh timed out") from None
    except (asyncssh.Error, OSError, ValueError) as error:
        raise ConnectError("FRM-DEST-1004", "ssh", str(error)) from None
    try:
        listener = await connection.forward_local_port("127.0.0.1", 0, str(s.get("host") or ""), int(s.get("port") or 0))
        try:
            yield "127.0.0.1", listener.get_port()
        finally:
            listener.close()
    finally:
        connection.close()


# ── TLS ─────────────────────────────────────────────────────────────────────────

def _tls_context(target: Target, verify: bool, check_name: bool) -> ssl.SSLContext:
    """A TLS context from the connection's certificates (they are written to a private temporary folder only
    for as long as the context is built)."""
    context = ssl.create_default_context()
    context.check_hostname = verify and check_name
    context.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    ca = target.secrets.get("ca_certificate")
    if ca:
        context.load_verify_locations(cadata=ca)
    cert, key = target.secrets.get("client_certificate"), target.secrets.get("client_key")
    if cert and key:
        with tempfile.TemporaryDirectory(prefix="formalie-tls-") as folder:
            cert_file, key_file = Path(folder) / "client.pem", Path(folder) / "client.key"
            cert_file.write_text(cert)
            key_file.write_text(key)
            context.load_cert_chain(str(cert_file), str(key_file))
    return context


# ── Connections ─────────────────────────────────────────────────────────────────

class Connection:
    """fetch(sql, params) → rows as dicts; execute(sql, params) → rows affected. `p(n)` writes the n-th placeholder."""

    engine: str

    def p(self, n: int) -> str:
        raise NotImplementedError

    async def fetch(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        raise NotImplementedError

    async def version(self) -> str | None:
        return None

    async def close(self) -> None:
        raise NotImplementedError


class _Postgres(Connection):
    engine = "postgresql"

    def __init__(self, raw: Any) -> None:
        self.raw = raw

    def p(self, n: int) -> str:
        return f"${n}"

    async def fetch(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        return [dict(r) for r in await self.raw.fetch(sql, *(params or []))]

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        status = await self.raw.execute(sql, *(params or []))
        try:
            return int(status.rsplit(" ", 1)[-1])
        except ValueError:
            return 0

    async def version(self) -> str | None:
        return str(self.raw.get_server_version().major) + "." + str(self.raw.get_server_version().minor)

    async def close(self) -> None:
        await self.raw.close()


class _MySQL(Connection):
    def __init__(self, raw: Any, engine: str) -> None:
        self.raw, self.engine = raw, engine

    def p(self, n: int) -> str:
        return "%s"

    async def fetch(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        import aiomysql

        async with self.raw.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(sql, params or None)
            return list(await cursor.fetchall())

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        async with self.raw.cursor() as cursor:
            count = await cursor.execute(sql, params or None)
            await self.raw.commit()
            return int(count or 0)

    async def version(self) -> str | None:
        return str(self.raw.get_server_info())

    async def close(self) -> None:
        self.raw.close()


class _Threaded(Connection):
    """Drivers without asyncio (pymssql): every call runs in a worker thread."""

    def __init__(self, raw: Any, engine: str, placeholder: str) -> None:
        self.raw, self.engine, self.placeholder = raw, engine, placeholder

    def p(self, n: int) -> str:
        return self.placeholder

    async def fetch(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        def run() -> list[dict[str, Any]]:
            cursor = self.raw.cursor(as_dict=True)
            cursor.execute(sql, tuple(params or ()))
            return list(cursor.fetchall())
        return await asyncio.to_thread(run)

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        def run() -> int:
            cursor = self.raw.cursor()
            cursor.execute(sql, tuple(params or ()))
            self.raw.commit()
            return int(cursor.rowcount or 0)
        return await asyncio.to_thread(run)

    async def version(self) -> str | None:
        rows = await self.fetch("SELECT CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(64)) AS v")
        return str(rows[0]["v"]) if rows else None

    async def close(self) -> None:
        await asyncio.to_thread(self.raw.close)


class _Oracle(Connection):
    engine = "oracle"

    def __init__(self, raw: Any) -> None:
        self.raw = raw

    def p(self, n: int) -> str:
        return f":{n}"

    async def fetch(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        with self.raw.cursor() as cursor:
            await cursor.execute(sql, params or [])
            names = [d[0].lower() for d in cursor.description or []]
            return [dict(zip(names, row, strict=False)) for row in await cursor.fetchall()]

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        with self.raw.cursor() as cursor:
            await cursor.execute(sql, params or [])
            await self.raw.commit()
            return int(cursor.rowcount or 0)

    async def version(self) -> str | None:
        return str(self.raw.version)

    async def close(self) -> None:
        await self.raw.close()


def _sign_in_code(error: Exception) -> str:
    text = str(error).lower()
    if any(w in text for w in ("password", "authentication", "access denied", "login failed", "ora-01017", "1045")):
        return "FRM-DEST-1002"
    if any(w in text for w in ("does not exist", "unknown database", "cannot open database", "ora-12514", "ora-12505", "1049")):
        return "FRM-DEST-1005"
    if any(w in text for w in ("ssl", "tls", "certificate")):
        return "FRM-DEST-1003"
    if "timeout" in text or "timed out" in text:
        return "FRM-DEST-1011"
    return "FRM-DEST-1001"


async def _open(target: Target, host: str, port: int) -> Connection:
    s, secrets, timeout = target.settings, target.secrets, target.timeout
    engine = target.engine
    if engine == "postgresql":
        import asyncpg

        mode = str(s.get("ssl_mode") or "require")
        ssl_arg: Any = {"disable": False, "allow": "allow", "prefer": "prefer"}.get(mode)
        if mode in ("require", "verify-ca", "verify-full"):
            ssl_arg = _tls_context(target, verify=mode != "require", check_name=mode == "verify-full")
        raw = await asyncpg.connect(host=host, port=port, user=str(s.get("username") or ""),
                                    password=secrets.get("password"), database=database_name_of(engine, s),
                                    ssl=ssl_arg, timeout=timeout, command_timeout=60,
                                    target_session_attrs=str(s.get("target_session_attrs") or "any"),
                                    server_settings={"application_name": "Formalie"})
        return _Postgres(raw)
    if engine in ("mysql", "mariadb"):
        import aiomysql

        mode = str(s.get("ssl_mode") or "required")
        context = None
        if mode not in ("disabled", "preferred"):
            context = _tls_context(target, verify=mode in ("verify_ca", "verify_identity"), check_name=mode == "verify_identity")
        raw = await aiomysql.connect(host=host, port=port, user=str(s.get("username") or ""),
                                     password=secrets.get("password") or "", db=database_name_of(engine, s),
                                     charset=str(s.get("charset") or "utf8mb4"), ssl=context, connect_timeout=timeout,
                                     autocommit=False, init_command=f"SET time_zone = '{_tz(s)}'")
        return _MySQL(raw, engine)
    if engine == "sqlserver":
        if s.get("auth") not in (None, "", "sql"):
            raise ConnectError("FRM-DEST-1002", "sign_in", "Microsoft Entra sign-in is not available yet")
        import pymssql

        server = host if not s.get("instance") or s.get("ssh") else f"{host}\\{s['instance']}"

        def connect() -> Any:
            return pymssql.connect(server=server, port=str(port), user=str(s.get("username") or ""),
                                   password=secrets.get("password") or "", database=database_name_of(engine, s),
                                   login_timeout=int(timeout), timeout=60, appname="Formalie", autocommit=False)
        return _Threaded(await asyncio.to_thread(connect), engine, "%s")
    if engine == "oracle":
        import oracledb

        protocol = "tcp" if s.get("protocol") == "tcp" and s.get("connect_by") != "descriptor" else "tcps"
        if s.get("connect_by") == "descriptor" and not s.get("ssh"):
            dsn = str(s.get("descriptor") or "")
        else:
            service = f"(SID={s.get('sid')})" if s.get("connect_by") == "sid" else f"(SERVICE_NAME={database_name_of(engine, s)})"
            dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL={protocol})(HOST={host})(PORT={port}))(CONNECT_DATA={service}))"
        params = oracledb.ConnectParams(tcp_connect_timeout=timeout,
                                        ssl_server_dn_match=bool(s.get("ssl_server_dn_match", True)))
        raw = await oracledb.connect_async(user=str(s.get("username") or ""), password=secrets.get("password") or "",
                                           dsn=dsn, params=params)
        return _Oracle(raw)
    raise ConnectError("FRM-DEST-1001", "network", f"unknown engine {engine}")


def _tz(settings: dict[str, Any]) -> str:
    zone = str(settings.get("time_zone") or "+00:00")
    import re

    return zone if re.fullmatch(r"[+-]\d{2}:\d{2}|[A-Za-z_/]+", zone) else "+00:00"


@asynccontextmanager
async def connect(target: Target) -> AsyncIterator[Connection]:
    """A signed-in connection (through the tunnel when there is one), closed afterwards."""
    async with tunnel(target) as (host, port):
        if not target.settings.get("ssh") and host:
            await resolve(host, port)
        try:
            connection = await asyncio.wait_for(_open(target, host, port), target.timeout + 5)
        except ConnectError:
            raise
        except TimeoutError:
            raise ConnectError("FRM-DEST-1011", "sign_in", "sign-in timed out") from None
        except ssl.SSLError as error:
            raise ConnectError("FRM-DEST-1003", "tls", str(error)) from None
        except Exception as error:  # noqa: BLE001 (drivers raise many kinds)
            log.info("data source sign-in failed", extra={"engine": target.engine, "error": str(error)[:300]})
            raise ConnectError(_sign_in_code(error), "sign_in", str(error)) from None
        try:
            yield connection
        finally:
            try:
                await connection.close()
            except Exception:  # noqa: BLE001
                pass

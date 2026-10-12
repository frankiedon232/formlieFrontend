"""Connecting to a customer's own database (B9): one small interface over the drivers, from Formalie's servers.

    PostgreSQL       asyncpg              ssl modes disable → verify-full, client certificate
    MySQL / MariaDB  aiomysql             ssl modes disabled → verify_identity, client certificate
    SQL Server       pymssql (in a thread) SQL sign-in; Microsoft Entra sign-in is not available yet
    Oracle           oracledb, thin mode  TCPS with the server's certificate; native network encryption
                                           needs the Oracle client and is not available yet
    every engine     an SSH tunnel (asyncssh) when switched on; a connect time-out

Addresses (security review B17, H1):
- The name check (engines.is_blocked_host, the same answers as the frontend) runs first, then every address the name
  resolves to goes through Formalie's one blocklist (app.core.outbound.blocked: anything not globally routable, so
  private networks, loopback, link-local, CGNAT, unique local, metadata, multicast). Private networks are reached
  only through an SSH tunnel, whose server must itself be public.
- The driver then connects to that checked address, never to the name again (no DNS rebinding); the name is kept
  for TLS (SNI and the certificate's name check, drivers.NamedTLSContext).
- Oracle descriptors are parsed: exactly one address, TCP or TCPS, a service name or SID, nothing else (no address
  lists, proxies or wallet folders); Formalie writes the descriptor it connects with.
- SSH host keys are pinned: the first successful test stores the server's key fingerprint, and a different key is
  refused (FRM-DEST-1004, reason `host_key_changed`) until someone with data.edit changes the SSH settings.
- Development and tests may allow local addresses (DATASOURCES_ALLOW_LOCAL, APP_ENV development or test only).

The drivers' own client-side file features are off: aiomysql's LOCAL INFILE (drivers.install_mysql_guard) and
multiple statements, asyncpg's password file (a password is always passed), Oracle's tnsnames and wallets (Formalie
writes the whole descriptor), FreeTDS aliases (the server is always an address).

Every error leaves as a ConnectError with its FRM-DEST code; driver messages are never shown to people (they can
carry host names and accounts), only logged.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import ssl
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from app.core import outbound
from app.core.config import get_settings
from app.modules.data_sources.drivers import install_mysql_guard, named_context
from app.modules.data_sources.engines import database_name_of, is_blocked_host

log = logging.getLogger("formalie.datasources")
install_mysql_guard()  # at import: no MySQL connection is ever opened without it


class ConnectError(Exception):
    """`reason`: a short machine word for the FRM error's details (e.g. host_key_changed), when there is one."""

    def __init__(self, code: str, step: str, detail: str = "", reason: str | None = None) -> None:
        super().__init__(f"{code} at {step}: {detail[:300]}")
        self.code, self.step, self.detail, self.reason = code, step, detail, reason

    def details(self) -> list[dict[str, str]] | None:
        if not self.reason:
            return None
        return [{"field": "ssh_host" if self.step == "ssh" else "host", "message": self.reason}]


@dataclass
class Target:
    engine: str
    settings: dict[str, Any]
    secrets: dict[str, str] = field(default_factory=dict)
    host_key: str | None = None  # the SSH server's pinned key, "host:port SHA256:...", None until the first test
    seen_host_key: str | None = None  # the same for the key the SSH server showed this time

    @property
    def timeout(self) -> float:
        try:
            return max(1.0, min(120.0, float(self.settings.get("connect_timeout") or 10)))
        except (TypeError, ValueError):
            return 10.0


# ── Addresses ───────────────────────────────────────────────────────────────────

def _allow_local() -> bool:
    return outbound.local_allowed(get_settings().datasources_allow_local)


async def resolve(host: str, port: int, step: str = "network") -> str:
    """The checked address to connect to; refused when the name (or any address it resolves to) is one Formalie
    never reaches (outbound.blocked: private networks included; those go through an SSH tunnel)."""
    allow_local = _allow_local()
    name = host.strip().strip("[]").rstrip(".")
    if not name:
        raise ConnectError("FRM-DEST-1001", step, "no host")
    if is_blocked_host(name) and not allow_local:
        raise ConnectError("FRM-DEST-1001", step, "blocked host")
    try:
        if outbound.resolver is not None:  # tests
            addresses = list(await outbound.resolver(name, port))
        else:
            infos = await asyncio.get_running_loop().getaddrinfo(name, port, type=socket.SOCK_STREAM)
            addresses = [str(info[4][0]) for info in infos]
    except (socket.gaierror, OSError, UnicodeError) as error:
        raise ConnectError("FRM-DEST-1001", step, f"name not found: {error}") from None
    if not addresses:
        raise ConnectError("FRM-DEST-1001", step, "name not found")
    if not allow_local and any(outbound.blocked(a) for a in addresses):
        raise ConnectError("FRM-DEST-1001", step, "resolves to a blocked address")
    return addresses[0].split("%")[0]


# ── Oracle descriptors ──────────────────────────────────────────────────────────

_ORACLE_NAME = re.compile(r"^[A-Za-z0-9_.$#-]{1,128}$")
_DESCRIPTOR_KEYS = {"DESCRIPTION", "ADDRESS", "ADDRESS_LIST", "PROTOCOL", "HOST", "PORT", "CONNECT_DATA",
                    "SERVICE_NAME", "SID", "SERVER", "INSTANCE_NAME", "RETRY_COUNT", "RETRY_DELAY",
                    "CONNECT_TIMEOUT", "TRANSPORT_CONNECT_TIMEOUT"}


def oracle_descriptor(descriptor: str) -> dict[str, Any]:
    """{host, port, protocol, service_name | sid} from a pasted descriptor; refused (FRM-DEST-1001, reason
    `descriptor`) when it has more than one address, a proxy, a wallet folder, a security section or anything else
    Formalie doesn't write itself."""
    text = descriptor.strip()
    keys = [k.upper() for k in re.findall(r"\(\s*([A-Za-z_]+)\s*=", text)]
    if not text.startswith("(") or not keys or any(k not in _DESCRIPTOR_KEYS for k in keys):
        raise ConnectError("FRM-DEST-1001", "network", "descriptor option not allowed", "descriptor")
    values: dict[str, list[str]] = {}
    for key, value in re.findall(r"\(\s*([A-Za-z_]+)\s*=\s*([^()]*?)\s*\)", text):
        values.setdefault(key.upper(), []).append(value)
    hosts, ports, protocols = values.get("HOST", []), values.get("PORT", []), values.get("PROTOCOL", [])
    if len(hosts) != 1 or len(ports) > 1 or len(protocols) > 1 or keys.count("ADDRESS") > 1 \
            or keys.count("DESCRIPTION") > 1:
        raise ConnectError("FRM-DEST-1001", "network", "one address only", "descriptor")
    protocol = (protocols[0] if protocols else "tcp").lower()
    if protocol not in ("tcp", "tcps"):
        raise ConnectError("FRM-DEST-1001", "network", "protocol not allowed", "descriptor")
    port = ports[0] if ports else "1521"
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ConnectError("FRM-DEST-1001", "network", "port", "descriptor")
    service, sid = values.get("SERVICE_NAME", []), values.get("SID", [])
    if len(service) + len(sid) != 1 or not _ORACLE_NAME.fullmatch((service or sid)[0]):
        raise ConnectError("FRM-DEST-1005", "database", "service name", "descriptor")
    return {"host": hosts[0], "port": int(port), "protocol": protocol,
            **({"service_name": service[0]} if service else {"sid": sid[0]})}


def endpoint(target: Target) -> tuple[str, int]:
    """The database's own (host, port), as the customer typed it (descriptors parsed)."""
    s = target.settings
    if target.engine == "oracle" and s.get("connect_by") == "descriptor":
        parsed = oracle_descriptor(str(s.get("descriptor") or ""))
        return parsed["host"], parsed["port"]
    try:
        return str(s.get("host") or ""), int(s.get("port") or 0)
    except (TypeError, ValueError):
        raise ConnectError("FRM-DEST-1001", "network", "port") from None


def first_hop(target: Target) -> tuple[str, int]:
    """Where Formalie's server connects first: the SSH server, or the database."""
    s = target.settings
    if s.get("ssh"):
        try:
            return str(s.get("ssh_host") or ""), int(s.get("ssh_port") or 22)
        except (TypeError, ValueError):
            raise ConnectError("FRM-DEST-1004", "ssh", "port") from None
    return endpoint(target)


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

def host_key_of(connection: Any) -> str | None:
    key = connection.get_server_host_key()
    return key.get_fingerprint("sha256") if key is not None else None


def check_host_key(target: Target, hop: str, seen: str | None) -> None:
    """Pinned SSH host keys, kept as "host:port SHA256:...": a key other than the one pinned for this SSH server is
    refused before anything else is sent. A pin for another server (the SSH settings changed) doesn't count; the
    next successful test pins the new one."""
    target.seen_host_key = f"{hop} {seen}" if seen else None
    pinned = target.host_key or ""
    if pinned.partition(" ")[0] == hop and pinned != target.seen_host_key:
        raise ConnectError("FRM-DEST-1004", "ssh", "the SSH server's host key changed", "host_key_changed")


@asynccontextmanager
async def tunnel(target: Target) -> AsyncIterator[tuple[str, int]]:
    """The (address, port) to connect the driver to: the database's checked address, or the local end of an SSH
    tunnel (the SSH server's address is checked; the database behind it may be on the customer's private network)."""
    s = target.settings
    host, port = endpoint(target)
    if not s.get("ssh"):
        yield await resolve(host, port), port
        return
    import asyncssh

    ssh_host, ssh_port = first_hop(target)
    address = await resolve(ssh_host, ssh_port, "ssh")
    try:
        key = asyncssh.import_private_key(target.secrets.get("ssh_private_key", ""), target.secrets.get("ssh_passphrase") or None)
        # known_hosts=None: the key is checked against the pinned fingerprint right after the handshake, before any
        # port is forwarded (a client key only signs this session, so nothing reusable has left yet)
        connection = await asyncio.wait_for(asyncssh.connect(
            address, ssh_port, username=str(s.get("ssh_username") or ""), client_keys=[key],
            known_hosts=None, agent_path=None, config=None), target.timeout)
    except TimeoutError:
        raise ConnectError("FRM-DEST-1004", "ssh", "ssh timed out") from None
    except (asyncssh.Error, OSError, ValueError) as error:
        raise ConnectError("FRM-DEST-1004", "ssh", str(error)) from None
    try:
        check_host_key(target, f"{ssh_host.strip().strip('[]').rstrip('.').lower()}:{ssh_port}", host_key_of(connection))
        listener = await connection.forward_local_port("127.0.0.1", 0, host, port)
        try:
            yield "127.0.0.1", listener.get_port()
        finally:
            listener.close()
    finally:
        connection.close()


# ── TLS ─────────────────────────────────────────────────────────────────────────

def _tls_context(target: Target, verify: bool, check_name: bool) -> ssl.SSLContext:
    """A TLS context from the connection's certificates (they are written to a private temporary folder only
    for as long as the context is built), naming the database's host for SNI and the name check whatever address
    the driver connects to."""
    context = named_context(_tls_name(target))
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

    async def limit(self, seconds: float) -> None:
        """A time limit on every statement from now on (answers FRM-DEST-1011 when over it)."""

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

    async def limit(self, seconds: float) -> None:
        await self.raw.execute(f"SET statement_timeout = {int(seconds * 1000)}")

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

    async def limit(self, seconds: float) -> None:
        statement = (f"SET SESSION max_statement_time = {seconds:g}" if self.engine == "mariadb"
                     else f"SET SESSION MAX_EXECUTION_TIME = {int(seconds * 1000)}")
        try:
            async with self.raw.cursor() as cursor:
                await cursor.execute(statement)
        except Exception:  # noqa: BLE001 (older servers without it: the driver's own time-out still applies)
            pass

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

    async def limit(self, seconds: float) -> None:
        try:
            self.raw._conn.query_timeout = max(1, int(seconds))  # pymssql's command time-out
        except Exception:  # noqa: BLE001
            pass

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

    async def limit(self, seconds: float) -> None:
        self.raw.call_timeout = int(seconds * 1000)

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


def _tls_name(target: Target) -> str | None:
    try:
        name = endpoint(target)[0].strip().strip("[]").rstrip(".")
    except ConnectError:
        return None
    return name or None


_INSTANCE = re.compile(r"^[A-Za-z0-9_$-]{1,32}$")


async def _open(target: Target, host: str, port: int) -> Connection:
    """`host` is always an address: the checked one, or the local end of the tunnel."""
    s, secrets, timeout = target.settings, target.secrets, target.timeout
    engine = target.engine
    if engine == "postgresql":
        import asyncpg

        mode = str(s.get("ssl_mode") or "require")
        ssl_arg: Any = {"disable": False, "allow": "allow", "prefer": "prefer"}.get(mode)
        if mode in ("require", "verify-ca", "verify-full"):
            ssl_arg = _tls_context(target, verify=mode != "require", check_name=mode == "verify-full")
        # A password is always passed (empty when none), so asyncpg never reads PGPASSWORD or a .pgpass file
        raw = await asyncpg.connect(host=host, port=port, user=str(s.get("username") or ""),
                                    password=secrets.get("password") or "", database=database_name_of(engine, s),
                                    ssl=ssl_arg, timeout=timeout, command_timeout=60,
                                    target_session_attrs=str(s.get("target_session_attrs") or "any"),
                                    server_settings={"application_name": "Formalie"})
        return _Postgres(raw)
    if engine in ("mysql", "mariadb"):
        from app.modules.data_sources.drivers import open_mysql

        mode = str(s.get("ssl_mode") or "required")
        context = None
        if mode not in ("disabled", "preferred"):
            context = _tls_context(target, verify=mode in ("verify_ca", "verify_identity"), check_name=mode == "verify_identity")
        # No LOCAL INFILE, no multiple statements per query (drivers.py)
        raw = await open_mysql(host=host, port=port, user=str(s.get("username") or ""),
                               password=secrets.get("password") or "", db=database_name_of(engine, s),
                               charset=str(s.get("charset") or "utf8mb4"), ssl=context, connect_timeout=timeout,
                               autocommit=False, init_command=f"SET time_zone = '{_tz(s)}'")
        return _MySQL(raw, engine)
    if engine == "sqlserver":
        if s.get("auth") not in (None, "", "sql"):
            raise ConnectError("FRM-DEST-1002", "sign_in", "Microsoft Entra sign-in is not available yet")
        import pymssql

        instance = str(s.get("instance") or "")
        if instance and not _INSTANCE.fullmatch(instance):
            raise ConnectError("FRM-DEST-1001", "network", "instance name")
        server = host if not instance or s.get("ssh") else f"{host}\\{instance}"

        def connect() -> Any:
            return pymssql.connect(server=server, port=str(port), user=str(s.get("username") or ""),
                                   password=secrets.get("password") or "", database=database_name_of(engine, s),
                                   login_timeout=int(timeout), timeout=60, appname="Formalie", autocommit=False)
        return _Threaded(await asyncio.to_thread(connect), engine, "%s")
    if engine == "oracle":
        import oracledb

        # Formalie writes the whole descriptor: one address (the checked one), a service name or SID, nothing else
        if s.get("connect_by") == "descriptor":
            parsed = oracle_descriptor(str(s.get("descriptor") or ""))
            protocol, by_sid = parsed["protocol"], "sid" in parsed
            name = str(parsed.get("sid") if by_sid else parsed.get("service_name"))
        else:
            protocol = "tcp" if s.get("protocol") == "tcp" else "tcps"
            by_sid = s.get("connect_by") == "sid"
            name = str(s.get("sid") or "") if by_sid else database_name_of(engine, s)
        if not _ORACLE_NAME.fullmatch(name):
            raise ConnectError("FRM-DEST-1005", "database", "service name")
        service = f"(SID={name})" if by_sid else f"(SERVICE_NAME={name})"
        address = f"[{host}]" if ":" in host else host
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL={protocol})(HOST={address})(PORT={int(port)}))(CONNECT_DATA={service}))"
        tls: dict[str, Any] = {}
        if protocol == "tcps":
            # The name check is the context's (on the host name, not on the address connected to)
            tls = {"ssl_context": _tls_context(target, verify=True, check_name=bool(s.get("ssl_server_dn_match", True))),
                   "ssl_server_dn_match": False}
        params = oracledb.ConnectParams(tcp_connect_timeout=timeout, **tls)
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

"""Security review B17: C1 (a rogue MySQL server asking for a local file), H1 (one blocklist, pinned addresses,
Oracle descriptors, SSH host keys), M7 (reads that hide changes) and M13 (capped outgoing replies). No database
needed: a fake MySQL server runs on this machine."""

from __future__ import annotations

import asyncio
import ssl
import struct
from typing import Any

import httpx
import pytest

from app.core import outbound
from app.core.config import get_settings
from app.modules.data_sources import connect as C
from app.modules.data_sources.drivers import mysql_guard_installed, named_context, open_mysql
from app.modules.data_sources.sql_guard import read_is_safe

CLIENT_LOCAL_FILES, CLIENT_MULTI_STATEMENTS = 128, 1 << 16


# ── C1: the fake MySQL server ───────────────────────────────────────────────────

class RogueMySQL:
    """Answers the handshake, accepts any password, then answers the first query with LOAD DATA LOCAL INFILE for
    `wanted`, and records what the client sends back."""

    def __init__(self, wanted: str) -> None:
        self.wanted = wanted
        self.client_flags = 0
        self.after_request: list[bytes] = []
        self.done = asyncio.Event()

    @staticmethod
    def packet(seq: int, payload: bytes) -> bytes:
        return struct.pack("<I", len(payload))[:3] + bytes([seq]) + payload

    @staticmethod
    async def read(reader: asyncio.StreamReader) -> tuple[int, bytes]:
        head = await reader.readexactly(4)
        size = int.from_bytes(head[:3], "little")
        return head[3], await reader.readexactly(size)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            caps = 1 | 4 | 512 | 8192 | 32768 | (1 << 19) | CLIENT_LOCAL_FILES | CLIENT_MULTI_STATEMENTS
            greeting = (b"\x0a" + b"8.0.0-rogue\x00" + struct.pack("<I", 7) + b"abcdefgh" + b"\x00"
                        + struct.pack("<H", caps & 0xFFFF) + b"\x21" + struct.pack("<H", 2)
                        + struct.pack("<H", caps >> 16) + b"\x15" + b"\x00" * 10 + b"ijklmnopqrst" + b"\x00"
                        + b"mysql_native_password\x00")
            writer.write(self.packet(0, greeting))
            _, answer = await self.read(reader)
            self.client_flags = struct.unpack("<I", answer[:4])[0]
            writer.write(self.packet(2, b"\x00\x00\x00\x02\x00\x00\x00"))  # OK: signed in
            await writer.drain()
            await self.read(reader)  # the first query (SET time_zone ...)
            writer.write(self.packet(1, b"\xfb" + self.wanted.encode()))  # "send me this file"
            await writer.drain()
            try:
                while True:
                    _, payload = await asyncio.wait_for(self.read(reader), 2)
                    self.after_request.append(payload)
                    if payload == b"":
                        writer.write(self.packet(3, b"\x00\x00\x00\x02\x00\x00\x00"))
                        await writer.drain()
                        break
            except (asyncio.IncompleteReadError, TimeoutError):
                pass
        finally:
            self.done.set()
            writer.close()


async def test_a_rogue_mysql_server_gets_no_file(tmp_path) -> None:  # noqa: ANN001
    secret = tmp_path / "secret.env"
    secret.write_text("FERNET_KEYS=do-not-leak")
    rogue = RogueMySQL(str(secret))
    server = await asyncio.start_server(rogue.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    opened: list[str] = []
    real_open = open

    def spy(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    import builtins

    builtins.open, saved = spy, builtins.open
    try:
        with pytest.raises(Exception) as refused:
            await open_mysql(host="127.0.0.1", port=port, user="u", password="p", db=None, connect_timeout=3,
                             autocommit=False, init_command="SET time_zone = '+00:00'")
        await asyncio.wait_for(rogue.done.wait(), 3)
    finally:
        builtins.open = saved
        server.close()
        await server.wait_closed()
    assert "LOCAL INFILE refused" in str(refused.value)
    assert str(secret) not in opened  # nothing was opened...
    assert rogue.after_request == [b""]  # ...and only an empty file went back
    assert not rogue.client_flags & CLIENT_LOCAL_FILES and not rogue.client_flags & CLIENT_MULTI_STATEMENTS
    assert mysql_guard_installed()


# ── H1: one blocklist, checked and pinned addresses ─────────────────────────────

@pytest.mark.parametrize("address", [
    "10.0.0.5", "172.16.0.1", "192.168.1.1", "127.0.0.1", "169.254.169.254", "100.64.0.1", "0.0.0.0", "224.0.1.1",
    "198.18.0.1", "192.0.0.8", "192.88.99.1", "192.0.2.1", "203.0.113.9", "240.0.0.1", "::1", "fe80::1", "fd00:ec2::254",
    "ff0e::1", "2002:7f00:1::", "64:ff9b::7f00:1", "::ffff:10.0.0.1", "2001::1", "not-an-ip"])
def test_one_blocklist_refuses_everything_not_public(address: str) -> None:
    assert outbound.blocked(address)


@pytest.mark.parametrize("address", ["8.8.8.8", "93.184.215.14", "2606:4700::1111", "::ffff:8.8.8.8"])
def test_public_addresses_pass(address: str) -> None:
    assert not outbound.blocked(address)


def test_local_flags_count_only_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    for env, allowed in (("development", True), ("test", True), ("staging", False), ("production", False)):
        monkeypatch.setattr(get_settings(), "app_env", env)
        assert outbound.local_allowed(True) is allowed
    assert outbound.local_allowed(False) is False


@pytest.fixture
def dns(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    answers: dict[str, list[str]] = {}

    async def resolve(host: str, port: int) -> list[str]:
        return answers[host]
    monkeypatch.setattr(outbound, "resolver", resolve)
    monkeypatch.setattr(get_settings(), "datasources_allow_local", False)
    return answers


async def test_private_networks_and_rebinding_are_refused(dns: dict[str, list[str]]) -> None:
    dns.update({"inside.example": ["10.0.0.5"], "mixed.example": ["93.184.215.14", "127.0.0.1"],
                "public.example": ["93.184.215.14"]})
    for host in ("inside.example", "mixed.example", "10.0.0.5"):
        dns.setdefault("10.0.0.5", ["10.0.0.5"])
        with pytest.raises(C.ConnectError) as error:
            await C.resolve(host, 5432)
        assert error.value.code == "FRM-DEST-1001"
    assert await C.resolve("public.example", 5432) == "93.184.215.14"


async def test_the_driver_gets_the_checked_address_and_tls_the_name(dns: dict[str, list[str]],
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    dns["db.example.com"] = ["93.184.215.14"]
    seen: dict[str, Any] = {}

    async def fake_open(target: C.Target, host: str, port: int) -> Any:
        seen.update(host=host, port=port, tls=C._tls_context(target, verify=True, check_name=True))

        class Done(C.Connection):
            async def close(self) -> None:
                pass
        return Done()
    monkeypatch.setattr(C, "_open", fake_open)
    target = C.Target("postgresql", {"host": "db.example.com", "port": 5432, "ssl_mode": "verify-full"})
    async with C.connect(target):
        pass
    assert seen["host"] == "93.184.215.14" and seen["port"] == 5432  # never the name: no second lookup
    bio = seen["tls"].wrap_bio(ssl.MemoryBIO(), ssl.MemoryBIO(), server_hostname=seen["host"])
    assert bio.server_hostname == "db.example.com"  # SNI and the certificate check use the name


def test_named_context_keeps_the_name() -> None:
    context = named_context("db.example.com")
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert context.wrap_bio(ssl.MemoryBIO(), ssl.MemoryBIO(), server_hostname="203.0.113.1").server_hostname == "db.example.com"


@pytest.mark.parametrize("descriptor", [
    "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=tcp)(HOST=public.example)(PORT=1521))"
    "(ADDRESS=(PROTOCOL=tcp)(HOST=127.0.0.1)(PORT=6432)))(CONNECT_DATA=(SERVICE_NAME=orcl)))",
    "(DESCRIPTION=(ADDRESS=(HTTPS_PROXY=proxy.example)(PROTOCOL=tcps)(HOST=db.example)(PORT=2484))"
    "(CONNECT_DATA=(SERVICE_NAME=orcl)))",
    "(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)(HOST=db.example)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=orcl))"
    "(SECURITY=(MY_WALLET_DIRECTORY=/etc/secret)))",
    "(DESCRIPTION=(ADDRESS=(PROTOCOL=ipc)(KEY=x)(HOST=db.example))(CONNECT_DATA=(SERVICE_NAME=orcl)))",
    "(DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=db.example)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=orcl)(HOST=x)))",
    "db.example:1521/orcl",
])
def test_oracle_descriptors_with_more_than_one_address_or_extras_are_refused(descriptor: str) -> None:
    with pytest.raises(C.ConnectError) as error:
        C.oracle_descriptor(descriptor)
    assert error.value.code == "FRM-DEST-1001" and error.value.reason == "descriptor"


def test_a_plain_oracle_descriptor_is_read() -> None:
    assert C.oracle_descriptor("(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=db.example.com)(PORT=2484))"
                               "(CONNECT_DATA=(SERVICE_NAME=orcl.example)))") == {
        "host": "db.example.com", "port": 2484, "protocol": "tcps", "service_name": "orcl.example"}
    with pytest.raises(C.ConnectError) as error:
        C.oracle_descriptor("(DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=d)(PORT=1))(CONNECT_DATA=(SERVICE_NAME=a)(SID=b)))")
    assert error.value.code == "FRM-DEST-1005"
    target = C.Target("oracle", {"connect_by": "descriptor", "ssh": False, "descriptor":
                                 "(DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=db.example)(PORT=1522))(CONNECT_DATA=(SID=X)))"})
    assert C.first_hop(target) == ("db.example", 1522)


def test_ssh_host_keys_are_pinned() -> None:
    target = C.Target("postgresql", {}, host_key="ssh.example.com:22 SHA256:old")
    with pytest.raises(C.ConnectError) as error:
        C.check_host_key(target, "ssh.example.com:22", "SHA256:new")
    assert error.value.code == "FRM-DEST-1004" and error.value.details() == [
        {"field": "ssh_host", "message": "host_key_changed"}]
    C.check_host_key(target, "ssh.example.com:22", "SHA256:old")  # the same key: fine
    C.check_host_key(target, "other.example.com:22", "SHA256:new")  # another server (settings changed): re-pinned later
    assert target.seen_host_key == "other.example.com:22 SHA256:new"
    fresh = C.Target("postgresql", {})
    C.check_host_key(fresh, "ssh.example.com:22", "SHA256:first")
    assert fresh.seen_host_key == "ssh.example.com:22 SHA256:first"


# ── M7: reads that would run changes ────────────────────────────────────────────

@pytest.mark.parametrize(("engine", "sql", "safe"), [
    ("mysql", "SELECT * FROM t", True),
    ("mysql", "SHOW TABLES # '\n; COMMIT; UPDATE t SET a = 1", False),
    ("mariadb", "SELECT 1 /*!; UPDATE t SET a = 1 */", False),
    ("mysql", "SELECT 'a\\'; DELETE FROM t; -- '", False),
    ("mysql", "SELECT * FROM t INTO OUTFILE '/tmp/x'", False),
    ("mysql", "SELECT '#' AS hash, `#` FROM t", True),
    ("sqlserver", "SELECT 1 UPDATE dbo.t SET a = 1 COMMIT", False),
    ("sqlserver", "SELECT 1 EXEC sp_configure", False),
    ("sqlserver", "SELECT CASE WHEN a = 1 THEN 2 END AS [update] FROM t WHERE b = 'DELETE'", True),
    ("sqlserver", "SELECT 1 /* a /* b */ UPDATE t SET a = 1 */", True),
    ("sqlserver", "SELECT 1 /* a /* b */ */ UPDATE t SET a = 1", False),
    ("postgresql", "SELECT E'\\'' ; DELETE FROM t", False),
    ("postgresql", "SELECT 1 /* a /* b */ ; DELETE FROM t */", True),
    ("postgresql", "SELECT $x$ ; DELETE $x$", True),
    ("postgresql", "WITH x AS (SELECT 1) SELECT * FROM x;", True),
    ("oracle", "SELECT * FROM dual", True),
])
def test_reads_that_hide_changes_are_not_reads(engine: str, sql: str, safe: bool) -> None:
    assert read_is_safe(engine, sql) is safe


# ── M13: outgoing replies are capped ────────────────────────────────────────────

async def test_outgoing_replies_have_a_size_cap_and_a_total_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/slow":
            await asyncio.sleep(5)
        size = 2_000_000 if request.url.path == "/big" else 10
        return httpx.Response(200, content=b"x" * size, headers={"content-type": "text/plain"})
    monkeypatch.setattr(outbound, "transport", httpx.MockTransport(handler))
    small = await outbound.http("GET", "https://idp.example.com/ok")
    assert small is not None and small.status_code == 200 and small.text == "x" * 10
    assert await outbound.http("GET", "https://idp.example.com/big") is None
    assert await outbound.http("GET", "https://idp.example.com/slow", total=0.2) is None


def test_export_file_names_always_fit_the_header() -> None:
    """B17 L12: quotes, semicolons and non-Latin names can't break Content-Disposition."""
    from app.core.disposition import disposition

    header = disposition('Klienți "x";.csv')
    assert header == "attachment; filename=\"Klien_i _x__.csv\"; filename*=UTF-8''Klien%C8%9Bi%20%22x%22%3B.csv"
    header.encode("latin-1")

"""Driver hardening for customers' databases (security review B17: C1, H1, M7). Formalie chooses the near end of
these connections, the customer chooses the far end, so the far end is never trusted:

- **MySQL / MariaDB (aiomysql):** a server may answer any query with a LOAD DATA LOCAL INFILE request naming a file,
  and aiomysql would open that file on Formalie's server and send it (whatever `local_infile` says: that only stops
  the client from advertising the feature). `install_mysql_guard()` replaces the handler: an empty reply is sent,
  nothing is opened, and the query fails. It checks the driver still has the shape it patches, and refuses to run
  otherwise, so an aiomysql upgrade can never silently undo it.
- **Multiple statements:** aiomysql always asks the server for CLIENT_MULTI_STATEMENTS. `SafeMySQLConnection` drops
  it (and CLIENT_LOCAL_FILES), so one query is one statement whatever the text hides in comments.
- **TLS to a pinned address:** drivers connect to the address Formalie checked (never a name resolved again, so DNS
  rebinding can't swap it), while `NamedTLSContext` keeps the host name for SNI and certificate checks.
"""

from __future__ import annotations

import ssl
from typing import Any

_GUARDED = False


class LocalInfileRefused(Exception):
    """The server asked for a local file."""


def install_mysql_guard() -> None:
    """Refuse LOAD DATA LOCAL INFILE requests in aiomysql (once per process)."""
    global _GUARDED
    if _GUARDED:
        return
    from aiomysql import connection as driver

    result_class = getattr(driver, "MySQLResult", None)
    sender_class = getattr(driver, "LoadLocalFile", None)
    if result_class is None or not hasattr(result_class, "_read_load_local_packet") or sender_class is None \
            or not hasattr(sender_class, "send_data"):
        # The driver changed shape: refuse to run rather than run unguarded.
        raise RuntimeError("aiomysql changed: the LOCAL INFILE guard can't be installed (app/modules/data_sources/drivers.py)")

    async def refuse_local_file(self: Any, first_packet: Any) -> None:
        connection = self.connection
        connection.write_packet(b"")  # an empty file: nothing is opened, nothing is read
        try:
            await connection._read_packet()  # the server's answer to the empty file (an error or OK)
        except Exception:  # noqa: BLE001 (the query fails below either way)
            pass
        raise driver.OperationalError(2000, "LOAD DATA LOCAL INFILE refused by Formalie")

    async def never_send(self: Any) -> None:
        raise driver.OperationalError(2000, "LOAD DATA LOCAL INFILE refused by Formalie")

    result_class._read_load_local_packet = refuse_local_file
    sender_class.send_data = never_send
    _GUARDED = True


def mysql_guard_installed() -> bool:
    from aiomysql import connection as driver

    return _GUARDED and driver.MySQLResult._read_load_local_packet.__name__ == "refuse_local_file"


def _safe_connection_class() -> type:
    import aiomysql
    from pymysql.constants import CLIENT

    class SafeMySQLConnection(aiomysql.Connection):  # type: ignore[misc, name-defined]
        """No multiple statements per query, no local files."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["local_infile"] = False
            kwargs["read_default_file"] = None
            super().__init__(*args, **kwargs)
            self.client_flag &= ~(CLIENT.MULTI_STATEMENTS | CLIENT.LOCAL_FILES)

        async def _request_authentication(self) -> None:
            self.client_flag &= ~(CLIENT.MULTI_STATEMENTS | CLIENT.LOCAL_FILES)
            await super()._request_authentication()

    return SafeMySQLConnection


async def open_mysql(**kwargs: Any) -> Any:
    """aiomysql.connect(**kwargs), with the guard and without multiple statements."""
    install_mysql_guard()
    connection = _safe_connection_class()(**kwargs)
    try:
        await connection._connect()
    except BaseException:
        connection.close()
        raise
    return connection


class NamedTLSContext(ssl.SSLContext):
    """An SSL context that always uses `tls_name` for SNI and the certificate's name check, whatever address the
    driver connected to (it passes the address it was given, which is the checked IP)."""

    tls_name: str | None = None

    def wrap_socket(self, sock: Any, server_side: bool = False, do_handshake_on_connect: bool = True,  # type: ignore[override]
                    suppress_ragged_eofs: bool = True, server_hostname: str | None = None, session: Any = None) -> Any:
        return super().wrap_socket(sock, server_side, do_handshake_on_connect, suppress_ragged_eofs,
                                   self.tls_name or server_hostname, session)

    def wrap_bio(self, incoming: Any, outgoing: Any, server_side: bool = False,  # type: ignore[override]
                 server_hostname: str | None = None, session: Any = None) -> Any:
        return super().wrap_bio(incoming, outgoing, server_side, self.tls_name or server_hostname, session)


def named_context(name: str | None) -> NamedTLSContext:
    """Like ssl.create_default_context(), pinned to `name` (None: the address the driver uses)."""
    context = NamedTLSContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    context.tls_name = name or None
    return context

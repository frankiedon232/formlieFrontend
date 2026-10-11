"""Connection settings per database engine and what Formalie does on a connected database (ports of
shared/utils/datasources/engines.ts and permissions.ts), held to the frontend's answers by
tests/parity/test_datasource_rules.py. One catalogue drives the fields, their checks on both sides and the
connection's summary; secrets never come back from the API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core import js

DB_ENGINES = ("mysql", "postgresql", "sqlserver", "oracle", "mariadb")
Settings = dict[str, Any]


@dataclass(frozen=True)
class EngineField:
    key: str
    step: str
    type: str
    default: Any = None
    options: tuple[str, ...] = ()
    required: bool = False
    when: Callable[[Settings], bool] | None = field(default=None, compare=False)
    format: str | None = None

    @property
    def secret(self) -> bool:
        return self.type in ("secret", "certificate")


def _same(a: Any, b: Any) -> bool:
    """JavaScript's === for settings values (true is not 1, "true" is not true)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return type(a) is type(b) and a == b or (isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b)


def _is(key: str, *values: Any) -> Callable[[Settings], bool]:
    return lambda s: any(_same(v, s.get(key, js.UNDEFINED)) for v in values)


def _not(key: str, *values: str) -> Callable[[Settings], bool]:
    return lambda s: not any(_same(v, s.get(key, js.UNDEFINED)) for v in values)


def _host(when: Callable[[Settings], bool] | None = None) -> EngineField:
    return EngineField("host", "server", "text", required=True, format="host", when=when)


def _port(value: int, when: Callable[[Settings], bool] | None = None) -> EngineField:
    return EngineField("port", "server", "number", default=value, required=True, format="port", when=when)


def _timeout(value: int) -> EngineField:
    return EngineField("connect_timeout", "server", "number", default=value, format="seconds")


def _username(when: Callable[[Settings], bool] | None = None) -> EngineField:
    return EngineField("username", "signin", "text", required=True, when=when)


def _password(when: Callable[[Settings], bool] | None = None) -> EngineField:
    return EngineField("password", "signin", "secret", required=True, when=when)


def _client_certificate(when: Callable[[Settings], bool]) -> list[EngineField]:
    return [EngineField("client_certificate", "security", "certificate", format="pem", when=when),
            EngineField("client_key", "security", "certificate", format="pem", when=when)]


_SSH = [
    EngineField("ssh", "security", "switch", default=False),
    EngineField("ssh_host", "security", "text", required=True, format="host", when=_is("ssh", True)),
    EngineField("ssh_port", "security", "number", default=22, required=True, format="port", when=_is("ssh", True)),
    EngineField("ssh_username", "security", "text", required=True, when=_is("ssh", True)),
    EngineField("ssh_private_key", "security", "certificate", required=True, format="pem", when=_is("ssh", True)),
    EngineField("ssh_passphrase", "security", "secret", when=_is("ssh", True)),
]
_MYSQL_TLS = ("disabled", "preferred", "required", "verify_ca", "verify_identity")


def _mysql_like() -> list[EngineField]:
    return [
        _host(), _port(3306), EngineField("database", "server", "text", required=True),
        EngineField("charset", "server", "select", options=("utf8mb4", "utf8mb3", "latin1"), default="utf8mb4"),
        EngineField("time_zone", "server", "text", default="+00:00"), _timeout(10), _username(), _password(),
        EngineField("ssl_mode", "security", "select", options=_MYSQL_TLS, default="required"),
        EngineField("ca_certificate", "security", "certificate", required=True, format="pem",
                    when=_is("ssl_mode", "verify_ca", "verify_identity")),
        *_client_certificate(_not("ssl_mode", "disabled")), *_SSH,
    ]


ENGINE_FIELDS: dict[str, list[EngineField]] = {
    "mysql": _mysql_like(),
    "mariadb": _mysql_like(),
    "postgresql": [
        _host(), _port(5432), EngineField("database", "server", "text", required=True),
        EngineField("target_session_attrs", "server", "select",
                    options=("any", "read-write", "read-only", "primary", "standby", "prefer-standby"), default="any"),
        _timeout(10), _username(), _password(),
        EngineField("ssl_mode", "security", "select", options=("disable", "allow", "prefer", "require", "verify-ca",
                                                                "verify-full"), default="require"),
        EngineField("ca_certificate", "security", "certificate", required=True, format="pem",
                    when=_is("ssl_mode", "verify-ca", "verify-full")),
        *_client_certificate(_not("ssl_mode", "disable")), *_SSH,
    ],
    "sqlserver": [
        _host(), EngineField("instance", "server", "text", format="identifier"), _port(1433),
        EngineField("database", "server", "text", required=True),
        EngineField("application_intent", "server", "select", options=("read_write", "read_only"), default="read_write"),
        EngineField("multi_subnet_failover", "server", "switch", default=False), _timeout(15),
        EngineField("auth", "signin", "select", options=("sql", "entra_password", "entra_service_principal"), default="sql"),
        _username(_not("auth", "entra_service_principal")), _password(_not("auth", "entra_service_principal")),
        EngineField("tenant_id", "signin", "text", required=True, format="uuid", when=_is("auth", "entra_service_principal")),
        EngineField("client_id", "signin", "text", required=True, format="uuid", when=_is("auth", "entra_service_principal")),
        EngineField("client_secret", "signin", "secret", required=True, when=_is("auth", "entra_service_principal")),
        EngineField("encrypt", "security", "select", options=("mandatory", "strict", "optional"), default="mandatory"),
        EngineField("trust_server_certificate", "security", "switch", default=False, when=_is("encrypt", "mandatory")),
        EngineField("host_name_in_certificate", "security", "text", format="host", when=_not("encrypt", "optional")),
        EngineField("ca_certificate", "security", "certificate", format="pem", when=_not("encrypt", "optional")),
        *_SSH,
    ],
    "oracle": [
        EngineField("connect_by", "server", "select", options=("service_name", "sid", "descriptor"), default="service_name"),
        _host(_not("connect_by", "descriptor")), _port(1521, _not("connect_by", "descriptor")),
        EngineField("service_name", "server", "text", required=True, when=_is("connect_by", "service_name")),
        EngineField("sid", "server", "text", required=True, format="identifier", when=_is("connect_by", "sid")),
        EngineField("descriptor", "server", "text", required=True, when=_is("connect_by", "descriptor")),
        _timeout(10), _username(), _password(),
        EngineField("protocol", "security", "select", options=("tcps", "tcp"), default="tcps",
                    when=_not("connect_by", "descriptor")),
        EngineField("network_encryption", "security", "select", options=("required", "requested", "accepted"),
                    default="required", when=lambda s: s.get("protocol") == "tcp" and s.get("connect_by") != "descriptor"),
        EngineField("ca_certificate", "security", "certificate", format="pem",
                    when=lambda s: s.get("protocol") != "tcp" or s.get("connect_by") == "descriptor"),
        EngineField("ssl_server_dn_match", "security", "switch", default=True,
                    when=lambda s: s.get("protocol") != "tcp" or s.get("connect_by") == "descriptor"),
        *_SSH,
    ],
}


def fields_for(engine: str, settings: Settings, step: str | None = None) -> list[EngineField]:
    return [f for f in ENGINE_FIELDS[engine] if (not step or f.step == step) and (f.when is None or f.when(settings))]


def default_settings(engine: str) -> Settings:
    out: Settings = {}
    for f in ENGINE_FIELDS[engine]:
        if f.secret:
            continue
        out[f.key] = f.default if f.default is not None else (False if f.type == "switch" else 0 if f.type == "number" else "")
    return out


def clean_settings(engine: str, given: Settings) -> Settings:
    """Only this engine's non-secret keys (anything else in a request is dropped)."""
    base = default_settings(engine)
    for key in list(base):
        value = given.get(key, js.UNDEFINED)
        if js.nullish(value):
            continue
        kind = base[key]
        if isinstance(kind, bool):
            base[key] = value is True or value == "true"
        elif isinstance(kind, (int, float)):
            n = js.to_number(value)
            base[key] = int(n) if n == n and n.is_integer() and abs(n) < 2**53 else n
        else:
            base[key] = js.trim(js.to_string(value))
    return base


# ── Checks ──────────────────────────────────────────────────────────────────────

_HOST = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$", re.ASCII)
_IPV4 = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", re.ASCII)
_IPV6 = re.compile(r"^\[?[0-9A-Fa-f:.]+\]?$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]+-----[\s\S]+-----END [A-Z0-9 ]+-----")


def _identifier(text: str) -> bool:
    """/^[\\p{L}_][\\p{L}\\p{N}_$#@ .-]{0,127}$/u (code points)."""
    if not text or len(text) > 128:
        return False
    first, rest = text[0], text[1:]
    return (first.isalpha() or first == "_") and all(c.isalpha() or c.isnumeric() or c in "_$#@ .-" for c in rest)


def is_blocked_host(value: str) -> bool:
    """Formalie's servers never connect to themselves or to cloud metadata addresses (server-side request forgery).
    The connector repeats this on the resolved address."""
    host = re.sub(r"\.$", "", re.sub(r"^\[|\]$", "", js.trim(value).lower()))
    if host == "localhost" or host.endswith(".localhost") or host == "metadata.google.internal":
        return True
    if host in ("::1", "::") or host.startswith("fe80:") or host.startswith("::ffff:127."):
        return True
    ip = _IPV4.fullmatch(host)
    if not ip:
        return False
    a, b = int(ip.group(1)), int(ip.group(2))
    return a == 0 or a == 127 or (a == 169 and b == 254) or (a == 100 and 64 <= b <= 127) or a >= 224


def _integer_between(value: Any, low: int, high: int) -> bool:
    n = js.to_number(value)
    return n == n and n != float("inf") and n != float("-inf") and n.is_integer() and low <= n <= high


def _check_value(f: EngineField, value: Any) -> str | None:
    text = js.trim(value) if isinstance(value, str) else value
    if text == "" or js.nullish(text):
        return "required" if f.required else None
    name = js.to_string(text)
    if f.format == "host":
        if not _HOST.fullmatch(name) and not _IPV4.fullmatch(name) and not _IPV6.fullmatch(name):
            return "host"
        if _IPV4.fullmatch(name) and any(int(part) > 255 for part in name.split(".")):
            return "host"
        return "host_blocked" if is_blocked_host(name) else None
    if f.format == "port":
        return None if _integer_between(text, 1, 65535) else "port"
    if f.format == "seconds":
        return None if _integer_between(text, 1, 120) else "seconds"
    if f.format == "pem":
        return None if _PEM.search(name) else "pem"
    if f.format == "uuid":
        return None if _UUID.fullmatch(name) else "uuid"
    if f.format == "identifier":
        return None if _identifier(name) else "identifier"
    return None


def check_config(engine: str, settings: Settings, secrets: dict[str, str] | None = None,
                 secrets_set: list[str] | None = None, step: str | None = None) -> dict[str, str]:
    """Problems per field (`secrets_set`: secrets already stored for a saved connection, so empty keeps them)."""
    secrets, secrets_set = secrets or {}, secrets_set or []
    problems: dict[str, str] = {}
    for f in fields_for(engine, settings, step):
        if f.type in ("switch", "select"):
            continue
        if f.secret and not secrets.get(f.key) and f.key in secrets_set:
            continue
        problem = _check_value(f, secrets.get(f.key, js.UNDEFINED) if f.secret else settings.get(f.key, js.UNDEFINED))
        if problem:
            problems[f.key] = problem
    return problems


def clean_secrets(engine: str, settings: Settings, secrets: dict[str, Any] | None = None) -> dict[str, str]:
    """Only the secrets this engine and these settings use."""
    keys = {f.key for f in fields_for(engine, settings) if f.secret}
    return {k: v for k, v in (secrets or {}).items() if k in keys and isinstance(v, str) and js.trim(v) != ""}


def address_of(engine: str, settings: Settings) -> str:
    if engine == "oracle" and settings.get("connect_by") == "descriptor":
        descriptor = js.to_string(settings.get("descriptor") or "")
        host = re.search(r"HOST\s*=\s*([^)\s]+)", descriptor, re.IGNORECASE)
        port = re.search(r"PORT\s*=\s*(\d+)", descriptor, re.IGNORECASE)
        return f"{host.group(1)}{':' + port.group(1) if port else ''}" if host else ""
    instance = f"\\{settings['instance']}" if engine == "sqlserver" and settings.get("instance") else ""
    return f"{js.to_string(settings['host'])}{instance}:{js.to_string(settings.get('port', js.UNDEFINED))}" \
        if settings.get("host") else ""


def database_name_of(engine: str, settings: Settings) -> str:
    def text(key: str) -> str:
        value = settings.get(key, js.UNDEFINED)
        return "" if js.nullish(value) else js.to_string(value)
    if engine != "oracle":
        return text("database")
    if settings.get("connect_by") == "sid":
        return text("sid")
    if settings.get("connect_by") == "descriptor":
        found = re.search(r"SERVICE_NAME\s*=\s*([^)\s]+)", text("descriptor"), re.IGNORECASE)
        return found.group(1) if found else ""
    return text("service_name")


def default_schema_of(engine: str, settings: Settings) -> str:
    if engine in ("mysql", "mariadb"):
        value = settings.get("database", js.UNDEFINED)
        return "" if js.nullish(value) else js.to_string(value)
    if engine == "oracle":
        return js.to_string(settings.get("username") or "").upper()
    return "public" if engine == "postgresql" else "dbo"


def is_encrypted(engine: str, settings: Settings) -> bool:
    if engine in ("mysql", "mariadb"):
        return js.to_string(settings.get("ssl_mode", js.UNDEFINED)) not in ("disabled", "preferred")
    if engine == "postgresql":
        return js.to_string(settings.get("ssl_mode", js.UNDEFINED)) in ("require", "verify-ca", "verify-full")
    if engine == "sqlserver":
        return settings.get("encrypt") != "optional"
    return settings.get("connect_by") == "descriptor" or settings.get("protocol") != "tcp" \
        or settings.get("network_encryption") == "required"


# ── What Formalie does there (permissions.ts) ───────────────────────────────────

DB_OPERATIONS = [
    ("connect", "own", None), ("create_table", "own", None), ("own_rows", "own", None), ("alter_table", "own", None),
    ("create_index", "own", None), ("cancel", "own", None), ("read_schema", "read", None), ("row_counts", "read", None),
    ("read_rows", "read", None), ("insert", "write", None), ("update", "write", None), ("delete", "write", None),
    ("sequences", "write", ("postgresql", "oracle")), ("other_structure", "write", None),
]


def levels_for(access: dict[str, Any]) -> list[str]:
    other = access.get("other")
    return ["own", "read", "write"] if other == "read_write" else ["own", "read"] if other == "read" else ["own"]


def operations_for(engine: str, access: dict[str, Any]) -> list[dict[str, Any]]:
    levels = levels_for(access)
    return [{"key": key, "level": level, "needed": level in levels}
            for key, level, engines in DB_OPERATIONS if engines is None or engine in engines]


def has_tables_schema(engine: str) -> bool:
    return engine in ("postgresql", "sqlserver")


def tables_schema_of(engine: str, settings: Settings, access: dict[str, Any]) -> str:
    """Where Formalie's tables live (a schema; MySQL / MariaDB: the database)."""
    if engine == "postgresql":
        return access.get("tables_schema") or "public"
    if engine == "sqlserver":
        return access.get("tables_schema") or "formalie"
    if engine == "oracle":
        return js.to_string(settings.get("username") or "formalie_app").upper()
    return js.to_string(settings.get("database") or "")

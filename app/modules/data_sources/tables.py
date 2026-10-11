"""Response tables (shared/utils/datasources/tables.ts, values.ts): turning a form into a table on a connection,
matching a form to an existing table, checking the match, writing a response as a row, and typed text as a column's
value. Same answers as the frontend (tests/parity/test_table_rules.py).

    names    prefix + form name, lower snake case (Oracle upper case); columns from field keys; reserved words get a
             suffix; within each engine's length limit
    types    per field type and engine
    rows     ISO dates, numbers as numbers, choices by value or label, several values as JSON or "; "-joined text,
             files as their secure links
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Any

from app.core import js
from app.modules.responses.answers import answer_text

Column = dict[str, Any]
Field = dict[str, Any]

MAX_NAME = {"postgresql": 63, "mysql": 64, "mariadb": 64, "sqlserver": 128, "oracle": 128}

RESERVED = {
    "all", "and", "as", "asc", "between", "by", "case", "check", "column", "comment", "create", "date", "default", "delete",
    "desc", "distinct", "drop", "else", "end", "exists", "file", "for", "from", "grant", "group", "having", "in", "index",
    "insert", "into", "is", "join", "key", "level", "like", "limit", "number", "not", "null", "of", "on", "option", "or",
    "order", "primary", "references", "rows", "select", "session", "size", "table", "then", "to", "trigger", "uid", "union",
    "unique", "update", "user", "values", "view", "when", "where", "with",
}

META_COLUMNS = ("response_id", "submitted_at", "form_version", "language", "response_number", "respondent_email",
                "review_status")

_MARKS = re.compile("[̀-ͯ]")
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
_NOT_WORD = re.compile(r"[^a-z0-9]+")
_EDGE = re.compile(r"^_+|_+$")


def snake(text: str) -> str:
    """lower_snake_case, ASCII only (other letters dropped), never empty, never starting with a digit."""
    out = _MARKS.sub("", unicodedata.normalize("NFKD", text))
    out = _EDGE.sub("", _NOT_WORD.sub("_", _CAMEL.sub(r"\1_\2", out).lower()))
    return f"c_{out}" if out[:1].isdigit() and out[:1].isascii() else out


def _cased(engine: str, name: str) -> str:
    return name.upper() if engine == "oracle" else name


def table_name_for(engine: str, prefix: str, form_name: str) -> str:
    base = snake(form_name) or "form"
    return _cased(engine, re.sub(r"_+$", "", js.utf16_slice(f"{prefix}{base}", MAX_NAME[engine])))


def column_name_for(engine: str, key: str, taken: set[str]) -> str:
    """A column name for a field key, unique within `taken` (which it adds to)."""
    base = snake(key) or "answer"
    if base in RESERVED:
        base = f"{base}_value"
    base = base[: MAX_NAME[engine] - 3]
    name = base
    n = 2
    while name.lower() in taken:
        name = f"{base}_{n}"
        n += 1
    taken.add(name.lower())
    return _cased(engine, name)


TABLE_REST_MIN = 6
_REST = re.compile(r"[A-Za-z0-9_]+")


def check_table_rest(engine: str, prefix: str, rest: str) -> str | None:
    if not rest:
        return "required"
    if not _REST.fullmatch(rest):
        return "chars"
    if len(rest) < TABLE_REST_MIN:
        return "short"
    if js.utf16_len(prefix) + len(rest) > MAX_NAME[engine]:
        return "long"
    return None


def table_rest_max(engine: str, prefix: str) -> int:
    return MAX_NAME[engine] - js.utf16_len(prefix)


def normalise_table_rest(engine: str, text: str) -> str:
    joined = re.sub(f"[{js._WS}]+", "_", text)
    return joined.upper() if engine == "oracle" else joined.lower()


# ── Types ───────────────────────────────────────────────────────────────────────

TYPES: dict[str, dict[str, str]] = {
    "postgresql": {"short": "VARCHAR(1000)", "long": "TEXT", "code": "VARCHAR(320)", "decimal": "NUMERIC(18,4)", "integer": "INTEGER",
                   "date": "DATE", "time": "TIME", "datetime": "TIMESTAMPTZ", "boolean": "BOOLEAN", "json": "JSONB", "links": "JSONB",
                   "uuid": "UUID", "lang": "VARCHAR(35)", "state": "VARCHAR(16)"},
    "mysql": {"short": "VARCHAR(1000)", "long": "LONGTEXT", "code": "VARCHAR(320)", "decimal": "DECIMAL(18,4)", "integer": "INT",
              "date": "DATE", "time": "TIME", "datetime": "DATETIME(3)", "boolean": "TINYINT(1)", "json": "JSON", "links": "JSON",
              "uuid": "CHAR(36)", "lang": "VARCHAR(35)", "state": "VARCHAR(16)"},
    "mariadb": {"short": "VARCHAR(1000)", "long": "LONGTEXT", "code": "VARCHAR(320)", "decimal": "DECIMAL(18,4)", "integer": "INT",
                "date": "DATE", "time": "TIME", "datetime": "DATETIME(3)", "boolean": "TINYINT(1)", "json": "LONGTEXT",
                "links": "LONGTEXT", "uuid": "CHAR(36)", "lang": "VARCHAR(35)", "state": "VARCHAR(16)"},
    "sqlserver": {"short": "NVARCHAR(1000)", "long": "NVARCHAR(MAX)", "code": "NVARCHAR(320)", "decimal": "DECIMAL(18,4)",
                  "integer": "INT", "date": "DATE", "time": "TIME", "datetime": "DATETIMEOFFSET", "boolean": "BIT",
                  "json": "NVARCHAR(MAX)", "links": "NVARCHAR(MAX)", "uuid": "UNIQUEIDENTIFIER", "lang": "NVARCHAR(35)",
                  "state": "NVARCHAR(16)"},
    "oracle": {"short": "VARCHAR2(1000 CHAR)", "long": "CLOB", "code": "VARCHAR2(320 CHAR)", "decimal": "NUMBER(18,4)",
               "integer": "NUMBER(10)", "date": "DATE", "time": "VARCHAR2(8)", "datetime": "TIMESTAMP WITH TIME ZONE",
               "boolean": "NUMBER(1)", "json": "CLOB", "links": "CLOB", "uuid": "VARCHAR2(36)", "lang": "VARCHAR2(35 CHAR)",
               "state": "VARCHAR2(16 CHAR)"},
}

SEVERAL = {"checkbox", "multi_select", "ranking", "matrix", "date_range", "duration", "full_name", "address"}
FILES = {"file_upload", "image_upload", "signature"}
_CODE = {"email", "phone", "url", "domain", "ip_address", "mac_address", "iban", "bic", "color", "country", "language",
         "timezone", "currency_code"}
_KIND = {"long_text": "long", "rich_text": "long", **{t: "code" for t in _CODE},
         **{t: "decimal" for t in ("number", "currency", "percentage", "slider", "calculated")},
         "rating": "integer", "scale": "integer", "date": "date", "time": "time", "datetime": "datetime",
         "toggle": "boolean", "consent": "boolean"}


def kind_of_field(type_: str, multi: str) -> str:
    if type_ in SEVERAL:
        return "json" if multi == "json" else "long"
    if type_ in FILES:
        return "links" if multi == "json" else "long"
    return _KIND.get(type_, "short")


META_KIND = {"response_id": "uuid", "submitted_at": "datetime", "form_version": "integer", "language": "lang",
             "response_number": "integer", "respondent_email": "code", "review_status": "state"}


def column_type_for(engine: str, field: Field, multi: str) -> str:
    return TYPES[engine][kind_of_field(field["type"], multi)]


def meta_type_for(engine: str, meta: str) -> str:
    return TYPES[engine][META_KIND[meta]]


def _source_kind(column: Column) -> str | None:
    source = column.get("source")
    return source["kind"] if source else None


def typed_for_engine(engine: str, columns: list[Column], fields: list[Field], multi: str) -> list[Column]:
    """Columns of a table Formalie creates, with every type worked out for the engine (never taken from a request)."""
    by_key = {f["key"]: f for f in fields}
    out = []
    for column in columns:
        kind = _source_kind(column)
        if kind == "meta":
            out.append({**column, "type": meta_type_for(engine, column["source"]["key"])})
            continue
        field = by_key.get(column["source"]["key"]) if kind == "field" else None
        out.append({**column, "type": column_type_for(engine, field, multi)} if field else column)
    return out


def columns_for_form(engine: str, fields: list[Field], settings: dict[str, Any],
                     meta: tuple[str, ...] = ("response_id", "submitted_at", "form_version", "language")) -> list[Column]:
    taken: set[str] = set()
    out = [{"column": column_name_for(engine, key, taken), "type": meta_type_for(engine, key),
            "source": {"kind": "meta", "key": key}, "nullable": key not in ("response_id", "submitted_at"), "existing": False}
           for key in meta]
    out += [{"column": column_name_for(engine, f["key"], taken), "type": column_type_for(engine, f, settings["multi_value"]),
             "source": {"kind": "field", "key": f["key"]}, "nullable": True, "existing": False} for f in fields]
    return out


# ── SQL ─────────────────────────────────────────────────────────────────────────

def quote_name(engine: str, name: str) -> str:
    if engine in ("mysql", "mariadb"):
        return "`" + name.replace("`", "``") + "`"
    if engine == "sqlserver":
        return "[" + name.replace("]", "]]") + "]"
    return '"' + name.replace('"', '""') + '"'


def qualified(engine: str, schema: str, table: str) -> str:
    return f"{quote_name(engine, schema)}.{quote_name(engine, table)}" if schema else quote_name(engine, table)


def _is_meta(column: Column, key: str) -> bool:
    return _source_kind(column) == "meta" and column["source"]["key"] == key


def create_table_sql(engine: str, schema: str, table: str, columns: list[Column]) -> str:
    key = next((c for c in columns if _is_meta(c, "response_id")), None)
    lines = [f"  {quote_name(engine, c['column'])} {c['type']}{'' if c['nullable'] else ' NOT NULL'}" for c in columns]
    if key:
        name = js.utf16_slice(f"{table}_pk", MAX_NAME[engine])
        lines.append(f"  CONSTRAINT {quote_name(engine, name)} PRIMARY KEY ({quote_name(engine, key['column'])})")
    body = ",\n".join(lines)
    create = f"CREATE TABLE {qualified(engine, schema, table)} (\n{body}\n);"
    submitted = next((c for c in columns if _is_meta(c, "submitted_at")), None)
    return f"{create}\n{index_sql(engine, schema, table, submitted['column'])}" if submitted else create


def index_sql(engine: str, schema: str, table: str, column: str) -> str:
    name = js.utf16_slice(f"{table}_{column}_idx", MAX_NAME[engine])
    return f"CREATE INDEX {quote_name(engine, name)} ON {qualified(engine, schema, table)} ({quote_name(engine, column)});"


def add_column_sql(engine: str, schema: str, table: str, column: Column) -> str:
    add = "ADD" if engine in ("sqlserver", "oracle") else "ADD COLUMN"
    body = f"{quote_name(engine, column['column'])} {column['type']}"
    if engine == "oracle":
        body = f"({body})"
    return f"ALTER TABLE {qualified(engine, schema, table)} {add} {body};"


def unique_key_sql(engine: str, schema: str, table: str, column: str) -> str:
    name = js.utf16_slice(f"{table}_{column}_uq", MAX_NAME[engine])
    return f"CREATE UNIQUE INDEX {quote_name(engine, name)} ON {qualified(engine, schema, table)} ({quote_name(engine, column)});"


def standard_settings(settings: dict[str, Any], columns: list[Column]) -> dict[str, Any]:
    """Formalie's standard for the tables it creates: one row per response, found by its response id."""
    found = next((c for c in columns if _is_meta(c, "response_id")), None)
    return {**settings, "write_mode": "upsert", "key_column": found["column"] if found else settings["key_column"]}


_VIEW_STRIP = re.compile(r'["`\[\]]')


def view_sql(engine: str, schema: str, table: str, columns: list[Column], labels: dict[str, str]) -> str:
    limit = MAX_NAME[engine]
    view = js.utf16_slice(f"{table}_view", limit)
    used: set[str] = set()
    lines = []
    for column in columns:
        key = column["source"]["key"] if _source_kind(column) == "field" else None
        label = labels.get(key) if key else None
        alias = (js.trim(label) if label is not None else "") or column["column"]
        alias = js.utf16_slice(_VIEW_STRIP.sub("", alias), limit)
        n = 2
        while alias.lower() in used:
            alias = f"{js.utf16_slice(alias, limit - 3)} {n}"
            n += 1
        used.add(alias.lower())
        lines.append(f"  {quote_name(engine, column['column'])} AS {quote_name(engine, alias)}")
    create = "CREATE OR ALTER VIEW" if engine == "sqlserver" else "CREATE OR REPLACE VIEW"
    body = ",\n".join(lines)
    return f"{create} {qualified(engine, schema, view)} AS\nSELECT\n{body}\nFROM {qualified(engine, schema, table)};"


# ── Matching an existing table ──────────────────────────────────────────────────

def _norm(name: str) -> str:
    return snake(name).replace("_", "")


META_ALIASES = {
    "response_id": ["responseid", "formalieid", "submissionid"],
    "submitted_at": ["submittedat", "createdat", "receivedat", "submissiondate"],
    "form_version": ["formversion", "version"],
    "language": ["language", "lang", "locale"],
    "response_number": ["responsenumber", "number", "reference"],
    "respondent_email": ["respondentemail", "email"],
    "review_status": ["reviewstatus", "status"],
}


def match_columns(columns: list[Column], fields: list[Field]) -> list[Column]:
    """Map an existing table's columns to the form: same name (ignoring case and underscores) first."""
    used: set[str] = set()

    def pick(candidates: list[str]) -> Column | None:
        for candidate in candidates:
            hit = next((c for c in columns if c["name"] not in used and _norm(c["name"]) == candidate), None)
            if hit:
                used.add(hit["name"])
                return hit
        return None
    sources: dict[str, dict[str, str]] = {}
    for key in ("response_id", "submitted_at", "form_version", "language", "response_number", "review_status"):
        hit = pick(META_ALIASES[key])
        if hit:
            sources[hit["name"]] = {"kind": "meta", "key": key}
    for f in fields:
        label = f.get("label")
        hit = pick([c for c in (_norm(f["key"]), _norm("" if label is None else label)) if c])
        if hit:
            sources[hit["name"]] = {"kind": "field", "key": f["key"]}
    return [{"column": c["name"], "type": c["type"], "source": sources.get(c["name"]),
             "nullable": bool(c["nullable"] or c["has_default"]), "existing": True} for c in columns]


# ── Checks ──────────────────────────────────────────────────────────────────────

_BOOL = re.compile(r"BOOL|^BIT$|TINYINT\(1\)|NUMBER\(1\)")


def family(type_: str) -> str:
    t = type_.upper()
    if _BOOL.search(t):
        return "bool"
    if "JSON" in t:
        return "json"
    if re.search(r"INT|NUM|DEC|FLOAT|DOUBLE|REAL|MONEY", t):
        return "number"
    if re.search(r"DATE|TIME", t):
        return "date"
    if re.search(r"CHAR|TEXT|CLOB|STRING|UNIQUEIDENTIFIER|UUID", t):
        return "text"
    return "other"


def _field_family(type_: str, multi: str) -> str:
    return family(TYPES["postgresql"][kind_of_field(type_, multi)])


def check_mapping(columns: list[Column], fields: list[Field], settings: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not any(_is_meta(c, "response_id") for c in columns):
        issues.append({"code": "no_key", "column": None})
    seen: set[str] = set()
    for c in columns:
        source = c.get("source")
        if not source and not c["nullable"]:
            issues.append({"code": "required_unmapped", "column": c["column"]})
        if not source:
            continue
        ident = f"{source['kind']}:{source['key']}"
        if ident in seen:
            issues.append({"code": "duplicate_source", "column": c["column"]})
        seen.add(ident)
        if source["kind"] != "field":
            continue
        field = next((f for f in fields if f["key"] == source["key"]), None)
        if field is None:
            continue
        want = _field_family(field["type"], settings["multi_value"])
        have = family(c["type"])
        if have not in ("text", "other") and have != want and not (have == "json" and want == "text"):
            issues.append({"code": "type_mismatch", "column": c["column"], "field": field["key"]})
    if settings["write_mode"] == "upsert" and not any(c["column"] == settings["key_column"] and c.get("source") for c in columns):
        issues.append({"code": "upsert_key", "column": settings["key_column"]})
    return issues


def blocking(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for i in issues if i["code"] != "type_mismatch"]


# ── Rows ────────────────────────────────────────────────────────────────────────

def row_for(columns: list[Column], fields: list[Field], answers: dict[str, Any], facts: dict[str, Any],
            settings: dict[str, Any], file_link: Callable[[Any], list[str]] = lambda _: []) -> dict[str, Any]:
    """A response as the row Formalie writes (values as the driver receives them). `facts`: id, submitted_at,
    form_version, language, number, email, review_status."""
    by_key = {f["key"]: f for f in fields}
    meta = {"response_id": facts["id"], "submitted_at": facts["submitted_at"], "form_version": facts["form_version"],
            "language": facts["language"], "response_number": facts["number"], "respondent_email": facts["email"],
            "review_status": facts["review_status"]}
    row: dict[str, Any] = {}
    for c in columns:
        source = c.get("source")
        if not source:
            continue
        if source["kind"] == "meta":
            value = meta.get(source["key"])
            row[c["column"]] = None if js.nullish(value) else value
        else:
            row[c["column"]] = _value_for(by_key.get(source["key"]), answers.get(source["key"], js.UNDEFINED),
                                          settings["multi_value"], settings["choices"], file_link)
    return row


def _is_object(value: Any) -> bool:
    return isinstance(value, (dict, list))


def _value_for(field: Field | None, value: Any, multi: str, choices: str, file_link: Callable[[Any], list[str]]) -> Any:
    if js.nullish(value) or value == "" and isinstance(value, str) or (isinstance(value, list) and not value):
        return None
    if field is None:
        return js.stringify(value) if _is_object(value) else value
    options = field.get("options") or []

    def label(v: Any) -> str:
        text = js.to_string(v)
        if choices != "label":
            return text
        found = next((o for o in options if o.get("value") == text), None)
        got = found.get("label", js.UNDEFINED) if found else js.UNDEFINED
        return text if js.nullish(got) else got
    type_ = field["type"]
    if type_ in FILES:
        links = file_link(value)
        return js.stringify(links) if multi == "json" else "; ".join(links)
    if type_ in SEVERAL:
        if multi == "text":
            if choices == "label" or not isinstance(value, list):
                return answer_text(field, value)
            return "; ".join(js.to_string(v) for v in value)
        if isinstance(value, list):
            shaped: Any = [label(v) for v in value]
        elif type_ == "matrix" and isinstance(value, dict):
            shaped = {row: label(v) for row, v in value.items()}
        else:
            shaped = value
        return js.stringify(shaped)
    kind = kind_of_field(type_, multi)
    if kind in ("decimal", "integer"):
        number = js.to_number(value)
        return number if number == number and number not in (float("inf"), float("-inf")) else None
    if kind == "boolean":
        return value is True or value in ("true", "yes") and isinstance(value, str)
    if kind == "long":
        return js.to_string(value)
    if options:
        return label(value)
    return js.stringify(value) if _is_object(value) else js.to_string(value)


# ── Typed text as a column's value (values.ts) ──────────────────────────────────

def kind_of_type(type_: str) -> str:
    t = type_.upper()
    if re.search(r"^BOOL|^BIT$|TINYINT\(1\)|NUMBER\(1\)$", t):
        return "boolean"
    if "JSON" in t:
        return "json"
    if re.search(r"^(BIG|SMALL|TINY|MEDIUM)?INT|^INTEGER|^SERIAL|NUMBER\(\d+\)$|^NUMBER\(19\)", t):
        return "integer"
    if re.search(r"DEC|NUMERIC|NUMBER|FLOAT|DOUBLE|REAL|MONEY", t):
        return "decimal"
    if re.search(r"TIMESTAMP|DATETIME", t):
        return "datetime"
    if t == "DATE":
        return "date"
    if t.startswith("TIME"):
        return "time"
    return "text"


def length_of(type_: str) -> int | None:
    match = re.search(r"CHAR2?\((\d+)", type_, re.IGNORECASE)
    return int(match.group(1)) if match else None


YES = {"true", "yes", "1", "y", "on"}
NO = {"false", "no", "0", "n", "off"}
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIME = re.compile(r"[0-9]{2}:[0-9]{2}(:[0-9]{2})?")


def js_date_parse(text: str) -> float | None:
    """Date.parse for the ISO forms (date, date and time, with Z or an offset; without one, UTC): ms, or None.
    Like V8, a day up to 31 is taken in any month (2026-02-30 is 2 March)."""
    from datetime import UTC, datetime, timedelta

    m = re.fullmatch(r"([0-9]{4})-([0-9]{2})-([0-9]{2})(?:T([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]{1,9}))?)?"
                     r"(Z|[+-][0-9]{2}:[0-9]{2})?)?", js.trim(text))
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hour, minute, second = int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0)
    if not (1 <= month <= 12 and 1 <= day <= 31 and minute <= 59 and second <= 59
            and (hour <= 23 or (hour == 24 and minute == 0 and second == 0 and not int(m.group(7) or 0)))):
        return None
    ms = int((m.group(7) or "0")[:3].ljust(3, "0"))
    moment = datetime(year, month, 1, tzinfo=UTC) + timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second,
                                                              milliseconds=ms)
    zone = m.group(8)
    if zone and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        moment -= sign * timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
    return moment.timestamp() * 1000


def parse_value(column: dict[str, Any], raw: Any) -> dict[str, Any]:
    """Typed text as a column's value (values.ts parseValue): {"value": …} or {"problem": …}."""
    from datetime import UTC, datetime

    text = "" if js.nullish(raw) else (js.trim(raw) if isinstance(raw, str) else raw)
    if text == "" and isinstance(text, str) or text is None:
        return {"value": None} if column.get("nullable") or column.get("has_default") else {"problem": "required"}
    kind = kind_of_type(column["type"])
    if kind == "integer":
        number = js.to_number(text)
        return {"value": number} if number == number and number not in (float("inf"), float("-inf")) and number == int(number)             else {"problem": "integer"}
    if kind == "decimal":
        number = js.to_number(re.sub(f"[{js._WS}]", "", text) if isinstance(text, str) else text)
        return {"value": number} if number == number and number not in (float("inf"), float("-inf")) else {"problem": "number"}
    if kind == "boolean":
        if isinstance(text, bool):
            return {"value": text}
        word = js.to_string(text).lower()
        return {"value": True} if word in YES else {"value": False} if word in NO else {"problem": "boolean"}
    if kind == "date":
        s = js.to_string(text)
        return {"value": s} if _DATE.fullmatch(s) and js_date_parse(s) is not None else {"problem": "date"}
    if kind == "datetime":
        ms = js_date_parse(js.to_string(text))
        if ms is None:
            return {"problem": "datetime"}
        moment = datetime.fromtimestamp(ms / 1000, UTC)
        return {"value": moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")}
    if kind == "time":
        s = js.to_string(text)
        return {"value": s} if _TIME.fullmatch(s) else {"problem": "time"}
    if kind == "json":
        if isinstance(text, (dict, list)):
            return {"value": js.stringify(text)}
        import json

        def refuse(_: str) -> Any:
            raise ValueError
        try:
            json.loads(js.to_string(text), parse_constant=refuse)
            return {"value": js.to_string(text)}
        except ValueError:
            return {"problem": "json"}
    value = js.to_string(text)
    limit = length_of(column["type"])
    return {"problem": "length"} if limit is not None and js.utf16_len(value) > limit else {"value": value}

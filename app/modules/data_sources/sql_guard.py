"""Is a "read" really only a read? (security review B17, M7). Server side only, on top of the shared rules.

sql.py gives the same answers as the frontend (statement_kind, the one-statement rule) and stays as it is. Some
engines read a statement differently from that shared splitter, so before a statement classified as a read runs on
the read path (no confirm step, `data.query_read` is enough, the connection's Read only setting allows it), it is
masked again the way its own engine reads it:

- MySQL / MariaDB: `#` starts a comment; `-- ` needs a space after it; backslash escapes inside quotes; `/*! */` and
  `/*+ */` are code, not comments. (The connection also has multiple statements switched off, drivers.py, and the
  read runs in a READ ONLY transaction that must start.)
- PostgreSQL: E'' strings with backslash escapes; nested /* */ comments; dollar quotes. (Reads are prepared, which
  allows one statement only, inside a read-only transaction.)
- SQL Server: nested /* */ comments; [names] and "names"; no `;` is needed between statements, so a read must not
  contain any word that only a change or a second statement uses (UPDATE, EXEC, INTO, COMMIT, DECLARE, ...).

A read that fails this check is not refused: it is treated as a change (`other`), so it needs `data.query_write`, a
connection with read and write access, and the confirm step, and it is audited as what it is.
"""

from __future__ import annotations

import re

# T-SQL words a single read never uses; any of them means a change or a second statement
_TSQL_CHANGES = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|EXEC|EXECUTE|SP_EXECUTESQL|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|DENY|COMMIT|"
    r"ROLLBACK|BEGIN|SAVE|DECLARE|SET|USE|DBCC|BACKUP|RESTORE|KILL|SHUTDOWN|WAITFOR|INTO|BULK|OPENROWSET|"
    r"OPENQUERY|OPENDATASOURCE|RECONFIGURE|RAISERROR|THROW|PRINT|CHECKPOINT|UPDATETEXT|WRITETEXT)\b", re.I | re.A)
# Words that change data, on every engine (SELECT ... INTO writes a table or, on MySQL, a file)
_CHANGES = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|INTO)\b", re.I | re.A)
_READS = ("SELECT", "WITH", "SHOW", "EXPLAIN", "DESCRIBE", "DESC", "VALUES", "TABLE")


def _skip_quoted(sql: str, i: int, close: str, backslash: bool) -> int:
    """Index just after the quote that closes the one at `i` (doubled quotes stay inside)."""
    n = len(sql)
    i += 1
    while i < n:
        char = sql[i]
        if backslash and char == "\\":
            i += 2
            continue
        if char == close:
            if i + 1 < n and sql[i + 1] == close:
                i += 2
                continue
            return i + 1
        i += 1
    return n


def _skip_block_comment(sql: str, i: int, nested: bool) -> int:
    n, depth = len(sql), 0
    while i < n:
        if sql.startswith("/*", i):
            depth = depth + 1 if nested or depth == 0 else depth
            i += 2
            continue
        if sql.startswith("*/", i):
            depth -= 1
            i += 2
            if depth <= 0:
                return i
            continue
        i += 1
    return n


def engine_code(engine: str, sql: str, backslashes: bool = True) -> str:
    """The statement with comments and quoted text blanked out, read the way `engine` reads it (`backslashes`:
    MySQL's default; False reads it as with sql_mode NO_BACKSLASH_ESCAPES)."""
    mysql, postgres, sqlserver = engine in ("mysql", "mariadb"), engine == "postgresql", engine == "sqlserver"
    escapes = mysql and backslashes
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        char, nxt = sql[i], sql[i + 1] if i + 1 < n else ""
        start = i
        if char == "-" and nxt == "-" and (not mysql or i + 2 >= n or sql[i + 2] in " \t\r\n\f\v"):
            end = sql.find("\n", i)
            i = n if end < 0 else end
        elif char == "#" and mysql:
            end = sql.find("\n", i)
            i = n if end < 0 else end
        elif char == "/" and nxt == "*":
            if mysql and i + 2 < n and sql[i + 2] in "!+":
                out.append(" " * 3)  # executable comment: its contents are code
                i += 3
                continue
            i = _skip_block_comment(sql, i, nested=postgres or sqlserver)
        elif char == "'":
            escaped = escapes or (postgres and i > 0 and sql[i - 1] in "eE" and (i < 2 or not sql[i - 2].isalnum()))
            i = _skip_quoted(sql, i, "'", escaped)
        elif char == '"':
            i = _skip_quoted(sql, i, '"', escapes)
        elif char == "`" and mysql:
            i = _skip_quoted(sql, i, "`", False)
        elif char == "[" and sqlserver:
            i = _skip_quoted(sql, i, "]", False)
        elif char == "$" and postgres and re.match(r"\$[A-Za-z_]*\$", sql[i:]):
            tag = re.match(r"\$[A-Za-z_]*\$", sql[i:]).group(0)  # type: ignore[union-attr]
            end = sql.find(tag, i + len(tag))
            i = n if end < 0 else end + len(tag)
        elif mysql and char == "*" and nxt == "/":
            i += 2  # the end of an executable comment
        else:
            out.append(char)
            i += 1
            continue
        out.append(" " * (i - start))
    return "".join(out)


def read_is_safe(engine: str, sql: str) -> bool:
    """False when the engine would see more than one statement, or a change, in what the shared rules call a read."""
    if engine in ("mysql", "mariadb") and not _read_is_safe(engine, sql, False):
        return False  # the server's sql_mode isn't known: safe both with and without backslash escapes
    return _read_is_safe(engine, sql, True)


def _read_is_safe(engine: str, sql: str, backslashes: bool) -> bool:
    code = engine_code(engine, sql, backslashes).rstrip().rstrip(";")
    if ";" in code:
        return False
    first = re.match(r"\s*\(?\s*([A-Za-z]+)", code)
    if (first.group(1).upper() if first else "") not in _READS or _CHANGES.search(code):
        return False
    return not (engine == "sqlserver" and _TSQL_CHANGES.search(code))

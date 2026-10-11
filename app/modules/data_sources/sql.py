"""SQL text helpers for the Query editor (shared/utils/datasources/sql.ts): split a script into statements (quotes,
comments and dollar quotes respected), the statement at the cursor, what a statement does, the tables it names, its
`:name` parameters, and the layout of "Format". Same answers as the frontend (tests/parity/test_sql_rules.py).

Offsets (`from`, `to`, the cursor) count UTF-16 code units, as the browser does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core import js

WS = f"[{js._WS}]"
_DOLLAR = re.compile(r"\$[A-Za-z_]*\$")


@dataclass(frozen=True)
class Statement:
    text: str
    start: int  # `from` in the frontend
    end: int  # `to`

    def view(self) -> dict[str, object]:
        return {"text": self.text, "from": self.start, "to": self.end}


def _mask(sql: str) -> list[bool]:
    """Each character: in code (True), or inside a quote / comment (False)."""
    n = len(sql)
    mask = [False] * n
    i = 0
    while i < n:
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if char == "-" and nxt == "-":
            end = sql.find("\n", i)
            i = n if end < 0 else end
            continue
        if char == "/" and nxt == "*":
            end = sql.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if char in "'\"`[":
            close = "]" if char == "[" else char
            i += 1
            while i < n:
                if sql[i] == close:
                    if i + 1 < n and sql[i + 1] == close and close != "]":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if char == "$":
            dollar = _DOLLAR.match(sql, i)
            if dollar:
                tag = dollar.group(0)
                end = sql.find(tag, i + len(tag))
                i = n if end < 0 else end + len(tag)
                continue
        mask[i] = True
        i += 1
    return mask


def _u16(text: str) -> list[int]:
    """Code point index → UTF-16 offset (one more entry for the end)."""
    out = [0]
    for ch in text:
        out.append(out[-1] + (2 if ord(ch) > 0xFFFF else 1))
    return out


def _without_comments(sql: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", re.sub(r"--[^\n]*", " ", sql), flags=re.S)


def split_statements(sql: str) -> list[Statement]:
    mask = _mask(sql)
    parts: list[tuple[str, int, int]] = []
    start = 0
    for index, in_code in enumerate(mask):
        if in_code and sql[index] == ";":
            parts.append((sql[start:index], start, index))
            start = index + 1
    parts.append((sql[start:], start, len(sql)))
    u16 = _u16(sql)
    out = []
    for text, begin, _ in parts:
        lead = len(text) - len(js.trim_start(text))
        body = js.trim(text)
        if not js.trim(_without_comments(body)):
            continue
        first = u16[begin + lead]
        out.append(Statement(body, first, first + js.utf16_len(body)))
    return out


def statement_at(sql: str, cursor: int) -> Statement | None:
    statements = split_statements(sql)
    if not statements:
        return None
    found = next((s for s in statements if s.start <= cursor <= s.end + 1), None)
    if found:
        return found
    return next((s for s in reversed(statements) if s.start <= cursor), statements[0])


def code_only(sql: str) -> str:
    """The text with comments blanked out and quoted parts as spaces."""
    mask = _mask(sql)
    return "".join(ch if mask[i] else " " for i, ch in enumerate(sql))


_FIRST = re.compile(rf"^{WS}*\(?{WS}*([A-Z]+)")
_READS = {"SELECT", "SHOW", "EXPLAIN", "DESCRIBE", "DESC", "VALUES", "TABLE"}
_STRUCTURE = {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME", "COMMENT", "GRANT", "REVOKE"}


def _change(text: str) -> str | None:
    if re.search(r"\bDELETE\b", text, re.A):
        return "delete"
    if re.search(r"\bUPDATE\b", text, re.A):
        return "update"
    if re.search(r"\b(INSERT|MERGE)\b", text, re.A):
        return "insert"
    return None


def statement_kind(sql: str) -> str:
    """read · insert · update · delete · structure · other."""
    code = code_only(sql).upper()
    found = _FIRST.match(code)
    first = found.group(1) if found else ""
    if first == "WITH":
        return _change(code) or "read"
    if first in _READS:
        return "insert" if re.search(r"\bINTO\b", code, re.A) and first == "SELECT" else "read"
    if first in ("INSERT", "MERGE", "UPSERT", "REPLACE"):
        return "insert"
    if first == "UPDATE":
        return "update"
    if first == "DELETE":
        return "delete"
    if first in _STRUCTURE:
        return "structure"
    return "other"


_NAME = r'(?:[A-Za-z0-9_$]+|"[^"]*"|`[^`]*`|\[[^\]]*\])'
_TABLES = re.compile(rf"\b(?:FROM|JOIN|UPDATE|INTO|TABLE){WS}+({_NAME}(?:{WS}*\.{WS}*{_NAME})?)", re.I | re.A)


def tables_in(sql: str) -> list[str]:
    """Tables the statement names (after FROM, JOIN, UPDATE, INTO, TABLE), as written, quotes removed."""
    code = re.sub(r"'(?:[^']|'')*'", " ", _without_comments(sql))
    out: list[str] = []
    for match in _TABLES.finditer(code):
        name = re.sub(r'["`\[\]]', "", re.sub(f"{WS}", "", match.group(1)))
        if name not in out:
            out.append(name)
    return out


_PARAM = re.compile(r"(?<![:A-Za-z0-9_]):([A-Za-z_][A-Za-z0-9_]*)")


def parameters_in(sql: str) -> list[str]:
    out: list[str] = []
    for match in _PARAM.finditer(code_only(sql)):
        if match.group(1) not in out:
            out.append(match.group(1))
    return out


def parameter_spans(sql: str) -> list[tuple[int, int, str]]:
    """(start, end, name) of each `:name` in code (for binding them), code point offsets."""
    return [(m.start(), m.end(), m.group(1)) for m in _PARAM.finditer(code_only(sql))]


# ── Format ──────────────────────────────────────────────────────────────────────

KEYWORDS = set(
    "select from where and or not in is null like ilike between exists as on join left right inner outer full cross "
    "natural using group by order having limit offset fetch first next rows row only union all distinct insert into "
    "values update set delete returning with case when then else end asc desc create alter drop table index view "
    "truncate primary key foreign references default unique check constraint add column rename to top count sum avg "
    "min max coalesce cast true false interval over partition".split(" "))
CLAUSES = ["GROUP BY", "ORDER BY", "INSERT INTO", "DELETE FROM", "UNION ALL", "LEFT OUTER JOIN", "RIGHT OUTER JOIN",
           "FULL OUTER JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN", "CROSS JOIN", "FETCH FIRST", "SELECT",
           "FROM", "WHERE", "HAVING", "LIMIT", "OFFSET", "UNION", "JOIN", "VALUES", "SET", "RETURNING", "UPDATE", "WITH", "ON"]
_TOKEN = re.compile(
    r"""('(?:[^']|'')*'|"(?:[^"]|"")*"|`[^`]*`|\[[^\]]*\]|--[^\n]*|/\*.*?\*/|\$[A-Za-z_]*\$.*?\$[A-Za-z_]*\$|"""
    + WS + r"""+|[A-Za-z_][A-Za-z0-9_$]*|[0-9]+(?:\.[0-9]+)?|::|<>|!=|<=|>=|\|\||.)""", re.S)
_ONLY_WS = re.compile(rf"^{WS}+\Z")
_OPEN_TIGHT = re.compile(r'[A-Za-z0-9_"`\]]\Z')
_OPEN_LOOSE = re.compile(rf"\b(IN|AS|VALUES|ON|AND|OR|NOT|EXISTS){WS}*\Z", re.I | re.A)
_AFTER_SPACE = re.compile(rf"(?:{WS}|[(.])\Z")


def _format_statement(sql: str) -> str:
    tokens = [m.group(0) for m in _TOKEN.finditer(sql) if not _ONLY_WS.match(m.group(0))]
    words = [t.upper() if re.match(r"[A-Za-z_]", t) and t.lower() in KEYWORDS else t for t in tokens]
    out = ""
    depth = 0
    clause = ""

    def newline(indent: str = "") -> None:
        nonlocal out
        out = js.trim_end(out)
        out += ("\n" if out else "") + "  " * depth + indent

    i = 0
    while i < len(words):
        word = words[i]
        ahead = " ".join(words[i:i + 3])
        before = words[i - 1] if i >= 1 else None
        match = next((name for name in CLAUSES if ahead == name or ahead.startswith(f"{name} ")), None) \
            if depth == 0 or before == "(" else None
        if match and (depth == 0 or match == "SELECT"):
            newline("  ") if match == "ON" else newline()
            out += match
            clause = match
            i += len(match.split(" ")) - 1
            if match in ("SELECT", "SET", "GROUP BY", "ORDER BY"):
                following = words[i + 1] if i + 1 < len(words) else None
                if following in ("DISTINCT", "TOP"):
                    out += " "
                else:
                    newline("  ")
            else:
                out += " "
            i += 1
            continue
        two_back = words[i - 2] if i >= 2 else None
        if word in ("AND", "OR") and depth == 0 and re.search("WHERE|HAVING|ON", clause) and two_back != "BETWEEN":
            newline("  ")
            out += f"{word} "
            i += 1
            continue
        if word.startswith("--"):
            out += (" " if out and not out.endswith("\n") else "") + word
            newline()
            i += 1
            continue
        if word == "(":
            if _OPEN_TIGHT.search(out) and not _OPEN_LOOSE.search(out):
                out += "("
            else:
                out += ("" if out.endswith(" ") or not out else " ") + "("
            depth += 1
            i += 1
            continue
        if word == ")":
            depth = max(0, depth - 1)
            out = js.trim_end(out) + ")"
            i += 1
            continue
        if word == ",":
            out = js.trim_end(out) + ","
            if depth == 0 and clause in ("SELECT", "SET", "GROUP BY", "ORDER BY"):
                newline("  ")
            else:
                out += " "
            i += 1
            continue
        if word in (".", "::"):
            out = js.trim_end(out) + word
            i += 1
            continue
        out += (" " if out and not _AFTER_SPACE.search(out) and not out.endswith("::") else "") + word
        i += 1
    return js.trim(re.sub(r"[ \t]+$", "", out, flags=re.M))


def format_sql(sql: str) -> str:
    return "\n\n".join(f"{_format_statement(s.text)};" for s in split_statements(sql))


def script_kind(sql: str) -> str:
    """A whole script's kind: its strongest statement (structure > delete > update > insert > other > read)."""
    kinds = [statement_kind(s.text) for s in split_statements(sql)]
    return next((k for k in ("structure", "delete", "update", "insert", "other", "read") if k in kinds), "read")

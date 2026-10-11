"""Answer validation (port of shared/utils/forms/validate.ts, catalogues.ts checks and file-answers.ts), one set of
rules for the form page and the API: the server checks every submission again with the same rules. Held to the
frontend's answers by tests/parity/test_submission_rules.py.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core import js

EMAIL = re.compile(r"^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[^\s@.]{2,}$")
NUMERIC_TYPES = ("number", "currency", "slider", "scale", "rating", "percentage")
TEXT_TYPES = ("short_text", "long_text", "email", "url", "phone")
IPV4 = re.compile(r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$", re.ASCII)
DOMAIN = re.compile(r"^(?=.{1,253}$)(?!-)([a-z0-9-]{1,63}(?<!-)\.)+[a-z]{2,63}$", re.IGNORECASE | re.ASCII)
MAC = re.compile(r"^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$|^([0-9a-f]{4}\.){2}[0-9a-f]{4}$", re.IGNORECASE)
BIC = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
_JS_SPACE = "\t\n\v\f\r                  　﻿"

LANGUAGE_CODES = (
    "aa ab af ak am an ar as av ay az ba be bg bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee el en eo es et "
    "eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj "
    "kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr "
    "nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te "
    "tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu").split()

MAX_RESPONDENT_FILE_BYTES = 25 * 1024 * 1024
FILE_FIELD_TYPES = ("file_upload", "image_upload")


@lru_cache(maxsize=1)
def _intl() -> dict[str, Any]:
    """Node's Intl answers (currencies, time zones), recorded by scripts/dump_submission_rules.py."""
    return json.loads((Path(__file__).parent / "data" / "intl.json").read_text(encoding="utf-8"))


def is_language_code(value: str) -> bool:
    return value in LANGUAGE_CODES


def is_currency_code(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}", value)) and value in _intl()["currencies"]


def is_time_zone(value: str) -> bool:
    """new Intl.DateTimeFormat('en', { timeZone }) accepts IANA names and links in any letter case, and offsets."""
    if value == "UTC":
        return True
    zones = _intl()["zones_lower"]
    if value.lower() in zones:
        return True
    return bool(re.fullmatch(r"[+-](?:[01]\d|2[0-3])(?::?[0-5]\d)?", value))


# ── Small checks ────────────────────────────────────────────────────────────────

def is_ipv4(value: str) -> bool:
    return bool(IPV4.fullmatch(value))


def is_ipv6(value: str) -> bool:
    if not re.fullmatch(r"[0-9a-fA-F:.]+", value) or value.count("::") > 1:
        return False
    parts = value.split(":")
    groups = 8
    tail = parts[-1] if parts else ""
    if "." in tail:
        if not IPV4.fullmatch(tail):
            return False
        parts, groups = parts[:-1], 6
    filled = [p for p in parts if p]
    if not all(re.fullmatch(r"[0-9a-fA-F]{1,4}", g) for g in filled):
        return False
    return len(filled) < groups if "::" in value else len(filled) == groups and len(parts) == groups


def is_iban(value: str) -> bool:
    iban = re.sub(r"\s+", "", value).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", iban, re.ASCII):
        return False
    moved = iban[4:] + iban[:4]
    rest = 0
    for char in moved:
        code = str(ord(char) - 55) if "A" <= char <= "Z" else char
        for digit in code:
            rest = (rest * 10 + int(digit)) % 97
    return rest == 1


def is_blank(value: Any) -> bool:
    if js.nullish(value) or value == "" or value is False:
        return True
    if isinstance(value, list):
        return not value
    if isinstance(value, dict):
        return not any(not js.nullish(v) and js.trim(js.to_string(v)) != "" for v in value.values())
    return False


def plain_text(html: str) -> str:
    """Visible text of rich text HTML (what length limits count)."""
    text = re.sub(r"<[^>]*>", "", html).replace("&nbsp;", " ")
    return re.sub(r"&[a-z]+;|&#\d+;", "x", text, flags=re.IGNORECASE | re.ASCII)


def required_address_parts(fld: dict[str, Any]) -> list[str]:
    props = fld.get("props") or {}
    return ["line1", "city", *(["region"] if props.get("require_region") is True else []),
            *([] if props.get("require_postal_code") is False else ["postal_code"]), "country"]


def _num(value: Any) -> float:
    return math.nan if value == "" or js.nullish(value) else js.to_number(value)


def _param(n: float) -> float | int:
    return int(n) if n.is_integer() else n


# ── URLs (new URL(text): protocol http / https and a host with a dot) ───────────

_FORBIDDEN_HOST = set("\x00\t\n\r #/:<>?@[\\]^|%")


def _ipv4_host(host: str) -> str | None | bool:
    """WHATWG IPv4 parsing: False = not an IPv4 address, None = a failure, else the dotted address."""
    parts = host.split(".")
    if parts[-1] == "":
        parts = parts[:-1]
        if not parts:
            return False
    last = parts[-1]
    if not (re.fullmatch(r"\d+", last, re.ASCII) or re.fullmatch(r"0[xX][0-9a-fA-F]*", last)):
        return False
    if len(parts) > 4:
        return None
    numbers = []
    for part in parts:
        if part == "":
            return None
        if re.fullmatch(r"0[xX][0-9a-fA-F]*", part):
            n = int(part[2:] or "0", 16)
        elif re.fullmatch(r"0[0-7]+", part):
            n = int(part, 8)
        elif re.fullmatch(r"\d+", part, re.ASCII):
            if len(part) > 1 and part.startswith("0"):
                return None
            n = int(part)
        else:
            return None
        numbers.append(n)
    if any(n > 255 for n in numbers[:-1]) or numbers[-1] >= 256 ** (5 - len(numbers)):
        return None
    address = numbers[-1] + sum(n * 256 ** (3 - i) for i, n in enumerate(numbers[:-1]))
    return ".".join(str((address >> s) & 255) for s in (24, 16, 8, 0))


def url_ok(text: str) -> bool:
    raw = text.strip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18"
                     "\x19\x1a\x1b\x1c\x1d\x1e\x1f ")
    raw = re.sub(r"[\t\n\r]", "", raw)
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", raw)
    if not scheme or scheme.group(1).lower() not in ("http", "https"):
        return False
    rest = raw[scheme.end():].lstrip("/\\")
    authority = re.split(r"[/\\?#]", rest, maxsplit=1)[0]
    if "@" in authority:
        authority = authority.rsplit("@", 1)[1]
    if authority.startswith("["):
        return False  # an IPv6 host has no dot
    host, _, port = authority.partition(":")
    if port and not re.fullmatch(r"\d+", port, re.ASCII):
        return False
    if port and int(port) > 65535:
        return False
    if not host:
        return False
    try:
        from urllib.parse import unquote

        host = unquote(host, errors="strict")
    except UnicodeDecodeError:
        return False
    host = re.sub(r"[。．｡]", ".", host).lower()
    if any(c in _FORBIDDEN_HOST - {"%"} for c in host) or any(ord(c) < 0x20 or ord(c) == 0x7f for c in host):
        return False
    if not host.isascii():
        try:
            host = ".".join(label.encode("idna").decode("ascii") if label else "" for label in host.split("."))
        except UnicodeError:
            return False
    ipv4 = _ipv4_host(host)
    if ipv4 is None:
        return False
    if isinstance(ipv4, str):
        host = ipv4
    return "." in host


# ── One answer ──────────────────────────────────────────────────────────────────

def _compile(pattern: str) -> re.Pattern[str] | None:
    """A JavaScript pattern in Python's dialect (named groups); None when it can't be read."""
    translated = re.sub(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>", r"(?P<\1>", pattern)
    translated = re.sub(r"\\k<([A-Za-z_][A-Za-z0-9_]*)>", r"(?P=\1)", translated)
    try:
        return re.compile(translated, re.ASCII)
    except re.error:
        return None


def validate_answer(fld: dict[str, Any], value: Any, required: bool) -> dict[str, Any] | None:
    """The first problem with an answer ({code, params?, parts?}), or None."""
    rules = fld.get("validation") or {}
    kind = fld.get("type")

    def as_object(v: Any) -> Any:
        """`value && typeof value === 'object' ? value : {}` (a list is an object too, with no named parts)."""
        return v if isinstance(v, (dict, list)) and v is not None else {}

    def part(obj: Any, key: str) -> Any:
        return obj.get(key, js.UNDEFINED) if isinstance(obj, dict) else js.UNDEFINED

    if kind == "address":
        address = as_object(value)
        if is_blank(address):
            return {"code": "required"} if required else None
        parts = [p for p in required_address_parts(fld) if is_blank(part(address, p))]
        return {"code": "address", "parts": parts} if parts else None
    if kind == "full_name":
        name = as_object(value)
        if is_blank(name):
            return {"code": "required"} if required else None
        return {"code": "name"} if is_blank(part(name, "first")) or is_blank(part(name, "last")) else None
    if kind == "consent":
        return {"code": "consent"} if required and value is not True else None
    if kind == "duration":
        d = as_object(value)
        if is_blank(d):
            return {"code": "required"} if required else None
        h = _num(0 if js.nullish(part(d, "hours")) else part(d, "hours"))
        m = _num(0 if js.nullish(part(d, "minutes")) else part(d, "minutes"))
        bad = math.isnan(h) or math.isnan(m) or h < 0 or m < 0 or m > 59 or h + m == 0
        return {"code": "duration"} if bad else None
    if kind == "date_range":
        r = as_object(value)
        start, end = part(r, "from"), part(r, "to")
        if not _js_truthy(start) and not _js_truthy(end):
            return {"code": "required"} if required else None
        if not _js_truthy(start) or not _js_truthy(end):
            return {"code": "date_range"}
        return {"code": "date_range"} if _js_greater(start, end) else None

    empty = not js.trim(plain_text(js.to_string("" if js.nullish(value) else value))) if kind == "rich_text" else is_blank(value)
    if empty:
        return {"code": "required"} if required else None

    text = js.trim(value) if isinstance(value, str) else ""
    if kind == "email" and not EMAIL.fullmatch(text):
        return {"code": "email"}
    if kind == "url" and not url_ok(text):
        return {"code": "url"}
    if kind == "phone":
        digits = re.sub(r"[\s().-]", "", text)
        if not re.fullmatch(r"\+?\d{6,15}", digits, re.ASCII):
            return {"code": "phone"}
    if kind == "ip_address":
        raw_version = (fld.get("props") or {}).get("ip_version", js.UNDEFINED)
        version = "any" if js.nullish(raw_version) else js.to_string(raw_version)
        ok = (version != "v6" and is_ipv4(text)) or (version != "v4" and is_ipv6(text))
        if not ok:
            return {"code": "ip", "params": {"version": version}}
    if kind == "domain" and not DOMAIN.fullmatch(re.sub(r"\.$", "", text)):
        return {"code": "domain"}
    if kind == "mac_address" and not MAC.fullmatch(text):
        return {"code": "mac"}
    if kind == "iban" and not is_iban(text):
        return {"code": "iban"}
    if kind == "bic" and not BIC.fullmatch(re.sub(r"\s+", "", text).upper()):
        return {"code": "bic"}
    if kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return {"code": "color"}
    if kind == "language" and not is_language_code(text):
        return {"code": "choice"}
    if kind == "timezone" and not is_time_zone(text):
        return {"code": "choice"}
    if kind == "currency_code" and not is_currency_code(text):
        return {"code": "choice"}

    if kind in NUMERIC_TYPES:
        n = _num(value)
        if math.isnan(n):
            return {"code": "number"}
        low, high = _num(rules.get("min", js.UNDEFINED)), _num(rules.get("max", js.UNDEFINED))
        if not math.isnan(low) and n < low:
            return {"code": "min", "params": {"min": _param(low)}}
        if not math.isnan(high) and n > high:
            return {"code": "max", "params": {"max": _param(high)}}

    if kind in TEXT_TYPES or kind == "rich_text":
        length = js.utf16_len(plain_text(js.to_string(value))) if kind == "rich_text" else js.utf16_len(text)
        low, high = _num(rules.get("min_length", js.UNDEFINED)), _num(rules.get("max_length", js.UNDEFINED))
        if not math.isnan(low) and length < low:
            return {"code": "min_length", "params": {"n": _param(low)}}
        if not math.isnan(high) and length > high:
            return {"code": "max_length", "params": {"n": _param(high)}}
        pattern = rules.get("pattern")
        if isinstance(pattern, str) and pattern and kind != "rich_text":
            compiled = _compile(pattern)
            if compiled is not None and not compiled.search(text):
                return {"code": "pattern"}

    if isinstance(value, list) and kind in ("checkbox", "multi_select"):
        low, high = _num(rules.get("min_selected", js.UNDEFINED)), _num(rules.get("max_selected", js.UNDEFINED))
        if not math.isnan(low) and len(value) < low:
            return {"code": "min_selected", "params": {"n": _param(low)}}
        if not math.isnan(high) and len(value) > high:
            return {"code": "max_selected", "params": {"n": _param(high)}}

    if kind in FILE_FIELD_TYPES:
        count = len(value) if isinstance(value, list) else 1
        raw = (fld.get("props") or {}).get("max_files", js.UNDEFINED)
        high = _num(1 if js.nullish(raw) else raw)
        if not math.isnan(high) and count > high:
            return {"code": "max_files", "params": {"n": _param(high)}}
    return None


def _js_truthy(value: Any) -> bool:
    if js.nullish(value) or value is False or value == "":
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0 and not math.isnan(value)
    return True


def _js_greater(a: Any, b: Any) -> bool:
    """`a > b` for the date range's two ends (texts compare as UTF-16, numbers as numbers)."""
    if isinstance(a, str) and isinstance(b, str):
        return js.js_less(b, a)
    x, y = js.to_number(a), js.to_number(b)
    return not (math.isnan(x) or math.isnan(y)) and x > y


# ── File answers (file-answers.ts) ──────────────────────────────────────────────

def is_file_answer(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("id"), str) and isinstance(value.get("name"), str) \
        and isinstance(value.get("size"), (int, float)) and not isinstance(value.get("size"), bool) \
        and isinstance(value.get("type"), str)


def file_answers(value: Any) -> list[dict[str, Any]]:
    return [v for v in value if is_file_answer(v)] if isinstance(value, list) else []


def max_file_bytes(props: dict[str, Any] | None) -> int:
    raw = (props or {}).get("max_mb", js.UNDEFINED)
    mb = js.to_number(10 if js.nullish(raw) else raw)
    return int(min(MAX_RESPONDENT_FILE_BYTES, (mb if math.isfinite(mb) and mb > 0 else 10) * 1024 * 1024))

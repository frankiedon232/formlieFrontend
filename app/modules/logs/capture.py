"""Turning a raw request / response into a request-log record: masking, body parsing, attack flags.

Pure functions, no I/O. Secrets are masked at capture, so they never reach the queue, the files or the database:
Authorization, cookies, CSRF, internal and platform signatures, passwords, tokens, secrets, OTP and recovery codes.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from app.core.logging.setup import MASK, is_sensitive, mask

SENSITIVE_HEADERS = {
    "authorization", "proxy-authorization", "cookie", "set-cookie", "x-csrf-token", "x-formalie-internal",
    "x-platform-signature", "x-api-key", "x-amz-security-token",
}
ENVELOPE_HEADER = "x-formalie-envelope"
# Left out of every record entirely, not even masked: the edge's shared secret (request_context.py)
DROPPED_HEADERS = {"x-formalie-edge"}
ENVELOPE_CONTENT_TYPE = "application/vnd.formalie.enc+json"

# Where a plain `code` (or `codes`) is a one-time code or recovery code, not a business code.
_CODE_PATHS = re.compile(r"/(auth|me/two-step|tenants/find-workspace|public/forms/[^/]+/verify)(/|$)")
_CODE_KEYS = {"code", "codes", "recovery_code", "recovery_codes"}

_SQLI = re.compile(
    r"(\bunion\b\s+(all\s+)?select\b|\bor\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?\s*(--|#|$)|;\s*(drop|truncate|alter)\s+table\b"
    r"|\b(sleep|benchmark|pg_sleep)\s*\(|\bxp_cmdshell\b|\binformation_schema\b|'\s*--)",
    re.IGNORECASE,
)
_XSS = re.compile(r"(<\s*script\b|javascript\s*:|\bon(error|load|click|mouseover|focus)\s*=|<\s*iframe\b|document\.cookie)",
                  re.IGNORECASE)
_TRAVERSAL = re.compile(r"(\.\./|\.\.\\|%2e%2e(%2f|/|%5c)|/etc/passwd|\bwin\.ini\b)", re.IGNORECASE)
# The query editor and explorer carry SQL on purpose.
_SQL_BY_DESIGN = re.compile(r"/datasources/[^/]+/(query|explorer)")


def mask_headers(raw: list[tuple[bytes, bytes]]) -> dict[str, str]:
    """All headers, names lower-cased; repeated headers joined with ', '. Secrets keep only their shape."""
    out: dict[str, str] = {}
    for key_b, value_b in raw:
        key = key_b.decode("latin-1").lower()
        if key in DROPPED_HEADERS:
            continue
        value = value_b.decode("latin-1")
        if key in ("authorization", "proxy-authorization"):
            scheme = value.split(" ", 1)[0] if " " in value else ""
            value = f"{scheme} {MASK}".strip()
        elif key == "cookie":  # every cookie's name, no value
            value = "; ".join(f"{part.split('=', 1)[0].strip()}={MASK}" for part in value.split(";") if "=" in part)
        elif key == "set-cookie":  # the cookie's name and its attributes (Path, HttpOnly …), no value
            first, *attributes = value.split(";")
            value = ";".join([f"{first.split('=', 1)[0].strip()}={MASK}", *attributes])
        elif key == ENVELOPE_HEADER:
            value = f"<envelope {len(value)} chars>"
        elif key in SENSITIVE_HEADERS or is_sensitive(key):
            value = MASK
        out[key] = f"{out[key]}, {value}" if key in out else value[:4096]
    return out


def _mask_codes(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: (MASK if k.lower() in _CODE_KEYS else _mask_codes(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_codes(v) for v in value]
    return value


def mask_payload(value: Any, path: str) -> Any:
    masked = mask(value)
    return _mask_codes(masked) if _CODE_PATHS.search(path) else masked


def parse_query(query_string: str, path: str) -> dict[str, Any] | None:
    if not query_string:
        return None
    parsed = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(query_string, keep_blank_values=True).items()}
    return mask_payload(parsed, path)


def body_record(
    content_type: str | None,
    body: bytes,
    total_size: int,
    sha256: str | None,
    truncated: bool,
    path: str,
    decrypted: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """`request_body` (JSON, masked), `request_body_text` (other text), keys, field count, truncation."""
    kind = (content_type or "").split(";")[0].strip().lower()
    record: dict[str, Any] = {
        "request_content_type": content_type,
        "request_body_sha256": sha256 if total_size else None,
        "request_body_truncated": truncated,
        "request_body": None,
        "request_body_text": None,
        "request_body_keys": None,
        "request_body_fields": None,
    }
    parsed: Any = None
    if decrypted is not None:  # B1: what the client really sent inside the envelope
        parsed = {"body": decrypted.get("body"), "envelope": True}
    elif not total_size:
        return record
    elif kind == ENVELOPE_CONTENT_TYPE:
        try:
            env = json.loads(body)
            parsed = {"envelope": {"kid": env.get("kid"), "ts": env.get("ts"),
                                   "ct_chars": len(env.get("ct") or "")}} if isinstance(env, dict) else None
        except ValueError:
            parsed = None
    elif kind.endswith("json") and not truncated:
        try:
            parsed = json.loads(body)
        except ValueError:
            record["request_body_text"] = body.decode("utf-8", "replace")
    elif kind == "application/x-www-form-urlencoded" and not truncated:
        parsed = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(body.decode("utf-8", "replace")).items()}
    elif kind.startswith("text/") or kind.endswith(("json", "xml")):
        record["request_body_text"] = body.decode("utf-8", "replace")
    # multipart and binary uploads: size, type and hash only

    if parsed is not None:
        masked = mask_payload(parsed, path)
        record["request_body"] = masked
        inner = masked.get("body") if isinstance(masked, dict) and masked.get("envelope") is True else masked
        if isinstance(inner, dict):
            record["request_body_keys"] = sorted(inner)[:100]
            record["request_body_fields"] = len(inner)
    return record


def response_body(content_type: str | None, body: bytes, truncated: bool) -> Any:
    kind = (content_type or "").split(";")[0].strip().lower()
    if not body:
        return None
    if kind.endswith("json") and not truncated:
        try:
            return mask(json.loads(body))
        except ValueError:
            pass
    return {"text": body.decode("utf-8", "replace")[:2048], "truncated": truncated}


def attack_flags(path: str, query_string: str, body_text: str) -> set[str]:
    haystack = unquote_plus(f"{path}?{query_string}") + "\n" + body_text[:65_536]
    flags: set[str] = set()
    if not _SQL_BY_DESIGN.search(path) and _SQLI.search(haystack):
        flags.add("sqli")
    if _XSS.search(haystack):
        flags.add("xss")
    if _TRAVERSAL.search(f"{path}?{query_string}") or _TRAVERSAL.search(haystack):
        flags.add("path_traversal")
    return flags

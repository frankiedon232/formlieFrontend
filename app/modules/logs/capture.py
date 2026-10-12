"""Turning a raw request / response into a request-log record: masking, body parsing, attack flags.

Pure functions, no I/O. Secrets are masked at capture, so they never reach the queue, the files or the database:
Authorization, cookies, CSRF, internal and platform signatures, passwords, tokens, secrets, OTP and recovery codes.

Bodies follow a policy per route (B17 review M8): routes that carry respondents' answers or customers' secrets
(public forms, responses, the API service, data sources, destinations, webhooks, email and SSO settings, privacy
requests, AI, uploads, the internal API) keep **field names only, never values**. Everywhere else values are kept,
with secrets masked by field name, by value (tokens, keys, passwords in URLs) and as `value` next to a `name`
(header lists such as an API endpoint's required headers).
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from app.core.logging.redact import redact_text
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
# Field names only, never values (M8): answers, drafts, files, API calls and logs, connection details, secrets.
NAMES_ONLY = re.compile(
    r"^(?:/api/v\d+)?/(public|responses?|response-[a-z]+|api-[a-z-]+|datasources?|datasource-[a-z]+|saved-queries"
    r"|explorer[a-z-]*|destinations|webhooks?|webhook-[a-z]+|settings/(?:emails?|sso|address)|privacy|ai|communications"
    r"|storage|uploads|internal|email)(/|$)"
)
# Bodies that are never kept at all, not even their field names: raw upload bytes
NO_BODY = re.compile(r"^(?:/api/v\d+)?/storage/")


def body_policy(path: str) -> str:
    """`none` (not kept), `names` (field names only) or `masked` (values with secrets masked)."""
    if NO_BODY.search(path):
        return "none"
    return "names" if NAMES_ONLY.search(path) else "masked"


def names_only(value: Any, depth: int = 0) -> Any:
    """The shape of a payload: every key kept, every value replaced by `***`."""
    if depth > 6:
        return MASK
    if isinstance(value, dict):
        return {str(k)[:200]: names_only(v, depth + 1) for k, v in list(value.items())[:200]}
    if isinstance(value, (list, tuple)):
        return [names_only(v, depth + 1) for v in list(value)[:20]]
    return None if value is None else MASK


def _mask_named_values(value: Any) -> Any:
    """`{"name": "X-Secret", "value": "…"}`: the value is masked wherever a sibling `name` exists (header lists)."""
    if isinstance(value, dict):
        out = {k: _mask_named_values(v) for k, v in value.items()}
        if "name" in out and "value" in out and out["value"] is not None:
            out["value"] = MASK
        return out
    if isinstance(value, list):
        return [_mask_named_values(v) for v in value]
    return value


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
    masked = _mask_named_values(mask(value))
    return _mask_codes(masked) if _CODE_PATHS.search(path) else masked


# On `names` routes the query keeps these values (paging, sorting, plain filters); every other value is `***`
# (searches, the unsubscribe link's `t`, prefilled answers).
_PLAIN_QUERY_KEYS = frozenset({"page", "per_page", "sort", "order", "dir", "view", "status", "from", "to", "level",
                               "limit", "offset", "lang", "locale", "tz", "mode", "range", "days", "kind", "type"})


def parse_query(query_string: str, path: str) -> dict[str, Any] | None:
    if not query_string:
        return None
    parsed = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(query_string, keep_blank_values=True).items()}
    if body_policy(path) != "masked":
        parsed = {k: (v if k.lower() in _PLAIN_QUERY_KEYS else MASK) for k, v in parsed.items()}
    return mask_payload(parsed, path)


def body_record(
    content_type: str | None,
    body: bytes,
    total_size: int,
    sha256: str | None,
    truncated: bool,
    path: str,
    decrypted: dict[str, Any] | None = None,
    policy: str | None = None,
) -> dict[str, Any]:
    """`request_body` (JSON, masked), `request_body_text` (other text), keys, field count, truncation.
    `policy` (default: by route, `body_policy`): `names` keeps the payload's shape with every value as `***`,
    `none` keeps no body at all (size and hash only)."""
    policy = policy or body_policy(path)
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
    if policy == "none":
        return record
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
            record["request_body_text"] = MASK if policy == "names" else redact_text(body.decode("utf-8", "replace"))
    elif kind == "application/x-www-form-urlencoded" and not truncated:
        parsed = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(body.decode("utf-8", "replace")).items()}
    elif (kind.startswith("text/") or kind.endswith(("json", "xml"))) and policy != "names":
        record["request_body_text"] = redact_text(body.decode("utf-8", "replace"))
    # multipart and binary uploads: size, type and hash only

    if parsed is not None:
        masked = mask_payload(parsed, path)
        if policy == "names" and not (decrypted is None and kind == ENVELOPE_CONTENT_TYPE):  # envelope facts stay
            inner = masked.get("body") if isinstance(masked, dict) and masked.get("envelope") is True else masked
            shape = names_only(inner)
            masked = {**masked, "body": shape} if inner is not masked else shape
        record["request_body"] = masked
        inner = masked.get("body") if isinstance(masked, dict) and masked.get("envelope") is True else masked
        if isinstance(inner, dict):
            record["request_body_keys"] = sorted(inner)[:100]
            record["request_body_fields"] = len(inner)
    return record


def response_body(content_type: str | None, body: bytes, truncated: bool, policy: str = "masked") -> Any:
    """An answer as the log keeps it. On `names` / `none` routes only an error is kept as it is (its code and
    details); anything else keeps its shape, no values."""
    kind = (content_type or "").split(";")[0].strip().lower()
    if not body:
        return None
    if kind.endswith("json") and not truncated:
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = None
        else:
            if policy == "masked" or (isinstance(parsed, dict) and set(parsed) <= {"success", "error", "trace_id"}):
                return _mask_named_values(mask(parsed))
            return names_only(parsed)
    if policy != "masked":
        return {"text": MASK, "truncated": truncated}
    return {"text": redact_text(body.decode("utf-8", "replace")[:2048]), "truncated": truncated}


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

"""Token and header rules (port of shared/utils/apiService/tokens.ts, F13 M2, SECURITY-PROTOCOL §9), held to the
frontend's answers by tests/parity/test_api_rules.py: token prefixes (test / live told apart at a glance, and by
secret scanners), status from the dates, the visible preview of a secret, scope checks, the names allowed for required
headers, the Formalie-Key check and the canonical JSON a retry is recognised by.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

API_METHODS = ("GET", "POST", "PUT", "DELETE")
API_TOKEN_MODES = ("live", "test")
API_TOKEN_KINDS = ("static", "client", "webhook")
API_TOKEN_STATUSES = ("active", "expiring", "expired", "revoked")

DAY_MS = 86_400_000
# "Expiring" shows this many days before a token expires.
EXPIRING_DAYS = 14
# Expiry choices for a new token, in days (None = never).
TOKEN_EXPIRY_DAYS: list[int | None] = [30, 90, 365, None]
# Minutes a short-lived token (client credentials) lasts.
TOKEN_LIFETIMES = [5, 15, 30, 60]
# After rotating, the old secret keeps working for this many hours (0 = stops at once).
ROTATION_GRACE_HOURS = [0, 24, 168]
MAX_REQUIRED_HEADERS = 5
HEADER_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9-]{1,63}")
RESERVED_HEADERS = ["authorization", "content-type", "content-length", "host", "cookie", "formalie-key", "accept",
                    "user-agent", "origin", "referer"]
CALL_KEY_MIN = 16

_PREVIEW = re.compile(r"formalie_(?:[a-z]+_)?(?:live|test)_")
_HEADER_VALUE = re.compile(r"[\x21-\x7e][\x20-\x7e]{0,199}")
_CALL_KEY = re.compile(r"[A-Za-z0-9._:-]+")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def token_prefix(kind: str, mode: str) -> str:
    """Every secret says Formalie (owner, 2026-10-06): `formalie_live_` / `formalie_test_` (bearer tokens),
    `formalie_client_…` (client ids), `formalie_secret_…` (client secrets), `formalie_sign_…` (signing secrets),
    `formalie_hook_…` (webhook tokens), `formalie_access_…` (short-lived tokens from the token address)."""
    part = {"static": "", "client": "secret_", "client_id": "client_", "signing": "sign_", "webhook": "hook_"}.get(kind, "access_")
    return f"formalie_{part}{mode}_"


def secret_preview(secret: str) -> str:
    """The visible part of a secret: its prefix and last 4 characters."""
    m = _PREVIEW.match(secret)
    return f"{m.group(0) if m else ''}…{secret[-4:]}"


def mask_value(value: str) -> str:
    """A header value shown masked except its last 4 characters."""
    return "••••" if len(value) <= 4 else f"••••{value[-4:]}"


def _ms(value: datetime | str) -> float:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.timestamp() * 1000


def token_status_of(revoked_at: Any, expires_at: Any, now: datetime | None = None) -> str:
    """Status from the dates: revoked, expired, expiring (within 14 days) or active."""
    if revoked_at:
        return "revoked"
    if expires_at:
        left = _ms(expires_at) - _ms(now or datetime.now(UTC))
        if left <= 0:
            return "expired"
        if left <= EXPIRING_DAYS * DAY_MS:
            return "expiring"
    return "active"


def scope_allows(scopes: dict[str, list[str]], endpoint_id: str, service_id: str, method: str) -> bool:
    """Whether a token's scopes allow a method on an endpoint (empty lists allow all)."""
    service = not scopes["services"] or service_id in scopes["services"]
    endpoint = not scopes["endpoints"] or endpoint_id in scopes["endpoints"]
    allowed = not scopes["methods"] or method in scopes["methods"]
    return service and endpoint and allowed


def token_reach(scopes: dict[str, list[str]], endpoint_id: str, service_id: str) -> str:
    """How a token's scopes reach an endpoint it may call: named, through its service, or as a token for everything."""
    if endpoint_id in scopes["endpoints"]:
        return "endpoint"
    if service_id in scopes["services"]:
        return "service"
    return "all"


def check_header_name(name: str) -> str | None:
    """Problems with a required header's name: `required`, `pattern` or `reserved` (set by Formalie itself)."""
    if not name:
        return "required"
    if not HEADER_NAME_PATTERN.fullmatch(name):
        return "pattern"
    lower = name.lower()
    if lower in RESERVED_HEADERS or lower.startswith("formalie-") or lower.startswith("x-formalie-"):
        return "reserved"
    return None


def check_header_value(value: str) -> str | None:
    """Problems with a required header's value: `required` or `chars` (printable ASCII only, up to 200)."""
    if not value:
        return "required"
    return None if _HEADER_VALUE.fullmatch(value) else "chars"


def check_call_key(key: str) -> str | None:
    """A Formalie-Key (owner, 2026-10-06): 16 to 100 letters, digits and . _ : -, and not an obvious pattern
    (`1111…`, `abab…`, counting). A UUID always passes."""
    if not key:
        return "missing"
    if len(key) > 100 or not _CALL_KEY.fullmatch(key):
        return "invalid"
    if len(key) < CALL_KEY_MIN:
        return "short"
    plain = re.sub(r"[._:-]", "", key.lower())
    if len(set(plain)) <= 4:
        return "weak"
    up = down = 0
    for i in range(1, len(plain)):
        step = ord(plain[i]) - ord(plain[i - 1])
        if step == 1:
            up += 1
        if step == -1:
            down += 1
    return "weak" if max(up, down) >= (len(plain) - 1) * 0.75 else None


def js_number(n: float | int) -> str:
    """A number as JSON.stringify writes it (2 not 2.0, 1e+21, 1e-7)."""
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if n != n or n in (float("inf"), float("-inf")):
        return "null"
    if n == 0:
        return "0"
    sign, digits, exponent = Decimal(repr(n)).normalize().as_tuple()
    text = "".join(str(d) for d in digits)
    point = len(text) + int(exponent)  # where the decimal point goes in `text`
    if -6 < point <= 21:
        if point <= 0:
            out = "0." + "0" * -point + text
        elif point >= len(text):
            out = text + "0" * (point - len(text))
        else:
            out = f"{text[:point]}.{text[point:]}"
    else:
        e = point - 1
        out = (text[0] + ("." + text[1:] if len(text) > 1 else "")) + f"e{'+' if e > 0 else '-'}{abs(e)}"
    return ("-" if sign else "") + out


def _js_key(key: str) -> list[int]:
    """Array.prototype.sort() order: UTF-16 code units."""
    return list(key.encode("utf-16-be"))


def canonical_json(value: Any) -> str:
    """The same JSON whatever the order of its keys, so a retry is recognised as the same request."""
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(v) for v in value) + "]"
    if isinstance(value, dict) and value:
        return "{" + ",".join(f"{json.dumps(k, ensure_ascii=False)}:{canonical_json(value[k])}"
                              for k in sorted(value, key=_js_key)) + "}"
    if isinstance(value, dict):
        return "{}"
    if isinstance(value, bool) or value is None:
        return "true" if value is True else "false" if value is False else "null"
    if isinstance(value, (int, float)):
        return js_number(value)
    return json.dumps(value, ensure_ascii=False)


# ── Secrets (the store's side; never sent back after the first time, except through reveal) ─────────────────

def new_secret(kind: str, mode: str) -> str:
    """A random secret with its prefix: 32 characters for tokens, 16 for client ids, 40 for client and signing secrets."""
    length = 32 if kind == "static" else 16 if kind == "client_id" else 40
    return token_prefix(kind, mode) + "".join(ALPHABET[b % len(ALPHABET)] for b in secrets.token_bytes(length))


def hash_secret(secret: str) -> str:
    """SHA-256 of a random secret (DATABASE-DESIGN → Secrets): what is kept and looked up."""
    return hashlib.sha256(secret.encode()).hexdigest()

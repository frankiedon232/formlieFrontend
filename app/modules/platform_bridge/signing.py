"""Signed calls from the platform admin to the internal admin API (PLATFORM-ADMIN-INTEGRATION §2).

Headers on every call:
    X-Platform-Key-Id        which shared key signed it (PLATFORM_ADMIN_KEYS "key_id:secret")
    X-Platform-Timestamp     Unix seconds; refused when more than PLATFORM_ADMIN_WINDOW_SECONDS (300) off
    X-Platform-Nonce         16 to 64 characters [A-Za-z0-9_-], used once (Redis, kept twice the window)
    X-Platform-Signature     "v1=" + hex HMAC-SHA256(secret, canonical string)
and on every change (POST):
    X-Platform-Staff-Id      the staff member's id in the platform admin
    X-Platform-Staff-Name    their name, percent-encoded UTF-8 (RFC 3986)
    X-Platform-Reason        why, percent-encoded UTF-8
    X-Platform-Approval-Id   the approval, when the action needed one
    Idempotency-Key          8 to 200 characters [A-Za-z0-9_.:-], one per action (a retry repeats it)

Canonical string (lines joined with "\\n", empty line for a header that is not sent):
    FORMALIE-PLATFORM-V1
    METHOD                   upper case
    PATH                     as sent, with "?" and the query when there is one
    TIMESTAMP
    NONCE
    SHA256(body)             hex of the raw body bytes (an empty body too)
    STAFF-ID
    STAFF-NAME               as sent (still percent-encoded)
    APPROVAL-ID
    REASON                   as sent (still percent-encoded)
    IDEMPOTENCY-KEY

The staff headers are inside the signature, so the name written into the workspace's audit trail is the one the
platform signed. In production the platform also presents its client certificate (mutual TLS, checked by Nginx);
see `mtls_ok`.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Mapping

SCHEME = "FORMALIE-PLATFORM-V1"
H_KEY = "x-platform-key-id"
H_TS = "x-platform-timestamp"
H_NONCE = "x-platform-nonce"
H_SIG = "x-platform-signature"
H_STAFF_ID = "x-platform-staff-id"
H_STAFF_NAME = "x-platform-staff-name"
H_APPROVAL = "x-platform-approval-id"
H_REASON = "x-platform-reason"
H_IDEMPOTENCY = "idempotency-key"
SIGNED_HEADERS = (H_STAFF_ID, H_STAFF_NAME, H_APPROVAL, H_REASON, H_IDEMPOTENCY)

NONCE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_.:-]{8,200}$")


def body_hash(body: bytes) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def canonical(method: str, path: str, timestamp: str, nonce: str, body: bytes, headers: Mapping[str, str]) -> str:
    lowered = {k.lower(): v for k, v in headers.items()}
    return "\n".join([SCHEME, method.upper(), path, timestamp, nonce, body_hash(body),
                      *(lowered.get(name, "") for name in SIGNED_HEADERS)])


def signature(secret: str, text: str) -> str:
    return "v1=" + hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest()


def keys_of(pairs: list[str]) -> dict[str, str]:
    """PLATFORM_ADMIN_KEYS entries "key_id:secret" → {key_id: secret}; malformed entries are ignored."""
    out: dict[str, str] = {}
    for pair in pairs:
        key_id, _, secret = pair.partition(":")
        if key_id.strip() and len(secret.strip()) >= 32:
            out[key_id.strip()] = secret.strip()
    return out


def fresh(timestamp: str, window_seconds: int, now: float | None = None) -> bool:
    try:
        moment = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs((now if now is not None else time.time()) - moment) <= window_seconds


def matches(secret: str, text: str, given: str) -> bool:
    return hmac.compare_digest(signature(secret, text), given or "")


def fingerprint(value: str) -> str:
    return re.sub(r"[^0-9a-f]", "", (value or "").lower())


def mtls_ok(verify: str | None, presented: str | None, allowed: list[str]) -> bool:
    """Nginx verified the client certificate (`ssl_verify_client on`; it passes $ssl_client_verify and the
    certificate's SHA-256 fingerprint) and the fingerprint is one of the platform's."""
    if (verify or "").upper() != "SUCCESS" or not presented:
        return False
    wanted = {fingerprint(f) for f in allowed if fingerprint(f)}
    return fingerprint(presented) in wanted


def sign_headers(key_id: str, secret: str, method: str, path: str, body: bytes = b"",
                 extra: Mapping[str, str] | None = None, *, timestamp: int | None = None,
                 nonce: str | None = None) -> dict[str, str]:
    """The headers the platform sends (used by tests and the platform's client as the reference)."""
    headers = dict(extra or {})
    ts = str(timestamp if timestamp is not None else int(time.time()))
    nonce = nonce or secrets.token_urlsafe(24)
    text = canonical(method, path, ts, nonce, body, headers)
    return {**headers, "X-Platform-Key-Id": key_id, "X-Platform-Timestamp": ts, "X-Platform-Nonce": nonce,
            "X-Platform-Signature": signature(secret, text)}

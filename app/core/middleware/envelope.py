"""5. Envelope: every API request and response is encrypted (SECURITY-PROTOCOL §2, §3, CLAUDE.md rule 3).

B0 builds the gate and the list of documented plaintext exceptions; it fails closed:
  - no envelope, or a malformed one              → FRM-SEC-1001 (plaintext, like the mock)
  - an envelope whose `kid` is not a live key    → FRM-SEC-1004 (plaintext, the client re-handshakes)
B1 adds the handshake (which stores the keys), freshness (FRM-SEC-1002), the nonce store (FRM-SEC-1003),
AES-GCM decryption with method+path binding (FRM-SEC-1005), the CSRF check and sealing every response.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from typing import Any

from redis.exceptions import RedisError

from app.core.cache.redis import get_redis
from app.core.config import Settings
from app.core.middleware.asgi import ASGIApp, Receive, Scope, Send, header, route_path, send_error

log = logging.getLogger("formalie.envelope")

ENVELOPE_HEADER = "x-formalie-envelope"
ENVELOPE_CONTENT_TYPE = "application/vnd.formalie.enc+json"
SESSION_KEY_PREFIX = "fm:v1:sec:key:"
MAX_ENVELOPE_BYTES = 2 * 1024 * 1024
BODY_METHODS = {"POST", "PUT", "PATCH"}


def plaintext_patterns(prefix: str) -> list[re.Pattern[str]]:
    """The documented exceptions (SECURITY-PROTOCOL §4, API-CONTRACT Conventions). Nothing else is plain."""
    p = re.escape(prefix)
    return [re.compile(rx) for rx in (
        rf"^{p}/health$",
        rf"^{p}/crypto/handshake$",
        rf"^{p}/auth/oauth/[a-z]+/start$",  # browser redirect
        rf"^{p}/auth/sso/start$",  # browser redirect
        rf"^{p}/downloads/[^/]+$",  # single-use signed download links
        rf"^{p}/response-exports/[^/]+$",
        rf"^{p}/response-files/[^/]+$",
        rf"^{p}/datasource-exports/[^/]+$",
        rf"^{p}/billing/webhooks/payoneer$",  # signed by the processor
        rf"^{p}/internal/",  # service to service (server-only token / mTLS), never through the public proxy
    )]


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64_len(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return len(base64.b64decode(value, validate=True))
    except (binascii.Error, ValueError):
        return None


def parse_envelope(raw: bytes) -> dict[str, Any] | None:
    """Checks the envelope's structure: {kid, iv (12 bytes), ts (ms), nonce (16 bytes), ct}."""
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    kid, ts = data.get("kid"), data.get("ts")
    if not isinstance(kid, str) or not 8 <= len(kid) <= 64:
        return None
    if not isinstance(ts, int) or isinstance(ts, bool) or ts <= 0:
        return None
    if _b64_len(data.get("iv")) != 12 or _b64_len(data.get("nonce")) != 16:
        return None
    ct_len = _b64_len(data.get("ct"))
    if ct_len is None or ct_len < 16:  # at least the GCM tag
        return None
    return data


async def _read_body(receive: Receive, limit: int) -> bytes | None:
    chunks: list[bytes] = []
    size = 0
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return None
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
        if not message.get("more_body"):
            return b"".join(chunks)


class EnvelopeMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.prefix = settings.api_prefix
        self.plain = plaintext_patterns(settings.api_prefix)

    def is_plaintext(self, path: str) -> bool:
        return any(rx.match(path) for rx in self.plain)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = route_path(scope)
        if scope["type"] != "http" or not path.startswith(self.prefix) or self.is_plaintext(path):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method == "OPTIONS":  # same-origin portal: no CORS preflights to answer
            await send_error(send, "FRM-GEN-1004")
            return

        envelope: dict[str, Any] | None = None
        if method in BODY_METHODS:
            content_type = (header(scope, "content-type") or "").split(";")[0].strip().lower()
            raw = await _read_body(receive, MAX_ENVELOPE_BYTES)
            if raw is None:
                return
            if content_type == ENVELOPE_CONTENT_TYPE:
                envelope = parse_envelope(raw)
        else:
            encoded = header(scope, ENVELOPE_HEADER)
            if encoded:
                try:
                    envelope = parse_envelope(_b64url_decode(encoded))
                except (binascii.Error, ValueError):
                    envelope = None

        if envelope is None:
            log.warning("FRM-SEC-1001 missing or malformed envelope", extra={"error_code": "FRM-SEC-1001", "method": method})
            await send_error(send, "FRM-SEC-1001")
            return

        try:
            key = await get_redis().get(SESSION_KEY_PREFIX + envelope["kid"])
        except RedisError:
            log.exception("FRM-GEN-5003 session key store unavailable", extra={"error_code": "FRM-GEN-5003"})
            await send_error(send, "FRM-GEN-5003")
            return
        if key is None:
            log.info("FRM-SEC-1004 unknown or expired session key", extra={"error_code": "FRM-SEC-1004"})
            await send_error(send, "FRM-SEC-1004")
            return

        # B1 replaces this: freshness, nonce, decrypt, bind method+path, CSRF, hand the decrypted payload to the
        # app and seal the response. Before B1 no key can exist (there is no handshake), so this fails closed.
        log.error("FRM-SEC-1005 envelope decryption arrives in B1", extra={"error_code": "FRM-SEC-1005"})
        await send_error(send, "FRM-SEC-1005")

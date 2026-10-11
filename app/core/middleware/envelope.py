"""5 + 5b. Envelope and encrypted references: every API request and response is encrypted (SECURITY-PROTOCOL §2,
§3, §10; CLAUDE.md rules 3 and 7). Port of the mock's server/mock/core/route.ts, in the same order:

  1. no or malformed envelope                        → FRM-SEC-1001 (plain)
  2. unknown / expired key, or a key of another host → FRM-SEC-1004 (plain: the client re-handshakes)
  3. older or newer than 60 s                        → FRM-SEC-1002 (sealed, from here on)
  4. nonce seen before (Redis SET NX EX 120)         → FRM-SEC-1003
  5. decryption fails, or method / path not the ones the envelope was sealed for → FRM-SEC-1005
  6. POST / PUT / PATCH / DELETE without a valid CSRF token for this key → FRM-SEC-1006
then references in the path, query and body become ids, the app gets the decrypted body as plain JSON, and its
reply is sealed with the same key after every id in it became a reference. Documented plaintext routes pass.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote, urlencode

from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.context import get_context
from app.core.errors.codes import ERROR_CODES
from app.core.errors.exceptions import error_body
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send, header, route_path, send_error
from app.core.middleware.tenant import normalise_host
from app.core.security import envelope as env
from app.core.security.csrf import HEADER as CSRF_HEADER
from app.core.security.csrf import csrf_token_valid
from app.core.security.refs import get_codec
from app.core.security.session_keys import claim_nonce, use_session_key

log = logging.getLogger("formalie.envelope")

ENVELOPE_HEADER = env.ENVELOPE_HEADER
ENVELOPE_CONTENT_TYPE = env.ENVELOPE_CONTENT_TYPE
SESSION_KEY_PREFIX = "fm:v1:sec:key:"
MAX_ENVELOPE_BYTES = 2 * 1024 * 1024
BODY_METHODS = {"POST", "PUT", "PATCH"}
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


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


def _well_formed(data: Any) -> bool:
    if not env.is_envelope(data) or not 8 <= len(data["kid"]) <= 64 or data["ts"] <= 0:
        return False
    try:
        return (len(env.b64decode(data["iv"])) == 12 and len(env.b64decode(data["nonce"])) == 16
                and len(env.b64decode(data["ct"])) >= 16)
    except ValueError:
        return False


def parse_envelope(raw: bytes) -> dict[str, Any] | None:
    """A well-formed envelope: the five fields, iv 12 bytes, nonce 16 bytes, ct at least a GCM tag."""
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    return data if _well_formed(data) else None


def flatten_query(query: dict[str, Any]) -> list[tuple[str, str]]:
    """The decrypted query back into `key=value` pairs. Lists repeat the key; nested objects become key[sub]."""
    pairs: list[tuple[str, str]] = []

    def add(key: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for sub, item in value.items():
                add(f"{key}[{sub}]", item)
        elif isinstance(value, list):
            for item in value:
                add(key, item)
        elif isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        else:
            pairs.append((key, str(value)))

    for k, v in query.items():
        add(str(k), v)
    return pairs


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


def _flag(name: str) -> None:
    ctx = get_context()
    if ctx is not None:
        ctx.flags.add(name)


async def _send_sealed(send: Send, status: int, body: Any, key: bytes, kid: str,
                       headers: list[tuple[bytes, bytes]] | None = None) -> None:
    sealed = env.to_json(env.seal(key, kid, get_codec().encode_ids(body)))
    # The route's own headers stay (Set-Cookie for the refresh cookie, Cache-Control …); only the body changes.
    kept = [(k, v) for k, v in (headers or []) if k.lower() not in (b"content-type", b"content-length")]
    await send({"type": "http.response.start", "status": status, "headers": [
        *kept, (b"content-type", ENVELOPE_CONTENT_TYPE.encode()), (b"content-length", str(len(sealed)).encode()),
    ]})
    await send({"type": "http.response.body", "body": sealed})


async def _sealed_error(send: Send, code: str, key: bytes, kid: str) -> None:
    ctx = get_context()
    if ctx is not None:
        ctx.error_code = code
    await _send_sealed(send, ERROR_CODES[code].status, error_body(code, ctx.trace_id if ctx else None), key, kid)


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

        # 1. The envelope
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
            decoded = env.decode_header(encoded) if encoded else None
            envelope = decoded if decoded is not None and _well_formed(decoded) else None
        if envelope is None:
            _flag("invalid_envelope")
            log.warning("FRM-SEC-1001 missing or malformed envelope", extra={"error_code": "FRM-SEC-1001", "method": method})
            await send_error(send, "FRM-SEC-1001")
            return

        # 2. Its key, made by a handshake on this same host
        kid = envelope["kid"]
        try:
            session = await use_session_key(kid)
        except RedisError:
            log.error("FRM-GEN-5003 session key store unavailable", extra={"error_code": "FRM-GEN-5003"})
            await send_error(send, "FRM-GEN-5003")
            return
        ctx = get_context()
        host = normalise_host(ctx.host) if ctx and ctx.host else ""
        if session is None or (session.host and host and normalise_host(session.host) != host):
            _flag("unknown_session_key")
            log.info("FRM-SEC-1004 unknown or expired session key", extra={"error_code": "FRM-SEC-1004"})
            await send_error(send, "FRM-SEC-1004")
            return
        key = session.key

        # 3. Fresh  4. Not replayed
        if not env.is_fresh(int(envelope["ts"])):
            log.info("FRM-SEC-1002 envelope expired", extra={"error_code": "FRM-SEC-1002"})
            await _sealed_error(send, "FRM-SEC-1002", key, kid)
            return
        try:
            first_use = await claim_nonce(envelope["nonce"])
        except RedisError:
            await _sealed_error(send, "FRM-GEN-5003", key, kid)
            return
        if not first_use:
            _flag("replay")
            log.warning("FRM-SEC-1003 replayed envelope", extra={"error_code": "FRM-SEC-1003"})
            await _sealed_error(send, "FRM-SEC-1003", key, kid)
            return

        # 5. Decrypts, and was sealed for this method and this address
        try:
            payload = env.open_envelope(key, envelope)
        except env.EnvelopeError:
            log.warning("FRM-SEC-1005 envelope did not decrypt", extra={"error_code": "FRM-SEC-1005"})
            await _sealed_error(send, "FRM-SEC-1005", key, kid)
            return
        if (not isinstance(payload, dict) or str(payload.get("method", "")).upper() != method
                or payload.get("path") != scope.get("path")):
            _flag("envelope_mismatch")
            log.warning("FRM-SEC-1005 envelope bound to another method or path", extra={"error_code": "FRM-SEC-1005"})
            await _sealed_error(send, "FRM-SEC-1005", key, kid)
            return

        # 6. CSRF on state-changing requests
        if method in STATE_CHANGING and not csrf_token_valid(header(scope, CSRF_HEADER), kid):
            log.info("FRM-SEC-1006 CSRF token missing or expired", extra={"error_code": "FRM-SEC-1006"})
            await _sealed_error(send, "FRM-SEC-1006", key, kid)
            return

        # References → ids (path, query, body); the app sees plain JSON and real ids.
        codec = get_codec()
        seen: set[str] = set()
        raw_query = payload.get("query")
        query = codec.decode_ids(raw_query if isinstance(raw_query, dict) else {}, seen)
        body = codec.decode_ids(payload.get("body"), seen)
        new_path = codec.decode_path(scope["path"], seen)
        if ctx is not None:
            ctx.kid = kid
            ctx.ref_ids = seen
            ctx.decrypted_payload = {"method": method, "path": payload.get("path"), "query": query, "body": body}

        body_bytes = env.to_json(body) if body is not None else b""
        scope["path"] = new_path
        scope["raw_path"] = quote(new_path).encode()
        scope["query_string"] = urlencode(flatten_query(query)).encode()
        scope["headers"] = [(k, v) for k, v in scope.get("headers", [])
                            if k not in (b"content-type", b"content-length")] + [
            (b"content-type", b"application/json"), (b"content-length", str(len(body_bytes)).encode())]

        delivered = False

        async def plain_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return await receive()

        # The reply: collected, ids → references, sealed with the same key.
        response: dict[str, Any] = {"status": 500, "chunks": [], "headers": []}

        async def sealing_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = list(message.get("headers", []))
                return
            if message["type"] == "http.response.body":
                response["chunks"].append(message.get("body", b""))
                if not message.get("more_body"):
                    raw_reply = b"".join(response["chunks"])
                    try:
                        reply: Any = json.loads(raw_reply) if raw_reply else None
                    except ValueError:
                        log.error("FRM-GEN-5000 non-JSON reply on an enveloped route", extra={"error_code": "FRM-GEN-5000"})
                        reply, response["status"] = error_body("FRM-GEN-5000", ctx.trace_id if ctx else None), 500
                    await _send_sealed(send, response["status"], reply, key, kid, response["headers"])
                return
            await send(message)

        await self.app(scope, plain_receive, sealing_send)

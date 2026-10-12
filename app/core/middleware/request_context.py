"""1. RequestContext: trace_id (UUIDv7, returned as X-Trace-Id), start time, real client IP, user agent, host.

Forwarding headers (X-Forwarded-For, X-Forwarded-Host, CF-Connecting-IP) are trusted only when the direct
peer is a trusted proxy (TRUSTED_PROXIES: Nginx, the Nuxt dev proxy). Otherwise the socket peer and Host win.

Edge trust (production, 2026-10-12): the Cloudflare Worker in front of every portal host forwards `/api/*` to the
services host with `X-Formalie-Edge: <EDGE_SECRET>`. A request carrying the right secret (constant-time compare,
only when EDGE_SECRET is set) has its X-Forwarded-Host, X-Forwarded-Proto and X-Forwarded-For (one visitor
address) trusted whatever the socket peer. While EDGE_SECRET is set, X-Forwarded-Host counts only with the secret
(Nginx passes the Worker's headers through unchanged, so a trusted peer alone proves nothing about the host).
A wrong or missing secret: the forwarded headers are ignored as for an untrusted peer. The secret is never logged.
Also the last line of defence: anything an inner layer throws becomes FRM-GEN-5000.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import time
from functools import lru_cache

from app.core.config import Settings
from app.core.context import RequestContext, reset_context, set_context
from app.core.ids import uuid7
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send, header, send_error

log = logging.getLogger("formalie.request")

IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@lru_cache(maxsize=1024)
def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    value = value.strip()
    if value.startswith("[") and "]" in value:
        value = value[1:value.index("]")]
    elif value.count(":") == 1:  # ipv4:port
        value = value.split(":")[0]
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


EDGE_HEADER = "x-formalie-edge"


class TrustedProxies:
    def __init__(self, cidrs: list[str], edge_secret: str | None = None) -> None:
        self.networks: list[IpNetwork] = [ipaddress.ip_network(c, strict=False) for c in cidrs]
        self._edge = (edge_secret or "").encode()

    @classmethod
    def from_settings(cls, settings: Settings) -> TrustedProxies:
        secret = settings.edge_secret.get_secret_value() if settings.edge_secret else None
        return cls(settings.trusted_proxies, secret)

    def trusts(self, ip: str | None) -> bool:
        parsed = _parse_ip(ip) if ip else None
        return parsed is not None and any(parsed in net for net in self.networks)

    def edge(self, scope: Scope) -> bool:
        """The request came through Formalie's own edge (the Worker): it carries the right X-Formalie-Edge."""
        if not self._edge:
            return False
        given = header(scope, EDGE_HEADER)
        return given is not None and hmac.compare_digest(given.encode("latin-1", "replace"), self._edge)

    def client_ip(self, peer: str | None, scope: Scope) -> str | None:
        if self.edge(scope):
            # The Worker sends the visitor's address alone; anything a proxy appended after it is not the visitor.
            first = (header(scope, "x-forwarded-for") or "").split(",")[0]
            parsed = _parse_ip(first) if first.strip() else None
            if parsed is not None:
                return str(parsed)
        if not self.trusts(peer):
            return peer
        cf = header(scope, "cf-connecting-ip")
        if cf and _parse_ip(cf):
            return str(_parse_ip(cf))
        forwarded = header(scope, "x-forwarded-for")
        if forwarded:
            # Right to left: the first address that is not one of our proxies is the client.
            for hop in reversed([h for h in forwarded.split(",") if h.strip()]):
                parsed = _parse_ip(hop)
                if parsed is None:
                    break
                if not self.trusts(str(parsed)):
                    return str(parsed)
        return peer

    def host(self, peer: str | None, scope: Scope) -> str | None:
        if self.edge(scope) or (not self._edge and self.trusts(peer)):
            forwarded = (header(scope, "x-forwarded-host") or "").split(",")[0].strip()
            if forwarded:
                return forwarded
        return header(scope, "host")

    def scheme(self, peer: str | None, scope: Scope) -> str | None:
        """http / https as the visitor used it: X-Forwarded-Proto from the edge or a trusted proxy, else the socket's."""
        if self.edge(scope) or self.trusts(peer):
            forwarded = (header(scope, "x-forwarded-proto") or "").split(",")[0].strip().lower()
            if forwarded in ("http", "https"):
                return forwarded
        value = scope.get("scheme")
        return str(value) if value else None


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.proxies = TrustedProxies.from_settings(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        peer = scope["client"][0] if scope.get("client") else None
        ctx = RequestContext(
            trace_id=str(uuid7()),
            started_at=time.perf_counter(),
            client_ip=self.proxies.client_ip(peer, scope),
            peer_ip=peer,
            proxy_trusted=self.proxies.trusts(peer),
            edge_trusted=self.proxies.edge(scope),
            scheme=self.proxies.scheme(peer, scope),
            user_agent=(header(scope, "user-agent") or "")[:512] or None,
            host=self.proxies.host(peer, scope),
            method=scope.get("method"),
            path=str(scope.get("path") or "")[:500] or None,
        )
        scope.setdefault("state", {})["ctx"] = ctx
        token = set_context(ctx)
        started = False

        async def send_with_trace(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message.setdefault("headers", [])
                message["headers"] = [*message["headers"], (b"x-trace-id", ctx.trace_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        except Exception:
            log.exception("FRM-GEN-5000 unhandled error in the middleware chain", extra={"error_code": "FRM-GEN-5000"})
            if not started:
                await send_error(send_with_trace, "FRM-GEN-5000")
        finally:
            reset_context(token)

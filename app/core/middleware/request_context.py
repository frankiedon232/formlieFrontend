"""1. RequestContext: trace_id (UUIDv7, returned as X-Trace-Id), start time, real client IP, user agent, host.

Forwarding headers (X-Forwarded-For, X-Forwarded-Host, CF-Connecting-IP) are trusted only when the direct
peer is a trusted proxy (TRUSTED_PROXIES: Nginx, the Nuxt dev proxy). Otherwise the socket peer and Host win.
Also the last line of defence: anything an inner layer throws becomes FRM-GEN-5000.
"""

from __future__ import annotations

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


class TrustedProxies:
    def __init__(self, cidrs: list[str]) -> None:
        self.networks: list[IpNetwork] = [ipaddress.ip_network(c, strict=False) for c in cidrs]

    def trusts(self, ip: str | None) -> bool:
        parsed = _parse_ip(ip) if ip else None
        return parsed is not None and any(parsed in net for net in self.networks)

    def client_ip(self, peer: str | None, scope: Scope) -> str | None:
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
        if self.trusts(peer):
            forwarded = header(scope, "x-forwarded-host")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return header(scope, "host")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.proxies = TrustedProxies(settings.trusted_proxies)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        peer = scope["client"][0] if scope.get("client") else None
        ctx = RequestContext(
            trace_id=str(uuid7()),
            started_at=time.perf_counter(),
            client_ip=self.proxies.client_ip(peer, scope),
            user_agent=(header(scope, "user-agent") or "")[:512] or None,
            host=self.proxies.host(peer, scope),
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

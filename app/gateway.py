r"""The public API service on `api.formalie.*` (BACKEND-SPEC §14, SECURITY-PROTOCOL §9): its own app, so it can run as
its own process and deployment with its own limits. Plain HTTPS + JSON; no portal envelope, CSRF or workspace host.

    fmly\Scripts\python.exe -m app.gateway
    uvicorn app.gateway:app --host 0.0.0.0 --port 5005 --no-proxy-headers --ssl-certfile ... --ssl-keyfile ...

The main app (app/run.py) also forwards requests whose host is `api.<ROOT_DOMAIN>` to this app (ApiHostMiddleware),
so in development one server answers both. `--no-proxy-headers` is required for the same reason as the main app:
X-Forwarded-For is read only from TRUSTED_PROXIES (request_context.py).

Middleware, outermost first: request context (trace id, real client IP) → request log (the platform's log of every
request, bodies left out: they are answers to forms, the workspace's own API log keeps them when it chooses) →
security headers → a ceiling per caller IP across every workspace. Each workspace's own limits, access rules and
tokens are checked in the order of the mock (app/modules/api_service/gateway.py).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from starlette.applications import Starlette
from starlette.routing import Route

from app.core.cache.redis import close_redis
from app.core.config import Settings, get_settings
from app.core.db.engines import dispose_engines
from app.core.context import get_context
from app.core.logging.setup import configure_logging
from app.core.middleware.asgi import ASGIApp, Receive, Scope, Send
from app.core.middleware.rate_limit import RateLimiterUnavailable, SlidingWindowLimiter
from app.core.middleware.request_context import RequestContextMiddleware
from app.core.middleware.request_log import RequestLogMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.net import ip_bucket
from app.core.errors.codes import ERROR_CODES

log = logging.getLogger("formalie.api.gateway")

ALL_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"]
BODY_FIELDS = ("request_body", "request_body_text", "request_body_keys", "request_body_fields", "response_body")


class BodylessShipper:
    """The platform's request log without bodies (answers to forms stay out of it; sizes and hashes are kept)."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def submit(self, record: dict[str, Any]) -> None:
        self.inner.submit({**record, **{name: None for name in BODY_FIELDS}})

    async def drain(self) -> None:
        await self.inner.drain()


class GatewayIpLimit:
    """A ceiling per caller IP across every workspace (GATEWAY_IP_PER_MINUTE), before any lookup. Over it: 429
    FRM-GEN-1029 in the API service's own error shape."""

    def __init__(self, app: ASGIApp, settings: Settings, limiter: SlidingWindowLimiter | None = None) -> None:
        self.app = app
        self.settings = settings
        self.limiter = limiter or SlidingWindowLimiter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return
        ctx = get_context()
        ip = ip_bucket(ctx.client_ip if ctx else None)  # IPv6 by its /64 (M15)
        try:
            result = await self.limiter.hit(f"gw:ip:{ip}", self.settings.gateway_ip_per_minute, 60)
        except RateLimiterUnavailable as exc:
            if not self.settings.rate_limit_fail_open:
                await _send(send, "FRM-GEN-5003", {})
                return
            log.warning("gateway rate limiter unavailable, allowing request", extra={"error": str(exc)})
            await self.app(scope, receive, send)
            return
        if not result.allowed:
            if ctx is not None:
                ctx.rate_limited, ctx.error_code = True, "FRM-GEN-1029"
            await _send(send, "FRM-GEN-1029", {"Retry-After": str(result.retry_after),
                                               "X-RateLimit-Limit": str(result.limit), "X-RateLimit-Remaining": "0"})
            return
        await self.app(scope, receive, send)


async def _send(send: Send, code: str, headers: dict[str, str]) -> None:
    definition = ERROR_CODES[code]
    body = json.dumps({"error": {"code": code, "message": definition.message, "details": []}}).encode()
    raw = [(b"content-type", b"application/json; charset=utf-8"), (b"content-length", str(len(body)).encode())]
    raw += [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    await send({"type": "http.response.start", "status": definition.status, "headers": raw})
    await send({"type": "http.response.body", "body": body})


async def _endpoint(request: Any) -> Any:
    from app.modules.api_service.gateway import handle_request

    return await handle_request(request)


def _lifespan(shipper: Any | None) -> Any:
    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        from app.core.startup import ensure_safe_start

        ensure_safe_start(get_settings())  # APP_ENV explicit; staging and production with their secrets (M5)
        yield
        if shipper is not None:
            await shipper.drain()
        await dispose_engines()
        await close_redis()

    return lifespan


def create_gateway_app(settings: Settings | None = None, *, request_log_shipper: Any | None = None,
                       limiter: SlidingWindowLimiter | None = None, configure: bool = True) -> Starlette:
    settings = settings or get_settings()
    if configure:
        configure_logging(settings)
    if request_log_shipper is None and settings.request_log_enabled:
        from app.modules.logs.service import RequestLogShipper

        request_log_shipper = RequestLogShipper(settings.request_log_sink)
    app = Starlette(routes=[Route("/{path:path}", _endpoint, methods=ALL_METHODS)],
                    lifespan=_lifespan(request_log_shipper))
    # Starlette runs the last added first, so this list is innermost → outermost.
    app.add_middleware(GatewayIpLimit, settings=settings, limiter=limiter)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    # No bodies at all, and none held while they stream: the gateway reads its own, capped (M12)
    app.add_middleware(RequestLogMiddleware, shipper=BodylessShipper(request_log_shipper) if request_log_shipper else None,
                       settings=settings, body_policy="none")
    app.add_middleware(RequestContextMiddleware, settings=settings)
    return app


def __getattr__(name: str) -> Any:
    """`app.gateway:app` for uvicorn, made on first use (importing this module makes no app)."""
    if name == "app":
        made = create_gateway_app()
        globals()["app"] = made
        return made
    raise AttributeError(name)


if __name__ == "__main__":
    import uvicorn

    run_settings = get_settings()
    uvicorn.run(
        "app.gateway:app",
        host=run_settings.server_host,
        port=run_settings.gateway_port,
        ssl_certfile=run_settings.ssl_certfile,
        ssl_keyfile=run_settings.ssl_keyfile,
        proxy_headers=False,  # see the module docstring
        log_config=None,
    )

r"""Formalie API.

    fmly\Scripts\python.exe -m app.run
    uvicorn app.run:app --host 0.0.0.0 --port 5004 --no-proxy-headers --ssl-certfile ... --ssl-keyfile ...

`--no-proxy-headers` is required: the app reads X-Forwarded-For / X-Forwarded-Host itself, and only from
TRUSTED_PROXIES (request_context.py). Uvicorn's own handling would replace the proxy's address with the visitor's
before the app sees it, so the proxy would no longer be recognised and workspaces not found from their host.

Requests for api.<ROOT_DOMAIN> (the public API service) are handed to app/gateway.py, which also runs on its own:
`fmly\Scripts\python.exe -m app.gateway` (port GATEWAY_PORT, 5005).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.cache.redis import close_redis
from app.core.config import Settings, get_settings
from app.core.db.engines import dispose_engines
from app.core.errors.handlers import install_exception_handlers
from app.core.logging.setup import configure_logging
from app.core.middleware.api_host import ApiHostMiddleware
from app.core.middleware.envelope import EnvelopeMiddleware
from app.core.middleware.rate_limit import IpRateLimitMiddleware, SlidingWindowLimiter
from app.core.middleware.request_context import RequestContextMiddleware
from app.core.middleware.request_log import RequestLogMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.middleware.tenant import TenantMiddleware, TenantResolver


def make_lifespan(shipper: Any | None) -> Callable[[FastAPI], Any]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if shipper is not None:
            await shipper.drain()  # write what is still queued before the pools close
        await dispose_engines()
        await close_redis()

    return lifespan


def create_app(
    settings: Settings | None = None,
    *,
    tenant_resolver: TenantResolver | None = None,
    limiter: SlidingWindowLimiter | None = None,
    request_log_shipper: Any | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    docs = settings.docs_enabled and not settings.is_production
    if request_log_shipper is None and settings.request_log_enabled:
        from app.modules.logs.service import RequestLogShipper

        request_log_shipper = RequestLogShipper(settings.request_log_sink)
    app = FastAPI(
        title="Formalie API",
        version=settings.app_release,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        lifespan=make_lifespan(request_log_shipper),
    )
    install_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    # The platform admin's internal API (B16): /internal/admin/v1, signed, private network (mutual TLS in production)
    from app.modules.platform_bridge.admin_routes import router as platform_admin_router

    app.include_router(platform_admin_router)

    if tenant_resolver is None:
        from app.modules.tenants.service import TenantDirectory

        tenant_resolver = TenantDirectory()

    # Pure ASGI middleware, BACKEND-SPEC §1. Starlette runs the last added first, so this list is innermost → outermost.
    app.add_middleware(EnvelopeMiddleware, settings=settings)  # 5 (5b references: B1)
    app.add_middleware(TenantMiddleware, settings=settings, resolver=tenant_resolver)  # 4
    app.add_middleware(IpRateLimitMiddleware, settings=settings, limiter=limiter)  # 3
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)  # 2
    app.add_middleware(RequestLogMiddleware, shipper=request_log_shipper, settings=settings)  # 10, outside the rejecting layers: every request is recorded
    app.add_middleware(RequestContextMiddleware, settings=settings)  # 1
    # 0: api.<ROOT_DOMAIN> is the public API service's own app (app/gateway.py), no portal layer
    app.add_middleware(ApiHostMiddleware, settings=settings, request_log_shipper=request_log_shipper)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    run_settings = get_settings()
    uvicorn.run(
        "app.run:app",
        host=run_settings.server_host,
        port=run_settings.server_port,
        ssl_certfile=run_settings.ssl_certfile,
        ssl_keyfile=run_settings.ssl_keyfile,
        proxy_headers=False,  # see the module docstring
        log_config=None,  # our JSON logging (configure_logging) handles uvicorn's loggers
    )

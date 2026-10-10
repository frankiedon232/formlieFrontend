"""Formalie API. `uvicorn app.run:app --host 0.0.0.0 --port 5004 --ssl-certfile … --ssl-keyfile …`"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.cache.redis import close_redis
from app.core.config import Settings, get_settings
from app.core.db.engines import dispose_engines
from app.core.errors.handlers import install_exception_handlers
from app.core.logging.setup import configure_logging
from app.core.middleware.envelope import EnvelopeMiddleware
from app.core.middleware.rate_limit import IpRateLimitMiddleware, SlidingWindowLimiter
from app.core.middleware.request_context import RequestContextMiddleware
from app.core.middleware.request_log import RequestLogMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.middleware.tenant import TenantMiddleware, TenantResolver


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engines()
    await close_redis()


def create_app(
    settings: Settings | None = None,
    *,
    tenant_resolver: TenantResolver | None = None,
    limiter: SlidingWindowLimiter | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    docs = settings.docs_enabled and not settings.is_production
    app = FastAPI(
        title="Formalie API",
        version=settings.app_release,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        lifespan=lifespan,
    )
    install_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    if tenant_resolver is None:
        from app.modules.tenants.service import TenantDirectory

        tenant_resolver = TenantDirectory()

    # Pure ASGI middleware, BACKEND-SPEC §1. Starlette runs the last added first, so this list is innermost → outermost.
    app.add_middleware(EnvelopeMiddleware, settings=settings)  # 5 (5b references: B1)
    app.add_middleware(TenantMiddleware, settings=settings, resolver=tenant_resolver)  # 4
    app.add_middleware(IpRateLimitMiddleware, settings=settings, limiter=limiter)  # 3
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)  # 2
    app.add_middleware(RequestLogMiddleware)  # 10, kept outside the rejecting layers so every request is logged
    app.add_middleware(RequestContextMiddleware, settings=settings)  # 1
    return app


app = create_app()

"""Async engines: one primary (writes, read-after-write) and any number of replicas (lists, reports, analytics).

Behind PgBouncer in transaction mode asyncpg must not cache prepared statements (BACKEND-SPEC §3).
Every connection sets `statement_timeout` and an application name for pg_stat_activity.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings, get_settings
from app.core.ids import uuid7


def async_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


def make_engine(url: str, settings: Settings, *, name: str, statement_timeout_ms: int | None = None) -> AsyncEngine:
    connect_args: dict[str, object] = {
        "server_settings": {
            "application_name": f"formalie-api-{name}",
            "statement_timeout": str(statement_timeout_ms or settings.db_statement_timeout_ms),
            "timezone": "UTC",
            "search_path": f"{settings.db_schema}, platform",
        },
        "timeout": settings.db_pool_timeout,
    }
    if settings.db_pgbouncer:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: f"__fm_{uuid7().hex}__"
    return create_async_engine(
        async_url(url),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args,
    )


class Engines:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.db_app_url is None:
            raise RuntimeError("DB_APP_URL is not set (see .env.example)")
        self.primary = make_engine(self.settings.db_app_url.get_secret_value(), self.settings, name="primary")
        self.replicas = [
            make_engine(url.get_secret_value(), self.settings, name=f"replica{i}")
            for i, url in enumerate(self.settings.db_replica_urls)
        ]
        self._next_replica: Iterator[AsyncEngine] = itertools.cycle(self.replicas or [self.primary])

    def replica(self) -> AsyncEngine:
        """Round-robin over replicas; the primary when none is configured."""
        return next(self._next_replica)

    async def dispose(self) -> None:
        for engine in (self.primary, *self.replicas):
            await engine.dispose()


_engines: Engines | None = None


def get_engines() -> Engines:
    global _engines
    if _engines is None:
        _engines = Engines()
    return _engines


def set_engines(engines: Engines | None) -> None:
    global _engines
    _engines = engines


async def dispose_engines() -> None:
    global _engines
    if _engines is not None:
        await _engines.dispose()
        _engines = None

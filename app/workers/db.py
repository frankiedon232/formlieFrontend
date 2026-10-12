"""Synchronous engine for maintenance workers (outbox relay, partitions), as `formalie_worker` (DB_RELAY_URL).

`formalie_worker` reads every workspace's outbox rows (BYPASSRLS) but holds privileges on nothing else.
Workers that act for one workspace use the app role and `db_session(tenant_id=…)` instead.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


def _sync_url(url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache
def worker_engine() -> Engine:
    settings = get_settings()
    if settings.db_relay_url is None:
        raise RuntimeError("DB_RELAY_URL is not set (see .env.example)")
    return create_engine(
        _sync_url(settings.db_relay_url.get_secret_value()),
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
        hide_parameters=True,  # SQL errors in logs never carry bound values (B17 review L18)
        connect_args={"application_name": "formalie-worker",
                      "options": f"-c statement_timeout=30000 -c search_path={settings.db_schema},platform"},
    )

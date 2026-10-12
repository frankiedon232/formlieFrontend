"""Health of Formalie's services for the platform admin's Operations page (`GET /internal/admin/v1/health/services`).

Each check has a short time-out and reports `ok` / `down` (or `degraded`) with its latency; no addresses, user names
or secrets in the answer. Checks: the primary database and each replica, Redis, RabbitMQ with every Celery queue
(messages waiting, workers attached, dead letters), and the event outbox (events waiting to be published, the
oldest one's age).
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings

TIMEOUT_S = 3.0
OUTBOX_LATE_S = 60  # events older than this still waiting: degraded


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


async def _database(engine: Any, name: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        async def ping() -> None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        await asyncio.wait_for(ping(), TIMEOUT_S)
        return {"name": name, "status": "ok", "latency_ms": _ms(started)}
    except Exception:  # noqa: BLE001
        return {"name": name, "status": "down", "latency_ms": _ms(started)}


async def _redis() -> dict[str, Any]:
    from app.core.cache.redis import get_redis

    started = time.monotonic()
    try:
        await asyncio.wait_for(get_redis().ping(), TIMEOUT_S)
        return {"name": "redis", "status": "ok", "latency_ms": _ms(started)}
    except Exception:  # noqa: BLE001
        return {"name": "redis", "status": "down", "latency_ms": _ms(started)}


def _queues_sync() -> dict[str, Any]:
    """RabbitMQ: each Celery queue and its dead letters (passive declare: nothing is created)."""
    from kombu import Connection

    from app.workers.queues import QUEUE_NAMES

    started = time.monotonic()
    queues = []
    with Connection(get_settings().rabbitmq_url.get_secret_value(), connect_timeout=TIMEOUT_S) as conn:
        channel = conn.channel()
        for name in QUEUE_NAMES:
            entry: dict[str, Any] = {"name": name}
            for key, queue in (("waiting", name), ("dead", f"{name}.dead")):
                try:
                    _, messages, consumers = channel.queue_declare(queue=queue, passive=True)
                    entry[key] = messages
                    if key == "waiting":
                        entry["workers"] = consumers
                except Exception:  # noqa: BLE001 (not declared yet: no worker ever started)
                    channel = conn.channel()
                    entry.setdefault(key, None)
                    entry.setdefault("workers", 0)
            queues.append(entry)
    return {"name": "rabbitmq", "status": "ok", "latency_ms": _ms(started), "queues": queues}


async def _rabbitmq() -> dict[str, Any]:
    started = time.monotonic()
    try:
        return await asyncio.wait_for(asyncio.to_thread(_queues_sync), TIMEOUT_S * 3)
    except Exception:  # noqa: BLE001
        return {"name": "rabbitmq", "status": "down", "latency_ms": _ms(started), "queues": []}


async def _outbox() -> dict[str, Any]:
    from app.core.db.session import db_session

    started = time.monotonic()
    try:
        async def read() -> Any:
            async with db_session("write") as db:
                return (await db.execute(text("SELECT waiting, oldest, retrying FROM platform.outbox_backlog()"))).first()
        waiting, oldest, retrying = await asyncio.wait_for(read(), TIMEOUT_S)
        age = int((datetime.now(UTC) - oldest).total_seconds()) if oldest else 0
        return {"name": "event_outbox", "status": "degraded" if age > OUTBOX_LATE_S else "ok",
                "latency_ms": _ms(started), "waiting": int(waiting or 0), "retrying": int(retrying or 0),
                "oldest_age_seconds": age}
    except Exception:  # noqa: BLE001
        return {"name": "event_outbox", "status": "down", "latency_ms": _ms(started)}


async def services() -> dict[str, Any]:
    from app.core.db.engines import get_engines

    engines = get_engines()
    checks = await asyncio.gather(
        _database(engines.primary, "database_primary"),
        *(_database(engine, f"database_replica_{i}") for i, engine in enumerate(engines.replicas)),
        _redis(), _rabbitmq(), _outbox())
    worst = "down" if any(c["status"] == "down" for c in checks) else (
        "degraded" if any(c["status"] == "degraded" for c in checks) else "ok")
    settings = get_settings()
    return {"status": worst, "checked_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "release": settings.app_release, "environment": settings.app_env, "services": list(checks)}

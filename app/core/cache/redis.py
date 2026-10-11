"""The shared async Redis client (cache, rate limits, nonces, session keys). Tests swap it with set_redis().

Circuit breaker: when Redis cannot be reached, every call would otherwise wait for connect timeouts, several
times per request. After one connection failure the breaker opens for REDIS_BREAKER_SECONDS: calls fail at once
with a ConnectionError (each caller already has its fallback: load from the DB, allow or refuse per the rate-limit
setting, FRM-GEN-5003), then Redis is tried again. The outage is logged once per opening, not per request.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import get_settings

log = logging.getLogger("formalie.redis")


class RedisBreaker:
    def __init__(self, cooldown_seconds: float) -> None:
        self.cooldown = cooldown_seconds
        self.open_until = 0.0

    @property
    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def trip(self, error: BaseException | None = None) -> None:
        if not self.is_open:
            log.critical("Redis unavailable, failing fast", extra={"cooldown_seconds": self.cooldown,
                                                                   "error": str(error) if error else None})
        self.open_until = time.monotonic() + self.cooldown

    def reset(self) -> None:
        self.open_until = 0.0


breaker = RedisBreaker(get_settings().redis_breaker_seconds)


class GuardedRedis(Redis):
    """Redis whose commands go through the breaker. (Pipelines are guarded by their callers: see rate_limit.)"""

    async def execute_command(self, *args: Any, **options: Any) -> Any:
        if breaker.is_open:
            raise RedisConnectionError("Redis marked unavailable (circuit open)")
        try:
            return await super().execute_command(*args, **options)
        except (RedisConnectionError, RedisTimeoutError) as exc:
            breaker.trip(exc)
            raise


def make_redis(url: str) -> GuardedRedis:
    return GuardedRedis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry=Retry(NoBackoff(), 1),
        health_check_interval=30,
    )


_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = make_redis(get_settings().redis_url.get_secret_value())
    return _client


def set_redis(client: Redis | None) -> None:
    global _client
    _client = client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

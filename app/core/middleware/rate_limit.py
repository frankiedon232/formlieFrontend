"""3. RateLimit (IP tier): a cheap rejection before any decryption (BACKEND-SPEC §1, CLAUDE.md rule 5).

SlidingWindowLimiter is the Redis sliding window (a sorted set of hit times per key) used by every tier:
this middleware for IPs, and per-route dependencies for user / tenant / route from B1 on.
Over the limit: 429 FRM-GEN-1029 with Retry-After.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.cache.redis import get_redis
from app.core.config import Settings
from app.core.context import get_context
from app.core.ids import uuid7
from app.core.middleware.asgi import ASGIApp, Receive, Scope, Send, send_error

log = logging.getLogger("formalie.ratelimit")

KEY_PREFIX = "fm:v1:rl"


@dataclass(slots=True, frozen=True)
class LimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # seconds, 0 when allowed


class RateLimiterUnavailable(Exception):
    pass


class SlidingWindowLimiter:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def hit(self, bucket: str, limit: int, window_seconds: int) -> LimitResult:
        key = f"{KEY_PREFIX}:{bucket}"
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, now_ms - window_ms)
                pipe.zcard(key)
                _, count = await pipe.execute()
            if count >= limit:
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                oldest_ms = int(oldest[0][1]) if oldest else now_ms
                retry = max(1, math.ceil((oldest_ms + window_ms - now_ms) / 1000))
                return LimitResult(False, limit, 0, retry)
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zadd(key, {f"{now_ms}:{uuid7().hex[-8:]}": now_ms})
                pipe.pexpire(key, window_ms)
                await pipe.execute()
            return LimitResult(True, limit, max(0, limit - count - 1), 0)
        except RedisError as exc:
            raise RateLimiterUnavailable(str(exc)) from exc


class IpRateLimitMiddleware:
    """Per client IP, across all API routes. Health checks from trusted monitors count like anyone else."""

    def __init__(self, app: ASGIApp, settings: Settings, limiter: SlidingWindowLimiter | None = None) -> None:
        self.app = app
        self.settings = settings
        self.limiter = limiter or SlidingWindowLimiter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return
        ctx = get_context()
        ip = (ctx.client_ip if ctx else None) or "unknown"
        try:
            result = await self.limiter.hit(f"ip:{ip}", self.settings.rate_limit_ip_per_minute, 60)
        except RateLimiterUnavailable as exc:
            if self.settings.rate_limit_fail_open:
                log.critical("rate limiter unavailable, allowing request", extra={"error": str(exc)})
                await self.app(scope, receive, send)
            else:
                log.critical("rate limiter unavailable, refusing request", extra={"error": str(exc)})
                await send_error(send, "FRM-GEN-5003")
            return
        if not result.allowed:
            if ctx is not None:
                ctx.rate_limited = True
            log.warning("FRM-GEN-1029 IP rate limit", extra={"error_code": "FRM-GEN-1029", "tier": "ip"})
            await send_error(send, "FRM-GEN-1029", headers={
                "Retry-After": str(result.retry_after),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
            })
            return
        await self.app(scope, receive, send)

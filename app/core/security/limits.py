"""Per-route rate limits (CLAUDE.md rule 5; SECURITY-PROTOCOL §8: stricter on sign-in, codes and public submit).

    @router.post("/auth/login", dependencies=[rate_limit("login", per_minute=10)])

Counted per client IP and route in Redis (the same sliding window as the IP tier). Over the limit: 429
FRM-GEN-1029 with Retry-After. `per_value(...)` limits on something in the request too (an email address), so one
address can't be hammered from many IPs. Redis down: allowed (the IP tier and the breaker already logged it).
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable

from fastapi import Depends

from app.core.context import get_context
from app.core.errors import FrmError
from app.core.middleware.rate_limit import RateLimiterUnavailable, SlidingWindowLimiter

_limiter = SlidingWindowLimiter()


async def check(bucket: str, limit: int, window_seconds: int) -> None:
    try:
        result = await _limiter.hit(bucket, limit, window_seconds)
    except RateLimiterUnavailable:
        return
    if not result.allowed:
        ctx = get_context()
        if ctx is not None:
            ctx.rate_limited = True
        raise FrmError("FRM-GEN-1029", headers={"Retry-After": str(result.retry_after),
                                                "X-RateLimit-Limit": str(result.limit), "X-RateLimit-Remaining": "0"})


def rate_limit(name: str, *, per_minute: int) -> Callable[[], Awaitable[None]]:
    async def dependency() -> None:
        ctx = get_context()
        await check(f"route:{name}:ip:{(ctx.client_ip if ctx else None) or 'unknown'}", per_minute, 60)

    return Depends(dependency)  # type: ignore[return-value]


async def per_value(name: str, value: str, *, limit: int, window_seconds: int) -> None:
    """A limit on a value from the request (hashed, never stored as it is)."""
    digest = hashlib.sha256(value.strip().lower().encode()).hexdigest()[:32]
    await check(f"route:{name}:v:{digest}", limit, window_seconds)

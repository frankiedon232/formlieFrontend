"""Per-route rate limits (CLAUDE.md rule 5; SECURITY-PROTOCOL §8: stricter on sign-in, codes and public submit).

    @router.post("/auth/login", dependencies=[rate_limit("login", per_minute=10)])

Counted per client IP and route in Redis (the same sliding window as the IP tier). Over the limit: 429
FRM-GEN-1029 with Retry-After. `per_value(...)` limits on something in the request too (an email address), so one
address can't be hammered from many IPs. Callers are counted by `ip_bucket` (IPv6 by its /64, B17 review M15).
Redis down: allowed (the IP tier and the breaker already logged it), except on sign-in, password and code routes
(FAIL_CLOSED), which answer 503 FRM-GEN-5003 rather than let guesses through uncounted (L14).
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable

from fastapi import Depends

from app.core.context import get_context
from app.core.errors import FrmError
from app.core.middleware.rate_limit import RateLimiterUnavailable, SlidingWindowLimiter
from app.core.net import ip_bucket

_limiter = SlidingWindowLimiter()

# Limits that guard secrets (passwords, one-time codes, invite and recovery steps): Redis down refuses, never allows
FAIL_CLOSED = frozenset({
    "login", "otp-verify", "otp-resend", "password-forgot", "password-reset", "signup", "signup-complete",
    "find-workspace", "find-workspace-verify", "invite-accept", "exchange-ticket", "me-password", "me-two-step",
    "public-verify", "public-unlock", "public-verify-codes", "public-unlock-tries",
})


def _name_of(bucket: str) -> str:
    """`route:{name}:…` → name."""
    parts = bucket.split(":", 2)
    return parts[1] if len(parts) > 2 and parts[0] == "route" else ""


async def check(bucket: str, limit: int, window_seconds: int) -> None:
    try:
        result = await _limiter.hit(bucket, limit, window_seconds)
    except RateLimiterUnavailable:
        if _name_of(bucket) in FAIL_CLOSED:
            raise FrmError("FRM-GEN-5003") from None
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
        await check(f"route:{name}:ip:{ip_bucket(ctx.client_ip if ctx else None)}", per_minute, 60)

    return Depends(dependency)  # type: ignore[return-value]


async def per_value(name: str, value: str, *, limit: int, window_seconds: int) -> None:
    """A limit on a value from the request (hashed, never stored as it is)."""
    digest = hashlib.sha256(value.strip().lower().encode()).hexdigest()[:32]
    await check(f"route:{name}:v:{digest}", limit, window_seconds)

"""Handshake session keys and envelope nonces in Redis (SECURITY-PROTOCOL §1, §2).

Key  `fm:v1:sec:key:{kid}`   → {"k": AES key (base64), "h": host it was made for}, TTL 30 min, sliding on use.
Key  `fm:v1:sec:nonce:{nonce}` → SET NX EX 120: the second use of a nonce is a replay.
Keys are kept in memory on the client only and in Redis here, never in PostgreSQL.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.security.envelope import NONCE_TTL_S

KEY_PREFIX = "fm:v1:sec:key:"
NONCE_PREFIX = "fm:v1:sec:nonce:"


@dataclass(frozen=True, slots=True)
class SessionKey:
    kid: str
    key: bytes
    host: str


async def save_session_key(kid: str, key: bytes, host: str) -> datetime:
    ttl = get_settings().session_key_ttl_seconds
    value = json.dumps({"k": base64.b64encode(key).decode(), "h": host})
    await get_redis().set(KEY_PREFIX + kid, value, ex=ttl)
    return datetime.now(UTC) + timedelta(seconds=ttl)


async def use_session_key(kid: str) -> SessionKey | None:
    """The key, with its expiry slid forward; None when unknown or expired."""
    redis = get_redis()
    raw = await redis.get(KEY_PREFIX + kid)
    if raw is None:
        return None
    await redis.expire(KEY_PREFIX + kid, get_settings().session_key_ttl_seconds)
    data = json.loads(raw)
    return SessionKey(kid=kid, key=base64.b64decode(data["k"]), host=data.get("h", ""))


async def claim_nonce(nonce: str) -> bool:
    """True the first time a nonce is seen, False on a replay."""
    return bool(await get_redis().set(NONCE_PREFIX + nonce, "1", nx=True, ex=NONCE_TTL_S))

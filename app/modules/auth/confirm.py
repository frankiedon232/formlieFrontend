"""Confirming the password before something sensitive (mock: core/confirm.ts; F13 M7: viewing a token, the API key or
a webhook secret again). Five wrong tries in 15 minutes lock it for that person (FRM-AUTH-1004); a wrong one answers
FRM-AUTH-1013 with the tries left (422, not 401, so the portal does not take it for an expired session). The tries
are counted in Redis, per person.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.core.cache.redis import get_redis
from app.core.errors import FrmError
from app.core.security.passwords import verify_password

WINDOW_S = 15 * 60
MAX_TRIES = 5


def _key(user: Any) -> str:
    return f"fm:v1:auth:confirm:{user.tenant_id}:{user.id}"


async def confirm_password(user: Any, password: Any) -> None:
    redis = get_redis()
    now = time.time()
    raw = await redis.get(_key(user))
    recent = [t for t in (json.loads(raw) if raw else []) if t > now - WINDOW_S]
    if len(recent) >= MAX_TRIES:
        raise FrmError("FRM-AUTH-1004")
    if not isinstance(password, str) or not password or not verify_password(user.password_hash, password):
        recent.append(now)
        await redis.set(_key(user), json.dumps(recent), ex=WINDOW_S)
        raise FrmError("FRM-AUTH-1013", [{"field": "password", "message": str(max(0, MAX_TRIES - len(recent)))}])
    await redis.delete(_key(user))

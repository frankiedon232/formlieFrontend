"""Fernet tokens (MultiFernet: the first key makes, every key reads, so keys rotate without logging anyone out).

Used for CSRF tokens (here) and, from the auth module, access and refresh tokens. A Fernet token carries its own
time and a random IV, so two tokens are never the same, even for the same content (SECURITY-PROTOCOL §5).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> MultiFernet:
    keys = get_settings().fernet_keys
    if not keys:
        raise RuntimeError("FERNET_KEYS is not set (scripts/gen_keys.py)")
    return MultiFernet([Fernet(k.get_secret_value().encode()) for k in keys])


def reset_keys() -> None:
    """Forget the loaded keys (tests, rotation)."""
    _fernet.cache_clear()


def make_token(payload: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def read_token(token: str, ttl_seconds: int) -> dict[str, Any] | None:
    """The payload, or None when the token is altered, made with an unknown key or older than `ttl_seconds`."""
    try:
        data = json.loads(_fernet().decrypt(token.encode(), ttl=ttl_seconds))
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None

"""CSRF tokens (SECURITY-PROTOCOL §6): Fernet {kid, sid, n}, 2 hours, sent as X-CSRF-Token on POST/PUT/PATCH/DELETE.

Bound to the handshake key (`kid`), like the mock's store, and, once signed in, to the session (`sid`):
a token from another secure channel or another session is refused (FRM-SEC-1006). Stateless: nothing to store.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.security.fernet_tokens import make_token, read_token

HEADER = "x-csrf-token"


def issue_csrf_token(kid: str, session_id: str | None = None) -> tuple[str, datetime]:
    ttl = get_settings().csrf_ttl_seconds
    token = make_token({"t": "csrf", "k": kid, "s": session_id, "n": os.urandom(8).hex()})
    return token, datetime.now(UTC) + timedelta(seconds=ttl)


def csrf_token_valid(token: str | None, kid: str) -> bool:
    """Checked by the envelope layer before the route runs (kid). The session match is added by the auth layer."""
    if not token:
        return False
    data = read_token(token, get_settings().csrf_ttl_seconds)
    return bool(data) and data.get("t") == "csrf" and data.get("k") == kid


def csrf_session(token: str | None) -> str | None:
    data = read_token(token or "", get_settings().csrf_ttl_seconds)
    return data.get("s") if data else None

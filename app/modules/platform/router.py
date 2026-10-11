"""System routes (mock: server/mock/routes/system.ts): health, the handshake, the CSRF token."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, StrictInt
from redis.exceptions import RedisError

from app.core.context import get_context
from app.core.errors import FrmError
from app.core.responses import ApiSuccess, ok
from app.core.security import envelope as env
from app.core.security.csrf import issue_csrf_token
from app.core.security.session_keys import save_session_key

router = APIRouter(tags=["system"])
log = logging.getLogger("formalie.handshake")


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class HealthResponse(BaseModel):
    """shared/types/api.ts HealthResponse."""

    status: Literal["ok"]
    mock: bool
    time: str


@router.get("/health", response_model=ApiSuccess[HealthResponse])
async def health() -> ApiSuccess[HealthResponse]:
    """Liveness. Plaintext (SECURITY-PROTOCOL §4), answers on any host. Dependency checks: B16 `/health/services`."""
    return ok(HealthResponse(status="ok", mock=False, time=_iso(datetime.now(UTC))))


class HandshakeRequest(BaseModel):
    """shared/types/crypto.ts HandshakeRequest (mock schema: key 80 to 120 characters, ts an integer)."""

    client_public_key: str = Field(min_length=80, max_length=120)
    client_ts: StrictInt


class HandshakeResponse(BaseModel):
    key_id: str
    server_public_key: str
    salt: str
    expires_at: str


@router.post("/crypto/handshake", response_model=ApiSuccess[HandshakeResponse])
async def handshake(body: HandshakeRequest) -> ApiSuccess[HandshakeResponse]:
    """ECDH P-256 + HKDF (SECURITY-PROTOCOL §1). The only plaintext JSON endpoint; it carries no secrets.
    The key is kept in Redis for 30 minutes (sliding) and only works on the host it was made for."""
    server_key = env.generate_key_pair()
    salt = env.b64encode(os.urandom(32))
    try:
        session_key = env.derive_session_key(server_key, body.client_public_key, salt)
    except ValueError as exc:
        raise FrmError("FRM-GEN-1001", [{"field": "client_public_key", "message": "Invalid P-256 public key."}]) from exc
    kid = str(uuid.uuid4())
    ctx = get_context()
    try:
        expires_at = await save_session_key(kid, session_key, (ctx.host if ctx else None) or "")
    except RedisError as exc:
        raise FrmError("FRM-GEN-5003") from exc
    return ok(HandshakeResponse(key_id=kid, server_public_key=env.raw_public_key(server_key), salt=salt,
                                expires_at=_iso(expires_at)))


class CsrfTokenResponse(BaseModel):
    """shared/types/api.ts CsrfTokenResponse."""

    csrf_token: str
    expires_at: str


@router.get("/auth/csrf", response_model=ApiSuccess[CsrfTokenResponse])
async def csrf() -> ApiSuccess[CsrfTokenResponse]:
    """A CSRF token bound to this secure channel (and the session once signed in), 2 hours (SECURITY-PROTOCOL §6)."""
    ctx = get_context()
    if ctx is None or not ctx.kid:
        raise FrmError("FRM-SEC-1001")
    token, expires_at = issue_csrf_token(ctx.kid, str(ctx.session_id) if ctx.session_id else None)
    return ok(CsrfTokenResponse(csrf_token=token, expires_at=_iso(expires_at)))

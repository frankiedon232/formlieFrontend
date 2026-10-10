"""System routes (mock: server/mock/routes/system.ts). The handshake and CSRF routes arrive in B1."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.responses import ApiSuccess, ok

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """shared/types/api.ts HealthResponse."""

    status: Literal["ok"]
    mock: bool
    time: str


@router.get("/health", response_model=ApiSuccess[HealthResponse])
async def health() -> ApiSuccess[HealthResponse]:
    """Liveness. Plaintext (SECURITY-PROTOCOL §4), answers on any host. Dependency checks: B16 `/health/services`."""
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return ok(HealthResponse(status="ok", mock=False, time=now))

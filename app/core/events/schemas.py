"""The event envelope on `formalie.events` (BACKEND-SPEC §5). Payloads carry references, never answers or secrets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.ids import uuid7


class EventEnvelope(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid7)
    type: str  # routing key `domain.action`, e.g. form.published
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: uuid.UUID | None = None
    organisation_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    trace_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int = 1

    def wire(self) -> dict[str, Any]:
        """The message body on `formalie.events`: personal data stripped (app/core/events/wire.py, B16)."""
        from app.core.events.wire import to_wire

        return to_wire(self)

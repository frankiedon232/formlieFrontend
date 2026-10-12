"""Transactional outbox (BACKEND-SPEC §5).

A service records an event in the same transaction as its change:

    await record_event(session, "form.published", {"form_id": str(form.id)})

The row is only visible once that transaction commits. The relay (Celery `scheduled` queue, every 2 s,
app/core/events/tasks.py) publishes unpublished rows to RabbitMQ and stamps `published_at`. Consumers stay
idempotent with `processed_events` (`claim_event`). `formalie_app` may only INSERT here; the relay runs as
`formalie_worker`. Rows are kept 7 days after publishing for replay (monthly partitions).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, PrimaryKeyConstraint, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.context import get_context
from app.core.db.base import Base
from app.core.events.schemas import EventEnvelope
from app.core.ids import uuid7


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    __table_args__ = (
        PrimaryKeyConstraint("id", "created_at"),
        Index("ix_event_outbox_unpublished", "created_at", postgresql_where=text("published_at IS NULL")),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    trace_id: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)

    def envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_id=self.id, type=self.type, occurred_at=self.created_at, tenant_id=self.tenant_id,
            organisation_id=self.organisation_id, actor_id=self.actor_id, trace_id=self.trace_id,
            payload=self.payload, version=self.version,
        )


class ProcessedEvent(Base):
    """One row per (consumer, event): a redelivered event is skipped."""

    __tablename__ = "processed_events"
    __table_args__ = (PrimaryKeyConstraint("consumer", "event_id"),
                      Index("ix_processed_events_processed_at", "processed_at"))  # the daily prune (0037)

    consumer: Mapped[str] = mapped_column(String(100))
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


async def record_event(
    session: AsyncSession,
    type_: str,
    payload: dict[str, Any] | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Adds an event to the current transaction. Workspace and actor default to the request's."""
    ctx = get_context()
    if ctx is not None and ctx.tenant is not None:
        tenant_id = tenant_id or ctx.tenant.id
        organisation_id = organisation_id or ctx.tenant.organisation_id
    actor_id = actor_id or (ctx.user_id if ctx else None)
    event_id = uuid7()
    # created_at is set here, not by the database: reading a server default back needs SELECT, which the app lacks.
    await session.execute(insert(EventOutbox).values(
        id=event_id, created_at=datetime.now(UTC), tenant_id=tenant_id, organisation_id=organisation_id, actor_id=actor_id, type=type_,
        routing_key=type_, payload=payload or {}, trace_id=ctx.trace_id if ctx else None,
    ))
    return event_id


def claim_event(session: Session, consumer: str, event_id: uuid.UUID) -> bool:
    """True the first time this consumer sees the event (inside the consumer's own transaction)."""
    result = session.execute(
        insert(ProcessedEvent).values(consumer=consumer, event_id=event_id)
        .on_conflict_do_nothing().returning(ProcessedEvent.event_id)
    )
    return result.first() is not None

"""Outbox relay: publishes committed events to RabbitMQ, oldest first, at least once."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.events.bus import EventBus
from app.core.events.outbox import EventOutbox
from app.workers.celery_app import celery_app
from app.workers.db import worker_engine

log = logging.getLogger("formalie.events")

_bus: EventBus | None = None


def relay_once(session: Session, bus: EventBus, batch: int) -> int:
    """Publishes one batch inside the caller's transaction. Locked rows are skipped, so relays can run in parallel."""
    rows = session.execute(
        select(EventOutbox)
        .where(EventOutbox.published_at.is_(None))
        .order_by(EventOutbox.created_at)
        .limit(batch)
        .with_for_update(skip_locked=True)
    ).scalars().all()
    published = 0
    for row in rows:
        try:
            bus.publish(row.envelope())
        except Exception as exc:  # noqa: BLE001 (the broker is down: keep the row, try again next run)
            session.execute(update(EventOutbox).where(EventOutbox.id == row.id, EventOutbox.created_at == row.created_at)
                            .values(attempts=EventOutbox.attempts + 1, last_error=str(exc)[:1000]))
            log.error("outbox publish failed", extra={"event_id": str(row.id), "event_type": row.type, "error": str(exc)})
            break
        session.execute(update(EventOutbox).where(EventOutbox.id == row.id, EventOutbox.created_at == row.created_at)
                        .values(published_at=func.now(), attempts=EventOutbox.attempts + 1, last_error=None))
        published += 1
    return published


@celery_app.task(name="events.relay_outbox", ignore_result=True)
def relay_outbox() -> int:
    global _bus
    _bus = _bus or EventBus()
    with Session(worker_engine()) as session, session.begin():
        count = relay_once(session, _bus, get_settings().outbox_relay_batch)
    if count:
        log.info("outbox relayed", extra={"count": count})
    return count

"""Outbox relay: publishes committed events to RabbitMQ, oldest first, at least once. Once a day, consumers' dedup rows
older than the replay window are pruned (prune_processed)."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text, update
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


PRUNE_AFTER_DAYS = 7  # the outbox replay window: an event older than this is never delivered again
PRUNE_BATCH = 10_000


def prune_processed() -> int:
    """processed_events rows processed more than PRUNE_AFTER_DAYS ago (query review Q12), in batches, as
    formalie_worker through platform.prune_processed_events (0037). A technical dedup table: no tenant data, so its
    old rows are removed rather than marked (owner to confirm)."""
    removed = 0
    while True:
        with Session(worker_engine()) as session, session.begin():
            batch = session.execute(text("SELECT platform.prune_processed_events(:days, :limit)"),
                                    {"days": PRUNE_AFTER_DAYS, "limit": PRUNE_BATCH}).scalar_one()
        removed += batch
        if batch < PRUNE_BATCH:
            return removed


@celery_app.task(name="events.prune_processed", ignore_result=True)
def prune_processed_task() -> int:
    removed = prune_processed()
    if removed:
        log.info("processed events pruned", extra={"count": removed})
    return removed

"""Celery queues, one worker service each (BACKEND-SPEC §5). Every queue dead-letters to `formalie.dlx`."""

from __future__ import annotations

from kombu import Exchange, Queue

TASKS_EXCHANGE = Exchange("formalie.tasks", type="direct", durable=True)
DEAD_LETTER_EXCHANGE = Exchange("formalie.dlx", type="direct", durable=True)

QUEUE_NAMES = (
    "notifications",  # email / SMS / OTP
    "destinations",   # writes to customers' databases
    "webhooks",
    "exports",
    "analytics",
    "files",          # scanning, image processing
    "logs",           # request / error log persistence
    "scheduled",      # Celery Beat jobs: outbox relay, partitions, cleanup, schedules
)


def _queue(name: str) -> Queue:
    return Queue(
        name,
        exchange=TASKS_EXCHANGE,
        routing_key=name,
        durable=True,
        queue_arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name, "x-dead-letter-routing-key": f"{name}.dead"},
    )


def _dead_letter(name: str) -> Queue:
    return Queue(f"{name}.dead", exchange=DEAD_LETTER_EXCHANGE, routing_key=f"{name}.dead", durable=True)


TASK_QUEUES = [_queue(name) for name in QUEUE_NAMES]
DEAD_LETTER_QUEUES = [_dead_letter(name) for name in QUEUE_NAMES]

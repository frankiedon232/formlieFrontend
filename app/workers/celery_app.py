"""The Celery app (RabbitMQ broker, Redis results).

Run a worker per queue (development, Windows: `--pool=solo` or `--pool=threads`):
    fmly\\Scripts\\celery.exe -A app.workers.celery_app worker -Q scheduled --pool=solo -l info
    fmly\\Scripts\\celery.exe -A app.workers.celery_app beat -l info
"""

from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging.setup import configure_logging
from app.workers.queues import DEAD_LETTER_QUEUES, TASK_QUEUES, TASKS_EXCHANGE

settings = get_settings()

celery_app = Celery(
    "formalie",
    broker=settings.rabbitmq_url.get_secret_value(),
    backend=settings.celery_result_backend.get_secret_value(),
    include=["app.core.events.tasks", "app.core.db.tasks", "app.modules.logs.tasks", "app.modules.emails.tasks",
             "app.modules.exports.tasks", "app.modules.responses.after"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_queues=[*TASK_QUEUES, *DEAD_LETTER_QUEUES],
    task_default_queue="scheduled",
    task_default_exchange=TASKS_EXCHANGE.name,
    task_default_routing_key="scheduled",
    task_acks_late=True,  # a crashed worker's task is redelivered
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=270,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_routes={
        "events.relay_outbox": {"queue": "scheduled"},
        "db.ensure_partitions": {"queue": "scheduled"},
        "logs.write_request_logs": {"queue": "logs"},
        "logs.update_geoip": {"queue": "scheduled"},
        "logs.ingest_error_files": {"queue": "scheduled"},
        "notifications.send_email": {"queue": "notifications"},
        "exports.build": {"queue": "exports"},
        "responses.after_submit": {"queue": "notifications"},
    },
    beat_schedule={
        "relay-outbox": {"task": "events.relay_outbox", "schedule": 2.0},
        "ensure-partitions": {"task": "db.ensure_partitions", "schedule": 6 * 3600.0},
        "update-geoip": {"task": "logs.update_geoip", "schedule": 7 * 24 * 3600.0},
        "ingest-error-files": {"task": "logs.ingest_error_files", "schedule": 30.0},
    },
)


@setup_logging.connect
def _logging(**_: object) -> None:
    configure_logging(get_settings())

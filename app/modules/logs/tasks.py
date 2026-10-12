"""Celery tasks of the logs module (queue `logs`; the GeoIP refresh runs on `scheduled`)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.logs.errors import alert_message, ingest
from app.modules.logs.geoip import update_geoip
from app.modules.logs.service import write_batch_sync
from app.workers.celery_app import celery_app
from app.workers.db import worker_engine

log = logging.getLogger("formalie.requestlog")


@celery_app.task(name="logs.write_request_logs", ignore_result=True, bind=True, max_retries=5,
                 autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300)
def write_request_logs(self, records: list[dict[str, Any]]) -> int:  # noqa: ANN001, ARG001
    with Session(worker_engine()) as session, session.begin():
        return write_batch_sync(session, records)


@celery_app.task(name="logs.update_geoip", ignore_result=True)
def refresh_geoip() -> list[str]:
    return update_geoip()


@celery_app.task(name="logs.ingest_error_files", ignore_result=True)
def ingest_error_files() -> int:
    """Warning, error and critical lines of every process → formaly.error_logs; CRITICAL ones emailed."""
    with Session(worker_engine()) as session, session.begin():
        rows = ingest(session)
    critical = [r for r in rows if r["level"] == "CRITICAL"]
    for to in get_settings().alert_emails if critical else []:
        celery_app.send_task("notifications.send_email", args=[alert_message(critical, to)], queue="notifications")
    return len(rows)

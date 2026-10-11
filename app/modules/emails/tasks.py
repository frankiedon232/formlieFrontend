"""Celery tasks of the emails module (queue `notifications`)."""

from __future__ import annotations

from app.modules.emails.service import deliver
from app.workers.celery_app import celery_app


@celery_app.task(name="notifications.send_email", ignore_result=True, autoretry_for=(Exception,),
                 retry_backoff=True, retry_backoff_max=600, max_retries=6)
def send_email(message: dict[str, str]) -> None:
    deliver(message)

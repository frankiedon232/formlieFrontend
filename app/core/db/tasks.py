"""Partition upkeep: keeps the next 3 months of every monthly-partitioned table ready (DATABASE-DESIGN, Partitioning).

`platform.ensure_monthly_partitions` is SECURITY DEFINER (owned by formalie_owner) and gives each new partition
RLS enabled and forced, so a partition can never be read around its parent's policy.
Retention (B17 review M8): `request_logs` partitions wholly older than REQUEST_LOG_RETENTION_DAYS are detached and
dropped once a day by `platform.drop_expired_partitions` (SECURITY DEFINER, request_logs only, never under 7 days).
That is how a privacy erasure reaches the request log's copies. Audit, responses, error and API logs never expire here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.workers.celery_app import celery_app
from app.workers.db import worker_engine

log = logging.getLogger("formalie.db")

MONTHLY_TABLES = tuple(f"{get_settings().db_schema}.{t}" for t in ("event_outbox", "request_logs", "audit_logs", "responses",
                                                                   "error_logs", "api_request_logs",
                                                                   "webhook_deliveries"))
MONTHS_AHEAD = 3


@celery_app.task(name="db.ensure_partitions", ignore_result=True)
def ensure_partitions() -> None:
    with Session(worker_engine()) as session, session.begin():
        for table in MONTHLY_TABLES:
            created = session.execute(
                text("SELECT platform.ensure_monthly_partitions(CAST(:t AS regclass), :n)"),
                {"t": table, "n": MONTHS_AHEAD},
            ).scalar_one()
            if created:
                log.info("partitions created", extra={"table": table, "count": created})


# Tables whose old partitions are dropped, with the setting that says how many days they keep
RETENTION = {"request_logs": "request_log_retention_days"}


def retention_cutoff(days: int, now: datetime | None = None) -> datetime | None:
    """Partitions ending at or before this moment go; None when retention is off (0 or less)."""
    if days <= 0:
        return None
    return (now or datetime.now(UTC)) - timedelta(days=max(days, 7))


@celery_app.task(name="db.drop_expired_partitions", ignore_result=True)
def drop_expired_partitions() -> int:
    settings = get_settings()
    dropped = 0
    for table, setting in RETENTION.items():
        cutoff = retention_cutoff(int(getattr(settings, setting)))
        if cutoff is None:
            continue
        name = f"{settings.db_schema}.{table}"
        try:
            with Session(worker_engine()) as session, session.begin():
                count = session.execute(
                    text("SELECT platform.drop_expired_partitions(CAST(:t AS regclass), :before)"),
                    {"t": name, "before": cutoff},
                ).scalar_one()
        except DBAPIError:
            log.exception("dropping expired partitions failed", extra={"table": name})
            continue
        if count:
            log.info("expired partitions dropped", extra={"table": name, "count": count, "before": cutoff.isoformat()})
        dropped += count
    return dropped

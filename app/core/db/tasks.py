"""Partition upkeep: keeps the next 3 months of every monthly-partitioned table ready (DATABASE-DESIGN, Partitioning).

`platform.ensure_monthly_partitions` is SECURITY DEFINER (owned by formalie_owner) and gives each new partition
RLS enabled and forced, so a partition can never be read around its parent's policy.
Detaching expired partitions to cold storage comes with the log tables (B2).
"""

from __future__ import annotations

import logging

from sqlalchemy import text
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

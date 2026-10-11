"""Response storage in a customer's database (DATABASE-DESIGN → Data sources, response storage). Tenant tables, RLS
forced, soft delete only.

- `response_destinations`: one form's responses go to a table on a connection (a table Formalie created, or an
  existing one of theirs), with the column mapping and how values are written. One per form.
- `destination_deliveries`: one per response sent (or to send): pending, sent, failed (retried with growing waits)
  or held (the destination is paused). A response without one was never sent (before the destination covered it).
- `destination_backfills`: sending earlier responses for a date range, with progress.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)


class ResponseDestination(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "response_destinations"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        tenant_fk("datasource_id", "datasources"),
        Index("uq_response_destinations_form", "tenant_id", "form_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_response_destinations_source", "tenant_id", "datasource_id"),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    datasource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    table_schema: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    table_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    columns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    covers_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DestinationDelivery(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "destination_deliveries"
    __table_args__ = tenant_table_args(
        tenant_fk("destination_id", "response_destinations"),
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'held')", name="status"),
        Index("uq_destination_deliveries", "tenant_id", "destination_id", "response_id", unique=True),
        Index("ix_destination_deliveries_due", "next_attempt_at", postgresql_where=text("status IN ('pending', 'failed')")),
        Index("ix_destination_deliveries_list", "tenant_id", "destination_id", "response_submitted_at"),
    )

    destination_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    response_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    response_submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(20))
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # the last attempt
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # when pending or failed


class DestinationBackfill(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "destination_backfills"
    __table_args__ = tenant_table_args(
        tenant_fk("destination_id", "response_destinations"),
        CheckConstraint("status IN ('running', 'done')", name="status"),
        Index("ix_destination_backfills", "tenant_id", "destination_id", "started_at"),
    )

    destination_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    range_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    range_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    done: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

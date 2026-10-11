"""The Query editor (DATABASE-DESIGN → Data sources, response storage, explorer and query). Tenant tables, RLS forced,
soft delete only.

- `query_history`: each person's statements per connection (the editor shows the last 50); the statement, never its
  result rows. Clearing it marks the entries deleted.
- `saved_queries`: saved statements (or scripts), personal or shared with the workspace; changed only by their owner.
- `saved_query_runs_daily`: runs of a saved query per day, for its chart.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class QueryHistory(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "query_history"
    __table_args__ = tenant_table_args(
        tenant_fk("datasource_id", "datasources"),
        Index("ix_query_history_person", "tenant_id", "user_id", "datasource_id", "ran_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    datasource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    rows: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(20))


class SavedQuery(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "saved_queries"
    __table_args__ = tenant_table_args(
        tenant_fk("datasource_id", "datasources"),
        Index("ix_saved_queries_owner", "tenant_id", "owner_id"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    datasource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    shared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SavedQueryRunsDaily(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "saved_query_runs_daily"
    __table_args__ = tenant_table_args(
        tenant_fk("saved_query_id", "saved_queries"),
        Index("uq_saved_query_runs_daily", "tenant_id", "saved_query_id", "day", unique=True),
    )

    saved_query_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    runs: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

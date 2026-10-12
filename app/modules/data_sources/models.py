"""Data sources: customers' own databases (DATABASE-DESIGN → Data sources, response storage, explorer and query).
Tenant tables, RLS forced, soft delete only.

- `datasources`: the connection. Secrets (passwords, keys, certificates) are kept encrypted (`secrets_enc`, Fernet)
  and never returned; only which ones are set.
- `datasource_tests`: a connection test, step by step as the worker runs it. A test of a configuration not saved
  yet carries its secrets encrypted until it finishes (then they are cleared).
- `datasource_checks`: health checks (every few minutes): latency, status, uptime.
- `datasource_ops_daily`: Formalie's operations per day (reads, writes, checks), for the charts.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)


class DataSource(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "datasources"
    __table_args__ = tenant_table_args(
        CheckConstraint("engine IN ('mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb')", name="engine"),
        Index("uq_datasources_name", "tenant_id", text("lower(name)"), unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    engine: Mapped[str] = mapped_column(String(12), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    secrets_enc: Mapped[str | None] = mapped_column(Text)
    secrets_set: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    secrets_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_test_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    ssh_host_key: Mapped[str | None] = mapped_column(String(400))  # pinned: "host:port SHA256:..." (first good test)


class DataSourceTest(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "datasource_tests"
    __table_args__ = tenant_table_args(
        CheckConstraint("status IN ('running', 'passed', 'warning', 'failed')", name="status"),
        Index("ix_datasource_tests_source", "tenant_id", "datasource_id", "started_at"),
    )

    datasource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="running")
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    permissions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    findings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    schemas: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    server_version: Mapped[str | None] = mapped_column(String(100))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tables_count: Mapped[int | None] = mapped_column(Integer)
    config_enc: Mapped[str | None] = mapped_column(Text)  # engine, settings, access and secrets while it runs
    ssh_host_key: Mapped[str | None] = mapped_column(String(400))  # the SSH server's key this test saw
    audited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataSourceCheck(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "datasource_checks"
    __table_args__ = tenant_table_args(
        tenant_fk("datasource_id", "datasources"),
        CheckConstraint("status IN ('passed', 'warning', 'failed')", name="status"),
        Index("ix_datasource_checks_source", "tenant_id", "datasource_id", "at"),
    )

    datasource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(20))


class DataSourceOpsDaily(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "datasource_ops_daily"
    __table_args__ = tenant_table_args(
        tenant_fk("datasource_id", "datasources"),
        Index("uq_datasource_ops_daily", "tenant_id", "datasource_id", "day", unique=True),
    )

    datasource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

"""A workspace's own web address (Settings → Address and domain; the mock's data/addressStore.ts). The subdomain itself
and its old ones live in the tenant directory (`platform.tenants`, `platform.tenant_subdomain_history`); the own domain
is set up here (records, verification token, last check) and, once verified, claimed in
`platform.custom_domains_directory` so the host finds the workspace before it has a tenant context."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class CustomDomain(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "custom_domains"
    __table_args__ = tenant_table_args(
        Index("uq_custom_domains_tenant", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint("status IN ('pending', 'verified', 'failed')", name="status"),
        CheckConstraint("domain = lower(domain)", name="domain_lower"),
    )

    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default="pending")
    records: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    problem: Mapped[str | None] = mapped_column(String(12))

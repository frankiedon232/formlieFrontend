"""Tenant directory (schema `platform`, no RLS, not readable by formalie_app) and organisations (tenant table).

The app never lists tenants: it resolves one host at a time through `platform.resolve_tenant()`
(SECURITY DEFINER, public fields only). DATABASE-DESIGN → Tenant directory.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, Text, Uuid, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args

TENANT_STATUSES = ("active", "suspended", "read_only", "closing")


class Tenant(UuidPkMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(f"status IN {TENANT_STATUSES}", name="status"),
        CheckConstraint("subdomain = lower(subdomain)", name="subdomain_lower"),
        Index("uq_tenants_subdomain_active", "subdomain", unique=True, postgresql_where=text("deleted_at IS NULL")),
        {"schema": "platform"},
    )

    subdomain: Mapped[str] = mapped_column(String(63), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    primary_organisation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    data_region: Mapped[str] = mapped_column(String(20), nullable=False, server_default="default")
    plan_id: Mapped[str] = mapped_column(String(40), nullable=False, server_default="starter")
    setup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set by the platform admin (B16): the trial's end, and limits that replace the plan's (enforced with B15)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_limits: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class TenantSubdomainHistory(UuidPkMixin, Base):
    """An old subdomain keeps resolving to its workspace until `until` (90 days, 03-DECISIONS F14 M7)."""

    __tablename__ = "tenant_subdomain_history"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT"),
        Index("ix_tenant_subdomain_history_subdomain", "subdomain"),
        {"schema": "platform"},
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    subdomain: Mapped[str] = mapped_column(String(63), nullable=False)
    until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class Organisation(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """An organisation unit inside a tenant. One per workspace today (03-DECISIONS 2026-10-07).

    Its `organisation_id` is its own id, so the same RLS policy (tenant AND organisation) covers it.
    """

    __tablename__ = "organisations"
    __table_args__ = tenant_table_args(
        CheckConstraint("organisation_id = id", name="self_organisation"),
        ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(300))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

"""The audit trail (`formaly.audit_logs`, BACKEND-SPEC §8.2 and §12): who did what, when, where, with what result.

Monthly partitions, insert-only: nobody may change or delete a row (no UPDATE / DELETE grants). RLS forced: a
workspace reads only its own entries. Actions come from app/modules/audit/events.py (the frontend's catalogue).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, PrimaryKeyConstraint, String, Uuid
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.ids import uuid7


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        PrimaryKeyConstraint("id", "occurred_at"),
        Index("ix_audit_logs_tenant_time", "tenant_id", "occurred_at"),
        Index("ix_audit_logs_tenant_area_time", "tenant_id", "area", "occurred_at"),
        Index("ix_audit_logs_tenant_actor_time", "tenant_id", "actor_id", "occurred_at"),
        Index("ix_audit_logs_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        {"postgresql_partition_by": "RANGE (occurred_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    area: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)  # success, failure, blocked
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # info, notice, warning, critical
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, api_key, system, platform_support
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_name: Mapped[str | None] = mapped_column(String(200))
    actor_email: Mapped[str | None] = mapped_column(String(254))
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    resource_name: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(INET)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(2))
    device: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(20))
    request_id: Mapped[str | None] = mapped_column(String(36))
    staff_id: Mapped[str | None] = mapped_column(String(64))
    staff_name: Mapped[str | None] = mapped_column(String(200))
    approval_id: Mapped[str | None] = mapped_column(String(64))

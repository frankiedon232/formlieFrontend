"""Organisation data (DATABASE-DESIGN → People, roles and access; mock data/orgStore.ts): each workspace's own
departments and job titles, and the people in them. Tenant tables: RLS forced, soft delete only (a merged or deleted
entry, and a person taken out, keep their rows with deleted_at)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class OrgUnit(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "org_units"
    __table_args__ = tenant_table_args(
        CheckConstraint("kind IN ('departments', 'job_titles')", name="kind"),
        Index("uq_org_units_name", "tenant_id", "kind", text("lower(name)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(200))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrgUnitMember(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "org_unit_members"
    __table_args__ = tenant_table_args(
        tenant_fk("org_unit_id", "org_units"),
        tenant_fk("user_id", "users"),
        Index("uq_org_unit_members", "tenant_id", "org_unit_id", "user_id", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("ix_org_unit_members_user", "tenant_id", "user_id"),
    )

    org_unit_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

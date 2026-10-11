"""The design library (DATABASE-DESIGN → Design; mock data/libraryStore.ts): the workspace's own themes and page
designs (Formalie's are built from presets, never stored), and saved fields. Tenant tables, RLS forced, soft delete."""

from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class Theme(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "themes"
    __table_args__ = tenant_table_args(
        CheckConstraint("source IN ('saved', 'created')", name="source"),
        Index("uq_themes_name", "tenant_id", text("lower(name)"), unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default="saved")
    tokens: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class PageDesign(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "page_designs"
    __table_args__ = tenant_table_args(
        CheckConstraint("source IN ('saved', 'created')", name="source"),
        Index("uq_page_designs_name", "tenant_id", text("lower(name)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default="saved")
    tokens: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class SavedField(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """A field kept for reuse (no id: inserting one gives it a new one)."""

    __tablename__ = "saved_fields"
    __table_args__ = tenant_table_args()

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    field: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

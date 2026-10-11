"""Option lists (DATABASE-DESIGN → Option lists; docs/OPTION-LISTS.md): each workspace's reusable choice lists and
their options, one row per option so a list of up to 200,000 can be searched and read level by level.

Options are matched by value (unique within a list, without case): saving a list updates its options in place,
and an option left out keeps its row with deleted_at. Formalie's sample lists carry `system_key` and are use-only.
Tenant tables, RLS forced, soft delete.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, Index, Integer, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)


class OptionList(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "option_lists"
    __table_args__ = tenant_table_args(
        Index("uq_option_lists_name", "tenant_id", text("lower(name)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    levels: Mapped[list[Any] | None] = mapped_column(JSONB)  # 2 to 4 named levels; null = a plain list
    columns: Mapped[list[Any] | None] = mapped_column(JSONB)  # up to 10 detail columns
    large: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    system_key: Mapped[str | None] = mapped_column(String(40))  # Formalie's sample lists (use-only)
    active_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class OptionItem(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "option_items"
    __table_args__ = tenant_table_args(
        tenant_fk("list_id", "option_lists"),
        Index("uq_option_items_value", "tenant_id", "list_id", text("lower(value)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("ix_option_items_list", "tenant_id", "list_id", "level", "sort_order"),
    )

    list_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    parent_value: Mapped[str | None] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    translations: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    attrs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

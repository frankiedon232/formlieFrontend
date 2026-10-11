"""The workspace's own templates (DATABASE-DESIGN → Templates; mock data/libraryStore.ts): a snapshot of a form,
its design included. Formalie's catalogue is data (data/system_templates.json). The app knows a workspace template
as `ws_<key_id>` (12 hex characters). Tenant table, RLS forced, soft delete."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class WorkspaceTemplate(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "workspace_templates"
    __table_args__ = tenant_table_args(
        Index("uq_workspace_templates_key", "tenant_id", "key_id", unique=True),
        Index("uq_workspace_templates_name", "tenant_id", text("lower(name)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    key_id: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False, server_default="")
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    icon: Mapped[str] = mapped_column(String(80), nullable=False)
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

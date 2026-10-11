"""Workspace settings: one row per section (company, branding, localisation, signin, security …), value in JSON.

Sections are validated with the port of shared/utils/settings/schemas.ts (B3/B11). Defaults come from
app/modules/settings/defaults.py, written when a workspace is made and filled in for any section still missing.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, RowVersionMixin, TenantMixin, UuidPkMixin, tenant_table_args


class WorkspaceSetting(UuidPkMixin, TenantMixin, AuditMixin, RowVersionMixin, Base):
    __tablename__ = "workspace_settings"
    __table_args__ = tenant_table_args(Index("uq_workspace_settings_section", "tenant_id", "section", unique=True))

    section: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

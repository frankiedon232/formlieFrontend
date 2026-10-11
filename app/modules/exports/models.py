"""Export jobs (mock: routes/audit.ts jobs): a file made in the background, then one download link.

The link's token is kept as a SHA-256 hash (to find the job) and encrypted (to show the link while polling). It
works once, for EXPORT_DOWNLOAD_MINUTES after the file is ready, and only on the workspace that made it.
Tenant table: RLS forced, soft delete only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args

EXPORT_STATUSES = ("queued", "running", "done", "failed")


class ExportJob(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "export_jobs"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"status IN {EXPORT_STATUSES}", name="status"),
        CheckConstraint("format IN ('xlsx', 'csv')", name="format"),
        Index("ix_export_jobs_creator", "tenant_id", "created_by", "created_at"),
        Index("uq_export_jobs_token", "token_hash", unique=True, postgresql_where=text("token_hash IS NOT NULL")),
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # audit · (responses, data sources: later)
    format: Mapped[str] = mapped_column(String(4), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    file_key: Mapped[str | None] = mapped_column(String(300))
    file_size: Mapped[int | None] = mapped_column(Integer)
    token_hash: Mapped[str | None] = mapped_column(String(64))  # for finding the job from its link
    token_enc: Mapped[str | None] = mapped_column(String(300))  # to show the link again; cleared once used
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(20))

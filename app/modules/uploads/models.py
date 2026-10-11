"""Uploads (mock: routes/uploads.ts): a short-lived ticket, the bytes sent straight to storage with it, then
"complete". The token is kept only as a hash. Respondents' files (public forms) join this table in B7.
Tenant table: RLS forced, soft delete only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args

PURPOSES = ("logo", "share_image", "form_image", "avatar")  # avatar: My profile photo


class Upload(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "uploads"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"purpose IN {PURPOSES}", name="purpose"),
        CheckConstraint("scan_status IN ('pending', 'clean', 'refused')", name="scan_status"),
        Index("uq_uploads_token", "token_hash", unique=True, postgresql_where=text("token_hash IS NOT NULL")),
    )

    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    max_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_key: Mapped[str | None] = mapped_column(String(300))
    stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scan_status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")

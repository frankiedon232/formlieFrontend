"""Uploads (mock: routes/uploads.ts): a short-lived ticket, the bytes sent straight to storage with it, then
"complete". The token is kept only as a hash. Respondents' files (public forms, purpose `response_file`) carry their
form, question and, once sent, their response; they are personal data and never served as public files.
Tenant table: RLS forced, soft delete only."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args

PURPOSES = ("logo", "share_image", "form_image", "avatar", "response_file")  # avatar: My profile photo


class Upload(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "uploads"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"purpose IN {PURPOSES}", name="purpose"),
        CheckConstraint("scan_status IN ('pending', 'clean', 'refused')", name="scan_status"),
        Index("uq_uploads_token", "token_hash", unique=True, postgresql_where=text("token_hash IS NOT NULL")),
        Index("ix_uploads_response", "tenant_id", "response_id", postgresql_where=text("response_id IS NOT NULL")),
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
    # Respondents' files: the form and question, what the question takes, the response once sent
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    field_key: Mapped[str | None] = mapped_column(String(64))
    file_kind: Mapped[str | None] = mapped_column(String(6))  # image or file
    listed: Mapped[list[Any] | None] = mapped_column(JSONB)  # extensions the question lists (programs allowed)
    response_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    response_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

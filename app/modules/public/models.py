"""Public filling (DATABASE-DESIGN → Public filling: sessions, resume, uploads, spam checks; mock resumeStore.ts and
the verification store in routes/publicForms.ts). Tenant tables, RLS forced, soft delete only. Tokens and codes are
kept as hashes; `platform_reader` never reads a draft's answers. Proof-of-work challenges, submission rate limits and
unlock attempts live in Redis."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class ResumeDraft(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Save and resume: the answers so far behind a resume token (30 days)."""

    __tablename__ = "resume_drafts"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        Index("uq_resume_drafts_token", "token_hash", unique=True),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    email: Mapped[str | None] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RespondentVerification(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """A 6-digit code sent to a respondent's email (10 minutes, 5 tries), then a token for one submission (30 min)."""

    __tablename__ = "respondent_verifications"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        Index("ix_respondent_verifications_email", "tenant_id", "form_id", "email_hash"),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

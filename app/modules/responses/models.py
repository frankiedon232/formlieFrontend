"""Responses (DATABASE-DESIGN → Responses, files and review; mock data/responseStore.ts). Tenant tables, RLS forced,
soft delete only.

- `responses` is partitioned by month on `submitted_at`; its key is (tenant_id, id, submitted_at), so tables that
  point at a response carry `response_submitted_at` too. `platform_reader` never reads `data` (the answers).
- `response_submissions` keeps one row per fill-in session (`Formalie-Key`) of a form: a partitioned table can't
  hold that unique key itself, so this small table does, and a repeat of the same session finds its response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, PrimaryKeyConstraint, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)
from app.core.ids import uuid7

RESPONSE_STATUSES = ("new", "reviewed", "approved", "rejected")
CHANNELS = ("link", "embed", "api")


class Response(TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "responses"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id", "submitted_at"),
        tenant_fk("form_id", "forms"),
        CheckConstraint(f"status IN {RESPONSE_STATUSES}", name="status"),
        CheckConstraint(f"channel IN {CHANNELS}", name="channel"),
        Index("ix_responses_form", "tenant_id", "form_id", "submitted_at"),
        Index("ix_responses_identity", "tenant_id", "form_id", "identity_email"),
        Index("ix_responses_device", "tenant_id", "form_id", "device_hash"),
        Index("ix_responses_fingerprint", "tenant_id", "form_id", "fingerprint"),
        {"postgresql_partition_by": "RANGE (submitted_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    form_version_no: Mapped[int | None] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    channel: Mapped[str] = mapped_column(String(6), nullable=False)
    submission_id: Mapped[str | None] = mapped_column(String(64))
    api_token_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    device_hash: Mapped[str | None] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_email: Mapped[str | None] = mapped_column(String(254))  # the respondent's own email, normalised
    respondent_kind: Mapped[str | None] = mapped_column(String(10))  # invite · member
    respondent_ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    respondent_email: Mapped[str | None] = mapped_column(String(254))
    respondent_name: Mapped[str | None] = mapped_column(String(200))
    possible_duplicate: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    duplicate_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="new")
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    edited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(2))
    device: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ResponseSubmission(UuidPkMixin, TenantMixin, AuditMixin, Base):
    """One per fill-in session of a form (Formalie-Key): the response it made."""

    __tablename__ = "response_submissions"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        Index("uq_response_submissions", "tenant_id", "form_id", "submission_id", unique=True),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    submission_id: Mapped[str] = mapped_column(String(64), nullable=False)
    response_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    response_submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

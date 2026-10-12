"""AI assistant tables (DATABASE-DESIGN → AI assistant; mock data/aiStore.ts). Tenant tables, RLS forced.

- `ai_settings`: one row per workspace (on or off, what it may read, masking, how long requests are kept, the agreed
  allowance for plans without one); the defaults until someone changes them.
- `ai_requests`: every request with who asked, the prompt (masked when the workspace asks), a plain summary of the
  result, the draft itself while it waits for a person (`output`), the engine that answered and its tokens. Past the
  workspace's keep setting (or removed by a person) a request is soft deleted and its prompt, result and draft are
  emptied; the row stays for the month's usage.
- `ai_usage`: per workspace and month: requests, credits, model calls and tokens (the allowance is read here, so a
  removed request never gives credits back).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args
from app.modules.ai.kinds import AI_KINDS, AI_STATUSES

ENGINES = ("model", "standin", "fallback")


class AiSettings(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "ai_settings"
    __table_args__ = tenant_table_args(
        CheckConstraint("keep_days IN (30, 90, 180, 365)", name="keep_days"),
        Index("uq_ai_settings_tenant", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mask_personal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    keep_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="90")
    monthly_credits: Mapped[int] = mapped_column(Integer, nullable=False, server_default="500")
    updated_by_name: Mapped[str | None] = mapped_column(String(200))


class AiRequest(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "ai_requests"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"kind IN {AI_KINDS}", name="kind"),
        CheckConstraint(f"status IN {AI_STATUSES}", name="status"),
        CheckConstraint(f"engine IN {ENGINES}", name="engine"),
        Index("ix_ai_requests_tenant_created", "tenant_id", "created_at"),
        Index("ix_ai_requests_tenant_by", "tenant_id", "by_id"),
    )

    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_key: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    by_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    by_name: Mapped[str] = mapped_column(String(200), nullable=False)
    target: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    prompt: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    result: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    read: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    masked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    notes: Mapped[list[Any] | None] = mapped_column(JSONB)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    engine: Mapped[str] = mapped_column(String(10), nullable=False, server_default="standin")
    model: Mapped[str | None] = mapped_column(String(80))
    fallback_reason: Mapped[str | None] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class AiUsage(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "ai_usage"
    __table_args__ = tenant_table_args(
        Index("uq_ai_usage_month", "tenant_id", "month", unique=True),
    )

    month: Mapped[date] = mapped_column(Date, nullable=False)  # the first day of the month (UTC)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    credits: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    model_calls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    cache_read_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    cache_write_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")

"""Webhooks (DATABASE-DESIGN → Webhooks; mock: data/integrationStore.ts). Tenant tables, RLS forced.

- `webhooks`: an address that gets the workspace's response events, the events and forms it listens to (an empty
  list = every form), on or off (paused by someone, or by itself after repeated failures), and the webhook token it
  sends (`api_tokens`, kind `webhook`; owner 2026-10-06: no separate signing secrets). Soft delete only.
- `webhook_deliveries`: one event sent to one webhook (or a `ping` test), partitioned by month on `at`; the key is
  (tenant_id, id, at). The body as sent is kept encrypted (Fernet) for retries and Send again; the copy shown in the
  log has personal answers masked. Every try is in `history`; `next_retry_at` is when the sweep tries again; `claimed_until` keeps two workers
  from trying the same delivery at once.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Index, Integer, PrimaryKeyConstraint, SmallInteger, String, Text, Uuid, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args
from app.core.ids import uuid7


class Webhook(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "webhooks"
    __table_args__ = tenant_table_args(
        tenant_fk("token_id", "api_tokens"),
        CheckConstraint("paused_reason IN ('manual', 'failures')", name="paused_reason"),
        Index("ix_webhooks_tenant", "tenant_id", "created_at", postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    form_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    paused_reason: Mapped[str | None] = mapped_column(String(8))
    token_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class WebhookDelivery(TenantMixin, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "id", "at"),
        tenant_fk("webhook_id", "webhooks"),
        CheckConstraint("status IN ('delivered', 'retrying', 'failed')", name="status"),
        Index("ix_webhook_deliveries_list", "tenant_id", "webhook_id", "at"),
        Index("ix_webhook_deliveries_at", "tenant_id", "at"),
        Index("ix_webhook_deliveries_id", "tenant_id", "id"),
        Index("ix_webhook_deliveries_due", "next_retry_at", postgresql_where=text("status = 'retrying'")),
        {"postgresql_partition_by": "RANGE (at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    webhook_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event: Mapped[str] = mapped_column(String(30), nullable=False)
    test: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    response_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status_code: Mapped[int | None] = mapped_column(SmallInteger)  # of the last try
    duration_ms: Mapped[int | None] = mapped_column(Integer)  # of the last try
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # a worker is trying it until then
    body_enc: Mapped[str | None] = mapped_column(Text)  # what is sent (Fernet), for retries and Send again
    logged_body: Mapped[str] = mapped_column(Text, nullable=False)  # the copy for the log (personal answers masked)
    request_headers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

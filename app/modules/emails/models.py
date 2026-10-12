"""Emails' tables: who stopped which optional emails with an Unsubscribe link (owner, 2026-10-12; one row per stop,
Undo soft-deletes it, so the history stays: no hard deletes, CLAUDE.md rule 6), the sent log and where a workspace's
emails come from (B11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class EmailUnsubscribe(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "email_unsubscribes"
    __table_args__ = tenant_table_args(
        Index("uq_email_unsubscribes_active", "tenant_id", "email", "kind", "ref", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    email: Mapped[str] = mapped_column(String(254), nullable=False)
    # response_notification · notification · daily_digest · form_invitation (shared/types/emails.ts UNSUBSCRIBE_KINDS)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # The form (new responses) or the event key (notifications); '' when the kind has none
    ref: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    stopped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class SentEmail(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """The sent log (Settings → Email templates; the mock's data/outboxStore.ts): every email sent for the workspace,
    newest first. Only the last 200 are kept: older ones are soft deleted with their bodies cleared. One-time codes
    and personal links are never stored (the log's copy shows dots in their place)."""

    __tablename__ = "sent_emails"
    __table_args__ = tenant_table_args(
        Index("ix_sent_emails_list", "tenant_id", "sent_at", postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint("to_email = lower(to_email)", name="to_email_lower"),
    )

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    to_email: Mapped[str] = mapped_column(String(254), nullable=False)
    subject: Mapped[str] = mapped_column(String(400), nullable=False)
    template: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    text_body: Mapped[str] = mapped_column("text", Text, nullable=False, server_default="")


class EmailSending(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Where the workspace's emails come from (Settings → Emails → Sending address; the mock's data/sendingStore.ts):
    one row per workspace. `domain` is the SendingDomain shape (with the DKIM key part of the record values), `smtp`
    the SmtpServer shape without the password, which is kept Fernet-encrypted in `smtp_password_enc` (write-only)."""

    __tablename__ = "email_sending"
    __table_args__ = tenant_table_args(
        Index("uq_email_sending_tenant", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint("mode IN ('formalie', 'domain', 'smtp')", name="mode"),
    )

    mode: Mapped[str] = mapped_column(String(10), nullable=False, server_default="formalie")
    domain: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    smtp: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    smtp_password_enc: Mapped[str | None] = mapped_column(Text)

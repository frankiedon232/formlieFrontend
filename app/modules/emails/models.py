"""Who stopped which optional emails with an Unsubscribe link (owner, 2026-10-12). One row per stop; Undo soft-deletes
it, so the history stays (no hard deletes, CLAUDE.md rule 6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, text
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

"""Invitations to invite-only forms (DATABASE-DESIGN → Sharing, links, invites, embed; mock data/formAccess.ts):
one person, one response. The personal token is only in the invitation link; the row keeps its SHA-256. Status is
read from the dates: revoked, responded, opened, invited. Tenant table, RLS forced, soft delete (an invitation
taken off the list keeps its row)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class FormInvitation(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "form_invitations"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        Index("uq_form_invitations_token", "token_hash", unique=True),
        Index("uq_form_invitations_email", "tenant_id", "form_id", "email", unique=True,
              postgresql_where=text("deleted_at IS NULL AND revoked_at IS NULL")),
        Index("ix_form_invitations_form", "tenant_id", "form_id", "sent_at"),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

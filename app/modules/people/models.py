"""Ways into a workspace (DATABASE-DESIGN → People, roles and access; mock routes/invites.ts, data/signupLinkStore.ts).

- `user_invites`: a personal link for one person (an activation for a profile an admin made, or a personal sign-up
  link). Only the token's SHA-256 is kept; a new link replaces the old one (`revoked_at`).
- `signup_links`: the workspace's one shared sign-up link. Its token is shown again on the People page, so it is
  kept encrypted (MultiFernet) and as a hash to find it; a new link stops the old one.
Tenant tables: RLS forced, soft delete only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class UserInvite(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "user_invites"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        CheckConstraint("kind IN ('invite', 'activation')", name="kind"),
        Index("uq_user_invites_token", "token_hash", unique=True),
        Index("ix_user_invites_user", "tenant_id", "user_id", "sent_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    invited_by_name: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SignupLink(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "signup_links"
    __table_args__ = tenant_table_args(
        Index("uq_signup_links_tenant", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("uq_signup_links_token", "token_hash", unique=True),
    )

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    domains: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

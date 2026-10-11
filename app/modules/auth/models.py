"""Sign-in sessions and refresh tokens (SECURITY-PROTOCOL §5). Tenant tables, RLS forced, soft delete only.

A session lives until it is revoked, idle too long, or reaches the workspace's maximum length (Settings → Security).
Refresh tokens are single use, kept as SHA-256 hashes, chained in a family: using one twice revokes the session.
Access tokens are Fernet tokens and are not stored; the session behind them is checked on every request.
Sign-in codes and one-time tickets are short-lived and live in Redis (app/modules/auth/challenges.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class UserSession(UuidPkMixin, TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        Index("ix_user_sessions_user", "tenant_id", "user_id", "last_active_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)
    device: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(2))
    method: Mapped[str | None] = mapped_column(String(20))  # password, signup_handoff, google, sso …
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(40))


class RefreshToken(UuidPkMixin, TenantMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = tenant_table_args(
        tenant_fk("session_id", "user_sessions"),
        Index("uq_refresh_tokens_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_session", "tenant_id", "session_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)

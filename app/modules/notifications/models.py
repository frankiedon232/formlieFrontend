"""Notifications (DATABASE-DESIGN → Emails, sending and notifications; mock data/notificationStore.ts): each person's
feed (the last 100 shown), the daily summary lines waiting to go out, and what was already announced once (a form
closing at a time, a finished export). Tenant tables, RLS forced, soft delete only (clearing hides read ones)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class Notification(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = tenant_table_args(Index("ix_notifications_user", "tenant_id", "user_id", "created_at"))

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    link: Mapped[str | None] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationDigestLine(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """A line waiting for someone's daily summary; sent lines get deleted_at."""

    __tablename__ = "notification_digest_lines"
    __table_args__ = tenant_table_args(Index("ix_notification_digest_lines_open", "tenant_id", "email",
                                             postgresql_where=text("deleted_at IS NULL")))

    email: Mapped[str] = mapped_column(String(254), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    line: Mapped[str] = mapped_column(String(500), nullable=False)


class NotificationOnce(UuidPkMixin, TenantMixin, AuditMixin, Base):
    """Something announced only once (`closing:{form}:{closes_at}`, `export:{id}`, `digest:{date}`)."""

    __tablename__ = "notification_once"
    __table_args__ = tenant_table_args(Index("uq_notification_once_key", "tenant_id", "key", unique=True))

    key: Mapped[str] = mapped_column(String(200), nullable=False)

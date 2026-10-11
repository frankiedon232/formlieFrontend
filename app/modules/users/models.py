"""People and roles of a workspace (DATABASE-DESIGN → Identity and sessions; People, roles and access).

Every table here is a tenant table: tenant_id + organisation_id, RLS forced (migration 0003), soft delete only.
Secrets are never stored as they are: passwords as Argon2id, recovery codes as SHA-256, the authenticator secret
encrypted (`_enc`, MultiFernet).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)

USER_STATUSES = ("active", "not_activated", "invited", "pending", "disabled")
BUILT_IN = ("owner", "admin", "member")


class Role(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    """A role holds grants: each action with its scope ({"forms.edit": "own_shared"}). Owner is fixed."""

    __tablename__ = "roles"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"built_in IS NULL OR built_in IN {BUILT_IN}", name="built_in"),
        Index("uq_roles_name_active", "tenant_id", text("lower(name)"), unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("uq_roles_built_in", "tenant_id", "built_in", unique=True,
              postgresql_where=text("built_in IS NOT NULL AND deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    built_in: Mapped[str | None] = mapped_column(String(10))
    grants: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class User(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "users"
    __table_args__ = tenant_table_args(
        CheckConstraint(f"status IN {USER_STATUSES}", name="status"),
        CheckConstraint("email = lower(email)", name="email_lower"),
        tenant_fk("role_id", "roles"),
        tenant_fk("manager_id", "users"),
        Index("uq_users_email_active", "tenant_id", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_users_tenant_role", "tenant_id", "role_id"),
        Index("ix_users_tenant_status", "tenant_id", "status"),
    )

    email: Mapped[str] = mapped_column(String(254), nullable=False)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    photo_upload_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    language: Mapped[str | None] = mapped_column(String(10))
    time_zone: Mapped[str | None] = mapped_column(String(64))
    date_format: Mapped[str | None] = mapped_column(String(16))
    notifications: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    request_via: Mapped[str | None] = mapped_column(String(10))  # invite, link
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserPasswordHistory(UuidPkMixin, TenantMixin, Base):
    """Earlier password hashes, for Settings → Security "don't reuse the last N"."""

    __tablename__ = "user_password_history"
    __table_args__ = tenant_table_args(tenant_fk("user_id", "users"), Index("ix_user_password_history_user", "tenant_id", "user_id"))

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class UserTwoStep(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Authenticator app (TOTP) and text-message phone of one person. One active row per person."""

    __tablename__ = "user_two_step"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        Index("uq_user_two_step_user_active", "tenant_id", "user_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text)
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_phone_enc: Mapped[str | None] = mapped_column(Text)
    sms_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserRecoveryCode(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Ten per set; a new set soft-deletes the old one. A used code keeps its row with `used_at`."""

    __tablename__ = "user_recovery_codes"
    __table_args__ = tenant_table_args(tenant_fk("user_id", "users"), Index("ix_user_recovery_codes_user", "tenant_id", "user_id"))

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserIdentity(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """A sign-in provider linked to a person (Google, Microsoft, Apple, Facebook, single sign-on)."""

    __tablename__ = "user_identities"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        CheckConstraint("provider IN ('google', 'microsoft', 'facebook', 'sso')", name="provider"),
        Index("uq_user_identities_provider_subject", "tenant_id", "provider", "provider_user_id", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))


class UserTour(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Tips on new pages (first-visit tours): switched off, and the tours already offered (taken or skipped)."""

    __tablename__ = "user_tours"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        Index("uq_user_tours_user", "tenant_id", "user_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    tours_off: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    seen: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

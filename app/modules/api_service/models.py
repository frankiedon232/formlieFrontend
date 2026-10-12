"""The API service (DATABASE-DESIGN → API service; mock: data/apiStore.ts). Tenant tables, RLS forced, soft delete only.

- `api_settings`: one row per workspace: its address handle (also in `platform.api_keys_directory`, so the gateway
  finds the workspace from the address without a tenant context), the previous handle during a rotation, the rate
  limits and the request log settings.
- `api_services`: groups of endpoints, with the websites allowed to call them from a browser (CORS).
- `api_endpoints`: one form as an API: its name (unique in the workspace: it is the address), methods, the field
  choices (accept, required, returned, filter, API name) and the pinned form version.
- `api_tokens`: bearer tokens, client credentials and webhook tokens. Only a SHA-256 hash of each secret is looked
  up; the secret itself is kept encrypted (Fernet) so it can be shown again after the password (owner, 2026-10-06).
  The visible part is the prefix and last 4 characters.
- `api_access_rules`: allow / block by IP or range, domain, country, region or anonymous network, everywhere or for
  one service or endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args


class ApiSettings(UuidPkMixin, TenantMixin, AuditMixin, Base):
    __tablename__ = "api_settings"
    __table_args__ = tenant_table_args(
        Index("uq_api_settings_tenant", "tenant_id", unique=True),
        CheckConstraint("log_days IN (1, 7, 30)", name="log_days"),
    )

    api_key: Mapped[str] = mapped_column(String(16), nullable=False)
    previous_key: Mapped[str | None] = mapped_column(String(16))
    previous_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rate_per_token: Mapped[int | None] = mapped_column(Integer)
    rate_per_ip: Mapped[int | None] = mapped_column(Integer)
    rate_per_endpoint: Mapped[int | None] = mapped_column(Integer)
    limits_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    log_keep_bodies: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    log_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")


class ApiService(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "api_services"
    __table_args__ = tenant_table_args(
        CheckConstraint("status IN ('active', 'disabled')", name="status"),
        Index("uq_api_services_name", "tenant_id", text("lower(name)"), unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    allowed_origins: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class ApiEndpoint(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "api_endpoints"
    __table_args__ = tenant_table_args(
        tenant_fk("service_id", "api_services"),
        tenant_fk("form_id", "forms"),
        CheckConstraint("status IN ('active', 'disabled')", name="status"),
        CheckConstraint("page_size BETWEEN 1 AND 100", name="page_size"),
        Index("uq_api_endpoints_name", "tenant_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_api_endpoints_service", "tenant_id", "service_id"),
        Index("ix_api_endpoints_form", "tenant_id", "form_id"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int | None] = mapped_column(Integer)  # pinned form version; None = the latest published one
    methods: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    fields: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)  # key, name, accept, required, returned, filter
    page_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    headers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # name, value_enc
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="disabled")


class ApiToken(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "api_tokens"
    __table_args__ = tenant_table_args(
        CheckConstraint("kind IN ('static', 'client', 'webhook')", name="kind"),
        CheckConstraint("mode IN ('live', 'test')", name="mode"),
        Index("ix_api_tokens_secret_hash", "tenant_id", "secret_hash"),
        Index("ix_api_tokens_previous_hash", "tenant_id", "previous_hash", postgresql_where=text("previous_hash IS NOT NULL")),
        Index("uq_api_tokens_client_id", "tenant_id", "client_id", unique=True, postgresql_where=text("client_id IS NOT NULL")),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    mode: Mapped[str] = mapped_column(String(4), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    secret_enc: Mapped[str | None] = mapped_column(Text)
    preview: Mapped[str] = mapped_column(String(80), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    rotating_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_id: Mapped[str | None] = mapped_column(String(64))
    lifetime_minutes: Mapped[int | None] = mapped_column(Integer)
    signing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    signing_secret_enc: Mapped[str | None] = mapped_column(Text)
    scopes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # services, endpoints, methods
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiAccessRule(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "api_access_rules"
    __table_args__ = tenant_table_args(
        CheckConstraint("action IN ('allow', 'block')", name="action"),
        CheckConstraint("kind IN ('ip', 'domain', 'country', 'region', 'network')", name="kind"),
        CheckConstraint("scope_type IN ('all', 'service', 'endpoint')", name="scope_type"),
        Index("ix_api_access_rules_scope", "tenant_id", "scope_type", "scope_id"),
    )

    action: Mapped[str] = mapped_column(String(5), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    values: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="all")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    note: Mapped[str | None] = mapped_column(String(300))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

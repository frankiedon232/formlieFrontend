"""Single sign-on (Settings → Sign-in; the mock's data/ssoStore.ts): one connection per workspace to the company's
identity provider (SAML 2.0 or OpenID Connect). The client secret is Fernet-encrypted (`client_secret_enc`, write-only);
`idp` keeps what the last passing test read from the provider (SAML: entity id, sign-in address and certificates;
OIDC: the discovery document's endpoints), so a sign-in never has to ask the provider for it first."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args


class SsoConnection(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sso_connections"
    __table_args__ = tenant_table_args(
        Index("uq_sso_connections_tenant", "tenant_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint("protocol IN ('saml', 'oidc')", name="protocol"),
        CheckConstraint("status IN ('draft', 'tested', 'active')", name="status"),
    )

    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    protocol: Mapped[str] = mapped_column(String(4), nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    saml: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    oidc: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    client_secret_enc: Mapped[str | None] = mapped_column(Text)
    idp: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    domains: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    enforce: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    auto_create: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    default_role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(6), nullable=False, server_default="draft")
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    problem: Mapped[str | None] = mapped_column(String(20))

"""The platform admin bridge (B16, PLATFORM-ADMIN-INTEGRATION).

Global tables (schema `platform`, no tenant columns, no RLS): the platform admin writes them as `platform_writer`
(insert and update, never delete: `retired_at`), Formalie reads them as `formalie_app`, cached in Redis and dropped on
`platform.published`. Each row says who published it from the platform admin and when (`published_by_staff_id`,
`published_at`; both empty on rows shipped with Formalie by migration 0034).

Tenant tables (RLS forced): the workspace's consent to Formalie support (grants), Formalie's requests for it, and the
support sessions started against a grant.

`platform.admin_calls`: every internal admin API call (who, what, the outcome) and its idempotency key.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String,
    Text, Uuid, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_table_args

P = "platform"


class PublishedMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class RetiredMixin:
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Platform settings, reserved subdomains, feature switches, announcements ──────────────────────────────────────

class PlatformSetting(PublishedMixin, RetiredMixin, Base):
    """key → value: legal {terms_url, privacy_url}, support {email, url}, egress_ips [..], status_page {url},
    branding {...}. A row published by the Formalie team wins over the server's settings (.env)."""

    __tablename__ = "platform_settings"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class ReservedSubdomain(PublishedMixin, RetiredMixin, Base):
    """Subdomains no workspace may take, on top of the ones the host rules reserve (tenant.py)."""

    __tablename__ = "reserved_subdomains"
    __table_args__ = (CheckConstraint("subdomain = lower(subdomain)", name="subdomain_lower"), {"schema": P})

    subdomain: Mapped[str] = mapped_column(String(63), primary_key=True)
    reason: Mapped[str | None] = mapped_column(String(200))


class FeatureFlag(PublishedMixin, RetiredMixin, Base):
    """On for the listed workspaces, else for the listed plans (all when empty) in `rollout_percent` of workspaces."""

    __tablename__ = "feature_flags"
    __table_args__ = (CheckConstraint("rollout_percent BETWEEN 0 AND 100", name="rollout_percent"), {"schema": P})

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    plans: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    tenant_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False, server_default=text("'{}'"))
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")


class Announcement(PublishedMixin, RetiredMixin, Base):
    """A portal banner or maintenance notice for everyone, some plans or some workspaces, during a period."""

    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint("kind IN ('banner', 'maintenance', 'news')", name="kind"),
        CheckConstraint("tone IN ('info', 'warning', 'critical')", name="tone"),
        CheckConstraint("audience IN ('all', 'plans', 'tenants')", name="audience"),
        {"schema": P},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False, server_default="banner")
    tone: Mapped[str] = mapped_column(String(10), nullable=False, server_default="info")
    audience: Mapped[str] = mapped_column(String(10), nullable=False, server_default="all")
    plans: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    tenant_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid), nullable=False, server_default=text("'{}'"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    link_url: Mapped[str | None] = mapped_column(Text)
    dismissible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class AnnouncementTranslation(PublishedMixin, Base):
    __tablename__ = "announcement_translations"
    __table_args__ = (
        PrimaryKeyConstraint("announcement_id", "language"),
        ForeignKeyConstraint(["announcement_id"], [f"{P}.announcements.id"], ondelete="RESTRICT"),
        {"schema": P},
    )

    announcement_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    language: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)


# ── The plan catalogue (read by the portal with B15; shipped from app/modules/billing/plans.py) ───────────────────

class PlanRow(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "plans"
    __table_args__ = ({"schema": P},)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class PlanPrice(PublishedMixin, Base):
    """No row for a plan: "Contact us" (Enterprise)."""

    __tablename__ = "plan_prices"
    __table_args__ = (
        PrimaryKeyConstraint("plan_id", "period"),
        ForeignKeyConstraint(["plan_id"], [f"{P}.plans.id"], ondelete="RESTRICT"),
        CheckConstraint("period IN ('monthly', 'quarterly', 'annually')", name="period"),
        {"schema": P},
    )

    plan_id: Mapped[str] = mapped_column(String(40))
    period: Mapped[str] = mapped_column(String(12))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class PlanLimit(PublishedMixin, Base):
    """Null = no limit."""

    __tablename__ = "plan_limits"
    __table_args__ = (ForeignKeyConstraint(["plan_id"], [f"{P}.plans.id"], ondelete="RESTRICT"), {"schema": P})

    plan_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    forms: Mapped[int | None] = mapped_column(Integer)
    responses_per_form: Mapped[int | None] = mapped_column(Integer)
    databases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    sso: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    custom_domains: Mapped[int | None] = mapped_column(Integer)
    custom_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    data_residency: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ai_credits: Mapped[int | None] = mapped_column(Integer)
    languages: Mapped[int | None] = mapped_column(Integer)


class PlanFeature(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "plan_features"
    __table_args__ = (
        PrimaryKeyConstraint("plan_id", "feature"),
        ForeignKeyConstraint(["plan_id"], [f"{P}.plans.id"], ondelete="RESTRICT"),
        {"schema": P},
    )

    plan_id: Mapped[str] = mapped_column(String(40))
    feature: Mapped[str] = mapped_column(String(40))


# ── Formalie's default data and catalogues ───────────────────────────────────────────────────────────────────────

class SystemOptionList(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_option_lists"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    levels: Mapped[Any | None] = mapped_column(JSONB)
    columns: Mapped[Any | None] = mapped_column(JSONB)
    large: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SystemOptionItem(PublishedMixin, Base):
    __tablename__ = "system_option_items"
    __table_args__ = (
        PrimaryKeyConstraint("list_key", "value"),
        ForeignKeyConstraint(["list_key"], [f"{P}.system_option_lists.key"], ondelete="RESTRICT"),
        {"schema": P},
    )

    list_key: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    parent_value: Mapped[str | None] = mapped_column(String(200))
    translations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    attrs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class SystemFolder(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_folders"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name_key: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str | None] = mapped_column(String(20))
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SystemEmailTemplate(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_email_templates"
    __table_args__ = (PrimaryKeyConstraint("key", "language"), {"schema": P})

    key: Mapped[str] = mapped_column(String(40))
    language: Mapped[str] = mapped_column(String(10))
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class SystemTemplate(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_templates"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    design: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SystemTemplateTranslation(PublishedMixin, Base):
    __tablename__ = "system_template_translations"
    __table_args__ = (
        PrimaryKeyConstraint("template_key", "language"),
        ForeignKeyConstraint(["template_key"], [f"{P}.system_templates.key"], ondelete="RESTRICT"),
        {"schema": P},
    )

    template_key: Mapped[str] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class SystemTheme(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_themes"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    name_key: Mapped[str | None] = mapped_column(String(80))
    tokens: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class SystemPageDesign(PublishedMixin, RetiredMixin, Base):
    __tablename__ = "system_page_designs"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    name_key: Mapped[str | None] = mapped_column(String(80))
    tokens: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


# ── Support access (tenant tables, RLS forced) ───────────────────────────────────────────────────────────────────

SUPPORT_MODES = ("read", "write")


class SupportAccessGrant(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """The workspace allows Formalie support in for a while (Settings → Security → Formalie support access)."""

    __tablename__ = "support_access_grants"
    __table_args__ = tenant_table_args(
        CheckConstraint("mode IN ('read', 'write')", name="mode"),
        Index("ix_support_access_grants_open", "tenant_id", "expires_at", postgresql_where=text("revoked_at IS NULL")),
    )

    mode: Mapped[str] = mapped_column(String(5), nullable=False, server_default="read")
    hours: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granted_by_name: Mapped[str | None] = mapped_column(String(200))
    request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    revoked_reason: Mapped[str | None] = mapped_column(String(20))  # turned_off, replaced, expired


class SupportAccessRequest(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """Formalie support asks for access; the workspace's admins approve (a grant) or decline."""

    __tablename__ = "support_access_requests"
    __table_args__ = tenant_table_args(
        CheckConstraint("mode IN ('read', 'write')", name="mode"),
        CheckConstraint("status IN ('pending', 'approved', 'declined', 'expired')", name="status"),
        Index("ix_support_access_requests_pending", "tenant_id", "expires_at",
              postgresql_where=text("status = 'pending'")),
    )

    staff_id: Mapped[str] = mapped_column(String(64), nullable=False)
    staff_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(5), nullable=False, server_default="read")
    hours: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(64))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decided_by_name: Mapped[str | None] = mapped_column(String(200))
    grant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class SupportSession(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """One Formalie staff member's time in the workspace, started against a grant with a one-time ticket."""

    __tablename__ = "support_sessions"
    __table_args__ = tenant_table_args(
        CheckConstraint("mode IN ('read', 'write')", name="mode"),
        Index("ix_support_sessions_open", "tenant_id", "ends_at", postgresql_where=text("ended_at IS NULL")),
        Index("uq_support_sessions_ticket", "ticket_hash", unique=True, postgresql_where=text("ticket_hash IS NOT NULL")),
    )

    grant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    staff_id: Mapped[str] = mapped_column(String(64), nullable=False)
    staff_name: Mapped[str] = mapped_column(String(200), nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(5), nullable=False, server_default="read")
    ticket_hash: Mapped[str | None] = mapped_column(String(64))
    ticket_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_reason: Mapped[str | None] = mapped_column(String(20))  # signed_out, expired, access_ended, by_formalie
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── The internal admin API's call log and idempotency keys (global) ──────────────────────────────────────────────

class AdminCall(UuidPkMixin, Base):
    __tablename__ = "admin_calls"
    __table_args__ = (
        Index("uq_admin_calls_idempotency_key", "idempotency_key", unique=True,
              postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_admin_calls_tenant", "tenant_id", "created_at"),
        {"schema": P},
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    staff_id: Mapped[str | None] = mapped_column(String(64))
    staff_name: Mapped[str | None] = mapped_column(String(200))
    approval_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(20))
    response_enc: Mapped[str | None] = mapped_column(Text)  # the answer, encrypted: replayed for the same key

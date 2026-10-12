"""Forms, folders, published versions and per-form sharing (DATABASE-DESIGN → Forms and versions; mock
data/formStore.ts, formPermissions.ts). Tenant tables, RLS forced, nothing ever hard deleted:

- a form in Trash has `deleted_at`; purging it (permanently, or after 30 days) also stamps `purged_at`, and it is
  gone from every list and lookup while the row stays. Slugs and custom links are unique among forms not purged.
- `form_versions` are immutable published snapshots: the app may only insert and read them.
- Folder access (who may see a folder and its forms) sits on the folder row.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import (
    AuditMixin, Base, RowVersionMixin, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args,
)

FORM_STATUSES = ("draft", "published", "closed", "archived")
FORM_ACCESS = ("public", "password", "invite", "organisation")


class Folder(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "folders"
    __table_args__ = tenant_table_args(
        Index("uq_folders_name", "tenant_id", text("lower(name)"), unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    name: Mapped[str] = mapped_column(String(60), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16))
    system_key: Mapped[str | None] = mapped_column(String(40))
    # Folder access (F22 R2): restricted folders, their forms and responses, only show to these
    access_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    access_roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    access_departments: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    access_people: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class Form(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, RowVersionMixin, Base):
    __tablename__ = "forms"
    __table_args__ = tenant_table_args(
        tenant_fk("folder_id", "folders"),
        tenant_fk("owner_id", "users"),
        CheckConstraint(f"status IN {FORM_STATUSES}", name="status"),
        CheckConstraint(f"access IN {FORM_ACCESS}", name="access"),
        CheckConstraint("team_access IN ('edit', 'view', 'none')", name="team_access"),
        Index("uq_forms_slug", "tenant_id", "slug", unique=True, postgresql_where=text("purged_at IS NULL")),
        Index("uq_forms_public_key", "public_key", unique=True),
        Index("uq_forms_custom_link", "tenant_id", "custom_link", unique=True,
              postgresql_where=text("custom_link IS NOT NULL AND purged_at IS NULL")),
        Index("uq_forms_short_code", "short_code", unique=True, postgresql_where=text("short_code IS NOT NULL")),
        Index("ix_forms_tenant_updated", "tenant_id", "updated_at"),
        Index("ix_forms_tenant_folder", "tenant_id", "folder_id"),
        Index("ix_forms_tenant_owner", "tenant_id", "owner_id"),
        # Query review I8 (0037): the list's plain filters, the Trash sweep, tags, closing announcements
        Index("ix_forms_live", "tenant_id", "status", text("updated_at DESC"),
              postgresql_where=text("deleted_at IS NULL AND purged_at IS NULL")),
        Index("ix_forms_trash", "tenant_id", "deleted_at",
              postgresql_where=text("deleted_at IS NOT NULL AND purged_at IS NULL")),
        Index("ix_forms_tags", "tags", postgresql_using="gin", postgresql_ops={"tags": "jsonb_path_ops"},
              postgresql_where=text("purged_at IS NULL")),
        Index("ix_forms_closing", "tenant_id", "closes_at",
              postgresql_where=text("status = 'published' AND deleted_at IS NULL")),
    )

    folder_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(70), nullable=False)
    public_key: Mapped[str] = mapped_column(String(20), nullable=False)
    custom_link: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")
    previous_status: Mapped[str | None] = mapped_column(String(10))
    draft_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    has_unpublished_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    template_key: Mapped[str | None] = mapped_column(String(80))
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    channels: Mapped[list[Any] | None] = mapped_column(JSONB)  # null = all three (link, embed, api)
    access: Mapped[str] = mapped_column(String(14), nullable=False, server_default="public")
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_limit: Mapped[int | None] = mapped_column(Integer)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embed_domains: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    team_access: Mapped[str] = mapped_column(String(6), nullable=False, server_default="edit")
    seo: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    short_code: Mapped[str | None] = mapped_column(String(16))
    short_clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    short_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responses_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_response_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    completion_rate: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FormVersion(UuidPkMixin, TenantMixin, Base):
    """A published snapshot. Immutable: inserted once, never changed."""

    __tablename__ = "form_versions"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        Index("uq_form_versions_number", "tenant_id", "form_id", "number", unique=True),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    published_by_name: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(500))
    fields_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class FormGrant(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """People access (decision 97): a person given a level on one form; `forms.team_access` is everyone else's."""

    __tablename__ = "form_grants"
    __table_args__ = tenant_table_args(
        tenant_fk("form_id", "forms"),
        tenant_fk("user_id", "users"),
        CheckConstraint("level IN ('responses', 'view', 'edit')", name="level"),
        Index("uq_form_grants", "tenant_id", "form_id", "user_id", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

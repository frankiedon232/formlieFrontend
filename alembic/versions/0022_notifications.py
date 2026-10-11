"""Notifications: each person's feed, the daily summary queue and things announced once

Revision ID: 0022
Revises: 0021
Created: 2026-10-11 18:48:08.160845+00:00

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = '0022'
down_revision: str | None = '0021'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('notification_digest_lines',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('line', sa.String(length=500), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_digest_lines')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_notification_digest_lines_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_notification_digest_lines_open', 'notification_digest_lines', ['tenant_id', 'email'], unique=False, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('notification_once',
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_once')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_notification_once_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_notification_once_key', 'notification_once', ['tenant_id', 'key'], unique=True, schema='formaly')
    op.create_table('notifications',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('event', sa.String(length=40), nullable=False),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('link', sa.String(length=500), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_notifications_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_notifications_user', 'notifications', ['tenant_id', 'user_id', 'created_at'], unique=False, schema='formaly')
    for statement in enable_tenant_rls("notifications"):
        op.execute(statement)
    for statement in enable_tenant_rls("notification_digest_lines"):
        op.execute(statement)
    for statement in enable_tenant_rls("notification_once"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("notification_once"):
        op.execute(statement)
    op.drop_table("notification_once", schema="formaly")
    for statement in disable_tenant_rls("notification_digest_lines"):
        op.execute(statement)
    op.drop_table("notification_digest_lines", schema="formaly")
    for statement in disable_tenant_rls("notifications"):
        op.execute(statement)
    op.drop_table("notifications", schema="formaly")

"""Invitations to invite-only forms (one person, one response; the token is kept as a hash)

Revision ID: 0017
Revises: 0016
Created: 2026-10-11 17:21:18.251915+00:00

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = '0017'
down_revision: str | None = '0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('form_invitations',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_form_invitations_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_form_invitations')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_form_invitations_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_form_invitations_form', 'form_invitations', ['tenant_id', 'form_id', 'sent_at'], unique=False, schema='formaly')
    op.create_index('uq_form_invitations_email', 'form_invitations', ['tenant_id', 'form_id', 'email'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL AND revoked_at IS NULL'))
    op.create_index('uq_form_invitations_token', 'form_invitations', ['token_hash'], unique=True, schema='formaly')
    for statement in enable_tenant_rls("form_invitations"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("form_invitations"):
        op.execute(statement)
    op.drop_table("form_invitations", schema="formaly")

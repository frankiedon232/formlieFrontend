"""Ways into a workspace: personal links (user_invites) and the shared sign-up link (signup_links).

Revision ID: 0010
Revises: 0009
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("user_invites", "signup_links")


def upgrade() -> None:
    op.create_table('signup_links',
    sa.Column('enabled', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('token_enc', sa.Text(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('domains', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_signup_links')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_signup_links_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('user_invites',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('invited_by', sa.Uuid(), nullable=True),
    sa.Column('invited_by_name', sa.String(length=200), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
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
    sa.CheckConstraint("kind IN ('invite', 'activation')", name=op.f('ck_user_invites_kind')),
    sa.ForeignKeyConstraint(['tenant_id', 'user_id'], ['formaly.users.tenant_id', 'formaly.users.id'], name=op.f('fk_user_invites_tenant_id_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_invites')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_user_invites_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_signup_links_tenant', 'signup_links', ['tenant_id'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('uq_signup_links_token', 'signup_links', ['token_hash'], unique=True, schema='formaly')
    op.create_index('ix_user_invites_user', 'user_invites', ['tenant_id', 'user_id', 'sent_at'], unique=False, schema='formaly')
    op.create_index('uq_user_invites_token', 'user_invites', ['token_hash'], unique=True, schema='formaly')
    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)


def downgrade() -> None:
    for table in TABLES:
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema="formaly")

"""Option lists and their options (one row per option, matched by value).

Revision ID: 0014
Revises: 0013
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("option_lists", "option_items")


def upgrade() -> None:
    op.create_table('option_lists',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('levels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('columns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('large', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('system_key', sa.String(length=40), nullable=True),
    sa.Column('active_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_option_lists')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_option_lists_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('option_items',
    sa.Column('list_id', sa.Uuid(), nullable=False),
    sa.Column('level', sa.Integer(), server_default='0', nullable=False),
    sa.Column('parent_value', sa.String(length=200), nullable=True),
    sa.Column('value', sa.String(length=200), nullable=False),
    sa.Column('label', sa.String(length=500), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('translations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('attrs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'list_id'], ['formaly.option_lists.tenant_id', 'formaly.option_lists.id'], name=op.f('fk_option_items_tenant_id_list_id_option_lists'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_option_items')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_option_items_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_option_lists_name', 'option_lists', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_option_items_list', 'option_items', ['tenant_id', 'list_id', 'level', 'sort_order'], unique=False, schema='formaly')
    op.create_index('uq_option_items_value', 'option_items', ['tenant_id', 'list_id', sa.literal_column('lower(value)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)


def downgrade() -> None:
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema="formaly")

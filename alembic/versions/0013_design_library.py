"""The design library: the workspace's own themes and page designs, and saved fields.

Revision ID: 0013
Revises: 0012
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("themes", "page_designs", "saved_fields")


def upgrade() -> None:
    op.create_table('themes',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('source', sa.String(length=10), server_default='saved', nullable=False),
    sa.Column('tokens', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
    sa.CheckConstraint("source IN ('saved', 'created')", name=op.f('ck_themes_source')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_themes')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_themes_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('page_designs',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('source', sa.String(length=10), server_default='saved', nullable=False),
    sa.Column('tokens', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
    sa.CheckConstraint("source IN ('saved', 'created')", name=op.f('ck_page_designs_source')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_page_designs')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_page_designs_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('saved_fields',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('field', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_saved_fields')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_saved_fields_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_page_designs_name', 'page_designs', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('uq_themes_name', 'themes', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)


def downgrade() -> None:
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema="formaly")

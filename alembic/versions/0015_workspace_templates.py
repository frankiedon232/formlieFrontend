"""The workspace's own templates (Formalie's catalogue is data in app/modules/templates/data).

Revision ID: 0015
Revises: 0014
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('workspace_templates',
    sa.Column('key_id', sa.String(length=12), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=300), server_default='', nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('icon', sa.String(length=80), nullable=False),
    sa.Column('schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source_form_id', sa.Uuid(), nullable=True),
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
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workspace_templates')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_workspace_templates_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_workspace_templates_key', 'workspace_templates', ['tenant_id', 'key_id'], unique=True, schema='formaly')
    op.create_index('uq_workspace_templates_name', 'workspace_templates', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for statement in enable_tenant_rls("workspace_templates"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("workspace_templates"):
        op.execute(statement)
    op.drop_table("workspace_templates", schema="formaly")

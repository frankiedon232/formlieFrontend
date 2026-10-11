"""Organisation data: departments and job titles (org_units) and the people in them (org_unit_members).

Revision ID: 0009
Revises: 0008
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("org_units", "org_unit_members")


def upgrade() -> None:
    op.create_table('org_units',
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("kind IN ('departments', 'job_titles')", name=op.f('ck_org_units_kind')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_org_units')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_org_units_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('org_unit_members',
    sa.Column('org_unit_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'org_unit_id'], ['formaly.org_units.tenant_id', 'formaly.org_units.id'], name=op.f('fk_org_unit_members_tenant_id_org_unit_id_org_units'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'user_id'], ['formaly.users.tenant_id', 'formaly.users.id'], name=op.f('fk_org_unit_members_tenant_id_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_org_unit_members')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_org_unit_members_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_org_units_name', 'org_units', ['tenant_id', 'kind', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_org_unit_members_user', 'org_unit_members', ['tenant_id', 'user_id'], unique=False, schema='formaly')
    op.create_index('uq_org_unit_members', 'org_unit_members', ['tenant_id', 'org_unit_id', 'user_id'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)


def downgrade() -> None:
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema="formaly")

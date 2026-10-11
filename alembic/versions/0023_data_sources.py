"""Data sources: connections, tests, health checks, daily operations

Revision ID: 0023
Revises: 0022
Created: 2026-10-11 19:13:02.720192+00:00

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = '0023'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('datasource_tests',
    sa.Column('datasource_id', sa.Uuid(), nullable=True),
    sa.Column('label', sa.String(length=300), nullable=False),
    sa.Column('status', sa.String(length=10), server_default='running', nullable=False),
    sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('findings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('schemas', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('server_version', sa.String(length=100), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('tables_count', sa.Integer(), nullable=True),
    sa.Column('config_enc', sa.Text(), nullable=True),
    sa.Column('audited', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('running', 'passed', 'warning', 'failed')", name=op.f('ck_datasource_tests_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datasource_tests')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_datasource_tests_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_datasource_tests_source', 'datasource_tests', ['tenant_id', 'datasource_id', 'started_at'], unique=False, schema='formaly')
    op.create_table('datasources',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('engine', sa.String(length=12), nullable=False),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('secrets_enc', sa.Text(), nullable=True),
    sa.Column('secrets_set', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('secrets_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('access', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('last_test_id', sa.Uuid(), nullable=True),
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
    sa.CheckConstraint("engine IN ('mysql', 'postgresql', 'sqlserver', 'oracle', 'mariadb')", name=op.f('ck_datasources_engine')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datasources')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_datasources_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_datasources_name', 'datasources', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('datasource_checks',
    sa.Column('datasource_id', sa.Uuid(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('passed', 'warning', 'failed')", name=op.f('ck_datasource_checks_status')),
    sa.ForeignKeyConstraint(['tenant_id', 'datasource_id'], ['formaly.datasources.tenant_id', 'formaly.datasources.id'], name=op.f('fk_datasource_checks_tenant_id_datasource_id_datasources'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datasource_checks')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_datasource_checks_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_datasource_checks_source', 'datasource_checks', ['tenant_id', 'datasource_id', 'at'], unique=False, schema='formaly')
    op.create_table('datasource_ops_daily',
    sa.Column('datasource_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'datasource_id'], ['formaly.datasources.tenant_id', 'formaly.datasources.id'], name=op.f('fk_datasource_ops_daily_tenant_id_datasource_id_datasources'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_datasource_ops_daily')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_datasource_ops_daily_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_datasource_ops_daily', 'datasource_ops_daily', ['tenant_id', 'datasource_id', 'day'], unique=True, schema='formaly')
    for statement in enable_tenant_rls("datasources"):
        op.execute(statement)
    for statement in enable_tenant_rls("datasource_tests"):
        op.execute(statement)
    for statement in enable_tenant_rls("datasource_checks"):
        op.execute(statement)
    for statement in enable_tenant_rls("datasource_ops_daily"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("datasource_ops_daily"):
        op.execute(statement)
    op.drop_table("datasource_ops_daily", schema="formaly")
    for statement in disable_tenant_rls("datasource_checks"):
        op.execute(statement)
    op.drop_table("datasource_checks", schema="formaly")
    for statement in disable_tenant_rls("datasource_tests"):
        op.execute(statement)
    op.drop_table("datasource_tests", schema="formaly")
    for statement in disable_tenant_rls("datasources"):
        op.execute(statement)
    op.drop_table("datasources", schema="formaly")

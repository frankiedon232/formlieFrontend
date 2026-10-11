"""query editor

Revision ID: 0026
Revises: 0025
Also: explorer and Query editor exports are export jobs too (formats json and sql).

Created: 2026-10-11 20:01:20.950571+00:00

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = '0026'
down_revision: str | None = '0025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('query_history',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('datasource_id', sa.Uuid(), nullable=False),
    sa.Column('sql', sa.Text(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('ran_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('rows', sa.Integer(), nullable=True),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'datasource_id'], ['formaly.datasources.tenant_id', 'formaly.datasources.id'], name=op.f('fk_query_history_tenant_id_datasource_id_datasources'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_query_history')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_query_history_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_query_history_person', 'query_history', ['tenant_id', 'user_id', 'datasource_id', 'ran_at'], unique=False, schema='formaly')
    op.create_table('saved_queries',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('sql', sa.Text(), nullable=False),
    sa.Column('datasource_id', sa.Uuid(), nullable=False),
    sa.Column('shared', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'datasource_id'], ['formaly.datasources.tenant_id', 'formaly.datasources.id'], name=op.f('fk_saved_queries_tenant_id_datasource_id_datasources'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_saved_queries')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_saved_queries_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_saved_queries_owner', 'saved_queries', ['tenant_id', 'owner_id'], unique=False, schema='formaly')
    op.create_table('saved_query_runs_daily',
    sa.Column('saved_query_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('runs', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'saved_query_id'], ['formaly.saved_queries.tenant_id', 'formaly.saved_queries.id'], name=op.f('fk_saved_query_runs_daily_tenant_id_saved_query_id_saved_queries'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_saved_query_runs_daily')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_saved_query_runs_daily_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_saved_query_runs_daily', 'saved_query_runs_daily', ['tenant_id', 'saved_query_id', 'day'], unique=True, schema='formaly')
    for statement in enable_tenant_rls("query_history"):
        op.execute(statement)
    for statement in enable_tenant_rls("saved_queries"):
        op.execute(statement)
    for statement in enable_tenant_rls("saved_query_runs_daily"):
        op.execute(statement)
    op.execute("ALTER TABLE formaly.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute("ALTER TABLE formaly.export_jobs ADD CONSTRAINT ck_export_jobs_format "
               "CHECK (format IN ('xlsx', 'csv', 'pdf', 'json', 'sql'))")


def downgrade() -> None:
    op.execute("ALTER TABLE formaly.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute("ALTER TABLE formaly.export_jobs ADD CONSTRAINT ck_export_jobs_format CHECK (format IN ('xlsx', 'csv', 'pdf'))")
    for statement in disable_tenant_rls("saved_query_runs_daily"):
        op.execute(statement)
    op.drop_table("saved_query_runs_daily", schema="formaly")
    for statement in disable_tenant_rls("saved_queries"):
        op.execute(statement)
    op.drop_table("saved_queries", schema="formaly")
    for statement in disable_tenant_rls("query_history"):
        op.execute(statement)
    op.drop_table("query_history", schema="formaly")

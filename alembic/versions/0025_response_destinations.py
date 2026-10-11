"""response destinations

Revision ID: 0025
Revises: 0024
Created: 2026-10-11 19:25:29.178249+00:00

Deliveries and backfills run for every workspace: platform.deliveries_due() and platform.backfills_running() list
them (ids and the workspace's subdomain, for links in rows) so the worker can handle each in its own workspace's context.

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = '0025'
down_revision: str | None = '0024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"


def upgrade() -> None:
    op.create_table('response_destinations',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('datasource_id', sa.Uuid(), nullable=False),
    sa.Column('table_schema', sa.String(length=128), server_default='', nullable=False),
    sa.Column('table_name', sa.String(length=128), nullable=False),
    sa.Column('table_created', sa.Boolean(), nullable=False),
    sa.Column('columns', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('covers_from', sa.DateTime(timezone=True), nullable=False),
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
    sa.ForeignKeyConstraint(['tenant_id', 'datasource_id'], ['formaly.datasources.tenant_id', 'formaly.datasources.id'], name=op.f('fk_response_destinations_tenant_id_datasource_id_datasources'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_response_destinations_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_response_destinations')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_response_destinations_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_response_destinations_source', 'response_destinations', ['tenant_id', 'datasource_id'], unique=False, schema='formaly')
    op.create_index('uq_response_destinations_form', 'response_destinations', ['tenant_id', 'form_id'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('destination_backfills',
    sa.Column('destination_id', sa.Uuid(), nullable=False),
    sa.Column('range_from', sa.DateTime(timezone=True), nullable=False),
    sa.Column('range_to', sa.DateTime(timezone=True), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('done', sa.Integer(), server_default='0', nullable=False),
    sa.Column('status', sa.String(length=8), server_default='running', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('running', 'done')", name=op.f('ck_destination_backfills_status')),
    sa.ForeignKeyConstraint(['tenant_id', 'destination_id'], ['formaly.response_destinations.tenant_id', 'formaly.response_destinations.id'], name=op.f('fk_destination_backfills_tenant_id_destination_id_response_destinations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_destination_backfills')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_destination_backfills_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_destination_backfills', 'destination_backfills', ['tenant_id', 'destination_id', 'started_at'], unique=False, schema='formaly')
    op.create_table('destination_deliveries',
    sa.Column('destination_id', sa.Uuid(), nullable=False),
    sa.Column('response_id', sa.Uuid(), nullable=False),
    sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=8), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('pending', 'sent', 'failed', 'held')", name=op.f('ck_destination_deliveries_status')),
    sa.ForeignKeyConstraint(['tenant_id', 'destination_id'], ['formaly.response_destinations.tenant_id', 'formaly.response_destinations.id'], name=op.f('fk_destination_deliveries_tenant_id_destination_id_response_destinations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_destination_deliveries')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_destination_deliveries_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_destination_deliveries_due', 'destination_deliveries', ['next_attempt_at'], unique=False, schema='formaly', postgresql_where=sa.text("status IN ('pending', 'failed')"))
    op.create_index('ix_destination_deliveries_list', 'destination_deliveries', ['tenant_id', 'destination_id', 'response_submitted_at'], unique=False, schema='formaly')
    op.create_index('uq_destination_deliveries', 'destination_deliveries', ['tenant_id', 'destination_id', 'response_id'], unique=True, schema='formaly')
    for statement in enable_tenant_rls("response_destinations"):
        op.execute(statement)
    for statement in enable_tenant_rls("destination_deliveries"):
        op.execute(statement)
    for statement in enable_tenant_rls("destination_backfills"):
        op.execute(statement)
    op.execute(f"GRANT SELECT (id, tenant_id, organisation_id, status, next_attempt_at) ON {S}.destination_deliveries "
               "TO formalie_directory")
    op.execute(f"GRANT SELECT (id, tenant_id, organisation_id, status) ON {S}.destination_backfills TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION platform.deliveries_due(max_rows integer)
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, subdomain text, delivery_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT d.tenant_id, d.organisation_id, t.subdomain::text, d.id FROM {S}.destination_deliveries d
              JOIN platform.tenants t ON t.id = d.tenant_id
             WHERE d.status IN ('pending', 'failed') AND d.next_attempt_at <= now()
             ORDER BY d.next_attempt_at LIMIT max_rows
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.backfills_running()
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, subdomain text, backfill_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT b.tenant_id, b.organisation_id, t.subdomain::text, b.id FROM {S}.destination_backfills b
              JOIN platform.tenants t ON t.id = b.tenant_id
             WHERE b.status = 'running'
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    for name in ("deliveries_due(integer)", "backfills_running()"):
        op.execute(f"ALTER FUNCTION platform.{name} OWNER TO formalie_directory")
        op.execute(f"REVOKE ALL ON FUNCTION platform.{name} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION platform.{name} TO formalie_app")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.deliveries_due(integer)")
    op.execute("DROP FUNCTION IF EXISTS platform.backfills_running()")
    for statement in disable_tenant_rls("destination_backfills"):
        op.execute(statement)
    op.drop_table("destination_backfills", schema="formaly")
    for statement in disable_tenant_rls("destination_deliveries"):
        op.execute(statement)
    op.drop_table("destination_deliveries", schema="formaly")
    for statement in disable_tenant_rls("response_destinations"):
        op.execute(statement)
    op.drop_table("response_destinations", schema="formaly")

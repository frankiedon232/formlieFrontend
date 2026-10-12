"""The public API service gateway (B10 step 3): the Formalie-Key of each POST, kept 24 hours.

  api_idempotency                             one row per endpoint and Formalie-Key (unique while not deleted)
  platform.api_idempotency_expired()          workspaces with keys older than 24 hours (Beat retires them hourly;
                                              owned by formalie_directory, lists ids only, like 0028's functions)

Revision ID: 0030
Revises: 0029
Created: 2026-10-12

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = '0030'
down_revision: str | None = '0029'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('api_idempotency',
    sa.Column('endpoint_id', sa.Uuid(), nullable=False),
    sa.Column('formalie_key', sa.String(length=100), nullable=False),
    sa.Column('body_hash', sa.String(length=64), nullable=False),
    sa.Column('response_id', sa.Uuid(), nullable=True),
    sa.Column('answer', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'endpoint_id'], ['formaly.api_endpoints.tenant_id', 'formaly.api_endpoints.id'],
                            name=op.f('fk_api_idempotency_tenant_id_endpoint_id_api_endpoints'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_idempotency')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_idempotency_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_api_idempotency_key', 'api_idempotency', ['tenant_id', 'endpoint_id', 'formalie_key'],
                    unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_api_idempotency_at', 'api_idempotency', ['tenant_id', 'at'], unique=False, schema='formaly')
    for statement in enable_tenant_rls("api_idempotency"):
        op.execute(statement)
    op.execute("GRANT SELECT (tenant_id, organisation_id, at, deleted_at) ON formaly.api_idempotency TO formalie_directory")
    op.execute("""
        CREATE FUNCTION platform.api_idempotency_expired()
        RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT DISTINCT k.tenant_id, k.organisation_id FROM formaly.api_idempotency k
             WHERE k.deleted_at IS NULL AND k.at < now() - interval '24 hours'
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    op.execute("ALTER FUNCTION platform.api_idempotency_expired() OWNER TO formalie_directory")
    op.execute("REVOKE ALL ON FUNCTION platform.api_idempotency_expired() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.api_idempotency_expired() TO formalie_app")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.api_idempotency_expired()")
    op.execute("REVOKE SELECT (tenant_id, organisation_id, at, deleted_at) ON formaly.api_idempotency FROM formalie_directory")
    for statement in disable_tenant_rls("api_idempotency"):
        op.execute(statement)
    op.drop_index('ix_api_idempotency_at', table_name='api_idempotency', schema='formaly')
    op.drop_index('uq_api_idempotency_key', table_name='api_idempotency', schema='formaly')
    op.drop_table('api_idempotency', schema='formaly')

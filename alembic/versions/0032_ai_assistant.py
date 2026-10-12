"""AI assistant (B13, F19): the workspace's settings, every request, and the month's usage.

  ai_settings                     one row per workspace (unique while not deleted)
  ai_requests                     every request (kind, status, who, prompt, result, draft, engine, tokens); soft
                                  deleted and emptied past the workspace's keep setting or when a person removes it
  ai_usage                        per workspace and month: requests, credits, model calls, tokens
  platform.ai_requests_expired()  workspaces with requests past their keep setting (Beat empties them hourly; owned
                                  by formalie_directory, lists ids only, like 0028's functions)

Revision ID: 0032
Revises: 0031
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

revision: str = '0032'
down_revision: str | None = '0031'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
KINDS = "('form', 'template', 'theme', 'builder', 'analysis', 'question', 'summary', 'translate', 'rewrite')"


def _common() -> list[sa.Column]:
    return [
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('organisation_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
    ]


def _deleted() -> list[sa.Column]:
    return [sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_by', sa.Uuid(), nullable=True)]


def upgrade() -> None:
    op.create_table('ai_settings',
    sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('mask_personal', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('keep_days', sa.Integer(), server_default='90', nullable=False),
    sa.Column('monthly_credits', sa.Integer(), server_default='500', nullable=False),
    sa.Column('updated_by_name', sa.String(length=200), nullable=True),
    *_common(), *_deleted(),
    sa.CheckConstraint('keep_days IN (30, 90, 180, 365)', name=op.f('ck_ai_settings_keep_days')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_settings')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_ai_settings_tenant_id_id')),
    schema=S
    )
    op.create_index('uq_ai_settings_tenant', 'ai_settings', ['tenant_id'], unique=True, schema=S,
                    postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_table('ai_requests',
    sa.Column('kind', sa.String(length=12), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('title_key', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('by_id', sa.Uuid(), nullable=False),
    sa.Column('by_name', sa.String(length=200), nullable=False),
    sa.Column('target', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('credits', sa.Integer(), server_default='0', nullable=False),
    sa.Column('prompt', sa.Text(), server_default='', nullable=False),
    sa.Column('result', sa.Text(), server_default='', nullable=False),
    sa.Column('read', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('masked', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('engine', sa.String(length=10), server_default='standin', nullable=False),
    sa.Column('model', sa.String(length=80), nullable=True),
    sa.Column('fallback_reason', sa.String(length=40), nullable=True),
    sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False),
    sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False),
    sa.Column('cache_read_tokens', sa.Integer(), server_default='0', nullable=False),
    sa.Column('cache_write_tokens', sa.Integer(), server_default='0', nullable=False),
    *_common(), *_deleted(),
    sa.CheckConstraint(f'kind IN {KINDS}', name=op.f('ck_ai_requests_kind')),
    sa.CheckConstraint("status IN ('proposed', 'applied', 'discarded', 'failed')", name=op.f('ck_ai_requests_status')),
    sa.CheckConstraint("engine IN ('model', 'standin', 'fallback')", name=op.f('ck_ai_requests_engine')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_requests')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_ai_requests_tenant_id_id')),
    schema=S
    )
    op.create_index('ix_ai_requests_tenant_created', 'ai_requests', ['tenant_id', 'created_at'], schema=S)
    op.create_index('ix_ai_requests_tenant_by', 'ai_requests', ['tenant_id', 'by_id'], schema=S)

    op.create_table('ai_usage',
    sa.Column('month', sa.Date(), nullable=False),
    sa.Column('requests', sa.Integer(), server_default='0', nullable=False),
    sa.Column('credits', sa.Integer(), server_default='0', nullable=False),
    sa.Column('model_calls', sa.Integer(), server_default='0', nullable=False),
    sa.Column('input_tokens', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('output_tokens', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('cache_read_tokens', sa.BigInteger(), server_default='0', nullable=False),
    sa.Column('cache_write_tokens', sa.BigInteger(), server_default='0', nullable=False),
    *_common(),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_usage')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_ai_usage_tenant_id_id')),
    schema=S
    )
    op.create_index('uq_ai_usage_month', 'ai_usage', ['tenant_id', 'month'], unique=True, schema=S)

    for table in ('ai_settings', 'ai_requests', 'ai_usage'):
        for statement in enable_tenant_rls(table):
            op.execute(statement)

    # ── Beat's list across workspaces (ids only) ──────────────────────────────
    op.execute(f"GRANT SELECT (tenant_id, organisation_id, created_at, deleted_at) ON {S}.ai_requests TO formalie_directory")
    op.execute(f"GRANT SELECT (tenant_id, keep_days, deleted_at) ON {S}.ai_settings TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION platform.ai_requests_expired()
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, keep_days integer)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT r.tenant_id, r.organisation_id, coalesce(min(s.keep_days), 90) FROM {S}.ai_requests r
              LEFT JOIN {S}.ai_settings s ON s.tenant_id = r.tenant_id AND s.deleted_at IS NULL
             WHERE r.deleted_at IS NULL
             GROUP BY r.tenant_id, r.organisation_id
            HAVING min(r.created_at) < now() - make_interval(days => coalesce(min(s.keep_days), 90))
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    op.execute("ALTER FUNCTION platform.ai_requests_expired() OWNER TO formalie_directory")
    op.execute("REVOKE ALL ON FUNCTION platform.ai_requests_expired() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.ai_requests_expired() TO formalie_app")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.ai_requests_expired()")
    op.execute(f"REVOKE SELECT (tenant_id, keep_days, deleted_at) ON {S}.ai_settings FROM formalie_directory")
    op.execute(f"REVOKE SELECT (tenant_id, organisation_id, created_at, deleted_at) ON {S}.ai_requests FROM formalie_directory")
    for table in ('ai_usage', 'ai_requests', 'ai_settings'):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
    op.drop_index('uq_ai_usage_month', table_name='ai_usage', schema=S)
    op.drop_table('ai_usage', schema=S)
    op.drop_index('ix_ai_requests_tenant_by', table_name='ai_requests', schema=S)
    op.drop_index('ix_ai_requests_tenant_created', table_name='ai_requests', schema=S)
    op.drop_table('ai_requests', schema=S)
    op.drop_index('uq_ai_settings_tenant', table_name='ai_settings', schema=S)
    op.drop_table('ai_settings', schema=S)

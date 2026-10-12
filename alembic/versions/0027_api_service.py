"""API service (B10 step 1): settings, services, endpoints, tokens and access rules, plus the address handles
(`{apiKey}` in `api.formalie.*/{apiKey}/{endpoint}`) in the tenant directory, so the gateway finds the workspace from
the address before it has a tenant context (DATABASE-DESIGN → Tenant directory). The app reaches the directory only
through these functions, always for the workspace of its own transaction (app.tenant_id):

  platform.claim_api_key(key)               → true when the handle was free (never used before, by anyone)
  platform.retire_api_key(key, until)       the handle stops answering at `until` (a rotation's grace period)
  platform.resolve_api_key(key)             → the workspace behind a handle that still answers, and whether it is
                                              the current one (the gateway, B10 step 3)

Revision ID: 0027
Revises: 0026
Created: 2026-10-12 11:36:59.255238+00:00

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

CURRENT_TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"
FUNCTIONS = ("platform.claim_api_key(text)", "platform.retire_api_key(text, timestamptz)", "platform.resolve_api_key(text)")

revision: str = '0027'
down_revision: str | None = '0026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('api_access_rules',
    sa.Column('action', sa.String(length=5), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('values', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('scope_type', sa.String(length=10), server_default='all', nullable=False),
    sa.Column('scope_id', sa.Uuid(), nullable=True),
    sa.Column('note', sa.String(length=300), nullable=True),
    sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('last_hit_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("action IN ('allow', 'block')", name=op.f('ck_api_access_rules_action')),
    sa.CheckConstraint("kind IN ('ip', 'domain', 'country', 'region', 'network')", name=op.f('ck_api_access_rules_kind')),
    sa.CheckConstraint("scope_type IN ('all', 'service', 'endpoint')", name=op.f('ck_api_access_rules_scope_type')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_access_rules')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_access_rules_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_api_access_rules_scope', 'api_access_rules', ['tenant_id', 'scope_type', 'scope_id'], unique=False, schema='formaly')
    op.create_table('api_services',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('status', sa.String(length=10), server_default='active', nullable=False),
    sa.Column('allowed_origins', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('active', 'disabled')", name=op.f('ck_api_services_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_services')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_services_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_api_services_name', 'api_services', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('api_settings',
    sa.Column('api_key', sa.String(length=16), nullable=False),
    sa.Column('previous_key', sa.String(length=16), nullable=True),
    sa.Column('previous_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rate_per_token', sa.Integer(), nullable=True),
    sa.Column('rate_per_ip', sa.Integer(), nullable=True),
    sa.Column('rate_per_endpoint', sa.Integer(), nullable=True),
    sa.Column('limits_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('log_keep_bodies', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('log_days', sa.Integer(), server_default='7', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint('log_days IN (1, 7, 30)', name=op.f('ck_api_settings_log_days')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_settings')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_settings_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_api_settings_tenant', 'api_settings', ['tenant_id'], unique=True, schema='formaly')
    op.create_table('api_tokens',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('mode', sa.String(length=4), nullable=False),
    sa.Column('secret_hash', sa.String(length=64), nullable=False),
    sa.Column('secret_enc', sa.Text(), nullable=True),
    sa.Column('preview', sa.String(length=80), nullable=False),
    sa.Column('previous_hash', sa.String(length=64), nullable=True),
    sa.Column('rotating_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('client_id', sa.String(length=64), nullable=True),
    sa.Column('lifetime_minutes', sa.Integer(), nullable=True),
    sa.Column('signing', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('signing_secret_enc', sa.Text(), nullable=True),
    sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
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
    sa.CheckConstraint("kind IN ('static', 'client', 'webhook')", name=op.f('ck_api_tokens_kind')),
    sa.CheckConstraint("mode IN ('live', 'test')", name=op.f('ck_api_tokens_mode')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_tokens')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_tokens_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_api_tokens_previous_hash', 'api_tokens', ['tenant_id', 'previous_hash'], unique=False, schema='formaly', postgresql_where=sa.text('previous_hash IS NOT NULL'))
    op.create_index('ix_api_tokens_secret_hash', 'api_tokens', ['tenant_id', 'secret_hash'], unique=False, schema='formaly')
    op.create_index('uq_api_tokens_client_id', 'api_tokens', ['tenant_id', 'client_id'], unique=True, schema='formaly', postgresql_where=sa.text('client_id IS NOT NULL'))
    op.create_table('api_endpoints',
    sa.Column('service_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('methods', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('page_size', sa.Integer(), server_default='50', nullable=False),
    sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('status', sa.String(length=10), server_default='disabled', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("status IN ('active', 'disabled')", name=op.f('ck_api_endpoints_status')),
    sa.CheckConstraint('page_size BETWEEN 1 AND 100', name=op.f('ck_api_endpoints_page_size')),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_api_endpoints_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'service_id'], ['formaly.api_services.tenant_id', 'formaly.api_services.id'], name=op.f('fk_api_endpoints_tenant_id_service_id_api_services'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_endpoints')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_api_endpoints_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_api_endpoints_form', 'api_endpoints', ['tenant_id', 'form_id'], unique=False, schema='formaly')
    op.create_index('ix_api_endpoints_service', 'api_endpoints', ['tenant_id', 'service_id'], unique=False, schema='formaly')
    op.create_index('uq_api_endpoints_name', 'api_endpoints', ['tenant_id', 'name'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for statement in enable_tenant_rls("api_settings"):
        op.execute(statement)
    for statement in enable_tenant_rls("api_services"):
        op.execute(statement)
    for statement in enable_tenant_rls("api_endpoints"):
        op.execute(statement)
    for statement in enable_tenant_rls("api_tokens"):
        op.execute(statement)
    for statement in enable_tenant_rls("api_access_rules"):
        op.execute(statement)

    # The address handles of every workspace, current and retired (a handle is never handed out twice)
    op.create_table(
        "api_keys_directory",
        sa.Column("api_key", sa.String(16), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT"),
        schema="platform",
    )
    op.create_index("ix_api_keys_directory_tenant", "api_keys_directory", ["tenant_id"], schema="platform")
    op.execute("GRANT SELECT ON platform.api_keys_directory TO platform_reader")
    op.execute(f"""
        CREATE FUNCTION platform.claim_api_key(p_key text) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        BEGIN
            IF {CURRENT_TENANT} IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            INSERT INTO platform.api_keys_directory (api_key, tenant_id) VALUES (p_key, {CURRENT_TENANT})
            ON CONFLICT DO NOTHING;
            RETURN FOUND;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.retire_api_key(p_key text, p_until timestamptz) RETURNS void
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            UPDATE platform.api_keys_directory SET retired_at = p_until
             WHERE api_key = p_key AND tenant_id = {CURRENT_TENANT}
        $$
    """)
    op.execute("""
        CREATE FUNCTION platform.resolve_api_key(p_key text)
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, subdomain text, status text, current boolean)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.primary_organisation_id, t.subdomain::text, t.status::text, d.retired_at IS NULL
              FROM platform.api_keys_directory d JOIN platform.tenants t ON t.id = d.tenant_id
             WHERE d.api_key = p_key AND (d.retired_at IS NULL OR d.retired_at > now()) AND t.deleted_at IS NULL
        $$
    """)
    for fn in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO formalie_app")


def downgrade() -> None:
    for fn in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    op.drop_table("api_keys_directory", schema="platform")
    for statement in disable_tenant_rls("api_access_rules"):
        op.execute(statement)
    op.drop_table("api_access_rules", schema="formaly")
    for statement in disable_tenant_rls("api_tokens"):
        op.execute(statement)
    op.drop_table("api_tokens", schema="formaly")
    for statement in disable_tenant_rls("api_endpoints"):
        op.execute(statement)
    op.drop_table("api_endpoints", schema="formaly")
    for statement in disable_tenant_rls("api_services"):
        op.execute(statement)
    op.drop_table("api_services", schema="formaly")
    for statement in disable_tenant_rls("api_settings"):
        op.execute(statement)
    op.drop_table("api_settings", schema="formaly")

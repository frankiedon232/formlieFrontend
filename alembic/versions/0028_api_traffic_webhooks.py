"""API traffic and webhooks (B10 step 2): the request log of the public API, webhooks and their deliveries.

  api_request_logs       one row per call to the public API (monthly partitions on `at`); every count of calls,
                         errors, answer times, rule hits and limited calls is read from it
  webhooks               addresses that get the workspace's response events, with the webhook token they send
  webhook_deliveries     one event sent to one webhook, with every try (monthly partitions on `at`)

Cross-workspace work runs through functions that only list ids (owned by formalie_directory, like
platform.deliveries_due in 0025), so the worker handles each row in its own workspace's context:

  platform.webhook_deliveries_due(n)     retries whose time has come, and first tries the worker never got (with the
                                         workspace's name and subdomain)
  platform.api_log_body_settings()       workspaces whose request log keeps bodies, and for how many days
  platform.ensure_monthly_partitions_back(table, n)
                                         the last n months' partitions (sample traffic of the development seed; the
                                         Beat task keeps the months ahead)

Revision ID: 0028
Revises: 0027
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

revision: str = '0028'
down_revision: str | None = '0027'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
DIRECTORY_FUNCTIONS = ("webhook_deliveries_due(integer)", "api_log_body_settings()")


def _tenant_columns() -> list[sa.Column]:
    return [sa.Column('tenant_id', sa.Uuid(), nullable=False), sa.Column('organisation_id', sa.Uuid(), nullable=False)]


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
    ]


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    # ── The request log of the public API ───────────────────────────────────────
    op.create_table('api_request_logs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('method', sa.String(length=10), nullable=False),
    sa.Column('path', sa.Text(), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('endpoint_id', sa.Uuid(), nullable=True),
    sa.Column('endpoint_name', sa.String(length=64), nullable=True),
    sa.Column('service_id', sa.Uuid(), nullable=True),
    sa.Column('service_name', sa.String(length=80), nullable=True),
    sa.Column('token_id', sa.Uuid(), nullable=True),
    sa.Column('token_name', sa.String(length=80), nullable=True),
    sa.Column('token_mode', sa.String(length=4), nullable=True),
    sa.Column('rule_id', sa.Uuid(), nullable=True),
    sa.Column('rate_limited', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=False),
    sa.Column('country', sa.String(length=2), nullable=True),
    sa.Column('origin', sa.String(length=300), nullable=True),
    sa.Column('user_agent', sa.String(length=200), server_default='', nullable=False),
    sa.Column('request_id', sa.String(length=100), nullable=False),
    sa.Column('request_headers', jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('request_body', jsonb, nullable=True),
    sa.Column('response_body', jsonb, nullable=True),
    *_tenant_columns(),
    sa.PrimaryKeyConstraint('tenant_id', 'id', 'at', name=op.f('pk_api_request_logs')),
    schema=S,
    postgresql_partition_by='RANGE (at)'
    )
    op.create_index('ix_api_request_logs_at', 'api_request_logs', ['tenant_id', 'at'], schema=S)
    op.create_index('ix_api_request_logs_endpoint', 'api_request_logs', ['tenant_id', 'endpoint_id', 'at'], schema=S)
    op.create_index('ix_api_request_logs_token', 'api_request_logs', ['tenant_id', 'token_id', 'at'], schema=S)
    op.create_index('ix_api_request_logs_rule', 'api_request_logs', ['tenant_id', 'rule_id', 'at'], schema=S,
                    postgresql_where=sa.text('rule_id IS NOT NULL'))
    op.create_index('ix_api_request_logs_id', 'api_request_logs', ['tenant_id', 'id'], schema=S)

    # ── Webhooks and their deliveries ──────────────────────────────────────────
    op.create_table('webhooks',
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('url', sa.String(length=2000), nullable=False),
    sa.Column('events', jsonb, nullable=False),
    sa.Column('form_ids', jsonb, server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('paused_reason', sa.String(length=8), nullable=True),
    sa.Column('token_id', sa.Uuid(), nullable=True),
    sa.Column('consecutive_failures', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    *_tenant_columns(),
    *_audit_columns(),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("paused_reason IN ('manual', 'failures')", name=op.f('ck_webhooks_paused_reason')),
    sa.ForeignKeyConstraint(['tenant_id', 'token_id'], [f'{S}.api_tokens.tenant_id', f'{S}.api_tokens.id'],
                            name=op.f('fk_webhooks_tenant_id_token_id_api_tokens'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_webhooks')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_webhooks_tenant_id_id')),
    schema=S
    )
    op.create_index('ix_webhooks_tenant', 'webhooks', ['tenant_id', 'created_at'], schema=S,
                    postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_table('webhook_deliveries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('webhook_id', sa.Uuid(), nullable=False),
    sa.Column('event', sa.String(length=30), nullable=False),
    sa.Column('test', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('form_id', sa.Uuid(), nullable=True),
    sa.Column('response_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('status_code', sa.SmallInteger(), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('claimed_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('body_enc', sa.Text(), nullable=True),
    sa.Column('logged_body', sa.Text(), nullable=False),
    sa.Column('request_headers', jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('response', jsonb, nullable=True),
    sa.Column('history', jsonb, server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    *_tenant_columns(),
    sa.CheckConstraint("status IN ('delivered', 'retrying', 'failed')", name=op.f('ck_webhook_deliveries_status')),
    sa.ForeignKeyConstraint(['tenant_id', 'webhook_id'], [f'{S}.webhooks.tenant_id', f'{S}.webhooks.id'],
                            name=op.f('fk_webhook_deliveries_tenant_id_webhook_id_webhooks'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('tenant_id', 'id', 'at', name=op.f('pk_webhook_deliveries')),
    schema=S,
    postgresql_partition_by='RANGE (at)'
    )
    op.create_index('ix_webhook_deliveries_list', 'webhook_deliveries', ['tenant_id', 'webhook_id', 'at'], schema=S)
    op.create_index('ix_webhook_deliveries_at', 'webhook_deliveries', ['tenant_id', 'at'], schema=S)
    op.create_index('ix_webhook_deliveries_id', 'webhook_deliveries', ['tenant_id', 'id'], schema=S)
    op.create_index('ix_webhook_deliveries_due', 'webhook_deliveries', ['next_retry_at'], schema=S,
                    postgresql_where=sa.text("status = 'retrying'"))

    for table in ("api_request_logs", "webhooks", "webhook_deliveries"):
        for statement in enable_tenant_rls(table):
            op.execute(statement)
    # platform_reader: never the bodies (answers may sit in them) nor the encrypted body of a delivery
    op.execute(f"REVOKE SELECT ON {S}.api_request_logs FROM platform_reader")
    op.execute(f"GRANT SELECT (id, at, method, path, status, code, duration_ms, endpoint_id, endpoint_name, service_id, "
               f"service_name, token_id, token_name, token_mode, rule_id, rate_limited, ip, country, origin, user_agent, "
               f"request_id, tenant_id, organisation_id) ON {S}.api_request_logs TO platform_reader")
    op.execute(f"REVOKE SELECT ON {S}.webhook_deliveries FROM platform_reader")
    op.execute(f"GRANT SELECT (id, at, webhook_id, event, test, form_id, response_id, status, attempts, status_code, "
               f"duration_ms, next_retry_at, history, updated_at, tenant_id, organisation_id) ON {S}.webhook_deliveries "
               f"TO platform_reader")

    # ── Partitions: the last months too (the development seed's sample traffic) ─────────
    op.execute("""
        CREATE FUNCTION platform.ensure_monthly_partitions_back(p_parent regclass, p_months_back integer)
        RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog
        AS $$
        DECLARE
            v_schema text;
            v_table text;
            v_kind "char";
            v_month date := date_trunc('month', now() AT TIME ZONE 'UTC')::date;
            v_name text;
            v_created integer := 0;
        BEGIN
            SELECT n.nspname, c.relname, c.relkind INTO v_schema, v_table, v_kind
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.oid = p_parent;
            IF v_kind IS DISTINCT FROM 'p' THEN
                RAISE EXCEPTION '% is not a partitioned table', p_parent;
            END IF;
            FOR i IN 1..least(greatest(p_months_back, 0), 12) LOOP
                v_name := v_table || '_p' || to_char(v_month - make_interval(months => i), 'YYYYMM');
                IF to_regclass(format('%I.%I', v_schema, v_name)) IS NULL THEN
                    EXECUTE format('CREATE TABLE %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L)',
                        v_schema, v_name, v_schema, v_table,
                        (v_month - make_interval(months => i))::timestamp AT TIME ZONE 'UTC',
                        (v_month - make_interval(months => i - 1))::timestamp AT TIME ZONE 'UTC');
                    EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', v_schema, v_name);
                    EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY', v_schema, v_name);
                    v_created := v_created + 1;
                END IF;
            END LOOP;
            RETURN v_created;
        END
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION platform.ensure_monthly_partitions_back(regclass, integer) FROM PUBLIC")
    for table in ("api_request_logs", "webhook_deliveries"):
        op.execute(f"SELECT platform.ensure_monthly_partitions('{S}.{table}'::regclass, 3)")
        op.execute(f"SELECT platform.ensure_monthly_partitions_back('{S}.{table}'::regclass, 3)")

    # ── The worker's lists across workspaces (ids only) ─────────────────────────
    op.execute(f"GRANT SELECT (id, at, tenant_id, organisation_id, status, next_retry_at, claimed_until, body_enc) ON {S}.webhook_deliveries "
               "TO formalie_directory")
    op.execute(f"GRANT SELECT (tenant_id, organisation_id, log_keep_bodies, log_days) ON {S}.api_settings "
               "TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION platform.webhook_deliveries_due(max_rows integer)
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, subdomain text, name text, delivery_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT d.tenant_id, d.organisation_id, t.subdomain::text, t.name::text, d.id FROM {S}.webhook_deliveries d
              JOIN platform.tenants t ON t.id = d.tenant_id
             WHERE d.status = 'retrying' AND d.body_enc IS NOT NULL
               AND (d.claimed_until IS NULL OR d.claimed_until < now())
               AND (d.next_retry_at <= now() OR (d.next_retry_at IS NULL AND d.at < now() - interval '2 minutes'))
             ORDER BY coalesce(d.next_retry_at, d.at) LIMIT max_rows
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.api_log_body_settings()
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, log_days integer)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT s.tenant_id, s.organisation_id, s.log_days FROM {S}.api_settings s
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    for name in DIRECTORY_FUNCTIONS:
        op.execute(f"ALTER FUNCTION platform.{name} OWNER TO formalie_directory")
        op.execute(f"REVOKE ALL ON FUNCTION platform.{name} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION platform.{name} TO formalie_app")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")


def downgrade() -> None:
    for name in DIRECTORY_FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS platform.{name}")
    op.execute("DROP FUNCTION IF EXISTS platform.ensure_monthly_partitions_back(regclass, integer)")
    op.execute(f"REVOKE SELECT (tenant_id, organisation_id, log_keep_bodies, log_days) ON {S}.api_settings "
               "FROM formalie_directory")
    for table in ("webhook_deliveries", "webhooks", "api_request_logs"):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema=S)  # drops the partitions with it

"""B0 foundation: schemas, grants, tenant directory, organisations, event outbox, partition upkeep.

Revision ID: 0001
Revises:
Created: 2026-10-10

The roles themselves are made once per cluster by scripts/db_bootstrap.py (they carry passwords, which never go
in a migration): formalie_owner, formalie_app (NOBYPASSRLS), formalie_worker (BYPASSRLS, outbox only),
formalie_readonly, platform_reader (BYPASSRLS, replica), platform_writer.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import TENANT_MATCH, disable_tenant_rls, enable_tenant_rls

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUNTIME_ROLES = "formalie_app, formalie_worker, formalie_readonly, platform_reader, platform_writer"


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
    ]


def upgrade() -> None:
    # ── Schemas and baseline privileges ────────────────────────────────────────
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")
    op.execute(f"GRANT USAGE ON SCHEMA public, platform TO {RUNTIME_ROLES}")

    # ── Tenant directory (platform schema, no RLS, never readable by formalie_app) ──
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subdomain", sa.String(63), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("suspended_reason", sa.Text()),
        sa.Column("close_at", sa.DateTime(timezone=True)),
        sa.Column("primary_organisation_id", sa.Uuid()),
        sa.Column("data_region", sa.String(20), server_default="default", nullable=False),
        sa.Column("plan_id", sa.String(40), server_default="starter", nullable=False),
        sa.Column("setup_completed_at", sa.DateTime(timezone=True)),
        *_audit_columns(),
        sa.CheckConstraint("status IN ('active', 'suspended', 'read_only', 'closing')", name="status"),
        sa.CheckConstraint("subdomain = lower(subdomain)", name="subdomain_lower"),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        schema="platform",
    )
    op.create_index("uq_tenants_subdomain_active", "tenants", ["subdomain"], unique=True, schema="platform",
                    postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "tenant_subdomain_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("subdomain", sa.String(63), nullable=False),
        sa.Column("until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT",
                                name="fk_tenant_subdomain_history_tenant_id_tenants"),
        sa.PrimaryKeyConstraint("id", name="pk_tenant_subdomain_history"),
        schema="platform",
    )
    op.create_index("ix_tenant_subdomain_history_subdomain", "tenant_subdomain_history", ["subdomain"], schema="platform")
    op.execute("GRANT SELECT ON platform.tenants, platform.tenant_subdomain_history TO platform_reader")

    # Host → workspace before any tenant context exists. Public fields only; a current subdomain wins over an old one.
    op.execute("""
        CREATE FUNCTION platform.resolve_tenant(p_subdomain text)
        RETURNS TABLE (id uuid, subdomain text, name text, status text, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, platform
        AS $$
            SELECT r.id, r.subdomain, r.name, r.status, r.organisation_id FROM (
                SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id AS organisation_id, 0 AS rank
                  FROM platform.tenants t
                 WHERE t.subdomain = lower(p_subdomain) AND t.deleted_at IS NULL
                UNION ALL
                SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id, 1
                  FROM platform.tenant_subdomain_history h
                  JOIN platform.tenants t ON t.id = h.tenant_id
                 WHERE h.subdomain = lower(p_subdomain) AND h.until > now() AND t.deleted_at IS NULL
            ) r
            WHERE r.organisation_id IS NOT NULL
            ORDER BY r.rank
            LIMIT 1
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION platform.resolve_tenant(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.resolve_tenant(text) TO formalie_app, formalie_readonly")

    # ── Organisations (first tenant table) ─────────────────────────────────────
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("legal_name", sa.String(300)),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_organisations"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_organisations_tenant_id_id"),
        sa.CheckConstraint("organisation_id = id", name="self_organisation"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT",
                                name="fk_organisations_tenant_id_tenants"),
    )
    op.create_index("ix_organisations_tenant_org", "organisations", ["tenant_id", "organisation_id"],
                    postgresql_where=sa.text("deleted_at IS NULL"))
    for statement in enable_tenant_rls("organisations"):
        op.execute(statement)

    # ── Event outbox (monthly partitions; the app may only add events) ─────────
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid()),
        sa.Column("organisation_id", sa.Uuid()),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("routing_key", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.PrimaryKeyConstraint("id", "created_at", name="pk_event_outbox"),
        postgresql_partition_by="RANGE (created_at)",
    )
    op.create_index("ix_event_outbox_unpublished", "event_outbox", ["created_at"],
                    postgresql_where=sa.text("published_at IS NULL"))
    op.execute("ALTER TABLE public.event_outbox ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.event_outbox FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY event_outbox_isolation ON public.event_outbox
        USING ({TENANT_MATCH})
        WITH CHECK (({TENANT_MATCH}) OR (tenant_id IS NULL AND organisation_id IS NULL))
    """)
    op.execute("GRANT INSERT ON public.event_outbox TO formalie_app")
    op.execute("GRANT SELECT, UPDATE ON public.event_outbox TO formalie_worker")
    op.execute("GRANT SELECT ON public.event_outbox TO platform_reader")

    op.create_table(
        "processed_events",
        sa.Column("consumer", sa.String(100), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("consumer", "event_id", name="pk_processed_events"),
    )
    op.execute("GRANT SELECT, INSERT ON public.processed_events TO formalie_app, formalie_worker")

    # ── Monthly partitions: next N months, each with RLS forced like its parent ──
    op.execute("""
        CREATE FUNCTION platform.ensure_monthly_partitions(p_parent regclass, p_months_ahead integer)
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
            FOR i IN 0..greatest(p_months_ahead, 0) LOOP
                v_name := v_table || '_p' || to_char(v_month + make_interval(months => i), 'YYYYMM');
                IF to_regclass(format('%I.%I', v_schema, v_name)) IS NULL THEN
                    EXECUTE format('CREATE TABLE %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L)',
                        v_schema, v_name, v_schema, v_table,
                        (v_month + make_interval(months => i))::timestamp AT TIME ZONE 'UTC',
                        (v_month + make_interval(months => i + 1))::timestamp AT TIME ZONE 'UTC');
                    EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', v_schema, v_name);
                    EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY', v_schema, v_name);
                    v_created := v_created + 1;
                END IF;
            END LOOP;
            RETURN v_created;
        END
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION platform.ensure_monthly_partitions(regclass, integer) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.ensure_monthly_partitions(regclass, integer) TO formalie_worker")
    op.execute("SELECT platform.ensure_monthly_partitions('public.event_outbox'::regclass, 3)")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.ensure_monthly_partitions(regclass, integer)")
    op.drop_table("processed_events")
    op.drop_table("event_outbox")  # drops its partitions with it
    for statement in disable_tenant_rls("organisations"):
        op.execute(statement)
    op.drop_table("organisations")
    op.execute("DROP FUNCTION IF EXISTS platform.resolve_tenant(text)")
    op.drop_table("tenant_subdomain_history", schema="platform")
    op.drop_table("tenants", schema="platform")
    op.execute("DROP SCHEMA IF EXISTS platform")

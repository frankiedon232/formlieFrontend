"""B11, Settings the rest: the sent log, sending addresses, single sign-on, own web domains, and the tenant directory
functions the address, region and retention screens need.

Tenant tables (RLS forced): `sent_emails`, `email_sending`, `sso_connections`, `custom_domains`.
Tenant directory (platform, reached only through these functions):
  platform.custom_domains_directory           a verified own domain → its workspace (one holder at a time)
  platform.tenant_profile()                   the current workspace's subdomain, name, plan and data region
  platform.subdomain_history_of()             its old subdomains that still lead to it, and until when
  platform.change_subdomain(new, id)          a new subdomain; the old one keeps answering for 90 days (5 at most)
  platform.claim_domain(domain)               this workspace answers on a domain it verified
  platform.release_domain(domain)             it stops answering on it
  platform.resolve_domain(domain)             host → workspace (like resolve_tenant), before any tenant context
  platform.retention_workspaces()             every live workspace (response retention, once a day)

Revision ID: 0031
Revises: 0030
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

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
CURRENT_TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"
TABLES = ("sent_emails", "email_sending", "sso_connections", "custom_domains")
FUNCTIONS = ("platform.tenant_profile()", "platform.subdomain_history_of()", "platform.change_subdomain(text, uuid)",
             "platform.claim_domain(text)", "platform.release_domain(text)", "platform.resolve_domain(text)",
             "platform.retention_workspaces()")


def _common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
    ]


def _keys(table: str) -> list[sa.Constraint]:
    return [sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
            sa.UniqueConstraint("tenant_id", "id", name=f"uq_{table}_tenant_id_id")]


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "sent_emails",
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("to_email", sa.String(254), nullable=False),
        sa.Column("subject", sa.String(400), nullable=False),
        sa.Column("template", sa.String(32), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("html", sa.Text(), server_default="", nullable=False),
        sa.Column("text", sa.Text(), server_default="", nullable=False),
        *_common(), *_keys("sent_emails"),
        sa.CheckConstraint("to_email = lower(to_email)", name="ck_sent_emails_to_email_lower"),
        schema=S,
    )
    op.create_index("ix_sent_emails_list", "sent_emails", ["tenant_id", "sent_at"], schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "email_sending",
        sa.Column("mode", sa.String(10), server_default="formalie", nullable=False),
        sa.Column("domain", jsonb, nullable=True),
        sa.Column("smtp", jsonb, nullable=True),
        sa.Column("smtp_password_enc", sa.Text(), nullable=True),
        *_common(), *_keys("email_sending"),
        sa.CheckConstraint("mode IN ('formalie', 'domain', 'smtp')", name="ck_email_sending_mode"),
        schema=S,
    )
    op.create_index("uq_email_sending_tenant", "email_sending", ["tenant_id"], unique=True, schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "sso_connections",
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("protocol", sa.String(4), nullable=False),
        sa.Column("label", sa.String(40), nullable=False),
        sa.Column("saml", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("oidc", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("client_secret_enc", sa.Text(), nullable=True),
        sa.Column("idp", jsonb, nullable=True),
        sa.Column("domains", jsonb, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("enforce", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("auto_create", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("default_role", sa.String(100), nullable=False),
        sa.Column("status", sa.String(6), server_default="draft", nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("problem", sa.String(20), nullable=True),
        *_common(), *_keys("sso_connections"),
        sa.CheckConstraint("protocol IN ('saml', 'oidc')", name="ck_sso_connections_protocol"),
        sa.CheckConstraint("status IN ('draft', 'tested', 'active')", name="ck_sso_connections_status"),
        schema=S,
    )
    op.create_index("uq_sso_connections_tenant", "sso_connections", ["tenant_id"], unique=True, schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "custom_domains",
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("status", sa.String(8), server_default="pending", nullable=False),
        sa.Column("records", jsonb, nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("problem", sa.String(12), nullable=True),
        *_common(), *_keys("custom_domains"),
        sa.CheckConstraint("status IN ('pending', 'verified', 'failed')", name="ck_custom_domains_status"),
        sa.CheckConstraint("domain = lower(domain)", name="ck_custom_domains_domain_lower"),
        schema=S,
    )
    op.create_index("uq_custom_domains_tenant", "custom_domains", ["tenant_id"], unique=True, schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL"))

    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)
    # Erasing a person's data (privacy requests, retention) clears the answers kept in a response's edit history;
    # the rest of the history stays append-only
    op.execute(f"GRANT UPDATE (before, after) ON {S}.response_changes TO formalie_app")

    # ── Tenant directory ─────────────────────────────────────────────────────────────
    op.create_table(
        "custom_domains_directory",
        sa.Column("domain", sa.String(253), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT",
                                name="fk_custom_domains_directory_tenant_id_tenants"),
        sa.CheckConstraint("domain = lower(domain)", name="ck_custom_domains_directory_domain_lower"),
        schema="platform",
    )
    op.create_index("ix_custom_domains_directory_tenant", "custom_domains_directory", ["tenant_id"], schema="platform")
    op.execute("GRANT SELECT ON platform.custom_domains_directory TO platform_reader")

    op.execute(f"""
        CREATE FUNCTION platform.tenant_profile()
        RETURNS TABLE (subdomain text, name text, plan_id text, data_region text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.subdomain::text, t.name::text, t.plan_id::text, t.data_region::text
              FROM platform.tenants t WHERE t.id = {CURRENT_TENANT} AND t.deleted_at IS NULL
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.subdomain_history_of() RETURNS TABLE (subdomain text, until timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT h.subdomain::text, h.until FROM platform.tenant_subdomain_history h
             WHERE h.tenant_id = {CURRENT_TENANT} AND h.until > now() ORDER BY h.until DESC
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.change_subdomain(p_new text, p_id uuid) RETURNS text
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        DECLARE
            v_tenant uuid := {CURRENT_TENANT};
            v_old text;
            v_new text := lower(p_new);
        BEGIN
            IF v_tenant IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            SELECT t.subdomain INTO v_old FROM platform.tenants t
             WHERE t.id = v_tenant AND t.deleted_at IS NULL FOR UPDATE;
            IF v_old IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            IF v_old = v_new THEN RETURN v_old; END IF;
            -- In use by any workspace now, or as another workspace's old address: taken (its own old one may come back)
            IF EXISTS (SELECT 1 FROM platform.tenants WHERE subdomain = v_new AND deleted_at IS NULL)
               OR EXISTS (SELECT 1 FROM platform.tenant_subdomain_history
                           WHERE subdomain = v_new AND until > now() AND tenant_id <> v_tenant) THEN
                RAISE EXCEPTION 'subdomain taken' USING ERRCODE = 'unique_violation';
            END IF;
            UPDATE platform.tenant_subdomain_history SET until = now()
             WHERE tenant_id = v_tenant AND subdomain = v_new AND until > now();
            INSERT INTO platform.tenant_subdomain_history (id, tenant_id, subdomain, until)
            VALUES (p_id, v_tenant, v_old, now() + interval '90 days');
            -- The five most recent old addresses keep answering
            UPDATE platform.tenant_subdomain_history SET until = now()
             WHERE tenant_id = v_tenant AND until > now() AND id NOT IN (
                   SELECT id FROM platform.tenant_subdomain_history
                    WHERE tenant_id = v_tenant AND until > now() ORDER BY until DESC LIMIT 5);
            UPDATE platform.tenants SET subdomain = v_new, updated_at = now() WHERE id = v_tenant;
            RETURN v_old;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.claim_domain(p_domain text) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        BEGIN
            IF {CURRENT_TENANT} IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            INSERT INTO platform.custom_domains_directory (domain, tenant_id) VALUES (lower(p_domain), {CURRENT_TENANT})
            ON CONFLICT (domain) DO UPDATE
               SET tenant_id = EXCLUDED.tenant_id, verified_at = now(), released_at = NULL;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.release_domain(p_domain text) RETURNS void
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            UPDATE platform.custom_domains_directory SET released_at = now()
             WHERE domain = lower(p_domain) AND tenant_id = {CURRENT_TENANT} AND released_at IS NULL
        $$
    """)
    op.execute("""
        CREATE FUNCTION platform.resolve_domain(p_domain text)
        RETURNS TABLE (id uuid, subdomain text, name text, status text, organisation_id uuid, plan_id text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id, t.plan_id::text
              FROM platform.custom_domains_directory d JOIN platform.tenants t ON t.id = d.tenant_id
             WHERE d.domain = lower(p_domain) AND d.released_at IS NULL AND t.deleted_at IS NULL
               AND t.primary_organisation_id IS NOT NULL
        $$
    """)
    op.execute("""
        CREATE FUNCTION platform.retention_workspaces() RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.primary_organisation_id FROM platform.tenants t
             WHERE t.deleted_at IS NULL AND t.primary_organisation_id IS NOT NULL
        $$
    """)
    for fn in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO formalie_app")
    op.execute("GRANT EXECUTE ON FUNCTION platform.tenant_profile(), platform.resolve_domain(text), "
               "platform.retention_workspaces() TO formalie_worker, formalie_readonly")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (before, after) ON {S}.response_changes FROM formalie_app")
    for fn in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    op.drop_table("custom_domains_directory", schema="platform")
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema=S)

"""Platform admin bridge (B16, PLATFORM-ADMIN-INTEGRATION §1 to §5).

Global tables (schema `platform`; formalie_app reads, platform_writer inserts and updates, nobody deletes):
  platform_settings · reserved_subdomains · feature_flags · announcements · announcement_translations
  plans · plan_prices · plan_limits · plan_features
  system_option_lists · system_option_items · system_folders · system_email_templates
  system_templates · system_template_translations · system_themes · system_page_designs
  Each carries published_at / published_by_staff_id; a trigger (platform.stamp_published) refuses a write by
  platform_writer without the staff id and stamps published_at. Seeded from what Formalie ships today
  (app/modules/platform_bridge/seed.py), so nothing changes for workspaces.

Tenant tables (RLS forced): support_access_grants · support_access_requests · support_sessions.

platform.admin_calls: every internal admin API call and its idempotency key (formalie_app writes it).

platform.tenants gains trial_ends_at and plan_limits (limits set by the platform, enforced with B15).

Functions (SECURITY DEFINER):
  platform.admin_tenant(uuid)                         one workspace by id (formalie_owner)
  platform.admin_set_status(text, text, timestamptz)  the workspace in context: status, reason, closing date
  platform.admin_set_plan(text, jsonb, timestamptz, boolean, boolean)   plan, limits, trial end
  platform.communication_workspaces(text[], uuid[])   workspaces a message from Formalie goes to
  platform.user_workspace(uuid) · platform.support_grant_workspace(uuid)   where a person / a grant lives
  platform.support_due()                              workspaces with support access to expire
  platform.outbox_backlog()                           events waiting to be published (health)
  (the last four belong to formalie_directory and read only the columns they need)

platform_reader: column privileges on every table of both schemas, without secrets (`*_hash`, `*_enc`) and answer
content (app/modules/platform_bridge/grants.py); `enable_tenant_rls` applies the same rule to later tables.

Revision ID: 0034
Revises: 0033
Created: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls
from app.modules.platform_bridge.grants import B16_GLOBAL_TABLES, reader_sql

revision: str = '0034'
down_revision: str | None = '0033'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
P = "platform"
CURRENT_TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"
SUPPORT_TABLES = ("support_access_grants", "support_access_requests", "support_sessions")
OWNER_FUNCTIONS = ("platform.admin_tenant(uuid)", "platform.admin_set_status(text, text, timestamptz)",
                   "platform.admin_set_plan(text, jsonb, timestamptz, boolean, boolean)",
                   "platform.communication_workspaces(text[], uuid[])")
DIRECTORY_FUNCTIONS = ("platform.user_workspace(uuid)", "platform.support_grant_workspace(uuid)",
                       "platform.support_due()", "platform.outbox_backlog()")

DDL = [
    # platform.platform_settings
    """CREATE TABLE platform.platform_settings (
    key VARCHAR(60) NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_platform_settings PRIMARY KEY (key)
)""",
    # platform.reserved_subdomains
    """CREATE TABLE platform.reserved_subdomains (
    subdomain VARCHAR(63) NOT NULL,
    reason VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_reserved_subdomains PRIMARY KEY (subdomain),
    CONSTRAINT ck_reserved_subdomains_subdomain_lower CHECK (subdomain = lower(subdomain))
)""",
    # platform.feature_flags
    """CREATE TABLE platform.feature_flags (
    key VARCHAR(80) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT 'false' NOT NULL,
    plans TEXT[] DEFAULT '{}' NOT NULL,
    tenant_ids UUID[] DEFAULT '{}' NOT NULL,
    rollout_percent INTEGER DEFAULT '100' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_feature_flags PRIMARY KEY (key),
    CONSTRAINT ck_feature_flags_rollout_percent CHECK (rollout_percent BETWEEN 0 AND 100)
)""",
    # platform.announcements
    """CREATE TABLE platform.announcements (
    id UUID NOT NULL,
    kind VARCHAR(12) DEFAULT 'banner' NOT NULL,
    tone VARCHAR(10) DEFAULT 'info' NOT NULL,
    audience VARCHAR(10) DEFAULT 'all' NOT NULL,
    plans TEXT[] DEFAULT '{}' NOT NULL,
    tenant_ids UUID[] DEFAULT '{}' NOT NULL,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ends_at TIMESTAMP WITH TIME ZONE,
    link_url TEXT,
    dismissible BOOLEAN DEFAULT 'true' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_announcements PRIMARY KEY (id),
    CONSTRAINT ck_announcements_kind CHECK (kind IN ('banner', 'maintenance', 'news')),
    CONSTRAINT ck_announcements_tone CHECK (tone IN ('info', 'warning', 'critical')),
    CONSTRAINT ck_announcements_audience CHECK (audience IN ('all', 'plans', 'tenants'))
)""",
    # platform.announcement_translations
    """CREATE TABLE platform.announcement_translations (
    announcement_id UUID NOT NULL,
    language VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    CONSTRAINT pk_announcement_translations PRIMARY KEY (announcement_id, language),
    CONSTRAINT fk_announcement_translations_announcement_id_announcements FOREIGN KEY(announcement_id) REFERENCES platform.announcements (id) ON DELETE RESTRICT
)""",
    # platform.plans
    """CREATE TABLE platform.plans (
    id VARCHAR(40) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    recommended BOOLEAN DEFAULT 'false' NOT NULL,
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_plans PRIMARY KEY (id)
)""",
    # platform.plan_prices
    """CREATE TABLE platform.plan_prices (
    plan_id VARCHAR(40) NOT NULL,
    period VARCHAR(12) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    CONSTRAINT pk_plan_prices PRIMARY KEY (plan_id, period),
    CONSTRAINT fk_plan_prices_plan_id_plans FOREIGN KEY(plan_id) REFERENCES platform.plans (id) ON DELETE RESTRICT,
    CONSTRAINT ck_plan_prices_period CHECK (period IN ('monthly', 'quarterly', 'annually'))
)""",
    # platform.plan_limits
    """CREATE TABLE platform.plan_limits (
    plan_id VARCHAR(40) NOT NULL,
    forms INTEGER,
    responses_per_form INTEGER,
    databases TEXT[] DEFAULT '{}' NOT NULL,
    sso BOOLEAN DEFAULT 'false' NOT NULL,
    custom_domains INTEGER,
    custom_email BOOLEAN DEFAULT 'false' NOT NULL,
    data_residency BOOLEAN DEFAULT 'false' NOT NULL,
    ai_credits INTEGER,
    languages INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    CONSTRAINT pk_plan_limits PRIMARY KEY (plan_id),
    CONSTRAINT fk_plan_limits_plan_id_plans FOREIGN KEY(plan_id) REFERENCES platform.plans (id) ON DELETE RESTRICT
)""",
    # platform.plan_features
    """CREATE TABLE platform.plan_features (
    plan_id VARCHAR(40) NOT NULL,
    feature VARCHAR(40) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_plan_features PRIMARY KEY (plan_id, feature),
    CONSTRAINT fk_plan_features_plan_id_plans FOREIGN KEY(plan_id) REFERENCES platform.plans (id) ON DELETE RESTRICT
)""",
    # platform.system_option_lists
    """CREATE TABLE platform.system_option_lists (
    key VARCHAR(60) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    levels JSONB,
    columns JSONB,
    large BOOLEAN DEFAULT 'false' NOT NULL,
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_option_lists PRIMARY KEY (key)
)""",
    # platform.system_option_items
    """CREATE TABLE platform.system_option_items (
    list_key VARCHAR(60) NOT NULL,
    value VARCHAR(200) NOT NULL,
    label TEXT NOT NULL,
    level INTEGER DEFAULT '0' NOT NULL,
    parent_value VARCHAR(200),
    translations JSONB DEFAULT '{}'::jsonb NOT NULL,
    attrs JSONB DEFAULT '{}'::jsonb NOT NULL,
    sort_order INTEGER DEFAULT '0' NOT NULL,
    active BOOLEAN DEFAULT 'true' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    CONSTRAINT pk_system_option_items PRIMARY KEY (list_key, value),
    CONSTRAINT fk_system_option_items_list_key_system_option_lists FOREIGN KEY(list_key) REFERENCES platform.system_option_lists (key) ON DELETE RESTRICT
)""",
    # platform.system_folders
    """CREATE TABLE platform.system_folders (
    key VARCHAR(40) NOT NULL,
    name_key VARCHAR(80) NOT NULL,
    color VARCHAR(20),
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_folders PRIMARY KEY (key)
)""",
    # platform.system_email_templates
    """CREATE TABLE platform.system_email_templates (
    key VARCHAR(40) NOT NULL,
    language VARCHAR(10) NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_email_templates PRIMARY KEY (key, language)
)""",
    # platform.system_templates
    """CREATE TABLE platform.system_templates (
    key VARCHAR(80) NOT NULL,
    category VARCHAR(40) NOT NULL,
    icon VARCHAR(80),
    tags TEXT[] DEFAULT '{}' NOT NULL,
    minutes INTEGER DEFAULT '0' NOT NULL,
    design JSONB DEFAULT '{}'::jsonb NOT NULL,
    schema JSONB NOT NULL,
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_templates PRIMARY KEY (key)
)""",
    # platform.system_template_translations
    """CREATE TABLE platform.system_template_translations (
    template_key VARCHAR(80) NOT NULL,
    language VARCHAR(10) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    content JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    CONSTRAINT pk_system_template_translations PRIMARY KEY (template_key, language),
    CONSTRAINT fk_system_template_translations_template_key_system_templates FOREIGN KEY(template_key) REFERENCES platform.system_templates (key) ON DELETE RESTRICT
)""",
    # platform.system_themes
    """CREATE TABLE platform.system_themes (
    key VARCHAR(60) NOT NULL,
    name_key VARCHAR(80),
    tokens JSONB NOT NULL,
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_themes PRIMARY KEY (key)
)""",
    # platform.system_page_designs
    """CREATE TABLE platform.system_page_designs (
    key VARCHAR(60) NOT NULL,
    name_key VARCHAR(80),
    tokens JSONB NOT NULL,
    sort INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    published_by_staff_id UUID,
    retired_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_system_page_designs PRIMARY KEY (key)
)""",
    # formaly.support_access_grants
    """CREATE TABLE formaly.support_access_grants (
    mode VARCHAR(5) DEFAULT 'read' NOT NULL,
    hours INTEGER NOT NULL,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    granted_by_name VARCHAR(200),
    request_id UUID,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by UUID,
    revoked_reason VARCHAR(20),
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    organisation_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_support_access_grants PRIMARY KEY (id),
    CONSTRAINT ck_support_access_grants_mode CHECK (mode IN ('read', 'write')),
    CONSTRAINT uq_support_access_grants_tenant_id_id UNIQUE (tenant_id, id)
)""",
    """CREATE INDEX ix_support_access_grants_open ON formaly.support_access_grants (tenant_id, expires_at) WHERE revoked_at IS NULL""",
    # formaly.support_access_requests
    """CREATE TABLE formaly.support_access_requests (
    staff_id VARCHAR(64) NOT NULL,
    staff_name VARCHAR(200) NOT NULL,
    reason TEXT NOT NULL,
    mode VARCHAR(5) DEFAULT 'read' NOT NULL,
    hours INTEGER NOT NULL,
    status VARCHAR(10) DEFAULT 'pending' NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    approval_id VARCHAR(64),
    decided_at TIMESTAMP WITH TIME ZONE,
    decided_by UUID,
    decided_by_name VARCHAR(200),
    grant_id UUID,
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    organisation_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_support_access_requests PRIMARY KEY (id),
    CONSTRAINT ck_support_access_requests_mode CHECK (mode IN ('read', 'write')),
    CONSTRAINT ck_support_access_requests_status CHECK (status IN ('pending', 'approved', 'declined', 'expired')),
    CONSTRAINT uq_support_access_requests_tenant_id_id UNIQUE (tenant_id, id)
)""",
    """CREATE INDEX ix_support_access_requests_pending ON formaly.support_access_requests (tenant_id, expires_at) WHERE status = 'pending'""",
    # formaly.support_sessions
    """CREATE TABLE formaly.support_sessions (
    grant_id UUID NOT NULL,
    staff_id VARCHAR(64) NOT NULL,
    staff_name VARCHAR(200) NOT NULL,
    approval_id VARCHAR(64),
    mode VARCHAR(5) DEFAULT 'read' NOT NULL,
    ticket_hash VARCHAR(64),
    ticket_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    redeemed_at TIMESTAMP WITH TIME ZONE,
    ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    ended_reason VARCHAR(20),
    last_seen_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    organisation_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    CONSTRAINT pk_support_sessions PRIMARY KEY (id),
    CONSTRAINT ck_support_sessions_mode CHECK (mode IN ('read', 'write')),
    CONSTRAINT uq_support_sessions_tenant_id_id UNIQUE (tenant_id, id)
)""",
    """CREATE INDEX ix_support_sessions_open ON formaly.support_sessions (tenant_id, ends_at) WHERE ended_at IS NULL""",
    """CREATE UNIQUE INDEX uq_support_sessions_ticket ON formaly.support_sessions (ticket_hash) WHERE ticket_hash IS NOT NULL""",
    # platform.admin_calls
    """CREATE TABLE platform.admin_calls (
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    key_id VARCHAR(40) NOT NULL,
    idempotency_key VARCHAR(200),
    request_hash VARCHAR(64) NOT NULL,
    method VARCHAR(8) NOT NULL,
    path VARCHAR(300) NOT NULL,
    tenant_id UUID,
    staff_id VARCHAR(64),
    staff_name VARCHAR(200),
    approval_id VARCHAR(64),
    reason TEXT,
    status_code INTEGER,
    error_code VARCHAR(20),
    response_enc TEXT,
    id UUID NOT NULL,
    CONSTRAINT pk_admin_calls PRIMARY KEY (id)
)""",
    """CREATE INDEX ix_admin_calls_tenant ON platform.admin_calls (tenant_id, created_at)""",
    """CREATE UNIQUE INDEX uq_admin_calls_idempotency_key ON platform.admin_calls (idempotency_key) WHERE idempotency_key IS NOT NULL""",
]


def _functions() -> None:
    op.execute(f"""
        CREATE FUNCTION {P}.stamp_published() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN NEW.updated_at := now(); END IF;
            IF current_user = 'platform_writer' THEN
                IF NEW.published_by_staff_id IS NULL THEN
                    RAISE EXCEPTION 'published_by_staff_id is required' USING ERRCODE = 'not_null_violation';
                END IF;
                NEW.published_at := now();
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.admin_tenant(p_id uuid)
        RETURNS TABLE (id uuid, subdomain text, name text, status text, organisation_id uuid, plan_id text,
                       suspended_reason text, close_at timestamptz, trial_ends_at timestamptz, plan_limits jsonb,
                       data_region text, setup_completed_at timestamptz, created_at timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id, t.plan_id::text,
                   t.suspended_reason, t.close_at, t.trial_ends_at, t.plan_limits, t.data_region::text,
                   t.setup_completed_at, t.created_at
              FROM platform.tenants t
             WHERE t.id = p_id AND t.deleted_at IS NULL AND t.primary_organisation_id IS NOT NULL
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.admin_set_status(p_status text, p_reason text, p_close_at timestamptz) RETURNS text
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        DECLARE v_old text;
        BEGIN
            SELECT t.status INTO v_old FROM platform.tenants t
             WHERE t.id = {CURRENT_TENANT} AND t.deleted_at IS NULL FOR UPDATE;
            IF v_old IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            UPDATE platform.tenants
               SET status = p_status,
                   suspended_reason = CASE WHEN p_status = 'active' THEN NULL ELSE p_reason END,
                   close_at = CASE WHEN p_status = 'closing' THEN p_close_at ELSE NULL END,
                   updated_at = now()
             WHERE id = {CURRENT_TENANT};
            RETURN v_old;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.admin_set_plan(p_plan text, p_limits jsonb, p_trial_ends_at timestamptz,
                                           p_set_limits boolean, p_set_trial boolean) RETURNS jsonb
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        DECLARE v_old jsonb;
        BEGIN
            SELECT jsonb_build_object('plan_id', t.plan_id, 'plan_limits', t.plan_limits,
                                      'trial_ends_at', t.trial_ends_at) INTO v_old
              FROM platform.tenants t WHERE t.id = {CURRENT_TENANT} AND t.deleted_at IS NULL FOR UPDATE;
            IF v_old IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            UPDATE platform.tenants
               SET plan_id = coalesce(p_plan, plan_id),
                   plan_limits = CASE WHEN p_set_limits THEN p_limits ELSE plan_limits END,
                   trial_ends_at = CASE WHEN p_set_trial THEN p_trial_ends_at ELSE trial_ends_at END,
                   updated_at = now()
             WHERE id = {CURRENT_TENANT};
            RETURN v_old;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.communication_workspaces(p_plans text[], p_tenants uuid[])
        RETURNS TABLE (id uuid, organisation_id uuid, subdomain text, name text, plan_id text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.primary_organisation_id, t.subdomain::text, t.name::text, t.plan_id::text
              FROM platform.tenants t
             WHERE t.deleted_at IS NULL AND t.primary_organisation_id IS NOT NULL
               AND (cardinality(p_tenants) = 0 OR t.id = ANY(p_tenants))
               AND (cardinality(p_plans) = 0 OR t.plan_id = ANY(p_plans))
             ORDER BY t.created_at
        $$
    """)
    # ── formalie_directory's lookups: only the columns they need ──
    op.execute(f"GRANT SELECT (id, organisation_id) ON {S}.users TO formalie_directory")
    op.execute(f"GRANT SELECT (id, tenant_id, organisation_id, expires_at, revoked_at, deleted_at) "
               f"ON {S}.support_access_grants TO formalie_directory")
    op.execute(f"GRANT SELECT (tenant_id, organisation_id, ends_at, ended_at, redeemed_at, ticket_expires_at, "
               f"deleted_at) ON {S}.support_sessions TO formalie_directory")
    op.execute(f"GRANT SELECT (tenant_id, organisation_id, status, expires_at, deleted_at) "
               f"ON {S}.support_access_requests TO formalie_directory")
    op.execute(f"GRANT SELECT (created_at, published_at, attempts) ON {S}.event_outbox TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION {P}.user_workspace(p_user uuid) RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$ SELECT u.tenant_id, u.organisation_id FROM {S}.users u WHERE u.id = p_user AND u.deleted_at IS NULL $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.support_grant_workspace(p_grant uuid) RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$ SELECT g.tenant_id, g.organisation_id FROM {S}.support_access_grants g
               WHERE g.id = p_grant AND g.deleted_at IS NULL $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.support_due() RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT g.tenant_id, g.organisation_id FROM {S}.support_access_grants g
             WHERE g.revoked_at IS NULL AND g.deleted_at IS NULL AND g.expires_at <= now()
            UNION
            SELECT s.tenant_id, s.organisation_id FROM {S}.support_sessions s
             WHERE s.ended_at IS NULL AND s.deleted_at IS NULL
               AND (s.ends_at <= now() OR (s.redeemed_at IS NULL AND s.ticket_expires_at <= now()))
            UNION
            SELECT r.tenant_id, r.organisation_id FROM {S}.support_access_requests r
             WHERE r.status = 'pending' AND r.deleted_at IS NULL AND r.expires_at <= now()
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.outbox_backlog() RETURNS TABLE (waiting bigint, oldest timestamptz, retrying bigint)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT count(*), min(o.created_at), count(*) FILTER (WHERE o.attempts > 0)
              FROM {S}.event_outbox o WHERE o.published_at IS NULL
        $$
    """)
    op.execute(f"GRANT CREATE ON SCHEMA {P} TO formalie_directory")
    for fn in DIRECTORY_FUNCTIONS:
        op.execute(f"ALTER FUNCTION {fn} OWNER TO formalie_directory")
    op.execute(f"REVOKE CREATE ON SCHEMA {P} FROM formalie_directory")
    for fn in (*OWNER_FUNCTIONS, *DIRECTORY_FUNCTIONS):
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO formalie_app")


def upgrade() -> None:
    op.execute(f"ALTER TABLE {P}.tenants ADD COLUMN trial_ends_at timestamptz, ADD COLUMN plan_limits jsonb")
    # A whole workspace's export is a ZIP (the internal admin API's /tenants/{id}/export)
    op.execute(f"ALTER TABLE {S}.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute(f"ALTER TABLE {S}.export_jobs ADD CONSTRAINT ck_export_jobs_format "
               "CHECK (format IN ('xlsx', 'csv', 'pdf', 'json', 'sql', 'zip'))")
    for statement in DDL:
        op.execute(statement)
    for table in SUPPORT_TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)

    globals_ = ", ".join(f"{P}.{t}" for t in B16_GLOBAL_TABLES)
    op.execute(f"GRANT SELECT ON {globals_} TO formalie_app, formalie_readonly")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {globals_} TO platform_writer")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {P}.admin_calls TO formalie_app")
    _functions()
    for table in B16_GLOBAL_TABLES:
        op.execute(f"CREATE TRIGGER stamp_published BEFORE INSERT OR UPDATE ON {P}.{table} "
                   f"FOR EACH ROW EXECUTE FUNCTION {P}.stamp_published()")

    # platform_reader: every table of both schemas, column by column, without secrets and answers
    bind = op.get_bind()
    tables = bind.execute(sa.text(
        "SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname IN (:s, :p) AND c.relkind IN ('r', 'p') AND NOT c.relispartition ORDER BY 1, 2"),
        {"s": S, "p": P}).all()
    for schema, table in tables:
        op.execute(reader_sql(f"{schema}.{table}"))

    # What Formalie ships today
    from app.modules.platform_bridge.seed import seed_globals

    seed_globals(bind)


def downgrade() -> None:
    for fn in (*OWNER_FUNCTIONS, *DIRECTORY_FUNCTIONS):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    op.execute(f"REVOKE SELECT (id, organisation_id) ON {S}.users FROM formalie_directory")
    op.execute(f"REVOKE SELECT (created_at, published_at, attempts) ON {S}.event_outbox FROM formalie_directory")
    for table in SUPPORT_TABLES:
        op.execute(f"REVOKE ALL ON {S}.{table} FROM formalie_directory")
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.execute(f"DROP TABLE {S}.{table}")
    op.execute(f"DROP TABLE {P}.admin_calls")
    for table in ("announcement_translations", "announcements", "plan_prices", "plan_limits", "plan_features",
                  "plans", "system_option_items", "system_option_lists", "system_template_translations",
                  "system_templates", "platform_settings", "reserved_subdomains", "feature_flags", "system_folders",
                  "system_email_templates", "system_themes", "system_page_designs"):
        op.execute(f"DROP TABLE {P}.{table}")
    op.execute(f"DROP FUNCTION IF EXISTS {P}.stamp_published()")
    op.execute(f"ALTER TABLE {P}.tenants DROP COLUMN trial_ends_at, DROP COLUMN plan_limits")
    op.execute(f"ALTER TABLE {S}.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute(f"ALTER TABLE {S}.export_jobs ADD CONSTRAINT ck_export_jobs_format "
               "CHECK (format IN ('xlsx', 'csv', 'pdf', 'json', 'sql'))")

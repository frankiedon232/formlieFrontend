"""B17 security fixes (security review 2026-10-12).

M6   The platform admin functions (platform.admin_tenant, admin_set_status, admin_set_plan,
     communication_workspaces) are no longer executable by formalie_app: only formalie_admin_api, the internal admin
     API's own login (DB_ADMIN_API_URL, created by scripts/db_bootstrap.py as a member of formalie_app), keeps
     EXECUTE. When that role doesn't exist yet the grants wait: scripts/db_bootstrap.py applies them (it runs the same
     statements after creating the role), so a database is never left without either.
     The portal's one use (why Formalie suspended the workspace) gets its own function, limited to the workspace in
     app.tenant_id:  platform.current_suspended_reason() → text.
M11  platform_reader no longer reads audit_logs.changes (edited answers' before / after) nor audit_logs.metadata
     (the Query editor's SQL text), see app/modules/platform_bridge/grants.py.
M8   request_logs retention: platform.drop_expired_partitions(regclass, timestamptz), SECURITY DEFINER, for
     request_logs only and never under 7 days; formalie_worker runs it daily (REQUEST_LOG_RETENTION_DAYS, 30). These
     are technical log rows, not workspace data: the documented exception to "no hard deletes" for logs.
H1   SSH host key pinning: datasources.ssh_host_key (the pinned key, "host:port SHA256:...") and
     datasource_tests.ssh_host_key (the key a test saw).

Revision ID: 0036
Revises: 0035
Created: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings
from app.modules.platform_bridge.grants import reader_sql

revision: str = '0036'
down_revision: str | None = '0035'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema
P = "platform"
CURRENT_TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"
ADMIN_FUNCTIONS = ("platform.admin_tenant(uuid)", "platform.admin_set_status(text, text, timestamptz)",
                   "platform.admin_set_plan(text, jsonb, timestamptz, boolean, boolean)",
                   "platform.communication_workspaces(text[], uuid[])")
ADMIN_ROLE = "formalie_admin_api"


def admin_grants_sql() -> str:
    """EXECUTE on the admin functions for formalie_admin_api only (when the role exists). Also run by
    scripts/db_bootstrap.py after it creates the role."""
    statements = "".join(
        f"EXECUTE 'REVOKE ALL ON FUNCTION {fn} FROM formalie_app'; "
        f"EXECUTE 'GRANT EXECUTE ON FUNCTION {fn} TO {ADMIN_ROLE}'; " for fn in ADMIN_FUNCTIONS)
    return f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ADMIN_ROLE}') THEN {statements}
            ELSE RAISE NOTICE '{ADMIN_ROLE} does not exist yet: run scripts/db_bootstrap.py, which applies these grants';
            END IF;
        END $$"""


DROP_EXPIRED = r"""
CREATE FUNCTION platform.drop_expired_partitions(p_parent regclass, p_before timestamptz)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_schema text;
    v_table text;
    v_part record;
    v_upper timestamptz;
    v_dropped integer := 0;
BEGIN
    SELECT n.nspname, c.relname INTO v_schema, v_table
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.oid = p_parent AND c.relkind = 'p';
    -- Only the request log expires this way; audit, responses, error and API logs never do
    IF v_table IS DISTINCT FROM 'request_logs' THEN
        RAISE EXCEPTION '% has no partition retention', p_parent;
    END IF;
    IF p_before > now() - interval '7 days' THEN
        RAISE EXCEPTION 'retention shorter than 7 days refused';
    END IF;
    FOR v_part IN
        SELECT c.relname, pg_get_expr(c.relpartbound, c.oid) AS bound
          FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
         WHERE i.inhparent = p_parent
    LOOP
        -- FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00'): a partition goes once all of it
        -- is older than the cut-off
        v_upper := substring(v_part.bound FROM 'TO \(''([^'']+)''\)')::timestamptz;
        IF v_upper IS NOT NULL AND v_upper <= p_before THEN
            EXECUTE format('ALTER TABLE %I.%I DETACH PARTITION %I.%I', v_schema, v_table, v_schema, v_part.relname);
            EXECUTE format('DROP TABLE %I.%I', v_schema, v_part.relname);
            v_dropped := v_dropped + 1;
        END IF;
    END LOOP;
    RETURN v_dropped;
END
$$
"""


def upgrade() -> None:
    # M8: request_logs retention (REQUEST_LOG_RETENTION_DAYS, Beat db.drop_expired_partitions as formalie_worker)
    op.execute(DROP_EXPIRED)
    op.execute("REVOKE ALL ON FUNCTION platform.drop_expired_partitions(regclass, timestamptz) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.drop_expired_partitions(regclass, timestamptz) TO formalie_worker")
    op.execute(f"ALTER TABLE {S}.datasources ADD COLUMN ssh_host_key varchar(400)")
    op.execute(f"ALTER TABLE {S}.datasource_tests ADD COLUMN ssh_host_key varchar(400)")
    op.execute(f"""
        CREATE FUNCTION {P}.current_suspended_reason() RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$ SELECT t.suspended_reason FROM platform.tenants t WHERE t.id = {CURRENT_TENANT} AND t.deleted_at IS NULL $$
    """)
    op.execute(f"REVOKE ALL ON FUNCTION {P}.current_suspended_reason() FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {P}.current_suspended_reason() TO formalie_app")
    op.execute(admin_grants_sql())
    # M11 and the two new columns: platform_reader's column list again (grants.py hides changes and metadata)
    op.execute(reader_sql(f"{S}.audit_logs"))
    op.execute(reader_sql(f"{S}.datasources"))
    op.execute(reader_sql(f"{S}.datasource_tests"))


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.drop_expired_partitions(regclass, timestamptz)")
    for fn in ADMIN_FUNCTIONS:
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO formalie_app")
    op.execute(f"DROP FUNCTION {P}.current_suspended_reason()")
    op.execute(f"ALTER TABLE {S}.datasources DROP COLUMN ssh_host_key")
    op.execute(f"ALTER TABLE {S}.datasource_tests DROP COLUMN ssh_host_key")
    op.execute(f"GRANT SELECT (changes, metadata) ON {S}.audit_logs TO platform_reader")

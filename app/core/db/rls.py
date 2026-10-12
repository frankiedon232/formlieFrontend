"""SQL for Row-Level Security, used by every migration that creates a tenant table (CLAUDE.md rule 1).

    for statement in enable_tenant_rls("organisations"):
        op.execute(statement)

turns RLS on and FORCES it (so even the table owner obeys it), adds the isolation policy on tenant_id AND
organisation_id, and grants `formalie_app` SELECT, INSERT, UPDATE: never DELETE (soft delete only, rule 6).
`platform_reader` gets every column but secrets and answers (app/modules/platform_bridge/grants.py, B16).
tests/db/test_rls.py fails if any table with a tenant_id column misses any of this.
"""

from __future__ import annotations

from app.core.config import get_settings

APP_ROLE = "formalie_app"
READONLY_ROLE = "formalie_readonly"
WORKER_ROLE = "formalie_worker"
PLATFORM_READER_ROLE = "platform_reader"
PLATFORM_WRITER_ROLE = "platform_writer"
OWNER_ROLE = "formalie_owner"

TENANT_MATCH = (
    "tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid "
    "AND organisation_id = nullif(current_setting('app.organisation_id', true), '')::uuid"
)


def _qualified(table: str, schema: str) -> str:
    return f"{schema}.{table}"


def enable_tenant_rls(
    table: str,
    schema: str | None = None,
    *,
    app_privileges: str = "SELECT, INSERT, UPDATE",
) -> list[str]:
    from app.modules.platform_bridge.grants import reader_sql

    name = _qualified(table, schema or get_settings().db_schema)
    return [
        f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY {table}_isolation ON {name} USING ({TENANT_MATCH}) WITH CHECK ({TENANT_MATCH})",
        f"GRANT {app_privileges} ON {name} TO {APP_ROLE}",
        f"GRANT SELECT ON {name} TO {READONLY_ROLE}",
        reader_sql(name),  # platform_reader: every column but secrets and answers
    ]


def disable_tenant_rls(table: str, schema: str | None = None) -> list[str]:
    """Downgrade counterpart (drops the policy and privileges; the table drop itself is the migration's)."""
    name = _qualified(table, schema or get_settings().db_schema)
    return [
        f"REVOKE ALL ON {name} FROM {APP_ROLE}, {READONLY_ROLE}, {PLATFORM_READER_ROLE}",
        f"DROP POLICY IF EXISTS {table}_isolation ON {name}",
    ]

"""Health checks of customers' databases run every few minutes for every workspace: platform.datasources_due() lists
the enabled connections (ids only) so the worker can check each in its own workspace's context.

Revision ID: 0024
Revises: 0023
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"


def upgrade() -> None:
    op.execute(f"GRANT SELECT (id, tenant_id, organisation_id, enabled, deleted_at) ON {S}.datasources TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION platform.datasources_due()
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, datasource_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT d.tenant_id, d.organisation_id, d.id FROM {S}.datasources d
             WHERE d.enabled AND d.deleted_at IS NULL
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    op.execute("ALTER FUNCTION platform.datasources_due() OWNER TO formalie_directory")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")
    op.execute("REVOKE ALL ON FUNCTION platform.datasources_due() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.datasources_due() TO formalie_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.datasources_due()")
    op.execute(f"REVOKE SELECT (id, tenant_id, organisation_id, enabled, deleted_at) ON {S}.datasources FROM formalie_directory")

"""platform.resolve_tenant also returns the workspace's plan (what its sign-in page may offer depends on it).

Revision ID: 0004
Revises: 0003
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BODY = """
    SELECT r.id, r.subdomain, r.name, r.status, r.organisation_id{plan_select} FROM (
        SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id AS organisation_id,
               t.plan_id::text AS plan_id, 0 AS rank
          FROM platform.tenants t
         WHERE t.subdomain = lower(p_subdomain) AND t.deleted_at IS NULL
        UNION ALL
        SELECT t.id, t.subdomain::text, t.name::text, t.status::text, t.primary_organisation_id, t.plan_id::text, 1
          FROM platform.tenant_subdomain_history h
          JOIN platform.tenants t ON t.id = h.tenant_id
         WHERE h.subdomain = lower(p_subdomain) AND h.until > now() AND t.deleted_at IS NULL
    ) r
    WHERE r.organisation_id IS NOT NULL
    ORDER BY r.rank
    LIMIT 1
"""


def _create(with_plan: bool) -> None:
    columns = "id uuid, subdomain text, name text, status text, organisation_id uuid" + (", plan_id text" if with_plan else "")
    op.execute("DROP FUNCTION IF EXISTS platform.resolve_tenant(text)")
    op.execute(f"""
        CREATE FUNCTION platform.resolve_tenant(p_subdomain text) RETURNS TABLE ({columns})
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $${BODY.format(plan_select=", r.plan_id" if with_plan else "")}$$
    """)
    op.execute("REVOKE ALL ON FUNCTION platform.resolve_tenant(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.resolve_tenant(text) TO formalie_app, formalie_readonly")


def upgrade() -> None:
    _create(with_plan=True)


def downgrade() -> None:
    _create(with_plan=False)

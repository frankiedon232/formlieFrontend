"""Edge proxy and closed workspaces (owner, 2026-10-12).

platform.tenants.status gains `closed`: a closing workspace whose date has passed. A soft state, nothing is
deleted (purging stays a platform admin decision for later); sign-in, the API and public forms refuse it.

platform.close_due_workspaces()   SECURITY DEFINER (formalie_owner): closing workspaces past close_at become
                                  closed; returns them for the audit trail (Beat task platform.close_due_workspaces)

platform.reserved_subdomains gains `services`: the API's own address (services.formalie.com) is never a workspace.

Revision ID: 0035
Revises: 0034
Created: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0035'
down_revision: str | None = '0034'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P = "platform"
FUNCTION = "platform.close_due_workspaces()"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {P}.tenants DROP CONSTRAINT IF EXISTS ck_tenants_status")
    op.execute(f"ALTER TABLE {P}.tenants ADD CONSTRAINT ck_tenants_status "
               "CHECK (status IN ('active', 'suspended', 'read_only', 'closing', 'closed'))")
    op.execute(f"""
        CREATE FUNCTION {FUNCTION}
        RETURNS TABLE (id uuid, organisation_id uuid, subdomain text, name text, close_at timestamptz)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            UPDATE platform.tenants t
               SET status = 'closed', updated_at = now()
             WHERE t.status = 'closing' AND t.close_at IS NOT NULL AND t.close_at <= now()
               AND t.deleted_at IS NULL AND t.primary_organisation_id IS NOT NULL
            RETURNING t.id, t.primary_organisation_id, t.subdomain::text, t.name::text, t.close_at
        $$
    """)
    op.execute(f"REVOKE ALL ON FUNCTION {FUNCTION} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {FUNCTION} TO formalie_app")
    op.execute(f"INSERT INTO {P}.reserved_subdomains (subdomain, reason, created_at, updated_at) "
               "VALUES ('services', 'Formalie''s own addresses', now(), now()) ON CONFLICT (subdomain) DO NOTHING")


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION}")
    # Back to the last state the old constraint knows; the closing date is still there
    op.execute(f"UPDATE {P}.tenants SET status = 'closing', updated_at = now() WHERE status = 'closed'")
    op.execute(f"ALTER TABLE {P}.tenants DROP CONSTRAINT IF EXISTS ck_tenants_status")
    op.execute(f"ALTER TABLE {P}.tenants ADD CONSTRAINT ck_tenants_status "
               "CHECK (status IN ('active', 'suspended', 'read_only', 'closing'))")
    op.execute(f"UPDATE {P}.reserved_subdomains SET retired_at = now(), updated_at = now() "
               "WHERE subdomain = 'services' AND retired_at IS NULL AND published_by_staff_id IS NULL")

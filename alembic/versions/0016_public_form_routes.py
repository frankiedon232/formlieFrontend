"""Public form addresses across workspaces (DATABASE-DESIGN → Tenant directory): a form's key on the shared forms host
and short link codes (unique across every organisation, retired codes never handed out again). The app reaches them
only through these functions, always for the workspace of its own transaction (app.tenant_id):

  platform.register_form_key(key, form)       a new form's public key
  platform.resolve_form_key(key)              → the workspace and form behind a key (public pages)
  platform.claim_short_code(code, form)       → true when the code was free (never used, never retired)
  platform.retire_short_code(code)            the code stops working for good
  platform.resolve_short_code(code)           → the workspace and form behind a live code

Revision ID: 0016
Revises: 0015
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
CURRENT_TENANT = "nullif(current_setting('app.tenant_id', true), '')::uuid"
RESOLVED = "tenant_id uuid, organisation_id uuid, subdomain text, status text, form_id uuid"
FUNCTIONS = ("platform.register_form_key(text, uuid)", "platform.resolve_form_key(text)",
             "platform.claim_short_code(text, uuid)", "platform.retire_short_code(text)",
             "platform.resolve_short_code(text)")


def upgrade() -> None:
    op.create_table(
        "public_form_routes",
        sa.Column("public_key", sa.String(20), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("form_id", sa.Uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT"),
        schema="platform",
    )
    op.create_table(
        "short_link_codes",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("form_id", sa.Uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform.tenants.id"], ondelete="RESTRICT"),
        schema="platform",
    )
    op.execute("GRANT SELECT ON platform.public_form_routes, platform.short_link_codes TO platform_reader")
    # Forms made before: their keys and short codes
    op.execute(f"INSERT INTO platform.public_form_routes (public_key, tenant_id, form_id) "
               f"SELECT public_key, tenant_id, id FROM {S}.forms ON CONFLICT DO NOTHING")
    op.execute(f"INSERT INTO platform.short_link_codes (code, tenant_id, form_id, retired_at) "
               f"SELECT short_code, tenant_id, id, purged_at FROM {S}.forms WHERE short_code IS NOT NULL ON CONFLICT DO NOTHING")

    op.execute(f"""
        CREATE FUNCTION platform.register_form_key(p_key text, p_form uuid) RETURNS void
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        BEGIN
            IF {CURRENT_TENANT} IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            INSERT INTO platform.public_form_routes (public_key, tenant_id, form_id) VALUES (p_key, {CURRENT_TENANT}, p_form);
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.resolve_form_key(p_key text) RETURNS TABLE ({RESOLVED})
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.primary_organisation_id, t.subdomain::text, t.status::text, r.form_id
              FROM platform.public_form_routes r JOIN platform.tenants t ON t.id = r.tenant_id
             WHERE r.public_key = p_key AND t.deleted_at IS NULL
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.claim_short_code(p_code text, p_form uuid) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
        BEGIN
            IF {CURRENT_TENANT} IS NULL THEN RAISE EXCEPTION 'no workspace'; END IF;
            INSERT INTO platform.short_link_codes (code, tenant_id, form_id) VALUES (p_code, {CURRENT_TENANT}, p_form)
            ON CONFLICT DO NOTHING;
            RETURN FOUND;
        END
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.retire_short_code(p_code text) RETURNS void
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            UPDATE platform.short_link_codes SET retired_at = now()
             WHERE code = p_code AND tenant_id = {CURRENT_TENANT} AND retired_at IS NULL
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION platform.resolve_short_code(p_code text) RETURNS TABLE ({RESOLVED})
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT t.id, t.primary_organisation_id, t.subdomain::text, t.status::text, c.form_id
              FROM platform.short_link_codes c JOIN platform.tenants t ON t.id = c.tenant_id
             WHERE c.code = p_code AND c.retired_at IS NULL AND t.deleted_at IS NULL
        $$
    """)
    for fn in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO formalie_app")


def downgrade() -> None:
    for fn in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    op.drop_table("short_link_codes", schema="platform")
    op.drop_table("public_form_routes", schema="platform")

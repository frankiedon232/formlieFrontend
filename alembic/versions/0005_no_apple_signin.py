"""No Apple sign-in (owner 2026-10-11): social sign-in is Google, Microsoft and Facebook only.

- user_identities.provider no longer allows 'apple'.
- Saved sign-in settings lose 'apple' from their methods (each workspace in turn, since RLS is forced on the owner).

Revision ID: 0005
Revises: 0004
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema


def _provider_check(values: str) -> None:
    op.execute(f"ALTER TABLE {S}.user_identities DROP CONSTRAINT IF EXISTS ck_user_identities_provider")
    op.execute(f"ALTER TABLE {S}.user_identities ADD CONSTRAINT ck_user_identities_provider CHECK (provider IN ({values}))")


def upgrade() -> None:
    _provider_check("'google', 'microsoft', 'facebook', 'sso'")
    op.execute(f"""
        DO $$
        DECLARE t record;
        BEGIN
            FOR t IN SELECT id, primary_organisation_id FROM platform.tenants WHERE primary_organisation_id IS NOT NULL LOOP
                PERFORM set_config('app.tenant_id', t.id::text, true),
                        set_config('app.organisation_id', t.primary_organisation_id::text, true);
                UPDATE {S}.workspace_settings
                   SET value = jsonb_set(value, '{{methods}}', COALESCE(
                           (SELECT jsonb_agg(m) FROM jsonb_array_elements(value -> 'methods') m WHERE m <> '"apple"'),
                           '[]'::jsonb)),
                       updated_at = now()
                 WHERE section = 'signin' AND value -> 'methods' ? 'apple';
            END LOOP;
            PERFORM set_config('app.tenant_id', '', true), set_config('app.organisation_id', '', true);
        END
        $$
    """)


def downgrade() -> None:
    _provider_check("'google', 'microsoft', 'apple', 'facebook', 'sso'")

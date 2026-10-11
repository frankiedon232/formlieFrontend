"""Respondents' files are personal data: platform.public_file() never serves them (they are seen only inside their
workspace, behind a short-lived link, B8).

Revision ID: 0019
Revises: 0018
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"


def _create(private: bool) -> None:
    extra = " AND u.purpose <> 'response_file'" if private else ""
    op.execute(f"""
        CREATE OR REPLACE FUNCTION platform.public_file(p_id uuid)
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, file_key text, content_type text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT u.tenant_id, u.organisation_id, u.file_key::text, u.content_type::text FROM {S}.uploads u
             WHERE u.id = p_id AND u.completed_at IS NOT NULL AND u.deleted_at IS NULL AND u.scan_status = 'clean'{extra}
        $$
    """)


def upgrade() -> None:
    op.execute(f"GRANT SELECT (purpose) ON {S}.uploads TO formalie_directory")
    _create(private=True)


def downgrade() -> None:
    _create(private=False)
    op.execute(f"REVOKE SELECT (purpose) ON {S}.uploads FROM formalie_directory")

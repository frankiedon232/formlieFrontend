"""Response exports use the export jobs: PDF joins the formats.

Revision ID: 0021
Revises: 0020
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {S}.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute(f"ALTER TABLE {S}.export_jobs ADD CONSTRAINT ck_export_jobs_format CHECK (format IN ('xlsx', 'csv', 'pdf'))")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_export_jobs_kind ON {S}.export_jobs (tenant_id, kind, created_at)")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {S}.ix_export_jobs_kind")
    op.execute(f"ALTER TABLE {S}.export_jobs DROP CONSTRAINT IF EXISTS ck_export_jobs_format")
    op.execute(f"ALTER TABLE {S}.export_jobs ADD CONSTRAINT ck_export_jobs_format CHECK (format IN ('xlsx', 'csv'))")

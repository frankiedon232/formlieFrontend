"""Error logs in the database (BACKEND-SPEC §8.3): warning, error and critical lines of every process, loaded from the
dated level files by the `logs.ingest_error_files` Beat task. Insert-only, monthly partitions, RLS forced.

Revision ID: 0007
Revises: 0006
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings
from app.core.db.rls import TENANT_MATCH

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema


def upgrade() -> None:
    op.create_table(
        "error_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("logger", sa.String(120)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(20)),
        sa.Column("security_event", sa.String(60)),
        sa.Column("trace_id", sa.String(36)),
        sa.Column("tenant_id", sa.Uuid()),
        sa.Column("organisation_id", sa.Uuid()),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("method", sa.String(10)),
        sa.Column("path", sa.String(500)),
        sa.Column("stack", sa.Text()),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("environment", sa.String(20)),
        sa.Column("release", sa.String(40)),
        sa.Column("source", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id", "occurred_at", name="pk_error_logs"),
        schema=S,
        postgresql_partition_by="RANGE (occurred_at)",
    )
    op.create_index("ix_error_logs_level_occurred", "error_logs", ["level", "occurred_at"], schema=S)
    op.create_index("ix_error_logs_tenant_occurred", "error_logs", ["tenant_id", "occurred_at"], schema=S)
    op.create_index("ix_error_logs_trace_id", "error_logs", ["trace_id"], schema=S)
    op.create_index("ix_error_logs_code", "error_logs", ["error_code", "occurred_at"], schema=S)

    op.execute(f"ALTER TABLE {S}.error_logs ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {S}.error_logs FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY error_logs_read ON {S}.error_logs FOR SELECT USING ({TENANT_MATCH})")
    op.execute(f"CREATE POLICY error_logs_write ON {S}.error_logs FOR INSERT TO formalie_worker WITH CHECK (true)")
    op.execute(f"GRANT INSERT ON {S}.error_logs TO formalie_worker")
    op.execute(f"GRANT SELECT ON {S}.error_logs TO platform_reader")
    op.execute(f"SELECT platform.ensure_monthly_partitions('{S}.error_logs'::regclass, 3)")

    op.create_table(
        "log_ingest_offsets",
        sa.Column("file", sa.String(200), nullable=False),
        sa.Column("offset", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("file", name="pk_log_ingest_offsets"),
        schema=S,
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {S}.log_ingest_offsets TO formalie_worker")


def downgrade() -> None:
    op.drop_table("log_ingest_offsets", schema=S)
    op.drop_table("error_logs", schema=S)  # drops its partitions with it

"""Request log: every request in full (BACKEND-SPEC §8.1; owner 2026-10-11).

Revision ID: 0002
Revises: 0001
Created: 2026-10-11

Monthly partitions. RLS forced: reads only within a workspace (`request_logs_read`), inserts by the two writers
(`request_logs_write`: the API's `database` sink and the `logs` Celery queue). Nobody may update or delete.
`platform_reader` reads every column except the bodies (answers may sit in them).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings
from app.core.db.rls import TENANT_MATCH

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema
BODY_COLUMNS = ("request_body", "request_body_text", "response_body")


def upgrade() -> None:
    text_array = postgresql.ARRAY(sa.Text())
    table = op.create_table(
        "request_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(36), nullable=False),
        # who
        sa.Column("tenant_id", sa.Uuid()),
        sa.Column("organisation_id", sa.Uuid()),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("session_id", sa.Uuid()),
        # what
        sa.Column("scheme", sa.String(8)),
        sa.Column("http_version", sa.String(8)),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("host", sa.String(255)),
        sa.Column("host_kind", sa.String(10)),
        sa.Column("subdomain", sa.String(63)),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("route", sa.Text()),
        sa.Column("query", postgresql.JSONB()),
        # outcome
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("duration_ms", sa.Float()),
        sa.Column("request_bytes", sa.BigInteger()),
        sa.Column("response_bytes", sa.BigInteger()),
        sa.Column("error_code", sa.String(20)),
        sa.Column("rate_limited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("flags", text_array),
        # where from
        sa.Column("client_ip", postgresql.INET()),
        sa.Column("peer_ip", postgresql.INET()),
        sa.Column("forwarded_for", sa.Text()),
        sa.Column("proxy_trusted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("geo_source", sa.String(12)),
        sa.Column("continent", sa.String(2)),
        sa.Column("country", sa.String(2)),
        sa.Column("country_name", sa.String(100)),
        sa.Column("region", sa.String(100)),
        sa.Column("region_code", sa.String(10)),
        sa.Column("city", sa.String(100)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("timezone", sa.String(64)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("accuracy_km", sa.Integer()),
        sa.Column("asn", sa.BigInteger()),
        sa.Column("as_org", sa.String(255)),
        # client
        sa.Column("user_agent", sa.Text()),
        sa.Column("device_type", sa.String(10)),
        sa.Column("device_brand", sa.String(100)),
        sa.Column("device_model", sa.String(100)),
        sa.Column("os", sa.String(100)),
        sa.Column("os_version", sa.String(50)),
        sa.Column("browser", sa.String(100)),
        sa.Column("browser_version", sa.String(50)),
        sa.Column("is_bot", sa.Boolean()),
        sa.Column("referer", sa.Text()),
        sa.Column("origin", sa.Text()),
        sa.Column("client_app", sa.String(100)),
        sa.Column("client_version", sa.String(50)),
        # request in full (secrets masked at capture)
        sa.Column("request_headers", postgresql.JSONB()),
        sa.Column("request_content_type", sa.String(255)),
        sa.Column("request_body", postgresql.JSONB()),
        sa.Column("request_body_text", sa.Text()),
        sa.Column("request_body_sha256", sa.String(64)),
        sa.Column("request_body_keys", text_array),
        sa.Column("request_body_fields", sa.Integer()),
        sa.Column("request_body_truncated", sa.Boolean(), server_default="false", nullable=False),
        # response
        sa.Column("response_headers", postgresql.JSONB()),
        sa.Column("response_content_type", sa.String(255)),
        sa.Column("response_body", postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id", "occurred_at", name="pk_request_logs"),
        schema=S,
        postgresql_partition_by="RANGE (occurred_at)",
    )
    op.create_index("ix_request_logs_occurred_at", "request_logs", ["occurred_at"], schema=S)
    op.create_index("ix_request_logs_tenant_occurred", "request_logs", ["tenant_id", "occurred_at"], schema=S)
    op.create_index("ix_request_logs_client_ip", "request_logs", ["client_ip", "occurred_at"], schema=S)
    op.create_index("ix_request_logs_trace_id", "request_logs", ["trace_id"], schema=S)

    op.execute(f"ALTER TABLE {S}.request_logs ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {S}.request_logs FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY request_logs_read ON {S}.request_logs FOR SELECT USING ({TENANT_MATCH})")
    op.execute(f"CREATE POLICY request_logs_write ON {S}.request_logs FOR INSERT "
               f"TO formalie_app, formalie_worker WITH CHECK (true)")
    op.execute(f"GRANT INSERT ON {S}.request_logs TO formalie_app, formalie_worker")
    readable = ", ".join(c.name for c in table.columns if c.name not in BODY_COLUMNS)
    op.execute(f"GRANT SELECT ({readable}) ON {S}.request_logs TO platform_reader")
    op.execute(f"SELECT platform.ensure_monthly_partitions('{S}.request_logs'::regclass, 3)")


def downgrade() -> None:
    op.drop_table("request_logs", schema=S)  # drops its partitions with it

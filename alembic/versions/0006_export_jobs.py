"""Export jobs: files made in the background (the audit trail first), then a one-time download link.

Revision ID: 0006
Revises: 0005
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('export_jobs',
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('format', sa.String(length=4), nullable=False),
    sa.Column('file_name', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=10), server_default='queued', nullable=False),
    sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
    sa.Column('rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('file_key', sa.String(length=300), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=True),
    sa.Column('token_enc', sa.String(length=300), nullable=True),
    sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("format IN ('xlsx', 'csv')", name=op.f('ck_export_jobs_format')),
    sa.CheckConstraint("status IN ('queued', 'running', 'done', 'failed')", name=op.f('ck_export_jobs_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_export_jobs')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_export_jobs_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_export_jobs_creator', 'export_jobs', ['tenant_id', 'created_by', 'created_at'], unique=False, schema='formaly')
    op.create_index('uq_export_jobs_token', 'export_jobs', ['token_hash'], unique=True, schema='formaly', postgresql_where=sa.text('token_hash IS NOT NULL'))
    for statement in enable_tenant_rls("export_jobs"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("export_jobs"):
        op.execute(statement)
    op.drop_table("export_jobs", schema="formaly")

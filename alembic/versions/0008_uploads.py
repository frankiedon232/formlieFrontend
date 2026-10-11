"""Uploads: tickets, stored bytes and finished files (logos, share images, images in forms), and
platform.public_file() so a public page (sign-in page, public form) can show a workspace's file by its id.

Revision ID: 0008
Revises: 0007
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema


def upgrade() -> None:
    op.create_table('uploads',
    sa.Column('purpose', sa.String(length=20), nullable=False),
    sa.Column('file_name', sa.String(length=200), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('max_bytes', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('file_key', sa.String(length=300), nullable=True),
    sa.Column('stored_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scan_status', sa.String(length=10), server_default='pending', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("purpose IN ('logo', 'share_image', 'form_image')", name=op.f('ck_uploads_purpose')),
    sa.CheckConstraint("scan_status IN ('pending', 'clean', 'refused')", name=op.f('ck_uploads_scan_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_uploads')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_uploads_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_uploads_token', 'uploads', ['token_hash'], unique=True, schema='formaly', postgresql_where=sa.text('token_hash IS NOT NULL'))
    for statement in enable_tenant_rls("uploads"):
        op.execute(statement)
    # Public pages: a finished file by its id, whatever the workspace (only what serving it needs)
    op.execute(f"GRANT SELECT (id, tenant_id, organisation_id, file_key, content_type, completed_at, deleted_at, "
               f"scan_status) ON {S}.uploads TO formalie_directory")
    op.execute(f"""
        CREATE FUNCTION platform.public_file(p_id uuid)
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, file_key text, content_type text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT u.tenant_id, u.organisation_id, u.file_key::text, u.content_type::text FROM {S}.uploads u
             WHERE u.id = p_id AND u.completed_at IS NOT NULL AND u.deleted_at IS NULL AND u.scan_status = 'clean'
        $$
    """)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    op.execute("ALTER FUNCTION platform.public_file(uuid) OWNER TO formalie_directory")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")
    op.execute("REVOKE ALL ON FUNCTION platform.public_file(uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION platform.public_file(uuid) TO formalie_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS platform.public_file(uuid)")
    for statement in disable_tenant_rls("uploads"):
        op.execute(statement)
    op.drop_table("uploads", schema=S)

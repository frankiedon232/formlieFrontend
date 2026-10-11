"""Forms: folders (with folder access), forms, immutable published versions, per-form sharing (form_grants).

Revision ID: 0012
Revises: 0011
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("folders", "forms", "form_versions", "form_grants")


def upgrade() -> None:
    op.create_table('folders',
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.Column('color', sa.String(length=16), nullable=True),
    sa.Column('system_key', sa.String(length=40), nullable=True),
    sa.Column('access_restricted', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('access_roles', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('access_departments', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('access_people', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_folders')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_folders_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('forms',
    sa.Column('folder_id', sa.Uuid(), nullable=True),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('slug', sa.String(length=70), nullable=False),
    sa.Column('public_key', sa.String(length=20), nullable=False),
    sa.Column('custom_link', sa.String(length=80), nullable=True),
    sa.Column('status', sa.String(length=10), server_default='draft', nullable=False),
    sa.Column('previous_status', sa.String(length=10), nullable=True),
    sa.Column('draft_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('published_version_id', sa.Uuid(), nullable=True),
    sa.Column('has_unpublished_changes', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('template_key', sa.String(length=80), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('access', sa.String(length=14), server_default='public', nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=True),
    sa.Column('password_version', sa.Integer(), server_default='0', nullable=False),
    sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('response_limit', sa.Integer(), nullable=True),
    sa.Column('opens_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closes_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('embed_domains', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('team_access', sa.String(length=6), server_default='edit', nullable=False),
    sa.Column('seo', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('short_code', sa.String(length=16), nullable=True),
    sa.Column('short_clicks', sa.Integer(), server_default='0', nullable=False),
    sa.Column('short_created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('responses_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('next_response_number', sa.Integer(), server_default='1', nullable=False),
    sa.Column('completion_rate', sa.Integer(), server_default='0', nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('purged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.CheckConstraint("access IN ('public', 'password', 'invite', 'organisation')", name=op.f('ck_forms_access')),
    sa.CheckConstraint("status IN ('draft', 'published', 'closed', 'archived')", name=op.f('ck_forms_status')),
    sa.CheckConstraint("team_access IN ('edit', 'view', 'none')", name=op.f('ck_forms_team_access')),
    sa.ForeignKeyConstraint(['tenant_id', 'folder_id'], ['formaly.folders.tenant_id', 'formaly.folders.id'], name=op.f('fk_forms_tenant_id_folder_id_folders'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'owner_id'], ['formaly.users.tenant_id', 'formaly.users.id'], name=op.f('fk_forms_tenant_id_owner_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_forms')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_forms_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('form_versions',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('published_by', sa.Uuid(), nullable=True),
    sa.Column('published_by_name', sa.String(length=200), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('change_summary', sa.String(length=500), nullable=True),
    sa.Column('fields_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_form_versions_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_form_versions')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_form_versions_tenant_id_id')),
    schema='formaly'
    )
    op.create_table('form_grants',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("level IN ('responses', 'view', 'edit')", name=op.f('ck_form_grants_level')),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_form_grants_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'user_id'], ['formaly.users.tenant_id', 'formaly.users.id'], name=op.f('fk_form_grants_tenant_id_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_form_grants')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_form_grants_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_folders_name', 'folders', ['tenant_id', sa.literal_column('lower(name)')], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_forms_tenant_folder', 'forms', ['tenant_id', 'folder_id'], unique=False, schema='formaly')
    op.create_index('ix_forms_tenant_owner', 'forms', ['tenant_id', 'owner_id'], unique=False, schema='formaly')
    op.create_index('ix_forms_tenant_updated', 'forms', ['tenant_id', 'updated_at'], unique=False, schema='formaly')
    op.create_index('uq_forms_custom_link', 'forms', ['tenant_id', 'custom_link'], unique=True, schema='formaly', postgresql_where=sa.text('custom_link IS NOT NULL AND purged_at IS NULL'))
    op.create_index('uq_forms_public_key', 'forms', ['public_key'], unique=True, schema='formaly')
    op.create_index('uq_forms_short_code', 'forms', ['short_code'], unique=True, schema='formaly', postgresql_where=sa.text('short_code IS NOT NULL'))
    op.create_index('uq_forms_slug', 'forms', ['tenant_id', 'slug'], unique=True, schema='formaly', postgresql_where=sa.text('purged_at IS NULL'))
    op.create_index('uq_form_grants', 'form_grants', ['tenant_id', 'form_id', 'user_id'], unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('uq_form_versions_number', 'form_versions', ['tenant_id', 'form_id', 'number'], unique=True, schema='formaly')
    for table in TABLES:
        # Published versions never change: the app may only add and read them
        privileges = "SELECT, INSERT" if table == "form_versions" else "SELECT, INSERT, UPDATE"
        for statement in enable_tenant_rls(table, app_privileges=privileges):
            op.execute(statement)


def downgrade() -> None:
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema="formaly")

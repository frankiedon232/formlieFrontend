"""Responses and public filling: responses (monthly partitions on submitted_at), one row per fill-in session,
save-and-resume drafts, respondent email codes, and respondents' files on uploads.

Revision ID: 0018
Revises: 0017
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
TABLES = ("responses", "response_submissions", "resume_drafts", "respondent_verifications")
PURPOSES = ("logo", "share_image", "form_image", "avatar", "response_file")
# platform_reader reads everything but the answers (PLATFORM-ADMIN-INTEGRATION §1)
HIDDEN = {"responses": "data", "resume_drafts": "data"}


def _columns_but(table: str, hidden: str) -> str:
    return f"""
        DO $$ DECLARE cols text; BEGIN
            SELECT string_agg(quote_ident(column_name), ', ') INTO cols FROM information_schema.columns
             WHERE table_schema = '{S}' AND table_name = '{table}' AND column_name <> '{hidden}';
            EXECUTE format('REVOKE SELECT ON {S}.{table} FROM platform_reader');
            EXECUTE format('GRANT SELECT (%s) ON {S}.{table} TO platform_reader', cols);
        END $$"""


def upgrade() -> None:
    op.create_table('respondent_verifications',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('email_hash', sa.String(length=64), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=True),
    sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_respondent_verifications_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_respondent_verifications')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_respondent_verifications_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_respondent_verifications_email', 'respondent_verifications', ['tenant_id', 'form_id', 'email_hash'], unique=False, schema='formaly')
    op.create_table('response_submissions',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('submission_id', sa.String(length=64), nullable=False),
    sa.Column('response_id', sa.Uuid(), nullable=False),
    sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_response_submissions_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_response_submissions')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_response_submissions_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_response_submissions', 'response_submissions', ['tenant_id', 'form_id', 'submission_id'], unique=True, schema='formaly')
    op.create_table('responses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('form_version_no', sa.Integer(), nullable=True),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('channel', sa.String(length=6), nullable=False),
    sa.Column('submission_id', sa.String(length=64), nullable=True),
    sa.Column('api_token_id', sa.Uuid(), nullable=True),
    sa.Column('device_hash', sa.String(length=64), nullable=True),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('identity_email', sa.String(length=254), nullable=True),
    sa.Column('respondent_kind', sa.String(length=10), nullable=True),
    sa.Column('respondent_ref_id', sa.Uuid(), nullable=True),
    sa.Column('respondent_email', sa.String(length=254), nullable=True),
    sa.Column('respondent_name', sa.String(length=200), nullable=True),
    sa.Column('possible_duplicate', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('duplicate_cleared', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('status', sa.String(length=10), server_default='new', nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('edited', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('country', sa.String(length=2), nullable=True),
    sa.Column('device', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.CheckConstraint("channel IN ('link', 'embed', 'api')", name=op.f('ck_responses_channel')),
    sa.CheckConstraint("status IN ('new', 'reviewed', 'approved', 'rejected')", name=op.f('ck_responses_status')),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_responses_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('tenant_id', 'id', 'submitted_at', name=op.f('pk_responses')),
    schema='formaly',
    postgresql_partition_by='RANGE (submitted_at)'
    )
    op.create_index('ix_responses_device', 'responses', ['tenant_id', 'form_id', 'device_hash'], unique=False, schema='formaly')
    op.create_index('ix_responses_fingerprint', 'responses', ['tenant_id', 'form_id', 'fingerprint'], unique=False, schema='formaly')
    op.create_index('ix_responses_form', 'responses', ['tenant_id', 'form_id', 'submitted_at'], unique=False, schema='formaly')
    op.create_index('ix_responses_identity', 'responses', ['tenant_id', 'form_id', 'identity_email'], unique=False, schema='formaly')
    op.create_table('resume_drafts',
    sa.Column('form_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('page', sa.Integer(), server_default='0', nullable=False),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'form_id'], ['formaly.forms.tenant_id', 'formaly.forms.id'], name=op.f('fk_resume_drafts_tenant_id_form_id_forms'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resume_drafts')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_resume_drafts_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_resume_drafts_token', 'resume_drafts', ['token_hash'], unique=True, schema='formaly')
    op.add_column('uploads', sa.Column('form_id', sa.Uuid(), nullable=True), schema='formaly')
    op.add_column('uploads', sa.Column('field_key', sa.String(length=64), nullable=True), schema='formaly')
    op.add_column('uploads', sa.Column('file_kind', sa.String(length=6), nullable=True), schema='formaly')
    op.add_column('uploads', sa.Column('listed', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='formaly')
    op.add_column('uploads', sa.Column('response_id', sa.Uuid(), nullable=True), schema='formaly')
    op.add_column('uploads', sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=True), schema='formaly')
    op.create_index('ix_uploads_response', 'uploads', ['tenant_id', 'response_id'], unique=False, schema='formaly', postgresql_where=sa.text('response_id IS NOT NULL'))

    for table in TABLES:
        for statement in enable_tenant_rls(table):
            op.execute(statement)
    for table, hidden in HIDDEN.items():
        op.execute(_columns_but(table, hidden))
    op.execute(f"SELECT platform.ensure_monthly_partitions('{S}.responses'::regclass, 3)")
    values = ", ".join(f"'{p}'" for p in PURPOSES)
    op.execute(f"ALTER TABLE {S}.uploads DROP CONSTRAINT IF EXISTS ck_uploads_purpose")
    op.execute(f"ALTER TABLE {S}.uploads ADD CONSTRAINT ck_uploads_purpose CHECK (purpose IN ({values}))")


def downgrade() -> None:
    values = ", ".join(f"'{p}'" for p in PURPOSES[:-1])
    op.execute(f"ALTER TABLE {S}.uploads DROP CONSTRAINT IF EXISTS ck_uploads_purpose")
    op.execute(f"ALTER TABLE {S}.uploads ADD CONSTRAINT ck_uploads_purpose CHECK (purpose IN ({values}))")
    op.drop_index("ix_uploads_response", table_name="uploads", schema=S)
    for column in ("response_submitted_at", "response_id", "listed", "file_kind", "field_key", "form_id"):
        op.drop_column("uploads", column, schema=S)
    for table in reversed(TABLES):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema=S)

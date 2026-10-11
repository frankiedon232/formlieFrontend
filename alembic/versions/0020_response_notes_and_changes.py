"""The team's notes on responses and the history of changes to them (status, tags, edited answers).

Revision ID: 0020
Revises: 0019
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"


def upgrade() -> None:
    op.create_table('response_changes',
    sa.Column('response_id', sa.Uuid(), nullable=False),
    sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('by_id', sa.Uuid(), nullable=True),
    sa.Column('by_name', sa.String(length=200), nullable=False),
    sa.Column('field', sa.String(length=100), nullable=False),
    sa.Column('before', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('after', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id', 'response_id', 'response_submitted_at'], ['formaly.responses.tenant_id', 'formaly.responses.id', 'formaly.responses.submitted_at'], name=op.f('fk_response_changes_tenant_id_response_id_response_submitted_at_responses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_response_changes')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_response_changes_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_response_changes_response', 'response_changes', ['tenant_id', 'response_id', 'at'], unique=False, schema='formaly')
    op.create_table('response_notes',
    sa.Column('response_id', sa.Uuid(), nullable=False),
    sa.Column('response_submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=True),
    sa.Column('author_name', sa.String(length=200), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'response_id', 'response_submitted_at'], ['formaly.responses.tenant_id', 'formaly.responses.id', 'formaly.responses.submitted_at'], name=op.f('fk_response_notes_tenant_id_response_id_response_submitted_at_responses'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_response_notes')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_response_notes_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('ix_response_notes_response', 'response_notes', ['tenant_id', 'response_id'], unique=False, schema='formaly')
    for statement in enable_tenant_rls("response_notes"):
        op.execute(statement)
    # The history is kept as it is: the app may only add to it
    for statement in enable_tenant_rls("response_changes", app_privileges="SELECT, INSERT"):
        op.execute(statement)


def downgrade() -> None:
    for table in ("response_changes", "response_notes"):
        for statement in disable_tenant_rls(table):
            op.execute(statement)
        op.drop_table(table, schema=S)

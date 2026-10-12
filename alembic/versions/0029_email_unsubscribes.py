"""Unsubscribe links in optional emails (owner, 2026-10-12): who stopped which kind of email, per workspace.

Revision ID: 0029
Revises: 0028
Created: 2026-10-12

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = '0029'
down_revision: str | None = '0028'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('email_unsubscribes',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('ref', sa.String(length=64), server_default='', nullable=False),
    sa.Column('stopped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("kind IN ('response_notification', 'notification', 'daily_digest', 'form_invitation')",
                       name=op.f('ck_email_unsubscribes_kind')),
    sa.CheckConstraint("email = lower(email)", name=op.f('ck_email_unsubscribes_email_lower')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_unsubscribes')),
    sa.UniqueConstraint('tenant_id', 'id', name=op.f('uq_email_unsubscribes_tenant_id_id')),
    schema='formaly'
    )
    op.create_index('uq_email_unsubscribes_active', 'email_unsubscribes', ['tenant_id', 'email', 'kind', 'ref'],
                    unique=True, schema='formaly', postgresql_where=sa.text('deleted_at IS NULL'))
    for statement in enable_tenant_rls("email_unsubscribes"):
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls("email_unsubscribes"):
        op.execute(statement)
    op.drop_index('uq_email_unsubscribes_active', table_name='email_unsubscribes', schema='formaly')
    op.drop_table('email_unsubscribes', schema='formaly')

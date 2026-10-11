"""Tips on new pages per person (user_tours), and profile photos as uploads (purpose `avatar`).

Revision ID: 0011
Revises: 0010
Created: 2026-10-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = get_settings().db_schema


def _purposes(values: str) -> None:
    op.execute(f"ALTER TABLE {S}.uploads DROP CONSTRAINT IF EXISTS ck_uploads_purpose")
    op.execute(f"ALTER TABLE {S}.uploads ADD CONSTRAINT ck_uploads_purpose CHECK (purpose IN ({values}))")


def upgrade() -> None:
    op.create_table(
        "user_tours",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tours_off", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("seen", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], [f"{S}.users.tenant_id", f"{S}.users.id"],
                                name=op.f("fk_user_tours_tenant_id_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_tours")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_user_tours_tenant_id_id")),
        schema=S,
    )
    op.create_index("uq_user_tours_user", "user_tours", ["tenant_id", "user_id"], unique=True, schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL"))
    for statement in enable_tenant_rls("user_tours"):
        op.execute(statement)
    _purposes("'logo', 'share_image', 'form_image', 'avatar'")


def downgrade() -> None:
    _purposes("'logo', 'share_image', 'form_image'")
    for statement in disable_tenant_rls("user_tours"):
        op.execute(statement)
    op.drop_table("user_tours", schema=S)

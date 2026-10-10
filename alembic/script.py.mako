"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Created: ${create_date}

Checklist for a tenant table: TenantMixin, tenant_table_args(), tenant-aware FKs (tenant_fk), partial uniques
WHERE deleted_at IS NULL, no ON DELETE CASCADE, and `for s in enable_tenant_rls("table"): op.execute(s)`.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
from app.core.db.rls import disable_tenant_rls, enable_tenant_rls  # noqa: F401

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}

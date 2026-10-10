"""Declarative base and mixins (DATABASE-DESIGN, Conventions).

- UUIDv7 primary keys made in the app (CLAUDE.md rule 7).
- TenantMixin: tenant_id + organisation_id, composite unique (tenant_id, id) for tenant-aware foreign keys.
  Every tenant table also gets RLS ENABLED and FORCED in its migration (`enable_tenant_rls`, app/core/db/rls.py).
- Soft delete only (rule 6): `deleted_at` / `deleted_by`; `session.delete()` is refused by the guard below,
  and `formalie_app` has no DELETE privilege on tenant tables, so a hard delete fails twice.
- Foreign keys are ON DELETE RESTRICT, never CASCADE.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, MetaData, UniqueConstraint, Uuid, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.config import get_settings
from app.core.ids import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


APP_SCHEMA = get_settings().db_schema


class Base(DeclarativeBase):
    """Tables without an explicit schema go into the app schema (DB_SCHEMA, `formaly`); global ones say `platform`."""

    metadata = MetaData(schema=APP_SCHEMA, naming_convention=NAMING_CONVENTION)


class UuidPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)


class TenantMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    organisation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    def soft_delete(self, by: uuid.UUID | None) -> None:
        self.deleted_at = datetime.now(UTC)
        self.deleted_by = by


class RowVersionMixin:
    """Optimistic locking: the client sends `row_version` back; a mismatch is FRM-GEN-1009."""

    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


def tenant_table_args(*extra: Any) -> tuple[Any, ...]:
    """`__table_args__` for a tenant table: the (tenant_id, id) unique key that tenant-aware FKs point at."""
    return (UniqueConstraint("tenant_id", "id"), *extra)


def tenant_fk(column: str, target: str, *, name: str | None = None) -> ForeignKeyConstraint:
    """Tenant-aware FK `(tenant_id, column) → target(tenant_id, id)`, ON DELETE RESTRICT (no cross-tenant links)."""
    target = target if "." in target else f"{APP_SCHEMA}.{target}"
    return ForeignKeyConstraint(
        ["tenant_id", column], [f"{target}.tenant_id", f"{target}.id"], ondelete="RESTRICT", name=name
    )


class HardDeleteRefused(RuntimeError):
    pass


@event.listens_for(Session, "before_flush")
def _refuse_hard_deletes(session: Session, *_: Any) -> None:
    if session.deleted:
        names = sorted({type(obj).__name__ for obj in session.deleted})
        raise HardDeleteRefused(f"Hard delete refused for {', '.join(names)}: use soft_delete() (CLAUDE.md rule 6)")

"""Public form addresses across workspaces (migration 0016): the platform functions behind a form's key on the
shared forms host and its short link. Writes are always for the workspace of the current transaction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.links.urls import new_short_code


@dataclass(frozen=True)
class Resolved:
    tenant_id: uuid.UUID
    organisation_id: uuid.UUID
    subdomain: str
    status: str
    form_id: uuid.UUID


async def register_form_key(db: AsyncSession, key: str, form_id: uuid.UUID) -> None:
    await db.execute(text("SELECT platform.register_form_key(:k, :f)"), {"k": key, "f": form_id})


async def claim_new_short_code(db: AsyncSession, form_id: uuid.UUID) -> str:
    """A code no form of any organisation has ever had."""
    while True:
        code = new_short_code()
        if (await db.execute(text("SELECT platform.claim_short_code(:c, :f)"), {"c": code, "f": form_id})).scalar_one():
            return code


async def retire_short_code(db: AsyncSession, code: str) -> None:
    await db.execute(text("SELECT platform.retire_short_code(:c)"), {"c": code})


async def _resolve(db: AsyncSession, function: str, value: str) -> Resolved | None:
    row = (await db.execute(text(f"SELECT * FROM platform.{function}(:v)"), {"v": value})).first()
    return Resolved(*row) if row else None


async def resolve_form_key(db: AsyncSession, key: str) -> Resolved | None:
    return await _resolve(db, "resolve_form_key", key)


async def resolve_short_code(db: AsyncSession, code: str) -> Resolved | None:
    return await _resolve(db, "resolve_short_code", code)

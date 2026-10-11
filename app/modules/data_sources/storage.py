"""Responses stored in customers' databases (filled in by B9 step 2)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def forms_on_connections(db: AsyncSession, tenant_id: uuid.UUID,
                               ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict[str, str]]]:
    """Forms storing their responses on each connection."""
    return {}

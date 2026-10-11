"""Responses stored in customers' databases: which forms send their responses to each connection (the connection
panel lists them; deleting a connection is refused while any do)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def forms_on_connections(db: AsyncSession, tenant_id: uuid.UUID,
                               ids: list[uuid.UUID]) -> dict[uuid.UUID, list[dict[str, str]]]:
    """Forms storing their responses on each connection."""
    from app.modules.destinations.models import ResponseDestination
    from app.modules.forms.models import Form

    if not ids:
        return {}
    rows = (await db.execute(select(ResponseDestination.datasource_id, Form.id, Form.name).join(
        Form, (Form.tenant_id == ResponseDestination.tenant_id) & (Form.id == ResponseDestination.form_id)).where(
        ResponseDestination.tenant_id == tenant_id, ResponseDestination.datasource_id.in_(ids),
        ResponseDestination.deleted_at.is_(None)).order_by(Form.name))).all()
    out: dict[uuid.UUID, list[dict[str, str]]] = {}
    for datasource_id, form_id, name in rows:
        out.setdefault(datasource_id, []).append({"id": str(form_id), "name": name})
    return out

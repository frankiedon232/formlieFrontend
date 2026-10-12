"""Erasing responses without hard deletes (B11; 03-DECISIONS 2026-10-12 "Privacy erasure: redact in place"): a
person's data request (Settings → Privacy) and response retention remove the personal data and keep the row.

Each response: its answers become `{}`, the respondent's name and emails, IP address, browser, device, country and
fingerprint are cleared, then it is deleted like a delete in the portal (`deleted_at`), with the form's count, the
`response.deleted` event and the webhooks' `response.deleted` (ids only). Its notes are emptied and deleted, the
answers in its edit history cleared, its respondent files removed from storage (the upload rows stay, deleted, with
the file name cleared), and the bodies of webhook deliveries about it cleared. The row, its number and relations,
and the audit entry stay.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import null, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import record_event
from app.modules.forms.models import Form
from app.modules.responses.models import Response, ResponseChange, ResponseNote


async def erase(db: AsyncSession, forms: dict[uuid.UUID, Form], responses: list[Response], by: uuid.UUID | None) -> int:
    """→ how many were erased. The caller audits (settings.data_deleted / settings.retention_applied)."""
    from app.core import storage
    from app.modules.uploads.models import Upload
    from app.modules.webhooks.service import forget_response_bodies, response_event

    if not responses:
        return 0
    now = datetime.now(UTC)
    ids = [r.id for r in responses]
    counts: dict[uuid.UUID, int] = {}
    for r in responses:
        form = forms[r.form_id]
        await record_event(db, "response.deleted", {"form_id": str(form.id), "response_id": str(r.id),
                                                    "submitted_at": r.submitted_at.astimezone(UTC).isoformat()})
        await response_event(db, "response.deleted", form, r)
        r.data, r.respondent_email, r.respondent_name, r.identity_email = {}, None, None, None
        r.ip, r.user_agent, r.device, r.country, r.device_hash, r.fingerprint = None, None, None, None, None, ""
        r.possible_duplicate, r.tags = None, []
        if r.deleted_at is None:
            r.deleted_at, r.deleted_by = now, by
            counts[r.form_id] = counts.get(r.form_id, 0) + 1
        r.updated_at, r.updated_by = now, by
    for form_id, n in counts.items():
        await db.execute(update(Form).where(Form.id == form_id, Form.tenant_id == forms[form_id].tenant_id)
                         .values(responses_count=func_greatest(Form.responses_count - n)))
    tenant_id = responses[0].tenant_id
    await db.execute(update(ResponseNote).where(ResponseNote.tenant_id == tenant_id, ResponseNote.response_id.in_(ids))
                     .values(text="", deleted_at=now, deleted_by=by))
    await db.execute(update(ResponseChange).where(ResponseChange.tenant_id == tenant_id,
                                                  ResponseChange.response_id.in_(ids)).values(before=null(), after=null()))
    files: list[Any] = list((await db.execute(Upload.__table__.select().where(
        Upload.tenant_id == tenant_id, Upload.response_id.in_(ids)))).mappings())
    for file in files:
        if file["file_key"]:
            try:
                storage.remove(file["file_key"])
            except OSError:
                pass
    if files:
        await db.execute(update(Upload).where(Upload.tenant_id == tenant_id, Upload.response_id.in_(ids))
                         .values(file_name="removed", file_key=None, deleted_at=now, deleted_by=by))
    await forget_response_bodies(db, tenant_id, ids)
    await db.flush()
    return len(responses)


def func_greatest(value: Any) -> Any:
    from sqlalchemy import func

    return func.greatest(value, 0)

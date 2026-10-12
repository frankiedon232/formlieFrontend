"""Privacy and data (port of the mock's data/retentionStore.ts; Settings → Privacy and data).

- A person's responses: their respondent email, or an answer that is exactly that address, in the workspace's forms
  (forms in the trash and deleted responses don't count).
- Export: everything about them, readable (form, number, when, language, answers by question).
- Delete: erased in place (app/modules/responses/erase.py): the answers and personal fields are cleared, the row,
  its relations and the audit entry stay (no hard deletes; 03-DECISIONS 2026-10-12). Their saved drafts and the
  emails sent to them (sent log) are cleared too.
- Retention: responses older than their form's limit (the form's own, else the workspace's) are erased the same way,
  when the setting is saved and once a day (Beat `privacy.apply_retention`).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import Actor, record
from app.modules.forms.models import Form
from app.modules.forms.schema import all_fields
from app.modules.responses.answers import answer_text
from app.modules.responses.models import Response
from app.modules.responses.service import respondent_from, response_schema
from app.modules.settings.service import get_section

BATCH = 500


def normalise(email: str) -> str:
    return email.strip().lower()


def masked(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}•••@{domain}"


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _like(value: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", json.dumps(value, ensure_ascii=False)[1:-1]) + "%"


async def _forms(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, Form]:
    rows = (await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.deleted_at.is_(None),
                                                Form.purged_at.is_(None)))).scalars().all()
    return {f.id: f for f in rows}


async def person_responses(db: AsyncSession, tenant_id: uuid.UUID, email: str) -> tuple[
        dict[uuid.UUID, Form], dict[uuid.UUID, Any], list[Response]]:
    """(forms, their schemas, the person's responses, oldest first)."""
    wanted = normalise(email)
    forms = await _forms(db, tenant_id)
    if not forms:
        return forms, {}, []
    candidates = (await db.execute(select(Response).where(
        Response.tenant_id == tenant_id, Response.deleted_at.is_(None), Response.form_id.in_(list(forms)),
        or_(func.lower(Response.respondent_email) == wanted, func.lower(Response.identity_email) == wanted,
            func.lower(cast(Response.data, Text)).like(_like(wanted), escape="\\")),
    ).order_by(Response.submitted_at))).scalars().all()
    schemas: dict[uuid.UUID, Any] = {}
    found: list[Response] = []
    for r in candidates:
        form = forms[r.form_id]
        if r.form_id not in schemas:
            schemas[r.form_id] = await response_schema(db, form)
        data = r.data or {}
        own = respondent_from(schemas[r.form_id], data, r).get("email")
        if (isinstance(own, str) and normalise(own) == wanted) or normalise(r.identity_email or "") == wanted \
                or any(isinstance(v, str) and normalise(v) == wanted for v in data.values()):
            found.append(r)
    return forms, schemas, found


async def search(db: AsyncSession, tenant_id: uuid.UUID, email: str) -> dict[str, Any]:
    forms, _, found = await person_responses(db, tenant_id, email)
    by_form: dict[uuid.UUID, dict[str, Any]] = {}
    for r in found:
        item = by_form.setdefault(r.form_id, {"id": str(r.form_id), "name": forms[r.form_id].name, "count": 0,
                                              "latest": iso(r.submitted_at), "_at": r.submitted_at})
        item["count"] += 1
        if r.submitted_at > item["_at"]:
            item["latest"], item["_at"] = iso(r.submitted_at), r.submitted_at
    listed = sorted(by_form.values(), key=lambda i: -i["count"])
    return {"email": normalise(email), "total": len(found),
            "forms": [{k: v for k, v in i.items() if k != "_at"} for i in listed]}


async def export(db: AsyncSession, tenant_id: uuid.UUID, email: str) -> dict[str, Any]:
    forms, schemas, found = await person_responses(db, tenant_id, email)
    out = []
    for r in found:
        data = r.data or {}
        fields = [f for f in all_fields(schemas.get(r.form_id)) if f.get("key") in data]
        out.append({"form": forms[r.form_id].name, "number": r.number, "submitted_at": iso(r.submitted_at),
                    "language": r.language,
                    "answers": {(str(f.get("label") or "").strip() or f["key"]): answer_text(f, data[f["key"]])
                                for f in fields}})
    return {"email": normalise(email), "exported_at": iso(datetime.now(UTC)), "responses": out}


async def erase_person(db: AsyncSession, tenant_id: uuid.UUID, email: str, by: uuid.UUID | None) -> dict[str, int]:
    from app.modules.emails.workspace import forget_address
    from app.modules.public.service import forget_drafts
    from app.modules.responses.erase import erase

    forms, _, found = await person_responses(db, tenant_id, email)
    await erase(db, forms, found, by)
    await forget_drafts(db, tenant_id, email, by)
    await forget_address(db, tenant_id, email, masked(normalise(email)))
    return {"responses": len(found), "forms": len({r.form_id for r in found})}


# ── Retention ─────────────────────────────────────────────────────────────────────

async def _limits(db: AsyncSession, tenant_id: uuid.UUID, override: int | None) -> list[tuple[Form, int]]:
    """Every form with the days its responses are kept (the form's own, else the override, else the workspace's)."""
    workspace = int((await get_section(db, tenant_id, "privacy")).get("retention_days") or 0)
    out = []
    for form in (await _forms(db, tenant_id)).values():
        schema = await response_schema(db, form)
        own = ((schema or {}).get("settings") or {}).get("retention_days")
        days = own if own is not None else (override if override is not None else workspace)
        out.append((form, int(days or 0)))
    return out


async def preview(db: AsyncSession, tenant_id: uuid.UUID, days: int) -> dict[str, Any]:
    """What that limit would remove now (RetentionPreview)."""
    now = datetime.now(UTC)
    responses, forms, newest = 0, 0, None
    for form, limit in await _limits(db, tenant_id, days):
        if not limit:
            continue
        count, latest = (await db.execute(select(func.count(), func.max(Response.submitted_at)).where(
            Response.tenant_id == tenant_id, Response.form_id == form.id, Response.deleted_at.is_(None),
            Response.submitted_at < now - timedelta(days=limit)))).one()
        if count:
            responses, forms = responses + count, forms + 1
            newest = latest if newest is None or latest > newest else newest
    return {"days": days, "responses": responses, "forms": forms, "oldest_kept": iso(newest) if newest else None}


async def apply_retention(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID,
                          user: Any = None) -> int:
    """Erases what is past its limit; `user` when someone saved the setting (else Formalie, daily) → how many."""
    from app.modules.responses.erase import erase

    now = datetime.now(UTC)
    removed, touched = 0, 0
    for form, limit in await _limits(db, tenant_id, None):
        if not limit:
            continue
        erased_here = 0
        while True:
            batch = (await db.execute(select(Response).where(
                Response.tenant_id == tenant_id, Response.form_id == form.id, Response.deleted_at.is_(None),
                Response.submitted_at < now - timedelta(days=limit)).order_by(Response.submitted_at).limit(BATCH)
            )).scalars().all()
            if not batch:
                break
            erased_here += await erase(db, {form.id: form}, list(batch), user.id if user is not None else None)
        if erased_here:
            removed, touched = removed + erased_here, touched + 1
    if removed:
        await record(db, tenant_id=tenant_id, organisation_id=organisation_id, action="settings.retention_applied",
                     actor=Actor.user(user) if user is not None else Actor.system(),
                     resource={"type": "setting", "id": None, "name": "Privacy and data"},
                     metadata={"responses": str(removed), "forms": str(touched)})
    return removed

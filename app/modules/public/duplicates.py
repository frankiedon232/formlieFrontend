"""The same or a near email on submit (decision 85; query review Q2), for the form page and the API gateway.

`rules.match_identity` decides, exactly as before; this only chooses which earlier responses it needs to see, from
`identity_email` (the respondent's own email, normalised at submit and kept in step when answers are edited), read
through ix_responses_identity_live, never every response's answers:

- **Same email:** one index lookup, newest first, `LIMIT 1`.
- **Near email:** a near email (`rules.emails_near`) is at most 1 edit away in the domain and at most 2 in the name
  part, and an edit changes a length by at most 1, so only emails whose name part is within 2 characters of this
  length and whose domain is within 1 can match. Those candidates are read in pages of `PAGE`, newest first; the
  answers (for the name comparison and the masked hint) are read only for candidates that pass `emails_near`, and
  the first page with a match ends the search. The answer is the one the whole list gave: the newest near
  response whose name is similar.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public import rules
from app.modules.responses.models import Response

PAGE = 500


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def _records(db: AsyncSession, live: tuple[Any, ...], ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    """{ id, submitted_at, data } of these responses, newest first (the shape match_identity reads)."""
    if not ids:
        return []
    rows = (await db.execute(select(Response.id, Response.submitted_at, Response.data)
                             .where(*live, Response.id.in_(ids))
                             .order_by(Response.submitted_at.desc(), Response.id.desc()))).all()
    return [{"id": str(r.id), "submitted_at": _iso(r.submitted_at), "data": r.data} for r in rows]


async def match_earlier(db: AsyncSession, tenant_id: uuid.UUID, form_id: uuid.UUID, schema: dict[str, Any],
                        answers: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """rules.match_identity against the form's live responses: { level: none | likely | clear, reason?, record? }."""
    key = identity.get("email")
    email = rules.normalise_email(answers.get(key)) if key else None
    if not key or not email:
        return {"level": "none"}
    live = (Response.tenant_id == tenant_id, Response.form_id == form_id, Response.deleted_at.is_(None))
    newest = (Response.submitted_at.desc(), Response.id.desc())
    same = (await db.execute(select(Response.id).where(*live, Response.identity_email == email)
                             .order_by(*newest).limit(1))).scalar_one_or_none()
    if same is not None:
        return {"level": "clear", "reason": "email", "record": (await _records(db, live, [same]))[0]}

    local, domain = email.split("@", 1)
    name_len, domain_len = func.length(func.split_part(Response.identity_email, "@", 1)), \
        func.length(func.split_part(Response.identity_email, "@", 2))
    candidates = select(Response.id, Response.submitted_at, Response.identity_email).where(
        *live, Response.identity_email.is_not(None), Response.identity_email != email,
        name_len.between(len(local) - 2, len(local) + 2), domain_len.between(len(domain) - 1, len(domain) + 1),
    ).order_by(*newest).limit(PAGE)
    after: tuple[datetime, uuid.UUID] | None = None
    while True:
        page = candidates if after is None else candidates.where(or_(
            Response.submitted_at < after[0], and_(Response.submitted_at == after[0], Response.id < after[1])))
        rows = (await db.execute(page)).all()
        near = [r.id for r in rows if rules.emails_near(email, r.identity_email)]
        if near:
            match = rules.match_identity(schema, answers, await _records(db, live, near), identity)
            if match["level"] != "none":
                return match
        if len(rows) < PAGE:
            return {"level": "none"}
        after = (rows[-1].submitted_at, rows[-1].id)


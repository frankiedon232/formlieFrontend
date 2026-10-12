"""What the dashboard views and analytics share: the workspace's time zone and days, the forms a person may see
(folder access, sharing, role) with the dashboard's filter, and responses counted per form and day in SQL.

A day is a day in the workspace's time zone (Settings → Localisation, UTC when unset). Responses are counted in the
database (grouped by form and day); nothing reads them one by one.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_context
from app.modules.auth.sessions import Principal
from app.modules.dashboard.rules import Scope, date_of, day_of, scope_from
from app.modules.forms import access
from app.modules.forms.access import Viewer
from app.modules.forms.models import Form


def scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


# ── Days in the workspace's time zone ───────────────────────────────────────────

class Clock:
    """The workspace's time zone: today, where a day starts, and the day of a moment (in SQL)."""

    def __init__(self, name: str | None) -> None:
        try:
            self.zone = ZoneInfo(name or "UTC")
            self.name = name or "UTC"
        except Exception:  # noqa: BLE001 (an unknown zone: UTC)
            self.zone, self.name = ZoneInfo("UTC"), "UTC"

    def today(self) -> int:
        return day_of(datetime.now(self.zone).date())

    def starts(self, day: int) -> datetime:
        """The moment a day starts (clamped to the dates Python holds)."""
        return datetime.combine(date_of(day), time.min, tzinfo=self.zone).astimezone(UTC)

    def day_of(self, moment: datetime) -> int:
        return day_of(moment.astimezone(self.zone).date())

    def sql_day(self, column: Any) -> Any:
        return cast(func.timezone(self.name, column), Date)


async def clock_of(db: AsyncSession, tenant_id: uuid.UUID) -> Clock:
    from app.modules.settings.service import get_section

    return Clock((await get_section(db, tenant_id, "localisation")).get("timezone"))


# ── Forms this person may see, with the filter ──────────────────────────────────

def filter_of(query: dict[str, Any]) -> Scope:
    """scopeFrom(), where an id counts only when it came in as a reference (anything else matches no form)."""
    wanted = scope_from(query)
    ctx = get_context()
    known = {i.lower() for i in (ctx.ref_ids if ctx else set())}

    def checked(value: str | None, none_ok: bool) -> str | None:
        if value is None or (none_ok and value == "none") or value.lower() in known:
            return value
        return "\x00unknown"
    return Scope(checked(wanted.folder, True), checked(wanted.owner, False))


def form_folder(form: Form, viewer: Viewer) -> str | None:
    return str(form.folder_id) if form.folder_id and form.folder_id in viewer.folders else None


async def visible_forms(db: AsyncSession, viewer: Viewer, tenant_id: uuid.UUID) -> list[Form]:
    """Forms that exist (not in Trash) and this person may see."""
    from app.modules.forms.service import forms_of

    return [f for f in await forms_of(db, tenant_id) if f.deleted_at is None and access.can_see(f, viewer)]


def with_responses(forms: list[Form], viewer: Viewer) -> list[Form]:
    """Of those, the forms whose responses this person may see."""
    return [f for f in forms if access.responses_allowed(f, viewer, "view")]


# ── Responses, counted in the database ──────────────────────────────────────────

async def responses_per_day(db: AsyncSession, tenant_id: uuid.UUID, form_ids: list[uuid.UUID], clock: Clock,
                            start: int, end: int) -> dict[uuid.UUID, dict[int, int]]:
    """Responses per form and day, from `start` to `end` (days, both included)."""
    from app.modules.responses.models import Response

    if not form_ids:
        return {}
    day = clock.sql_day(Response.submitted_at)
    rows = (await db.execute(select(Response.form_id, day, func.count()).where(
        Response.tenant_id == tenant_id, Response.form_id.in_(form_ids), Response.deleted_at.is_(None),
        Response.submitted_at >= clock.starts(start), Response.submitted_at < clock.starts(end + 1))
        .group_by(Response.form_id, day))).all()
    out: dict[uuid.UUID, dict[int, int]] = {}
    for form_id, on, count in rows:
        out.setdefault(form_id, {})[day_of(on)] = count
    return out


async def to_review(db: AsyncSession, tenant_id: uuid.UUID, form_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Responses still `new` per form (whenever they came)."""
    from app.modules.responses.models import Response

    if not form_ids:
        return {}
    return dict((await db.execute(select(Response.form_id, func.count()).where(
        Response.tenant_id == tenant_id, Response.form_id.in_(form_ids), Response.deleted_at.is_(None),
        Response.status == "new").group_by(Response.form_id))).all())


async def channels(db: AsyncSession, tenant_id: uuid.UUID, form_ids: list[uuid.UUID], clock: Clock, start: int,
                   end: int) -> dict[str, int]:
    """Responses in the period by how they came in."""
    from app.modules.responses.models import Response

    out = {"link": 0, "embed": 0, "api": 0}
    if not form_ids:
        return out
    for channel, count in (await db.execute(select(Response.channel, func.count()).where(
            Response.tenant_id == tenant_id, Response.form_id.in_(form_ids), Response.deleted_at.is_(None),
            Response.submitted_at >= clock.starts(start), Response.submitted_at < clock.starts(end + 1))
            .group_by(Response.channel))).all():
        if channel in out:
            out[channel] += count
    return out


async def median_seconds(db: AsyncSession, tenant_id: uuid.UUID, form_ids: list[uuid.UUID], clock: Clock, start: int,
                         end: int, *, per_form: bool = False) -> dict[uuid.UUID | None, float]:
    """The median time to fill in (seconds, the middle one or the mean of the two middle ones), of all the forms
    together (key None) or per form."""
    from app.modules.responses.models import Response

    if not form_ids:
        return {}
    median = func.percentile_cont(0.5).within_group(Response.duration_seconds)
    where = (Response.tenant_id == tenant_id, Response.form_id.in_(form_ids), Response.deleted_at.is_(None),
             Response.duration_seconds.is_not(None), Response.submitted_at >= clock.starts(start),
             Response.submitted_at < clock.starts(end + 1))
    if per_form:
        rows = (await db.execute(select(Response.form_id, median).where(*where).group_by(Response.form_id))).all()
        return {form_id: float(value) for form_id, value in rows if value is not None}
    value = (await db.execute(select(median).where(*where))).scalar_one_or_none()
    return {None: float(value)} if value is not None else {}

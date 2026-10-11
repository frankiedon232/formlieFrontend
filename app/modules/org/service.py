"""Organisation data (mock: data/orgStore.ts): reading entries with their people, and saving the people in one.

Forms restrict fields to departments and job titles (field access). Forms arrive in B5; until then no entry is used
by a form (`usage_of` is empty, `forms_count` 0) and merging moves no fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.org.models import OrgUnit, OrgUnitMember
from app.modules.users.models import User

LABEL = {"departments": "Department", "job_titles": "Job title"}


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


async def people_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, str]]:
    """peopleOf(): everyone on the People page except disabled accounts (invited people count too)."""
    users = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                 User.status != "disabled").order_by(User.created_at, User.id))).scalars()
    return [{"id": str(u.id), "name": f"{u.first_name} {u.last_name}".strip() or u.email, "email": u.email} for u in users]


async def units_of(db: AsyncSession, tenant_id: uuid.UUID, kind: str) -> list[OrgUnit]:
    return list((await db.execute(select(OrgUnit).where(OrgUnit.tenant_id == tenant_id, OrgUnit.kind == kind,
                                                        OrgUnit.deleted_at.is_(None))
                                  .order_by(OrgUnit.created_at, OrgUnit.id))).scalars())


async def members_of(db: AsyncSession, tenant_id: uuid.UUID, unit_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """Each entry's people, in the order they were added."""
    out: dict[uuid.UUID, list[str]] = {uid: [] for uid in unit_ids}
    if not unit_ids:
        return out
    rows = await db.execute(select(OrgUnitMember.org_unit_id, OrgUnitMember.user_id).where(
        OrgUnitMember.tenant_id == tenant_id, OrgUnitMember.org_unit_id.in_(unit_ids),
        OrgUnitMember.deleted_at.is_(None)).order_by(OrgUnitMember.created_at, OrgUnitMember.id))
    for unit_id, user_id in rows:
        out[unit_id].append(str(user_id))
    return out


def usage_of(kind: str, unit_id: uuid.UUID) -> list[dict[str, Any]]:  # noqa: ARG001
    """Forms with a field restricted to this entry, and those fields' labels (forms: B5)."""
    return []


def move_audience(kind: str, from_ids: list[uuid.UUID], into: uuid.UUID) -> int:  # noqa: ARG001
    """Fields restricted to `from_ids` are restricted to `into` instead (forms: B5). → fields moved."""
    return 0


def to_item(kind: str, unit: OrgUnit, member_ids: list[str], people: list[dict[str, str]]) -> dict[str, Any]:
    """OrgItem (shared/types/org.ts)."""
    by_id = {p["id"]: p for p in people}
    return {
        "id": str(unit.id), "kind": kind, "name": unit.name, "code": unit.code, "description": unit.description,
        "status": "archived" if unit.archived_at else "active",
        "members": [by_id[m] for m in member_ids if m in by_id],
        "forms_count": len(usage_of(kind, unit.id)),
        "created_at": _iso(unit.created_at), "updated_at": _iso(unit.updated_at), "archived_at": _iso(unit.archived_at),
    }


async def set_members(db: AsyncSession, unit: OrgUnit, member_ids: list[str], by: uuid.UUID) -> None:
    """The entry's people become exactly these (people taken out keep their row, with deleted_at)."""
    current = (await db.execute(select(OrgUnitMember).where(
        OrgUnitMember.tenant_id == unit.tenant_id, OrgUnitMember.org_unit_id == unit.id,
        OrgUnitMember.deleted_at.is_(None)))).scalars().all()
    wanted = list(dict.fromkeys(member_ids))
    now = datetime.now(UTC)
    for row in current:
        if str(row.user_id) not in wanted:
            row.deleted_at, row.deleted_by = now, by
    have = {str(row.user_id) for row in current}
    for user_id in wanted:
        if user_id not in have:
            db.add(OrgUnitMember(tenant_id=unit.tenant_id, organisation_id=unit.organisation_id, org_unit_id=unit.id,
                                 user_id=uuid.UUID(user_id), created_by=by))
    await db.flush()


async def set_person_units(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, user_id: uuid.UUID,
                           kind: str, ids: list[str], by: uuid.UUID) -> dict[str, Any] | None:
    """setMemberships(): the person is in exactly these active entries of a kind (archived ones are left as they
    are) → the audit change (names before and after), or None when nothing changed."""
    units = await units_of(db, tenant_id, kind)
    members = await members_of(db, tenant_id, [u.id for u in units])
    before = [u.name for u in units if str(user_id) in members[u.id]]
    now = datetime.now(UTC)
    for unit in units:
        wanted = str(unit.id) in ids and not unit.archived_at
        has = str(user_id) in members[unit.id]
        if wanted and not has:
            db.add(OrgUnitMember(tenant_id=tenant_id, organisation_id=organisation_id, org_unit_id=unit.id,
                                 user_id=user_id, created_by=by))
            members[unit.id].append(str(user_id))
        elif not wanted and has and not unit.archived_at:
            for row in (await db.execute(select(OrgUnitMember).where(
                    OrgUnitMember.tenant_id == tenant_id, OrgUnitMember.org_unit_id == unit.id,
                    OrgUnitMember.user_id == user_id, OrgUnitMember.deleted_at.is_(None)))).scalars():
                row.deleted_at, row.deleted_by = now, by
            members[unit.id].remove(str(user_id))
    await db.flush()
    after = [u.name for u in units if str(user_id) in members[u.id]]
    if before == after:
        return None
    return {"field": kind, "before": ", ".join(before) or None, "after": ", ".join(after) or None}


async def leave_all(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, by: uuid.UUID) -> None:
    """Someone removed from the workspace leaves every entry (their rows keep deleted_at)."""
    now = datetime.now(UTC)
    for row in (await db.execute(select(OrgUnitMember).where(
            OrgUnitMember.tenant_id == tenant_id, OrgUnitMember.user_id == user_id,
            OrgUnitMember.deleted_at.is_(None)))).scalars():
        row.deleted_at, row.deleted_by = now, by

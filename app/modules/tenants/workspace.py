"""Making a workspace, in one transaction (BACKEND-SPEC §7, DATABASE-DESIGN → Seeded default data):
the directory row (platform.create_tenant), the primary organisation, the built-in roles, the default settings
sections, onboarding and the founding person as Owner. Used by sign-up and by the development seed.

The rest of Formalie's default data (FRONTEND-REFERENCE → Default data) is seeded by each module as it is built:
the module registers a seeder with `register_seeder`, and every new workspace runs them all in the same
transaction (default folders: B5, email templates: B11). Formalie's templates are a catalogue in code
(app/modules/templates), not rows; the sample lists go to the seeded development workspaces only (scripts/seed_dev.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import set_rls_context
from app.core.errors import FrmError
from app.core.ids import uuid7
from app.modules.onboarding.state import SECTION, new_state
from app.modules.rbac.service import built_in_roles
from app.modules.settings.service import defaults, seed_rows
from app.modules.tenants.models import Organisation
from app.modules.users.models import User


@dataclass(frozen=True, slots=True)
class Founder:
    first_name: str
    last_name: str
    email: str
    password_hash: str | None


@dataclass(frozen=True, slots=True)
class NewWorkspace:
    tenant_id: uuid.UUID
    organisation_id: uuid.UUID
    owner_id: uuid.UUID | None
    subdomain: str
    name: str


async def create_workspace(
    session: AsyncSession,
    *,
    name: str,
    subdomain: str,
    founder: Founder | None,
    plan_id: str = "starter",
    signin_methods: list[str] | None = None,
    website: str | None = None,
    tenant_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    onboarding: bool = True,
) -> NewWorkspace:
    """Inside the caller's transaction; leaves the session's RLS context on the new workspace."""
    tenant_id = tenant_id or uuid7()
    organisation_id = organisation_id or uuid7()
    owner_id = (owner_id or uuid7()) if founder else None
    try:
        async with session.begin_nested():
            await session.execute(text("SELECT platform.create_tenant(:id, :sub, :name, :org, :plan)"),
                                  {"id": tenant_id, "sub": subdomain, "name": name, "org": organisation_id, "plan": plan_id})
    except IntegrityError as exc:
        raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "This subdomain is taken."}]) from exc

    await set_rls_context(session, tenant_id, organisation_id, owner_id)
    session.add(Organisation(id=organisation_id, tenant_id=tenant_id, organisation_id=organisation_id, name=name,
                             legal_name=name, is_primary=True))
    roles = built_in_roles(tenant_id, organisation_id)
    session.add_all(roles)
    sections = defaults(name=name, website=website, signin_methods=signin_methods)
    if onboarding:  # the seeded workspaces count as set up (no onboarding row)
        sections[SECTION] = new_state()
    session.add_all(seed_rows(tenant_id, organisation_id, sections))
    await session.flush()
    if founder is None:  # Formalie's own workspace: nobody signs in to it
        made = NewWorkspace(tenant_id, organisation_id, None, subdomain, name)
        for seeder in _SEEDERS:
            await seeder(session, made)
        return made
    owner_role = next(r for r in roles if r.built_in == "owner")
    now = datetime.now(UTC)
    session.add(User(id=owner_id, tenant_id=tenant_id, organisation_id=organisation_id, email=founder.email.lower(),
                     first_name=founder.first_name, last_name=founder.last_name, status="active", role_id=owner_role.id,
                     password_hash=founder.password_hash, password_changed_at=now if founder.password_hash else None,
                     joined_at=now, created_by=owner_id))
    await session.flush()
    made = NewWorkspace(tenant_id, organisation_id, owner_id, subdomain, name)
    for seeder in _SEEDERS:
        await seeder(session, made)
    return made


# A module's default data for every new workspace: async seeder(session, workspace), in the workspace's RLS context.
Seeder = Callable[[AsyncSession, NewWorkspace], Awaitable[None]]
_SEEDERS: list[Seeder] = []


def register_seeder(seeder: Seeder) -> Seeder:
    _SEEDERS.append(seeder)
    return seeder

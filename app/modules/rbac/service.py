"""Roles of a workspace (port of the mock's data/rolesStore.ts). Every workspace starts with Owner (everything,
can't be changed or deleted), Admin and Member (editable defaults); a person holds one role."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rbac.catalogue import ALL_PERMISSIONS, BUILT_IN_ROLE_TEXT, BUILT_IN_ROLES, DEFAULT_ROLE_GRANTS
from app.modules.rbac.permissions import ALL_GRANTS, OWNER_ROLE, Grants, with_needs
from app.modules.users.models import Role


def built_in_roles(tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> list[Role]:
    return [
        Role(tenant_id=tenant_id, organisation_id=organisation_id, name=BUILT_IN_ROLE_TEXT[key]["name"],
             description=BUILT_IN_ROLE_TEXT[key]["description"], built_in=key, grants=dict(DEFAULT_ROLE_GRANTS[key]))
        for key in BUILT_IN_ROLES
    ]


async def role_by_key(session: AsyncSession, key: str) -> Role | None:
    """A built-in role by its key (owner · admin · member) in the workspace of the session's context."""
    return (await session.execute(
        select(Role).where(Role.built_in == key, Role.deleted_at.is_(None))
    )).scalar_one_or_none()


def grants_of(role: Role | None) -> Grants:
    """What a role allows, with each action's scope. Owner holds everything there is (new actions included);
    a role that is gone gives nothing (grantsOf)."""
    if role is None or role.deleted_at is not None:
        return {}
    if role.built_in == OWNER_ROLE:
        return dict(ALL_GRANTS)
    return with_needs(role.grants or {})


def permissions_of(grants: Grants) -> list[str]:
    """The actions held, whatever their scope, in catalogue order (permissionsOf)."""
    return [p for p in ALL_PERMISSIONS if grants.get(p)]


def role_key(role: Role | None) -> str:
    """The role as the app knows it: owner · admin · member, or the workspace role's id."""
    if role is None:
        return ""
    return role.built_in or str(role.id)


def role_name(role: Role | None) -> str:
    return role.name if role is not None else ""


async def find_role(session: AsyncSession, tenant_id: uuid.UUID, key: str | None) -> Role | None:
    """A role by what the app calls it: owner · admin · member, or a workspace role's id."""
    if not key:
        return None
    if key in BUILT_IN_ROLES:
        query = select(Role).where(Role.tenant_id == tenant_id, Role.built_in == key, Role.deleted_at.is_(None))
    else:
        try:
            wanted = uuid.UUID(key)
        except ValueError:
            return None
        query = select(Role).where(Role.tenant_id == tenant_id, Role.id == wanted, Role.deleted_at.is_(None))
    return (await session.execute(query)).scalar_one_or_none()


async def roles_of(session: AsyncSession, tenant_id: uuid.UUID) -> list[Role]:
    """Owner, Admin, Member, then the workspace's own in the order they were made."""
    order = {key: i for i, key in enumerate(BUILT_IN_ROLES)}
    roles = (await session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.deleted_at.is_(None))
                                   .order_by(Role.created_at, Role.id))).scalars().all()
    return sorted(roles, key=lambda r: order.get(r.built_in or "", len(order)))

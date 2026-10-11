"""Which sign-in methods a workspace offers (owner, 2026-10-11).

Someone who came in with Google, Microsoft or Facebook keeps signing in that way, with no password, whatever the plan:
the plan's social sign-in feature only decides whether the workspace may add those methods for other people. So a
social method is offered when the workspace has it switched on and either the plan includes social sign-in or
someone in the workspace already has that provider linked (the Owner who signed up with it, typically). At the
callback, without the plan, only a person whose own account is linked to that provider gets in.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.service import has_feature
from app.modules.settings.service import SIGNIN_METHODS
from app.modules.users.models import User, UserIdentity


async def linked_providers(db: AsyncSession, tenant_id: uuid.UUID) -> set[str]:
    """Providers linked to at least one person of the workspace (not removed)."""
    rows = await db.execute(
        select(UserIdentity.provider).join(User, (User.id == UserIdentity.user_id) & (User.tenant_id == UserIdentity.tenant_id))
        .where(UserIdentity.tenant_id == tenant_id, UserIdentity.deleted_at.is_(None), User.deleted_at.is_(None))
        .distinct())
    return set(rows.scalars())


def offered_methods(signin: dict[str, Any], plan_id: str | None, linked: set[str]) -> list[str]:
    """The sign-in page's buttons, in the settings' order (methods that no longer exist, such as Apple, dropped)."""
    social = has_feature(plan_id, "social_signin")
    methods = [m for m in signin["methods"] if m in SIGNIN_METHODS and (m == "password" or social or m in linked)]
    return methods or ["password"]

"""Who may change an item of a workspace library (mock: data/resourceAccess.ts; F22 R2 M3): templates, lists,
themes, page designs and saved fields. Formalie's own items are use-only for everyone in a workspace; otherwise the
role's grant for `<area>.edit` / `<area>.delete` and its scope: own (they made it) · all."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.errors import FrmError


def _reach(area: str, action: str, created_by: uuid.UUID | None, principal: Any, system: bool) -> bool:
    if system:
        return False
    scope = principal.grants.get(f"{area}.{action}")
    return scope == "all" or (scope == "own" and created_by is not None and created_by == principal.user.id)


def resource_actions(area: str, created_by: uuid.UUID | None, principal: Any, *, system: bool = False) -> dict[str, bool]:
    """What this person may do with this item (sent with every row as `can`). Saved fields are never edited."""
    return {"edit": area != "fields" and _reach(area, "edit", created_by, principal, system),
            "delete": _reach(area, "delete", created_by, principal, system)}


def require_resource(area: str, action: str, created_by: uuid.UUID | None, principal: Any, *, system: bool = False) -> None:
    if not _reach(area, action, created_by, principal, system):
        raise FrmError("FRM-PERM-1001")


def owned_reach(permission: str, created_by: uuid.UUID | None, principal: Any) -> bool:
    """own · all for an action on an item that records its maker (data connections, API services)."""
    scope = principal.grants.get(permission)
    return scope == "all" or (scope == "own" and created_by is not None and created_by == principal.user.id)

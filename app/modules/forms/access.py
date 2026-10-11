"""Who may do what with a form (port of the mock's data/formPermissions.ts; F10 M3 people access, F22 R2 scopes).

One answer for every route and every list:

1. Folder access: a form in a folder the person may not see doesn't exist for them (lists, counts, search,
   responses, exports …). Owner, people who decide folder access, and those the folder is open to (roles,
   departments, people) see it.
2. The role's grant for the action (forms.rename, forms.publish …) and its scope:
     own     the person made the form
     shared  someone else's form shared with them at the level the action needs (their own level, else the
             form's team default)
     all     every form
   No grant: not even their own. Form sharing never goes beyond the role.

Too little → FRM-PERM-1001; can't see → FRM-GEN-1004, so a name never leaks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FrmError
from app.modules.auth.sessions import Principal
from app.modules.forms.catalogues import FORM_ACTIONS, RESPONSE_ACTIONS
from app.modules.forms.models import Folder, Form, FormGrant
from app.modules.org.models import OrgUnitMember
from app.modules.rbac.permissions import scope_parts
from app.modules.rbac.service import role_key

RANK = {"none": 0, "responses": 1, "view": 2, "edit": 3}

# The sharing level an action needs when the role reaches "shared" forms
LEVEL_FOR = {
    "view": "responses", "preview": "view", "share_view": "view", "duplicate": "view", "save_template": "edit",
    "rename": "edit", "edit": "edit", "versions": "edit", "share": "edit", "availability": "edit", "publish": "edit",
    "close": "edit", "archive": "edit", "move": "edit", "delete": "edit", "purge": "edit",
}
RESPONSE_LEVEL = {"view": "responses", "review": "responses", "export": "responses", "edit": "edit", "delete": "edit"}


@dataclass
class Viewer:
    """The signed-in person with what form access needs: role key, grants, departments, folders, sharing."""

    principal: Principal
    departments: set[str] = field(default_factory=set)
    folders: dict[uuid.UUID, Folder] = field(default_factory=dict)
    shared: dict[uuid.UUID, str] = field(default_factory=dict)  # form id → this person's own level

    @property
    def user_id(self) -> uuid.UUID:
        return self.principal.user.id

    @property
    def role(self) -> str:
        return role_key(self.principal.role)

    def scope(self, permission: str) -> str | None:
        return self.principal.grants.get(permission)

    def can(self, permission: str) -> bool:
        return bool(self.principal.grants.get(permission))


async def viewer_for(db: AsyncSession, principal: Principal) -> Viewer:
    """Everything access needs, read once per request."""
    tenant_id, user_id = principal.tenant.id, principal.user.id
    from app.modules.org.models import OrgUnit

    departments = {str(unit_id) for unit_id in (await db.execute(
        select(OrgUnitMember.org_unit_id).join(OrgUnit, OrgUnit.id == OrgUnitMember.org_unit_id).where(
            OrgUnitMember.tenant_id == tenant_id, OrgUnitMember.user_id == user_id, OrgUnitMember.deleted_at.is_(None),
            OrgUnit.kind == "departments", OrgUnit.deleted_at.is_(None)))).scalars()}
    folders = {f.id: f for f in (await db.execute(select(Folder).where(
        Folder.tenant_id == tenant_id, Folder.deleted_at.is_(None)))).scalars()}
    shared = {g.form_id: g.level for g in (await db.execute(select(FormGrant).where(
        FormGrant.tenant_id == tenant_id, FormGrant.user_id == user_id, FormGrant.deleted_at.is_(None)))).scalars()}
    return Viewer(principal=principal, departments=departments, folders=folders, shared=shared)


# ── Folders ─────────────────────────────────────────────────────────────────────

def folder_visible(folder: Folder | None, viewer: Viewer) -> bool:
    """True when this person may see the folder (and so the forms in it)."""
    if folder is None or not folder.access_restricted:
        return True
    if viewer.role == "owner" or viewer.can("folders.access"):
        return True
    if str(viewer.user_id) in folder.access_people or viewer.role in folder.access_roles:
        return True
    return any(d in viewer.departments for d in folder.access_departments)


def folder_actions(folder: Folder, viewer: Viewer) -> dict[str, bool]:
    """Change it (own · all), delete it, decide who sees it."""
    def reach(permission: str) -> bool:
        scope = viewer.scope(permission)
        return scope == "all" or (scope == "own" and folder.created_by == viewer.user_id)
    return {"edit": reach("folders.edit"), "delete": reach("folders.delete"), "access": viewer.can("folders.access")}


# ── Forms ───────────────────────────────────────────────────────────────────────

def _folder_of(form: Form, viewer: Viewer) -> Folder | None:
    return viewer.folders.get(form.folder_id) if form.folder_id else None


def shared_level(form: Form, viewer: Viewer) -> str:
    """The level the form is shared with this person (their own, else the team default; the maker: edit)."""
    if form.owner_id == viewer.user_id:
        return "edit"
    return viewer.shared.get(form.id) or form.team_access or "edit"


def reaches(form: Form, viewer: Viewer, scope: str | None, level: str) -> bool:
    """own: they made it · shared: someone else's form shared with them at the level needed · all: any form."""
    if not scope:
        return False
    parts = scope_parts(scope)
    if parts & 4:
        return True
    if form.owner_id == viewer.user_id:
        return bool(parts & 1)
    return bool(parts & 2) and RANK[shared_level(form, viewer)] >= RANK[level]


def allows(form: Form, viewer: Viewer, action: str) -> bool:
    if not folder_visible(_folder_of(form, viewer), viewer):
        return False
    return reaches(form, viewer, viewer.scope(f"forms.{action}"), LEVEL_FOR[action])


def actions_of(form: Form, viewer: Viewer) -> dict[str, bool]:
    return {action: allows(form, viewer, action) for action in FORM_ACTIONS}


def require_action(form: Form, viewer: Viewer, action: str) -> None:
    """A form they can't see stays "not found"; one they see but may not change says so."""
    if not allows(form, viewer, "view"):
        raise FrmError("FRM-GEN-1004")
    if not allows(form, viewer, action):
        raise FrmError("FRM-PERM-1001")


def level_of(form: Form, viewer: Viewer) -> str:
    """none < responses < view < edit (for the response routes)."""
    if not allows(form, viewer, "view"):
        return "none"
    if allows(form, viewer, "edit"):
        return "edit"
    if allows(form, viewer, "preview"):
        return "view"
    return "responses"


def require_level(form: Form, viewer: Viewer, needed: str) -> str:
    level = level_of(form, viewer)
    if level == "none":
        raise FrmError("FRM-GEN-1004")
    if RANK[level] < RANK[needed]:
        raise FrmError("FRM-PERM-1001")
    return level


def responses_allowed(form: Form, viewer: Viewer, action: str) -> bool:
    if not folder_visible(_folder_of(form, viewer), viewer):
        return False
    return reaches(form, viewer, viewer.scope(f"responses.{action}"), RESPONSE_LEVEL[action])


def response_actions_of(form: Form, viewer: Viewer) -> dict[str, bool]:
    return {action: responses_allowed(form, viewer, action) for action in RESPONSE_ACTIONS}


def can_see(form: Form, viewer: Viewer) -> bool:
    return allows(form, viewer, "view")



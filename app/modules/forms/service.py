"""Forms of a workspace (mock: data/formStore.ts and the helpers of routes/forms.ts): summaries as the app gets
them, lookups with access, the Trash's 30 days, a new form and the workspace's form defaults."""

from __future__ import annotations

import copy
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FrmError
from app.modules.audit.service import Actor, record
from app.modules.billing.service import limits_of
from app.modules.forms import access
from app.modules.forms.access import Viewer
from app.modules.forms.catalogues import TRASH_RETENTION_DAYS
from app.modules.forms.models import Folder, Form
from app.modules.forms.slugs import unique_slug
from app.modules.settings.service import get_section
from app.modules.users.models import User

KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def new_public_key() -> str:
    """newPublicKey(): ten letters and digits that can't be confused (no 0, O, 1, l, I)."""
    return "".join(secrets.choice(KEY_ALPHABET) for _ in range(10))


def name_of(user: User | None) -> str:
    return f"{user.first_name} {user.last_name}".strip() if user else ""


class Names:
    """People's names, read once per request (form owners, folder makers)."""

    def __init__(self) -> None:
        self.by_id: dict[uuid.UUID, str] = {}

    async def load(self, db: AsyncSession, tenant_id: uuid.UUID) -> Names:
        for user in (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars():
            self.by_id[user.id] = name_of(user) or user.email
        return self

    def ref(self, user_id: uuid.UUID | None) -> dict[str, str] | None:
        return {"id": str(user_id), "name": self.by_id.get(user_id, "")} if user_id else None


def folder_ref(folder: Folder | None) -> dict[str, Any] | None:
    return {"id": str(folder.id), "name": folder.name, "color": folder.color} if folder else None


def summary(form: Form, viewer: Viewer, names: Names) -> dict[str, Any]:
    """FormSummary (shared/types/forms.ts) with what this person may do with it."""
    out: dict[str, Any] = {
        "id": str(form.id), "name": form.name, "slug": form.slug, "public_key": form.public_key,
        "status": form.status, "has_unpublished_changes": form.has_unpublished_changes,
        "folder": folder_ref(viewer.folders.get(form.folder_id) if form.folder_id else None),
        "owner": names.ref(form.owner_id), "tags": list(form.tags or []), "responses_count": form.responses_count,
        "completion_rate": form.completion_rate, "created_at": iso(form.created_at), "updated_at": iso(form.updated_at),
        "row_version": form.row_version, "deleted_at": iso(form.deleted_at), "opens_at": iso(form.opens_at),
        "closes_at": iso(form.closes_at), "custom_link": form.custom_link, "access": form.access,
        "response_limit": form.response_limit, "short_code": form.short_code,
        "my_access": access.level_of(form, viewer), "can": access.actions_of(form, viewer),
        "responses_can": access.response_actions_of(form, viewer),
    }
    if form.channels:
        out["channels"] = list(form.channels)
    return out


def folder_view(folder: Folder, viewer: Viewer, names: Names) -> dict[str, Any]:
    """A folder as the app gets it: who it is open to only for people who decide that."""
    actions = access.folder_actions(folder, viewer)
    if actions["access"]:
        shown = {"restricted": folder.access_restricted, "roles": list(folder.access_roles),
                 "departments": list(folder.access_departments), "people": list(folder.access_people)}
    else:
        shown = {"restricted": True, "roles": [], "departments": [], "people": []} if folder.access_restricted else None
    return {"id": str(folder.id), "name": folder.name, "color": folder.color, "created_by": names.ref(folder.created_by),
            "access": shown, "can": actions}


async def sweep_trash(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Forms in Trash longer than 30 days are purged (the rows stay, with purged_at)."""
    cutoff = datetime.now(UTC) - timedelta(days=TRASH_RETENTION_DAYS)
    await db.execute(update(Form).where(Form.tenant_id == tenant_id, Form.deleted_at.is_not(None),
                                        Form.deleted_at < cutoff, Form.purged_at.is_(None))
                     .values(purged_at=datetime.now(UTC)))


async def forms_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[Form]:
    """Every form that still exists (in Trash or not), newest change first."""
    return list((await db.execute(select(Form).where(Form.tenant_id == tenant_id, Form.purged_at.is_(None))
                                  .order_by(Form.updated_at.desc(), Form.id))).scalars())


async def find_form(db: AsyncSession, viewer: Viewer, form_id: str, *, action: str, trash: bool = False) -> Form:
    """A form of this workspace and the action this person wants to take on it."""
    try:
        wanted = uuid.UUID(form_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    form = await db.get(Form, wanted)
    if form is None or form.tenant_id != viewer.principal.tenant.id or form.purged_at is not None \
            or (form.deleted_at is not None) != trash:
        raise FrmError("FRM-GEN-1004")
    access.require_action(form, viewer, action)
    return form


def check_version(form: Form, version: Any) -> None:
    if version is not None and version != form.row_version:
        raise FrmError("FRM-GEN-1009")


def touch(form: Form, viewer: Viewer) -> None:
    form.row_version += 1
    form.updated_at, form.updated_by = datetime.now(UTC), viewer.user_id


async def audit(db: AsyncSession, viewer: Viewer, action: str, form: Form, changes: list[dict[str, Any]] | None = None,
                metadata: dict[str, str] | None = None) -> None:
    tenant = viewer.principal.tenant
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action=action,
                 actor=Actor.user(viewer.principal.user), resource={"type": "form", "id": str(form.id), "name": form.name},
                 changes=changes or [], metadata=metadata or {})


async def require_form_slot(db: AsyncSession, viewer: Viewer) -> None:
    """The plan's number of forms (Trash doesn't count): FRM-PLAN-1001."""
    tenant = viewer.principal.tenant
    allowed = limits_of(tenant.plan_id).get("forms")
    if allowed is None:
        return
    live = (await db.execute(select(func.count()).select_from(Form).where(
        Form.tenant_id == tenant.id, Form.deleted_at.is_(None), Form.purged_at.is_(None)))).scalar_one()
    if live >= allowed:
        raise FrmError("FRM-PLAN-1001", [{"field": "forms", "message": str(allowed)}])


def visible_folder(viewer: Viewer, folder_id: str | None) -> Folder | None:
    """A folder to put a form in: one this person can see (a hidden folder is "not there")."""
    if not folder_id:
        return None
    try:
        folder = viewer.folders.get(uuid.UUID(folder_id))
    except ValueError:
        folder = None
    if folder is None or not access.folder_visible(folder, viewer):
        raise FrmError("FRM-GEN-1002", [{"field": "folder_id", "message": "Choose a folder."}])
    return folder


async def new_form(db: AsyncSession, viewer: Viewer, *, name: str, folder: Folder | None, schema: dict[str, Any],
                   template_key: str | None = None) -> Form:
    await require_form_slot(db, viewer)
    tenant = viewer.principal.tenant
    taken = (await db.execute(select(Form.slug).where(Form.tenant_id == tenant.id, Form.purged_at.is_(None)))).scalars()
    now = datetime.now(UTC)
    form = Form(tenant_id=tenant.id, organisation_id=tenant.organisation_id, folder_id=folder.id if folder else None,
                owner_id=viewer.user_id, name=name, slug=unique_slug(name, taken), public_key=new_public_key(),
                status="draft", draft_schema=schema, template_key=template_key, tags=[], embed_domains=[],
                created_by=viewer.user_id, created_at=now, updated_at=now)
    db.add(form)
    await db.flush()
    await db.refresh(form)  # the database's defaults (row_version, access …)
    return form


async def with_form_defaults(db: AsyncSession, form: Form, label_position: str | None = None) -> None:
    """Settings → Form defaults: a new blank or template form starts with the workspace's settings, thank-you
    text, response emails and allowed websites; what the dialog chose (label position) wins. (Default themes come
    with themes, B6.)"""
    defaults = await get_section(db, form.tenant_id, "form_defaults")
    schema = copy.deepcopy(form.draft_schema) if form.draft_schema else None
    if schema is not None:
        chosen = defaults["settings"]
        schema["settings"] = {
            **(schema.get("settings") or {}),
            "progress_bar": chosen["progress_bar"], "save_resume": chosen["save_resume"],
            "field_icons": chosen["field_icons"], "label_position": label_position or chosen["label_position"],
            **({"emails": {"team": list(defaults["team_emails"]), "others": [], "others_personal": False,
                           "receipt_field": None}} if defaults["team_emails"] else {}),
        }
        thanks = defaults["thank_you"]
        if thanks.get("title") or thanks.get("message"):
            schema["thank_you"] = {**(schema.get("thank_you") or {}),
                                   **({"title": thanks["title"]} if thanks.get("title") else {}),
                                   **({"message": thanks["message"]} if thanks.get("message") else {})}
        form.draft_schema = schema
    if defaults["embed_domains"]:
        form.embed_domains = list(defaults["embed_domains"])

"""A full export of one workspace (the internal admin API's `/tenants/{id}/export`), for the workspace's Owner.

A ZIP of JSON files, one per kind of record: the workspace's settings, organisation units, people (no password,
two-step or session data), roles, folders, forms with their published versions, responses with their answers, lists
with their options, themes, page designs, saved fields and templates. Secrets (`*_hash`, `*_enc`) never go in.

The job runs on the `exports` queue like every export; once the file is ready, the Owners get the "Your export is
ready" notice (in the app and by email, Settings → Notifications) with a one-time link valid for 7 days.
"""

from __future__ import annotations

import io
import json
import secrets
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security.fernet_tokens import encrypt_secret
from app.modules.exports.models import ExportJob
from app.modules.exports.service import _hash, register

KIND = "workspace"
KEEP_DAYS = 7


def _tables() -> list[tuple[str, Any]]:
    from app.modules.design.models import PageDesign, SavedField, Theme
    from app.modules.forms.models import Folder, Form, FormVersion
    from app.modules.lists.models import OptionItem, OptionList
    from app.modules.org.models import OrgUnit, OrgUnitMember
    from app.modules.responses.models import Response
    from app.modules.settings.models import WorkspaceSetting
    from app.modules.templates.models import WorkspaceTemplate
    from app.modules.users.models import Role, User

    return [("settings", WorkspaceSetting), ("org_units", OrgUnit), ("org_unit_members", OrgUnitMember),
            ("roles", Role), ("people", User), ("folders", Folder), ("forms", Form), ("form_versions", FormVersion),
            ("responses", Response), ("option_lists", OptionList), ("option_items", OptionItem), ("themes", Theme),
            ("page_designs", PageDesign), ("saved_fields", SavedField), ("templates", WorkspaceTemplate)]


SKIP = {"tenant_id", "organisation_id", "password_hash", "must_change_password", "photo_upload_id"}


def _plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return value


def _row(model: Any, obj: Any) -> dict[str, Any]:
    return {c.key: _plain(getattr(obj, c.key)) for c in model.__mapper__.column_attrs
            if c.key not in SKIP and not c.key.endswith(("_hash", "_enc"))}


async def build_workspace_file(db: AsyncSession, job: ExportJob) -> tuple[bytes, int]:
    buffer = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        counts: dict[str, int] = {}
        for name, model in _tables():
            query = select(model).where(model.tenant_id == job.tenant_id)
            if hasattr(model, "deleted_at"):
                query = query.where(model.deleted_at.is_(None))
            rows = [_row(model, obj) for obj in (await db.execute(query)).scalars()]
            counts[name] = len(rows)
            total += len(rows)
            archive.writestr(f"{name}.json", json.dumps(rows, ensure_ascii=False, indent=1, default=str))
        archive.writestr("about.json", json.dumps({
            "workspace": job.params.get("workspace"), "made_at": _plain(datetime.now(UTC)), "counts": counts,
            "note": "Formalie workspace export. Ids are Formalie's own; secrets are never included."}, indent=1))
    return buffer.getvalue(), total


async def tell_owners(db: AsyncSession, job: ExportJob) -> None:
    """The file is ready: a one-time link (7 days) to the Owners, as the "Your export is ready" notice."""
    from app.modules.notifications.service import notify
    from app.modules.users.models import Role, User

    token = secrets.token_urlsafe(32)
    await db.execute(update(ExportJob).where(ExportJob.id == job.id, ExportJob.tenant_id == job.tenant_id).values(
        token_hash=_hash(token), token_enc=encrypt_secret(token),
        expires_at=datetime.now(UTC) + timedelta(days=KEEP_DAYS)))
    owners = [u.id for u in (await db.execute(select(User).join(Role, Role.id == User.role_id).where(
        User.tenant_id == job.tenant_id, User.deleted_at.is_(None), User.status == "active",
        Role.built_in == "owner"))).scalars()]
    workspace = job.params.get("workspace") or {}
    await notify(db, job.tenant_id, job.organisation_id,
                 {"name": workspace.get("name", ""), "subdomain": workspace.get("subdomain", "")},
                 "export_ready", {"file": job.file_name}, f"{get_settings().api_prefix}/downloads/{token}",
                 only=owners)


register(KIND, build_workspace_file, keep_days=KEEP_DAYS, on_ready=tell_owners)

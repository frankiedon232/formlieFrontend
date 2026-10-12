"""The public form page (mock: routes/publicForms.ts): the form behind an address on this host, whether it takes
responses, who is visiting (data/formAccess.ts), and the `PublicForm` the page gets.

A workspace host serves only its own forms, by key or custom link. The shared forms host (`forms.*`) finds the
workspace from the key (platform.resolve_form_key). A form without the channel asked for (its web link or embed;
without either, any web route) answers exactly like one that does not exist (FRM-FORM-1001).
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import current_host_context
from app.modules.billing.service import limits_of
from app.modules.design.theme import resolve_theme
from app.modules.forms.models import Form
from app.modules.links import directory
from app.modules.links.access_tokens import read_unlock
from app.modules.links.models import FormInvitation
from app.modules.links.seo import published_schema, seo_of
from app.modules.links.urls import frame_ancestors, is_form_address
from app.modules.public import rules
from app.modules.public.submit import all_fields
from app.modules.settings.service import get_section
from app.modules.uploads.service import completed_url
from app.modules.users.models import User

FORM_CHANNELS = ("link", "embed", "api")
STATE_ERRORS = {"closed": "FRM-FORM-1002", "expired": "FRM-FORM-1015", "scheduled": "FRM-FORM-1016",
                "limit_reached": "FRM-FORM-1003"}


@dataclass
class Found:
    tenant: TenantInfo
    form: Form


@dataclass
class Visitor:
    kind: str  # public · password · invite · member
    invite: FormInvitation | None = None
    user: User | None = None

    def identity(self) -> dict[str, Any] | None:
        """Name and email of a known visitor (invitation or member), for "Filling in as …" and the response."""
        if self.kind == "invite" and self.invite:
            return {"kind": "invite", "id": self.invite.id, "name": self.invite.name, "email": self.invite.email}
        if self.kind == "member" and self.user:
            return {"kind": "member", "id": self.user.id, "email": self.user.email,
                    "name": f"{self.user.first_name} {self.user.last_name}".strip()}
        return None


def scope_of(tenant: TenantInfo) -> dict[str, Any]:
    return {"tenant_id": tenant.id, "organisation_id": tenant.organisation_id}


async def _tenant_by_subdomain(subdomain: str) -> TenantInfo | None:
    from app.modules.tenants.service import _load_by_subdomain, _to_info

    row = await _load_by_subdomain(subdomain)
    return None if row.get("missing") else _to_info(row)


async def workspace_for(key: str) -> TenantInfo:
    """The workspace an address on this host belongs to (FRM-FORM-1001 when none)."""
    if not is_form_address(key):
        raise FrmError("FRM-FORM-1001")
    ctx = get_context()
    host = current_host_context()
    if host and host.kind in ("tenant", "custom"):
        tenant = ctx.tenant if ctx else None
        if tenant is None or tenant.status == "suspended":
            raise FrmError("FRM-FORM-1001")
        return tenant
    if host and host.kind == "forms":
        async with db_session("read") as db:
            found = await directory.resolve_form_key(db, key)
        if found is None or found.status == "suspended":
            raise FrmError("FRM-FORM-1001")
        tenant = await _tenant_by_subdomain(found.subdomain)
        if tenant is None or tenant.status == "suspended":
            raise FrmError("FRM-FORM-1001")
        return tenant
    raise FrmError("FRM-FORM-1001")


async def find_form(db: AsyncSession, tenant: TenantInfo, key: str, channel: str | None) -> Form:
    host = current_host_context()
    by_key = host is not None and host.kind == "forms"
    form = (await db.execute(select(Form).where(
        Form.tenant_id == tenant.id, Form.deleted_at.is_(None), Form.purged_at.is_(None),
        Form.public_key == key if by_key else or_(Form.public_key == key, Form.custom_link == key)).limit(1))).scalar_one_or_none()
    if form is None:
        raise FrmError("FRM-FORM-1001")
    channels = list(form.channels) if form.channels else list(FORM_CHANNELS)
    if (channel not in channels) if channel else not any(c != "api" for c in channels):
        raise FrmError("FRM-FORM-1001")
    return form


def channel_of(request: Request) -> str:
    return "embed" if request.query_params.get("channel") == "embed" else "link"


def limit_reached(tenant: TenantInfo, form: Form) -> bool:
    """The form's own limit, or the plan's responses on each form."""
    if form.response_limit is not None and form.responses_count >= form.response_limit:
        return True
    plan_limit = limits_of(tenant.plan_id).get("responses_per_form")
    return plan_limit is not None and form.responses_count >= plan_limit


def state_of(tenant: TenantInfo, form: Form, ignore_limit: bool = False) -> str:
    if form.status == "published":
        window = rules.availability_of(form.opens_at, form.closes_at)
        if window in ("expired", "scheduled"):
            return window
        return "limit_reached" if not ignore_limit and limit_reached(tenant, form) else "open"
    return "closed" if form.status in ("closed", "archived") else "not_published"


async def live_schema(db: AsyncSession, form: Form) -> dict[str, Any] | None:
    """The published version with the options of lists kept on the server filled in."""
    from app.modules.lists.service import full_schema

    return await full_schema(db, form.tenant_id, await published_schema(db, form))


def unlock_cookie(form: Form) -> str:
    return f"formalie_unlock_{form.public_key}"


async def visitor_of(db: AsyncSession, request: Request, form: Form) -> Visitor | None:
    """The visitor behind this browser's unlock, or None when the form is locked for them."""
    if form.access == "public":
        return Visitor("public")
    found = read_unlock(form, request.cookies.get(unlock_cookie(form)))
    if found is None:
        return None
    kind, ref = found
    try:
        ref_id = uuid.UUID(ref) if ref else None
    except ValueError:
        return None
    if form.access == "password" and kind == "pw":
        return Visitor("password")
    if form.access == "invite" and kind == "inv" and ref_id:
        invite = await db.get(FormInvitation, ref_id)
        ok = invite is not None and invite.form_id == form.id and invite.revoked_at is None and invite.deleted_at is None
        return Visitor("invite", invite=invite) if ok else None
    if form.access == "organisation" and kind == "usr" and ref_id:
        user = await db.get(User, ref_id)
        ok = user is not None and user.tenant_id == form.tenant_id and user.deleted_at is None and user.status == "active"
        return Visitor("member", user=user) if ok else None
    return None


async def taking_responses(db: AsyncSession, request: Request, tenant: TenantInfo, key: str, *,
                           ignore_limit: bool = False, channel: str | None = None) -> tuple[Form, dict[str, Any], Visitor]:
    """The form takes responses from this visitor right now: open and unlocked for them, or why not."""
    form = await find_form(db, tenant, key, channel)
    state = state_of(tenant, form, ignore_limit)
    schema = await live_schema(db, form) if state == "open" else None
    if schema is None:
        raise FrmError(STATE_ERRORS.get(state, "FRM-FORM-1001"))
    visitor = await visitor_of(db, request, form)
    if visitor is None:
        raise FrmError("FRM-FORM-1005")
    return form, schema, visitor


async def branding(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[str | None, str | None]:
    section = await get_section(db, tenant_id, "branding")
    return section.get("logo_url"), section.get("brand_color")


def _trim_remote(schema: dict[str, Any]) -> None:
    """Long lists stay on the server: the page asks for matches as people type (large lists also say which choices
    above have options under them)."""
    for fld in all_fields(schema):
        if not rules.served_remotely(fld):
            continue
        options = fld.get("options") or []
        extra: dict[str, Any] = {"options_remote": {"total": len(options)}}
        if fld.get("options_large"):
            parents = list(dict.fromkeys(o["parent"] for o in options if "parent" in o))
            extra["options_large"] = {"total": len(options), **({"parents": parents} if fld.get("option_parent") else {})}
        fld.update(extra)
        fld["options"] = []


async def public_view(db: AsyncSession, request: Request, tenant: TenantInfo, key: str, channel: str) -> dict[str, Any]:
    """PublicForm (shared/types/public.ts)."""
    form = await find_form(db, tenant, key, channel)
    state = state_of(tenant, form)
    visitor = await visitor_of(db, request, form) if state == "open" else None
    locked = state == "open" and visitor is None
    identity = visitor.identity() if visitor else None
    published = await live_schema(db, form) if state == "open" else None
    logo, primary = await branding(db, tenant.id)
    schema = None
    if published is not None:
        schema = {**copy.deepcopy(published), "theme": resolve_theme(published.get("theme"), logo, primary)}
        _trim_remote(schema)
    languages = rules.form_languages(published or await published_schema(db, form) or form.draft_schema)
    seo = await seo_of(db, form, published_only=True)
    image_path = await completed_url(db, tenant.id, seo["image_upload_id"]) if seo["image_upload_id"] else None
    ctx = get_context()
    host = (ctx.host if ctx else None) or ""
    privacy = await get_section(db, tenant.id, "privacy")
    company = await get_section(db, tenant.id, "company")
    settings = get_settings()
    from app.modules.platform_bridge.globals import legal_links

    return {
        "key": form.custom_link or form.public_key, "name": form.name,
        "state": state if schema is not None else "not_published" if state == "open" else state,
        "opens_at": _iso(form.opens_at), "closes_at": _iso(form.closes_at),
        "schema": None if locked else schema,
        "workspace": {"name": tenant.name, "logo_url": logo, "primary": primary, "subdomain": tenant.subdomain,
                      "website": company.get("website")},
        "seo": {"title": seo["title"], "description": seo["description"],
                "image": f"https://{host}{image_path}" if image_path and host else None,
                "noindex": state != "open" or seo["noindex"]},
        "legal": await legal_links(),  # platform settings (B16): published by the Formalie team, else the server's
        "privacy": {"notice_url": privacy.get("notice_url"), "consent": bool(privacy.get("consent")),
                    "consent_text": privacy.get("consent_text")},
        "languages": languages, "language": languages[0], "locked": locked,
        "lock": form.access if locked else None,
        "visitor": {"name": identity["name"], "email": identity["email"]} if identity else None,
        "embed_ancestors": frame_ancestors(list(form.embed_domains or []), settings.root_domain),
    }


def _iso(value: Any) -> str | None:
    from app.modules.forms.service import iso

    return iso(value)


async def forget_drafts(db: AsyncSession, tenant_id: uuid.UUID, email: str, by: uuid.UUID | None) -> int:
    """A person's data erased (Settings → Privacy): their saved drafts lose their answers and address and close."""
    from datetime import UTC, datetime

    from sqlalchemy import func, update

    from app.modules.public.models import ResumeDraft

    now = datetime.now(UTC)
    result = await db.execute(update(ResumeDraft).where(
        ResumeDraft.tenant_id == tenant_id, func.lower(ResumeDraft.email) == email.strip().lower()
    ).values(data={}, email=None, closed_at=func.coalesce(ResumeDraft.closed_at, now), deleted_at=now, deleted_by=by))
    return int(result.rowcount or 0)  # type: ignore[attr-defined]

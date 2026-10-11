"""Sharing a form (mock: routes/formShare.ts, formAccess.ts; API-CONTRACT → Sharing):

    GET    /forms/{id}/share              where people answer, access, password set?, limit, custom link, embed
                                          websites, people access, search & link preview, short link
    PUT    /forms/{id}/share              change them (row_version); audited as forms.shared, never the password
    GET    /forms/{id}/share/link-check   is a custom link free? (+ up to three free suggestions)
    POST   /forms/{id}/short-link         the form's short link (or the one it has)
    DELETE /forms/{id}/short-link         remove it: the code stops working and is never handed out again
    GET    /forms/{id}/access             who can see this form and why (read only)

Passwords are argon2 hashes; a new one moves the form's password version on, so everyone who unlocked the form
must unlock it again. Sharing is for editors (decision 97): `share_view` to look, `share` to change.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.core.security.passwords import hash_password
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms import access
from app.modules.forms.access import Viewer, viewer_for
from app.modules.forms.models import Form, FormGrant
from app.modules.forms.service import audit, find_form, iso
from app.modules.links import directory, urls
from app.modules.links.seo import SEO_DESCRIPTION_MAX, SEO_TITLE_MAX, seo_defaults
from app.modules.rbac.permissions import scope_parts
from app.modules.rbac.service import grants_of, role_key, role_name, roles_of
from app.modules.uploads.service import completed_url, file_url
from app.modules.users.models import User

router = APIRouter(tags=["sharing"])

FORM_CHANNELS = ("link", "embed", "api")
ACCESS_RANK = {"edit": 0, "view": 1, "responses": 2, "none": 3}

share_schema = z.obj(
    row_version=z.number().int().optional(),
    access=z.enum(["public", "password", "invite", "organisation"]).optional(),
    password=z.string().min(8).max(100).optional(),
    response_limit=z.number().int().min(2).max(1_000_000).nullable().optional(),
    custom_link=z.string().max(80).nullable().optional(),
    seo=z.obj(title=z.string().max(SEO_TITLE_MAX).nullable(), description=z.string().max(SEO_DESCRIPTION_MAX).nullable(),
              image_upload_id=z.string().max(64).nullable(), noindex=z.boolean()).optional(),
    people=z.obj(team_access=z.enum(["edit", "view", "none"]),
                 grants=z.array(z.obj(user_id=z.string().max(64), level=z.enum(["edit", "view", "responses"]))).max(500))
    .optional(),
    channels=z.array(z.enum(list(FORM_CHANNELS))).min(1).max(3).optional(),
    embed_domains=z.array(z.string().max(253)).max(urls.MAX_EMBED_DOMAINS).optional(),
)


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def channels_of(form: Form) -> list[str]:
    return list(form.channels) if form.channels else list(FORM_CHANNELS)


def _name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


async def _people(db: Any, tenant_id: uuid.UUID) -> list[User]:
    """Everyone who can be given access: the People page's people, invited ones too, not disabled ones."""
    return list((await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                     User.status != "disabled"))).scalars())


async def _grants(db: Any, form: Form) -> list[FormGrant]:
    return list((await db.execute(select(FormGrant).where(
        FormGrant.tenant_id == form.tenant_id, FormGrant.form_id == form.id, FormGrant.deleted_at.is_(None))
        .order_by(FormGrant.granted_at, FormGrant.id))).scalars())


async def settings_of(db: Any, form: Form) -> dict[str, Any]:
    """FormShareSettings (shared/types/forms.ts)."""
    people = await _people(db, form.tenant_id)
    ref = {u.id: {"id": str(u.id), "name": _name(u), "email": u.email} for u in people}
    roles = {r.id: r for r in await roles_of(db, form.tenant_id)}
    admins = [u for u in people if u.status == "active" and (
        role_key(roles.get(u.role_id)) == "owner" or grants_of(roles.get(u.role_id)).get("forms.view") == "all")]
    always = [{"user": ref[u.id], "reason": "workspace_admin"} for u in admins]
    if not any(u.id == form.owner_id for u in admins):
        owner = ref.get(form.owner_id)
        if owner is None:
            gone = await db.get(User, form.owner_id)
            owner = {"id": str(form.owner_id), "name": _name(gone) if gone else "", "email": ""}
        always.append({"user": owner, "reason": "form_owner"})
    grants = [{"user": ref[g.user_id], "level": g.level} for g in await _grants(db, form) if g.user_id in ref]
    seo = form.seo or {}
    defaults = await seo_defaults(db, form)
    image = seo.get("image_upload_id")
    return {
        "channels": channels_of(form), "access": form.access, "has_password": bool(form.password_hash),
        "password_changed_at": iso(form.password_changed_at), "response_limit": form.response_limit,
        "responses_count": form.responses_count, "custom_link": form.custom_link, "opens_at": iso(form.opens_at),
        "closes_at": iso(form.closes_at), "row_version": form.row_version, "embed_domains": list(form.embed_domains or []),
        "people": {"team_access": form.team_access, "grants": grants, "always": always},
        "seo": {"title": seo.get("title"), "description": seo.get("description"), "image_upload_id": image,
                "image_url": await completed_url(db, form.tenant_id, image) if image else None,
                "noindex": bool(seo.get("noindex")), "default_title": defaults["title"],
                "default_description": defaults["description"]},
        "short_link": {"code": form.short_code, "clicks": form.short_clicks,
                       "created_at": iso(form.short_created_at or form.updated_at)} if form.short_code else None,
    }


# ── Custom links ────────────────────────────────────────────────────────────────

async def _holder(db: Any, value: str, form: Form) -> Form | None:
    """The form of this workspace already answering to this address (custom link, or a key that reads the same).
    Every workspace has its own host, so links only need to differ within the workspace."""
    return (await db.execute(select(Form).where(
        Form.tenant_id == form.tenant_id, Form.id != form.id, Form.deleted_at.is_(None), Form.purged_at.is_(None),
        (Form.custom_link == value) | (Form.public_key == value)).limit(1))).scalar_one_or_none()


async def _suggestions(db: Any, value: str, form: Form, principal: Principal) -> list[str]:
    base = urls.tidy_custom_link(value)
    if len(base) < 2:
        return []
    org = urls.tidy_custom_link(principal.tenant.subdomain or principal.tenant.name)[:20]
    year = datetime.now(UTC).year
    candidates = [org and f"{org}-{base}", org and f"{base}-{org}", f"{base}-{year}", f"{base}-form",
                  *(f"{base}-{n}" for n in range(2, 50))]
    free: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        link = urls.tidy_custom_link(candidate)
        if link not in free and not urls.custom_link_problem(link) and not await _holder(db, link, form):
            free.append(link)
        if len(free) == 3:
            break
    return free


async def check_link(db: Any, value: str, form: Form, principal: Principal) -> dict[str, Any]:
    """CustomLinkCheck: reserved words still get suggestions; unreadable input doesn't."""
    problem = urls.custom_link_problem(value)
    if problem == "invalid":
        return {"value": value, "available": False, "reason": "invalid", "suggestions": [], "taken_by": None}
    holder = None if problem else await _holder(db, value, form)
    if not problem and not holder:
        return {"value": value, "available": True, "reason": None, "suggestions": [], "taken_by": None}
    return {"value": value, "available": False, "reason": problem or "taken",
            "suggestions": await _suggestions(db, value, form, principal),
            "taken_by": {"id": str(holder.id), "name": holder.name, "status": holder.status,
                         "link": holder.custom_link == value} if holder else None}


# ── Routes ──────────────────────────────────────────────────────────────────────

@router.get("/forms/{form_id}/share", dependencies=[rate_limit("share-get", per_minute=120)])
async def get_share(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        form = await find_form(db, await viewer_for(db, principal), form_id, action="share_view")
        return ok(await settings_of(db, form))


@router.get("/forms/{form_id}/share/link-check", dependencies=[rate_limit("share-link-check", per_minute=120)])
async def link_check(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    value = str(request.query_params.get("value") or "")[:80]
    async with db_session("read", **_scope(principal)) as db:
        form = await find_form(db, await viewer_for(db, principal), form_id, action="share_view")
        return ok(await check_link(db, value, form, principal))


def _text(value: Any) -> str | None:
    return None if value is None else str(value).lower() if isinstance(value, bool) else str(value)


@router.put("/forms/{form_id}/share", dependencies=[rate_limit("share-save", per_minute=60)])
async def save_share(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await find_form(db, viewer, form_id, action="share")
        data = share_schema.parse(await request.json())
        if data.get("row_version") is not None and data["row_version"] != form.row_version:
            raise FrmError("FRM-GEN-1009")
        changes: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        if data.get("password") is not None:
            form.password_hash = hash_password(data["password"])
            form.password_version += 1
            form.password_changed_at = now
            changes.append({"field": "password", "before": None, "after": "changed"})  # never the password itself
        if data.get("access") is not None and data["access"] != form.access:
            if data["access"] == "password" and not form.password_hash:
                raise FrmError("FRM-GEN-1002", [{"field": "password", "message": "Set a password for this form."}])
            changes.append({"field": "access", "before": form.access, "after": data["access"]})
            form.access = data["access"]
        if "response_limit" in data and data["response_limit"] != form.response_limit:
            changes.append({"field": "response_limit", "before": _text(form.response_limit),
                            "after": _text(data["response_limit"])})
            form.response_limit = data["response_limit"]
        if "custom_link" in data:
            value = (data["custom_link"] or "").strip() or None
            if value != form.custom_link:
                if value:
                    result = await check_link(db, value, form, principal)
                    if not result["available"]:
                        raise FrmError("FRM-FORM-1006" if result["reason"] == "taken" else "FRM-GEN-1002",
                                       [{"field": "custom_link", "message": result["reason"] or "invalid"}])
                    if urls.FORM_KEY_PATTERN.fullmatch(value) and any(c.isupper() for c in value):
                        raise FrmError("FRM-GEN-1002", [{"field": "custom_link", "message": "invalid"}])
                changes.append({"field": "custom_link", "before": form.custom_link, "after": value})
                form.custom_link = value

        if "people" in data:
            people = {u.id: u for u in await _people(db, form.tenant_id)}
            wanted: dict[uuid.UUID, str] = {}
            for grant in data["people"]["grants"]:
                try:
                    person = uuid.UUID(grant["user_id"])
                except ValueError:
                    person = None
                if person not in people:
                    raise FrmError("FRM-GEN-1002", [{"field": "people", "message": "Unknown person."}])
                wanted[person] = grant["level"]  # the last one for a person wins
            if form.team_access != data["people"]["team_access"]:
                changes.append({"field": "team_access", "before": form.team_access, "after": data["people"]["team_access"]})
            current = await _grants(db, form)
            describe = lambda pairs: ",".join(sorted(f"{u}:{lv}" for u, lv in pairs))  # noqa: E731
            if describe((g.user_id, g.level) for g in current) != describe(wanted.items()):
                def names(pairs: Any) -> str | None:
                    return ", ".join(f"{_name(people[u]) if u in people else '?'} ({lv})" for u, lv in pairs) or None
                changes.append({"field": "people_access", "before": names((g.user_id, g.level) for g in current),
                                "after": names(wanted.items())})
                for g in current:
                    if g.user_id not in wanted:
                        g.deleted_at, g.deleted_by = now, principal.user.id
                    elif g.level != wanted[g.user_id]:
                        g.level, g.updated_by = wanted[g.user_id], principal.user.id
                kept = {g.user_id for g in current}
                for person, level in wanted.items():
                    if person not in kept:
                        db.add(FormGrant(tenant_id=form.tenant_id, organisation_id=form.organisation_id, form_id=form.id,
                                         user_id=person, level=level, granted_at=now, created_by=principal.user.id))
            form.team_access = data["people"]["team_access"]

        if "seo" in data:
            seo = data["seo"]
            nxt = {"title": (seo["title"] or "").strip() or None, "description": (seo["description"] or "").strip() or None,
                   "image_upload_id": seo["image_upload_id"], "noindex": seo["noindex"]}
            if nxt["image_upload_id"] and not await completed_url(db, form.tenant_id, nxt["image_upload_id"]):
                raise FrmError("FRM-GEN-1002", [{"field": "seo.image_upload_id", "message": "Upload the image again."}])
            before = {"title": None, "description": None, "image_upload_id": None, "noindex": False, **(form.seo or {})}
            for field in ("title", "description", "noindex"):
                if before[field] != nxt[field]:
                    changes.append({"field": f"seo_{field}", "before": _text(before[field]), "after": _text(nxt[field])})
            if before["image_upload_id"] != nxt["image_upload_id"]:
                changes.append({"field": "seo_image", "before": "image" if before["image_upload_id"] else None,
                                "after": "image" if nxt["image_upload_id"] else None})
            form.seo = nxt
        if "channels" in data:
            nxt_channels = [c for c in FORM_CHANNELS if c in data["channels"]]
            before_channels = channels_of(form)
            if nxt_channels != before_channels:
                changes.append({"field": "channels", "before": ", ".join(before_channels), "after": ", ".join(nxt_channels)})
                form.channels = nxt_channels
        if "embed_domains" in data:
            domains = list(dict.fromkeys(urls.normalise_embed_domain(d) for d in data["embed_domains"]))
            if any(d is None for d in domains):
                raise FrmError("FRM-GEN-1002", [{"field": "embed_domains", "message": "invalid"}])
            before_domains = ", ".join(form.embed_domains or [])
            if ", ".join(domains) != before_domains:  # type: ignore[arg-type]
                changes.append({"field": "embed_domains", "before": before_domains or None,
                                "after": ", ".join(domains) or None})  # type: ignore[arg-type]
                form.embed_domains = domains

        if changes:
            form.row_version += 1
            form.updated_at, form.updated_by = now, principal.user.id
            await db.flush()
            await audit(db, viewer, "forms.shared", form, changes)
        return ok(await settings_of(db, form))


async def _short_link(form_id: str, principal: Principal, create: bool) -> tuple[Any, bool]:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await find_form(db, viewer, form_id, action="share")
        before = form.short_code
        now = datetime.now(UTC)
        if create and not form.short_code:
            form.short_code = await directory.claim_new_short_code(db, form.id)
            form.short_clicks, form.short_created_at = 0, now
        elif not create and form.short_code:
            await directory.retire_short_code(db, form.short_code)
            form.short_code, form.short_clicks, form.short_created_at = None, 0, None
        if form.short_code != before:
            form.row_version += 1
            form.updated_at, form.updated_by = now, principal.user.id
            await db.flush()
            await audit(db, viewer, "forms.shared", form, [{"field": "short_link", "before": before, "after": form.short_code}])
        return ok(await settings_of(db, form)), create and before is None


@router.post("/forms/{form_id}/short-link", dependencies=[rate_limit("share-short-link", per_minute=30)])
async def create_short_link(form_id: str, response: Response, principal: Principal = Depends(require_auth)) -> Any:
    """201 when the link was just made, 200 when the form had one."""
    reply, made = await _short_link(form_id, principal, True)
    response.status_code = 201 if made else 200
    return reply


@router.delete("/forms/{form_id}/short-link", dependencies=[rate_limit("share-short-link", per_minute=30)])
async def remove_short_link(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    return (await _short_link(form_id, principal, False))[0]


# ── Who can see this form ───────────────────────────────────────────────────────

def _reason(form: Form, viewer: Viewer) -> str:
    """The first rule that decides this person's access, in the order the checks run."""
    folder = viewer.folders.get(form.folder_id) if form.folder_id else None
    if not access.folder_visible(folder, viewer):
        return "folder_hidden"
    scope = viewer.scope("forms.view")
    if not scope:
        return "role_none"
    parts = scope_parts(scope)
    if parts & 4:
        return "workspace_owner" if viewer.role == "owner" else "all_forms"
    if form.owner_id == viewer.user_id:
        return "form_owner" if parts & 1 else "role_none"
    if not parts & 2:
        return "role_own_only"
    if form.id in viewer.shared:
        return "own_grant"
    return "not_shared" if form.team_access == "none" else "team_default"


@router.get("/forms/{form_id}/access", dependencies=[rate_limit("form-access", per_minute=60)])
async def form_access(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """Everyone active in the workspace, what they may do with the form and the first rule that decides it, worked
    out with the same checks every route uses."""
    from dataclasses import replace

    from app.modules.org.models import OrgUnit, OrgUnitMember

    async with db_session("read", **_scope(principal)) as db:
        me = await viewer_for(db, principal)
        form = await find_form(db, me, form_id, action="share_view")
        roles = {r.id: r for r in await roles_of(db, principal.tenant.id)}
        users = list((await db.execute(select(User).where(User.tenant_id == principal.tenant.id, User.deleted_at.is_(None),
                                                          User.status == "active"))).scalars())
        grants = {g.user_id: g.level for g in await _grants(db, form)}
        departments: dict[uuid.UUID, set[str]] = {}
        for user_id, unit_id in (await db.execute(
                select(OrgUnitMember.user_id, OrgUnitMember.org_unit_id).join(OrgUnit, OrgUnit.id == OrgUnitMember.org_unit_id)
                .where(OrgUnitMember.tenant_id == principal.tenant.id, OrgUnitMember.deleted_at.is_(None),
                       OrgUnit.kind == "departments", OrgUnit.deleted_at.is_(None)))).all():
            departments.setdefault(user_id, set()).add(str(unit_id))
    people = []
    for user in users:
        role = roles.get(user.role_id)
        as_them = replace(principal, user=user, role=role, grants=grants_of(role))
        viewer = Viewer(principal=as_them, departments=departments.get(user.id, set()), folders=me.folders,
                        shared={form.id: grants[user.id]} if user.id in grants else {})
        people.append({
            "user": {"id": str(user.id), "name": _name(user), "email": user.email,
                     "photo": file_url(user.photo_upload_id) if user.photo_upload_id else None},
            "role": {"id": role_key(role), "name": role_name(role)},
            "level": access.level_of(form, viewer), "responses": access.responses_allowed(form, viewer, "view"),
            "reason": _reason(form, viewer),
        })
    people.sort(key=lambda p: (ACCESS_RANK[p["level"]], p["user"]["name"]))
    folder = me.folders.get(form.folder_id) if form.folder_id else None
    return ok({"folder": {"id": str(folder.id), "name": folder.name, "restricted": folder.access_restricted}
               if folder else None, "people": people})

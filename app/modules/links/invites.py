"""Invite-only forms and member passes (mock: routes/formInvites.ts; decision 96):

    GET    /forms/{id}/invites                       the invitations and their status
    POST   /forms/{id}/invites                       invite people { people: [{ email, name? }] }: personal links,
                                                     emailed (development also returns them as meta.dev_links)
    POST   /forms/{id}/invites/{invite_id}/resend    a new personal link (the old one stops working)
    DELETE /forms/{id}/invites/{invite_id}           revoke (the link stops working); ?remove=1 takes a revoked
                                                     invitation off the list (the row stays, deleted_at)
    POST   /forms/pass                               { key } → a 2-minute sign-in pass for an organisation-only form

Invitations are their own list: changing them doesn't move the form's row_version on, so share settings being
edited on the same page still save. Audited as forms.shared.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select

from app.modules.emails import unsubscribe as unsub
from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.emails import workspace as workspace_mail
from app.modules.forms.access import viewer_for
from app.modules.forms.models import Form
from app.modules.forms.service import audit, find_form, iso
from app.modules.links import urls
from app.modules.links.access_tokens import hash_token, issue_pass, new_invite_token
from app.modules.links.models import FormInvitation
from app.modules.settings.service import get_section

router = APIRouter(tags=["sharing"])

MAX_INVITES = 500
invite_schema = z.obj(people=z.array(z.obj(email=z.string().email().max(200),
                                           name=z.string().trim().max(120).optional())).min(1).max(200))
pass_schema = z.obj(key=z.string().min(3).max(80))


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def status_of(invite: FormInvitation) -> str:
    return ("revoked" if invite.revoked_at else "responded" if invite.responded_at
            else "opened" if invite.opened_at else "invited")


def view_of(invite: FormInvitation) -> dict[str, Any]:
    return {"id": str(invite.id), "email": invite.email, "name": invite.name, "status": status_of(invite),
            "sent_at": iso(invite.sent_at), "opened_at": iso(invite.opened_at), "responded_at": iso(invite.responded_at)}


async def _invites(db: Any, form: Form) -> list[FormInvitation]:
    return list((await db.execute(select(FormInvitation).where(
        FormInvitation.tenant_id == form.tenant_id, FormInvitation.form_id == form.id,
        FormInvitation.deleted_at.is_(None)).order_by(FormInvitation.sent_at.desc(), FormInvitation.id.desc()))).scalars())


async def _list(db: Any, form: Form) -> list[dict[str, Any]]:
    return [view_of(i) for i in await _invites(db, form)]


def personal_link(principal: Principal, form: Form, token: str) -> str:
    return f"{urls.form_link(principal.tenant.subdomain, form.custom_link or form.public_key)}?invite={token}"


def _dev(links: list[dict[str, str]]) -> dict[str, Any]:
    """Development shows the links so they can be copied; production only emails them."""
    return {"dev_links": links} if get_settings().dev_replies else {}  # exactly APP_ENV=development (M5)


async def _send(db: Any, principal: Principal, form: Form, email: str, name: str | None, link: str) -> None:
    tenant = principal.tenant
    language = (await get_section(db, tenant.id, "localisation")).get("language") or "en"
    # They used the Unsubscribe link of an earlier invitation from this workspace: not sent again
    link_out = await unsub.prepare(db, tenant_id=tenant.id, subdomain=tenant.subdomain, email=email,
                                   kind="form_invitation")
    if link_out is None:
        return
    # The workspace's look and wording, its sending address and sent log (the personal link shows as dots there)
    await workspace_mail.send(db, tenant.id, tenant.name, to=email, key="form_invitation", language=language,
                              values={"name": name or email, "form": form.name, "link": link}, reason="form_invitation",
                              footer="form", unsubscribe=link_out, hidden=("link",))


async def _form(db: Any, principal: Principal, form_id: str, action: str) -> Any:
    viewer = await viewer_for(db, principal)
    return viewer, await find_form(db, viewer, form_id, action=action)


async def _touch(db: Any, viewer: Any, form: Form, field: str, after: str) -> None:
    form.updated_at = datetime.now(UTC)
    await db.flush()
    await audit(db, viewer, "forms.shared", form, [{"field": field, "before": None, "after": after}])


@router.get("/forms/{form_id}/invites", dependencies=[rate_limit("invites-list", per_minute=120)])
async def list_invites(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        _, form = await _form(db, principal, form_id, "share_view")
        return ok(await _list(db, form))


@router.post("/forms/{form_id}/invites", status_code=201, dependencies=[rate_limit("invites-create", per_minute=20)])
async def create_invites(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """People already invited (and not revoked) are skipped, not invited twice."""
    async with db_session("write", **_scope(principal)) as db:
        viewer, form = await _form(db, principal, form_id, "share")
        data = invite_schema.parse(await request.json())
        active = {i.email for i in await _invites(db, form) if not i.revoked_at}
        if len(active) + len(data["people"]) > MAX_INVITES:
            raise FrmError("FRM-GEN-1002", [{"field": "people", "message": f"At most {MAX_INVITES} invitations per form."}])
        links: list[dict[str, str]] = []
        skipped: list[str] = []
        now = datetime.now(UTC)
        for person in data["people"]:
            email = person["email"].strip().lower()
            if email in active:
                skipped.append(email)
                continue
            active.add(email)
            token = new_invite_token()
            db.add(FormInvitation(tenant_id=form.tenant_id, organisation_id=form.organisation_id, form_id=form.id,
                                  email=email, name=person.get("name") or None, token_hash=hash_token(token),
                                  sent_at=now, created_by=principal.user.id))
            link = personal_link(principal, form, token)
            links.append({"email": email, "url": link})
            await _send(db, principal, form, email, person.get("name"), link)
        if links:
            await _touch(db, viewer, form, "invitations", f"{len(links)} invited")
        return ok({"invitations": await _list(db, form), "created": len(links), "skipped": skipped}, _dev(links))


async def _invite(db: Any, form: Form, invite_id: str) -> FormInvitation:
    try:
        wanted = uuid.UUID(invite_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    invite = await db.get(FormInvitation, wanted)
    if invite is None or invite.form_id != form.id or invite.tenant_id != form.tenant_id or invite.deleted_at:
        raise FrmError("FRM-GEN-1004")
    return invite


@router.post("/forms/{form_id}/invites/{invite_id}/resend", dependencies=[rate_limit("invites-resend", per_minute=30)])
async def resend_invite(form_id: str, invite_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer, form = await _form(db, principal, form_id, "share")
        invite = await _invite(db, form, invite_id)
        if invite.revoked_at:
            raise FrmError("FRM-FORM-1007")
        token = new_invite_token()
        invite.token_hash, invite.sent_at, invite.updated_by = hash_token(token), datetime.now(UTC), principal.user.id
        link = personal_link(principal, form, token)
        await _send(db, principal, form, invite.email, invite.name, link)
        await _touch(db, viewer, form, "invitation_resent", invite.email)
        return ok({"invitations": await _list(db, form)}, _dev([{"email": invite.email, "url": link}]))


@router.delete("/forms/{form_id}/invites/{invite_id}", dependencies=[rate_limit("invites-revoke", per_minute=60)])
async def revoke_invite(form_id: str, invite_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """The link stops working (a response already sent stays). ?remove=1 takes a revoked invitation off the list;
    an active one must be revoked first."""
    async with db_session("write", **_scope(principal)) as db:
        viewer, form = await _form(db, principal, form_id, "share")
        invite = await _invite(db, form, invite_id)
        now = datetime.now(UTC)
        if request.query_params.get("remove") == "1":
            if not invite.revoked_at:
                raise FrmError("FRM-FORM-1007")
            invite.deleted_at, invite.deleted_by = now, principal.user.id
            await _touch(db, viewer, form, "invitation_removed", invite.email)
        elif not invite.revoked_at:
            invite.revoked_at, invite.updated_by = now, principal.user.id
            await _touch(db, viewer, form, "invitation_revoked", invite.email)
        return ok({"invitations": await _list(db, form)})


@router.post("/forms/pass", dependencies=[rate_limit("forms-pass", per_minute=30)])
async def form_pass(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """A signed-in member asks to open an organisation-only form of their workspace: the form's address with a
    2-minute pass the public page trades for its unlock."""
    key = pass_schema.parse(await request.json())["key"]
    async with db_session("read", **_scope(principal)) as db:
        form = (await db.execute(select(Form).where(
            Form.tenant_id == principal.tenant.id, Form.deleted_at.is_(None), Form.purged_at.is_(None),
            or_(Form.public_key == key, Form.custom_link == key)).limit(1))).scalar_one_or_none()
    if form is None:  # another workspace's form: the member's sign-in doesn't open it
        raise FrmError("FRM-PERM-1001")
    from urllib.parse import quote

    fill = urls.form_link(principal.tenant.subdomain, form.custom_link or form.public_key)
    return ok({"url": f"{fill}?pass={quote(issue_pass(form, principal.user.id), safe='')}"})


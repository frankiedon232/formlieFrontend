"""After a response is stored (mock: data/responseEmails.ts, notifyResponse): the form's response emails and the
workspace's notifications, in the `notifications` Celery queue so the submission stays fast (CLAUDE.md rule 8).

- the chosen team members get the response with a link to it;
- outside addresses get it without a link, personal answers masked unless the form allows them;
- the respondent gets a copy in the language they filled in;
- "new response" (or "possible duplicate"), and "the form is full" when this was the last one it takes.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select

from app.modules.emails import unsubscribe as unsub
from app.core.db.session import db_session
from app.modules.emails import workspace as mail
from app.modules.forms.models import Form
from app.modules.notifications.service import notify, workspace_url
from app.modules.public.submit import all_fields
from app.modules.responses.answers import answer_text
from app.modules.responses.models import Response
from app.modules.responses.service import response_schema
from app.modules.users.models import User
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.responses")

PERSONAL_TYPES = {"email", "phone", "full_name", "address", "iban", "bic", "ip_address", "signature", "date"}
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def form_emails_of(schema: dict[str, Any] | None) -> dict[str, Any]:
    """The form's response emails (shared/utils/forms/emails.ts formEmailsOf)."""
    stored = ((schema or {}).get("settings") or {}).get("emails") or {}
    return {"team": [], "others": [], "others_personal": False, "receipt_field": None, **stored}


def _mask(text: str) -> str:
    return "••" if len(text) <= 2 else f"{text[0]}•••{text[-1]}"


async def _emails(db: Any, tenant: dict[str, Any], form: Form, schema: dict[str, Any], response: Response) -> None:
    settings = form_emails_of(schema)
    if not settings["team"] and not settings["others"] and not settings["receipt_field"]:
        return
    from app.core.security.refs import get_codec

    tenant_id, data = tenant["id"], response.data or {}
    fields = [f for f in all_fields(schema) if f["key"] in data]

    def answers(hide_personal: bool) -> list[dict[str, str]]:
        out = []
        for f in fields:
            value = answer_text(f, data[f["key"]])
            if value and hide_personal and f["type"] in PERSONAL_TYPES:
                value = _mask(value)
            if value != "":
                out.append({"label": (f.get("label") or "").strip() or f["key"], "value": value})
        return out

    async def values(language: str) -> dict[str, Any]:
        return {"form": form.name, "number": form.responses_count,
                "date": await mail.email_date(db, tenant_id, language, response.submitted_at)}
    language = await mail.email_language(db, tenant_id)
    codec = get_codec()
    link = workspace_url(tenant["subdomain"], f"/forms/{codec.encode_id(str(form.id))}/responses?response="
                                               f"{codec.encode_id(str(response.id))}")
    team = {str(t) for t in settings["team"]}
    people = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                  User.status != "disabled"))).scalars()
    for person in people:
        if str(person.id) in team:
            # They used the Unsubscribe link for this form's new responses: skipped
            link_out = await unsub.prepare(db, tenant_id=tenant_id, subdomain=tenant["subdomain"], email=person.email,
                                           kind="response_notification", ref=str(form.id))
            if link_out is None:
                continue
            await mail.send(db, tenant_id, tenant["name"], to=person.email, key="response_notification", language=language,
                            values={**await values(language), "link": link}, answers=answers(False), reason="response",
                            unsubscribe=link_out)
    if settings["others"]:
        text = await mail.template_text(db, tenant_id, "response_notification", language)
        without_link = {"subject": text["subject"],
                        "body": "\n".join(line for line in text["body"].split("\n") if "{{link}}" not in line)}
        for to in settings["others"]:
            link_out = await unsub.prepare(db, tenant_id=tenant_id, subdomain=tenant["subdomain"], email=to,
                                           kind="response_notification", ref=str(form.id))
            if link_out is None:
                continue
            await mail.send(db, tenant_id, tenant["name"], to=to, key="response_notification", language=language,
                            values=await values(language), answers=answers(not settings["others_personal"]),
                            text=without_link, reason="response_outside", footer="form", unsubscribe=link_out)
    receipt = settings["receipt_field"]
    to = str(data.get(receipt) or "").strip() if receipt else ""
    if _EMAIL.match(to):
        theirs = await mail.email_language(db, tenant_id, response.language)
        await mail.send(db, tenant_id, tenant["name"], to=to, key="response_receipt", language=theirs,
                        values=await values(theirs), answers=answers(False), reason="receipt", footer="form")


async def after_submit(tenant: dict[str, Any], form_id: uuid.UUID, response_id: uuid.UUID) -> None:
    """`tenant`: {id, organisation_id, name, subdomain}. Never raises."""
    from app.core.security.refs import get_codec

    try:
        async with db_session("write", tenant_id=tenant["id"], organisation_id=tenant["organisation_id"]) as db:
            form = await db.get(Form, form_id)
            response = (await db.execute(select(Response).where(Response.tenant_id == tenant["id"],
                                                                Response.id == response_id))).scalar_one_or_none()
            if form is None or response is None or response.deleted_at is not None:
                return
            schema = await response_schema(db, form)
            if schema:
                await _emails(db, tenant, form, schema, response)
            codec = get_codec()
            workspace = {"name": tenant["name"], "subdomain": tenant["subdomain"]}
            link = f"/forms/{codec.encode_id(str(form.id))}/responses?response={codec.encode_id(str(response.id))}"
            duplicate = bool(response.possible_duplicate)
            await notify(db, tenant["id"], tenant["organisation_id"], workspace,
                         "response_duplicate" if duplicate else "response_new", {"form": form.name}, link)
            if form.response_limit is not None and form.responses_count == form.response_limit:
                await notify(db, tenant["id"], tenant["organisation_id"], workspace, "form_limit",
                             {"form": form.name, "limit": form.response_limit},
                             f"/forms/{codec.encode_id(str(form.id))}/share")
    except Exception:  # noqa: BLE001
        log.exception("after submit failed", extra={"response_id": str(response_id)})


@celery_app.task(name="responses.after_submit", ignore_result=True, acks_late=True)
def after_submit_task(tenant: dict[str, str], form_id: str, response_id: str) -> None:
    from app.core.db.engines import dispose_engines

    async def run() -> None:
        try:
            await after_submit({**tenant, "id": uuid.UUID(tenant["id"]),
                                "organisation_id": uuid.UUID(tenant["organisation_id"])},
                               uuid.UUID(form_id), uuid.UUID(response_id))
        finally:
            await dispose_engines()
    asyncio.run(run())


def dispatch(tenant: Any, form_id: uuid.UUID, response_id: uuid.UUID) -> None:
    """To the `notifications` queue, after the submission's transaction committed. Tests replace this."""
    after_submit_task.apply_async(args=[{"id": str(tenant.id), "organisation_id": str(tenant.organisation_id),
                                         "name": tenant.name, "subdomain": tenant.subdomain},
                                        str(form_id), str(response_id)], queue="notifications")

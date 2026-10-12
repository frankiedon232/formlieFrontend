"""Emails in a workspace's look (port of the mock's core/email.ts and data/outboxStore.ts sendEmail): its name, logo
and colour, its own wording for a template when it has one (Settings → Emails), the answers of a response as a table,
and the footer for people with an account or people writing to a form. Sent through the `notifications` queue, by
the way the workspace chose (Settings → Emails → Sending address, sending.py), and kept in its sent log
(`sent_emails`, the last 200). One-time codes and personal links (`hidden`) show as dots in the log's copy.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.emails import service as emails
from app.modules.settings.service import get_section

ANSWERS = "[[formalie:answers]]"
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def defaults(language: str) -> dict[str, Any]:
    """Formalie's texts in this language (English for anything missing)."""
    en = emails._catalogue("en")
    own = emails._catalogue(language) if language != "en" else None
    if not own:
        return en
    return {part: {**en.get(part, {}), **own.get(part, {})} for part in ("templates", "events", "layout", "reasons", "account")}


def fill_in(text: str, values: dict[str, Any]) -> str:
    return _VAR.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)




async def email_language(db: AsyncSession, tenant_id: uuid.UUID, wanted: str | None = None) -> str:
    """The one asked for when the workspace offers it, else the workspace's language."""
    local = await get_section(db, tenant_id, "localisation")
    offered = local.get("form_languages") or []
    return wanted if wanted and (wanted == local.get("language") or wanted in offered) else local.get("language") or "en"


async def email_date(db: AsyncSession, tenant_id: uuid.UUID, language: str, value: datetime | None = None) -> str:
    """A date and time as the workspace shows them (its time zone), in the email's language."""
    from babel import Locale, UnknownLocaleError
    from babel.dates import format_date, format_time, get_datetime_format

    zone = (await get_section(db, tenant_id, "localisation")).get("timezone") or "UTC"
    try:
        moment = (value or datetime.now(UTC)).astimezone(ZoneInfo(zone))
    except Exception:  # noqa: BLE001 (an unknown zone: UTC)
        moment = (value or datetime.now(UTC)).astimezone(UTC)
    try:
        locale = Locale.parse(language.replace("-", "_"))
    except (UnknownLocaleError, ValueError):
        locale = Locale.parse("en")
    pattern = str(get_datetime_format("medium", locale=locale))
    return pattern.replace("{1}", format_date(moment, "medium", locale=locale)).replace(
        "{0}", format_time(moment, "short", locale=locale))


async def template_text(db: AsyncSession, tenant_id: uuid.UUID, key: str, language: str) -> dict[str, str]:
    """The workspace's own text for this language, else Formalie's."""
    custom = ((await get_section(db, tenant_id, "emails")).get("custom") or {}).get(key, {}).get(language)
    return custom or defaults(language)["templates"][key]


async def render(db: AsyncSession, tenant_id: uuid.UUID, workspace_name: str, key: str, language: str,
                 values: dict[str, Any], *, text: dict[str, str] | None = None,
                 answers: list[dict[str, str]] | None = None, footer: str = "account",
                 unsubscribe_url: str | None = None) -> dict[str, str]:
    """Subject, HTML and plain text in the shared layout (layout.py); `{{answers}}` becomes a table (HTML) or lines."""
    from app.modules.emails.layout import ANSWERS as BLOCK, Look, page

    company = await get_section(db, tenant_id, "company")
    branding = await get_section(db, tenant_id, "branding")
    settings_emails = await get_section(db, tenant_id, "emails")
    name = company.get("display_name") or workspace_name
    texts = defaults(language).get("layout", {})
    every = {"workspace": name, **values}
    source = text or await template_text(db, tenant_id, key, language)
    subject = re.sub(r"\s+", " ", fill_in(source["subject"], every)).strip()
    body = fill_in(source["body"], {**every, "answers": BLOCK})
    footer_lines = [line for line in (settings_emails.get("footer"),
                                      fill_in(texts.get("footer_form" if footer == "form" else "footer", ""), every)) if line]
    look = Look(workspace=name, logo_url=branding.get("logo_url"), brand_color=branding.get("brand_color"),
                footer_lines=footer_lines, texts=texts, language=language, unsubscribe_url=unsubscribe_url)
    message = page(subject, body, every, look, answers)
    sender = settings_emails.get("sender_name") or name
    return {**message, "from_name": sender, "reply_to": settings_emails.get("reply_to") or ""}


MASK = "••••••"
KEEP_SENT = 200
# Emails that let someone in (security review H3). They always leave through Formalie's relay (Formalie's address,
# or the workspace's verified domain, which is also signed and sent by the relay), never the workspace's own mail
# server: an admin running that server would read the Owner's reset or sign-in code. Sign-up and find-my-workspace
# codes are Formalie's own emails (service.send) and never use a workspace route.
RELAY_ONLY = frozenset({"signin_code", "password_reset", "invitation", "account_activation", "respondent_code",
                        "resume_link"})
# Of those, the ones for accounts are always in Formalie's wording, whatever the workspace saved for them (a custom
# body could put {{code}} or {{link}} in an image address on the admin's server). A test send keeps the draft.
FIXED_TEXT = frozenset({"signin_code", "password_reset", "invitation", "account_activation"})


async def _plan(db: AsyncSession, tenant_id: uuid.UUID) -> str | None:
    from app.core.context import get_context

    ctx = get_context()
    if ctx is not None and ctx.tenant is not None and ctx.tenant.id == tenant_id:
        return ctx.tenant.plan_id
    row = (await db.execute(text("SELECT plan_id FROM platform.tenant_profile()"))).first()
    return row[0] if row else None


async def log_sent(db: AsyncSession, tenant_id: uuid.UUID, *, to: str, key: str, language: str, reason: str,
                   message: dict[str, str]) -> dict[str, Any] | None:
    """The sent log's entry (SentEmail without the bodies), or None when it couldn't be written (a read-only
    session): the email still goes. Beyond the last 200, older entries are retired with their bodies cleared."""
    from app.modules.emails.models import SentEmail

    try:
        async with db.begin_nested():
            organisation = (await db.execute(text(
                "SELECT nullif(current_setting('app.organisation_id', true), '')::uuid"))).scalar_one()
            row = SentEmail(tenant_id=tenant_id, organisation_id=organisation, to_email=to.strip().lower()[:254],
                            subject=message["subject"][:400], template=key, language=language, reason=reason[:40],
                            html=message["html"], text_body=message["text"], sent_at=datetime.now(UTC))
            db.add(row)
            await db.flush()
            await db.execute(update(SentEmail).where(
                SentEmail.tenant_id == tenant_id, SentEmail.deleted_at.is_(None),
                SentEmail.id.in_(select(SentEmail.id).where(SentEmail.tenant_id == tenant_id,
                                                            SentEmail.deleted_at.is_(None))
                                 .order_by(SentEmail.sent_at.desc(), SentEmail.id.desc()).offset(KEEP_SENT))
            ).values(deleted_at=datetime.now(UTC), html="", text_body=""))
        return sent_item(row)
    except Exception:  # noqa: BLE001
        emails.log.warning("sent log not written", extra={"template": key})
        return None


def sent_item(row: Any, with_bodies: bool = False) -> dict[str, Any]:
    item = {"id": str(row.id), "at": row.sent_at.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "to": row.to_email, "subject": row.subject, "template": row.template, "language": row.language,
            "reason": row.reason}
    return {**item, "html": row.html, "text": row.text_body} if with_bodies else item


async def send(db: AsyncSession, tenant_id: uuid.UUID, workspace_name: str, *, to: str, key: str, values: dict[str, Any],
               reason: str, language: str | None = None, answers: list[dict[str, str]] | None = None,
               text: dict[str, str] | None = None, footer: str = "account", unsubscribe: Any = None,
               hidden: tuple[str, ...] = ()) -> dict[str, Any] | None:
    """Rendered in the workspace's look, written to its sent log and queued by its sending route. Never raises (an
    email never breaks what caused it) → the sent log's entry, or None when nothing went.
    `unsubscribe`: the Link from unsubscribe.prepare() for optional emails (footer link and List-Unsubscribe).
    `hidden`: values never kept in the log (one-time codes, links that sign someone in)."""
    from app.modules.emails import sending

    try:
        lang = await email_language(db, tenant_id, language)
        if key in FIXED_TEXT and reason != "test":
            text = defaults(lang)["templates"][key]  # Formalie's wording: no code or link hidden in an image address
        url = unsubscribe.page_url if unsubscribe is not None and unsubscribe.page_url else None
        message = await render(db, tenant_id, workspace_name, key, lang, values, text=text, answers=answers, footer=footer,
                               unsubscribe_url=url)
        kept = message
        if hidden:
            masked = {**values, **{name: MASK for name in hidden if name in values}}
            kept = await render(db, tenant_id, workspace_name, key, lang, masked, text=text, answers=answers,
                                footer=footer, unsubscribe_url=url)
        route = await sending.route_for(db, tenant_id, await _plan(db, tenant_id))
        if key in RELAY_ONLY and route and route.get("mode") == "smtp":
            route = None  # never the workspace's own mail server: whoever runs it would read the code or link
        item = await log_sent(db, tenant_id, to=to, key=key, language=lang, reason=reason, message=kept)
        headers = {"headers": unsubscribe.headers} if url else {}
        emails.queue({"to": to, **message, **headers, **({"route": route} if route else {})}, key=key,
                     values={**values, "reason": reason})
        return item or {"id": None}
    except Exception:  # noqa: BLE001
        emails.log.exception("workspace email could not be sent", extra={"template": key})
        return None


async def forget_address(db: AsyncSession, tenant_id: uuid.UUID, email: str, masked: str) -> int:
    """A person's data erased (Settings → Privacy): emails sent to them stay in the log as a line (when, which
    template), their address masked and the bodies and subject cleared."""
    from app.modules.emails.models import SentEmail

    result = await db.execute(update(SentEmail).where(
        SentEmail.tenant_id == tenant_id, SentEmail.to_email == email.strip().lower()
    ).values(to_email=masked.lower(), subject="", html="", text_body=""))
    return int(result.rowcount or 0)  # type: ignore[attr-defined]

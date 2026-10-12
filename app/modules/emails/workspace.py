"""Emails in a workspace's look (port of the mock's core/email.ts and data/outboxStore.ts sendEmail): its name, logo
and colour, its own wording for a template when it has one (Settings → Emails), the answers of a response as a table,
and the footer for people with an account or people writing to a form. Sent through the `notifications` queue.

The log of sent emails and the workspace's own sending domain arrive with Settings → Emails (B11).
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

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


async def send(db: AsyncSession, tenant_id: uuid.UUID, workspace_name: str, *, to: str, key: str, values: dict[str, Any],
               reason: str, language: str | None = None, answers: list[dict[str, str]] | None = None,
               text: dict[str, str] | None = None, footer: str = "account", unsubscribe: Any = None) -> None:
    """Rendered in the workspace's look and queued. Never raises (an email never breaks what caused it).
    `unsubscribe`: the Link from unsubscribe.prepare() for optional emails (footer link and List-Unsubscribe)."""
    try:
        lang = await email_language(db, tenant_id, language)
        url = unsubscribe.page_url if unsubscribe is not None and unsubscribe.page_url else None
        message = await render(db, tenant_id, workspace_name, key, lang, values, text=text, answers=answers, footer=footer,
                               unsubscribe_url=url)
        headers = {"headers": unsubscribe.headers} if url else {}
        emails.queue({"to": to, **message, **headers}, key=key, values={**values, "reason": reason})
    except Exception:  # noqa: BLE001
        emails.log.exception("workspace email could not be sent", extra={"template": key})


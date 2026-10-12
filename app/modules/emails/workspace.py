"""Emails in a workspace's look (port of the mock's core/email.ts and data/outboxStore.ts sendEmail): its name, logo
and colour, its own wording for a template when it has one (Settings → Emails), the answers of a response as a table,
and the footer for people with an account or people writing to a form. Sent through the `notifications` queue.

The log of sent emails and the workspace's own sending domain arrive with Settings → Emails (B11).
"""

from __future__ import annotations

import html as html_lib
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.emails import service as emails
from app.modules.settings.service import get_section

ANSWERS = "[[formalie:answers]]"
FORMALIE_MARK = ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:14px '
                 'auto 0"><tr><td align="center" style="font-size:11px"><a href="https://formalie.com" style="color:#6b6b6b;'
                 'text-decoration:none"><span style="display:inline-block;width:16px;height:16px;line-height:16px;'
                 'border-radius:4px;background:#111111;color:#ffffff;font-size:10px;font-weight:700;text-align:center;'
                 'vertical-align:middle">F</span>&nbsp;<span style="vertical-align:middle;font-weight:600">Formalie</span>'
                 '</a></td></tr></table>')
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


def _escape(text: str) -> str:
    return html_lib.escape(text, quote=True).replace("&#x27;", "&#39;")


def _linkify(text: str) -> str:
    return re.sub(r"(https?://[^\s<]+)", r'<a href="\1" style="color:inherit;text-decoration:underline">\1</a>', text)


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
                 answers: list[dict[str, str]] | None = None, footer: str = "account") -> dict[str, str]:
    """Subject, HTML and plain text; `{{answers}}` becomes a table (HTML) or lines (text)."""
    company = await get_section(db, tenant_id, "company")
    branding = await get_section(db, tenant_id, "branding")
    settings_emails = await get_section(db, tenant_id, "emails")
    name = company.get("display_name") or workspace_name
    texts = defaults(language)
    every = {"workspace": name, **values}
    source = text or await template_text(db, tenant_id, key, language)
    subject = re.sub(r"\s+", " ", fill_in(source["subject"], every)).strip()
    answers = answers or []
    answers_text = "\n".join(f"{a['label']}: {a['value']}" for a in answers)
    body = fill_in(source["body"], {**every, "answers": ANSWERS})
    color = branding.get("brand_color") or "#111111"
    layout = texts.get("layout", {})
    footer_lines = [line for line in (settings_emails.get("footer"),
                                      fill_in(layout.get("footer_form" if footer == "form" else "footer", ""), every)) if line]
    table = ""
    if answers:
        table = ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
                 'margin:8px 0 16px;border:1px solid #e5e5e5;border-radius:8px">' + "".join(
                     f'<tr><td style="padding:8px 12px;border-bottom:1px solid #eee;color:#666;font-size:13px;width:40%;'
                     f'vertical-align:top">{_escape(a["label"])}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;'
                     f'font-size:13px;color:#111;white-space:pre-wrap">{_escape(a["value"])}</td></tr>' for a in answers)
                 + "</table>")
    paragraphs = "".join(
        table if part.strip() == ANSWERS else
        f'<p style="margin:0 0 14px;line-height:1.55">{_linkify(_escape(part.replace(ANSWERS, ""))).replace(chr(10), "<br>")}</p>'
        for part in re.split(r"\n{2,}", body))
    logo_url = branding.get("logo_url")
    logo = (f'<img src="{_escape(logo_url)}" alt="" height="28" style="height:28px;max-width:160px;object-fit:contain;'
            f'vertical-align:middle">') if logo_url else ""
    page = (f'<!doctype html><html><body style="margin:0;padding:24px;background:#f4f4f5;font-family:-apple-system,Segoe UI,'
            f'Roboto,Helvetica,Arial,sans-serif;color:#111"><table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;'
            f'border:1px solid #e5e5e5"><tr><td style="height:4px;background:{_escape(color)}"></td></tr><tr><td '
            f'style="padding:20px 28px 4px;font-weight:600;font-size:15px">{logo}{"&nbsp;&nbsp;" if logo else ""}<span '
            f'style="vertical-align:middle">{_escape(name)}</span></td></tr><tr><td style="padding:12px 28px 8px;'
            f'font-size:14px">{paragraphs}</td></tr><tr><td style="padding:16px 28px 22px;border-top:1px solid #eee;'
            f'color:#888;font-size:12px;line-height:1.5">{"<br>".join(_escape(line) for line in footer_lines)}</td></tr>'
            f'</table>{FORMALIE_MARK}</body></html>')
    plain = f"{body.replace(ANSWERS, answers_text)}\n\n--\n" + "\n".join(footer_lines) + "\n\nFormalie · https://formalie.com"
    sender = settings_emails.get("sender_name") or name
    return {"subject": subject, "html": page, "text": plain, "from_name": sender,
            "reply_to": settings_emails.get("reply_to") or ""}


async def send(db: AsyncSession, tenant_id: uuid.UUID, workspace_name: str, *, to: str, key: str, values: dict[str, Any],
               reason: str, language: str | None = None, answers: list[dict[str, str]] | None = None,
               text: dict[str, str] | None = None, footer: str = "account") -> None:
    """Rendered in the workspace's look and queued. Never raises (an email never breaks what caused it)."""
    try:
        lang = await email_language(db, tenant_id, language)
        message = await render(db, tenant_id, workspace_name, key, lang, values, text=text, answers=answers, footer=footer)
        emails.queue({"to": to, **message}, key=key, values={**values, "reason": reason})
    except Exception:  # noqa: BLE001
        emails.log.exception("workspace email could not be sent", extra={"template": key})


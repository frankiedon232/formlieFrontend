"""Emails: Formalie's default templates (app/modules/emails/defaults, synced from the frontend's mock) rendered in
the person's language, then sent through the `notifications` Celery queue (CLAUDE.md rule 8).

Workspaces' own wording, sending domains and SMTP servers arrive in B11; until then everything is sent as Formalie
(EMAIL_FROM) through SMTP_* (Mailpit in development, http://127.0.0.1:8025). Codes are never logged.
"""

from __future__ import annotations

import json
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("formalie.emails")

DEFAULTS = Path(__file__).parent / "defaults"
FORM_EMAILS = {"form_invitation", "respondent_code", "resume_link", "response_receipt"}
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")
SENT: list[dict[str, Any]] = []  # EMAIL_DELIVERY=memory (tests): what would have been sent


@lru_cache
def _catalogue(language: str) -> dict[str, Any]:
    path = DEFAULTS / f"{language}.json"
    if not path.exists():
        path = DEFAULTS / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _fill(template: str, values: dict[str, Any]) -> str:
    return _VAR.sub(lambda m: str(values.get(m.group(1), "")), template)


def render(key: str, language: str | None, values: dict[str, Any], unsubscribe_url: str | None = None) -> dict[str, str]:
    """Subject, plain text and HTML of a default template in a language (English when missing), in the shared layout
    (layout.py). Formalie's own emails (no workspace yet: sign-up, find workspace) carry the Field F mark."""
    from app.modules.emails.layout import Look, page

    lang = language or "en"
    catalogue = _catalogue(lang)
    english = _catalogue("en")
    template = catalogue["templates"].get(key) or english["templates"][key]
    texts = {**english.get("layout", {}), **catalogue.get("layout", {})}
    workspace = str(values.get("workspace") or "Formalie")
    every = {**values, "workspace": workspace}
    subject = re.sub(r"\s+", " ", _fill(template["subject"], every)).strip()
    body = _fill(template["body"], every)
    # People writing to a form have no account: "because of a form from …"
    footer = _fill(texts.get("footer_form" if key in FORM_EMAILS else "footer", ""), every)
    look = Look(workspace=workspace, formalie=workspace == "Formalie", footer_lines=[footer] if footer else [],
                texts=texts, language=lang, unsubscribe_url=unsubscribe_url)
    return page(subject, body, every, look)


def deliver(message: dict[str, str]) -> None:
    """SMTP delivery (the Celery task, or direct). Raises on failure so the task retries."""
    settings = get_settings()
    email = EmailMessage()
    # A workspace's emails carry its name; the address stays Formalie's until its own domain is set up (B11)
    email["From"] = formataddr((message["from_name"], parseaddr(settings.email_from)[1])) if message.get("from_name") \
        else settings.email_from
    email["To"] = message["to"]
    if message.get("reply_to"):
        email["Reply-To"] = message["reply_to"]
    email["Subject"] = message["subject"]
    # Optional emails: List-Unsubscribe and List-Unsubscribe-Post (RFC 8058; Gmail and Yahoo ask bulk senders for them)
    for name, value in (message.get("headers") or {}).items():
        if name in ("List-Unsubscribe", "List-Unsubscribe-Post"):
            email[name] = value
    email.set_content(message["text"])
    email.add_alternative(message["html"], subtype="html")
    if settings.smtp_security == "tls":
        client: smtplib.SMTP = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15,
                                                context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
    with client:
        if settings.smtp_security == "starttls":
            client.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        client.send_message(email)


def send(to: str, key: str, language: str | None, values: dict[str, Any], unsubscribe: Any = None) -> None:
    """Queue one templated email. Never raises: a sending problem is logged (the person can ask for a resend).
    `unsubscribe`: the Link from unsubscribe.prepare() for optional emails (footer link and List-Unsubscribe)."""
    url = unsubscribe.page_url if unsubscribe is not None and unsubscribe.page_url else None
    headers = {"headers": unsubscribe.headers} if url else {}
    queue({"to": to, **render(key, language, values, url), **headers}, key=key, values=values)


def queue(message: dict[str, str], *, key: str, values: dict[str, Any]) -> None:
    """One rendered email to the `notifications` queue (memory: kept in SENT; direct: sent now). Never raises."""
    mode = get_settings().email_delivery
    try:
        if mode == "memory":
            SENT.append({**message, "key": key, "values": values})
        elif mode == "direct":
            deliver(message)
        else:
            from app.workers.celery_app import celery_app

            celery_app.send_task("notifications.send_email", args=[message], queue="notifications")
    except Exception as exc:  # noqa: BLE001
        log.error("email could not be queued", extra={"template": key, "error": str(exc)[:300]})

"""Emails: Formalie's default templates (app/modules/emails/defaults, synced from the frontend's mock) rendered in
the person's language, then sent through the `notifications` Celery queue (CLAUDE.md rule 8).

Workspaces' own wording, sending domains and SMTP servers arrive in B11; until then everything is sent as Formalie
(EMAIL_FROM) through SMTP_* (Mailpit in development, http://127.0.0.1:8025). Codes are never logged.
"""

from __future__ import annotations

import html
import json
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("formalie.emails")

DEFAULTS = Path(__file__).parent / "defaults"
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


def render(key: str, language: str | None, values: dict[str, Any]) -> dict[str, str]:
    """Subject, plain text and simple HTML of a default template in a language (English when missing)."""
    catalogue = _catalogue(language or "en")
    template = catalogue["templates"].get(key) or _catalogue("en")["templates"][key]
    subject = _fill(template["subject"], values)
    body = _fill(template["body"], values)
    footer = _fill(catalogue.get("layout", {}).get("footer", ""), values)
    text = f"{body}\n\n--\n{footer}" if footer else body
    paragraphs = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in body.split("\n\n"))
    html_body = (f'<div style="font-family:system-ui,sans-serif;font-size:15px;line-height:1.5;color:#111">{paragraphs}'
                 f'<hr style="border:none;border-top:1px solid #ddd"><p style="color:#666;font-size:13px">'
                 f"{html.escape(footer)}</p></div>")
    return {"subject": subject, "text": text, "html": html_body}


def deliver(message: dict[str, str]) -> None:
    """SMTP delivery (the Celery task, or direct). Raises on failure so the task retries."""
    settings = get_settings()
    email = EmailMessage()
    email["From"] = settings.email_from
    email["To"] = message["to"]
    email["Subject"] = message["subject"]
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


def send(to: str, key: str, language: str | None, values: dict[str, Any]) -> None:
    """Queue one templated email. Never raises: a sending problem is logged (the person can ask for a resend)."""
    message = {"to": to, **render(key, language, values)}
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

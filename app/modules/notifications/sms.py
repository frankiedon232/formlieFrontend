"""Text messages (sign-in codes by SMS, confirming a phone). No SMS provider is set up yet (B11): tests keep the
messages in memory (EMAIL_DELIVERY=memory); otherwise nothing is sent and a warning says so, without the text,
since it holds a code."""

from __future__ import annotations

import logging

from app.core.config import get_settings

log = logging.getLogger("formalie.sms")

SENT: list[dict[str, str]] = []


def send(to: str, text: str) -> bool:
    """True when the message went out (or was kept, in tests)."""
    if get_settings().email_delivery == "memory":
        SENT.append({"to": to, "text": text})
        return True
    log.warning("no SMS provider configured: text message not sent", extra={"to_last4": to[-4:]})
    return False

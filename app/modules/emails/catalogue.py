"""The placeholders each email template can use (the frontend's shared/types/emails.ts EMAIL_VARIABLES; held to it by
tests/parity/test_settings_more_rules.py)."""

from __future__ import annotations

EMAIL_VARIABLES: dict[str, list[str]] = {
    "signin_code": ["name", "code", "minutes", "workspace"],
    "password_reset": ["name", "code", "minutes", "workspace"],
    "invitation": ["name", "inviter", "workspace", "link"],
    "account_activation": ["name", "inviter", "workspace", "link", "days"],
    "account_approved": ["name", "inviter", "workspace", "link"],
    "account_rejected": ["name", "workspace", "reason"],
    "response_notification": ["form", "number", "date", "answers", "link", "workspace"],
    "response_receipt": ["form", "number", "date", "answers", "workspace"],
    "form_invitation": ["name", "form", "workspace", "link"],
    "respondent_code": ["code", "minutes", "form", "workspace"],
    "resume_link": ["form", "link", "days", "workspace"],
    "notification": ["title", "message", "link", "workspace"],
    "daily_digest": ["name", "summary", "link", "workspace"],
}

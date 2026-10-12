"""Every email template the settings offer exists in every language and fills every placeholder (owner, 2026-10-12:
each email Formalie sends has its own template, translated; none goes out through the generic one in English)."""

from __future__ import annotations

import re

import pytest

from app.core.locales import APP_LOCALE_CODES
from app.modules.emails import service as emails
from app.modules.settings.catalogues import EMAIL_TEMPLATES

SAMPLE = {"name": "Ada", "code": "483921", "minutes": 10, "workspace": "Acme", "inviter": "Sam Lee", "link": "https://x.test",
          "form": "Feedback", "number": 12, "date": "12 Oct 2026", "answers": "", "title": "T", "message": "M",
          "summary": "S", "days": 7, "reason": "Only staff can join."}


@pytest.mark.parametrize("language", sorted(APP_LOCALE_CODES))
@pytest.mark.parametrize("key", EMAIL_TEMPLATES)
def test_every_template_renders_in_every_language(key: str, language: str) -> None:
    own = emails._catalogue(language)["templates"]
    assert key in own, f"{key} missing in {language}"
    rendered = emails.render(key, language, SAMPLE)
    for part in ("subject", "text"):
        assert not re.search(r"\{\{\s*\w+\s*\}\}", rendered[part]), (key, language, rendered[part])


def test_respondent_and_account_emails_use_their_own_templates() -> None:
    for key in ("form_invitation", "respondent_code", "resume_link", "account_activation", "account_approved",
                "account_rejected"):
        assert key in EMAIL_TEMPLATES

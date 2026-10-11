"""Workspace settings: Formalie's defaults (port of the mock's data/settingsStore.ts seed) and reading a section.

B1 reads company, branding, localisation, signin and security; the other sections and their validation
(shared/utils/settings/schemas.ts) arrive with their pages (B3, B11). A section with no row yet reads as its
default, exactly like the mock fills in a section it doesn't have.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.locales import APP_LOCALE_CODES
from app.core.security.passwords import DEFAULT_PASSWORD_POLICY
from app.modules.settings.models import WorkspaceSetting


SIGNIN_METHODS = ("password", "google", "microsoft", "facebook")  # shared/utils/settings/schemas.ts (parity test)


def defaults(*, name: str, website: str | None = None, signin_methods: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """The sections a new workspace starts with (settingsStore.ts seed)."""
    return {
        "company": {
            "legal_name": name, "display_name": name, "industry": None, "size": None, "website": website,
            "registration_number": None, "tax_number": None, "support_email": None, "support_phone": None,
            "address": {"line1": None, "line2": None, "city": None, "region": None, "postal_code": None, "country": None},
        },
        "branding": {"logo_url": None, "logo_dark_url": None, "favicon_url": None, "brand_color": None, "signin_message": None},
        "localisation": {"language": "en", "timezone": "UTC", "currency": "USD", "date_format": "DD/MM/YYYY",
                         "number_format": "1,234.56", "week_start": "monday", "form_languages": list(APP_LOCALE_CODES)},
        # Codes by email; text messages only when switched on (owner, 2026-10-07)
        "signin": {"methods": list(signin_methods or ["password"]),
                   "code": {"sms": False, "expiry_minutes": 5, "max_attempts": 5}, "allowed_domains": []},
        "security": {
            "password": {**DEFAULT_PASSWORD_POLICY, "reuse_last": 0, "expiry_days": 0},
            "sessions": {"idle_minutes": 60, "max_hours": 168},
            "ip_allowlist": {"enabled": False, "entries": []},
        },
    }


_FALLBACK = defaults(name="")


async def get_section(session: AsyncSession, tenant_id: uuid.UUID, section: str) -> dict[str, Any]:
    """The section's value (RLS keeps it to the workspace in the session's context); its default when not saved."""
    row = (await session.execute(
        select(WorkspaceSetting.value).where(WorkspaceSetting.tenant_id == tenant_id, WorkspaceSetting.section == section)
    )).scalar_one_or_none()
    if row is not None:
        return row
    return copy.deepcopy(_FALLBACK.get(section, {}))


def seed_rows(tenant_id: uuid.UUID, organisation_id: uuid.UUID, sections: dict[str, dict[str, Any]]) -> list[WorkspaceSetting]:
    return [WorkspaceSetting(tenant_id=tenant_id, organisation_id=organisation_id, section=name, value=value)
            for name, value in sections.items()]

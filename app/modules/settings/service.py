"""Workspace settings: Formalie's defaults (port of the mock's data/settingsStore.ts seed) and reading a section.

All ten sections (shared/types/settings.ts SETTINGS_SECTIONS). A section with no row yet reads as its default,
exactly like the mock fills in a section it doesn't have. Saving: `save_section` (validated by the caller with
app/modules/settings/schemas.py); who saved it last is the row's updated_by and updated_at.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.locales import APP_LOCALE_CODES
from app.core.security.passwords import DEFAULT_PASSWORD_POLICY
from app.modules.settings.catalogues import FORMALIE_APPEARANCE, NOTIFICATION_EVENTS, SETTINGS_SECTIONS
from app.modules.settings.models import WorkspaceSetting


# The ways in on sign-up and on every workspace's sign-in page, always all of them (owner, 2026-10-12): a workspace
# doesn't choose them, its admin can only add single sign-on. shared/utils/settings/schemas.ts (parity test)
SIGNIN_PROVIDERS = ("password", "google", "facebook")


def defaults(*, name: str, website: str | None = None) -> dict[str, dict[str, Any]]:
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
        "signin": {"code": {"sms": False, "expiry_minutes": 5, "max_attempts": 5}, "allowed_domains": []},
        "security": {
            "password": {**DEFAULT_PASSWORD_POLICY, "reuse_last": 0, "expiry_days": 0},
            "sessions": {"idle_minutes": 60, "max_hours": 168},
            "ip_allowlist": {"enabled": False, "entries": []},
        },
        # Responses in the app for everyone; problems also by email to admins (F14 M4)
        "notifications": {
            "events": {event: {"in_app": True, "email": event in _EMAILED, "to": "everyone" if event == "response_new"
                               else "admins", "people": []} for event in NOTIFICATION_EVENTS},
            "digest": {"enabled": False, "hour": 8},
        },
        "emails": {"sender_name": None, "reply_to": None, "footer": None, "custom": {}},
        # Keep responses; no notice or consent line until set (F14 M5)
        "privacy": {"retention_days": 0, "notice_url": None, "consent": False, "consent_text": None},
        "form_defaults": {
            "settings": {"progress_bar": True, "save_resume": False, "field_icons": True, "label_position": "top"},
            "theme_id": None, "thank_you": {"title": None, "message": None}, "team_emails": [], "embed_domains": [],
        },
        "appearance": copy.deepcopy(FORMALIE_APPEARANCE),
    }


_EMAILED = ("form_limit", "form_closing", "webhook_failing", "security_alert")


_FALLBACK = defaults(name="")


def _current(section: str, value: dict[str, Any]) -> dict[str, Any]:
    """A stored value in today's shape: sign-in rows saved before 2026-10-12 still hold `methods` (the workspace's
    old ways in), which no longer exist; the row keeps it until the next save, the answer never shows it."""
    if section == "signin" and "methods" in value:
        return {k: v for k, v in value.items() if k != "methods"}
    return value


async def get_section(session: AsyncSession, tenant_id: uuid.UUID, section: str) -> dict[str, Any]:
    """The section's value (RLS keeps it to the workspace in the session's context); its default when not saved."""
    row = (await session.execute(
        select(WorkspaceSetting.value).where(WorkspaceSetting.tenant_id == tenant_id, WorkspaceSetting.section == section)
    )).scalar_one_or_none()
    if row is not None:
        return _current(section, row)
    return copy.deepcopy(_FALLBACK.get(section, {}))


def seed_rows(tenant_id: uuid.UUID, organisation_id: uuid.UUID, sections: dict[str, dict[str, Any]]) -> list[WorkspaceSetting]:
    return [WorkspaceSetting(tenant_id=tenant_id, organisation_id=organisation_id, section=name, value=value)
            for name, value in sections.items()]


async def all_settings(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """GET /settings: every section, and who changed each one last ({at, by} or null)."""
    from app.modules.users.models import User

    rows = {r.section: r for r in (await session.execute(
        select(WorkspaceSetting).where(WorkspaceSetting.tenant_id == tenant_id))).scalars()}
    editors = {u.id: f"{u.first_name} {u.last_name}".strip() for u in (await session.execute(
        select(User).where(User.id.in_([r.updated_by for r in rows.values() if r.updated_by])))).scalars()}
    out: dict[str, Any] = {}
    updated: dict[str, Any] = {}
    for section in SETTINGS_SECTIONS:
        row = rows.get(section)
        out[section] = _current(section, row.value) if row is not None else copy.deepcopy(_FALLBACK[section])
        updated[section] = ({"at": row.updated_at.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                             "by": editors.get(row.updated_by, "")} if row is not None and row.updated_by else None)
    out["updated"] = updated
    return out


async def save_section(session: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, section: str,
                       value: dict[str, Any], user_id: uuid.UUID) -> dict[str, Any]:
    row = (await session.execute(select(WorkspaceSetting).where(
        WorkspaceSetting.tenant_id == tenant_id, WorkspaceSetting.section == section))).scalar_one_or_none()
    if row is None:
        row = WorkspaceSetting(tenant_id=tenant_id, organisation_id=organisation_id, section=section, value=value,
                               created_by=user_id)
        session.add(row)
    else:
        row.value = value
        row.row_version += 1
    row.updated_by, row.updated_at = user_id, datetime.now(UTC)
    await session.flush()
    return value

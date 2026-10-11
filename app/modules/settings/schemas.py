"""Workspace settings validation, ported line by line from the frontend's shared/utils/settings/schemas.ts with
app/core/zod.py, and held to zod's own answers by tests/parity/test_settings_rules.py."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.core import zod as z
from app.core.locales import APP_LOCALE_CODES
from app.core.net import parse_cidr
from app.core.security.passwords import PASSWORD_LENGTH_RANGE
from app.core.validation import ZOD_EMAIL
from app.modules.settings.catalogues import (
    APPEARANCE_FONTS, APPEARANCE_NEUTRALS, APPEARANCE_PRIMARIES, APPEARANCE_RADII, COMPANY_SIZES, COUNTRY_CURRENCIES,
    CURRENCY_CODES, DATE_FORMATS, EMAIL_TEMPLATES, IDLE_MINUTES, INDUSTRIES, MAX_SESSION_HOURS, NOTIFICATION_EVENTS,
    NUMBER_FORMATS, RETENTION_DAYS,
)
from app.modules.settings.service import SIGNIN_METHODS

_WEBSITE = re.compile(r"^https?://[^\s.]+\.[^\s]+$", re.IGNORECASE)
_HTTPS = re.compile(r"^https://[^\s.]+\.[^\s]+$", re.IGNORECASE)
_PHONE = re.compile(r"^\+?[0-9 ()./-]{6,40}$")
_EMAIL_DOMAIN = re.compile(r"^(?=.{3,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_EMBED_DOMAIN = re.compile(r"^(\*\.)?(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def optional(size: int) -> z.Schema:
    """Optional text: trimmed, '' → None, at most `size` characters."""
    return z.string().trim().max(size).nullable().transform(lambda value: value or None)


def is_email(value: str) -> bool:
    return bool(ZOD_EMAIL.match(value))


def is_email_domain(value: str) -> bool:
    return bool(_EMAIL_DOMAIN.match(value))


def is_embed_domain(value: str) -> bool:
    return bool(_EMBED_DOMAIN.match(value))


def is_ip_or_range(value: str) -> bool:
    return parse_cidr(value) is not None


@lru_cache(maxsize=1)
def _zones() -> frozenset[str]:
    import zoneinfo

    return frozenset(name.lower() for name in zoneinfo.available_timezones())


def is_time_zone(value: str) -> bool:
    """isTimeZone(): what Intl accepts (IANA names and their old aliases, any letter case)."""
    return value == "UTC" or value.lower() in _zones()


def _unique(items: list[Any]) -> list[Any]:
    return list(dict.fromkeys(items))


company = z.obj(
    legal_name=z.string().trim().min(2).max(160),
    display_name=z.string().trim().min(2).max(80),
    industry=z.enum(INDUSTRIES).nullable(),
    size=z.enum(COMPANY_SIZES).nullable(),
    website=optional(200).refine(lambda v: not v or bool(_WEBSITE.match(v)), "website"),
    registration_number=optional(60),
    tax_number=optional(60),
    support_email=optional(200).refine(lambda v: not v or is_email(v), "email"),
    support_phone=optional(40).refine(lambda v: not v or bool(_PHONE.match(v)), "phone"),
    address=z.obj(
        line1=optional(160),
        line2=optional(160),
        city=optional(100),
        region=optional(100),
        postal_code=optional(20),
        country=z.string().nullable().refine(lambda v: not v or v in COUNTRY_CURRENCIES, "country"),
    ),
)

_upload_id = z.string().min(1).max(100).nullable().optional()
branding = z.obj(
    logo_upload_id=_upload_id,
    logo_dark_upload_id=_upload_id,
    favicon_upload_id=_upload_id,
    brand_color=z.string().regex(r"^#[0-9a-fA-F]{6}$", "color").nullable(),
    signin_message=optional(160),
)

localisation = z.obj(
    language=z.enum(APP_LOCALE_CODES),
    timezone=z.string().min(1).max(64).refine(is_time_zone, "timezone"),
    currency=z.string().refine(lambda code: code in CURRENCY_CODES, "currency"),
    date_format=z.enum(DATE_FORMATS),
    number_format=z.enum(NUMBER_FORMATS),
    week_start=z.enum(["monday", "sunday", "saturday"]),
    form_languages=z.array(z.enum(APP_LOCALE_CODES)).min(1, "form_languages").max(len(APP_LOCALE_CODES)),
)

signin = z.obj(
    methods=z.array(z.enum(SIGNIN_METHODS)).min(1, "methods")
    .transform(lambda items: [m for m in SIGNIN_METHODS if m in items]),
    code=z.obj(
        sms=z.boolean(),
        expiry_minutes=z.literals([5, 10, 15]),
        max_attempts=z.literals([3, 5, 10]),
    ),
    allowed_domains=z.array(
        z.string().trim().lower().transform(lambda v: re.sub(r"^@", "", v)).refine(is_email_domain, "domain"),
    ).max(50).transform(_unique),
)


def _drop_blank_entries(items: Any) -> Any:
    """Empty rows (an added line left blank) are dropped."""
    if not isinstance(items, list):
        return items
    return [e for e in items if str((e.get("value") if isinstance(e, dict) else None) or "").strip()]


security = z.obj(
    password=z.obj(
        min_length=z.number().int().min(PASSWORD_LENGTH_RANGE["min"]).max(PASSWORD_LENGTH_RANGE["max"]),
        lower=z.boolean(),
        upper=z.boolean(),
        number=z.boolean(),
        symbol=z.boolean(),
        reuse_last=z.literals([0, 3, 5, 10]),
        expiry_days=z.literals([0, 90, 180, 365]),
    ),
    sessions=z.obj(
        idle_minutes=z.number().refine(lambda v: v in IDLE_MINUTES),
        max_hours=z.number().refine(lambda v: v in MAX_SESSION_HOURS),
    ),
    ip_allowlist=z.obj(
        enabled=z.boolean(),
        entries=z.preprocess(_drop_blank_entries, z.array(z.obj(
            value=z.string().trim().refine(is_ip_or_range, "ip"),
            label=optional(60),
        )).max(100)),
    ).refine(lambda v: not v["enabled"] or len(v["entries"]) > 0, "ip_empty", ["entries"]),
)

_rule = z.obj(
    in_app=z.boolean(),
    email=z.boolean(),
    to=z.enum(["admins", "everyone", "people"]),
    people=z.array(z.string().max(64)).max(200),
).refine(lambda r: r["to"] != "people" or len(r["people"]) > 0, "people", ["people"])

notifications = z.obj(
    events=z.obj({event: _rule for event in NOTIFICATION_EVENTS}),
    digest=z.obj(enabled=z.boolean(), hour=z.number().int().min(0).max(23)),
)

email_text = z.obj(
    subject=z.string().trim().min(1, "subject").max(200),
    body=z.string().trim().min(1, "body").max(10_000),
)

emails = z.obj(
    sender_name=optional(80),
    reply_to=optional(200).refine(lambda v: not v or is_email(v), "email"),
    footer=optional(300),
    custom=z.partial_record(EMAIL_TEMPLATES, z.partial_record(APP_LOCALE_CODES, email_text)),
)

privacy = z.obj(
    retention_days=z.number().refine(lambda v: v in RETENTION_DAYS, "retention"),
    notice_url=optional(300).refine(lambda v: not v or bool(_HTTPS.match(v)), "https"),
    consent=z.boolean(),
    consent_text=optional(400),
)

form_defaults = z.obj(
    settings=z.obj(progress_bar=z.boolean(), save_resume=z.boolean(), field_icons=z.boolean(),
                   label_position=z.enum(["top", "left"])),
    theme_id=z.string().max(64).nullable(),
    thank_you=z.obj(title=optional(200), message=optional(2000)),
    team_emails=z.array(z.string().max(64)).max(50),
    embed_domains=z.array(
        z.string().trim().lower()
        .transform(lambda v: re.sub(r"/.*$", "", re.sub(r"^https?://", "", v)))
        .refine(is_embed_domain, "domain"),
    ).max(50).transform(_unique),
)

_plain_tinted = z.enum(["plain", "tinted"])
appearance = z.obj(
    preset=z.string().max(40),
    primary=z.enum(APPEARANCE_PRIMARIES),
    neutral=z.enum(APPEARANCE_NEUTRALS),
    background=_plain_tinted,
    radius=z.enum(APPEARANCE_RADII),
    font=z.enum(APPEARANCE_FONTS),
    text_size=z.enum(["sm", "md", "lg"]),
    rail=z.enum(["light", "dark"]),
    menu=z.enum(["light", "dark"]),
    menu_badges=z.boolean(),
    header=z.obj(breadcrumbs=z.boolean(), search=z.boolean()),
    footer=z.boolean(),
    content_width=z.enum(["full", "centred"]),
    density=z.enum(["comfortable", "compact"]),
    default_mode=z.enum(["system", "light", "dark"]),
    dark=z.obj(primary=z.enum(APPEARANCE_PRIMARIES), neutral=z.enum(APPEARANCE_NEUTRALS),
               background=_plain_tinted).nullable(),
)

SCHEMAS: dict[str, z.Schema] = {
    "company": company, "branding": branding, "localisation": localisation, "signin": signin, "security": security,
    "notifications": notifications, "emails": emails, "privacy": privacy, "form_defaults": form_defaults,
    "appearance": appearance,
}

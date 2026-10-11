"""Onboarding steps' validation, ported from the mock's routes/onboarding.ts with app/core/zod.py and held to zod's
answers (tests/parity/test_settings_rules.py). One deliberate difference: the website must be a web address (http or
https); zod's z.url() also takes javascript:, mailto: and others, which a public page must never link to."""

from __future__ import annotations

from app.core import zod as z
from app.core.locales import APP_LOCALE_CODES
from app.modules.settings.catalogues import (
    COMPANY_SIZES, COUNTRY_CURRENCIES, CURRENCY_CODES, DATE_FORMATS, INDUSTRIES, NUMBER_FORMATS, ONBOARDING_STEPS,
    STARTER_TEMPLATE_KEYS,
)

company = z.obj(
    name=z.string().trim().min(2).max(120),
    industry=z.enum(INDUSTRIES).nullable(),
    size=z.enum(COMPANY_SIZES).nullable(),
    country=z.string().refine(lambda v: v in COUNTRY_CURRENCIES, "Choose a country.").nullable(),
    website=z.string().url().max(200).nullable(),
)

branding = z.obj(
    logo_upload_id=z.string().nullable(),
    brand_color=z.string().regex(r"^#[0-9a-fA-F]{6}$").nullable(),
)

localisation = z.obj(
    language=z.enum(APP_LOCALE_CODES),
    timezone=z.string().min(1).max(64),
    currency=z.string().refine(lambda code: code in CURRENCY_CODES, "Choose a currency."),
    date_format=z.enum(DATE_FORMATS),
    number_format=z.enum(NUMBER_FORMATS),
    week_start=z.enum(["monday", "sunday", "saturday"]),
)

team = z.obj(
    invites=z.array(z.obj(email=z.string().email(), role=z.enum(["admin", "member"]))).max(20)
    .refine(lambda items: len({i["email"].lower() for i in items}) == len(items), "Each email once."),
)

first_form = z.obj(
    choice=z.enum(["blank", "template"]).nullable(),
    template_key=z.enum(STARTER_TEMPLATE_KEYS).nullable(),
)

patch = z.obj(
    step=z.enum(ONBOARDING_STEPS),
    action=z.enum(["save", "skip"]),
    data=z.unknown().optional(),
)

SCHEMAS = {"company": company, "branding": branding, "localisation": localisation, "team": team,
           "first_form": first_form, "patch": patch}

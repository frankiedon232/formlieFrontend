"""FormSchema v1 (API-CONTRACT → FormSchema), ported line by line from the frontend's shared/utils/forms/schema.ts
with app/core/zod.py and held to zod's answers (tests/parity/test_forms_rules.py).

Deliberately tolerant about field props (the builder owns the details) but strict about structure, ids and sizes,
so an imported file can never smuggle in something unexpected: unknown keys are dropped, like zod does.
One deliberate difference: the thank-you redirect must be a web address (http or https); zod's z.url() also takes
javascript: and others, which a form must never send people to.
"""

from __future__ import annotations

import secrets
from typing import Any

from app.core import zod as z
from app.modules.forms.catalogues import BLANK_SCHEMAS, MAX_LARGE_OPTIONS, MAX_LIST_LEVELS

_ID = r"^[A-Za-z0-9_-]{1,64}$"
ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def _id() -> z.Schema:
    return z.string().regex(_ID)


def _text(size: int) -> z.String:
    return z.string().max(size)


def _record_of(value: z.Schema) -> z.Schema:
    return z.record(z.string(), value)


form_field = z.obj(
    id=_id(),
    key=z.string().regex(r"^[a-z][a-z0-9_]{0,63}$"),
    type=z.string().regex(r"^[a-z_]{2,32}$"),
    label=_text(500),
    placeholder=_text(500).optional(),
    help=_text(2000).optional(),
    width=z.number().int().min(1).max(12).optional(),
    required=z.boolean().optional(),
    readonly=z.boolean().optional(),
    disabled=z.boolean().optional(),
    audience=z.obj(
        mode=z.enum(["everyone", "department", "job_title", "role", "user"]),
        all=z.boolean().optional(),
        ids=z.array(z.string().max(100)).max(500).optional(),
    ).optional(),
    validation=_record_of(z.unknown()).optional(),
    options=z.array(z.obj(
        value=_text(200), label=_text(500), score=z.number().optional(), parent=_text(200).optional(),
        attrs=z.record(z.string().max(40), z.union([z.string().max(500), z.number()])).optional(),
    )).max(MAX_LARGE_OPTIONS).nullable().optional(),
    options_remote=z.obj(total=z.number().int().min(0)).nullable().optional(),
    options_large=z.obj(total=z.number().int().min(0), parents=z.array(_text(200)).optional(),
                        partial=z.boolean().optional()).nullable().optional(),
    option_set_id=z.string().nullable().optional(),
    option_level=z.number().int().min(0).max(MAX_LIST_LEVELS - 1).optional(),
    option_parent=z.string().max(64).nullable().optional(),
    default=z.unknown().optional(),
    props=_record_of(z.unknown()).optional(),
)

form_schema_v1 = z.obj(
    schema_version=z.literal(1),
    settings=z.obj(
        progress_bar=z.boolean().optional(),
        save_resume=z.boolean().optional(),
        repeat=z.boolean().optional(),
        language=_text(10).optional(),
        languages=z.array(_text(10)).max(19).optional(),
        title=_text(200).optional(),
        label_position=z.enum(["top", "left"]).optional(),
        field_icons=z.boolean().optional(),
        identity=z.obj(email=_text(64).nullable(), verify=z.boolean()).optional(),
        retention_days=z.number().int().min(0).max(3650).nullable().optional(),
        emails=z.obj(
            team=z.array(z.string().max(64)).max(50),
            others=z.array(z.string().email().max(200)).max(20),
            others_personal=z.boolean(),
            receipt_field=_text(64).nullable(),
        ).optional(),
        guide=z.obj(enabled=z.boolean(), title=_text(120), html=_text(50_000)).optional(),
    ).optional(),
    pages=z.array(z.obj(
        id=_id(),
        title=_text(200).optional(),
        rows=z.array(z.obj(id=_id(), fields=z.array(form_field).max(12))).max(200),
    )).min(1).max(50),
    logic=z.array(z.unknown()).max(500).optional(),
    theme=_record_of(z.unknown()).optional(),
    theme_id=z.string().max(64).nullable().optional(),
    page_design_id=z.string().max(64).nullable().optional(),
    calculations=z.array(z.unknown()).max(200).optional(),
    translations=z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(50_000))).optional(),
    translated_from=z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(16))).optional(),
    thank_you=z.obj(
        title=_text(200).optional(),
        message=_text(5000).optional(),
        redirect_url=z.string().url().nullable().optional(),
    ).optional(),
)


def count_fields(schema: dict[str, Any]) -> int:
    return sum(len(row["fields"]) for page in schema["pages"] for row in page["rows"])


def all_fields(schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every field of every page, in order (build.ts allFields)."""
    if not schema:
        return []
    return [field for page in schema.get("pages", []) for row in page.get("rows", []) for field in row.get("fields", [])]


def new_id(prefix: str) -> str:
    """newId(): `pg_`, `row_`, `fld_`, `rule_` and ten random letters or digits."""
    return f"{prefix}_{''.join(secrets.choice(ID_ALPHABET) for _ in range(10))}"


def blank_schema(language: str = "en") -> dict[str, Any]:
    """The mock's blankFormSchema: one empty page, its texts in the creator's language (English otherwise)."""
    import copy

    schema = copy.deepcopy(BLANK_SCHEMAS.get(language) or BLANK_SCHEMAS["en"])
    schema["pages"][0]["id"] = new_id("pg")
    return schema

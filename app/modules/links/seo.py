"""Search & link preview of a form (mock: data/formSeo.ts, decision 95): what people see when the link is shared and
in search results. Empty title / description = taken from the form: its title shown to respondents, its first text
block or header subtitle. Public pages use only the published version, so draft text never leaks."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forms.models import Form, FormVersion

SEO_TITLE_MAX = 70
SEO_DESCRIPTION_MAX = 200


async def published_schema(db: AsyncSession, form: Form) -> dict[str, Any] | None:
    if not form.published_version_id:
        return None
    version = await db.get(FormVersion, form.published_version_id)
    return version.schema if version else None


def _summary(schema: dict[str, Any] | None) -> str:
    """Plain text from the first paragraph block (else the header subtitle)."""
    intro = next((f for p in (schema or {}).get("pages", []) for r in p.get("rows", []) for f in r.get("fields", [])
                  if f.get("type") == "paragraph"), None)
    html = str(((intro or {}).get("props") or {}).get("html") or "")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    theme = (schema or {}).get("theme")
    header = theme.get("header") if isinstance(theme, dict) else None
    subtitle = str((header or {}).get("subtitle") or "").strip() if isinstance(header, dict) else ""
    return (text or subtitle)[:SEO_DESCRIPTION_MAX]


def defaults_from(form: Form, schema: dict[str, Any] | None) -> dict[str, str]:
    title = str(((schema or {}).get("settings") or {}).get("title") or "").strip()
    return {"title": (title or form.name)[:SEO_TITLE_MAX], "description": _summary(schema)}


async def seo_defaults(db: AsyncSession, form: Form, published_only: bool = False) -> dict[str, str]:
    """The form's own title and intro (published version first; `published_only`: never the draft)."""
    schema = await published_schema(db, form)
    return defaults_from(form, schema if published_only else (schema or form.draft_schema))


async def seo_of(db: AsyncSession, form: Form, published_only: bool = False) -> dict[str, Any]:
    """The link preview as shown: the creator's text where set, the defaults otherwise."""
    defaults = await seo_defaults(db, form, published_only)
    seo = form.seo or {}
    return {"title": (seo.get("title") or "").strip() or defaults["title"],
            "description": (seo.get("description") or "").strip() or defaults["description"],
            "image_upload_id": seo.get("image_upload_id"), "noindex": bool(seo.get("noindex"))}

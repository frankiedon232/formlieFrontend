"""The help centre's content in one language (the mock's `helpContent`), read from the global help tables and
cached in Redis (CLAUDE.md rule 10: `fm:v1:platform:help:…`, one version counter for all of it).

Item by item, a language falls back to English: an article, FAQ, term or tour that isn't translated yet comes in
English (`language: "en"` on articles). Structure (area, page, related, order, tour targets) always comes from
the item itself, the words from the translation. The glossary is sorted in the reader's language with
PostgreSQL's ICU collation (the mock's `localeCompare`).

`invalidate()` drops every cached help answer; app/modules/platform/published.py calls it when the platform
admin publishes help tables (`platform.published`), and the seeder's script calls it after a reload.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.cache.tiers import RedisCache
from app.core.locales import APP_LOCALES

MODULE = "help"
TTL_SECONDS = 3600
LANGUAGES = tuple(locale["code"] for locale in APP_LOCALES)
P = "platform"

_cache = RedisCache()
_collations: dict[str, str | None] = {}


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lang_of(query: dict[str, Any]) -> str:
    """`lang` when it is one of the 20 languages, else English."""
    value = query.get("lang")
    return value if isinstance(value, str) and value in LANGUAGES else "en"


async def invalidate() -> None:
    await _cache.invalidate(None, MODULE)


async def cached(item: str, loader: Any) -> Any:
    return await _cache.get_or_set(None, MODULE, item, loader, ttl_seconds=TTL_SECONDS)


async def _collation(db: Any, lang: str) -> str | None:
    """The ICU collation for a language (`zh-CN` → `zh-x-icu`), else the root one, else none."""
    if lang not in _collations:
        wanted = [f"{lang.split('-')[0]}-x-icu", "und-x-icu"]
        found = {row[0] for row in (await db.execute(text(
            "SELECT collname FROM pg_collation WHERE collname = ANY(:names)"), {"names": wanted})).all()}
        _collations[lang] = next((name for name in wanted if name in found), None)
    return _collations[lang]


async def load(db: Any, lang: str) -> dict[str, Any]:
    """Articles (with their blocks, in order), FAQs, the sorted glossary and the tours, in `lang`."""
    params = {"lang": lang}
    rows = (await db.execute(text(f"""
        SELECT a.id, a.category, a.route, a.related, a.start_order, a.popular, a.minutes,
               CASE WHEN l.article_id IS NULL THEN 'en' ELSE l.language END AS language,
               coalesce(l.title, e.title) AS title, coalesce(l.summary, e.summary) AS summary,
               coalesce(l.keywords, e.keywords) AS keywords, coalesce(l.blocks, e.blocks) AS blocks,
               greatest(a.updated_at, coalesce(l.updated_at, e.updated_at)) AS updated_at
          FROM {P}.help_articles a
          JOIN {P}.help_categories c ON c.key = a.category
          LEFT JOIN {P}.help_article_translations l ON l.article_id = a.id AND l.language = :lang
          LEFT JOIN {P}.help_article_translations e ON e.article_id = a.id AND e.language = 'en'
         WHERE a.retired_at IS NULL AND (l.article_id IS NOT NULL OR e.article_id IS NOT NULL)
         ORDER BY a.sort, a.id"""), params)).mappings().all()
    articles = [{
        "id": r["id"], "category": r["category"], "title": r["title"], "summary": r["summary"],
        "minutes": r["minutes"], "updated_at": iso(r["updated_at"]), "language": r["language"],
        "route": r["route"], "related": list(r["related"] or []), "keywords": list(r["keywords"] or []),
        "blocks": r["blocks"] if not isinstance(r["blocks"], str) else json.loads(r["blocks"]),
        "start": r["start_order"], "popular": bool(r["popular"]),
    } for r in rows]

    faqs = [dict(r) for r in (await db.execute(text(f"""
        SELECT f.id, f.category, coalesce(l.question, e.question) AS question, coalesce(l.answer, e.answer) AS answer,
               f.article_id AS article
          FROM {P}.help_faqs f
          LEFT JOIN {P}.help_faq_translations l ON l.faq_id = f.id AND l.language = :lang
          LEFT JOIN {P}.help_faq_translations e ON e.faq_id = f.id AND e.language = 'en'
         WHERE f.retired_at IS NULL AND (l.faq_id IS NOT NULL OR e.faq_id IS NOT NULL)
         ORDER BY f.sort, f.id"""), params)).mappings().all()]

    collation = await _collation(db, lang)
    order = f'coalesce(l.term, e.term) COLLATE "{collation}", ' if collation else ""
    glossary = [dict(r) for r in (await db.execute(text(f"""
        SELECT g.id, coalesce(l.term, e.term) AS term, coalesce(l.definition, e.definition) AS definition,
               g.article_id AS article
          FROM {P}.help_glossary g
          LEFT JOIN {P}.help_glossary_translations l ON l.term_id = g.id AND l.language = :lang
          LEFT JOIN {P}.help_glossary_translations e ON e.term_id = g.id AND e.language = 'en'
         WHERE g.retired_at IS NULL AND (l.term_id IS NOT NULL OR e.term_id IS NOT NULL)
         ORDER BY {order}g.sort, g.id"""), params)).mappings().all()]

    tours = []
    for r in (await db.execute(text(f"""
        SELECT t.id, t.route, t.targets, coalesce(l.title, e.title) AS title, l.steps AS local_steps, e.steps AS steps
          FROM {P}.help_tours t
          LEFT JOIN {P}.help_tour_translations l ON l.tour_id = t.id AND l.language = :lang
          LEFT JOIN {P}.help_tour_translations e ON e.tour_id = t.id AND e.language = 'en'
         WHERE t.retired_at IS NULL AND (l.tour_id IS NOT NULL OR e.tour_id IS NOT NULL)
         ORDER BY t.sort, t.id"""), params)).mappings():
        source, local = _json(r["steps"]) or [], _json(r["local_steps"]) or []
        steps = []
        for index, target in enumerate(r["targets"] or []):
            words = local[index] if index < len(local) else {}
            fallback = source[index] if index < len(source) else {}
            steps.append({"target": target, "title": _pick(words, fallback, "title"),
                          "text": _pick(words, fallback, "text")})
        tours.append({"id": r["id"], "route": r["route"], "title": r["title"], "steps": steps})

    return {"articles": articles, "faqs": faqs, "glossary": glossary, "tours": tours}


def _pick(words: dict[str, Any], fallback: dict[str, Any], key: str) -> str:
    """The translation's words, the source's where the translation has none (the mock's `??`)."""
    value = words.get(key)
    return value if value is not None else fallback.get(key, "")


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def summary(article: dict[str, Any]) -> dict[str, Any]:
    """HelpArticleSummary."""
    return {key: article[key] for key in ("id", "category", "title", "summary", "minutes", "updated_at", "language")}


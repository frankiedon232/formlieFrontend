"""Loads the shipped help centre (app/modules/help/data/{lang}.json, the mock's files copied by
scripts/sync_frontend_data.py) into the global help tables. Migration 0033 runs it on a new database;
scripts/seed_help.py runs it again after a sync.

- English is the source: areas, articles' structure (area, page, related, "New here?" order, popular, minutes),
  FAQs' area and article, the glossary's article, tours' pages and the controls their steps point at. The other
  languages bring the words (title, summary, keywords, blocks; question and answer; term and definition; the
  tour's title and its steps' title and text), like the mock's `helpContent`.
- Rows the Formalie team published from the platform admin (`published_by_staff_id` set) are never overwritten;
  shipped rows are updated only when their content changed (then `updated_at` moves on).
- Items no longer shipped are retired (`retired_at`), never deleted; shipped again, they come back.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.locales import APP_LOCALES
from app.modules.help.rules import HELP_CATEGORIES

DATA = Path(__file__).resolve().parent / "data"
P = "platform"
# When the shipped content was published (the mock's HELP_UPDATED_AT)
SHIPPED_AT = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


@lru_cache(maxsize=1)
def shipped() -> dict[str, dict[str, Any]]:
    """Every language's file, English first."""
    codes = [locale["code"] for locale in APP_LOCALES]
    files = {code: json.loads((DATA / f"{code}.json").read_text(encoding="utf-8"))
             for code in codes if (DATA / f"{code}.json").exists()}
    if "en" not in files:
        raise RuntimeError(f"The English help file is missing in {DATA}")
    return {"en": files.pop("en"), **files}


def _upsert(conn: Connection, table: str, keys: tuple[str, ...], rows: list[dict[str, Any]],
            casts: dict[str, str] | None = None) -> None:
    if not rows:
        return
    casts = casts or {}
    columns = list(rows[0])
    values = ", ".join(f"CAST(:{c} AS {casts[c]})" if c in casts else f":{c}" for c in columns)
    changing = [c for c in columns if c not in keys and c not in ("updated_at", "created_at")]
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in changing)
    differs = " OR ".join(f"t.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in changing)
    retired = ", retired_at = NULL" if "sort" in columns and table not in ("help_categories",) else ""
    revive = " OR t.retired_at IS NOT NULL" if retired else ""
    conn.execute(text(
        f"INSERT INTO {P}.{table} AS t ({', '.join(columns)}) VALUES ({values}) "
        f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {sets}, updated_at = now(){retired} "
        f"WHERE t.published_by_staff_id IS NULL AND ({differs}{revive})"), rows)


def _retire(conn: Connection, table: str, ids: list[str]) -> None:
    conn.execute(text(f"UPDATE {P}.{table} SET retired_at = now() WHERE id <> ALL(:ids) AND retired_at IS NULL "
                      "AND published_by_staff_id IS NULL"), {"ids": ids})


def seed_help(conn: Connection) -> dict[str, int]:
    """Loads or refreshes the shipped content; returns how many rows of each kind it offered."""
    files = shipped()
    en = files["en"]
    stamp = {"created_at": SHIPPED_AT, "updated_at": SHIPPED_AT}

    _upsert(conn, "help_categories", ("key",), [{"key": key, "sort": i, **stamp} for i, key in enumerate(HELP_CATEGORIES)])

    articles = en["articles"]
    _upsert(conn, "help_articles", ("id",), [{
        "id": a["id"], "category": a["category"], "route": a.get("route") or None, "related": list(a.get("related") or []),
        "start_order": a.get("start"), "popular": bool(a.get("popular")), "minutes": a["minutes"], "sort": i, **stamp,
    } for i, a in enumerate(articles)])
    ids = {a["id"] for a in articles}
    translations = [{
        "article_id": a["id"], "language": lang, "title": a["title"], "summary": a["summary"],
        "keywords": list(a.get("keywords") or []), "blocks": json.dumps(a["blocks"], ensure_ascii=False), **stamp,
    } for lang, content in files.items() for a in content["articles"] if a["id"] in ids]
    _upsert(conn, "help_article_translations", ("article_id", "language"), translations, {"blocks": "jsonb"})

    faqs = en["faqs"]
    _upsert(conn, "help_faqs", ("id",), [{"id": f["id"], "category": f["category"], "article_id": f.get("article"),
                                          "sort": i, **stamp} for i, f in enumerate(faqs)])
    faq_ids = {f["id"] for f in faqs}
    _upsert(conn, "help_faq_translations", ("faq_id", "language"), [{
        "faq_id": f["id"], "language": lang, "question": f["question"], "answer": f["answer"], **stamp,
    } for lang, content in files.items() for f in content["faqs"] if f["id"] in faq_ids])

    terms = en["glossary"]
    _upsert(conn, "help_glossary", ("id",), [{"id": t["id"], "article_id": t.get("article"), "sort": i, **stamp}
                                             for i, t in enumerate(terms)])
    term_ids = {t["id"] for t in terms}
    _upsert(conn, "help_glossary_translations", ("term_id", "language"), [{
        "term_id": t["id"], "language": lang, "term": t["term"], "definition": t["definition"], **stamp,
    } for lang, content in files.items() for t in content["glossary"] if t["id"] in term_ids])

    tours = en.get("tours") or []
    _upsert(conn, "help_tours", ("id",), [{"id": t["id"], "route": t["route"],
                                           "targets": [s["target"] for s in t["steps"]], "sort": i, **stamp}
                                          for i, t in enumerate(tours)])
    tour_ids = {t["id"] for t in tours}
    _upsert(conn, "help_tour_translations", ("tour_id", "language"), [{
        "tour_id": t["id"], "language": lang, "title": t["title"],
        "steps": json.dumps([{"title": s["title"], "text": s["text"]} for s in t["steps"]], ensure_ascii=False), **stamp,
    } for lang, content in files.items() for t in content.get("tours") or [] if t["id"] in tour_ids], {"steps": "jsonb"})

    for table, kept in (("help_articles", ids), ("help_faqs", faq_ids), ("help_glossary", term_ids),
                        ("help_tours", tour_ids)):
        _retire(conn, table, sorted(kept))
    return {"articles": len(articles), "translations": len(translations), "faqs": len(faqs), "glossary": len(terms),
            "tours": len(tours), "languages": len(files)}

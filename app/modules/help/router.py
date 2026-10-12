"""Help centre (mock: server/mock/routes/help.ts, API-CONTRACT → Help centre). Read-only content for every
signed-in person (no permission needed), in the language asked for (`lang`, English when an item isn't
translated yet). Tips on new pages (`/me/tours`) are in app/modules/people/me.py.

    GET  /help/home                    areas with counts, the "New here?" path, popular, recently updated, support
    GET  /help/articles?category       summaries
    GET  /help/articles/{id}           one article with related ones and your "Was this helpful?" answer
    POST /help/articles/{id}/feedback  { helpful, comment? }, one answer per person and article
    GET  /help/search?q                articles (with a snippet), FAQs, glossary terms and a short answer; a search
                                       that finds nothing is recorded for the Formalie team
    GET  /help/faqs?category · /help/glossary
    GET  /help/context?path            the article for a page, more for it, and its tour
    GET  /help/tours                   every guided tour
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text

from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.ids import uuid7
from app.core.js import trim, utf16_len, utf16_slice
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.help import content as C
from app.modules.help import search as S
from app.modules.help.models import HelpFeedback
from app.modules.help.rules import HELP_CATEGORIES, answer_for, article_text, route_matches, search_terms, snippet

router = APIRouter(tags=["help"])
log = logging.getLogger("formalie.help")

feedback_schema = z.obj(helpful=z.boolean(), comment=z.string().trim().max(1000).nullable().optional())


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _query(request: Request) -> dict[str, str]:
    return dict(request.query_params)


async def _content(principal: Principal, lang: str) -> dict[str, Any]:
    async def loader() -> dict[str, Any]:
        async with db_session("read", **_scope(principal)) as db:
            return await C.load(db, lang)
    return await C.cached(f"content:{lang}", loader)


async def _helpful(principal: Principal, article_id: str) -> bool | None:
    async with db_session("read", **_scope(principal)) as db:
        return (await db.execute(select(HelpFeedback.helpful).where(
            HelpFeedback.tenant_id == principal.tenant.id, HelpFeedback.user_id == principal.user.id,
            HelpFeedback.article_id == article_id, HelpFeedback.deleted_at.is_(None)))).scalar_one_or_none()


def _full(article: dict[str, Any], articles: list[dict[str, Any]], helpful: bool | None) -> dict[str, Any]:
    """HelpArticle: the summary, its blocks, the page it explains, related summaries, your answer."""
    by_id = {item["id"]: item for item in articles}
    return {**C.summary(article), "blocks": article["blocks"], "route": article["route"],
            "related": [C.summary(by_id[i]) for i in article["related"] if i in by_id], "helpful": helpful}


@router.get("/help/home", dependencies=[rate_limit("help-home", per_minute=120)])
async def help_home(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    articles = (await _content(principal, C.lang_of(_query(request))))["articles"]
    settings = get_settings()
    start = sorted((a for a in articles if a["start"]), key=lambda a: a["start"])
    # Recently updated: newest first; equal times keep the reverse of the articles' order (the mock's last four)
    updated = sorted(enumerate(articles), key=lambda item: (item[1]["updated_at"], item[0]), reverse=True)[:4]
    counts = [{"key": key, "count": sum(1 for a in articles if a["category"] == key)} for key in HELP_CATEGORIES]
    return ok({
        "categories": [item for item in counts if item["count"]],
        "start": [C.summary(a) for a in start],
        "popular": [C.summary(a) for a in articles if a["popular"] and not a["start"]][:8],
        "updated": [C.summary(a) for _, a in updated],
        "support": {"email": settings.support_email or None, "url": settings.support_url or None},
    })


@router.get("/help/articles", dependencies=[rate_limit("help-articles", per_minute=120)])
async def list_help_articles(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = _query(request)
    category = query.get("category")
    articles = (await _content(principal, C.lang_of(query)))["articles"]
    return ok([C.summary(a) for a in articles if not category or a["category"] == category])


@router.get("/help/articles/{article_id}", dependencies=[rate_limit("help-article", per_minute=120)])
async def get_help_article(article_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    articles = (await _content(principal, C.lang_of(_query(request))))["articles"]
    article = next((a for a in articles if a["id"] == article_id), None)
    if article is None:
        raise FrmError("FRM-GEN-1004")
    return ok(_full(article, articles, await _helpful(principal, article_id)))


@router.post("/help/articles/{article_id}/feedback", dependencies=[rate_limit("help-feedback", per_minute=30)])
async def help_feedback(article_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    articles = (await _content(principal, "en"))["articles"]
    if not any(a["id"] == article_id for a in articles):
        raise FrmError("FRM-GEN-1004")
    body = feedback_schema.parse(await request.json())
    comment = body.get("comment") or None
    lang = C.lang_of(_query(request))
    async with db_session("write", **_scope(principal)) as db:
        row = (await db.execute(select(HelpFeedback).where(
            HelpFeedback.tenant_id == principal.tenant.id, HelpFeedback.user_id == principal.user.id,
            HelpFeedback.article_id == article_id, HelpFeedback.deleted_at.is_(None)))).scalar_one_or_none()
        if row is None:
            db.add(HelpFeedback(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                                user_id=principal.user.id, article_id=article_id, language=lang,
                                helpful=body["helpful"], comment=comment, created_by=principal.user.id))
        else:
            row.helpful, row.comment, row.language, row.updated_by = body["helpful"], comment, lang, principal.user.id
        await db.flush()
    return ok({"saved": True})


async def _record_miss(principal: Principal, lang: str, q: str) -> None:
    """A search that found nothing, for the Formalie team (lower case, at most 120 characters, 3 or more)."""
    key = utf16_slice(trim(q).lower(), 120)
    if utf16_len(key) < 3:
        return
    try:
        async with db_session("write", **_scope(principal)) as db:
            await db.execute(text(
                "INSERT INTO platform.help_search_misses AS m (id, language, query_norm) VALUES (:id, :lang, :q) "
                "ON CONFLICT (language, query_norm) DO UPDATE SET count = m.count + 1, last_at = now()"),
                {"id": uuid7(), "lang": lang, "q": key})
    except Exception:  # noqa: BLE001  (recording a miss never fails a search)
        log.exception("help search miss not recorded")


@router.get("/help/search", dependencies=[rate_limit("help-search", per_minute=120)])
async def search_help(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = _query(request)
    q = utf16_slice(trim(query.get("q") or ""), 200)
    lang = C.lang_of(query)

    async def loader() -> dict[str, Any]:
        content = await _content(principal, lang)
        asked = search_terms(q)
        async with db_session("read", **_scope(principal)) as db:
            ranked = S.best_articles(await S.rank_articles(db, lang, asked))
            faq_ids = await S.rank_faqs(db, lang, asked)
            term_ids = await S.rank_terms(db, lang, asked)
        by_id = {a["id"]: a for a in content["articles"]}
        found = [by_id[i] for i in ranked if i in by_id]
        faqs = {f["id"]: f for f in content["faqs"]}
        terms = {t["id"]: t for t in content["glossary"]}
        best = found[0] if found else None
        return {
            "query": q,
            "articles": [{**C.summary(a), "snippet": snippet(article_text(a["blocks"]), asked, a["summary"])}
                         for a in found],
            "faqs": [faqs[i] for i in faq_ids if i in faqs],
            "terms": [terms[i] for i in term_ids if i in terms],
            "answer": answer_for(q, asked, best, C.summary(best) if best else None),
        }

    if q:
        digest = hashlib.sha256(q.encode("utf-8")).hexdigest()[:32]
        result = await C.cached(f"search:{lang}:{digest}", loader)
    else:
        result = {"query": q, "articles": [], "faqs": [], "terms": [], "answer": None}
    if q and not (result["articles"] or result["faqs"] or result["terms"]):
        await _record_miss(principal, lang, q)
    return ok(result)


@router.get("/help/faqs", dependencies=[rate_limit("help-faqs", per_minute=120)])
async def list_help_faqs(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = _query(request)
    category = query.get("category")
    faqs = (await _content(principal, C.lang_of(query)))["faqs"]
    return ok([f for f in faqs if not category or f["category"] == category])


@router.get("/help/glossary", dependencies=[rate_limit("help-glossary", per_minute=120)])
async def list_help_glossary(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok((await _content(principal, C.lang_of(_query(request))))["glossary"])


@router.get("/help/tours", dependencies=[rate_limit("help-tours", per_minute=120)])
async def help_tours(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    return ok((await _content(principal, C.lang_of(_query(request))))["tours"])


@router.get("/help/context", dependencies=[rate_limit("help-context", per_minute=240)])
async def help_context(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = _query(request)
    path = query["path"].split("?")[0] if "path" in query else "/"
    content = await _content(principal, C.lang_of(query))
    articles = content["articles"]
    # The page's own articles; Getting started ones only when nothing else explains it
    found = sorted((a for a in articles if a["route"] and route_matches(a["route"], path)),
                   key=lambda a: (a["category"] == "start", not a["popular"]))
    main = found[0] if found else None
    return ok({
        "article": _full(main, articles, await _helpful(principal, main["id"])) if main else None,
        "more": [C.summary(a) for a in found[1:5]],
        "tour": next((t for t in content["tours"] if route_matches(t["route"], path)), None),
    })

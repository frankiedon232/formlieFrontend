"""Help centre and tours (B14) against the migrated test database: the mock's content and answers in all 20
languages (tests/vectors/help_rules.json, recorded by scripts/dump_help_rules.py), "Was this helpful?" per person
and workspace, search in English, Arabic and Chinese, missed searches, retired content, the cache and its
invalidation on `platform.published`."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psycopg
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db.engines import async_url
from app.core.security import limits
from app.modules.help import content as C
from app.modules.help.seed import seed_help
from app.modules.platform.published import handle_published
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db

V = json.loads((Path(__file__).parents[1] / "vectors" / "help_rules.json").read_text(encoding="utf-8"))
SUMMARY_KEYS = {"id", "category", "title", "summary", "minutes", "updated_at", "language"}


def sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


@pytest.fixture
def unlimited(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thousands of reads in one test: the per-route limits are tested elsewhere."""
    async def allow(*_: Any) -> None:
        return None
    monkeypatch.setattr(limits, "check", allow)


@asynccontextmanager
async def person(app) -> AsyncIterator[tuple[SecureClient, str]]:  # noqa: ANN001
    """A new workspace's Owner, signed in: (client, subdomain)."""
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        client = SecureClient(http)
        await sign_in(client, email, PASSWORD)
        yield client, sub


async def get(client: SecureClient, route: str, /, **query: str) -> Any:
    status, reply = await client.request("GET", route, query=query or None)
    assert status == 200, (route, query, reply)
    return reply["data"]


async def test_content_matches_the_mock_in_every_language(app, unlimited) -> None:  # noqa: ANN001
    async with person(app) as (client, _):
        mismatches: list[str] = []
        for lang, expected in V["hashes"].items():
            got = {
                "home": await get(client, "/help/home", lang=lang),
                "articles": await get(client, "/help/articles", lang=lang),
                "faqs": await get(client, "/help/faqs", lang=lang),
                "glossary": await get(client, "/help/glossary", lang=lang),
                "tours": await get(client, "/help/tours", lang=lang),
            }
            for key, value in got.items():
                if sha(value) != expected[key]:
                    mismatches.append(f"{lang} {key}")
            for category, digest in expected["by_category"].items():
                if sha(await get(client, "/help/articles", lang=lang, category=category)) != digest:
                    mismatches.append(f"{lang} articles?category={category}")
            for category, digest in expected["faqs_by_category"].items():
                if sha(await get(client, "/help/faqs", lang=lang, category=category)) != digest:
                    mismatches.append(f"{lang} faqs?category={category}")
            for article_id, digest in expected["article"].items():
                if sha(await get(client, f"/help/articles/{article_id}", lang=lang)) != digest:
                    mismatches.append(f"{lang} article {article_id}")
            for page, digest in expected["context"].items():
                if sha(await get(client, "/help/context", lang=lang, path=page)) != digest:
                    mismatches.append(f"{lang} context {page!r}")
            counts = V["counts"][lang]
            assert len(got["articles"]) == counts["articles"] and len(got["faqs"]) == counts["faqs"]
            assert len(got["glossary"]) == counts["glossary"] and len(got["tours"]) == counts["tours"]
            assert sum(a["language"] == lang for a in got["articles"]) == counts["translated"]
        assert not mismatches, mismatches[:40]

        # Unknown or missing language: English
        assert sha(await get(client, "/help/home", lang="xx")) == V["fallback"]["unknown"]
        assert sha(await get(client, "/help/home")) == V["fallback"]["none"]


async def test_shapes_and_english_answers(app) -> None:  # noqa: ANN001
    full = V["full"]["en"]
    async with person(app) as (client, sub):
        home = await get(client, "/help/home", lang="en")
        assert set(home) == {"categories", "start", "popular", "updated", "support"} and home == full["home"]
        assert home["support"] == {"email": "support@formalie.com", "url": None}
        assert all(set(item) == SUMMARY_KEYS for item in home["start"] + home["popular"] + home["updated"])
        article = await get(client, "/help/articles/first-form", lang="en")
        assert set(article) == SUMMARY_KEYS | {"blocks", "related", "route", "helpful"}
        assert article == full["article"]["first-form"]
        assert await get(client, "/help/tours", lang="en") == full["tours"]
        assert all(set(t) == {"id", "route", "title", "steps"} and all(set(s) == {"target", "title", "text"}
                                                                       for s in t["steps"]) for t in full["tours"])
        assert await get(client, "/help/glossary", lang="en") == full["glossary"]
        assert await get(client, "/help/context", lang="en", path="/forms/f_123/build") == full["context"]["/forms/f_123/build"]
        context = await get(client, "/help/context", lang="en", path="/nowhere")
        assert context == {"article": None, "more": [], "tour": None}

        status, reply = await client.request("GET", "/help/articles/nope")
        assert status == 404 and reply["error"]["code"] == "FRM-GEN-1004"
        assert await get(client, "/help/articles", category="nope") == []

    async with client_for(app, host=f"{sub}.formalie.dev") as anonymous:
        status, reply = await SecureClient(anonymous).request("GET", "/help/home")
        assert status == 401 and reply["error"]["code"].startswith("FRM-AUTH-"), reply


async def test_feedback_is_per_person_and_workspace(app, superuser: psycopg.Connection, app_dsn: str) -> None:  # noqa: ANN001
    async with person(app) as (first, first_sub), person(app) as (second, _):
        _, reply = await first.request("POST", "/help/articles/first-form/feedback", body={"helpful": "yes"})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await first.request("POST", "/help/articles/nope/feedback", body={"helpful": True})
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await first.request("POST", "/help/articles/first-form/feedback",
                                       body={"helpful": False, "comment": "  Missing the import step  "})
        assert reply["data"] == {"saved": True}
        _, reply = await first.request("POST", "/help/articles/first-form/feedback", body={"helpful": True, "comment": ""})
        assert reply["data"] == {"saved": True}

        assert (await get(first, "/help/articles/first-form"))["helpful"] is True
        assert (await get(first, "/help/context", path="/forms/new"))["article"]["helpful"] is True
        # Another workspace's person: their own answer only
        assert (await get(second, "/help/articles/first-form"))["helpful"] is None
        await second.request("POST", "/help/articles/first-form/feedback", body={"helpful": False})
        assert (await get(second, "/help/articles/first-form"))["helpful"] is False
        assert (await get(first, "/help/articles/first-form"))["helpful"] is True

    rows = superuser.execute(
        "SELECT f.helpful, f.comment, t.subdomain FROM formaly.help_feedback f JOIN platform.tenants t ON t.id = f.tenant_id "
        "WHERE f.article_id = 'first-form' AND t.subdomain = %s", (first_sub,)).fetchall()
    assert rows == [(True, None, first_sub)]  # one answer per person, the new one replaced the old

    # Row-level security: a workspace sees only its own answers; the app can't change the global content
    tenant, organisation = superuser.execute(
        "SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s", (first_sub,)).fetchone()
    with psycopg.connect(app_dsn, autocommit=False) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, true), set_config('app.organisation_id', %s, true)",
                     (str(tenant), str(organisation)))
        assert conn.execute("SELECT count(*), count(DISTINCT tenant_id) FROM formaly.help_feedback").fetchone() == (1, 1)
        conn.rollback()
        assert conn.execute("SELECT count(*) FROM formaly.help_feedback").fetchone()[0] == 0  # no workspace set
        conn.rollback()
        assert conn.execute("SELECT count(*) FROM platform.help_articles").fetchone()[0] == 46
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE platform.help_articles SET minutes = 9 WHERE id = 'welcome'")
        conn.rollback()


ENGLISH_TOP = ["create a form", "How do I share a form?", "invite people", "export responses", "webhook", "api token",
               "conditional logic", "two-step sign-in", "folder", "audit trail", "calculations",
               "embed", "versions", "trash", "roles", "data sources", "respon", "keyboard shortcuts", "landing page",
               "publish"]


async def test_search(app, superuser: psycopg.Connection) -> None:  # noqa: ANN001
    recorded = {(s["lang"], s["q"]): s for s in V["searches"]}
    async with person(app) as (client, _):
        # English: the same best article as the mock, its snippet and short answer too
        for q in ENGLISH_TOP:
            mock = recorded[("en", q)]
            result = await get(client, "/help/search", q=q, lang="en")
            assert set(result) == {"query", "articles", "faqs", "terms", "answer"}
            assert result["articles"] and result["articles"][0]["id"] == mock["articles"][0][0], (q, result["articles"])
            assert result["articles"][0]["snippet"] == mock["articles"][0][1], q
            assert {"article": result["answer"]["article"]["id"], "blocks": result["answer"]["blocks"]} == mock["answer"], q
            assert set(result["articles"][0]) == SUMMARY_KEYS | {"snippet"}
            assert len(result["articles"]) <= 8 and len(result["faqs"]) <= 5 and len(result["terms"]) <= 4
        # Stemming: other forms of a word find it too
        assert (await get(client, "/help/search", q="exporting responses"))["articles"][0]["id"] == "export-responses"
        assert (await get(client, "/help/search", q="webhooks"))["terms"][0]["id"] == "term-webhook"
        assert (await get(client, "/help/search", q="How do I reset my password?"))["faqs"][0] == {
            "id": "faq-forgot-password", "category": next(f["category"] for f in V["full"]["en"]["faqs"] if f["id"] == "faq-forgot-password"),
            "question": next(f["question"] for f in V["full"]["en"]["faqs"] if f["id"] == "faq-forgot-password"),
            "answer": next(f["answer"] for f in V["full"]["en"]["faqs"] if f["id"] == "faq-forgot-password"),
            "article": next(f["article"] for f in V["full"]["en"]["faqs"] if f["id"] == "faq-forgot-password")}

        # Arabic and Chinese: an article's title finds it first; English words find articles in any language
        for lang in ("ar", "zh-CN"):
            titles = [s for s in V["searches"] if s["lang"] == lang][:16]
            for case in titles:
                result = await get(client, "/help/search", q=case["q"], lang=lang)
                assert result["articles"][0]["id"] == case["articles"][0][0], (lang, case["q"], result["articles"][:3])
                assert result["articles"][0]["language"] == lang
            webhook = await get(client, "/help/search", q="webhook", lang=lang)
            assert webhook["articles"][0]["id"] == "webhooks"
        # Chinese without spaces: words inside a longer phrase are found
        phrase = [a["id"] for a in (await get(client, "/help/search", q="如何创建表单", lang="zh-CN"))["articles"]]
        assert phrase[0] in {"first-form", "ai-create-form", "builder-basics"} and "first-form" in phrase[:3]
        assert (await get(client, "/help/search", q="导出回复", lang="zh-CN"))["articles"]
        # Arabic with stemming: the plural finds the article on forms
        assert (await get(client, "/help/search", q="النماذج", lang="ar"))["articles"]

        # Nothing found: recorded once per question and language, counted
        empty = await get(client, "/help/search", q="  Xyzzy Plugh  ")
        assert empty == {"query": "Xyzzy Plugh", "articles": [], "faqs": [], "terms": [], "answer": None}
        await get(client, "/help/search", q="xyzzy plugh")
        await get(client, "/help/search", q="xy")
        assert await get(client, "/help/search") == {"query": "", "articles": [], "faqs": [], "terms": [], "answer": None}
    rows = superuser.execute("SELECT count FROM platform.help_search_misses WHERE language = 'en' AND query_norm = 'xyzzy plugh'").fetchall()
    assert rows and rows[0][0] >= 2
    assert not superuser.execute("SELECT 1 FROM platform.help_search_misses WHERE query_norm = 'xy'").fetchall()


async def test_published_content_drops_the_cache_and_retired_items_go(app, superuser: psycopg.Connection) -> None:  # noqa: ANN001
    async with person(app) as (client, _):
        before = await get(client, "/help/articles/trash", lang="fr")
        try:
            superuser.execute("UPDATE platform.help_article_translations SET title = 'Corbeille (nouveau)', "
                              "published_by_staff_id = gen_random_uuid(), published_at = now(), updated_at = now() "
                              "WHERE article_id = 'trash' AND language = 'fr'")
            superuser.execute("UPDATE platform.help_tours SET retired_at = now() WHERE id = 'help-tour'")
            assert (await get(client, "/help/articles/trash", lang="fr"))["title"] == before["title"]  # cached
            assert await handle_published({"table": "help_article_translations", "ids": ["trash"], "version": 2}) == [
                "help_article_translations"]
            after = await get(client, "/help/articles/trash", lang="fr")
            assert after["title"] == "Corbeille (nouveau)" and after["updated_at"] != before["updated_at"]
            assert "help-tour" not in {t["id"] for t in await get(client, "/help/tours", lang="fr")}
            assert await handle_published({"table": "plans"}) == []

            # The seeder never overwrites what the Formalie team published, and brings retired items back
            settings = get_settings()
            url = make_url(async_url(settings.db_owner_url.get_secret_value())).set(database=settings.db_test_database)
            engine = create_async_engine(url)
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(seed_help)
            finally:
                await engine.dispose()
            await C.invalidate()
            assert (await get(client, "/help/articles/trash", lang="fr"))["title"] == "Corbeille (nouveau)"
            assert "help-tour" in {t["id"] for t in await get(client, "/help/tours", lang="fr")}
        finally:
            superuser.execute("UPDATE platform.help_article_translations SET title = %s, published_by_staff_id = NULL, "
                              "published_at = NULL, updated_at = '2026-10-10T09:00:00Z' WHERE article_id = 'trash' "
                              "AND language = 'fr'", (before["title"],))
            superuser.execute("UPDATE platform.help_tours SET retired_at = NULL WHERE id = 'help-tour'")
            await C.invalidate()

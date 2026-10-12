"""Help search with PostgreSQL full text search (B14), with the mock's ranking (server/mock/routes/help.ts):

- The question becomes words (`rules.search_terms`: the mock's words and little words, whole words in every
  script, Chinese and Japanese as pairs of characters).
- Each word that an article's field holds adds the field's weight, like the mock: title 6, keywords 4, summary 3,
  text 1, and outside English the English title and keywords 2 (English words find articles in any language).
  FAQs: question 3, answer 1. Terms: term 4, definition 1.
- A field "holds" a word when PostgreSQL's full text search finds its stem in the language's own configuration
  ("creating" finds "create", "forms" finds "form"), or, for words of 3 or more letters, a word starting with it
  as typed (the mock's partial words: "respon" finds "responses"); Chinese and Japanese pairs are found anywhere
  in the text.
- The best articles: weak matches (under 35 % of the best) left out, at most 8; FAQs 5; terms 4.

The content's weighted vectors are generated columns (`search`, migration 0033), folded like the question
(`platform.help_fold`, `rules.fold`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.core.js import utf16_len
from app.modules.help.rules import is_cjk

P = "platform"
MAX_TERMS = 24


def _prefix_text(word: str) -> str:
    return f"'{word}':*" if utf16_len(word) > 2 else f"'{word}'"


def _terms_cte(terms: list[str]) -> tuple[str, dict[str, Any]]:
    """One row per word: the word, whether it is Chinese or Japanese, and its queries in the reader's language
    and in English. A query finds the word's stem (the language's configuration) or, from 3 letters, a word that
    starts with it as typed (`simple`); the language's own little words ("ein", "le") find nothing."""
    rows, params = [], {}
    for i, word in enumerate(terms[:MAX_TERMS]):
        params[f"w{i}"], params[f"c{i}"], params[f"p{i}"] = word, is_cjk(word), _prefix_text(word)
        rows.append(f"(CAST(:w{i} AS text), CAST(:c{i} AS boolean), CAST(:p{i} AS text))")
    cte = (f"terms AS (SELECT v.w, v.cjk, CASE WHEN numnode(s.l) > 0 THEN s.l || s.p ELSE s.l END AS ql, "
           f"CASE WHEN numnode(s.e) > 0 THEN s.e || s.p ELSE s.e END AS qe "
           f"FROM (VALUES {', '.join(rows)}) AS v(w, cjk, qp) "
           f"CROSS JOIN LATERAL (SELECT to_tsquery({P}.help_search_config(:lang), quote_literal(v.w)) AS l, "
           f"to_tsquery('pg_catalog.english', quote_literal(v.w)) AS e, to_tsquery('pg_catalog.simple', v.qp) AS p) s)")
    return cte, params


def _fts(vector: str, query: str, weights: list[tuple[str, int]]) -> str:
    return " + ".join(f"{weight} * (ts_filter({vector}, '{{{letter}}}') @@ {query})::int" for letter, weight in weights)


def _substring(fields: list[tuple[str, int]]) -> str:
    return " + ".join(f"{weight} * (strpos({P}.help_fold({expr}), t.w) > 0)::int" for expr, weight in fields)


async def _ranked(db: Any, sql: str, params: dict[str, Any]) -> list[tuple[str, int]]:
    return [(row[0], int(row[1])) for row in (await db.execute(text(sql), params)).all()]


async def rank_articles(db: Any, lang: str, terms: list[str]) -> list[tuple[str, int]]:
    """(article id, score) for every article holding a word, best first (ties in the articles' order)."""
    if not terms:
        return []
    cte, params = _terms_cte(terms)
    weights = [("a", 6), ("b", 4), ("c", 3), ("d", 1)]
    source = f" + {_fts('e.search', 't.qe', [('a,b', 2)])}" if lang != "en" else ""
    score = f"""CASE WHEN t.cjk THEN {_substring([("coalesce(l.title, e.title)", 6),
                                                   (f"{P}.help_join(coalesce(l.keywords, e.keywords))", 4),
                                                   ("coalesce(l.summary, e.summary)", 3),
                                                   ("coalesce(l.body, e.body)", 1)])}
                 WHEN l.article_id IS NOT NULL THEN {_fts('l.search', 't.ql', weights)}{source}
                 ELSE {_fts('e.search', 't.qe', weights)}{source} END"""
    sql = f"""WITH {cte}
        SELECT a.id, sum({score}) AS score
          FROM {P}.help_articles a
          JOIN {P}.help_categories c ON c.key = a.category
          LEFT JOIN {P}.help_article_translations l ON l.article_id = a.id AND l.language = :lang
          LEFT JOIN {P}.help_article_translations e ON e.article_id = a.id AND e.language = 'en'
         CROSS JOIN terms t
         WHERE a.retired_at IS NULL AND (l.article_id IS NOT NULL OR e.article_id IS NOT NULL)
         GROUP BY a.id, a.sort
        HAVING sum({score}) > 0
         ORDER BY score DESC, a.sort, a.id"""
    return await _ranked(db, sql, {**params, "lang": lang})


async def _rank_items(db: Any, lang: str, terms: list[str], *, table: str, translations: str, key: str,
                      first: tuple[str, int], second: tuple[str, int], limit: int) -> list[str]:
    if not terms:
        return []
    cte, params = _terms_cte(terms)
    weights = [("a", first[1]), ("d", second[1])]
    score = f"""CASE WHEN t.cjk THEN {_substring([(f"coalesce(l.{first[0]}, e.{first[0]})", first[1]),
                                                   (f"coalesce(l.{second[0]}, e.{second[0]})", second[1])])}
                 WHEN l.{key} IS NOT NULL THEN {_fts('l.search', 't.ql', weights)}
                 ELSE {_fts('e.search', 't.qe', weights)} END"""
    sql = f"""WITH {cte}
        SELECT x.id, sum({score}) AS score
          FROM {P}.{table} x
          LEFT JOIN {P}.{translations} l ON l.{key} = x.id AND l.language = :lang
          LEFT JOIN {P}.{translations} e ON e.{key} = x.id AND e.language = 'en'
         CROSS JOIN terms t
         WHERE x.retired_at IS NULL AND (l.{key} IS NOT NULL OR e.{key} IS NOT NULL)
         GROUP BY x.id, x.sort
        HAVING sum({score}) > 0
         ORDER BY score DESC, x.sort, x.id
         LIMIT {limit}"""
    return [item for item, _ in await _ranked(db, sql, {**params, "lang": lang})]


async def rank_faqs(db: Any, lang: str, terms: list[str]) -> list[str]:
    return await _rank_items(db, lang, terms, table="help_faqs", translations="help_faq_translations", key="faq_id",
                             first=("question", 3), second=("answer", 1), limit=5)


async def rank_terms(db: Any, lang: str, terms: list[str]) -> list[str]:
    return await _rank_items(db, lang, terms, table="help_glossary", translations="help_glossary_translations",
                             key="term_id", first=("term", 4), second=("definition", 1), limit=4)


def best_articles(ranked: list[tuple[str, int]]) -> list[str]:
    """Weak matches (a common word like "form") stay out when something matches clearly; at most 8."""
    if not ranked:
        return []
    top = ranked[0][1]
    return [item for item, value in ranked if value >= top * 0.35][:8]

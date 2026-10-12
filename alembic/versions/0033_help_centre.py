"""Help centre and tours (B14, F25): the published help content in global tables, and what people send back.

Global (schema `platform`, no tenant columns, no RLS; formalie_app reads, platform_writer publishes later):
  help_categories                       the areas, in order
  help_articles · help_article_translations     structure (area, page, related, "New here?" order, popular,
                                        minutes) · per language title, summary, keywords, blocks; `body` and the
                                        weighted full text `search` are generated columns
  help_faqs · help_faq_translations     area and article · per language question and answer
  help_glossary · help_glossary_translations    article · per language term and definition
  help_tours · help_tour_translations   page pattern and the controls each step points at · per language title
                                        and the steps' words
  help_search_misses                    searches that found nothing, per language (formalie_app adds and counts)
  platform.help_fold() · help_blocks_text() · help_join() · help_search_config()    immutable helpers the
                                        generated columns use (the search folds the question the same way)

Tenant table (RLS forced): help_feedback, one "Was this helpful?" answer per person and article.

The content is loaded from app/modules/help/data (the mock's help files, scripts/sync_frontend_data.py) by
app/modules/help/seed.py, so a new database has the mock's help centre. Re-running the seeder
(scripts/seed_help.py) never overwrites what the Formalie team published from the platform admin.

Revision ID: 0033
Revises: 0032
Created: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db.rls import disable_tenant_rls, enable_tenant_rls

revision: str = '0033'
down_revision: str | None = '0032'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
P = "platform"
CONTENT = ("help_categories", "help_articles", "help_article_translations", "help_faqs", "help_faq_translations",
           "help_glossary", "help_glossary_translations", "help_tours", "help_tour_translations")

# PostgreSQL's own text search configurations for the 20 languages; `simple` where it has none
SEARCH_CONFIGS = {"en": "english", "fr": "french", "es": "spanish", "pt": "portuguese", "de": "german",
                  "it": "italian", "nl": "dutch", "ru": "russian", "tr": "turkish", "ar": "arabic", "hi": "hindi",
                  "id": "indonesian"}


def _published() -> list[sa.Column]:
    """Who published it from the platform admin, and when (null: shipped with Formalie by the seeder)."""
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by_staff_id', sa.Uuid(), nullable=True),
    ]


def _fk(column: str, table: str, name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [f'{P}.{table}.id'], ondelete='RESTRICT', name=name)


def _search(*fields: tuple[str, str]) -> sa.Computed:
    parts = [f"setweight(to_tsvector({P}.help_search_config(language), {P}.help_fold({expr})), '{weight}')"
             for expr, weight in fields]
    return sa.Computed(" || ".join(parts), persisted=True)


def upgrade() -> None:
    # ── Helpers for the generated columns (immutable, so PostgreSQL can store their results) ──
    op.execute(rf"""
        CREATE FUNCTION {P}.help_fold(t text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE
        AS $$ SELECT normalize(regexp_replace(normalize(lower(coalesce(t, '')), NFKD), '[̀-ͯ]', '', 'g'), NFC) $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.help_join(items text[]) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE
        AS $$ SELECT coalesce(array_to_string(items, ' '), '') $$
    """)
    op.execute(f"""
        CREATE FUNCTION {P}.help_blocks_text(blocks jsonb) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE
        AS $$
            SELECT replace(coalesce(string_agg(
                CASE WHEN b ? 'text' THEN b->>'text'
                     WHEN b ? 'items' THEN (SELECT string_agg(i, ' ' ORDER BY n)
                                              FROM jsonb_array_elements_text(b->'items') WITH ORDINALITY AS x(i, n))
                     WHEN b ? 'label' THEN b->>'label'
                     WHEN b ? 'caption' THEN b->>'caption'
                     ELSE '' END, ' ' ORDER BY o), ''), '**', '')
              FROM jsonb_array_elements(coalesce(blocks, '[]'::jsonb)) WITH ORDINALITY AS e(b, o)
        $$
    """)
    cases = " ".join(f"WHEN '{code}' THEN 'pg_catalog.{name}'::regconfig" for code, name in SEARCH_CONFIGS.items())
    op.execute(f"""
        CREATE FUNCTION {P}.help_search_config(language text) RETURNS regconfig LANGUAGE sql IMMUTABLE PARALLEL SAFE
        AS $$ SELECT CASE language {cases} ELSE 'pg_catalog.simple'::regconfig END $$
    """)

    # ── Content ────────────────────────────────────────────────────────────────
    op.create_table('help_categories',
    sa.Column('key', sa.String(length=40), nullable=False),
    sa.Column('sort', sa.Integer(), nullable=False),
    *_published(),
    sa.PrimaryKeyConstraint('key', name='pk_help_categories'),
    schema=P)

    op.create_table('help_articles',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('route', sa.String(length=200), nullable=True),
    sa.Column('related', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('start_order', sa.Integer(), nullable=True),
    sa.Column('popular', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('minutes', sa.Integer(), server_default='2', nullable=False),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    *_published(),
    sa.ForeignKeyConstraint(['category'], [f'{P}.help_categories.key'], ondelete='RESTRICT',
                            name='fk_help_articles_category_help_categories'),
    sa.CheckConstraint('minutes > 0', name='minutes'),
    sa.PrimaryKeyConstraint('id', name='pk_help_articles'),
    schema=P)

    op.create_table('help_article_translations',
    sa.Column('article_id', sa.String(length=80), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('keywords', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('blocks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('body', sa.Text(), sa.Computed(f"{P}.help_blocks_text(blocks)", persisted=True), nullable=True),
    sa.Column('search', postgresql.TSVECTOR(), _search(("title", "A"), (f"{P}.help_join(keywords)", "B"),
                                                        ("summary", "C"), (f"{P}.help_blocks_text(blocks)", "D")),
              nullable=True),
    *_published(),
    _fk('article_id', 'help_articles', 'fk_help_article_translations_article_id_help_articles'),
    sa.PrimaryKeyConstraint('article_id', 'language', name='pk_help_article_translations'),
    schema=P)
    op.create_index('ix_help_article_translations_search', 'help_article_translations', ['search'], schema=P,
                    postgresql_using='gin')

    op.create_table('help_faqs',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('article_id', sa.String(length=80), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    *_published(),
    sa.ForeignKeyConstraint(['category'], [f'{P}.help_categories.key'], ondelete='RESTRICT',
                            name='fk_help_faqs_category_help_categories'),
    _fk('article_id', 'help_articles', 'fk_help_faqs_article_id_help_articles'),
    sa.PrimaryKeyConstraint('id', name='pk_help_faqs'),
    schema=P)

    op.create_table('help_faq_translations',
    sa.Column('faq_id', sa.String(length=80), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('search', postgresql.TSVECTOR(), _search(("question", "A"), ("answer", "D")), nullable=True),
    *_published(),
    _fk('faq_id', 'help_faqs', 'fk_help_faq_translations_faq_id_help_faqs'),
    sa.PrimaryKeyConstraint('faq_id', 'language', name='pk_help_faq_translations'),
    schema=P)

    op.create_table('help_glossary',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('article_id', sa.String(length=80), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    *_published(),
    _fk('article_id', 'help_articles', 'fk_help_glossary_article_id_help_articles'),
    sa.PrimaryKeyConstraint('id', name='pk_help_glossary'),
    schema=P)

    op.create_table('help_glossary_translations',
    sa.Column('term_id', sa.String(length=80), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('term', sa.Text(), nullable=False),
    sa.Column('definition', sa.Text(), nullable=False),
    sa.Column('search', postgresql.TSVECTOR(), _search(("term", "A"), ("definition", "D")), nullable=True),
    *_published(),
    _fk('term_id', 'help_glossary', 'fk_help_glossary_translations_term_id_help_glossary'),
    sa.PrimaryKeyConstraint('term_id', 'language', name='pk_help_glossary_translations'),
    schema=P)

    op.create_table('help_tours',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('route', sa.String(length=200), nullable=False),
    sa.Column('targets', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    *_published(),
    sa.PrimaryKeyConstraint('id', name='pk_help_tours'),
    schema=P)

    op.create_table('help_tour_translations',
    sa.Column('tour_id', sa.String(length=80), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    *_published(),
    _fk('tour_id', 'help_tours', 'fk_help_tour_translations_tour_id_help_tours'),
    sa.PrimaryKeyConstraint('tour_id', 'language', name='pk_help_tour_translations'),
    schema=P)

    op.create_table('help_search_misses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('query_norm', sa.String(length=120), nullable=False),
    sa.Column('count', sa.Integer(), server_default='1', nullable=False),
    sa.Column('first_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name='pk_help_search_misses'),
    sa.UniqueConstraint('language', 'query_norm', name='uq_help_search_misses_language_query_norm'),
    schema=P)

    tables = ", ".join(f"{P}.{t}" for t in CONTENT)
    op.execute(f"GRANT SELECT ON {tables} TO formalie_app, formalie_readonly, platform_reader")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {tables} TO platform_writer")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {P}.help_search_misses TO formalie_app")
    op.execute(f"GRANT SELECT ON {P}.help_search_misses TO formalie_readonly, platform_reader")

    # ── Was this helpful? (one answer per person and article; read by the platform for the Formalie team) ──
    op.create_table('help_feedback',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('organisation_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('article_id', sa.String(length=80), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('helpful', sa.Boolean(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id', 'user_id'], [f'{S}.users.tenant_id', f'{S}.users.id'], ondelete='RESTRICT',
                            name='fk_help_feedback_tenant_id_users'),
    sa.ForeignKeyConstraint(['article_id'], [f'{P}.help_articles.id'], ondelete='RESTRICT',
                            name='fk_help_feedback_article_id_help_articles'),
    sa.PrimaryKeyConstraint('id', name='pk_help_feedback'),
    sa.UniqueConstraint('tenant_id', 'id', name='uq_help_feedback_tenant_id_id'),
    schema=S)
    op.create_index('uq_help_feedback_person', 'help_feedback', ['tenant_id', 'user_id', 'article_id'], unique=True,
                    schema=S, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_help_feedback_article', 'help_feedback', ['article_id'], schema=S)
    for statement in enable_tenant_rls('help_feedback'):
        op.execute(statement)

    # ── The mock's help centre ──
    from app.modules.help.seed import seed_help

    seed_help(op.get_bind())


def downgrade() -> None:
    for statement in disable_tenant_rls('help_feedback'):
        op.execute(statement)
    op.drop_index('ix_help_feedback_article', table_name='help_feedback', schema=S)
    op.drop_index('uq_help_feedback_person', table_name='help_feedback', schema=S)
    op.drop_table('help_feedback', schema=S)
    op.drop_table('help_search_misses', schema=P)
    op.drop_index('ix_help_article_translations_search', table_name='help_article_translations', schema=P)
    for table in reversed(CONTENT):
        op.drop_table(table, schema=P)
    for function in ("help_search_config(text)", "help_blocks_text(jsonb)", "help_join(text[])", "help_fold(text)"):
        op.execute(f"DROP FUNCTION IF EXISTS {P}.{function}")

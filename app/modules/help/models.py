"""Help centre tables (B14, DATABASE-DESIGN → Help and tours; migration 0033).

The content is global (schema `platform`, no tenant columns, no RLS): the Formalie team publishes it from the
platform admin (`platform_writer`), Formalie reads it (cached in Redis, dropped on `platform.published`). Content
is read with plain SQL (app/modules/help/content.py); these classes describe the tables for the metadata.
What people send back about an article is a tenant table with RLS (`help_feedback`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY, Boolean, Computed, DateTime, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import AuditMixin, Base, SoftDeleteMixin, TenantMixin, UuidPkMixin, tenant_fk, tenant_table_args

P = "platform"


def _search(*fields: tuple[str, str]) -> Computed:
    return Computed(" || ".join(
        f"setweight(to_tsvector({P}.help_search_config(language), {P}.help_fold({expr})), '{weight}')"
        for expr, weight in fields), persisted=True)


class _Published:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class HelpCategory(_Published, Base):
    __tablename__ = "help_categories"
    __table_args__ = ({"schema": P},)

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False)


class HelpArticle(_Published, Base):
    __tablename__ = "help_articles"
    __table_args__ = (ForeignKeyConstraint(["category"], [f"{P}.help_categories.key"], ondelete="RESTRICT"),
                      {"schema": P})

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    route: Mapped[str | None] = mapped_column(String(200))
    related: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    start_order: Mapped[int | None] = mapped_column(Integer)
    popular: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    sort: Mapped[int] = mapped_column(Integer, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HelpArticleTranslation(_Published, Base):
    __tablename__ = "help_article_translations"
    __table_args__ = (ForeignKeyConstraint(["article_id"], [f"{P}.help_articles.id"], ondelete="RESTRICT"),
                      Index("ix_help_article_translations_search", "search", postgresql_using="gin"),
                      {"schema": P})

    article_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, Computed(f"{P}.help_blocks_text(blocks)", persisted=True))
    search: Mapped[Any] = mapped_column(TSVECTOR, _search(("title", "A"), (f"{P}.help_join(keywords)", "B"),
                                                          ("summary", "C"), (f"{P}.help_blocks_text(blocks)", "D")))


class HelpFaq(_Published, Base):
    __tablename__ = "help_faqs"
    __table_args__ = (ForeignKeyConstraint(["category"], [f"{P}.help_categories.key"], ondelete="RESTRICT"),
                      ForeignKeyConstraint(["article_id"], [f"{P}.help_articles.id"], ondelete="RESTRICT"),
                      {"schema": P})

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    article_id: Mapped[str | None] = mapped_column(String(80))
    sort: Mapped[int] = mapped_column(Integer, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HelpFaqTranslation(_Published, Base):
    __tablename__ = "help_faq_translations"
    __table_args__ = (ForeignKeyConstraint(["faq_id"], [f"{P}.help_faqs.id"], ondelete="RESTRICT"), {"schema": P})

    faq_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    search: Mapped[Any] = mapped_column(TSVECTOR, _search(("question", "A"), ("answer", "D")))


class HelpTerm(_Published, Base):
    __tablename__ = "help_glossary"
    __table_args__ = (ForeignKeyConstraint(["article_id"], [f"{P}.help_articles.id"], ondelete="RESTRICT"),
                      {"schema": P})

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    article_id: Mapped[str | None] = mapped_column(String(80))
    sort: Mapped[int] = mapped_column(Integer, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HelpTermTranslation(_Published, Base):
    __tablename__ = "help_glossary_translations"
    __table_args__ = (ForeignKeyConstraint(["term_id"], [f"{P}.help_glossary.id"], ondelete="RESTRICT"),
                      {"schema": P})

    term_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), primary_key=True)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    search: Mapped[Any] = mapped_column(TSVECTOR, _search(("term", "A"), ("definition", "D")))


class HelpTour(_Published, Base):
    __tablename__ = "help_tours"
    __table_args__ = ({"schema": P},)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    route: Mapped[str] = mapped_column(String(200), nullable=False)
    targets: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HelpTourTranslation(_Published, Base):
    __tablename__ = "help_tour_translations"
    __table_args__ = (ForeignKeyConstraint(["tour_id"], [f"{P}.help_tours.id"], ondelete="RESTRICT"), {"schema": P})

    tour_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)


class HelpSearchMiss(Base):
    """A search that found nothing, per language and question (lower case, at most 120 characters)."""

    __tablename__ = "help_search_misses"
    __table_args__ = (UniqueConstraint("language", "query_norm"), {"schema": P})

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    query_norm: Mapped[str] = mapped_column(String(120), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class HelpFeedback(UuidPkMixin, TenantMixin, AuditMixin, SoftDeleteMixin, Base):
    """"Was this helpful?": one answer per person and article (a new answer replaces the old one)."""

    __tablename__ = "help_feedback"
    __table_args__ = tenant_table_args(
        tenant_fk("user_id", "users"),
        ForeignKeyConstraint(["article_id"], [f"{P}.help_articles.id"], ondelete="RESTRICT"),
        Index("uq_help_feedback_person", "tenant_id", "user_id", "article_id", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("ix_help_feedback_article", "article_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    article_id: Mapped[str] = mapped_column(String(80), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

"""What the platform admin's two database roles may touch (PLATFORM-ADMIN-INTEGRATION §1, DATABASE-DESIGN → DB roles).

- `platform_reader` (read replica, BYPASSRLS, read only): every table of Formalie, column by column, except secrets
  and answer content. A column is hidden when its name ends in `_hash` or `_enc` (password, token, code, secret
  hashes; every encrypted secret), or when it is listed in HIDDEN (answers, bodies that can carry answers, values
  typed by respondents, form content beyond metadata, verification tokens).
- `platform_writer`: SELECT, INSERT, UPDATE on the platform-owned global tables only (no DELETE: rows are retired
  with `retired_at`). B14's help content tables are in the list too.

Migration 0034 applies `reader_sql()` to every table that exists; `enable_tenant_rls()` applies it to every tenant
table created later, so a new secret column stays hidden by default (a column added later to an existing table is
not readable until a migration grants it). tests/db/test_platform_grants.py is the CI guard for both rules.
"""

from __future__ import annotations

SECRET_SUFFIXES = ("_hash", "_enc")

# table → columns platform_reader never reads (besides the *_hash / *_enc ones)
HIDDEN: dict[str, frozenset[str]] = {
    # answers and what respondents typed
    "responses": frozenset({"data", "identity_email", "respondent_email", "respondent_name"}),
    "resume_drafts": frozenset({"data", "email"}),
    "response_changes": frozenset({"before", "after"}),
    "response_notes": frozenset({"text"}),
    # bodies that can carry answers or records
    "request_logs": frozenset({"request_body", "request_body_text", "response_body"}),
    "api_request_logs": frozenset({"request_body", "response_body"}),
    "api_idempotency": frozenset({"answer"}),
    "webhook_deliveries": frozenset({"logged_body", "response"}),
    "sent_emails": frozenset({"html", "text"}),
    "ai_requests": frozenset({"prompt", "result", "output"}),
    "query_history": frozenset({"sql"}),
    # the audit trail: edited answers' before / after (changes) and the Query editor's SQL (metadata.statement);
    # the rest of each entry (who, what, when, the resource, the outcome) stays readable (B17 review M11)
    "audit_logs": frozenset({"changes", "metadata"}),
    "saved_queries": frozenset({"sql"}),
    # form versions: metadata only (§1)
    "forms": frozenset({"draft_schema"}),
    "form_versions": frozenset({"schema"}),
    # a DNS verification value is a credential for the domain check
    "custom_domains": frozenset({"token"}),
}

# Global tables the platform admin publishes (schema `platform`, no tenant columns)
B16_GLOBAL_TABLES: tuple[str, ...] = (
    "platform_settings", "reserved_subdomains", "feature_flags", "announcements", "announcement_translations",
    "plans", "plan_prices", "plan_limits", "plan_features",
    "system_option_lists", "system_option_items", "system_folders", "system_email_templates",
    "system_templates", "system_template_translations", "system_themes", "system_page_designs",
)
HELP_GLOBAL_TABLES: tuple[str, ...] = (  # B14 (migration 0033)
    "help_categories", "help_articles", "help_article_translations", "help_faqs", "help_faq_translations",
    "help_glossary", "help_glossary_translations", "help_tours", "help_tour_translations",
)
WRITER_TABLES: tuple[str, ...] = B16_GLOBAL_TABLES + HELP_GLOBAL_TABLES


def is_hidden(table: str, column: str) -> bool:
    return column.endswith(SECRET_SUFFIXES) or column in HIDDEN.get(table, frozenset())


def reader_sql(qualified: str) -> str:
    """A DO block: platform_reader may SELECT exactly the visible columns of `schema.table` (nothing when every
    column is hidden). Idempotent; reads the columns as they are when it runs."""
    schema, table = qualified.split(".", 1)
    hidden = sorted(HIDDEN.get(table, frozenset()))
    hidden_list = ", ".join(f"'{c}'" for c in hidden) or "''"
    return f"""
        DO $$ DECLARE cols text; BEGIN
            SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) INTO cols
              FROM information_schema.columns
             WHERE table_schema = '{schema}' AND table_name = '{table}'
               AND column_name NOT LIKE '%\\_hash' AND column_name NOT LIKE '%\\_enc'
               AND column_name NOT IN ({hidden_list});
            EXECUTE 'REVOKE SELECT ON {schema}.{table} FROM platform_reader';
            IF cols IS NOT NULL THEN
                EXECUTE format('GRANT SELECT (%s) ON {schema}.{table} TO platform_reader', cols);
            END IF;
        END $$"""

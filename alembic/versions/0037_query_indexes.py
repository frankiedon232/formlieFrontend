"""Query review indexes and upkeep (B17, docs/reviews/2026-10-query-review.md, 2026-10-12).

Indexes on formaly.responses (partitioned: created on the parent, so every monthly partition gets its own):
ix_responses_form_live         (tenant_id, form_id, submitted_at DESC, id DESC) live rows: lists, keyset paging (I1)
ix_responses_respondent        (tenant_id, form_id, respondent_kind, respondent_ref_id) live rows with a known
                               respondent: the one-answer-per-person check on submit (I2)
ix_responses_new               (tenant_id, form_id) live rows still `new`: "to review" counts (I3)
ix_responses_identity_live     (tenant_id, form_id, identity_email) INCLUDE (submitted_at, id), live rows with an
                               email: the same / near email check on submit reads only this index (I4, Q2)
ix_responses_device_live       (tenant_id, form_id, device_hash) live rows with a device (I4)
ix_responses_fingerprint_live  (tenant_id, form_id, fingerprint) live rows (I4)
ix_responses_tags              GIN (tags jsonb_path_ops) live rows: tag filter and counts (I5)
The three old ix_responses_identity / _device / _fingerprint go: every query through them asks for live rows only.

Indexes on formaly.forms (I8; tags is jsonb):
ix_forms_live                  (tenant_id, status, updated_at DESC) forms not in Trash
ix_forms_trash                 (tenant_id, deleted_at) forms in Trash, not purged: the Trash sweep
ix_forms_tags                  GIN (tags jsonb_path_ops) forms not purged
ix_forms_closing               (tenant_id, closes_at) published forms that still exist: closing announcements

ix_processed_events_processed_at (processed_at): the daily prune of the consumers' dedup table (Q12).

Upkeep moved from GET requests to Celery Beat (Q11). SECURITY DEFINER functions list the workspaces with work only:
platform.trash_due_workspaces()        formalie_directory: workspaces with forms in Trash longer than 30 days
platform.notification_due_workspaces() formalie_directory: workspaces with a published form closing within a day
                                       or daily summary lines waiting (name and subdomain for the emails)
platform.prune_processed_events(int, int)  formalie_owner: removes up to p_limit processed_events rows processed
                                       more than p_days ago (at least 7, the outbox replay window); a technical
                                       dedup table without tenant data

Revision ID: 0037
Revises: 0036
Created: 2026-10-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '0037'
down_revision: str | None = '0036'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "formaly"
R = f"{S}.responses"
F = f"{S}.forms"
TRASH = "platform.trash_due_workspaces()"
DUE = "platform.notification_due_workspaces()"
PRUNE = "platform.prune_processed_events(integer, integer)"
FORM_COLUMNS = "(tenant_id, organisation_id, status, closes_at, deleted_at, purged_at)"
DIGEST_COLUMNS = "(tenant_id, organisation_id, deleted_at)"
NEW_INDEXES = (
    ("ix_responses_form_live", R, "(tenant_id, form_id, submitted_at DESC, id DESC) WHERE deleted_at IS NULL"),
    ("ix_responses_respondent", R, "(tenant_id, form_id, respondent_kind, respondent_ref_id) "
                                   "WHERE deleted_at IS NULL AND respondent_ref_id IS NOT NULL"),
    ("ix_responses_new", R, "(tenant_id, form_id) WHERE deleted_at IS NULL AND status = 'new'"),
    ("ix_responses_identity_live", R, "(tenant_id, form_id, identity_email) INCLUDE (submitted_at, id) "
                                      "WHERE deleted_at IS NULL AND identity_email IS NOT NULL"),
    ("ix_responses_device_live", R, "(tenant_id, form_id, device_hash) "
                                    "WHERE deleted_at IS NULL AND device_hash IS NOT NULL"),
    ("ix_responses_fingerprint_live", R, "(tenant_id, form_id, fingerprint) WHERE deleted_at IS NULL"),
    ("ix_responses_tags", R, "USING gin (tags jsonb_path_ops) WHERE deleted_at IS NULL"),
    ("ix_forms_live", F, "(tenant_id, status, updated_at DESC) WHERE deleted_at IS NULL AND purged_at IS NULL"),
    ("ix_forms_trash", F, "(tenant_id, deleted_at) WHERE deleted_at IS NOT NULL AND purged_at IS NULL"),
    ("ix_forms_tags", F, "USING gin (tags jsonb_path_ops) WHERE purged_at IS NULL"),
    ("ix_forms_closing", F, "(tenant_id, closes_at) WHERE status = 'published' AND deleted_at IS NULL"),
    ("ix_processed_events_processed_at", f"{S}.processed_events", "(processed_at)"),
)
OLD_INDEXES = (
    ("ix_responses_identity", "(tenant_id, form_id, identity_email)"),
    ("ix_responses_device", "(tenant_id, form_id, device_hash)"),
    ("ix_responses_fingerprint", "(tenant_id, form_id, fingerprint)"),
)


def _directory_function(name: str, body: str) -> None:
    op.execute(body)
    op.execute("GRANT CREATE ON SCHEMA platform TO formalie_directory")
    op.execute(f"ALTER FUNCTION {name} OWNER TO formalie_directory")
    op.execute("REVOKE CREATE ON SCHEMA platform FROM formalie_directory")
    op.execute(f"REVOKE ALL ON FUNCTION {name} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {name} TO formalie_app")


def upgrade() -> None:
    for name, table, definition in NEW_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} {definition}")
    for name, _ in OLD_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {S}.{name}")

    op.execute(f"GRANT SELECT {FORM_COLUMNS} ON {F} TO formalie_directory")
    op.execute(f"GRANT SELECT {DIGEST_COLUMNS} ON {S}.notification_digest_lines TO formalie_directory")
    _directory_function(TRASH, f"""
        CREATE FUNCTION {TRASH}
        RETURNS TABLE (tenant_id uuid, organisation_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT DISTINCT f.tenant_id, f.organisation_id FROM {F} f
              JOIN platform.tenants t ON t.id = f.tenant_id AND t.deleted_at IS NULL
             WHERE f.deleted_at IS NOT NULL AND f.purged_at IS NULL AND f.deleted_at < now() - interval '30 days'
        $$
    """)
    _directory_function(DUE, f"""
        CREATE FUNCTION {DUE}
        RETURNS TABLE (tenant_id uuid, organisation_id uuid, subdomain text, name text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, platform
        AS $$
            SELECT w.tenant_id, w.organisation_id, t.subdomain::text, t.name::text FROM (
                SELECT f.tenant_id, f.organisation_id FROM {F} f
                 WHERE f.status = 'published' AND f.deleted_at IS NULL
                   AND f.closes_at > now() AND f.closes_at <= now() + interval '1 day'
                UNION
                SELECT d.tenant_id, d.organisation_id FROM {S}.notification_digest_lines d WHERE d.deleted_at IS NULL
            ) w JOIN platform.tenants t ON t.id = w.tenant_id
             WHERE t.deleted_at IS NULL AND t.status <> 'closed'
        $$
    """)
    op.execute(f"""
        CREATE FUNCTION {PRUNE.replace('integer, integer', 'p_days integer, p_limit integer')}
        RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $$
        DECLARE
            v_removed integer;
        BEGIN
            DELETE FROM {S}.processed_events p
             WHERE (p.consumer, p.event_id) IN (
                SELECT q.consumer, q.event_id FROM {S}.processed_events q
                 WHERE q.processed_at < now() - make_interval(days => greatest(p_days, 7))
                 LIMIT least(greatest(p_limit, 1), 50000));
            GET DIAGNOSTICS v_removed = ROW_COUNT;
            RETURN v_removed;
        END
        $$
    """)
    op.execute(f"REVOKE ALL ON FUNCTION {PRUNE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {PRUNE} TO formalie_worker")


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {PRUNE}")
    op.execute(f"DROP FUNCTION IF EXISTS {DUE}")
    op.execute(f"DROP FUNCTION IF EXISTS {TRASH}")
    op.execute(f"REVOKE SELECT {DIGEST_COLUMNS} ON {S}.notification_digest_lines FROM formalie_directory")
    op.execute(f"REVOKE SELECT {FORM_COLUMNS} ON {F} FROM formalie_directory")
    for name, definition in OLD_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {R} {definition}")
    for name, _, _ in reversed(NEW_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {S}.{name}")

"""Data sources → Activity (shared/utils/datasources/activity.ts): what happened on the organisation's connections,
from the audit trail (area `data`), grouped into kinds people think in."""

from __future__ import annotations

ACTIVITY_KINDS = ("queries", "rows", "structure", "exports", "storage", "connections")
ACTIVITY_ACTIONS: dict[str, tuple[str, ...]] = {
    "queries": ("data.query_run", "data.saved_query_saved", "data.saved_query_deleted"),
    "rows": ("data.row_inserted", "data.row_updated", "data.row_deleted"),
    "structure": ("data.user_table_created", "data.table_altered", "data.table_truncated", "data.table_dropped"),
    "exports": ("data.table_exported", "data.query_exported"),
    "storage": ("data.destination_created", "data.destination_updated", "data.destination_paused", "data.destination_resumed",
                "data.destination_removed", "data.table_created", "data.column_added", "data.backfill_started",
                "data.deliveries_retried"),
    "connections": ("data.connection_created", "data.connection_updated", "data.connection_tested", "data.connection_duplicated",
                    "data.connection_enabled", "data.connection_disabled", "data.connection_deleted", "data.credentials_changed"),
}


def kind_of_action(action: str) -> str | None:
    return next((kind for kind in ACTIVITY_KINDS if action in ACTIVITY_ACTIONS[kind]), None)

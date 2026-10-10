"""UUIDv7 for every id (CLAUDE.md rule 7). Generated in the app so PostgreSQL 16 and 18 behave the same."""

from __future__ import annotations

import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)

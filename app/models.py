"""Imports every module's models so Base.metadata is complete (Alembic, tests)."""

from __future__ import annotations


def import_all_models() -> None:
    import app.core.events.outbox  # noqa: F401
    import app.modules.logs.models  # noqa: F401
    import app.modules.tenants.models  # noqa: F401

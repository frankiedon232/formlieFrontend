"""Imports every module's models so Base.metadata is complete (Alembic, tests)."""

from __future__ import annotations


def import_all_models() -> None:
    import app.core.events.outbox  # noqa: F401
    import app.modules.audit.models  # noqa: F401
    import app.modules.auth.models  # noqa: F401
    import app.modules.exports.models  # noqa: F401
    import app.modules.forms.models  # noqa: F401
    import app.modules.logs.models  # noqa: F401
    import app.modules.org.models  # noqa: F401
    import app.modules.people.models  # noqa: F401
    import app.modules.settings.models  # noqa: F401
    import app.modules.tenants.models  # noqa: F401
    import app.modules.uploads.models  # noqa: F401
    import app.modules.users.models  # noqa: F401

"""Imports every module's models so Base.metadata is complete (Alembic, tests)."""

from __future__ import annotations


def import_all_models() -> None:
    import app.core.events.outbox  # noqa: F401
    import app.modules.address.models  # noqa: F401
    import app.modules.ai.models  # noqa: F401
    import app.modules.api_service.models  # noqa: F401
    import app.modules.audit.models  # noqa: F401
    import app.modules.auth.models  # noqa: F401
    import app.modules.data_sources.models  # noqa: F401
    import app.modules.destinations.models  # noqa: F401
    import app.modules.emails.models  # noqa: F401
    import app.modules.query.models  # noqa: F401
    import app.modules.design.models  # noqa: F401
    import app.modules.exports.models  # noqa: F401
    import app.modules.forms.models  # noqa: F401
    import app.modules.help.models  # noqa: F401
    import app.modules.links.models  # noqa: F401
    import app.modules.lists.models  # noqa: F401
    import app.modules.logs.models  # noqa: F401
    import app.modules.notifications.models  # noqa: F401
    import app.modules.org.models  # noqa: F401
    import app.modules.people.models  # noqa: F401
    import app.modules.public.models  # noqa: F401
    import app.modules.responses.models  # noqa: F401
    import app.modules.settings.models  # noqa: F401
    import app.modules.sso.models  # noqa: F401
    import app.modules.templates.models  # noqa: F401
    import app.modules.tenants.models  # noqa: F401
    import app.modules.uploads.models  # noqa: F401
    import app.modules.users.models  # noqa: F401
    import app.modules.webhooks.models  # noqa: F401

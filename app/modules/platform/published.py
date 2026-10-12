"""`platform.published`: the platform admin wrote global tables (PLATFORM-ADMIN-INTEGRATION §1).

    { "table": "help_articles", "ids": ["welcome"], "version": 7 }

Formalie drops what it cached from those tables. The bus consumer (and the `/cache/invalidate` fallback of the
internal admin API) come with the platform bridge (B16); they call `handle_published()`. Each global table that
Formalie caches is listed here with what drops its cache.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger("formalie.platform")

HELP_TABLES = ("help_categories", "help_articles", "help_article_translations", "help_faqs", "help_faq_translations",
               "help_glossary", "help_glossary_translations", "help_tours", "help_tour_translations")


def _handlers() -> dict[str, Callable[[], Awaitable[None]]]:
    from app.modules.help.content import invalidate as help_invalidate

    return {table: help_invalidate for table in HELP_TABLES}


async def handle_published(event: dict[str, Any]) -> list[str]:
    """Drops the caches of the tables named in a `platform.published` event (`table`, or `tables` for several);
    returns the tables it acted on. Unknown tables are ignored (nothing of them is cached)."""
    names = event.get("tables") or [event.get("table")]
    handlers = _handlers()
    done: list[str] = []
    called: set[Callable[[], Awaitable[None]]] = set()
    for name in names:
        handler = handlers.get(name) if isinstance(name, str) else None
        if handler is None:
            continue
        if handler not in called:
            await handler()
            called.add(handler)
        done.append(name)
    log.info("platform content published", extra={"tables": done, "version": event.get("version")})
    return done

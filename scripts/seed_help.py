"""Loads the shipped help centre into the global help tables again (after scripts/sync_frontend_data.py brought
new help files), then drops the cached help answers (Redis, development database only). Migration 0033 already did it once on every database.
Content the Formalie team published from the platform admin is never overwritten (app/modules/help/seed.py).

    fmly\\Scripts\\python.exe scripts\\seed_help.py            # the development database
    fmly\\Scripts\\python.exe scripts\\seed_help.py --test     # the test database

Runs as formalie_owner (DB_OWNER_URL), like the migrations.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db.engines import async_url  # noqa: E402
from app.modules.help.content import invalidate  # noqa: E402
from app.modules.help.seed import seed_help  # noqa: E402


async def main(test: bool) -> None:
    settings = get_settings()
    if settings.db_owner_url is None:
        raise SystemExit("DB_OWNER_URL is not set")
    url = make_url(async_url(settings.db_owner_url.get_secret_value()))
    if test:
        url = url.set(database=settings.db_test_database)
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            counts = await conn.run_sync(seed_help)
    finally:
        await engine.dispose()
    if not test:  # the tests' caches are their own (fakeredis)
        await invalidate()
    print(f"Help centre loaded into {url.database}: {counts}")


if __name__ == "__main__":
    asyncio.run(main("--test" in sys.argv[1:]))

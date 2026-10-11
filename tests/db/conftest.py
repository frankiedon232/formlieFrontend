"""PostgreSQL test database fixtures. Migrates `DB_TEST_DATABASE` to head once per run, then tests connect as
formalie_owner (setup), formalie_app (what the API can do) and formalie_worker (relay)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.db.engines import Engines, set_engines
from app.core.ids import uuid7

pytestmark = pytest.mark.db


def _test_url(secret: object | None, driver: str = "postgresql") -> str | None:
    if secret is None:
        return None
    url = make_url(secret.get_secret_value())  # type: ignore[attr-defined]
    return url.set(drivername=driver, database=get_settings().db_test_database).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def db_settings() -> Settings:
    settings = get_settings()
    if not (settings.db_owner_url and settings.db_app_url and settings.db_relay_url):
        pytest.skip("DB_OWNER_URL, DB_APP_URL and DB_RELAY_URL are not set (see .env.example)")
    return settings.model_copy(update={
        "db_app_url": type(settings.db_app_url)(_test_url(settings.db_app_url)),
        "db_relay_url": type(settings.db_relay_url)(_test_url(settings.db_relay_url)),
        "db_replica_urls": [],
    })


@pytest.fixture(scope="session")
def migrated(db_settings: Settings) -> None:
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": ["db=test"]})()
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def owner_dsn(migrated: None) -> str:
    return _test_url(get_settings().db_owner_url)  # type: ignore[return-value]


@pytest.fixture(scope="session")
def app_dsn(db_settings: Settings, migrated: None) -> str:
    return db_settings.db_app_url.get_secret_value()  # type: ignore[union-attr]


@pytest.fixture(scope="session")
def worker_dsn(db_settings: Settings, migrated: None) -> str:
    return db_settings.db_relay_url.get_secret_value()  # type: ignore[union-attr]


@pytest.fixture
def owner(owner_dsn: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(owner_dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture
def superuser(migrated: None) -> Iterator[psycopg.Connection]:
    """For assertions across workspaces only (it bypasses RLS). Never used by the code under test."""
    settings = get_settings()
    if settings.db_superuser_url is None:
        pytest.skip("DB_SUPERUSER_URL is not set")
    with psycopg.connect(_test_url(settings.db_superuser_url), autocommit=True) as conn:  # type: ignore[arg-type]
        yield conn


@pytest.fixture
async def engines(db_settings: Settings, migrated: None, redis) -> AsyncIterator[Engines]:  # noqa: ANN001
    engines = Engines(db_settings)
    set_engines(engines)
    yield engines
    set_engines(None)
    await engines.dispose()


@dataclass
class Workspace:
    tenant_id: uuid.UUID
    organisation_id: uuid.UUID
    subdomain: str


def make_workspace(conn: psycopg.Connection, *, status: str = "active", old_subdomain: str | None = None) -> Workspace:
    """Inserts a tenant and its primary organisation as formalie_owner (RLS is forced on the owner too)."""
    ws = Workspace(uuid7(), uuid7(), f"t{uuid7().hex[-10:]}")
    with conn.transaction():
        conn.execute("INSERT INTO platform.tenants (id, subdomain, name, status, primary_organisation_id) "
                     "VALUES (%s, %s, %s, %s, %s)", (ws.tenant_id, ws.subdomain, f"Test {ws.subdomain}", status,
                                                    ws.organisation_id))
        conn.execute("SELECT set_config('app.tenant_id', %s, true), set_config('app.organisation_id', %s, true)",
                     (str(ws.tenant_id), str(ws.organisation_id)))
        conn.execute("INSERT INTO organisations (id, tenant_id, organisation_id, name, is_primary) "
                     "VALUES (%s, %s, %s, %s, true)", (ws.organisation_id, ws.tenant_id, ws.organisation_id,
                                                      f"Org {ws.subdomain}"))
        if old_subdomain:
            conn.execute("INSERT INTO platform.tenant_subdomain_history (id, tenant_id, subdomain, until) "
                         "VALUES (%s, %s, %s, %s)", (uuid7(), ws.tenant_id, old_subdomain,
                                                     datetime.now(UTC) + timedelta(days=90)))
    return ws


@pytest.fixture
def two_workspaces(owner: psycopg.Connection) -> tuple[Workspace, Workspace]:
    return make_workspace(owner), make_workspace(owner)

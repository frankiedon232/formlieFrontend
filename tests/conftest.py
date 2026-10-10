"""Shared fixtures. Unit and API tests need neither PostgreSQL nor Redis (fakeredis); tests/db needs the test DB."""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ["LOG_CONSOLE"] = "false"
os.environ["LOG_DIR"] = str(Path(tempfile.gettempdir()) / "formalie-test-logs")

import fakeredis  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from app.core.cache.redis import set_redis  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402
from app.core.context import TenantInfo  # noqa: E402

FRONTEND_DIR = Path(os.environ.get("FORMALIE_FRONTEND_DIR", r"C:\UNETPROJECTS\formalieFrontend"))

ACME = TenantInfo(id=uuid.UUID("01900000-0000-7000-8000-00000000000a"), subdomain="acme", name="Acme",
                  status="active", organisation_id=uuid.UUID("01900000-0000-7000-8000-0000000000a1"))
OLDCO = TenantInfo(id=uuid.UUID("01900000-0000-7000-8000-00000000000b"), subdomain="oldco", name="Old Co",
                   status="suspended", organisation_id=uuid.UUID("01900000-0000-7000-8000-0000000000b1"))


class FakeTenantResolver:
    def __init__(self, *tenants: TenantInfo) -> None:
        self.tenants = {t.subdomain: t for t in tenants}

    async def by_subdomain(self, subdomain: str) -> TenantInfo | None:
        return self.tenants.get(subdomain)

    async def by_domain(self, domain: str) -> TenantInfo | None:
        return None


@pytest.fixture
def frontend_dir() -> Path:
    if not (FRONTEND_DIR / "shared").is_dir():
        pytest.skip(f"frontend not found at {FRONTEND_DIR} (set FORMALIE_FRONTEND_DIR)")
    return FRONTEND_DIR


@pytest.fixture
def redis() -> fakeredis.FakeAsyncRedis:
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    set_redis(client)
    yield client
    set_redis(None)


@pytest.fixture
def settings() -> Settings:
    return get_settings().model_copy(update={"rate_limit_ip_per_minute": 1000})


def build_app(settings: Settings, **overrides: object) -> FastAPI:
    from app.run import create_app

    return create_app(settings.model_copy(update=overrides) if overrides else settings,
                      tenant_resolver=FakeTenantResolver(ACME, OLDCO))


@pytest.fixture
def app(settings: Settings, redis: fakeredis.FakeAsyncRedis) -> FastAPI:
    return build_app(settings)


def client_for(app: FastAPI, host: str = "manage.formalie.dev", peer: str = "203.0.113.7") -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(peer, 50000))
    return httpx.AsyncClient(transport=transport, base_url=f"https://{host}")


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with client_for(app) as c:
        yield c

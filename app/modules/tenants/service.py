"""Tenant directory: host → workspace, L1 (seconds) → Redis (minutes) → DB (`platform.resolve_tenant`).

Used by the tenant middleware before any tenant context exists. Only public fields leave the database.
Invalidate with `TenantDirectory.forget(subdomain)` when a workspace changes status or subdomain.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text

from app.core.cache.tiers import L1Cache, RedisCache
from app.core.config import get_settings
from app.core.context import TenantInfo
from app.core.db.session import db_session

log = logging.getLogger("formalie.tenants")

CACHE_MODULE = "tenant_directory"
_MISSING: dict[str, Any] = {"missing": True}


def _to_info(row: dict[str, Any]) -> TenantInfo:
    return TenantInfo(
        id=uuid.UUID(str(row["id"])),
        subdomain=row["subdomain"],
        name=row["name"],
        status=row["status"],
        organisation_id=uuid.UUID(str(row["organisation_id"])),
    )


async def _load_by_subdomain(subdomain: str) -> dict[str, Any]:
    async with db_session("read") as session:
        result = await session.execute(
            text("SELECT id, subdomain, name, status, organisation_id FROM platform.resolve_tenant(:subdomain)"),
            {"subdomain": subdomain},
        )
        row = result.mappings().first()
    if row is None:
        return _MISSING
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in row.items()}


class TenantDirectory:
    def __init__(self, cache: RedisCache | None = None) -> None:
        settings = get_settings()
        self.l1: L1Cache[str, dict[str, Any]] = L1Cache(settings.tenant_cache_seconds)
        self.l2 = cache or RedisCache()

    async def by_subdomain(self, subdomain: str) -> TenantInfo | None:
        key = subdomain.lower()
        row = self.l1.get(key)
        if row is None:
            row = await self.l2.get_or_set(None, CACHE_MODULE, key, lambda: _load_by_subdomain(key), ttl_seconds=300)
            self.l1.set(key, row)
        return None if row.get("missing") else _to_info(row)

    async def by_domain(self, domain: str) -> TenantInfo | None:
        """Own domains (Settings → Address) are verified in B11; until then no custom host maps to a workspace."""
        return None

    async def forget(self, subdomain: str) -> None:
        self.l1.delete(subdomain.lower())
        await self.l2.delete(None, CACHE_MODULE, subdomain.lower())

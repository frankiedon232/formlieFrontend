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

CACHE_MODULE = "tenant_directory_v2"  # v2: rows carry plan_id
_MISSING: dict[str, Any] = {"missing": True}


def _to_info(row: dict[str, Any]) -> TenantInfo:
    return TenantInfo(
        id=uuid.UUID(str(row["id"])),
        subdomain=row["subdomain"],
        name=row["name"],
        status=row["status"],
        organisation_id=uuid.UUID(str(row["organisation_id"])),
        plan_id=row.get("plan_id") or "starter",
    )


async def _load_by_subdomain(subdomain: str) -> dict[str, Any]:
    async with db_session("read") as session:
        result = await session.execute(
            text("SELECT id, subdomain, name, status, organisation_id, plan_id FROM platform.resolve_tenant(:subdomain)"),
            {"subdomain": subdomain},
        )
        row = result.mappings().first()
    if row is None:
        return _MISSING
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in row.items()}


async def _load_by_domain(domain: str) -> dict[str, Any]:
    async with db_session("read") as session:
        result = await session.execute(
            text("SELECT id, subdomain, name, status, organisation_id, plan_id FROM platform.resolve_domain(:domain)"),
            {"domain": domain},
        )
        row = result.mappings().first()
    if row is None:
        return _MISSING
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in row.items()}


_L1: L1Cache[str, dict[str, Any]] | None = None


def _shared_l1() -> L1Cache[str, dict[str, Any]]:
    """One L1 per process, so `forget()` from any instance (a settings change, the platform admin) reaches the one
    the tenant middleware reads."""
    global _L1
    if _L1 is None:
        _L1 = L1Cache(get_settings().tenant_cache_seconds)
    return _L1


class TenantDirectory:
    def __init__(self, cache: RedisCache | None = None) -> None:
        self.l1: L1Cache[str, dict[str, Any]] = _shared_l1()
        self.l2 = cache or RedisCache()

    async def by_subdomain(self, subdomain: str) -> TenantInfo | None:
        key = subdomain.lower()
        row = self.l1.get(key)
        if row is None:
            row = await self.l2.get_or_set(None, CACHE_MODULE, key, lambda: _load_by_subdomain(key), ttl_seconds=300)
            self.l1.set(key, row)
        return None if row.get("missing") else _to_info(row)

    async def by_domain(self, domain: str) -> TenantInfo | None:
        """A workspace's own verified domain (Settings → Address and domain), only while its plan includes one."""
        from app.modules.billing.service import has_feature

        key = f"domain:{domain.lower().rstrip('.')}"
        row = self.l1.get(key)
        if row is None:
            row = await self.l2.get_or_set(None, CACHE_MODULE, key, lambda: _load_by_domain(key[7:]), ttl_seconds=300)
            self.l1.set(key, row)
        if row.get("missing"):
            return None
        tenant = _to_info(row)
        return tenant if has_feature(tenant.plan_id, "custom_domain") else None

    async def forget_domain(self, domain: str) -> None:
        key = f"domain:{domain.lower().rstrip('.')}"
        self.l1.delete(key)
        await self.l2.delete(None, CACHE_MODULE, key)

    async def forget(self, subdomain: str) -> None:
        self.l1.delete(subdomain.lower())
        await self.l2.delete(None, CACHE_MODULE, subdomain.lower())

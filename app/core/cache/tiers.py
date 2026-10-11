"""Cache tiers (BACKEND-SPEC §4).

L1: in-process TTL cache (seconds) for the tenant directory and feature flags.
L2: Redis, cache-aside, keys `fm:v1:t:{tenant_id}:{module}:{id}:{version}` (CLAUDE.md rule 10).
    Each (tenant, module) has a version counter; bumping it drops every key of that module at once.
    A short lock stops a stampede when a hot key expires. Never cache secrets.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.cache.redis import get_redis

log = logging.getLogger("formalie.cache")

K = TypeVar("K")
V = TypeVar("V")

KEY_PREFIX = "fm:v1"
PLATFORM = "platform"  # tenant segment for global (platform) data


class L1Cache(Generic[K, V]):
    """Small in-process TTL + LRU cache. Per worker process; keep TTLs short."""

    def __init__(self, ttl_seconds: float, max_items: int = 10_000) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._items: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def get(self, key: K) -> V | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        self._items[key] = (time.monotonic() + self.ttl, value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def delete(self, key: K) -> None:
        self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()


def tenant_segment(tenant_id: uuid.UUID | str | None) -> str:
    return PLATFORM if tenant_id is None else f"t:{tenant_id}"


def version_key(tenant_id: uuid.UUID | str | None, module: str) -> str:
    return f"{KEY_PREFIX}:{tenant_segment(tenant_id)}:{module}:__ver"


def cache_key(tenant_id: uuid.UUID | str | None, module: str, item: str, version: int) -> str:
    return f"{KEY_PREFIX}:{tenant_segment(tenant_id)}:{module}:{item}:{version}"


class RedisCache:
    """L2 cache-aside. Values are JSON. A Redis failure falls back to the loader (logged), never to an error."""

    def __init__(self, redis: Redis | None = None, lock_ms: int = 3000) -> None:
        self._redis = redis
        self.lock_ms = lock_ms

    @property
    def redis(self) -> Redis:
        return self._redis or get_redis()

    async def _version(self, tenant_id: uuid.UUID | str | None, module: str) -> int:
        raw = await self.redis.get(version_key(tenant_id, module))
        return int(raw) if raw else 0

    async def get_or_set(
        self,
        tenant_id: uuid.UUID | str | None,
        module: str,
        item: str,
        loader: Callable[[], Awaitable[Any]],
        ttl_seconds: int = 300,
    ) -> Any:
        try:
            version = await self._version(tenant_id, module)
            key = cache_key(tenant_id, module, item, version)
            cached = await self.redis.get(key)
            if cached is not None:
                return json.loads(cached)
            lock_key = f"{key}:lock"
            if not await self.redis.set(lock_key, "1", nx=True, px=self.lock_ms):
                # Someone else is loading: wait briefly for their value, then load ourselves.
                for _ in range(10):
                    await asyncio.sleep(self.lock_ms / 10_000)
                    cached = await self.redis.get(key)
                    if cached is not None:
                        return json.loads(cached)
            try:
                value = await loader()
                await self.redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)
                return value
            finally:
                await self.redis.delete(lock_key)
        except RedisError as exc:
            log.warning("cache unavailable, loading directly", extra={"cache_module": module, "error": str(exc)})
            return await loader()

    async def invalidate(self, tenant_id: uuid.UUID | str | None, module: str) -> None:
        """Drops every cached item of a module for one tenant (call on change events)."""
        try:
            await self.redis.incr(version_key(tenant_id, module))
        except RedisError as exc:
            log.error("cache invalidation failed", extra={"cache_module": module, "error": str(exc)})

    async def delete(self, tenant_id: uuid.UUID | str | None, module: str, item: str) -> None:
        try:
            version = await self._version(tenant_id, module)
            await self.redis.delete(cache_key(tenant_id, module, item, version))
        except RedisError as exc:
            log.error("cache delete failed", extra={"cache_module": module, "error": str(exc)})

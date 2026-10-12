"""Reading the global tables the platform admin publishes (PLATFORM-ADMIN-INTEGRATION §1), cached in Redis.

Cache keys `fm:v1:platform:global:{table}:{item}:{version}`; `invalidate(tables)` bumps the versions. The
`platform.published` consumer (consumer.py) and the internal admin API's `/cache/invalidate` call `on_published()`,
which also hands help tables to B14's handler (app/modules/platform/published.py).

Platform settings: a row the Formalie team published (`published_by_staff_id` set, not retired) wins; otherwise
the server's own settings (.env) answer, which is also what migration 0034 copied into the shipped rows.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.cache.tiers import RedisCache
from app.core.config import get_settings
from app.core.context import TenantInfo
from app.core.db.session import db_session
from app.modules.platform_bridge.grants import B16_GLOBAL_TABLES, HELP_GLOBAL_TABLES

log = logging.getLogger("formalie.platform")

TTL_SECONDS = 600
P = "platform"
_cache = RedisCache()

# Which cache module each global table feeds (several tables share one answer)
CACHE_MODULES: dict[str, str] = {
    "platform_settings": "global:platform_settings",
    "reserved_subdomains": "global:reserved_subdomains",
    "feature_flags": "global:feature_flags",
    "announcements": "global:announcements",
    "announcement_translations": "global:announcements",
}
for _table in B16_GLOBAL_TABLES:
    CACHE_MODULES.setdefault(_table, f"global:{_table}")


async def _read(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    async with db_session("read") as db:
        rows = (await db.execute(text(sql), params or {})).mappings().all()
    return [dict(r) for r in rows]


def _plain(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


async def cached(table: str, item: str, loader: Any) -> Any:
    return await _cache.get_or_set(None, CACHE_MODULES[table], item, loader, ttl_seconds=TTL_SECONDS)


# ── Platform settings ────────────────────────────────────────────────────────────

async def _published_settings() -> dict[str, Any]:
    rows = await _read(f"SELECT key, value FROM {P}.platform_settings "
                       "WHERE retired_at IS NULL AND published_by_staff_id IS NOT NULL")
    return {r["key"]: r["value"] for r in rows}


def _from_server(key: str) -> Any:
    s = get_settings()
    return {
        "legal": {"terms_url": s.legal_terms_url, "privacy_url": s.legal_privacy_url},
        "support": {"email": getattr(s, "support_email", "support@formalie.com") or None,
                    "url": getattr(s, "support_url", None) or None},
        "egress_ips": list(s.egress_ips),
        "status_page": {"url": None},
    }.get(key)


async def platform_setting(key: str) -> Any:
    """The platform's value for a setting: published by the Formalie team, else the server's own."""
    published = await cached("platform_settings", "published", _published_settings)
    if key in published:
        server = _from_server(key)
        value = published[key]
        # A published object fills in what it leaves out from the server's value (a partial publish keeps working)
        return {**server, **value} if isinstance(server, dict) and isinstance(value, dict) else value
    return _from_server(key)


async def legal_links() -> dict[str, str]:
    legal = await platform_setting("legal") or {}
    return {"terms_url": str(legal.get("terms_url") or ""), "privacy_url": str(legal.get("privacy_url") or "")}


async def egress_ips() -> list[str]:
    value = await platform_setting("egress_ips")
    return [str(v) for v in value] if isinstance(value, list) else []


async def support_contact() -> dict[str, str | None]:
    """Where people reach Formalie's support team (the help centre, B14)."""
    value = await platform_setting("support") or {}
    return {"email": value.get("email") or None, "url": value.get("url") or None}


# ── Reserved subdomains ──────────────────────────────────────────────────────────

async def _reserved() -> list[str]:
    return [r["subdomain"] for r in await _read(f"SELECT subdomain FROM {P}.reserved_subdomains WHERE retired_at IS NULL")]


async def is_reserved(subdomain: str) -> bool:
    """Reserved by the host rules (tenant.py) or by the Formalie team (platform admin)."""
    from app.core.middleware.tenant import RESERVED_SUBDOMAINS

    value = subdomain.strip().lower()
    return value in RESERVED_SUBDOMAINS or value in set(await cached("reserved_subdomains", "all", _reserved))


# ── Feature switches ─────────────────────────────────────────────────────────────

async def _flags() -> list[dict[str, Any]]:
    rows = await _read(f"SELECT key, enabled, plans, tenant_ids, rollout_percent FROM {P}.feature_flags "
                       "WHERE retired_at IS NULL ORDER BY key")
    return [{k: _plain(v) for k, v in r.items()} for r in rows]


def flag_on(flag: dict[str, Any], tenant: TenantInfo) -> bool:
    """Listed workspaces always; otherwise the plan must be listed (none listed: every plan) and the workspace in
    the rollout percentage (a stable hash of the switch and the workspace)."""
    if not flag.get("enabled"):
        return False
    if str(tenant.id) in set(flag.get("tenant_ids") or []):
        return True
    plans = flag.get("plans") or []
    if plans and tenant.plan_id not in plans:
        return False
    percent = int(flag.get("rollout_percent") or 0)
    bucket = int(hashlib.sha256(f"{flag['key']}:{tenant.id}".encode()).hexdigest()[:8], 16) % 100
    return bucket < percent


async def flags_for(tenant: TenantInfo) -> dict[str, bool]:
    return {f["key"]: flag_on(f, tenant) for f in await cached("feature_flags", "all", _flags)}


async def feature_enabled(key: str, tenant: TenantInfo) -> bool:
    return (await flags_for(tenant)).get(key, False)


# ── Announcements ────────────────────────────────────────────────────────────────

async def _announcements() -> list[dict[str, Any]]:
    rows = await _read(f"""
        SELECT a.id, a.kind, a.tone, a.audience, a.plans, a.tenant_ids, a.starts_at, a.ends_at, a.link_url,
               a.dismissible, coalesce(jsonb_object_agg(t.language, jsonb_build_object('title', t.title, 'body', t.body))
                                       FILTER (WHERE t.language IS NOT NULL), '{{}}'::jsonb) AS texts
          FROM {P}.announcements a LEFT JOIN {P}.announcement_translations t ON t.announcement_id = a.id
         WHERE a.retired_at IS NULL AND (a.ends_at IS NULL OR a.ends_at > now() - interval '1 day')
         GROUP BY a.id ORDER BY a.starts_at DESC""")
    return [{k: _plain(v) for k, v in r.items()} for r in rows]


def _when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reaches(item: dict[str, Any], tenant: TenantInfo) -> bool:
    if item["audience"] == "tenants":
        return str(tenant.id) in set(item.get("tenant_ids") or [])
    if item["audience"] == "plans":
        return tenant.plan_id in set(item.get("plans") or [])
    return True


async def announcements_for(tenant: TenantInfo, language: str | None) -> list[dict[str, Any]]:
    """Banners showing now for this workspace, in the reader's language (English, else any, when missing)."""
    now = datetime.now(UTC)
    out = []
    for item in await cached("announcements", "all", _announcements):
        if _when(item["starts_at"]) > now or (item["ends_at"] and _when(item["ends_at"]) <= now):
            continue
        if not _reaches(item, tenant):
            continue
        texts = item.get("texts") or {}
        text_ = texts.get(language or "en") or texts.get("en") or next(iter(texts.values()), None)
        if not text_:
            continue
        out.append({"id": item["id"], "kind": item["kind"], "tone": item["tone"], "title": text_["title"],
                    "body": text_.get("body"), "link_url": item["link_url"], "dismissible": item["dismissible"],
                    "starts_at": item["starts_at"], "ends_at": item["ends_at"]})
    return out


# ── Invalidation ─────────────────────────────────────────────────────────────────

async def invalidate(tables: list[str]) -> list[str]:
    """Drops what Formalie cached from these global tables; returns the ones it knows."""
    modules: set[str] = set()
    known: list[str] = []
    for table in tables:
        module = CACHE_MODULES.get(table)
        if module:
            modules.add(module)
            known.append(table)
    for module in sorted(modules):
        await _cache.invalidate(None, module)
    return known


async def on_published(event: dict[str, Any]) -> list[str]:
    """A `platform.published` event ({table, ids, version} or {tables: [...]}, possibly inside `properties` or
    `payload`): drops the caches of every table it names. Returns the tables acted on."""
    body = event
    for wrapper in ("properties", "payload"):
        if isinstance(body.get(wrapper), dict) and ("table" in body[wrapper] or "tables" in body[wrapper]):
            body = body[wrapper]
    names = body.get("tables") or [body.get("table")]
    tables = [n for n in names if isinstance(n, str)]
    done = await invalidate([t for t in tables if t not in HELP_GLOBAL_TABLES])
    help_tables = [t for t in tables if t in HELP_GLOBAL_TABLES]
    if help_tables:
        try:
            from app.modules.platform.published import handle_published  # B14's help caches
        except ImportError:  # the help centre is not there yet
            handle_published = None
        if handle_published is not None:
            done += await handle_published({"tables": help_tables, "version": body.get("version")})
    log.info("global tables published", extra={"tables": done, "version": body.get("version")})
    return done


"""Sample traffic for the seeded development workspaces only (scripts/seed_dev.py), so the request log, the analytics
and every count of calls have something to show, like the mock's made-up history (data/apiTraffic.ts, apiStore.ts
usageOf). Real rows in `api_request_logs`: 60 days of calls on the live endpoints (fewer at weekends, a few errors),
calls refused by the sample block rules, and calls over a rate limit. Stable per endpoint and day. Values stay
international and neutral (documentation IP ranges). Run once: skipped when the workspace has any calls logged.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.ids import uuid7
from app.modules.api_service import tokens as T
from app.modules.api_service.models import (
    ApiAccessRule, ApiEndpoint, ApiRequestLog, ApiService, ApiSettings, ApiToken,
)
from app.modules.forms.models import Form

DAYS = 60
PER_DAY = 12  # at most, per endpoint
COUNTRIES = ["GB", "US", "NG", "DE", "IN", "BR", "KE", "FR", "JP", "ZA", "CA", "AU", "NL", "SG", "AE", "MX", "ID", "EG"]
AGENTS = ["PostmanRuntime/7.39.0", "python-requests/2.32.3", "axios/1.7.7", "okhttp/4.12.0", "curl/8.7.1", "Go-http-client/2.0"]
ERRORS = [(422, "FRM-RESP-1001"), (401, "FRM-API-1010"), (429, "FRM-GEN-1029"), (403, "FRM-API-1015"),
          (404, "FRM-API-1013"), (500, "FRM-GEN-5000")]


def seed_of(text_: str) -> int:
    return int.from_bytes(hashlib.sha256(text_.encode()).digest()[:4], "big")


def uuid_of(text_: str) -> str:
    """A stable UUID made from text (the mock's uuidOf)."""
    return str(uuid.UUID(bytes=hashlib.sha256(text_.encode()).digest()[:16], version=4))


async def ensure_past_partitions(session: AsyncSession, months: int = 3) -> None:
    """The last months' partitions (as formalie_owner, which the seed connects as); quietly skipped otherwise."""
    schema = get_settings().db_schema
    try:
        async with session.begin_nested():
            for table in ("api_request_logs", "webhook_deliveries"):
                await session.execute(text(f"SELECT platform.ensure_monthly_partitions_back('{schema}.{table}'::regclass, :n)"),
                                      {"n": months})
    except DBAPIError:
        pass


async def seed_sample_traffic(session: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> int:
    """Inside the workspace's RLS context. Returns how many calls were added (0 when it already has some)."""
    if (await session.execute(select(ApiRequestLog.id).where(ApiRequestLog.tenant_id == tenant_id).limit(1))).first():
        return 0
    settings = (await session.execute(select(ApiSettings).where(ApiSettings.tenant_id == tenant_id))).scalar_one_or_none()
    endpoints = list((await session.execute(select(ApiEndpoint).where(
        ApiEndpoint.tenant_id == tenant_id, ApiEndpoint.deleted_at.is_(None)).order_by(ApiEndpoint.created_at))).scalars())
    if settings is None or not endpoints:
        return 0
    await ensure_past_partitions(session)
    services = {s.id: s for s in (await session.execute(select(ApiService).where(
        ApiService.tenant_id == tenant_id, ApiService.deleted_at.is_(None)))).scalars()}
    forms = {f.id: f for f in (await session.execute(select(Form).where(
        Form.tenant_id == tenant_id, Form.id.in_({e.form_id for e in endpoints})))).scalars()}
    tokens = [t for t in (await session.execute(select(ApiToken).where(
        ApiToken.tenant_id == tenant_id, ApiToken.deleted_at.is_(None), ApiToken.kind != "webhook"))).scalars()]
    rules = list((await session.execute(select(ApiAccessRule).where(
        ApiAccessRule.tenant_id == tenant_id, ApiAccessRule.deleted_at.is_(None), ApiAccessRule.action == "block",
        ApiAccessRule.enabled.is_(True)))).scalars())
    now = datetime.now(UTC)
    today = datetime(now.year, now.month, now.day, tzinfo=UTC)
    base = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    rows: list[dict] = []

    def add(at: datetime, endpoint: ApiEndpoint, method: str, status: int, code: str | None, ms: int, token: ApiToken | None,
            seed: str, **extra: object) -> None:
        service = services.get(endpoint.service_id)
        one = method != "POST" and seed_of(f"{seed}:o") % 3 == 0
        v6 = seed_of(f"{seed}:6") % 5 == 0
        rows.append({
            **base, "id": uuid7(), "at": at, "method": method,
            "path": f"/{settings.api_key}/{endpoint.name}" + (f"/rsp_{seed_of(seed + ':r') % 100000:x}"
                                                             if one or method in ("PUT", "DELETE") else ""),
            "status": status, "code": code, "duration_ms": ms, "endpoint_id": endpoint.id, "endpoint_name": endpoint.name,
            "service_id": service.id if service else None, "service_name": service.name if service else None,
            "token_id": token.id if token else None, "token_name": token.name if token else None,
            "token_mode": token.mode if token else None, "rule_id": None, "rate_limited": False,
            "ip": f"2001:db8::{seed_of(seed + ':i') % 65535:x}" if v6 else
            f"{'203.0.113' if seed_of(seed + ':n') % 2 else '198.51.100'}.{seed_of(seed + ':i') % 250 + 2}",
            "country": COUNTRIES[seed_of(seed + ":g") % len(COUNTRIES)], "origin": None,
            "user_agent": AGENTS[seed_of(seed + ":u") % len(AGENTS)], "request_id": uuid_of(f"req:{seed}"),
            "request_headers": {"user-agent": AGENTS[seed_of(seed + ":u") % len(AGENTS)], "content-type": "application/json",
                                "authorization": f"Bearer {token.preview}" if token else "Bearer"},
            **extra,
        })

    for endpoint in endpoints:
        service = services.get(endpoint.service_id)
        form = forms.get(endpoint.form_id)
        live = endpoint.status == "active" and service is not None and service.status == "active" and form is not None \
            and form.status == "published" and form.deleted_at is None
        key = str(endpoint.id)
        base_count = 3 + seed_of(key) % (PER_DAY - 3)
        share = 0.01 + (seed_of(key) % 5) / 100
        avg = 40 + seed_of(key) % 140
        for back in range(DAYS):
            day = today - timedelta(days=back)
            if (not live and back < 12) or day + timedelta(days=1) < endpoint.created_at:
                continue
            shape = 0.35 if day.weekday() >= 5 else 1.0
            count = round(base_count * shape * (0.7 + (seed_of(f"{key}:{back}") % 60) / 100))
            for i in range(count):
                seed = f"{key}:{day.date()}:{i}"
                at = day + timedelta(milliseconds=seed_of(seed + ":t") % 86_400_000)
                if at > now:
                    continue
                method = endpoint.methods[seed_of(seed + ":m") % len(endpoint.methods)] if endpoint.methods else "POST"
                failed = (seed_of(seed + ":e") % 1000) / 1000 < share
                status, code = ERRORS[seed_of(seed + ":c") % len(ERRORS)] if failed else (201 if method == "POST" else 200, None)
                callers = [t for t in tokens if t.revoked_at is None and (t.expires_at is None or t.expires_at > at)
                           and T.scope_allows(t.scopes, key, str(endpoint.service_id), method)]
                token = None if code == "FRM-API-1010" or not callers else callers[seed_of(seed + ":k") % len(callers)]
                ms = max(8, round(avg * (0.4 + (seed_of(seed + ":d") % 220) / 100)))
                add(at, endpoint, method, status, code, ms, token, seed, rate_limited=code == "FRM-GEN-1029")
        # Callers the sample block rules turned away, now and then
        for rule in rules:
            for back in range(DAYS):
                seed = f"{rule.id}:{key}:{back}"
                if seed_of(seed) % 4:
                    continue
                at = today - timedelta(days=back) + timedelta(milliseconds=seed_of(seed + ":t") % 86_400_000)
                if at > now or at < rule.created_at:
                    continue
                values = list(rule.values)
                ip = values[0] if rule.kind == "ip" and "/" not in values[0] else "192.0.2.66"
                add(at, endpoint, endpoint.methods[0] if endpoint.methods else "POST", 403, "FRM-API-1015",
                    5 + seed_of(seed + ":d") % 20, None, seed, rule_id=rule.id, ip=ip,
                    origin="https://x.spam-example.net" if rule.kind == "domain" else None)
    for start in range(0, len(rows), 500):
        await session.execute(insert(ApiRequestLog), rows[start:start + 500])
    await session.flush()
    return len(rows)

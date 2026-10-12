"""API traffic (B10 step 2; mock: data/apiTraffic.ts, routes/apiTraffic.ts): the request log of the public API and
every number read from it.

- `record_call` is the write path: the gateway (gateway.py) calls it once per call, inside the workspace's context.
  It keeps the call's facts, the names of what was called as they were then, headers with secrets masked and, only
  while the workspace keeps them, the bodies with personal answers masked. Never the token itself: whatever the
  workspace chose, ALWAYS_MASKED fields and secret-looking values (B17 review M10) are masked in every body.
- `load_usage` reads, in three grouped queries, what every list of services, endpoints, tokens and access rules
  shows: calls per day for 60 days (this window and the one before), errors, the median answer time, the last call,
  rule hits. Days are UTC days; "30 days" is today and the 29 days before, like the mock.
- The log list, its insights and the analytics page are queries of their own (`list_logs`, `log_insights`,
  `analytics`).
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.core.logging.redact import redact_text
from app.modules.api_service import tokens as T
from app.modules.api_service.models import ApiAccessRule, ApiEndpoint, ApiRequestLog, ApiService, ApiSettings, ApiToken

PERSONAL_TYPES = frozenset({"email", "phone", "full_name", "address", "iban", "bic", "ip_address", "signature", "date"})
# The Docs console's token (Try it): never stored, so its calls carry only its name and mode (mock: `__console__`)
CONSOLE_TOKEN_ID = "__console__"
SECRET_HEADERS = frozenset({"authorization", "x-formalie-signature", "cookie"})
DROPPED_HEADERS = frozenset({"cookie", "host", "connection"})
BODY_TEXT_MAX = 2000
# Masked in every kept body at any depth, whatever the workspace chose (the token address's client secret and the
# tokens it issues): SECURITY-PROTOCOL §9, request logs never store tokens
ALWAYS_MASKED = frozenset({"client_secret", "access_token", "refresh_token", "id_token", "password", "token", "secret",
                           "api_key", "authorization"})
_BEARER = re.compile(r"^Bearer\s+", re.IGNORECASE)


def js_round(value: float) -> int:
    """Math.round: halves go up."""
    return math.floor(value + 0.5)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


# ── Masking (mock: core/mask.ts) ─────────────────────────────────────────────────

def _mask_text(value: Any) -> Any:
    if isinstance(value, str):
        return "••" if len(value) <= 2 else f"{value[0]}•••{value[-1]}"
    if isinstance(value, list):
        return [_mask_text(v) for v in value]
    if isinstance(value, dict):
        return {k: _mask_text(v) for k, v in value.items()}
    return value if value is None else "•••"


def mask_answers(value: Any, personal: set[str] | frozenset[str]) -> Any:
    """Masks the values of the given question keys at any depth: `a•••z` for text, `•••` for anything else."""
    if isinstance(value, list):
        return [mask_answers(v, personal) for v in value]
    if not isinstance(value, dict):
        return value
    return {k: _mask_text(v) if k in personal else mask_answers(v, personal) for k, v in value.items()}


def mask_secrets(value: Any, depth: int = 0) -> Any:
    """ALWAYS_MASKED fields as `••••` at any depth, and secret-looking values (tokens, keys) in any string."""
    if depth > 8:
        return value
    if isinstance(value, dict):
        return {k: "••••" if str(k).lower() in ALWAYS_MASKED and v is not None else mask_secrets(v, depth + 1)
                for k, v in value.items()}
    if isinstance(value, list):
        return [mask_secrets(v, depth + 1) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def masked_headers(headers: dict[str, str], secret_names: set[str] | None = None) -> dict[str, str]:
    """The headers a call sent, as the log keeps them: no cookies, host or browser `sec-` headers; the bearer token as
    its preview; other secrets (signatures, the endpoint's required headers) as dots; values cut at 200 characters."""
    secret = SECRET_HEADERS | {n.lower() for n in secret_names or set()}
    out: dict[str, str] = {}
    for raw_name, value in headers.items():
        name = raw_name.lower()
        if value is None or name in DROPPED_HEADERS or name.startswith("sec-"):
            continue
        if name == "authorization":
            out[name] = f"Bearer {T.secret_preview(_BEARER.sub('', str(value)))}"
        elif name in secret:
            out[name] = "••••"
        else:
            out[name] = str(value)[:200]
    return out


# ── The write path (the gateway, B10 step 3) ───────────────────────────────────────

@dataclass
class ApiCall:
    """One call to the public API, as the gateway saw it."""

    method: str
    path: str  # `/{apiKey}/{endpoint}[/{id}]`, without the query
    status: int
    duration_ms: int
    ip: str
    request_id: str
    at: datetime | None = None
    code: str | None = None  # the FRM-* code of a refused call
    endpoint_id: uuid.UUID | None = None
    service_id: uuid.UUID | None = None
    token_id: uuid.UUID | None = None
    token_label: tuple[str, str] | None = None  # (name, mode) of a token that is not stored (the Docs console)
    rule_id: uuid.UUID | None = None  # the access rule that decided the call
    rate_limited: bool = False
    country: str | None = None
    origin: str | None = None
    user_agent: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    secret_headers: set[str] = field(default_factory=set)  # the endpoint's required headers
    request_raw: str | None = None  # the body as it came
    response_body: Any = None
    personal: set[str] = field(default_factory=set)  # names of personal answers in the bodies


async def record_call(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, call: ApiCall) -> uuid.UUID:
    """Writes one call to the request log (inside the workspace's RLS context) and stamps the token's last use and the
    deciding rule's last hit. Returns the log entry's id."""
    import json

    at = call.at or datetime.now(UTC)
    settings = (await db.execute(text("SELECT log_keep_bodies FROM api_settings WHERE tenant_id = :t"),
                                 {"t": tenant_id})).scalar_one_or_none()
    keep = bool(settings)
    endpoint = await db.get(ApiEndpoint, call.endpoint_id) if call.endpoint_id else None
    service_id = call.service_id or (endpoint.service_id if endpoint else None)
    service = await db.get(ApiService, service_id) if service_id else None
    token = await db.get(ApiToken, call.token_id) if call.token_id else None
    request_body: Any = None
    if keep and call.request_raw:
        try:
            request_body = mask_secrets(mask_answers(json.loads(call.request_raw), call.personal))
        except ValueError:
            request_body = redact_text(call.request_raw[:BODY_TEXT_MAX])
    entry = ApiRequestLog(
        id=uuid7(), tenant_id=tenant_id, organisation_id=organisation_id, at=at, method=call.method.upper()[:10],
        path=call.path.split("?")[0], status=call.status, code=call.code, duration_ms=max(0, int(call.duration_ms)),
        endpoint_id=endpoint.id if endpoint else None, endpoint_name=endpoint.name if endpoint else None,
        service_id=service.id if service else None, service_name=service.name if service else None,
        token_id=token.id if token else None,
        token_name=token.name if token else call.token_label[0] if call.token_label else None,
        token_mode=token.mode if token else call.token_label[1] if call.token_label else None, rule_id=call.rule_id, rate_limited=call.rate_limited,
        ip=call.ip[:64] or "0.0.0.0", country=(call.country or None) and call.country.upper()[:2],
        origin=(call.origin or None) and call.origin[:300], user_agent=(call.user_agent or "")[:200],
        request_id=call.request_id[:100], request_headers=masked_headers(call.headers, call.secret_headers),
        request_body=request_body,
        response_body=mask_secrets(mask_answers(call.response_body, call.personal)) if keep else None)
    db.add(entry)
    if token is not None:
        await db.execute(update(ApiToken).where(ApiToken.tenant_id == tenant_id, ApiToken.id == token.id)
                         .values(last_used_at=at))
    if call.rule_id is not None:
        await db.execute(update(ApiAccessRule).where(ApiAccessRule.tenant_id == tenant_id, ApiAccessRule.id == call.rule_id)
                         .values(last_hit_at=at))
    from app.core.config import get_settings
    from app.modules.platform_bridge.events import emit, sampled

    rate = get_settings().platform_events_api_sample
    if sampled(rate):  # the platform's usage analytics (PLATFORM-ADMIN-INTEGRATION §4), counts and timings only
        await emit(db, "api.called", {
            "endpoint_id": str(entry.endpoint_id) if entry.endpoint_id else None,
            "service_id": str(entry.service_id) if entry.service_id else None, "method": entry.method,
            "status": entry.status, "duration_ms": entry.duration_ms, "token_mode": entry.token_mode,
            "sample_rate": rate}, tenant_id=tenant_id, organisation_id=organisation_id, source="api")
    await db.flush()
    return entry.id


# ── Days ───────────────────────────────────────────────────────────────────────

def today() -> date:
    return datetime.now(UTC).date()


def day_start(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def days_back(n: int, end: date | None = None) -> list[date]:
    last = end or today()
    return [last - timedelta(days=n - 1 - i) for i in range(n)]


# ── Usage per endpoint, token and rule (the lists) ─────────────────────────────────

@dataclass
class Usage:
    calls: dict[date, int] = field(default_factory=dict)
    errors: dict[date, int] = field(default_factory=dict)
    median: float | None = None
    last: datetime | None = None


@dataclass
class Traffic:
    endpoints: dict[uuid.UUID, Usage] = field(default_factory=dict)
    tokens: dict[uuid.UUID, Usage] = field(default_factory=dict)
    rules: dict[uuid.UUID, Usage] = field(default_factory=dict)
    limited: dict[date, int] = field(default_factory=dict)


_SETS = {3: "endpoints", 5: "tokens", 6: "rules"}  # GROUPING(endpoint_id, token_id, rule_id)


async def load_usage(db: AsyncSession, tenant_id: uuid.UUID) -> Traffic:
    """Calls, errors, answer times, last calls and rule hits of every endpoint, token and rule, in three queries."""
    out = Traffic()
    first = day_start(today() - timedelta(days=59))
    window = day_start(today() - timedelta(days=29))
    day = "((at AT TIME ZONE 'UTC')::date)"

    def slot(g: int, endpoint_id: Any, token_id: Any, rule_id: Any) -> Usage | None:
        group = _SETS.get(g)
        key = {"endpoints": endpoint_id, "tokens": token_id, "rules": rule_id}.get(group or "")
        if key is None:
            return None
        return getattr(out, group).setdefault(key, Usage())  # type: ignore[arg-type]

    rows = (await db.execute(text(
        f"SELECT GROUPING(endpoint_id, token_id, rule_id), endpoint_id, token_id, rule_id, {day}, count(*), "
        f"count(*) FILTER (WHERE status >= 400), count(*) FILTER (WHERE rate_limited) FROM api_request_logs "
        f"WHERE tenant_id = :t AND at >= :first "
        f"GROUP BY GROUPING SETS ((endpoint_id, {day}), (token_id, {day}), (rule_id, {day}), ({day}))"),
        {"t": tenant_id, "first": first})).all()
    for g, endpoint_id, token_id, rule_id, d, calls, errors, limited in rows:
        if g == 7:
            if limited:
                out.limited[d] = limited
            continue
        use = slot(g, endpoint_id, token_id, rule_id)
        if use is not None:
            use.calls[d], use.errors[d] = calls, errors
    for g, endpoint_id, token_id, rule_id, median in (await db.execute(text(
            "SELECT GROUPING(endpoint_id, token_id, rule_id), endpoint_id, token_id, rule_id, "
            "percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) FROM api_request_logs "
            "WHERE tenant_id = :t AND at >= :window GROUP BY GROUPING SETS ((endpoint_id), (token_id), (rule_id))"),
            {"t": tenant_id, "window": window})).all():
        use = slot(g, endpoint_id, token_id, rule_id)
        if use is not None:
            use.median = median
    for g, endpoint_id, token_id, rule_id, last in (await db.execute(text(
            "SELECT GROUPING(endpoint_id, token_id, rule_id), endpoint_id, token_id, rule_id, max(at) "
            "FROM api_request_logs WHERE tenant_id = :t GROUP BY GROUPING SETS ((endpoint_id), (token_id), (rule_id))"),
            {"t": tenant_id})).all():
        use = slot(g, endpoint_id, token_id, rule_id)
        if use is not None:
            use.last = last
    return out


def usage_view(use: Usage | None, also_last: datetime | None = None) -> dict[str, Any]:
    """ApiUsage: the last 30 days (with the 30 before), errors, the median answer time and the last call."""
    use = use or Usage()
    days = days_back(30)
    previous = days_back(30, days[0] - timedelta(days=1))
    daily = [{"date": d.isoformat(), "count": use.calls.get(d, 0)} for d in days]
    calls = sum(item["count"] for item in daily)
    last = max((v for v in (use.last, also_last) if v is not None), default=None)
    return {"calls_30d": calls, "previous_30d": sum(use.calls.get(d, 0) for d in previous),
            "errors_30d": sum(use.errors.get(d, 0) for d in days), "daily": daily,
            "avg_ms": js_round(use.median) if use.median is not None and calls else None, "last_call_at": iso(last)}


def sum_usage(items: list[dict[str, Any]]) -> dict[str, Any]:
    """sumUsage(): counts added up, the mean of the answer times, the latest call."""
    if not items:
        return usage_view(None)
    times = [u["avg_ms"] for u in items if u["avg_ms"] is not None]
    lasts = [u["last_call_at"] for u in items if u["last_call_at"]]
    return {"calls_30d": sum(u["calls_30d"] for u in items), "previous_30d": sum(u["previous_30d"] for u in items),
            "errors_30d": sum(u["errors_30d"] for u in items),
            "daily": [{"date": d["date"], "count": sum(u["daily"][i]["count"] for u in items)}
                      for i, d in enumerate(items[0]["daily"])],
            "avg_ms": js_round(sum(times) / len(times)) if times else None, "last_call_at": max(lasts) if lasts else None}


def hits_view(use: Usage | None, also_last: datetime | None) -> dict[str, Any]:
    """A rule's hits in the last 30 days."""
    view = usage_view(use, also_last)
    return {"hits_30d": view["calls_30d"], "daily": view["daily"], "last_hit_at": view["last_call_at"]}


# ── The log (GET /api-logs) ─────────────────────────────────────────────────────

LOG_SORTS = {"at": "at", "duration_ms": "duration_ms", "status": "status"}
_CLASS_SQL = {"2xx": "status < 400", "4xx": "(status >= 400 AND status < 500)", "5xx": "status >= 500"}


def entry_view(row: Any) -> dict[str, Any]:
    """ApiLogEntry."""
    return {
        "id": str(row.id), "at": iso(row.at), "method": row.method, "path": row.path, "status": row.status,
        "code": row.code, "duration_ms": row.duration_ms,
        "endpoint": {"id": str(row.endpoint_id), "name": row.endpoint_name or ""} if row.endpoint_id else None,
        "service": {"id": str(row.service_id), "name": row.service_name or ""} if row.service_id else None,
        "token": {"id": str(row.token_id), "name": row.token_name or "", "mode": row.token_mode or "live"}
        if row.token_id else {"id": CONSOLE_TOKEN_ID, "name": row.token_name, "mode": row.token_mode or "test"}
        if row.token_name else None,
        "ip": row.ip, "country": row.country, "user_agent": row.user_agent, "request_id": row.request_id,
    }


def detail_view(row: ApiRequestLog) -> dict[str, Any]:
    """ApiLogDetail: the entry with the headers and the kept bodies."""
    kept = row.request_body is not None or row.response_body is not None
    return {**entry_view(row), "request_body": row.request_body, "response_body": row.response_body,
            "request_headers": dict(row.request_headers or {}), "bodies_kept": kept}


def _ids(value: str | None) -> list[uuid.UUID]:
    out = []
    for part in (value or "").split(","):
        try:
            out.append(uuid.UUID(part))
        except ValueError:
            out.append(uuid.UUID(int=0))  # matches nothing, like an unknown id in the mock
    return out


def _date(value: str | None, end: bool) -> datetime | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return None
    start = day_start(d)
    return start + timedelta(days=1) - timedelta(milliseconds=1) if end else start


async def list_logs(db: AsyncSession, tenant_id: uuid.UUID, query: dict[str, str], offset: int,
                    limit: int) -> tuple[list[dict[str, Any]], int]:
    """The log between `from` and `to` (default the last 7 days), filtered, searched, sorted, one page."""
    now = datetime.now(UTC)
    start = _date(query.get("from"), False) or now - timedelta(days=7)
    end = _date(query.get("to"), True) or now
    where = ["tenant_id = :t", "at >= :start", "at <= :end"]
    params: dict[str, Any] = {"t": tenant_id, "start": start, "end": end}
    if query.get("filter[endpoint]"):
        where.append("endpoint_id = ANY(:endpoints)")
        params["endpoints"] = _ids(query["filter[endpoint]"])
    if query.get("filter[class]"):
        classes = [_CLASS_SQL[c] for c in query["filter[class]"].split(",") if c in _CLASS_SQL]
        where.append(f"({' OR '.join(classes)})" if classes else "false")
    if query.get("filter[method]"):
        where.append("method = ANY(:methods)")
        params["methods"] = query["filter[method]"].split(",")
    if query.get("filter[token]"):
        where.append("token_id = ANY(:tokens)")
        params["tokens"] = _ids(query["filter[token]"])
    if query.get("filter[mode]"):
        where.append("(token_id IS NOT NULL OR token_name IS NOT NULL) AND token_mode = ANY(:modes)")  # the console too
        params["modes"] = query["filter[mode]"].split(",")
    q = (query.get("q") or "").strip().lower()
    if q:
        where.append("strpos(lower(path || ' ' || ip || ' ' || request_id || ' ' || coalesce(code, '') || ' ' || "
                     "coalesce(token_name, '')), :q) > 0")
        params["q"] = q
    sort = query.get("sort") or "-at"
    desc = sort.startswith("-")
    column = LOG_SORTS.get(sort.lstrip("-"), "at")
    order = f"{column} {'DESC' if desc else 'ASC'}" + (", at DESC" if column != "at" else "") + ", id DESC"
    clause = " AND ".join(where)
    total = (await db.execute(text(f"SELECT count(*) FROM api_request_logs WHERE {clause}"), params)).scalar_one()
    rows = (await db.execute(text(
        f"SELECT id, at, method, path, status, code, duration_ms, endpoint_id, endpoint_name, service_id, service_name, "
        f"token_id, token_name, token_mode, ip, country, user_agent, request_id FROM api_request_logs WHERE {clause} "
        f"ORDER BY {order} OFFSET :offset LIMIT :limit"), {**params, "offset": offset, "limit": limit})).all()
    return [entry_view(r) for r in rows], total


# ── Insights (GET /api-logs/insights) ─────────────────────────────────────────────

async def log_insights(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """ApiLogInsights: 30 days of calls with the 30 before, errors, calls by status class, the median answer time."""
    days = days_back(30)
    first = day_start(days[0] - timedelta(days=30))
    window = day_start(days[0])
    per_day = {d: n for d, n in (await db.execute(text(
        "SELECT (at AT TIME ZONE 'UTC')::date, count(*) FROM api_request_logs WHERE tenant_id = :t AND at >= :first "
        "GROUP BY 1"), {"t": tenant_id, "first": first})).all()}
    two, four, five, median = (await db.execute(text(
        "SELECT count(*) FILTER (WHERE status < 400), count(*) FILTER (WHERE status >= 400 AND status < 500), "
        "count(*) FILTER (WHERE status >= 500), percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) "
        "FROM api_request_logs WHERE tenant_id = :t AND at >= :window"), {"t": tenant_id, "window": window})).one()
    daily = [{"date": d.isoformat(), "count": per_day.get(d, 0)} for d in days]
    previous = days_back(30, days[0] - timedelta(days=1))
    return {"calls_30d": sum(i["count"] for i in daily), "previous_30d": sum(per_day.get(d, 0) for d in previous),
            "errors_30d": four + five, "daily": daily, "by_class": {"2xx": two, "4xx": four, "5xx": five},
            "avg_ms": js_round(median) if median is not None else None}


# ── Analytics (GET /api-analytics) ──────────────────────────────────────────────

async def _totals(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime,
                  live_tokens: list[uuid.UUID]) -> dict[str, Any]:
    calls, errors, p50, p95 = (await db.execute(text(
        "SELECT count(*), count(*) FILTER (WHERE status >= 400), percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms), "
        "percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) FROM api_request_logs "
        "WHERE tenant_id = :t AND at >= :s AND at < :e"), {"t": tenant_id, "s": start, "e": end})).one()
    used = (await db.execute(text(
        "SELECT count(DISTINCT token_id) FROM api_request_logs WHERE tenant_id = :t AND at >= :s AND at < :e "
        "AND token_id = ANY(:live)"), {"t": tenant_id, "s": start, "e": end, "live": live_tokens})).scalar_one()
    return {"calls": calls, "errors": errors, "p50_ms": js_round(p50) if p50 is not None else None,
            "p95_ms": js_round(p95) if p95 is not None else None, "tokens_used": used}


async def analytics(db: AsyncSession, tenant_id: uuid.UUID, period: str | None, services: list[ApiService],
                    endpoints: list[ApiEndpoint], tokens: list[ApiToken]) -> dict[str, Any]:
    """ApiAnalytics for the last 7 or 30 days (anything else is 30), with the same span before."""
    n = 7 if period == "7d" else 30
    days = days_back(n)
    start, end = day_start(days[0]), day_start(days[-1] + timedelta(days=1))
    before = start - timedelta(days=n)
    live = [t for t in tokens if t.revoked_at is None]
    live_ids = [t.id for t in live]
    params = {"t": tenant_id, "s": start, "e": end}
    day = "((at AT TIME ZONE 'UTC')::date)"
    daily = {d: (c, e) for d, c, e in (await db.execute(text(
        f"SELECT {day}, count(*), count(*) FILTER (WHERE status >= 400) FROM api_request_logs "
        f"WHERE tenant_id = :t AND at >= :s AND at < :e GROUP BY 1"), params)).all()}
    per_endpoint = {(eid, d): c for eid, d, c in (await db.execute(text(
        f"SELECT endpoint_id, {day}, count(*) FROM api_request_logs WHERE tenant_id = :t AND at >= :s AND at < :e "
        f"AND endpoint_id IS NOT NULL GROUP BY 1, 2"), params)).all()}
    endpoint_facts = {eid: (c, e, p95) for eid, c, e, p95 in (await db.execute(text(
        "SELECT endpoint_id, count(*), count(*) FILTER (WHERE status >= 400), "
        "percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) FROM api_request_logs "
        "WHERE tenant_id = :t AND at >= :s AND at < :e AND endpoint_id IS NOT NULL GROUP BY 1"), params)).all()}
    token_facts = {tid: (c, e) for tid, c, e in (await db.execute(text(
        "SELECT token_id, count(*), count(*) FILTER (WHERE status >= 400) FROM api_request_logs "
        "WHERE tenant_id = :t AND at >= :s AND at < :e AND token_id IS NOT NULL GROUP BY 1"), params)).all()}
    countries = (await db.execute(text(
        "SELECT country, count(*) FROM api_request_logs WHERE tenant_id = :t AND at >= :s AND at < :e "
        "AND country IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 10"), params)).all()
    methods = dict.fromkeys(T.API_METHODS, 0)
    for method, count in (await db.execute(text(
            "SELECT method, count(*) FROM api_request_logs WHERE tenant_id = :t AND at >= :s AND at < :e GROUP BY 1"),
            params)).all():
        if method in methods:
            methods[method] = count
    names = {s.id: s.name for s in services}
    endpoint_rows = []
    for e in endpoints:
        calls, errors, p95 = endpoint_facts.get(e.id, (0, 0, None))
        endpoint_rows.append({"id": str(e.id), "name": e.name, "service": names.get(e.service_id, ""), "calls": calls,
                              "errors": errors, "p95_ms": js_round(p95) if p95 is not None else None,
                              "trend": [per_endpoint.get((e.id, d), 0) for d in days]})
    token_rows = [{"id": str(t.id), "name": t.name, "mode": t.mode, "calls": token_facts.get(t.id, (0, 0))[0],
                   "errors": token_facts.get(t.id, (0, 0))[1]} for t in live]
    return {
        "from": days[0].isoformat(), "to": days[-1].isoformat(),
        "totals": await _totals(db, tenant_id, start, end, live_ids),
        "previous": await _totals(db, tenant_id, before, start, live_ids),
        "daily": [{"date": d.isoformat(), "calls": daily.get(d, (0, 0))[0], "errors": daily.get(d, (0, 0))[1]} for d in days],
        "endpoints": sorted(endpoint_rows, key=lambda r: -r["calls"]),
        "tokens": sorted(token_rows, key=lambda r: -r["calls"]),
        "countries": [{"code": code, "calls": calls} for code, calls in countries],
        "methods": methods,
    }


# ── Settings and keeping bodies ─────────────────────────────────────────────────

def log_settings_view(row: ApiSettings) -> dict[str, Any]:
    """ApiLogSettings."""
    return {"keep_bodies": row.log_keep_bodies, "days": row.log_days}


async def prune_bodies(db: AsyncSession, tenant_id: uuid.UUID, days: int) -> int:
    """Bodies older than the workspace keeps them are cleared (the call itself stays in the log)."""
    result = await db.execute(text(
        "UPDATE api_request_logs SET request_body = NULL, response_body = NULL WHERE tenant_id = :t AND at < :before "
        "AND (request_body IS NOT NULL OR response_body IS NOT NULL)"),
        {"t": tenant_id, "before": datetime.now(UTC) - timedelta(days=days)})
    return result.rowcount or 0  # type: ignore[attr-defined]

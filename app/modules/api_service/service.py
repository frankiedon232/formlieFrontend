"""The API service as the portal sees it (mock: data/apiStore.ts): the workspace's address handle, and every service,
endpoint, token and access rule in the shapes of shared/types/apiService.ts.

Traffic is B10 step 2: until the request log exists, every count of calls is 0, `daily` is 30 days of 0, answer times
and the last call are None, and access rules have no hits. The shapes are the final ones, so nothing changes for the
portal when the numbers arrive.
"""

from __future__ import annotations

import functools
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import get_context
from app.core.ids import uuid7
from app.modules.api_service import access as A
from app.modules.api_service import tokens as T
from app.modules.api_service.endpoints import endpoint_fields_of
from app.modules.api_service.models import ApiAccessRule, ApiEndpoint, ApiService, ApiSettings, ApiToken
from app.modules.forms.models import Form, FormVersion
from app.modules.forms.router import _natural
from app.modules.forms.service import Names

API_METHODS = T.API_METHODS
HANDLE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
DEFAULT_LIMITS = {"per_token": 600, "per_ip": 120, "per_endpoint": 1200}
FORM_CHANNELS = ("link", "embed", "api")


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


def base_url() -> str:
    """The API service's own address (`https://api.formalie.dev`, `.com` in production)."""
    return f"https://api.{get_settings().root_domain}"


def endpoint_url(api_key: str, name: str) -> str:
    return f"{base_url().rstrip('/')}/{api_key}/{name}"


def ref_uuid(value: Any) -> uuid.UUID | None:
    """An id from a body or query, only when it arrived as an encrypted reference (SECURITY-PROTOCOL §10)."""
    ctx = get_context()
    if not isinstance(value, str) or ctx is None or value.lower() not in {i.lower() for i in ctx.ref_ids}:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def path_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


# ── Usage (B10 step 2) ────────────────────────────────────────────────────────────

def thirty_days() -> list[dict[str, Any]]:
    today = datetime.now(UTC).date()
    return [{"date": (today - timedelta(days=29 - i)).isoformat(), "count": 0} for i in range(30)]


def usage(last_call_at: str | None = None) -> dict[str, Any]:
    """ApiUsage. TODO(B10 step 2): counted from the request log (api_usage_daily); zeros until then."""
    return {"calls_30d": 0, "previous_30d": 0, "errors_30d": 0, "daily": thirty_days(), "avg_ms": None,
            "last_call_at": last_call_at}


def insights_of(statuses: list[str], methods: list[list[str]]) -> dict[str, Any]:
    """ApiInsights, the chart cards of Services and Endpoints."""
    use = usage()
    return {"total": len(statuses),
            "by_status": {"active": statuses.count("active"), "disabled": statuses.count("disabled")},
            "by_method": {m: sum(1 for ms in methods if m in ms) for m in API_METHODS},
            "calls_30d": use["calls_30d"], "previous_30d": use["previous_30d"], "errors_30d": use["errors_30d"],
            "daily": use["daily"], "avg_ms": use["avg_ms"]}


# ── Sorting and filters, like the mock's lists ─────────────────────────────────────

def _js_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "[object Object]"
    if isinstance(value, list):
        return ",".join(_js_text(v) for v in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def sort_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    """sortRows(): numbers as numbers, everything else as text with numbers inside compared as numbers."""
    desc = sort.startswith("-")
    key = sort[1:] if desc else sort

    def compare(a: dict[str, Any], b: dict[str, Any]) -> int:
        x, y = a.get(key), b.get(key)
        x = "" if x is None else x
        y = "" if y is None else y
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
            order = (x > y) - (x < y)
        else:
            nx, ny = _natural(_js_text(x)), _natural(_js_text(y))
            order = (nx > ny) - (nx < ny)
        return -order if desc else order

    return sorted(rows, key=functools.cmp_to_key(compare))


def in_list(value: str | None, actual: str) -> bool:
    return not value or actual in value.split(",")


# ── Settings and the address handle ─────────────────────────────────────────────

def new_handle() -> str:
    return "".join(HANDLE_ALPHABET[b % len(HANDLE_ALPHABET)] for b in secrets.token_bytes(10))


async def claim_handle(db: AsyncSession) -> str:
    """A new handle, registered in the tenant directory for this workspace (never one used before)."""
    for _ in range(10):
        handle = new_handle()
        if (await db.execute(text("SELECT platform.claim_api_key(:k)"), {"k": handle})).scalar():
            return handle
    raise RuntimeError("no free API key after 10 tries")


async def ensure_settings(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> ApiSettings:
    """The workspace's API settings, made with a new handle the first time (sign-up makes them too)."""
    found = (await db.execute(select(ApiSettings).where(ApiSettings.tenant_id == tenant_id))).scalar_one_or_none()
    if found is not None:
        return found
    handle = await claim_handle(db)
    # Two first visits at once (the API service page loads several lists together): one row wins, the other's
    # handle is retired at once and never answers
    made = (await db.execute(insert(ApiSettings).values(
        id=uuid7(), tenant_id=tenant_id, organisation_id=organisation_id, api_key=handle,
        rate_per_token=DEFAULT_LIMITS["per_token"], rate_per_ip=DEFAULT_LIMITS["per_ip"],
        rate_per_endpoint=DEFAULT_LIMITS["per_endpoint"]).on_conflict_do_nothing(
        index_elements=["tenant_id"]).returning(ApiSettings.id))).scalar_one_or_none()
    if made is None:
        await db.execute(text("SELECT platform.retire_api_key(:k, now())"), {"k": handle})
    return (await db.execute(select(ApiSettings).where(ApiSettings.tenant_id == tenant_id))).scalar_one()


def settings_view(row: ApiSettings) -> dict[str, Any]:
    """ApiServiceSettings: the old handle is shown only while it still answers."""
    grace = row.previous_until is not None and row.previous_until > datetime.now(UTC)
    return {"api_key": row.api_key, "base_url": base_url(), "previous_key": row.previous_key if grace else None,
            "previous_until": iso(row.previous_until) if grace else None, "rotated_at": iso(row.rotated_at)}


def limits_view(row: ApiSettings) -> dict[str, Any]:
    return {"per_token": row.rate_per_token, "per_ip": row.rate_per_ip, "per_endpoint": row.rate_per_endpoint,
            "updated_at": iso(row.limits_updated_at)}


# ── Everything of a workspace, read once per request ─────────────────────────────

@dataclass
class FormFacts:
    id: uuid.UUID
    name: str
    status: str
    deleted: bool
    channels: list[str]
    published_version_id: uuid.UUID | None
    versions: list[int] = field(default_factory=list)


@dataclass
class Store:
    tenant_id: uuid.UUID
    settings: ApiSettings | None = None
    services: list[ApiService] = field(default_factory=list)
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    tokens: list[ApiToken] = field(default_factory=list)
    rules: list[ApiAccessRule] = field(default_factory=list)
    forms: dict[uuid.UUID, FormFacts] = field(default_factory=dict)
    names: Names = field(default_factory=Names)

    async def load(self, db: AsyncSession, *, forms: bool = True) -> Store:
        t = self.tenant_id
        self.settings = (await db.execute(select(ApiSettings).where(ApiSettings.tenant_id == t))).scalar_one_or_none()
        self.services = list((await db.execute(select(ApiService).where(
            ApiService.tenant_id == t, ApiService.deleted_at.is_(None)).order_by(ApiService.created_at))).scalars())
        self.endpoints = list((await db.execute(select(ApiEndpoint).where(
            ApiEndpoint.tenant_id == t, ApiEndpoint.deleted_at.is_(None)).order_by(ApiEndpoint.created_at))).scalars())
        self.tokens = list((await db.execute(select(ApiToken).where(
            ApiToken.tenant_id == t, ApiToken.deleted_at.is_(None)).order_by(ApiToken.created_at.desc()))).scalars())
        self.rules = list((await db.execute(select(ApiAccessRule).where(
            ApiAccessRule.tenant_id == t, ApiAccessRule.deleted_at.is_(None)).order_by(ApiAccessRule.created_at.desc()))).scalars())
        if forms:
            await self.load_forms(db, {e.form_id for e in self.endpoints})
        await self.names.load(db, t)
        return self

    async def load_forms(self, db: AsyncSession, ids: set[uuid.UUID]) -> None:
        wanted = ids - set(self.forms)
        if not wanted:
            return
        for f in (await db.execute(select(Form).where(Form.tenant_id == self.tenant_id, Form.id.in_(wanted)))).scalars():
            self.forms[f.id] = FormFacts(f.id, f.name, f.status, f.deleted_at is not None or f.purged_at is not None,
                                         list(f.channels) if f.channels else list(FORM_CHANNELS), f.published_version_id)
        for form_id, number in (await db.execute(select(FormVersion.form_id, FormVersion.number).where(
                FormVersion.tenant_id == self.tenant_id, FormVersion.form_id.in_(wanted)))).all():
            if form_id in self.forms:
                self.forms[form_id].versions.append(number)
        for facts in self.forms.values():
            facts.versions.sort(reverse=True)

    def service(self, service_id: Any) -> ApiService | None:
        return next((s for s in self.services if s.id == service_id), None)

    def endpoint(self, endpoint_id: Any) -> ApiEndpoint | None:
        return next((e for e in self.endpoints if e.id == endpoint_id), None)

    def by(self, user_id: uuid.UUID | None) -> dict[str, str]:
        return self.names.ref(user_id) or {"id": "", "name": "Formalie"}


async def schema_of(db: AsyncSession, tenant_id: uuid.UUID, form: FormFacts | Form, version: int | None) -> dict[str, Any] | None:
    """The schema an endpoint uses: its pinned version, else the latest published one."""
    if version is not None:
        row = (await db.execute(select(FormVersion.schema).where(
            FormVersion.tenant_id == tenant_id, FormVersion.form_id == form.id, FormVersion.number == version))).scalar_one_or_none()
        return row
    if not form.published_version_id:
        return None
    return (await db.execute(select(FormVersion.schema).where(
        FormVersion.tenant_id == tenant_id, FormVersion.id == form.published_version_id))).scalar_one_or_none()


# ── Views ─────────────────────────────────────────────────────────────────────────

def _methods(values: list[str]) -> list[str]:
    return [m for m in API_METHODS if m in values]


def token_status(token: ApiToken) -> str:
    return T.token_status_of(token.revoked_at, token.expires_at)


def can_call(token: ApiToken, endpoint: ApiEndpoint) -> bool:
    return any(T.scope_allows(token.scopes, str(endpoint.id), str(endpoint.service_id), m) for m in endpoint.methods)


def callers(store: Store) -> list[ApiToken]:
    """Tokens that can call anything: not webhook tokens, not revoked or expired."""
    return [t for t in store.tokens if t.kind != "webhook" and token_status(t) not in ("revoked", "expired")]


def reach_of(token: ApiToken, endpoint: ApiEndpoint) -> str:
    return T.token_reach(token.scopes, str(endpoint.id), str(endpoint.service_id))


def rule_scope(rule: ApiAccessRule) -> tuple[str, str | None]:
    return rule.scope_type, str(rule.scope_id) if rule.scope_id else None


def rules_on(store: Store, endpoint: ApiEndpoint) -> list[ApiAccessRule]:
    return A.rules_for(store.rules, str(endpoint.id), str(endpoint.service_id), rule_scope)


def service_view(store: Store, service: ApiService) -> dict[str, Any]:
    endpoints = [e for e in store.endpoints if e.service_id == service.id]
    return {
        "id": str(service.id), "name": service.name, "description": service.description, "status": service.status,
        "allowed_origins": list(service.allowed_origins or []), "endpoints_count": len(endpoints),
        "methods": [m for m in API_METHODS if any(e.status == "active" and m in e.methods for e in endpoints)],
        "created_by": store.by(service.created_by), "created_at": iso(service.created_at), "updated_at": iso(service.updated_at),
        **usage(),
    }


def endpoint_view(store: Store, endpoint: ApiEndpoint) -> dict[str, Any]:
    service = store.service(endpoint.service_id)
    form = store.forms.get(endpoint.form_id)
    writes = any(m in ("POST", "PUT") for m in endpoint.methods)
    api_key = store.settings.api_key if store.settings else ""
    return {
        "id": str(endpoint.id), "name": endpoint.name, "description": endpoint.description,
        "service": {"id": str(endpoint.service_id), "name": service.name if service else "",
                    "status": service.status if service else "disabled"},
        "form": {"id": str(endpoint.form_id), "name": form.name if form else "",
                 "status": "archived" if form is None or form.deleted else form.status},
        "version": endpoint.version, "methods": _methods(endpoint.methods), "status": endpoint.status,
        "url": endpoint_url(api_key, endpoint.name),
        "fields_accepted": sum(1 for f in endpoint.fields if f.get("accept")) if writes else 0,
        "fields_returned": sum(1 for f in endpoint.fields if f.get("returned")) if "GET" in endpoint.methods else 0,
        "required_headers": [h["name"] for h in endpoint.headers or []],
        "created_at": iso(endpoint.created_at), "updated_at": iso(endpoint.updated_at),
        **usage(),
    }


def endpoint_setup(store: Store, endpoint: ApiEndpoint) -> dict[str, Any]:
    """How far the endpoint is set up (guided setup, F13 M7)."""
    form = store.forms.get(endpoint.form_id)
    service = store.service(endpoint.service_id)
    reachable = [t for t in callers(store) if can_call(t, endpoint)]

    def count(mode: str, everything: bool) -> int:
        return sum(1 for t in reachable if t.mode == mode and (reach_of(t, endpoint) == "all") == everything)

    return {
        "service_active": bool(service and service.status == "active"),
        "form_published": bool(form and form.status == "published"),
        "form_api": bool(form) and "api" in form.channels,  # type: ignore[union-attr]
        "tokens_live": count("live", False), "tokens_test": count("test", False),
        "tokens_all_live": count("live", True), "tokens_all_test": count("test", True),
        "signing_tokens": sum(1 for t in reachable if t.signing),
        "rules": sum(1 for r in rules_on(store, endpoint) if r.enabled),
        "live": endpoint.status == "active",
    }


async def endpoint_detail(db: AsyncSession, store: Store, endpoint: ApiEndpoint) -> dict[str, Any]:
    from app.core.security.fernet_tokens import decrypt_secret

    form = store.forms.get(endpoint.form_id)
    schema = await schema_of(db, store.tenant_id, form, endpoint.version) if form else None
    headers = []
    for h in endpoint.headers or []:
        value = decrypt_secret(h["value_enc"]) if h.get("value_enc") else ""
        headers.append({"name": h["name"], "preview": T.mask_value(value), "value": value})
    return {
        **endpoint_view(store, endpoint),
        "fields": endpoint_fields_of(schema, endpoint.fields) if schema else [],
        "page_size": endpoint.page_size, "headers": headers, "versions": list(form.versions) if form else [],
        "setup": endpoint_setup(store, endpoint),
    }


def token_view(store: Store, token: ApiToken) -> dict[str, Any]:
    live_services = {str(s.id): s.name for s in store.services}
    live_endpoints = {str(e.id): e.name for e in store.endpoints}
    scopes = token.scopes
    rotating = token.rotating_until if token.rotating_until and token.rotating_until > datetime.now(UTC) else None
    return {
        "id": str(token.id), "name": token.name, "kind": token.kind, "mode": token.mode, "status": token_status(token),
        "preview": token.client_id if token.kind == "client" else token.preview, "client_id": token.client_id,
        "lifetime_minutes": token.lifetime_minutes, "signing": token.signing,
        "scopes": {"services": list(scopes["services"]), "endpoints": list(scopes["endpoints"]),
                   "methods": list(scopes["methods"])},
        "scope_names": {"services": [live_services[i] for i in scopes["services"] if i in live_services],
                        "endpoints": [live_endpoints[i] for i in scopes["endpoints"] if i in live_endpoints]},
        "expires_at": iso(token.expires_at), "rotating_until": iso(rotating), "last_used_at": iso(token.last_used_at),
        "created_by": store.by(token.created_by), "created_at": iso(token.created_at), "revoked_at": iso(token.revoked_at),
        "viewable": bool(token.secret_enc) and token.revoked_at is None,
        # Deleted services or endpoints still in its scope: kept (dropping them would widen the token), shown as such
        "scope_gone": sum(1 for i in scopes["services"] if i not in live_services)
        + sum(1 for i in scopes["endpoints"] if i not in live_endpoints),
        **usage(iso(token.last_used_at)),
    }


def rule_view(store: Store, rule: ApiAccessRule) -> dict[str, Any]:
    name = None
    if rule.scope_type == "service":
        found = store.service(rule.scope_id)
        name = found.name if found else None
    elif rule.scope_type == "endpoint":
        found_e = store.endpoint(rule.scope_id)
        name = found_e.name if found_e else None
    return {
        "id": str(rule.id), "action": rule.action, "kind": rule.kind, "values": list(rule.values),
        "scope": {"type": rule.scope_type, "id": str(rule.scope_id) if rule.scope_id else None, "name": name},
        "note": rule.note, "enabled": rule.enabled,
        # TODO(B10 step 2): hits from api_rule_hits_daily
        "hits_30d": 0, "daily": thirty_days(), "last_hit_at": iso(rule.last_hit_at),
        "created_by": store.by(rule.created_by), "created_at": iso(rule.created_at), "updated_at": iso(rule.updated_at),
    }



# ── Every new workspace (DATABASE-DESIGN → Seeded default data: `api_settings` with a new API key) ──────────

def _register_seeder() -> None:
    from app.modules.tenants.workspace import NewWorkspace, register_seeder

    async def seed_api_settings(session: AsyncSession, workspace: NewWorkspace) -> None:
        await ensure_settings(session, workspace.tenant_id, workspace.organisation_id)

    register_seeder(seed_api_settings)


_register_seeder()

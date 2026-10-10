"""4. Tenant: the host decides the context, the subdomain decides the workspace (01-ARCHITECTURE, Subdomain flow).

`resolve_host_context` is a line-by-line port of the frontend's shared/utils/tenant/host.ts
(parity: tests/parity/test_tenant_host.py runs the same cases as test/tenant/host.test.ts).

The middleware resolves `{sub}.formalie.*` to a workspace through the tenant directory (L1 → Redis → DB via
`platform.resolve_tenant`). An unknown or malformed workspace host answers FRM-TEN-1001. A suspended workspace
is still resolved, so its public profile can say so; `require_tenant` refuses it with FRM-TEN-1002, like the
mock's requireTenant(). The token/subdomain match (FRM-TEN-1003) is checked by the auth dependency (B1).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.config import Settings
from app.core.context import TenantInfo, get_context
from app.core.errors.exceptions import FrmError
from app.core.middleware.asgi import ASGIApp, Receive, Scope, Send, header, route_path, send_error

log = logging.getLogger("formalie.tenant")

RESERVED_SUBDOMAINS: tuple[str, ...] = (
    "www", "manage", "api", "forms", "app", "admin", "mail", "static", "cdn", "docs", "status", "help",
    "support", "blog", "s", "auth", "login", "billing", "dev", "staging", "test",
)
_SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

DEV_TENANT_HEADER = "x-formalie-dev-tenant"


@dataclass(frozen=True, slots=True)
class HostContext:
    kind: Literal["manage", "tenant", "custom", "forms", "invalid"]
    host: str
    reason: str | None = None  # manage: manage | root | local; invalid: reserved | nested | malformed
    subdomain: str | None = None


def normalise_host(raw_host: str) -> str:
    """Lower-cases, strips port, IPv6 brackets and a trailing dot."""
    host = raw_host.strip().lower()
    if host.startswith("["):
        host = host[1:host.find("]")]
    elif len(host.split(":")) == 2:
        host = host.split(":")[0]
    return re.sub(r"\.$", "", host)


def _is_ip_address(host: str) -> bool:
    return bool(_IPV4.match(host)) or ":" in host


def is_valid_subdomain(value: str) -> bool:
    return bool(_SUBDOMAIN_PATTERN.match(value)) and value not in RESERVED_SUBDOMAINS


def _classify_subdomain(host: str, sub: str, manage_subdomain: str) -> HostContext:
    if "." in sub:
        return HostContext("invalid", host, reason="nested")
    if sub == manage_subdomain:
        return HostContext("manage", host, reason="manage")
    if sub == "www":
        return HostContext("manage", host, reason="root")
    if sub == "forms":
        return HostContext("forms", host)
    if sub in RESERVED_SUBDOMAINS:
        return HostContext("invalid", host, reason="reserved")
    if not _SUBDOMAIN_PATTERN.match(sub):
        return HostContext("invalid", host, reason="malformed")
    return HostContext("tenant", host, subdomain=sub)


def resolve_host_context(
    raw_host: str, *, root_domain: str, manage_subdomain: str, tenant_override: str | None = None
) -> HostContext:
    host = normalise_host(raw_host)
    root = root_domain.lower()
    is_local = host == "localhost" or _is_ip_address(host)

    if is_local:
        override = (tenant_override or "").strip().lower()
        if override:
            return _classify_subdomain(host, override, manage_subdomain)
        return HostContext("manage", host, reason="local")

    if host == root:
        return HostContext("manage", host, reason="root")

    for suffix in (f".{root}", ".localhost"):
        if host.endswith(suffix):
            return _classify_subdomain(host, host[: -len(suffix)], manage_subdomain)

    return HostContext("custom", host)


class TenantResolver(Protocol):
    async def by_subdomain(self, subdomain: str) -> TenantInfo | None: ...
    async def by_domain(self, domain: str) -> TenantInfo | None: ...



class TenantMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings, resolver: TenantResolver) -> None:
        self.app = app
        self.settings = settings
        self.resolver = resolver
        prefix = settings.api_prefix
        # Routes that answer on any host, workspace or not.
        self.host_free = (f"{prefix}/health",)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = route_path(scope)
        if scope["type"] != "http" or not path.startswith(self.settings.api_prefix):
            await self.app(scope, receive, send)
            return
        ctx = get_context()
        raw_host = (ctx.host if ctx else None) or header(scope, "host") or ""
        override = header(scope, DEV_TENANT_HEADER) if self.settings.is_development else None
        context = resolve_host_context(
            raw_host,
            root_domain=self.settings.root_domain,
            manage_subdomain=self.settings.manage_subdomain,
            tenant_override=override,
        )
        tenant: TenantInfo | None = None
        try:
            if context.kind == "tenant" and context.subdomain:
                tenant = await self.resolver.by_subdomain(context.subdomain)
            elif context.kind == "custom":
                tenant = await self.resolver.by_domain(context.host)
        except Exception:
            log.exception("FRM-GEN-5003 tenant directory unavailable", extra={"error_code": "FRM-GEN-5003"})
            await send_error(send, "FRM-GEN-5003")
            return

        if ctx is not None:
            ctx.host_kind = context.kind
            ctx.tenant = tenant
            ctx.extra["host_context"] = context

        needs_workspace = context.kind in ("tenant", "custom", "invalid")
        if needs_workspace and tenant is None and not path.startswith(self.host_free):
            log.info("FRM-TEN-1001 unknown workspace host", extra={"error_code": "FRM-TEN-1001", "host": context.host,
                                                                    "host_kind": context.kind, "reason": context.reason})
            await send_error(send, "FRM-TEN-1001")
            return
        await self.app(scope, receive, send)


def current_host_context() -> HostContext | None:
    ctx = get_context()
    value = ctx.extra.get("host_context") if ctx else None
    return value if isinstance(value, HostContext) else None


def require_tenant() -> TenantInfo:
    """FastAPI dependency: the active workspace of this host, or the right FRM-TEN error (mock: requireTenant)."""
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    if tenant is None:
        raise FrmError("FRM-TEN-1001")
    if tenant.status == "suspended":
        raise FrmError("FRM-TEN-1002")
    return tenant


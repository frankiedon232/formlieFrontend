"""Per-request context shared by middleware, logging, the DB session and services (contextvars, safe with asyncio)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass(slots=True)
class TenantInfo:
    """A workspace as `platform.resolve_tenant()` returns it: public fields only."""

    id: uuid.UUID
    subdomain: str
    name: str
    status: str  # active, suspended, read_only, closing
    organisation_id: uuid.UUID


@dataclass(slots=True)
class RequestContext:
    trace_id: str
    started_at: float
    client_ip: str | None = None
    user_agent: str | None = None
    host: str | None = None
    host_kind: str | None = None  # manage, tenant, forms, custom, invalid
    tenant: TenantInfo | None = None
    user_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    error_code: str | None = None
    rate_limited: bool = False
    extra: dict[str, object] = field(default_factory=dict)


_current: ContextVar[RequestContext | None] = ContextVar("formalie_request_context", default=None)


def set_context(ctx: RequestContext) -> object:
    return _current.set(ctx)


def reset_context(token: object) -> None:
    _current.reset(token)  # type: ignore[arg-type]


def get_context() -> RequestContext | None:
    return _current.get()


def current_trace_id() -> str | None:
    ctx = _current.get()
    return ctx.trace_id if ctx else None

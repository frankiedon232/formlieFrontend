"""Events for the platform admin's analytics (PLATFORM-ADMIN-INTEGRATION §4), through the transactional outbox.

`emit()` adds an event in the caller's transaction with the request's context (where, which device, which plan,
from where: portal, public, api or worker); app/core/events/wire.py strips anything personal on the way out.

Most events come from the audit trail: `after_audit()` (called by app.modules.audit.service.record for every entry)
turns the actions below into platform events, so every sign-in, invitation or form change is counted exactly where
it is audited. The rest are emitted where they happen: tenant.signed_up (sign-up), response.created (public filling
and the API service), export.completed, destination.failed, webhook.failed, api.called, tenant.suspended and
tenant.closed (the internal admin API).
"""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_context
from app.core.events.outbox import record_event
from app.core.logging.geo import get_geo

log = logging.getLogger("formalie.platform.events")

# audit action → (platform event, the resource id's property name or None)
FROM_AUDIT: dict[str, tuple[str, str | None]] = {
    "auth.login.succeeded": ("auth.signed_in", None),
    "auth.login.failed": ("auth.sign_in_failed", None),
    "auth.login.blocked": ("auth.sign_in_failed", None),
    "auth.logout": ("auth.signed_out", None),
    "workspace.setup_completed": ("tenant.setup_completed", None),
    "users.invited": ("user.invited", "user_id"),
    "users.profile_created": ("user.invited", "user_id"),  # a profile made by an admin, with its activation link
    "users.joined": ("user.joined", "user_id"),
    "users.approved": ("user.approved", "user_id"),
    "users.disabled": ("user.disabled", "user_id"),
    "forms.created": ("form.created", "form_id"),
    "forms.published": ("form.published", "form_id"),
    "forms.closed": ("form.closed", "form_id"),
    "forms.deleted": ("form.deleted", "form_id"),
}
# audit action → the named feature it counts as used
FEATURES: dict[str, str] = {
    "ai.applied": "ai", "data.query_run": "query_editor", "data.row_inserted": "data_explorer",
    "data.row_updated": "data_explorer", "data.table_exported": "data_explorer", "forms.theme_created": "designer",
    "forms.page_design_created": "page_designer", "forms.template_created": "templates",
    "responses.exported": "response_exports", "api.endpoint_created": "api_service",
    "integrations.webhook_created": "webhooks", "data.destination_created": "destinations",
}
AUTH_EVENTS = {"auth.signed_in", "auth.sign_in_failed", "auth.signed_out"}


def _source(explicit: str | None) -> str:
    if explicit:
        return explicit
    ctx = get_context()
    if ctx is None or not ctx.path:
        return "worker"
    if ctx.host_kind == "forms" or "/public/" in ctx.path:
        return "public"
    return "portal"


async def _plan(db: AsyncSession, tenant_id: uuid.UUID | None) -> str | None:
    ctx = get_context()
    if ctx is not None and ctx.tenant is not None and ctx.tenant.id == tenant_id:
        return ctx.tenant.plan_id
    if tenant_id is None:
        return None
    try:
        async with db.begin_nested():
            return (await db.execute(text("SELECT plan_id FROM platform.tenant_profile()"))).scalar_one_or_none()
    except Exception:  # noqa: BLE001 (no workspace in context: the plan stays unknown)
        return None


async def emit(db: AsyncSession, type_: str, properties: dict[str, Any] | None = None, *,
               tenant_id: uuid.UUID | None = None, organisation_id: uuid.UUID | None = None,
               actor_id: uuid.UUID | None = None, source: str | None = None, language: str | None = None) -> uuid.UUID:
    """One event for the platform, in the caller's transaction."""
    ctx = get_context()
    if ctx is not None and ctx.tenant is not None:
        tenant_id = tenant_id or ctx.tenant.id
        organisation_id = organisation_id or ctx.tenant.organisation_id
    ip = ctx.client_ip if ctx else None
    geo = get_geo().lookup(ip) if ip and ip != "unknown" else {}
    from app.modules.audit.service import device_from

    device = device_from(ctx.user_agent if ctx else None) if ctx and ctx.user_agent else {}
    payload = {
        "_shape": "platform",
        "session_ref": str(ctx.session_id) if ctx and ctx.session_id else None,
        "source": _source(source),
        "country": geo.get("country"), "region": geo.get("region"), "city": geo.get("city"),
        "device": device.get("type"), "browser": device.get("browser"), "os": device.get("os"),
        "language": language,
        "plan": await _plan(db, tenant_id),
        "properties": properties or {},
    }
    return await record_event(db, type_, payload, tenant_id=tenant_id, organisation_id=organisation_id,
                              actor_id=actor_id)


async def after_audit(db: AsyncSession, *, action: str, actor: Any, tenant_id: uuid.UUID | None,
                      organisation_id: uuid.UUID | None, outcome: str, resource: dict[str, Any] | None,
                      metadata: dict[str, Any] | None, reason: str | None) -> None:
    """The platform event an audit entry stands for, if any. Never breaks the audited action (a savepoint)."""
    if action not in FROM_AUDIT and action not in FEATURES:
        return
    try:
        async with db.begin_nested():
            await _from_audit(db, action=action, actor=actor, tenant_id=tenant_id, organisation_id=organisation_id,
                              outcome=outcome, resource=resource, metadata=metadata, reason=reason)
    except Exception:  # noqa: BLE001
        log.exception("platform event from the audit trail failed", extra={"action": action})


async def _from_audit(db: AsyncSession, *, action: str, actor: Any, tenant_id: uuid.UUID | None,
                      organisation_id: uuid.UUID | None, outcome: str, resource: dict[str, Any] | None,
                      metadata: dict[str, Any] | None, reason: str | None) -> None:
    mapped = FROM_AUDIT.get(action)
    feature = FEATURES.get(action)
    support = actor.type == "platform_support"
    actor_id = actor.id if actor.type == "user" else None
    meta = metadata or {}
    if mapped is not None and not (support and mapped[0] in AUTH_EVENTS):
        name, id_key = mapped
        props: dict[str, Any] = {}
        if name == "auth.signed_in":
            props = {"method": meta.get("method"), "channel": meta.get("channel")}
        elif name == "auth.sign_in_failed":
            props = {"method": meta.get("method"), "reason": reason, "outcome": outcome}
        elif id_key and resource and resource.get("id") is not None:
            props = {id_key: str(resource["id"])}
        await emit(db, name, props, tenant_id=tenant_id, organisation_id=organisation_id, actor_id=actor_id)
        if name == "auth.signed_in" and meta.get("channel"):
            await emit(db, "auth.two_step_used", {"method": meta.get("method"), "channel": meta.get("channel")},
                       tenant_id=tenant_id, organisation_id=organisation_id, actor_id=actor_id)
    if feature is not None and outcome == "success":
        await emit(db, "feature.used", {"feature": feature}, tenant_id=tenant_id, organisation_id=organisation_id,
                   actor_id=actor_id)


def sampled(rate: float) -> bool:
    """api.called: one call in 1/rate is sent (rate 1: every call)."""
    return rate >= 1 or random.random() < max(0.0, rate)  # noqa: S311 (sampling, not security)

"""Recording the audit trail (port of the mock's core/audit.ts `recordAudit`, BACKEND-SPEC §12).

Every change and every sign-in event writes one row, in the same transaction as the change it records:
who (actor), what (action from the catalogue, resource, changes), outcome and severity, where (IP, city, country,
device) and the request id. B2 adds the list, filters, detail and export.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_context
from app.core.ids import uuid7
from app.core.logging.geo import get_geo
from app.modules.audit.events import AUDIT_EVENTS
from app.modules.audit.models import AuditLog

DEFAULT_SEVERITY = {"success": "info", "failure": "warning", "blocked": "critical"}


@dataclass(frozen=True, slots=True)
class Actor:
    type: str  # user, api_key, system, platform_support
    id: uuid.UUID | None
    name: str | None
    email: str | None
    # Formalie staff acting through the platform admin (B16): their id and name, and the approval behind the action
    staff_id: str | None = None
    staff_name: str | None = None
    approval_id: str | None = None

    @classmethod
    def user(cls, user: Any) -> Actor:
        """actorOf(): a person with an account (or Formalie support in a support session, B16)."""
        support = getattr(user, "support_staff", None)
        if support is not None:
            return cls.support(support["staff_id"], support["staff_name"], support.get("approval_id"))
        return cls("user", user.id, f"{user.first_name} {user.last_name}".strip(), user.email)

    @classmethod
    def support(cls, staff_id: str | None, staff_name: str | None, approval_id: str | None = None) -> Actor:
        """Formalie support (platform admin staff): shown as Formalie under the staff member's name."""
        name = f"Formalie support ({staff_name})" if staff_name else "Formalie support"
        return cls("platform_support", None, name, None, staff_id, staff_name, approval_id)

    @classmethod
    def anonymous(cls, email: str) -> Actor:
        """anonymousActor(): someone known only by the email they typed."""
        return cls("user", None, email, email)

    @classmethod
    def system(cls, name: str = "Formalie") -> Actor:
        return cls("system", None, name, None)


def device_from(user_agent: str | None) -> dict[str, str | None]:
    """deviceFrom(): browser, OS and device type, exactly as the mock reads them."""
    ua = user_agent or ""
    browser = ("Edge" if re.search(r"Edg/", ua) else "Opera" if re.search(r"OPR/", ua)
               else "Firefox" if re.search(r"Firefox/", ua) else "Chrome" if re.search(r"Chrome/", ua)
               else "Safari" if re.search(r"Safari/", ua) else None)
    os_ = ("iOS" if re.search(r"iPhone|iPad|iPod", ua) else "Android" if re.search(r"Android", ua)
           else "Windows" if re.search(r"Windows", ua) else "macOS" if re.search(r"Mac OS X", ua)
           else "Linux" if re.search(r"Linux", ua) else None)
    kind = "tablet" if re.search(r"iPad|Tablet", ua) else "mobile" if re.search(r"Mobi|iPhone|Android", ua) else "desktop"
    return {"type": kind if ua else "unknown", "browser": browser, "os": os_}


async def record(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    organisation_id: uuid.UUID | None,
    action: str,
    actor: Actor,
    outcome: str = "success",
    severity: str | None = None,
    resource: dict[str, Any] | None = None,
    changes: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    reason: str | None = None,
) -> uuid.UUID:
    if action not in AUDIT_EVENTS:
        raise ValueError(f"Unknown audit action {action}: add it to the frontend's audit/events.ts first")
    ctx = get_context()
    ip = ctx.client_ip if ctx else None
    geo = get_geo().lookup(ip, trusted_proxy=False) if ip else {}
    entry_id = uuid7()
    await session.execute(insert(AuditLog).values(
        id=entry_id,
        occurred_at=datetime.now(UTC),
        tenant_id=tenant_id,
        organisation_id=organisation_id,
        action=action,
        area=AUDIT_EVENTS[action]["area"],
        outcome=outcome,
        severity=severity or DEFAULT_SEVERITY[outcome],
        actor_type=actor.type,
        actor_id=actor.id,
        actor_name=actor.name,
        actor_email=actor.email,
        resource_type=(resource or {}).get("type"),
        resource_id=str((resource or {}).get("id")) if (resource or {}).get("id") is not None else None,
        resource_name=(resource or {}).get("name"),
        ip=ip if ip and ip != "unknown" else None,
        city=geo.get("city"),
        country=geo.get("country"),
        device=device_from(ctx.user_agent if ctx else None),
        changes=changes or [],
        metadata_={k: str(v) for k, v in (metadata or {}).items()},
        reason=reason,
        request_id=ctx.trace_id if ctx else None,
        staff_id=actor.staff_id,
        staff_name=actor.staff_name,
        approval_id=actor.approval_id,
    ))
    from app.modules.platform_bridge.events import after_audit  # the platform's analytics event, if any (B16)

    await after_audit(session, action=action, actor=actor, tenant_id=tenant_id, organisation_id=organisation_id,
                      outcome=outcome, resource=resource, metadata=metadata, reason=reason)
    return entry_id

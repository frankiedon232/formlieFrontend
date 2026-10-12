"""What an event looks like on `formalie.events` (PLATFORM-ADMIN-INTEGRATION §4), and what never leaves in one.

    { id, type, occurred_at, tenant_ref, organisation_ref, actor_ref, session_ref,
      source: portal | public | api | worker, country, region, city, device, browser, os, language, plan,
      properties, version, trace_id }

References are Formalie's own ids as text (the platform reads the same ids from the replica; it is a server, never
a browser). `properties` carry ids, counts, plans, timings and codes only: for the event types the platform listens
to, only the keys listed in PLATFORM_EVENTS pass; for every event, keys that hold personal data or content are
dropped, and so is any text that looks like an email address or an IP address. Never answers, names, emails,
passwords, tokens or full IPs.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

# Event type → the property keys it may carry (the platform's routing keys, §4)
PLATFORM_EVENTS: dict[str, frozenset[str]] = {k: frozenset(v) for k, v in {
    "auth.signed_in": ("method", "channel"),
    "auth.sign_in_failed": ("method", "reason", "outcome"),
    "auth.signed_out": ("method",),
    "auth.two_step_used": ("method", "channel"),
    "session.page_viewed": ("path_template",),
    "tenant.signed_up": ("plan", "method", "utm_source", "utm_medium", "utm_campaign", "referrer_host"),
    "tenant.setup_completed": (),
    "tenant.suspended": ("previous_status", "status"),
    "tenant.closed": ("previous_status", "close_at"),
    "user.invited": ("user_id", "role"),
    "user.joined": ("user_id", "via"),
    "user.approved": ("user_id",),
    "user.disabled": ("user_id",),
    "form.created": ("form_id",),
    "form.published": ("form_id", "version"),
    "form.closed": ("form_id",),
    "form.deleted": ("form_id",),
    "response.created": ("form_id", "response_id", "channel", "submitted_at", "duration_seconds"),
    "export.completed": ("export_id", "kind", "format", "rows", "bytes"),
    "destination.failed": ("destination_id", "failed", "sent"),
    "webhook.failed": ("webhook_id", "delivery_id", "attempts", "status_code", "event"),
    "api.called": ("endpoint_id", "service_id", "method", "status", "duration_ms", "token_mode", "sample_rate"),
    "feature.used": ("feature",),
}.items()}

# Never in any event, whatever its type
DENIED_KEYS = frozenset({
    "email", "emails", "name", "first_name", "last_name", "full_name", "phone", "ip", "ip_address", "address",
    "data", "answers", "answer", "values", "password", "token", "secret", "code", "otp", "body", "text", "html",
    "subject", "message", "comment", "note", "prompt", "result", "user_agent",
})
SOURCES = ("portal", "public", "api", "worker")
CONTEXT_KEYS = ("session_ref", "source", "country", "region", "city", "device", "browser", "os", "language", "plan")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MAX_TEXT = 200


def _looks_personal(value: str) -> bool:
    if _EMAIL.search(value):
        return True
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def _clean_value(value: Any) -> Any:
    """Plain values only: text (short, never an email or an IP), numbers, booleans, null; lists of those."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return None if _looks_personal(value) else value[:MAX_TEXT]
    if isinstance(value, list | tuple):
        return [v for v in (_clean_value(item) for item in value[:50]) if v is not None and not isinstance(v, list)]
    return None  # objects never pass: they can hide anything


def clean_properties(type_: str, properties: dict[str, Any] | None) -> dict[str, Any]:
    allowed = PLATFORM_EVENTS.get(type_)
    out: dict[str, Any] = {}
    for key, value in (properties or {}).items():
        key = str(key)
        if key.lower() in DENIED_KEYS or (allowed is not None and key not in allowed):
            continue
        cleaned = _clean_value(value)
        if cleaned is not None:
            out[key] = cleaned
    return out


def _ref(value: Any) -> str | None:
    return str(value) if value else None


def to_wire(event: Any) -> dict[str, Any]:
    """An EventEnvelope as the message body. `payload` is either the platform shape stored by
    app.modules.platform_bridge.events.emit() (`_shape: "platform"`), or an older plain payload (its keys become
    the properties)."""
    payload = dict(event.payload or {})
    shaped = payload.pop("_shape", None) == "platform"
    context = {key: payload.get(key) for key in CONTEXT_KEYS} if shaped else {key: None for key in CONTEXT_KEYS}
    properties = payload.get("properties") if shaped else payload
    if context["source"] not in SOURCES:
        context["source"] = "worker"
    for key in ("country", "region", "city", "device", "browser", "os", "language", "plan", "session_ref"):
        value = context.get(key)
        context[key] = value[:MAX_TEXT] if isinstance(value, str) and not _looks_personal(value) else None
    return {
        "id": str(event.event_id),
        "type": event.type,
        "occurred_at": event.occurred_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "tenant_ref": _ref(event.tenant_id),
        "organisation_ref": _ref(event.organisation_id),
        "actor_ref": _ref(event.actor_id),
        **context,
        "properties": clean_properties(event.type, properties if isinstance(properties, dict) else {}),
        "version": event.version,
        "trace_id": event.trace_id,
    }

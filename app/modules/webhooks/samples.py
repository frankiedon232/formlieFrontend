"""The mock's sample webhooks (data/integrationStore.ts seed) for the seeded development workspaces only
(scripts/seed_dev.py): a CRM sync on the first two published forms, a data warehouse on every form that is failing
right now, and an old ticketing bridge switched off, each with its own webhook token and a month of made-up
deliveries (no bodies to send again: they are samples). Values stay international and neutral. Run once: skipped when
the workspace has ever had a webhook.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.api_service.traffic_samples import ensure_past_partitions, seed_of
from app.modules.forms.models import Form
from app.modules.webhooks.models import Webhook, WebhookDelivery
from app.modules.webhooks.rules import WEBHOOK_RETRY_MINUTES
from app.modules.webhooks.service import delivery_headers, dumps, iso, make_token, ref

SAMPLES = [
    ("CRM sync", "https://hooks.example.com/formalie/crm", ["response.created", "response.updated"], slice(0, 2), True, 0, 0.98),
    ("Data warehouse", "https://ingest.example.org/v2/events",
     ["response.created", "response.status_changed", "response.deleted"], None, True, 3, 0.82),
    ("Old ticketing bridge", "https://tickets.example.net/inbound", ["response.created"], slice(2, 3), False, 0, 0.9),
]
CODES = [500, 502, 503, 404, None]


async def seed_sample_webhooks(session: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID,
                               owner_id: uuid.UUID | None) -> int:
    """Inside the workspace's RLS context. Returns how many webhooks were added (0 when it already has some)."""
    if (await session.execute(select(Webhook.id).where(Webhook.tenant_id == tenant_id).limit(1))).first():
        return 0
    await ensure_past_partitions(session)
    forms = list((await session.execute(select(Form).where(
        Form.tenant_id == tenant_id, Form.deleted_at.is_(None), Form.status == "published").order_by(Form.created_at))).scalars())
    now = datetime.now(UTC)
    day = timedelta(days=1)
    rows: list[dict] = []
    for i, (name, url, events, picked, enabled, failing, rate) in enumerate(SAMPLES):
        created = now - (90 - i * 20) * day
        token, _ = await make_token(session, tenant_id, organisation_id, name, owner_id)
        hook = Webhook(tenant_id=tenant_id, organisation_id=organisation_id, name=name, url=url, events=events,
                       form_ids=[str(f.id) for f in forms[picked]] if picked else [], enabled=enabled,
                       paused_reason=None if enabled else "manual", token_id=token.id, consecutive_failures=failing,
                       created_by=owner_id, updated_by=owner_id, created_at=created, updated_at=created + day)
        session.add(hook)
        await session.flush()
        key = str(hook.id)
        for back in range(29, -1, -1):
            if not enabled and back < 12:
                continue
            for n in range(seed_of(f"{key}:{back}") % 7):
                at = now - back * day - timedelta(milliseconds=seed_of(f"{key}:{back}:{n}") % (86_400_000 - 60_000))
                ok = n >= failing if back == 0 and failing else (seed_of(f"{key}:{back}:{n}:ok") % 100) / 100 < rate
                tries = (1 + (1 if seed_of(f"{key}:{back}:{n}:t") % 6 == 0 else 0)) if ok else len(WEBHOOK_RETRY_MINUTES) + 1
                event = events[seed_of(f"{key}:{back}:{n}:e") % len(events)]
                form = forms[seed_of(f"{key}:{back}:{n}:f") % len(forms)] if forms else None
                rows.append(_delivery(hook, event, form, at, ok, tries, back == 0 and not ok, now))
    if rows:
        await session.execute(insert(WebhookDelivery), rows)
    await session.flush()
    return len(SAMPLES)


def _delivery(hook: Webhook, event: str, form: Form | None, at: datetime, ok: bool, tries: int, retrying: bool,
              now: datetime) -> dict:
    delivery_id = uuid7()
    fail_code = CODES[seed_of(f"{delivery_id}:c") % len(CODES)]
    shown = min(tries, 2) if retrying else tries
    history = []
    for i in range(shown):
        good = ok and i == tries - 1
        code = 200 if good else fail_code
        waited = sum(WEBHOOK_RETRY_MINUTES[:i])
        history.append({"at": iso(at + timedelta(minutes=waited)), "status_code": code,
                        "duration_ms": 80 + seed_of(f"{delivery_id}:{i}") % 700,
                        "error": None if good else ("timeout" if code is None else f"HTTP {code}")})
    body = dumps({"id": f"evt_{ref(delivery_id)}", "type": event, "created_at": iso(at), "test": False,
                  "data": {"form": {"id": ref(form.id), "name": form.name} if form else None,
                           "response": {"id": ref(uuid.uuid4()), "status": "new"}}})
    last_at = datetime.fromisoformat(history[-1]["at"].replace("Z", "+00:00"))
    return {
        "id": delivery_id, "tenant_id": hook.tenant_id, "organisation_id": hook.organisation_id, "at": at,
        "webhook_id": hook.id, "event": event, "test": False, "form_id": form.id if form else None, "response_id": None,
        "status": "delivered" if ok else "retrying" if retrying else "failed", "attempts": len(history),
        "status_code": history[-1]["status_code"], "duration_ms": history[-1]["duration_ms"],
        "next_retry_at": max(now + timedelta(minutes=10), last_at + timedelta(minutes=WEBHOOK_RETRY_MINUTES[len(history) - 1]))
        if retrying else None,
        "body_enc": None, "logged_body": body, "request_headers": delivery_headers(delivery_id, "formalie_hook_live_…"),
        "response": {"headers": {"content-type": "application/json" if ok else "text/html"},
                     "body": '{"received":true}' if ok else None},
        "history": history,
    }

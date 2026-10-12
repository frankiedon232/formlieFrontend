"""Sending webhook deliveries (queue `webhooks`; mock: data/integrationStore.ts attempt()).

One try: the webhook token from Tokens & headers as `Authorization: Bearer` (owner 2026-10-06), the delivery id as
`Formalie-Key`, a POST with the JSON body and 10 seconds to answer. Anything but 2xx is retried after 1, 5, 15, 60 and
360 minutes (the sweep, every 30 seconds, picks up retries whose time has come and first tries the worker never got),
then failed for good. After 20 failed deliveries in a row the webhook pauses itself (`webhook_failing` notification,
`integrations.webhook_paused` in the audit trail); nothing is lost, deliveries can be sent again. Without a usable
token (deleted, revoked, expired) nothing is sent and the try fails with `token`.

Outgoing calls never reach Formalie itself or private networks: the address is checked like the portal checks it, its
name is resolved here and every address it resolves to is checked, and the call goes to the checked address (the name
still names the host and the certificate). WEBHOOKS_ALLOW_LOCAL lets http://localhost through while developing;
production refuses it whatever the setting.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select, text, update

from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.security.fernet_tokens import decrypt_secret
from app.modules.api_service import tokens as T
from app.modules.api_service.access import ip_in_cidr
from app.modules.api_service.models import ApiToken
from app.modules.webhooks.models import Webhook, WebhookDelivery
from app.modules.webhooks.rules import (
    PRIVATE, WEBHOOK_AUTO_PAUSE, WEBHOOK_RETRY_MINUTES, WEBHOOK_TIMEOUT_MS, check_webhook_url, webhook_url_parts,
)
from app.modules.webhooks.service import NO_TOKEN, delivery_headers
from app.workers.celery_app import celery_app

log = logging.getLogger("formalie.webhooks")

LEASE = timedelta(seconds=120)  # a worker trying a delivery has it this long
SWEEP_ROWS = 500
KEPT_HEADERS = ("content-type", "content-length", "server", "date")
WEBHOOKS_LINK = "/api-service/webhooks"

# Tests swap these in; never set in the running app.
transport: httpx.AsyncBaseTransport | None = None
resolver: Any = None


def now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def allow_local() -> bool:
    settings = get_settings()
    return settings.webhooks_allow_local and not settings.is_production


def _blocked(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True
    return any(ip_in_cidr(str(ip), network) for network in PRIVATE)


async def _resolve(host: str, port: int) -> list[str]:
    if resolver is not None:
        return list(await resolver(host, port))
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


async def send(url: str, headers: dict[str, str], body: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """POSTs the body → (the try for the history, the receiver's answer or None). Never raises."""
    started = now()

    def failed(error: str) -> tuple[dict[str, Any], None]:
        took = int((now() - started).total_seconds() * 1000)
        return {"at": _iso(started), "status_code": None, "duration_ms": took, "error": error}, None

    local = allow_local()
    parts = webhook_url_parts(url.strip())
    if parts is None or check_webhook_url(url, allow_local=local):
        return failed("refused")
    host = str(parts["host"]).strip("[]").rstrip(".")
    scheme = str(parts["scheme"])
    port = int(parts["port"] or (443 if scheme == "https" else 80))  # type: ignore[call-overload]
    if not host:
        return failed("refused")
    try:
        addresses = await _resolve(host, port)
    except (socket.gaierror, OSError):
        return failed("dns")
    if not addresses:
        return failed("dns")
    if not local and any(_blocked(a) for a in addresses):
        return failed("refused")
    target = httpx.URL(url.strip())
    pinned = target.copy_with(host=addresses[0])
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_MS / 1000, follow_redirects=False, transport=transport,
                                     trust_env=False) as http:
            answer = await http.post(pinned, content=body.encode("utf-8"),
                                     headers={**headers, "Host": target.netloc.decode("ascii")},
                                     extensions={"sni_hostname": host})
            text_ = answer.text[:2000]
    except httpx.TimeoutException:
        return failed("timeout")
    except httpx.ConnectError as error:
        reason = str(error).upper()
        return failed("tls" if "SSL" in reason or "CERTIFICATE" in reason or "TLS" in reason else "refused")
    except (httpx.HTTPError, UnicodeError, ValueError):
        return failed("failed")
    took = int((now() - started).total_seconds() * 1000)
    good = 200 <= answer.status_code < 300
    entry = {"at": _iso(started), "status_code": answer.status_code, "duration_ms": took,
             "error": None if good else f"HTTP {answer.status_code}"}
    kept = {k: v for k, v in answer.headers.items() if k.lower() in KEPT_HEADERS}
    return entry, {"headers": kept, "body": text_ or None}


async def _claim(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_id: uuid.UUID, force: bool) -> bool:
    """This worker has the delivery for LEASE (unless another has it, or its next try isn't due and not forced)."""
    due = "" if force else " AND (next_retry_at IS NULL OR next_retry_at <= now())"
    async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        got = (await db.execute(text(
            "UPDATE webhook_deliveries SET claimed_until = :until, updated_at = now() WHERE tenant_id = :t AND id = :id "
            f"AND status = 'retrying' AND (claimed_until IS NULL OR claimed_until < now()){due} RETURNING id"),
            {"t": tenant_id, "id": delivery_id, "until": now() + LEASE})).first()
    return got is not None


async def attempt(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_id: uuid.UUID,
                  workspace: dict[str, str] | None = None, *, force: bool = False) -> bool:
    """One try of a delivery that is waiting (`retrying`). Returns whether a try was made."""
    if not await _claim(tenant_id, organisation_id, delivery_id, force):
        return False
    scope = {"tenant_id": tenant_id, "organisation_id": organisation_id}
    async with db_session("write", **scope) as db:
        delivery = (await db.execute(select(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id == delivery_id))).scalars().first()
        if delivery is None:
            return False
        hook = await db.get(Webhook, delivery.webhook_id)
        if hook is None or hook.deleted_at is not None or delivery.body_enc is None:
            # Its webhook is gone: nothing more to send
            await db.execute(update(WebhookDelivery).where(
                WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id == delivery_id).values(
                status="failed", next_retry_at=None, claimed_until=None))
            return False
        token = await db.get(ApiToken, hook.token_id) if hook.token_id else None
        token = token if token is not None and token.deleted_at is None else None
        status = T.token_status_of(token.revoked_at, token.expires_at) if token else None
        kept = decrypt_secret(token.secret_enc) if token and token.secret_enc else None
        secret = kept if status in ("active", "expiring") else None
        body, url, test = decrypt_secret(delivery.body_enc), hook.url, delivery.test
        shown = ((T.secret_preview(kept) if kept else "") or token.preview) if token else NO_TOKEN
    headers = delivery_headers(delivery_id, secret or "")
    if secret is None:
        entry: dict[str, Any] = {"at": _iso(now()), "status_code": None, "duration_ms": 0, "error": "token"}
        answer = None
    else:
        entry, answer = await send(url, headers, body)
    await _record(tenant_id, organisation_id, delivery_id, hook.id, entry, answer,
                  {**headers, "Authorization": f"Bearer {shown}"}, test, workspace)
    return True


async def _record(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_id: uuid.UUID, webhook_id: uuid.UUID,
                  entry: dict[str, Any], answer: dict[str, Any] | None, shown_headers: dict[str, str], test: bool,
                  workspace: dict[str, str] | None) -> None:
    from app.modules.audit.service import Actor, record
    from app.modules.notifications.service import notify

    async with db_session("write", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        delivery = (await db.execute(select(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id == delivery_id))).scalars().first()
        hook = (await db.execute(select(Webhook).where(Webhook.tenant_id == tenant_id, Webhook.id == webhook_id)
                                 .with_for_update())).scalar_one()
        if delivery is None:
            return
        history = [*(delivery.history or []), entry]
        good = entry["status_code"] is not None and 200 <= entry["status_code"] < 300
        at = now()
        values: dict[str, Any] = {"history": history, "attempts": len(history), "status_code": entry["status_code"],
                                  "duration_ms": entry["duration_ms"], "response": answer, "request_headers": shown_headers,
                                  "claimed_until": None, "updated_at": at}
        if good:
            values.update(status="delivered", next_retry_at=None)
            if not test:
                hook.consecutive_failures = 0
        elif not test and len(history) <= len(WEBHOOK_RETRY_MINUTES):
            values.update(status="retrying", next_retry_at=at + timedelta(minutes=WEBHOOK_RETRY_MINUTES[len(history) - 1]))
        else:
            values.update(status="failed", next_retry_at=None)
        await db.execute(update(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id == delivery_id).values(**values))
        if not good and not test:
            hook.consecutive_failures += 1
            if hook.enabled and hook.consecutive_failures >= WEBHOOK_AUTO_PAUSE:
                hook.enabled, hook.paused_reason = False, "failures"
                await notify(db, tenant_id, organisation_id, workspace or {"name": "", "subdomain": ""},
                             "webhook_failing", {"name": hook.name}, WEBHOOKS_LINK)
                await record(db, tenant_id=tenant_id, organisation_id=organisation_id, action="integrations.webhook_paused",
                             actor=Actor.system(), resource={"type": "webhook", "id": str(hook.id), "name": hook.name},
                             metadata={"reason": f"{WEBHOOK_AUTO_PAUSE} failed deliveries in a row"})
        await db.flush()


# ── The sweep ───────────────────────────────────────────────────────────────────

async def sweep() -> int:
    """Retries whose time has come and first tries the worker never got, each in its own workspace."""
    async with db_session("read") as db:
        due = (await db.execute(text("SELECT tenant_id, organisation_id, subdomain, name, delivery_id "
                                     "FROM platform.webhook_deliveries_due(:n)"), {"n": SWEEP_ROWS})).all()
    for tenant_id, organisation_id, subdomain, name, delivery_id in due:
        try:
            await attempt(tenant_id, organisation_id, delivery_id, {"name": name, "subdomain": subdomain})
        except Exception:  # noqa: BLE001 (one delivery never stops the others)
            log.exception("webhook delivery failed", extra={"delivery_id": str(delivery_id)})
    return len(due)


# ── Celery ──────────────────────────────────────────────────────────────────────

def _run(coroutine: Any) -> Any:
    from app.core.db.engines import dispose_engines

    async def wrapped() -> Any:
        try:
            return await coroutine
        finally:
            await dispose_engines()
    return asyncio.run(wrapped())


@celery_app.task(name="webhooks.deliver", ignore_result=True, acks_late=True)
def deliver_task(tenant_id: str, organisation_id: str, delivery_id: str, workspace: dict[str, str] | None = None) -> None:
    _run(attempt(uuid.UUID(tenant_id), uuid.UUID(organisation_id), uuid.UUID(delivery_id), workspace))


@celery_app.task(name="webhooks.sweep", ignore_result=True)
def sweep_task() -> None:
    _run(sweep())


def dispatch_delivery(tenant_id: uuid.UUID, organisation_id: uuid.UUID, delivery_id: uuid.UUID,
                      workspace: dict[str, str]) -> None:
    """To the `webhooks` queue, after the change committed. Tests replace this."""
    deliver_task.apply_async(args=[str(tenant_id), str(organisation_id), str(delivery_id), workspace], queue="webhooks")

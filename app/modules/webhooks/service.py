"""Webhooks as the portal sees them (mock: data/integrationStore.ts): the views in the shapes of
shared/types/integrations.ts, and deliveries made from response events.

A response event (created, updated, status changed, deleted) becomes one delivery per switched-on webhook that listens
to it and to the form, in the same transaction as the change; the worker sends it right after the commit (queue
`webhooks`, tasks.py). The body names answers like the API endpoints (the form's endpoint's names, else names from
the labels; owner 2026-10-06) and is kept encrypted for retries and Send again; the log's copy has personal answers
masked.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import after_commit
from app.core.ids import uuid7
from app.core.security.fernet_tokens import encrypt_secret
from app.modules.api_service import tokens as T
from app.modules.api_service.endpoints import endpoint_fields_of
from app.modules.api_service.models import ApiEndpoint, ApiToken
from app.modules.api_service.traffic import PERSONAL_TYPES, days_back, day_start, iso, js_round, mask_answers
from app.modules.forms.models import Form
from app.modules.webhooks.models import Webhook, WebhookDelivery
from app.modules.webhooks.rules import webhook_status_of

DAY = timedelta(days=1)
USER_AGENT = "Formalie-Webhooks/1.0"
NO_TOKEN = "(none)"


def now() -> datetime:
    return datetime.now(UTC)


def ref(value: uuid.UUID | str) -> str:
    from app.core.security.refs import get_codec

    return get_codec().encode_id(str(value))


def dumps(value: Any) -> str:
    """JSON.stringify."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def delivery_headers(delivery_id: uuid.UUID, bearer: str) -> dict[str, str]:
    """The same headers as an API call (owner 2026-10-06): the token as Bearer, JSON, and the delivery id as the
    Formalie-Key (the same on every retry of a delivery, so a receiver can skip one it already has)."""
    return {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json",
            "Formalie-Key": f"dlv_{ref(delivery_id)}", "User-Agent": USER_AGENT}


def workspace_of_request() -> dict[str, str]:
    from app.core.context import get_context

    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    return {"name": tenant.name if tenant else "", "subdomain": tenant.subdomain if tenant else ""}


# ── Queueing ──────────────────────────────────────────────────────────────────────

def new_delivery(webhook: Webhook, *, event: str, test: bool, form_id: uuid.UUID | None, response_id: uuid.UUID | None,
                 body: dict[str, Any], personal: set[str] | frozenset[str], logged: str | None = None) -> WebhookDelivery:
    """A delivery waiting for its first try (status `retrying`, no try yet): `{ id: "evt_…", …body }`."""
    delivery_id = uuid7()
    sent = dumps({"id": f"evt_{ref(delivery_id)}", **body})
    return WebhookDelivery(
        id=delivery_id, tenant_id=webhook.tenant_id, organisation_id=webhook.organisation_id, at=now(),
        webhook_id=webhook.id, event=event, test=test, form_id=form_id, response_id=response_id, status="retrying",
        attempts=0, next_retry_at=None, body_enc=encrypt_secret(sent),
        logged_body=logged if logged is not None else dumps(mask_answers(json.loads(sent), personal)),
        request_headers={}, response=None, history=[])


def queue(db: AsyncSession, delivery: WebhookDelivery) -> None:
    """Sent by the worker once this transaction committed (the sweep picks up what was missed)."""
    from app.modules.webhooks import tasks

    tenant_id, organisation_id, delivery_id = delivery.tenant_id, delivery.organisation_id, delivery.id
    workspace = workspace_of_request()
    after_commit(db, lambda: tasks.dispatch_delivery(tenant_id, organisation_id, delivery_id, workspace))


async def listening(db: AsyncSession, tenant_id: uuid.UUID, event: str, form_id: uuid.UUID) -> list[Webhook]:
    hooks = (await db.execute(select(Webhook).where(
        Webhook.tenant_id == tenant_id, Webhook.deleted_at.is_(None), Webhook.enabled.is_(True))
        .order_by(Webhook.created_at))).scalars()
    return [h for h in hooks if event in h.events and (not h.form_ids or str(form_id) in h.form_ids)]


async def answer_names(db: AsyncSession, form: Form) -> tuple[dict[str, str], set[str]]:
    """Question key → API name (the form's endpoint's names, else from the labels), and the personal answers' names."""
    from app.modules.api_service.service import schema_of
    from app.modules.public.submit import all_fields

    schema = await schema_of(db, form.tenant_id, form, None)
    if not schema:
        return {}, set()
    endpoint = (await db.execute(select(ApiEndpoint).where(
        ApiEndpoint.tenant_id == form.tenant_id, ApiEndpoint.form_id == form.id, ApiEndpoint.deleted_at.is_(None))
        .order_by(ApiEndpoint.created_at).limit(1))).scalar_one_or_none()
    names = {f["key"]: f["name"] for f in endpoint_fields_of(schema, endpoint.fields if endpoint else None)}
    personal = {names.get(f["key"], f["key"]) for f in all_fields(schema) if f.get("type") in PERSONAL_TYPES}
    return names, personal


async def response_event(db: AsyncSession, event: str, form: Form, response: Any, previous_status: str | None = None) -> int:
    """Every switched-on webhook listening to this event and form gets a delivery. Never raises (a webhook never
    stops a response from being saved). Returns how many were queued."""
    import logging

    try:
        hooks = await listening(db, form.tenant_id, event, form.id)
        if not hooks:
            return 0
        async with db.begin_nested():  # a failure here never spoils the change itself
            return await _queue_event(db, hooks, event, form, response, previous_status)
    except Exception:  # noqa: BLE001
        logging.getLogger("formalie.webhooks").exception("webhook event failed", extra={"event": event})
        return 0


async def _queue_event(db: AsyncSession, hooks: list[Webhook], event: str, form: Form, response: Any,
                       previous_status: str | None) -> int:
    names, personal = await answer_names(db, form)
    part: dict[str, Any] = {"id": ref(response.id)}
    if event != "response.deleted":
        part.update(submitted_at=iso(response.submitted_at), status=response.status, channel=response.channel,
                    answers={names.get(k, k): v for k, v in (response.data or {}).items()})
    body: dict[str, Any] = {"type": event, "created_at": iso(now()), "test": False,
                            "data": {"form": {"id": ref(form.id), "name": form.name}, "response": part}}
    if previous_status:
        body["data"]["previous_status"] = previous_status
    for hook in hooks:
        delivery = new_delivery(hook, event=event, test=False, form_id=form.id, response_id=response.id, body=body,
                                personal=personal)
        db.add(delivery)
        await db.flush()
        queue(db, delivery)
    return len(hooks)


# ── Tokens ──────────────────────────────────────────────────────────────────────────

async def make_token(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, webhook_name: str,
                     by: uuid.UUID | None) -> tuple[ApiToken, str]:
    """A webhook token named after the webhook ("{name} · webhook", numbered when taken). Returns it and its secret."""
    taken = {n.lower() for n in (await db.execute(select(ApiToken.name).where(
        ApiToken.tenant_id == tenant_id, ApiToken.deleted_at.is_(None)))).scalars()}
    label, n = f"{webhook_name} · webhook", 2
    while label.lower() in taken:
        label, n = f"{webhook_name} · webhook {n}", n + 1
    secret = T.new_secret("webhook", "live")
    token = ApiToken(tenant_id=tenant_id, organisation_id=organisation_id, name=label[:80], kind="webhook", mode="live",
                     secret_hash=T.hash_secret(secret), secret_enc=encrypt_secret(secret), preview=T.secret_preview(secret),
                     signing=False, scopes={"services": [], "endpoints": [], "methods": []}, created_by=by, updated_by=by)
    db.add(token)
    await db.flush()
    return token, secret


# ── Views ───────────────────────────────────────────────────────────────────────────

@dataclass
class Stats:
    deliveries_30d: int = 0
    failed_30d: int = 0
    finished: int = 0
    delivered: int = 0
    avg_ms: int | None = None
    daily: dict[Any, int] = field(default_factory=dict)
    last: dict[str, Any] | None = None


async def stats_of(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, Stats]:
    """Per webhook: deliveries in the last 30 days (tests left out), failed, success, answer time, per day, the last."""
    since = now() - 30 * DAY
    first_day = day_start(days_back(30)[0])
    out: dict[uuid.UUID, Stats] = {}
    params = {"t": tenant_id, "since": since, "first": first_day}
    for wid, total, failed, finished, delivered in (await db.execute(text(
            "SELECT webhook_id, count(*), count(*) FILTER (WHERE status = 'failed'), "
            "count(*) FILTER (WHERE status <> 'retrying'), count(*) FILTER (WHERE status = 'delivered') "
            "FROM webhook_deliveries WHERE tenant_id = :t AND NOT test AND at >= :since GROUP BY 1"), params)).all():
        out.setdefault(wid, Stats()).__dict__.update(deliveries_30d=total, failed_30d=failed, finished=finished,
                                                      delivered=delivered)
    for wid, avg in (await db.execute(text(
            "SELECT d.webhook_id, avg((h->>'duration_ms')::numeric) FROM webhook_deliveries d, "
            "jsonb_array_elements(d.history) h WHERE d.tenant_id = :t AND NOT d.test AND d.at >= :since GROUP BY 1"),
            params)).all():
        out.setdefault(wid, Stats()).avg_ms = js_round(float(avg)) if avg is not None else None
    for wid, d, count in (await db.execute(text(
            "SELECT webhook_id, (at AT TIME ZONE 'UTC')::date, count(*) FROM webhook_deliveries "
            "WHERE tenant_id = :t AND NOT test AND at >= :first GROUP BY 1, 2"), params)).all():
        out.setdefault(wid, Stats()).daily[d] = count
    for wid, status, last in (await db.execute(text(
            "SELECT DISTINCT ON (webhook_id) webhook_id, status, history -> -1 FROM webhook_deliveries "
            "WHERE tenant_id = :t ORDER BY webhook_id, at DESC, id DESC"), params)).all():
        if last:
            out.setdefault(wid, Stats()).last = {"at": last["at"], "ok": status == "delivered",
                                                 "status_code": last.get("status_code")}
    return out


async def forms_named(db: AsyncSession, tenant_id: uuid.UUID, ids: set[str]) -> dict[str, str]:
    wanted = []
    for i in ids:
        try:
            wanted.append(uuid.UUID(i))
        except ValueError:
            continue
    if not wanted:
        return {}
    return {str(i): n for i, n in (await db.execute(select(Form.id, Form.name).where(
        Form.tenant_id == tenant_id, Form.id.in_(wanted)))).all()}


async def tokens_of(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, ApiToken]:
    return {t.id: t for t in (await db.execute(select(ApiToken).where(
        ApiToken.tenant_id == tenant_id, ApiToken.deleted_at.is_(None)))).scalars()}


@dataclass
class Views:
    """What the webhook views need, read once per request."""

    stats: dict[uuid.UUID, Stats]
    forms: dict[str, str]
    tokens: dict[uuid.UUID, ApiToken]
    names: Any

    @classmethod
    async def load(cls, db: AsyncSession, tenant_id: uuid.UUID, hooks: list[Webhook]) -> Views:
        from app.modules.forms.service import Names

        names = Names()
        await names.load(db, tenant_id)
        return cls(await stats_of(db, tenant_id), await forms_named(db, tenant_id, {f for h in hooks for f in h.form_ids}),
                   await tokens_of(db, tenant_id), names)


def token_ref(token: ApiToken | None) -> dict[str, Any] | None:
    if token is None:
        return None
    return {"id": str(token.id), "name": token.name, "preview": token.client_id if token.kind == "client" else token.preview,
            "status": T.token_status_of(token.revoked_at, token.expires_at)}


def webhook_view(views: Views, hook: Webhook) -> dict[str, Any]:
    """Webhook."""
    s = views.stats.get(hook.id, Stats())
    return {
        "id": str(hook.id), "name": hook.name, "url": hook.url, "events": list(hook.events),
        "forms": [{"id": f, "name": views.forms[f]} for f in hook.form_ids if views.forms.get(f)],
        "enabled": hook.enabled, "status": webhook_status_of(hook.enabled, hook.consecutive_failures),
        "paused_reason": None if hook.enabled else hook.paused_reason,
        "token": token_ref(views.tokens.get(hook.token_id) if hook.token_id else None),
        "deliveries_30d": s.deliveries_30d, "failed_30d": s.failed_30d,
        "success_rate": s.delivered / s.finished if s.finished else None, "avg_ms": s.avg_ms,
        "last_delivery": s.last, "consecutive_failures": hook.consecutive_failures,
        "daily": [{"date": d.isoformat(), "count": s.daily.get(d, 0)} for d in days_back(30)],
        "created_by": views.names.ref(hook.created_by) or {"id": "", "name": "Formalie"},
        "created_at": iso(hook.created_at), "updated_at": iso(hook.updated_at),
    }


async def insights(db: AsyncSession, tenant_id: uuid.UUID, hooks: list[Webhook]) -> dict[str, Any]:
    """WebhookInsights: webhooks by status, deliveries in the last 30 days and the 30 before, failed, success."""
    since = now() - 30 * DAY
    live = [h.id for h in hooks]
    recent, previous, failed, finished, delivered = (await db.execute(text(
        "SELECT count(*) FILTER (WHERE at >= :since), count(*) FILTER (WHERE at < :since), "
        "count(*) FILTER (WHERE at >= :since AND status = 'failed'), "
        "count(*) FILTER (WHERE at >= :since AND status <> 'retrying'), "
        "count(*) FILTER (WHERE at >= :since AND status = 'delivered') FROM webhook_deliveries "
        "WHERE tenant_id = :t AND NOT test AND webhook_id = ANY(:live) AND at >= :before"),
        {"t": tenant_id, "since": since, "before": since - 30 * DAY, "live": live})).one()
    per_day = {d: n for d, n in (await db.execute(text(
        "SELECT (at AT TIME ZONE 'UTC')::date, count(*) FROM webhook_deliveries WHERE tenant_id = :t AND NOT test "
        "AND webhook_id = ANY(:live) AND at >= :since GROUP BY 1"), {"t": tenant_id, "since": since, "live": live})).all()}
    statuses = [webhook_status_of(h.enabled, h.consecutive_failures) for h in hooks]
    return {"total": len(hooks), "by_status": {s: statuses.count(s) for s in ("active", "failing", "paused")},
            "deliveries_30d": recent, "previous_30d": previous, "failed_30d": failed,
            "success_rate": delivered / finished if finished else None,
            "daily": [{"date": d.isoformat(), "count": per_day.get(d, 0)} for d in days_back(30)]}


def delivery_view(row: WebhookDelivery, hook: Webhook | None, form_name: str | None) -> dict[str, Any]:
    """WebhookDelivery."""
    return {
        "id": str(row.id), "webhook": {"id": str(row.webhook_id), "name": hook.name if hook else "", "url": hook.url if hook else ""},
        "event": row.event, "status": row.status, "attempts": row.attempts, "status_code": row.status_code,
        "duration_ms": row.duration_ms, "at": iso(row.at), "next_retry_at": iso(row.next_retry_at), "test": row.test,
        "form": {"id": str(row.form_id), "name": form_name} if row.form_id and form_name is not None else None,
        "response_id": str(row.response_id) if row.response_id else None,
    }


def delivery_detail(row: WebhookDelivery, hook: Webhook | None, form_name: str | None) -> dict[str, Any]:
    """WebhookDeliveryDetail: what was sent (secrets and personal answers masked), the last answer, every try."""
    return {**delivery_view(row, hook, form_name), "request": {"headers": dict(row.request_headers or {}),
                                                                "body": row.logged_body},
            "response": row.response, "history": list(row.history or [])}


async def find_delivery(db: AsyncSession, tenant_id: uuid.UUID, delivery_id: uuid.UUID | None) -> WebhookDelivery | None:
    if delivery_id is None:
        return None
    return (await db.execute(select(WebhookDelivery).where(
        WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id == delivery_id))).scalars().first()


async def detail_of(db: AsyncSession, tenant_id: uuid.UUID, delivery_id: uuid.UUID) -> dict[str, Any] | None:
    row = await find_delivery(db, tenant_id, delivery_id)
    if row is None:
        return None
    hook = await db.get(Webhook, row.webhook_id)
    if hook is None or hook.deleted_at is not None:
        return None
    form = await db.get(Form, row.form_id) if row.form_id else None
    return delivery_detail(row, hook, form.name if form else None)


DELIVERY_SORTS = {"at": "d.at", "attempts": "d.attempts", "duration_ms": "coalesce(d.duration_ms, -1)"}
_FILTER_UUID = "00000000-0000-0000-0000-000000000000"


async def list_deliveries(db: AsyncSession, tenant_id: uuid.UUID, query: dict[str, str], offset: int,
                          limit: int) -> tuple[list[dict[str, Any]], int]:
    """GET /webhook-deliveries: between `from` and `to` (default everything), filtered, searched, sorted, one page."""
    where = ["d.tenant_id = :t", "w.deleted_at IS NULL"]
    params: dict[str, Any] = {"t": tenant_id}
    if query.get("from"):
        try:
            params["from"] = day_start(datetime.fromisoformat(query["from"]).date())
            where.append("d.at >= :from")
        except ValueError:
            pass
    if query.get("to"):
        try:
            params["to"] = day_start(datetime.fromisoformat(query["to"]).date()) + DAY - timedelta(milliseconds=1)
            where.append("d.at <= :to")
        except ValueError:
            pass
    if query.get("filter[webhook]"):
        ids = []
        for part in query["filter[webhook]"].split(","):
            try:
                ids.append(uuid.UUID(part))
            except ValueError:
                ids.append(uuid.UUID(_FILTER_UUID))
        where.append("d.webhook_id = ANY(:hooks)")
        params["hooks"] = ids
    if query.get("filter[status]"):
        where.append("d.status = ANY(:statuses)")
        params["statuses"] = query["filter[status]"].split(",")
    if query.get("filter[event]"):
        where.append("d.event = ANY(:events)")
        params["events"] = query["filter[event]"].split(",")
    q = (query.get("q") or "").strip().lower()
    if q:
        where.append("strpos(lower(w.name || ' ' || d.event || ' ' || coalesce(f.name, '') || ' ' || "
                     "coalesce(d.status_code::text, '')), :q) > 0")
        params["q"] = q
    sort = query.get("sort") or "-at"
    desc = sort.startswith("-")
    column = DELIVERY_SORTS.get(sort.lstrip("-"), "d.at")
    order = f"{column} {'DESC' if desc else 'ASC'}" + (", d.at DESC" if column != "d.at" else "") + ", d.id DESC"
    joins = ("FROM webhook_deliveries d JOIN webhooks w ON w.tenant_id = d.tenant_id AND w.id = d.webhook_id "
             "LEFT JOIN forms f ON f.tenant_id = d.tenant_id AND f.id = d.form_id")
    clause = " AND ".join(where)
    total = (await db.execute(text(f"SELECT count(*) {joins} WHERE {clause}"), params)).scalar_one()
    ids = [r[0] for r in (await db.execute(text(
        f"SELECT d.id {joins} WHERE {clause} ORDER BY {order} OFFSET :offset LIMIT :limit"),
        {**params, "offset": offset, "limit": limit})).all()]
    if not ids:
        return [], total
    rows = {r.id: r for r in (await db.execute(select(WebhookDelivery).where(
        WebhookDelivery.tenant_id == tenant_id, WebhookDelivery.id.in_(ids)))).scalars()}
    hooks = {h.id: h for h in (await db.execute(select(Webhook).where(
        Webhook.tenant_id == tenant_id, Webhook.id.in_({r.webhook_id for r in rows.values()})))).scalars()}
    forms = await forms_named(db, tenant_id, {str(r.form_id) for r in rows.values() if r.form_id})
    return [delivery_view(rows[i], hooks.get(rows[i].webhook_id), forms.get(str(rows[i].form_id)))
            for i in ids if i in rows], total

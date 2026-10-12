"""Webhooks (mock: routes/webhooks.ts; API-CONTRACT → Integrations). Admins only.

    GET    /webhooks                         list (q, sort, filter[status|event]) · /insights · /{id}
    POST   /webhooks                         { name, url, events, form_ids, token_id ('new' makes one), enabled? }
                                             → { webhook, token } (the token's secret once, when one was made)
    PATCH  /webhooks/{id}                    the same, or { enabled } alone · DELETE (its deliveries leave the lists)
    POST   /webhooks/{id}/test               a `ping` delivery now → the delivery with the receiver's answer
    GET    /webhook-deliveries               (from, to, q, sort, filter[webhook|status|event]) · /{id}
    POST   /webhook-deliveries/{id}/resend   the same body again as a new delivery (while retrying: the retry now)

Each delivery sends the webhook token (Tokens & headers) as `Authorization: Bearer`. The test and Send again wait for
the receiver's answer (10 seconds at most), like the mock; deliveries from response events go through the worker.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import outbound
from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.fernet_tokens import decrypt_secret
from app.core.security.limits import rate_limit
from app.modules.api_service import service as S
from app.modules.api_service.models import ApiToken
from app.modules.api_service.router import audit, page, scope
from app.modules.auth.sessions import Principal, require_admin
from app.modules.forms.models import Form
from app.modules.webhooks import service as W
from app.modules.webhooks import tasks
from app.modules.webhooks.models import Webhook
from app.modules.webhooks.rules import WEBHOOK_EVENTS, check_webhook_url

router = APIRouter(tags=["webhooks"])

webhook_schema = z.obj(
    name=z.string().trim().min(1).max(80),
    url=z.string().trim().max(2000),
    events=z.array(z.enum(list(WEBHOOK_EVENTS))).min(1),
    form_ids=z.array(z.string()).max(100),
    enabled=z.boolean().optional(),
    token_id=z.string().max(100).optional(),
)
SORTS = ("created_at", "name", "deliveries_30d", "success_rate")
PING_ANSWERS = {"full_name": "Alex Morgan", "email": "alex.morgan@example.com"}


def _resource(hook: Webhook) -> dict[str, Any]:
    return {"type": "webhook", "id": str(hook.id), "name": hook.name}


async def _hooks(db: Any, tenant_id: uuid.UUID) -> list[Webhook]:
    return list((await db.execute(select(Webhook).where(Webhook.tenant_id == tenant_id, Webhook.deleted_at.is_(None))
                                  .order_by(Webhook.created_at.desc()))).scalars())


def _find(hooks: list[Webhook], raw: str | None) -> Webhook:
    wanted = S.path_uuid(raw)
    found = next((h for h in hooks if h.id == wanted), None)
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


async def _checked(db: Any, tenant_id: uuid.UUID, values: dict[str, Any]) -> dict[str, Any]:
    """The address checked like the portal does (http://localhost while developing) and the forms of this workspace."""
    settings = get_settings()
    problem = check_webhook_url(values["url"], allow_local=outbound.local_allowed(settings.webhooks_allow_local))
    if problem:
        raise FrmError("FRM-GEN-1002", [{"field": "url", "message": problem}])
    ids = [S.ref_uuid(i) for i in values["form_ids"]]
    known = set()
    if all(i is not None for i in ids) and ids:
        known = set((await db.execute(select(Form.id).where(
            Form.tenant_id == tenant_id, Form.id.in_(ids), Form.deleted_at.is_(None), Form.purged_at.is_(None)))).scalars())
    if any(i is None or i not in known for i in ids):
        raise FrmError("FRM-GEN-1002", [{"field": "form_ids", "message": "form"}])
    return {"name": values["name"], "url": values["url"].strip(), "events": list(dict.fromkeys(values["events"])),
            "form_ids": list(dict.fromkeys(str(i) for i in ids))}


async def _token_for(db: Any, principal: Principal, raw: str | None, name: str) -> tuple[uuid.UUID, dict[str, Any] | None]:
    """The webhook token it sends: one of this workspace's webhook tokens, or 'new' (made and named after it)."""
    if raw == "new" or not raw:
        token, secret = await W.make_token(db, principal.tenant.id, principal.tenant.organisation_id, name,
                                           principal.user.id)
        return token.id, {"id": str(token.id), "name": token.name, "secret": secret}
    wanted = S.ref_uuid(raw)
    token = (await db.execute(select(ApiToken).where(
        ApiToken.tenant_id == principal.tenant.id, ApiToken.id == wanted, ApiToken.kind == "webhook",
        ApiToken.deleted_at.is_(None), ApiToken.revoked_at.is_(None)))).scalar_one_or_none() if wanted else None
    if token is None:
        raise FrmError("FRM-GEN-1002", [{"field": "token_id", "message": "webhook_token"}])
    return token.id, None


async def _view(db: Any, tenant_id: uuid.UUID, hook: Webhook) -> dict[str, Any]:
    return W.webhook_view(await W.Views.load(db, tenant_id, [hook]), hook)


# ── Webhooks ────────────────────────────────────────────────────────────────────

@router.get("/webhooks", dependencies=[rate_limit("webhooks", per_minute=120)])
async def list_webhooks(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        hooks = await _hooks(db, principal.tenant.id)
        views = await W.Views.load(db, principal.tenant.id, hooks)
    rows = [W.webhook_view(views, h) for h in hooks]
    rows = [r for r in rows if S.in_list(query.get("filter[status]"), r["status"])
            and (not query.get("filter[event]") or any(e in query["filter[event]"].split(",") for e in r["events"]))]
    sort = query.get("sort") or "-created_at"
    desc, key = sort.startswith("-"), sort.lstrip("-")
    key = key if key in SORTS else "created_at"

    def value(row: dict[str, Any]) -> Any:
        v = row.get(key)
        return -1 if v is None else v
    numeric = key in ("deliveries_30d", "success_rate")
    rows.sort(key=lambda r: value(r) if numeric else str(value(r)).lower() if key == "name" else str(value(r)), reverse=desc)
    return page(query, rows, lambda r, q: q in f"{r['name']} {r['url']}".lower())


@router.get("/webhooks/insights", dependencies=[rate_limit("webhooks", per_minute=60)])
async def webhook_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        hooks = await _hooks(db, principal.tenant.id)
        return ok(await W.insights(db, principal.tenant.id, hooks))


@router.get("/webhooks/{webhook_id}", dependencies=[rate_limit("webhooks", per_minute=240)])
async def get_webhook(webhook_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        hook = _find(await _hooks(db, principal.tenant.id), webhook_id)
        return ok(await _view(db, principal.tenant.id, hook))


@router.post("/webhooks", status_code=201, dependencies=[rate_limit("webhooks-write", per_minute=30)])
async def create_webhook(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = webhook_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        fields = await _checked(db, principal.tenant.id, values)
        token_id, made = await _token_for(db, principal, values.get("token_id"), fields["name"])
        enabled = values.get("enabled", True) is not False
        hook = Webhook(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, **fields,
                       enabled=enabled, paused_reason=None if enabled else "manual", token_id=token_id,
                       consecutive_failures=0, created_by=principal.user.id, updated_by=principal.user.id)
        db.add(hook)
        await db.flush()
        await audit(db, principal, "integrations.webhook_created", _resource(hook),
                    metadata={"url": hook.url, "events": ", ".join(hook.events)})
        if made:
            await audit(db, principal, "api.token_created", {"type": "api_token", "id": made["id"], "name": made["name"]},
                        metadata={"kind": "webhook", "webhook": hook.name})
        return ok({"webhook": await _view(db, principal.tenant.id, hook), "token": made})


@router.patch("/webhooks/{webhook_id}", dependencies=[rate_limit("webhooks-write", per_minute=60)])
async def update_webhook(webhook_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = await request.json()
    async with db_session("write", **scope(principal)) as db:
        hook = _find(await _hooks(db, principal.tenant.id), webhook_id)
        if isinstance(body, dict) and list(body) == ["enabled"] and isinstance(body["enabled"], bool):
            if hook.enabled != body["enabled"]:
                hook.enabled = body["enabled"]
                hook.paused_reason = None if hook.enabled else "manual"
                if hook.enabled:
                    hook.consecutive_failures = 0
                hook.updated_by = principal.user.id
                await audit(db, principal, "integrations.webhook_enabled" if hook.enabled else "integrations.webhook_disabled",
                            _resource(hook))
                await db.flush()
            return ok(await _view(db, principal.tenant.id, hook))
        values = webhook_schema.parse(body)
        before = {"url": hook.url, "events": ", ".join(hook.events), "token": hook.token_id}
        fields = await _checked(db, principal.tenant.id, values)
        if values.get("token_id") and S.ref_uuid(values["token_id"]) != hook.token_id:
            hook.token_id, _ = await _token_for(db, principal, values["token_id"], fields["name"])
        for key, value in fields.items():
            setattr(hook, key, value)
        if values.get("enabled") is not None and values["enabled"] != hook.enabled:
            hook.enabled = values["enabled"]
            hook.paused_reason = None if hook.enabled else "manual"
            if hook.enabled:
                hook.consecutive_failures = 0
        hook.updated_by = principal.user.id
        changes = []
        if before["url"] != hook.url:
            changes.append({"field": "url", "before": before["url"], "after": hook.url})
        if before["events"] != ", ".join(hook.events):
            changes.append({"field": "events", "before": before["events"], "after": ", ".join(hook.events)})
        if before["token"] != hook.token_id:
            names = {t.id: t.name for t in (await W.tokens_of(db, principal.tenant.id)).values()}
            changes.append({"field": "token", "before": names.get(before["token"]) if before["token"] else None,
                            "after": names.get(hook.token_id) if hook.token_id else None})
        await audit(db, principal, "integrations.webhook_updated", _resource(hook), changes=changes)
        await db.flush()
        return ok(await _view(db, principal.tenant.id, hook))


@router.delete("/webhooks/{webhook_id}", dependencies=[rate_limit("webhooks-write", per_minute=30)])
async def delete_webhook(webhook_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        hook = _find(await _hooks(db, principal.tenant.id), webhook_id)
        hook.soft_delete(principal.user.id)
        await audit(db, principal, "integrations.webhook_deleted", _resource(hook))
    return ok({"deleted": True})


@router.post("/webhooks/{webhook_id}/test", dependencies=[rate_limit("webhooks-test", per_minute=20)])
async def test_webhook(webhook_id: str, principal: Principal = Depends(require_admin)) -> Any:
    """A `ping` with a sample of what a response event looks like; waits for the receiver's answer."""
    async with db_session("write", **scope(principal)) as db:
        hook = _find(await _hooks(db, principal.tenant.id), webhook_id)
        forms = select(Form).where(Form.tenant_id == principal.tenant.id, Form.deleted_at.is_(None),
                                   Form.purged_at.is_(None))
        if hook.form_ids:
            forms = forms.where(Form.id.in_([uuid.UUID(i) for i in hook.form_ids]))
        form = (await db.execute(forms.order_by(Form.created_at.desc()).limit(1))).scalar_one_or_none()
        body = {"type": "ping", "created_at": W.iso(W.now()), "test": True, "data": {
            "webhook": {"id": W.ref(hook.id), "name": hook.name, "events": list(hook.events)},
            "form": {"id": W.ref(form.id), "name": form.name} if form else None,
            "response": {"id": "rsp_sample", "status": "new", "channel": "link", "answers": PING_ANSWERS}}}
        delivery = W.new_delivery(hook, event="ping", test=True, form_id=form.id if form else None, response_id=None,
                                  body=body, personal={"full_name", "email"})
        db.add(delivery)
        await db.flush()
    await tasks.attempt(principal.tenant.id, principal.tenant.organisation_id, delivery.id, W.workspace_of_request())
    async with db_session("write", **scope(principal)) as db:
        return ok(await W.detail_of(db, principal.tenant.id, delivery.id))


# ── Deliveries ──────────────────────────────────────────────────────────────────

@router.get("/webhook-deliveries", dependencies=[rate_limit("webhooks", per_minute=120)])
async def list_deliveries(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    async with db_session("read", **scope(principal)) as db:
        rows, total = await W.list_deliveries(db, principal.tenant.id, query, params.offset, params.page_size)
    return ok(rows, params.meta(total))


@router.get("/webhook-deliveries/{delivery_id}", dependencies=[rate_limit("webhooks", per_minute=240)])
async def get_delivery(delivery_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        found = await W.detail_of(db, principal.tenant.id, S.path_uuid(delivery_id)) if S.path_uuid(delivery_id) else None
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return ok(found)


@router.post("/webhook-deliveries/{delivery_id}/resend", dependencies=[rate_limit("webhooks-test", per_minute=20)])
async def resend_delivery(delivery_id: str, principal: Principal = Depends(require_admin)) -> Any:
    """Send again: a new delivery with the same body (retries included); waits for the first try. While the delivery
    is still being retried, its next try happens now instead."""
    workspace = W.workspace_of_request()
    async with db_session("write", **scope(principal)) as db:
        source = await W.find_delivery(db, principal.tenant.id, S.path_uuid(delivery_id))
        hook = await db.get(Webhook, source.webhook_id) if source else None
        if source is None or hook is None or hook.deleted_at is not None:
            raise FrmError("FRM-GEN-1004")
        retry_now = source.status == "retrying" and source.body_enc is not None
        if not retry_now:
            parsed = json.loads(decrypt_secret(source.body_enc) if source.body_enc else source.logged_body)
            parsed.pop("id", None)
            delivery = W.new_delivery(hook, event=source.event, test=source.test, form_id=source.form_id,
                                      response_id=source.response_id, body=parsed, personal=set(), logged="")
            delivery.logged_body = re.sub(r'"id":"evt_[^"]*"', lambda _: f'"id":"evt_{W.ref(delivery.id)}"',
                                          source.logged_body, count=1)
            db.add(delivery)
            await db.flush()
            await audit(db, principal, "integrations.webhook_resent", _resource(hook), metadata={"event": source.event})
            target = delivery.id
        else:
            source.next_retry_at = None
            target = source.id
    await tasks.attempt(principal.tenant.id, principal.tenant.organisation_id, target, workspace, force=retry_now)
    async with db_session("write", **scope(principal)) as db:
        return ok(await W.detail_of(db, principal.tenant.id, target))

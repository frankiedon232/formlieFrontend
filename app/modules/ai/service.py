"""The assistant's bookkeeping (port of the mock's server/mock/data/aiStore.ts): settings, the month's allowance
(`require_ai`: FRM-AI-1001, 1003, 1002), recording a request with its usage, the rows the history shows, removal, and
emptying requests past the workspace's keep setting.

Differences from the mock: the allowance is read from `ai_usage` (a removed request never gives its credits back);
expired or removed requests are soft deleted with their prompt, result and draft emptied, and still count in usage.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, null, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import FrmError
from app.modules.ai.kinds import AI_DEFAULT_MONTHLY_CREDITS, AI_SOURCES, credits_of
from app.modules.ai.models import AiRequest, AiSettings, AiUsage
from app.modules.ai.provider import Usage
from app.modules.forms.service import iso

DAY = timedelta(days=1)


def now() -> datetime:
    return datetime.now(UTC)


def month_start(at: datetime | None = None) -> date:
    at = at or now()
    return date(at.year, at.month, 1)


def defaults() -> dict[str, Any]:
    return {"enabled": True, "sources": {"forms": True, "responses": True, "data": False}, "mask_personal": True,
            "keep_days": 90, "monthly_credits": AI_DEFAULT_MONTHLY_CREDITS, "updated_at": None, "updated_by": None}


async def settings_row(db: AsyncSession, tenant_id: uuid.UUID) -> AiSettings | None:
    return (await db.execute(select(AiSettings).where(AiSettings.tenant_id == tenant_id,
                                                      AiSettings.deleted_at.is_(None)))).scalar_one_or_none()


def settings_view(row: AiSettings | None) -> dict[str, Any]:
    if row is None:
        return defaults()
    sources = {source: bool((row.sources or {}).get(source, False)) for source in AI_SOURCES}
    return {"enabled": row.enabled, "sources": sources, "mask_personal": row.mask_personal, "keep_days": row.keep_days,
            "monthly_credits": row.monthly_credits, "updated_at": iso(row.updated_at) if row.updated_by else None,
            "updated_by": {"id": str(row.updated_by), "name": row.updated_by_name or ""} if row.updated_by else None}


async def settings_of(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    return settings_view(await settings_row(db, tenant_id))


def allowance_of(plan_id: str | None, settings: dict[str, Any]) -> int:
    """This month's credits: the plan's (F24); a plan without a number uses the agreed amount in the settings."""
    from app.modules.billing.service import limits_of

    credits = limits_of(plan_id).get("ai_credits")
    return int(credits) if credits is not None else int(settings["monthly_credits"])


async def credits_used(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Credits used since the start of this month (UTC)."""
    used = (await db.execute(select(AiUsage.credits).where(AiUsage.tenant_id == tenant_id,
                                                           AiUsage.month == month_start()))).scalar_one_or_none()
    return int(used or 0)


async def require_ai(db: AsyncSession, tenant: Any, kind: str, needs: list[str] | None = None,
                     cost: int | None = None) -> dict[str, Any]:
    """Every assistant call starts here: the assistant must be on (FRM-AI-1001), may read what the call needs
    (FRM-AI-1003) and the month's allowance must cover it (FRM-AI-1002)."""
    settings = await settings_of(db, tenant.id)
    if not settings["enabled"]:
        raise FrmError("FRM-AI-1001")
    if any(not settings["sources"].get(source) for source in needs or []):
        raise FrmError("FRM-AI-1003")
    spend = credits_of(kind) if cost is None else cost
    if await credits_used(db, tenant.id) + spend > allowance_of(tenant.plan_id, settings):
        raise FrmError("FRM-AI-1002")
    return settings


@dataclass
class Made:
    """What answered: the engine (model · standin · fallback), the model, why it fell back, and the tokens."""

    engine: str = "standin"
    model: str | None = None
    reason: str | None = None
    usage: Usage = field(default_factory=Usage)

    def join(self, other: Made) -> None:
        order = {"standin": 0, "model": 1, "fallback": 2}
        if order[other.engine] > order[self.engine]:
            self.engine = other.engine
        self.model = self.model or other.model
        self.reason = self.reason or other.reason
        self.usage.add(other.usage)


async def record_request(db: AsyncSession, principal: Any, settings: dict[str, Any], *, kind: str, status: str,
                         title: str, credits: int, prompt: str, result: str, read: list[str], made: Made,
                         target: dict[str, Any] | None = None, title_key: dict[str, Any] | None = None,
                         notes: list[dict[str, Any]] | None = None, stats: dict[str, Any] | None = None,
                         output: dict[str, Any] | None = None, masked: bool | None = None) -> AiRequest:
    """Keep a request and count it in the month's usage."""
    tenant, user = principal.tenant, principal.user
    at = now()
    request = AiRequest(
        tenant_id=tenant.id, organisation_id=tenant.organisation_id, kind=kind, status=status, title=title[:200],
        title_key=title_key, by_id=user.id, by_name=f"{user.first_name} {user.last_name}".strip() or user.email,
        target=target, credits=credits, prompt=prompt, result=result, read=read,
        masked=settings["mask_personal"] if masked is None else masked,
        applied_at=at if status == "applied" else None, output=output, notes=notes, stats=stats,
        engine=made.engine, model=made.model, fallback_reason=made.reason,
        input_tokens=made.usage.input_tokens, output_tokens=made.usage.output_tokens,
        cache_read_tokens=made.usage.cache_read_tokens, cache_write_tokens=made.usage.cache_write_tokens,
        created_by=user.id, created_at=at, updated_at=at)
    db.add(request)
    u = made.usage
    await db.execute(insert(AiUsage).values(
        id=uuid.uuid4(), tenant_id=tenant.id, organisation_id=tenant.organisation_id, month=month_start(at), requests=1,
        credits=credits, model_calls=u.model_calls, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
        cache_read_tokens=u.cache_read_tokens, cache_write_tokens=u.cache_write_tokens,
    ).on_conflict_do_update(index_elements=["tenant_id", "month"], set_={
        "requests": AiUsage.requests + 1, "credits": AiUsage.credits + credits,
        "model_calls": AiUsage.model_calls + u.model_calls, "input_tokens": AiUsage.input_tokens + u.input_tokens,
        "output_tokens": AiUsage.output_tokens + u.output_tokens,
        "cache_read_tokens": AiUsage.cache_read_tokens + u.cache_read_tokens,
        "cache_write_tokens": AiUsage.cache_write_tokens + u.cache_write_tokens, "updated_at": func.now()}))
    await db.flush()
    return request


async def replace(db: AsyncSession, principal: Any, request_id: uuid.UUID | None) -> None:
    """A request that was waiting is replaced by "Try again": the old one is put aside."""
    if request_id is None:
        return
    old = await db.get(AiRequest, request_id)
    if old is not None and old.tenant_id == principal.tenant.id and old.by_id == principal.user.id \
            and old.deleted_at is None and old.status == "proposed":
        old.status, old.output = "discarded", null()


# ── History ───────────────────────────────────────────────────────────────────

async def kept_requests(db: AsyncSession, principal: Any, settings: dict[str, Any]) -> list[AiRequest]:
    """The requests this person may see (their own, or the workspace's with ai.settings), newest first, within the
    workspace's keep setting."""
    cutoff = now() - settings["keep_days"] * DAY
    query = select(AiRequest).where(AiRequest.tenant_id == principal.tenant.id, AiRequest.deleted_at.is_(None),
                                    AiRequest.created_at >= cutoff)
    if not principal.can("ai.settings"):
        query = query.where(AiRequest.by_id == principal.user.id)
    return list((await db.execute(query.order_by(AiRequest.created_at.desc(), AiRequest.id.desc()))).scalars())


def to_row(request: AiRequest, principal: Any) -> dict[str, Any]:
    return {"id": str(request.id), "kind": request.kind, "status": request.status, "title": request.title,
            "title_key": request.title_key, "by": {"id": str(request.by_id), "name": request.by_name},
            "target": copy.deepcopy(request.target), "credits": request.credits, "created_at": iso(request.created_at),
            "applied_at": iso(request.applied_at), "mine": request.by_id == principal.user.id}


def to_detail(request: AiRequest, principal: Any, settings: dict[str, Any]) -> dict[str, Any]:
    out = {**to_row(request, principal), "prompt": request.prompt, "result": request.result, "read": list(request.read),
           "masked": request.masked, "expires_at": iso(request.created_at + settings["keep_days"] * DAY)}
    if request.notes is not None:
        out["notes"] = request.notes
    if request.stats is not None:
        out["stats"] = request.stats
    return out


def emptied(request: AiRequest, by: uuid.UUID | None) -> None:
    """Removed (by a person or past the keep setting): soft deleted, its content emptied; it still counts in usage."""
    request.deleted_at, request.deleted_by = now(), by
    request.prompt, request.result, request.output, request.notes = "", "", null(), null()


async def expire(db: AsyncSession, tenant_id: uuid.UUID, keep_days: int) -> int:
    result = await db.execute(update(AiRequest).where(
        AiRequest.tenant_id == tenant_id, AiRequest.deleted_at.is_(None),
        AiRequest.created_at < now() - keep_days * DAY).values(
        deleted_at=func.now(), prompt="", result="", output=null(), notes=null()))
    return result.rowcount or 0  # type: ignore[attr-defined]


async def all_rows(db: AsyncSession, tenant_id: uuid.UUID, since: datetime) -> list[AiRequest]:
    """Every request since a moment, removed ones included (usage counts them)."""
    return list((await db.execute(select(AiRequest).where(AiRequest.tenant_id == tenant_id,
                                                          AiRequest.created_at >= since))).scalars())

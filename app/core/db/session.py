"""Session router and RLS context (BACKEND-SPEC §2, §3; CLAUDE.md rules 1 and 9).

Every transaction starts with
    SELECT set_config('app.tenant_id', …, true), set_config('app.organisation_id', …, true),
           set_config('app.user_id', …, true)
transaction-local, so it is safe with PgBouncer transaction pooling. Without a tenant the settings are empty
and RLS matches no tenant row (fail closed).

intent="write" → primary. intent="read" → a replica, unless this user wrote in the last few seconds
(read-your-writes: Redis flag `fm:v1:rw:{user_id}`), then the primary.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.engines import get_engines
from app.core.errors.exceptions import FrmError

log = logging.getLogger("formalie.db")

Intent = Literal["read", "write"]

_SET_CONTEXT = text(
    "SELECT set_config('app.tenant_id', :tenant_id, true), "
    "set_config('app.organisation_id', :organisation_id, true), "
    "set_config('app.user_id', :user_id, true)"
)


def _rw_key(user_id: uuid.UUID) -> str:
    return f"fm:v1:rw:{user_id}"


async def set_rls_context(
    session: AsyncSession,
    tenant_id: uuid.UUID | None,
    organisation_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    await session.execute(_SET_CONTEXT, {
        "tenant_id": str(tenant_id) if tenant_id else "",
        "organisation_id": str(organisation_id) if organisation_id else "",
        "user_id": str(user_id) if user_id else "",
    })


async def _pinned_to_primary(user_id: uuid.UUID | None) -> bool:
    if user_id is None:
        return False
    try:
        return bool(await get_redis().exists(_rw_key(user_id)))
    except RedisError:
        return True  # unsure: read from the primary


async def _pin_after_write(user_id: uuid.UUID | None) -> None:
    if user_id is None:
        return
    try:
        await get_redis().set(_rw_key(user_id), "1", ex=get_settings().db_read_your_writes_seconds)
    except RedisError as exc:
        log.warning("read-your-writes pin failed", extra={"error": str(exc)})


@asynccontextmanager
async def db_session(
    intent: Intent = "write",
    *,
    tenant_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> AsyncIterator[AsyncSession]:
    """One transaction with the RLS context set. Commits on success, rolls back on any error (but see
    FrmError(commit=True))."""
    engines = get_engines()
    use_primary = intent == "write" or await _pinned_to_primary(user_id)
    engine = engines.primary if use_primary else engines.replica()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.begin()
        try:
            await set_rls_context(session, tenant_id, organisation_id, user_id)
            yield session
            await session.commit()
        except FrmError as exc:
            # An error marked commit=True keeps what was done (audit of a failed sign-in, a revoked session).
            await (session.commit() if exc.commit else session.rollback())
            raise
        except BaseException:
            await session.rollback()
            raise
    if intent == "write":
        await _pin_after_write(user_id)


def _request_scope() -> dict[str, uuid.UUID | None]:
    ctx = get_context()
    tenant = ctx.tenant if ctx else None
    return {
        "tenant_id": tenant.id if tenant else None,
        "organisation_id": tenant.organisation_id if tenant else None,
        "user_id": ctx.user_id if ctx else None,
    }


async def write_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: primary, scoped to this request's workspace and user."""
    async with db_session("write", **_request_scope()) as session:
        yield session


async def read_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: replica (or primary right after this user's write), scoped to this request."""
    async with db_session("read", **_request_scope()) as session:
        yield session

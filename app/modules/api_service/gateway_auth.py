"""Who calls the public API (mock: publicApi.ts `issueAccessToken`, `callerToken`, `issueConsoleToken`;
SECURITY-PROTOCOL §9): the token behind `Authorization: Bearer …`, the short-lived tokens of client credentials and of
and the Docs console.

- **Static tokens:** looked up by the SHA-256 of the secret (the old secret too while a rotation's grace lasts).
- **Client credentials:** `POST /{apiKey}/token` with the client id and secret gives a short-lived token
  (`formalie_access_{mode}_…`, its own lifetime, 15 minutes by default). It is signed and encrypted (Fernet: the
  workspace, the token and when it ends), so nothing is stored; it stops working with its client (revoked, expired).
- **The Docs console** (Try it): a test token that may call everything, lives a minute and is never stored.
- Two ways to sign in, never both (owner, 2026-10-06): a client id or secret sent as Bearer, or a bearer token sent to
  /token, is refused with a detail saying how to do it; a webhook token only identifies Formalie's calls to webhooks.
- **No signed calls** (owner, 2026-10-06): tokens only. `signing` stays in a token's shape, always false.
"""

from __future__ import annotations

import hmac
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.fernet_tokens import make_token, read_token
from app.modules.api_service import tokens as T
from app.modules.api_service.models import ApiToken
from app.modules.api_service.traffic import CONSOLE_TOKEN_ID

ACCESS_PURPOSE = "api_access"
CONSOLE_SECONDS = 60
MAX_LIFETIME_MINUTES = max(T.TOKEN_LIFETIMES)
_BEARER = re.compile(r"^Bearer\s+(\S+)$", re.IGNORECASE)


class Refused(Exception):
    """A call refused: the FRM code and its details (raised as GatewayError by the gateway)."""

    def __init__(self, code: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or []


@dataclass
class ConsoleToken:
    """The Docs console's token (mock: consoleToken()): test, may call everything, never stored."""

    id: str = CONSOLE_TOKEN_ID
    name: str = "Docs console"
    kind: str = "static"
    mode: str = "test"
    scopes: dict[str, list[str]] = field(default_factory=lambda: {"services": [], "endpoints": [], "methods": []})
    expires_at: datetime | None = None
    signing: bool = False


Caller = ApiToken | ConsoleToken


def bearer_of(headers: Any) -> str | None:
    found = _BEARER.match(headers.get("authorization") or "")
    return found.group(1) if found else None


def _same(a: str, b: str) -> bool:
    return len(a) == len(b) and hmac.compare_digest(a, b)


def matches(token: ApiToken, secret: str) -> bool:
    """The secret is the token's, or its previous one while the rotation's grace lasts."""
    digest = T.hash_secret(secret)
    if _same(token.secret_hash, digest):
        return True
    return bool(token.previous_hash) and token.rotating_until is not None \
        and token.rotating_until > datetime.now(UTC) and _same(token.previous_hash or "", digest)


def live(token: ApiToken) -> bool:
    return T.token_status_of(token.revoked_at, token.expires_at) in ("active", "expiring")


async def tokens_of(db: AsyncSession, tenant_id: uuid.UUID) -> list[ApiToken]:
    return list((await db.execute(select(ApiToken).where(
        ApiToken.tenant_id == tenant_id, ApiToken.deleted_at.is_(None)))).scalars())


# ── Short-lived tokens ──────────────────────────────────────────────────────────

def _short(tenant_id: uuid.UUID, ref: str, mode: str, seconds: int) -> str:
    payload = {"p": ACCESS_PURPOSE, "t": str(tenant_id), "k": ref, "e": int(time.time()) + seconds}
    return f"{T.token_prefix('access', mode)}{make_token(payload)}"


def read_short(bearer: str) -> dict[str, Any] | None:
    """The payload of a short-lived token (any workspace), or None when it is not one, altered or ended."""
    found = re.match(r"^formalie_access_(?:live|test)_(.+)$", bearer)
    if not found:
        return None
    payload = read_token(found.group(1), ttl_seconds=MAX_LIFETIME_MINUTES * 60 + 60)
    if not payload or payload.get("p") != ACCESS_PURPOSE or not isinstance(payload.get("e"), int):
        return None
    return payload


def issue_console_token(tenant_id: uuid.UUID) -> str:
    """A test token for the Docs console (Try it), a minute long (mock: issueConsoleToken)."""
    return _short(tenant_id, CONSOLE_TOKEN_ID, "test", CONSOLE_SECONDS)


async def issue_access_token(db: AsyncSession, tenant_id: uuid.UUID, headers: Any, body: dict[str, Any]) -> dict[str, Any]:
    """POST /{apiKey}/token: client credentials → a short-lived bearer token."""
    tokens = await tokens_of(db, tenant_id)
    client_id = body.get("client_id")
    token = next((t for t in tokens if t.kind == "client" and isinstance(client_id, str) and t.client_id == client_id), None)
    sent = [v for v in (body.get("client_secret"), client_id, bearer_of(headers)) if isinstance(v, str) and v]
    if token is None and any(t.kind == "static" and matches(t, v) for v in sent for t in tokens):
        raise Refused("FRM-API-1010", [{"field": "token", "message": "bearer_token: send it as Authorization: Bearer "
                                                                     "with each call, not to /token"}])
    secret = body.get("client_secret")
    if token is None or not isinstance(secret, str) or not matches(token, secret) or not live(token):
        raise Refused("FRM-API-1010")
    seconds = (token.lifetime_minutes or 15) * 60
    access = _short(tenant_id, str(token.id), token.mode, seconds)
    token.last_used_at = datetime.now(UTC)
    return {"access_token": access, "token_type": "Bearer", "expires_in": seconds}


async def caller_token(db: AsyncSession, tenant_id: uuid.UUID, headers: Any) -> Caller:
    """The token behind `Authorization: Bearer …` (a static token or a short-lived one), or FRM-API-1010."""
    bearer = bearer_of(headers)
    if not bearer:
        raise Refused("FRM-API-1010")
    tokens = await tokens_of(db, tenant_id)
    short = read_short(bearer)
    token: Caller | None = None
    if short is not None:
        valid = short["t"] == str(tenant_id) and short["e"] > time.time()
        if valid and short["k"] == CONSOLE_TOKEN_ID:
            token = ConsoleToken()
        elif valid:
            token = next((t for t in tokens if str(t.id) == short["k"]), None)
    elif not bearer.startswith("formalie_access_"):
        token = next((t for t in tokens if t.kind == "static" and matches(t, bearer)), None)
    if token is None and any(t.kind == "webhook" and matches(t, bearer) for t in tokens):
        raise Refused("FRM-API-1010", [{"field": "Authorization", "message": "webhook_token: it only identifies "
                                        "Formalie's calls to your webhooks and can not call the API"}])
    if token is None and any(t.kind == "client" and (t.client_id == bearer or matches(t, bearer)) for t in tokens):
        raise Refused("FRM-API-1010", [{"field": "Authorization", "message": "client_credentials: post the client id "
                                        "and secret to /token first, then send that short-lived token as Bearer"}])
    if token is None or (isinstance(token, ApiToken) and not live(token)):
        raise Refused("FRM-API-1010")
    return token

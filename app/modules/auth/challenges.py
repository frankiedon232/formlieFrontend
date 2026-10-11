"""Sign-in codes and one-time tickets in Redis (port of the mock's core/auth.ts challenge part, SECURITY-PROTOCOL §7).

A challenge: purpose (login · signup · find · reset), the email, channel(s), a 6-digit code kept only as a hash,
how long it lasts and how many tries it allows (the workspace's code rules, else 5 minutes and 5 tries), resends
(60 s apart, at most 3). Wrong code: FRM-AUTH-1003 with `attempts_left`; out of tries: FRM-AUTH-1004.
An authenticator-app challenge checks the person's TOTP or one of their recovery codes instead (the route does
that, with the database). Tickets: one-time, 2 minutes, for the hand-off to a new workspace's subdomain.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.cache.redis import get_redis
from app.core.errors import FrmError

PREFIX = "fm:v1:auth:ch:"
TICKET_PREFIX = "fm:v1:auth:ticket:"
KEEP_SECONDS = 30 * 60  # a challenge (with its resends) is kept at most this long
OTP_TTL_MS = 5 * 60 * 1000
OTP_MAX_ATTEMPTS = 5
RESEND_AFTER_S = 60
MAX_RESENDS = 3
TICKET_TTL_S = 120


@dataclass
class Challenge:
    id: str
    purpose: str
    email: str
    channel: str
    channels: list[str]
    tenant_id: str | None = None
    organisation_id: str | None = None
    tenant_name: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    language: str | None = None
    code_hash: str = ""
    expires_at: int = 0  # ms
    attempts: int = 0
    resends: int = 0
    last_sent_at: int = 0  # ms
    verified: bool = False
    ttl_ms: int = OTP_TTL_MS
    max_attempts: int = OTP_MAX_ATTEMPTS
    signup: dict[str, Any] | None = field(default=None)  # first_name, last_name, password_hash


def _now_ms() -> int:
    return int(time.time() * 1000)


def _hash(challenge_id: str, code: str) -> str:
    return hashlib.sha256(f"{challenge_id}:{code}".encode()).hexdigest()


def mask_email(email: str) -> str:
    """mask(): first and last letter of the name, dots between, the domain as it is."""
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'•' * max(1, len(name) - 2)}{name[-1:]}@{domain}"


async def _save(ch: Challenge) -> None:
    await get_redis().set(PREFIX + ch.id, json.dumps(asdict(ch)), ex=KEEP_SECONDS)


async def get_challenge(challenge_id: str) -> Challenge | None:
    if not challenge_id or len(challenge_id) > 64:
        return None
    raw = await get_redis().get(PREFIX + challenge_id)
    return Challenge(**json.loads(raw)) if raw else None


def _new_code(ch: Challenge) -> str:
    """A fresh code (sendCode): 6 digits, valid for the challenge's time from now."""
    code = f"{100000 + secrets.randbelow(900000)}"
    ch.code_hash = _hash(ch.id, code)
    ch.expires_at = _now_ms() + ch.ttl_ms
    ch.last_sent_at = _now_ms()
    return code


async def create_challenge(*, purpose: str, email: str, channel: str, channels: list[str],
                           tenant: dict[str, Any] | None = None, user: Any | None = None,
                           code_rules: dict[str, Any] | None = None, language: str | None = None,
                           signup: dict[str, Any] | None = None) -> tuple[Challenge, str | None]:
    """The challenge and its code (None for the authenticator app: nothing is sent)."""
    ch = Challenge(
        id=str(uuid.uuid4()), purpose=purpose, email=email, channel=channel, channels=channels,
        tenant_id=str(tenant["id"]) if tenant else None,
        organisation_id=str(tenant["organisation_id"]) if tenant else None,
        tenant_name=tenant["name"] if tenant else None,
        user_id=str(user.id) if user is not None else None,
        user_name=user.first_name if user is not None else None,
        language=language,
        ttl_ms=int(code_rules["expiry_minutes"]) * 60_000 if code_rules else OTP_TTL_MS,
        max_attempts=int(code_rules["max_attempts"]) if code_rules else OTP_MAX_ATTEMPTS,
        signup=signup,
    )
    code = _new_code(ch)
    await _save(ch)
    return ch, (None if channel == "totp" else code)


def describe(ch: Challenge) -> dict[str, Any]:
    """LoginChallenge (shared/types/auth.ts)."""
    return {
        "challenge_id": ch.id,
        "channels": ch.channels,
        "channel": ch.channel,
        "masked_destination": mask_email(ch.email),
        "resend_after": RESEND_AFTER_S,
        "expires_at": datetime.fromtimestamp(ch.expires_at / 1000, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


async def _wrong(ch: Challenge) -> FrmError:
    ch.attempts += 1
    await _save(ch)
    left = ch.max_attempts - ch.attempts
    if left <= 0:
        return FrmError("FRM-AUTH-1004")
    return FrmError("FRM-AUTH-1003", [{"field": "attempts_left", "message": str(left)}])


async def verify_code(challenge_id: str, code: str, purpose: str, *, second_factor: Any = None) -> Challenge:
    """verifyChallenge(). `second_factor(ch, code)` checks an authenticator / recovery code (async, returns bool)."""
    ch = await get_challenge(challenge_id)
    if ch is None or ch.purpose != purpose or ch.expires_at < _now_ms():
        raise FrmError("FRM-AUTH-1003")
    if ch.attempts >= ch.max_attempts:
        raise FrmError("FRM-AUTH-1004")
    if ch.channel == "totp" and second_factor is not None:
        ok = await second_factor(ch, code)
    else:
        ok = secrets.compare_digest(ch.code_hash, _hash(ch.id, code))
    if not ok:
        raise await _wrong(ch)
    ch.verified = True
    await _save(ch)
    return ch


async def resend(challenge_id: str, channel: str | None) -> tuple[Challenge, str | None]:
    """resendChallenge(): at most 3, 60 s apart (leaving the authenticator app for a sent code needs no wait)."""
    ch = await get_challenge(challenge_id)
    if ch is None or ch.verified:
        raise FrmError("FRM-AUTH-1003")
    if ch.resends >= MAX_RESENDS:
        raise FrmError("FRM-AUTH-1004")
    if ch.channel != "totp" and _now_ms() - ch.last_sent_at < RESEND_AFTER_S * 1000:
        raise FrmError("FRM-GEN-1029")
    if channel and channel in ch.channels:
        ch.channel = channel
    ch.resends += 1
    ch.attempts = 0
    code = _new_code(ch)
    await _save(ch)
    return ch, (None if ch.channel == "totp" else code)


async def consume(challenge_id: str) -> None:
    await get_redis().delete(PREFIX + challenge_id)


# ── One-time tickets (sign-up hand-off to the new subdomain) ───────────────────

def _ticket_key(ticket: str) -> str:
    return TICKET_PREFIX + hashlib.sha256(ticket.encode()).hexdigest()


async def issue_ticket(user_id: uuid.UUID, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> str:
    ticket = secrets.token_urlsafe(24)
    await get_redis().set(_ticket_key(ticket), json.dumps({"user_id": str(user_id), "tenant_id": str(tenant_id),
                                                           "organisation_id": str(organisation_id)}), ex=TICKET_TTL_S)
    return ticket


async def redeem_ticket(ticket: str) -> dict[str, str] | None:
    """Single use: read and removed at once (GETDEL)."""
    raw = await get_redis().getdel(_ticket_key(ticket))
    return json.loads(raw) if raw else None

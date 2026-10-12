"""Sign-in codes and one-time tickets in Redis (port of the mock's core/auth.ts challenge part, SECURITY-PROTOCOL §7).

A challenge: purpose (login · signup · find · reset), the email, channel(s), a 6-digit code kept only as a hash,
how long it lasts and how many tries it allows (the workspace's code rules, else 5 minutes and 5 tries), resends
(60 s apart, at most 3). Wrong code: FRM-AUTH-1003 with `attempts_left`; out of tries: FRM-AUTH-1004. Tries are
counted atomically in Redis before the comparison, one total per challenge whatever the resends.
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
    signup: dict[str, Any] | None = field(default=None)  # first_name, last_name, password_hash (+ provider, subject)
    method: str = "password"  # how the person proved who they are: password, google, microsoft, facebook


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
                           signup: dict[str, Any] | None = None, method: str = "password",
                           verified: bool = False) -> tuple[Challenge, str | None]:
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
        method=method,
        verified=verified,
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


def _attempts_key(challenge_id: str) -> str:
    return f"{PREFIX}{challenge_id}:attempts"


def _won_key(challenge_id: str) -> str:
    return f"{PREFIX}{challenge_id}:won"


async def _count_attempt(challenge_id: str) -> int:
    """One more try, counted in Redis before the code is compared (INCR is atomic, so parallel guesses each count).
    One total per challenge: a resend never resets it (security review M1)."""
    redis = get_redis()
    used = int(await redis.incr(_attempts_key(challenge_id)))
    if used == 1:
        await redis.expire(_attempts_key(challenge_id), KEEP_SECONDS)
    return used


async def attempts_used(challenge_id: str) -> int:
    raw = await get_redis().get(_attempts_key(challenge_id))
    return int(raw) if raw else 0


async def verify_code(challenge_id: str, code: str, purpose: str, *, second_factor: Any = None) -> Challenge:
    """verifyChallenge(). `second_factor(ch, code)` checks an authenticator / recovery code (async, returns bool).
    The try is counted before the comparison, and only one right answer ever wins a challenge (SET NX): parallel
    requests can neither multiply the guesses nor use one code twice."""
    ch = await get_challenge(challenge_id)
    if ch is None or ch.purpose != purpose or ch.expires_at < _now_ms():
        raise FrmError("FRM-AUTH-1003")
    used = await _count_attempt(ch.id)
    if used > ch.max_attempts:
        raise FrmError("FRM-AUTH-1004")
    if ch.channel == "totp" and second_factor is not None:
        ok = await second_factor(ch, code)
    else:
        ok = secrets.compare_digest(ch.code_hash, _hash(ch.id, code))
    if not ok:
        left = ch.max_attempts - used
        if left <= 0:
            raise FrmError("FRM-AUTH-1004")
        raise FrmError("FRM-AUTH-1003", [{"field": "attempts_left", "message": str(left)}])
    if not await get_redis().set(_won_key(ch.id), "1", nx=True, ex=KEEP_SECONDS):
        raise FrmError("FRM-AUTH-1003")  # a parallel request with the same code got there first
    ch.verified = True
    ch.attempts = used
    await _save(ch)
    return ch


async def resend(challenge_id: str, channel: str | None) -> tuple[Challenge, str | None]:
    """resendChallenge(): at most 3, 60 s apart (leaving the authenticator app for a sent code needs no wait).
    Only to a channel the challenge offers: an account with an authenticator app is offered the app only (M2),
    so asking for an email code there is FRM-AUTH-1008. The tries already used stay used (M1)."""
    ch = await get_challenge(challenge_id)
    if ch is None or ch.verified:
        raise FrmError("FRM-AUTH-1003")
    if channel and channel not in ch.channels:
        raise FrmError("FRM-AUTH-1008", [{"field": "channel", "message": "not_offered"}])
    if ch.resends >= MAX_RESENDS or await attempts_used(ch.id) >= ch.max_attempts:
        raise FrmError("FRM-AUTH-1004")
    if ch.channel != "totp" and _now_ms() - ch.last_sent_at < RESEND_AFTER_S * 1000:
        raise FrmError("FRM-GEN-1029")
    if channel:
        ch.channel = channel
    ch.resends += 1
    code = _new_code(ch)
    await _save(ch)
    return ch, (None if ch.channel == "totp" else code)


async def consume(challenge_id: str) -> None:
    await get_redis().delete(PREFIX + challenge_id, _attempts_key(challenge_id), _won_key(challenge_id))


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

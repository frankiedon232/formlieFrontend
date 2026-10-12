"""Unsubscribe links in optional emails (owner, 2026-10-12; port of the mock's data/unsubscribeStore.ts).

Only optional emails carry one: new responses (per form), notifications (per event, never `security_alert`), the daily
summary, and form invitations (per workspace). Never sign-in, account or respondent emails.

A link holds a signed token: the workspace (id and subdomain), the address, the kind and its ref, signed with a key
derived from ID_REF_MAC_KEY. It works without signing in and only for that address. The page `/email/unsubscribe?t=`
(manage.*) shows what stops and changes nothing until the person presses Unsubscribe (mail scanners open links on
their own); mail apps' own button posts to the plain `/email/one-click?t=` (RFC 8058). Before sending, `prepare()`
answers None for an address that stopped that kind of email, else the link and the headers for the message.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.emails.layout import assets_url
from app.modules.emails.models import EmailUnsubscribe

KINDS = ("response_notification", "notification", "daily_digest", "form_invitation")
NEVER = {"security_alert"}  # notifications that can't be turned off this way


@dataclass(frozen=True)
class Target:
    tenant_id: uuid.UUID
    subdomain: str
    email: str
    kind: str
    ref: str  # '' when the kind has none


@dataclass(frozen=True)
class Link:
    token: str
    page_url: str
    headers: dict[str, str]


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key() -> bytes:
    secret = get_settings().id_ref_mac_key
    if secret is None:
        raise RuntimeError("ID_REF_MAC_KEY is not set")
    return hmac.new(base64.b64decode(secret.get_secret_value()), b"formalie-unsubscribe-v1", hashlib.sha256).digest()


def _sign(payload: str) -> str:
    return _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest()[:18])


def token_for(target: Target) -> str:
    payload = _b64(json.dumps([str(target.tenant_id), target.subdomain, target.email.strip().lower(), target.kind,
                               target.ref], separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload)}"


def read_token(token: str | None) -> Target | None:
    """The target of a well-formed, untampered token, else None."""
    if not token or token.count(".") != 1 or len(token) > 600:
        return None
    payload, mac = token.split(".")
    if not hmac.compare_digest(_sign(payload), mac):
        return None
    try:
        tenant_id, subdomain, email, kind, ref = json.loads(_unb64(payload))
        if kind not in KINDS:
            return None
        return Target(uuid.UUID(tenant_id), str(subdomain), str(email), kind, str(ref or ""))
    except (ValueError, TypeError):
        return None


def link_for(target: Target) -> Link:
    token = token_for(target)
    base = assets_url()  # manage.* on the port the browser used (or EMAIL_ASSETS_URL)
    page = f"{base}/email/unsubscribe?t={token}"
    one_click = f"{base}{get_settings().api_prefix}/email/one-click?t={token}"
    return Link(token, page, {"List-Unsubscribe": f"<{one_click}>, <{page}>",
                              "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"})


async def _active(db: AsyncSession, target: Target) -> EmailUnsubscribe | None:
    return (await db.execute(select(EmailUnsubscribe).where(
        EmailUnsubscribe.tenant_id == target.tenant_id, EmailUnsubscribe.email == target.email.strip().lower(),
        EmailUnsubscribe.kind == target.kind, EmailUnsubscribe.ref == target.ref,
        EmailUnsubscribe.deleted_at.is_(None)))).scalar_one_or_none()


async def is_stopped(db: AsyncSession, target: Target) -> bool:
    return await _active(db, target) is not None


async def prepare(db: AsyncSession, *, tenant_id: uuid.UUID, subdomain: str, email: str, kind: str,
                  ref: str | None = None) -> Link | None:
    """Before sending an optional email: None when this address stopped it (skip), else its Unsubscribe link."""
    if kind == "notification" and ref in NEVER:
        return Link("", "", {})  # always sent, no link
    target = Target(tenant_id, subdomain, email.strip().lower(), kind, ref or "")
    if await is_stopped(db, target):
        return None
    return link_for(target)


async def set_stopped(db: AsyncSession, target: Target, organisation_id: uuid.UUID, stop: bool) -> bool:
    """→ True when something changed. Undo soft-deletes the stop, so the history stays."""
    row = await _active(db, target)
    if stop and row is None:
        db.add(EmailUnsubscribe(tenant_id=target.tenant_id, organisation_id=organisation_id,
                                email=target.email.strip().lower(), kind=target.kind, ref=target.ref))
        await db.flush()
        return True
    if not stop and row is not None:
        row.deleted_at = datetime.now(UTC)
        await db.flush()
        return True
    return False


def message_headers(link: Link | None) -> dict[str, Any]:
    """The extra fields a queued message carries so deliver() adds the List-Unsubscribe headers."""
    return {"headers": link.headers} if link and link.headers else {}

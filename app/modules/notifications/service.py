"""Telling people (mock: data/notificationStore.ts). `notify()` follows Settings → Notifications: in the app for the
people a rule names, by email (each time, or once a day in the summary). `params` fill the text (form name, count…),
never answers. Never raises: a notification never breaks the action that caused it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.emails import workspace as mail
from app.modules.notifications.models import Notification, NotificationDigestLine, NotificationOnce
from app.modules.rbac.service import grants_of, roles_of
from app.modules.settings.service import get_section
from app.modules.users.models import User

log = logging.getLogger("formalie.notifications")
KEEP = 100


def workspace_url(subdomain: str, path: str) -> str:
    """The workspace's portal address for a path (links in emails; the port the browser used, if any)."""
    from app.modules.tenants.router import host_port

    return f"https://{subdomain}.{get_settings().root_domain}{host_port()}{path}"


async def _recipients(db: AsyncSession, tenant_id: uuid.UUID, rule: dict[str, Any],
                      only: list[uuid.UUID] | None) -> tuple[list[uuid.UUID], list[tuple[str, str]]]:
    """Members get it in the app, everyone named gets the email."""
    users = list((await db.execute(select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None),
                                                      User.status == "active"))).scalars())
    if only is not None:
        chosen = [u for u in users if u.id in only]
    elif rule.get("to") == "people":
        wanted = {str(p) for p in rule.get("people") or []}
        chosen = [u for u in users if str(u.id) in wanted]
    elif rule.get("to") == "admins":
        roles = {r.id: r for r in await roles_of(db, tenant_id)}
        chosen = [u for u in users if grants_of(roles.get(u.role_id)).get("settings.manage")]
    else:
        chosen = users
    return [u.id for u in chosen], [(u.email, u.first_name or u.email) for u in chosen]


async def notify(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, workspace: dict[str, str],
                 event: str, params: dict[str, Any], link: str | None, only: list[uuid.UUID] | None = None) -> None:
    """`workspace`: {name, subdomain}. `link` is an in-app path; `only` limits it to these members."""
    try:
        settings = await get_section(db, tenant_id, "notifications")
        rule = (settings.get("events") or {}).get(event) or {}
        if not rule.get("in_app") and not rule.get("email"):
            return
        members, emails = await _recipients(db, tenant_id, rule, only)
        if rule.get("in_app"):
            for user_id in members:
                db.add(Notification(tenant_id=tenant_id, organisation_id=organisation_id, user_id=user_id, event=event,
                                    params=params, link=link))
        if rule.get("email") and emails:
            language = await mail.email_language(db, tenant_id)
            texts = mail.defaults(language)
            company = await get_section(db, tenant_id, "company")
            values = {"workspace": company.get("display_name") or workspace["name"], **params,
                      "reason": texts.get("reasons", {}).get(str(params.get("reason")), str(params.get("reason")))
                      if params.get("reason") else ""}
            event_texts = texts["events"][event]
            title = mail.fill_in(event_texts["title"], values)
            for email, name in emails:
                if (settings.get("digest") or {}).get("enabled"):
                    db.add(NotificationDigestLine(tenant_id=tenant_id, organisation_id=organisation_id, email=email,
                                                  name=name, line=title[:500]))
                else:
                    await mail.send(db, tenant_id, workspace["name"], to=email, key="notification", reason=event,
                                    values={"title": title, "message": mail.fill_in(event_texts["message"], values),
                                            "link": workspace_url(workspace["subdomain"], link or "/")})
        await db.flush()
    except Exception:  # noqa: BLE001
        log.exception("notification failed", extra={"event": event})


async def announce_once(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, key: str) -> bool:
    """True the first time a key is announced."""
    found = (await db.execute(select(NotificationOnce.id).where(NotificationOnce.tenant_id == tenant_id,
                                                                NotificationOnce.key == key))).scalar_one_or_none()
    if found is not None:
        return False
    db.add(NotificationOnce(tenant_id=tenant_id, organisation_id=organisation_id, key=key[:200]))
    await db.flush()
    return True


async def flush_digest(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, workspace: dict[str, str],
                       force: bool = False) -> int:
    """Sends the waiting daily summaries once the hour has come (or now, `force`) → how many went out."""
    settings = await get_section(db, tenant_id, "notifications")
    digest = settings.get("digest") or {}
    now = datetime.now(UTC)
    today = now.date().isoformat()
    if not force:
        if not digest.get("enabled") or now.hour < int(digest.get("hour") or 0):
            return 0
        if not await announce_once(db, tenant_id, organisation_id, f"digest:{today}"):
            return 0
    lines = list((await db.execute(select(NotificationDigestLine).where(
        NotificationDigestLine.tenant_id == tenant_id, NotificationDigestLine.deleted_at.is_(None))
        .order_by(NotificationDigestLine.created_at, NotificationDigestLine.id))).scalars())
    texts = mail.defaults(await mail.email_language(db, tenant_id))
    by_email: dict[str, dict[str, Any]] = {}
    for line in lines:
        entry = by_email.setdefault(line.email, {"name": line.name, "lines": []})
        entry["lines"].append(line.line)
        line.deleted_at = now
    sent = 0
    for email, entry in by_email.items():
        counts: dict[str, int] = {}
        for title in entry["lines"]:
            counts[title] = counts.get(title, 0) + 1
        summary = "\n".join(mail.fill_in(texts["layout"]["summary"], {"count": n, "title": t}) if n > 1 else t
                            for t, n in counts.items())
        await mail.send(db, tenant_id, workspace["name"], to=email, key="daily_digest", reason="daily_digest",
                        values={"name": entry["name"], "summary": summary,
                                "link": workspace_url(workspace["subdomain"], "/")})
        sent += 1
    await db.flush()
    return sent


async def announce_due(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID, workspace: dict[str, str]) -> None:
    """Forms closing within a day (once per closing time), and the daily summary when its hour has come."""
    from app.core.security.refs import get_codec
    from app.modules.forms.models import Form

    now = datetime.now(UTC)
    closing = (await db.execute(select(Form).where(
        Form.tenant_id == tenant_id, Form.status == "published", Form.deleted_at.is_(None),
        Form.closes_at > now, Form.closes_at <= now + timedelta(days=1)))).scalars()
    for form in closing:
        if await announce_once(db, tenant_id, organisation_id, f"closing:{form.id}:{form.closes_at.isoformat()}"):
            await notify(db, tenant_id, organisation_id, workspace, "form_closing",
                         {"form": form.name, "date": form.closes_at.astimezone(UTC).isoformat(timespec="milliseconds")
                          .replace("+00:00", "Z")}, f"/forms/{get_codec().encode_id(str(form.id))}/share")
    await flush_digest(db, tenant_id, organisation_id, workspace)


async def feed_of(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """NotificationFeed: newest first (100) and how many are unread."""
    mine = (Notification.tenant_id == tenant_id, Notification.user_id == user_id, Notification.deleted_at.is_(None))
    items = (await db.execute(select(Notification).where(*mine).order_by(Notification.created_at.desc(),
                                                                         Notification.id.desc()).limit(KEEP))).scalars()
    unread = (await db.execute(select(func.count()).select_from(Notification).where(
        *mine, Notification.read_at.is_(None)))).scalar_one()

    def iso(value: datetime | None) -> str | None:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None
    return {"items": [{"id": str(n.id), "event": n.event, "params": n.params, "link": n.link,
                       "created_at": iso(n.created_at), "read_at": iso(n.read_at)} for n in items], "unread": unread}


async def mark_read(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, ids: list[uuid.UUID] | None) -> None:
    """These (or all, None) are read."""
    where = [Notification.tenant_id == tenant_id, Notification.user_id == user_id, Notification.read_at.is_(None),
             Notification.deleted_at.is_(None)]
    if ids is not None:
        where.append(Notification.id.in_(ids))
    await db.execute(update(Notification).where(*where).values(read_at=datetime.now(UTC)))


async def clear_read(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """The read ones leave the feed (their rows stay, deleted_at)."""
    await db.execute(update(Notification).where(
        Notification.tenant_id == tenant_id, Notification.user_id == user_id, Notification.read_at.is_not(None),
        Notification.deleted_at.is_(None)).values(deleted_at=datetime.now(UTC), deleted_by=user_id))

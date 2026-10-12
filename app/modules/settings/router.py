"""Workspace settings routes (mock: routes/settings.ts, API-CONTRACT → Settings).

Admins only, except appearance, form defaults and localisation, which every member's portal needs. A change that
would lock the admin out is refused (FRM-AUTH-1017): their own email domain left off the allowed domains, or their
own address left off the IP allowlist. Every change is in the audit trail (`settings.updated`, field by field).
The single sign-on routes (`/settings/sso`, B11) must be included before this router.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.net import ip_in_cidr
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.audit import queries as audit_queries
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, active_sessions, require_admin, require_auth, revoke_sessions
from app.modules.billing.service import require_feature
from app.modules.settings import schemas
from app.modules.settings.catalogues import SETTINGS_SECTIONS
from app.modules.settings.changes import settings_changes
from app.modules.settings.service import all_settings, get_section, save_section
from app.modules.tenants.models import Organisation
from app.modules.uploads.service import completed_url

router = APIRouter(tags=["settings"])

LABELS = {"company": "Company", "branding": "Branding", "localisation": "Language and region", "signin": "Sign-in",
          "security": "Security", "notifications": "Notifications", "emails": "Email templates",
          "privacy": "Privacy and data", "form_defaults": "Form defaults", "appearance": "Appearance"}


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _section(value: str) -> str:
    if value not in SETTINGS_SECTIONS:
        raise FrmError("FRM-GEN-1004")
    return value


def _locked_out(field: str, message: str) -> FrmError:
    return FrmError("FRM-AUTH-1017", [{"field": field, "message": message}])


@router.get("/settings", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_settings_all(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await all_settings(db, principal.tenant.id))


async def _member_section(principal: Principal, section: str) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await get_section(db, principal.tenant.id, section))


@router.get("/settings/appearance", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_appearance(principal: Principal = Depends(require_auth)) -> Any:
    """Everyone's portal wears the workspace's look."""
    return await _member_section(principal, "appearance")


@router.get("/settings/form_defaults", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_form_defaults(principal: Principal = Depends(require_auth)) -> Any:
    """Every member's "new form" dialog starts from these."""
    return await _member_section(principal, "form_defaults")


@router.get("/settings/localisation", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_localisation(principal: Principal = Depends(require_auth)) -> Any:
    return await _member_section(principal, "localisation")


# ── Security: sessions and sign-in activity (before /settings/{section}) ──────────

@router.get("/settings/security/sessions", dependencies=[rate_limit("settings-sessions", per_minute=60)])
async def list_sessions(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await active_sessions(db, principal.tenant.id, principal.session_id))


@router.post("/settings/security/sessions/sign-out", dependencies=[rate_limit("settings-sign-out", per_minute=20)])
async def sign_out_sessions(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    """Ends the chosen sessions, or everyone's but the caller's (never the caller's own)."""
    body = await request.json()
    ids: list[uuid.UUID] | None = None
    if isinstance(body, dict) and body.get("everyone_else") is True and "ids" not in body:
        everyone = True
    else:
        everyone = False
        parsed = z.obj(ids=z.array(z.string().max(64)).min(1).max(500)).parse(body)
        ids = []
        for value in parsed["ids"]:
            try:
                ids.append(uuid.UUID(value))
            except ValueError:
                continue  # not one of ours: matches nothing
    async with db_session("write", **_scope(principal)) as db:
        ended = await revoke_sessions(db, principal.tenant.id, ids=ids, keep=principal.session_id)
        if ended:
            user = ended[0][1]
            await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                         action="auth.session.revoked", actor=Actor.user(principal.user),
                         resource={"type": "session", "id": None, "name": f"{user.first_name} {user.last_name}".strip()
                                   if len(ended) == 1 else f"{len(ended)} sessions"},
                         metadata={"cause": "signed_out_everyone" if everyone else "signed_out_by_admin",
                                   "sessions": str(len(ended))})
    return ok({"signed_out": len(ended)})


@router.get("/settings/security/activity", dependencies=[rate_limit("settings-activity", per_minute=60)])
async def security_activity(principal: Principal = Depends(require_admin)) -> Any:
    """Sign-in activity of the last 14 days, and the caller's address."""
    now = datetime.now(UTC)
    since = now - timedelta(days=14)
    async with db_session("read", **_scope(principal)) as db:
        events = await audit_queries.signin_activity(db, principal.tenant.id, since)
    days = [{"date": (since + timedelta(days=i + 1)).strftime("%Y-%m-%d"), "succeeded": 0, "failed": 0}
            for i in range(14)]
    by_date = {d["date"]: d for d in days}
    totals = {"succeeded": 0, "failed": 0, "blocked": 0, "locked": 0}
    for item in events:
        day = by_date.get(item.occurred_at.astimezone(UTC).strftime("%Y-%m-%d"))
        if item.action == "auth.login.succeeded":
            totals["succeeded"] += 1
            if day:
                day["succeeded"] += 1
            continue
        totals["blocked" if item.action == "auth.login.blocked" else "locked" if item.action == "auth.otp.locked"
               else "failed"] += 1
        if day:
            day["failed"] += 1
    ctx = get_context()
    recent = [{
        "id": str(item.id),
        "at": item.occurred_at.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "action": item.action, "outcome": item.outcome, "name": item.actor_name or "", "email": item.actor_email,
        "ip": (str(item.ip) if item.ip else "unknown").removeprefix("::ffff:"), "reason": item.reason,
    } for item in events[:8]]
    return ok({"my_ip": (ctx.client_ip if ctx else None) or "unknown", "days": days, "totals": totals, "recent": recent})


# ── Any section ───────────────────────────────────────────────────────────────────────

@router.get("/settings/{section}", dependencies=[rate_limit("settings-get", per_minute=120)])
async def get_one_section(section: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await get_section(db, principal.tenant.id, _section(section)))


async def _picture(db: Any, tenant_id: uuid.UUID, field: str, body: dict[str, Any], key: str,
                   current: str | None) -> str | None:
    """An upload id becomes its file address; null removes the picture; left out keeps it."""
    if key not in body:
        return current
    if body[key] is None:
        return None
    url = await completed_url(db, tenant_id, body[key])
    if url is None:
        raise FrmError("FRM-GEN-1002", [{"field": field, "message": "upload_again"}])
    return url


def _picture_change(field: str, a: str | None, b: str | None) -> list[dict[str, Any]]:
    """Pictures by what happened to them, never their addresses."""
    if a == b:
        return []
    return [{"field": field, "before": "set" if a else None, "after": ("replaced" if a else "uploaded") if b else "removed"}]


def _flat_security(value: dict[str, Any]) -> dict[str, Any]:
    entries = value["ip_allowlist"]["entries"]
    return {**value, "ip_allowlist": {"enabled": value["ip_allowlist"]["enabled"], "entries": [
        f"{e['value']} ({e['label']})" if e.get("label") else e["value"] for e in entries]}}


def _flat_emails(value: dict[str, Any]) -> dict[str, Any]:
    """Templates by which ones are the workspace's own, never their whole text."""
    return {"sender_name": value["sender_name"], "reply_to": value["reply_to"], "footer": value["footer"],
            **{f"template.{key}": ", ".join(sorted(langs or {})) or None for key, langs in value["custom"].items()}}


def _flat_notifications(value: dict[str, Any]) -> dict[str, Any]:
    """Rules by event, one line each."""
    def line(rule: dict[str, Any]) -> str:
        how = " + ".join(x for x in ("app" if rule["in_app"] else "", "email" if rule["email"] else "") if x) or "off"
        to = f"{len(rule['people'])} people" if rule["to"] == "people" else rule["to"]
        return f"{how} → {to}"
    return {"digest": value["digest"], **{key: line(rule) for key, rule in value["events"].items()}}


@router.patch("/settings/{section}", dependencies=[rate_limit("settings-patch", per_minute=30)])
async def patch_section(section: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    section = _section(section)
    raw = await request.json()
    value = schemas.SCHEMAS[section].parse(raw)
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        before = await get_section(db, tenant.id, section)
        if section == "branding":
            body = raw if isinstance(raw, dict) else {}
            value = {
                "logo_url": await _picture(db, tenant.id, "logo", body, "logo_upload_id", before.get("logo_url")),
                "logo_dark_url": await _picture(db, tenant.id, "logo_dark", body, "logo_dark_upload_id",
                                                before.get("logo_dark_url")),
                "favicon_url": await _picture(db, tenant.id, "favicon", body, "favicon_upload_id",
                                              before.get("favicon_url")),
                "brand_color": value["brand_color"].upper() if value["brand_color"] else None,
                "signin_message": value["signin_message"],
            }
            changes = [*(_picture_change(f, before.get(f), value[f]) for f in ("logo_url", "logo_dark_url", "favicon_url"))]
            changes = [c for group in changes for c in group] + settings_changes(
                {"brand_color": before.get("brand_color"), "signin_message": before.get("signin_message")},
                {"brand_color": value["brand_color"], "signin_message": value["signin_message"]})
        elif section == "signin":
            domain = principal.user.email.rsplit("@", 1)[-1].lower()
            if value["allowed_domains"] and not any(domain == d or domain.endswith(f".{d}") for d in value["allowed_domains"]):
                raise _locked_out("allowed_domains", "own_domain")
            # Google, Microsoft and Facebook come with Professional and up
            if any(m != "password" and m not in before["methods"] for m in value["methods"]):
                require_feature(tenant.plan_id, "social_signin")
            changes = settings_changes(before, value)
        elif section == "security":
            ctx = get_context()
            caller = (ctx.client_ip if ctx else None) or ""
            if value["ip_allowlist"]["enabled"] and not any(ip_in_cidr(caller, e["value"])
                                                            for e in value["ip_allowlist"]["entries"]):
                raise _locked_out("ip_allowlist", "own_ip")
            changes = settings_changes(_flat_security(before), _flat_security(value))
        elif section == "emails":
            flat_before, flat_after = _flat_emails(before), _flat_emails(value)
            for key in flat_before:
                flat_after.setdefault(key, None)
            changes = settings_changes(flat_before, flat_after)
        elif section == "notifications":
            changes = settings_changes(_flat_notifications(before), _flat_notifications(value))
        elif section == "form_defaults":
            if value["theme_id"] is not None:
                from app.modules.design.router import theme_for_new_form

                if await theme_for_new_form(db, tenant.id, value["theme_id"]) is None:
                    raise FrmError("FRM-GEN-1002", [{"field": "theme_id", "message": "theme"}])
            changes = settings_changes(before, value)
        else:
            changes = settings_changes(before, value)
        saved = await save_section(db, tenant.id, tenant.organisation_id, section, value, principal.user.id)
        if section == "company":
            organisation = await db.get(Organisation, tenant.organisation_id)
            if organisation is not None:
                organisation.name = value["display_name"]
        if changes:
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="settings.updated",
                         actor=Actor.user(principal.user), resource={"type": "setting", "id": None,
                                                                     "name": LABELS[section]}, changes=changes)
        if section == "privacy":
            # Retention runs when the setting is saved, then once a day (the mock's applyRetention)
            from app.modules.privacy.service import apply_retention

            await apply_retention(db, tenant.id, tenant.organisation_id, principal.user)
    return ok(saved)

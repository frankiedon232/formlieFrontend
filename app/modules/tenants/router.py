"""Workspace routes before sign-in (mock: server/mock/routes/tenants.ts): the public profile of this host,
subdomain availability, and find my workspace (email → code → the workspaces it belongs to)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.middleware.tenant import RESERVED_SUBDOMAINS, current_host_context, is_valid_subdomain
from app.core.responses import ok
from app.core.validation import Email
from app.core.security.limits import per_value, rate_limit
from app.modules.auth import challenges
from app.modules.billing.service import has_feature
from app.modules.emails import service as emails
from app.modules.settings.service import SIGNIN_METHODS, get_section
from app.modules.users.identities import linked_providers, offered_methods

router = APIRouter(tags=["tenants"])

ALL_PROVIDERS = list(SIGNIN_METHODS)  # manage.* offers every method for the first sign-up


def host_port() -> str:
    """The port the browser used (development: :2202 through the Nuxt proxy), for links to other subdomains."""
    ctx = get_context()
    host = (ctx.host or "") if ctx else ""
    if host.startswith("[") or host.count(":") != 1:
        return ""
    port = host.rsplit(":", 1)[1]
    return f":{port}" if port.isdigit() and port != "443" else ""


def workspace_url(subdomain: str, path: str) -> str:
    return f"https://{subdomain}.{get_settings().root_domain}{host_port()}{path}"


@router.get("/tenants/public")
async def public_profile() -> Any:
    """What the sign-in page of this host may show (no secrets): manage.* offers every provider for the first
    sign-up; a workspace shows its name, branding, enabled methods (as far as its plan allows) and password rules."""
    ctx = get_context()
    host = current_host_context()
    if host is not None and host.kind == "manage":
        return ok({"mode": "manage", "name": "Formalie", "subdomain": "manage", "logo_url": None,
                   "colors": {"primary": None}, "auth_providers": ALL_PROVIDERS, "status": "active"})
    tenant = ctx.tenant if ctx else None
    if tenant is None:
        raise FrmError("FRM-TEN-1001")
    async with db_session("read", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        company = await get_section(db, tenant.id, "company")
        branding = await get_section(db, tenant.id, "branding")
        signin = await get_section(db, tenant.id, "signin")
        security = await get_section(db, tenant.id, "security")
        linked = await linked_providers(db, tenant.id)
    rules = security["password"]
    return ok({
        "mode": "tenant",
        "name": company.get("display_name") or tenant.name,
        "subdomain": tenant.subdomain,
        "logo_url": branding.get("logo_url"),
        "logo_dark_url": branding.get("logo_dark_url"),
        "favicon_url": branding.get("favicon_url"),
        "signin_message": branding.get("signin_message"),
        "colors": {"primary": branding.get("brand_color")},
        "website": company.get("website"),
        # Social methods while the plan has them, and always the ones people here already sign in with
        "auth_providers": offered_methods(signin, tenant.plan_id, linked),
        "sso": None,  # single sign-on connections arrive in B11 (settings/sso)
        "password_policy": {k: rules[k] for k in ("min_length", "lower", "upper", "number", "symbol")},
        "status": tenant.status if tenant.status in ("active", "suspended") else "active",
    })


@router.get("/tenants/subdomain-availability", dependencies=[rate_limit("subdomain-availability", per_minute=60)])
async def subdomain_availability(subdomain: str = "") -> Any:
    value = subdomain.strip().lower()
    reason = None
    if value in RESERVED_SUBDOMAINS:
        reason = "reserved"
    elif not is_valid_subdomain(value) or len(value) < 3:
        reason = "invalid"
    else:
        async with db_session("read") as db:
            if (await db.execute(text("SELECT platform.subdomain_taken(:s)"), {"s": value})).scalar():
                reason = "taken"
    return ok({"available": reason is None, "reason": reason})


class EmailBody(BaseModel):
    email: Email


@router.post("/tenants/find-workspace", dependencies=[rate_limit("find-workspace", per_minute=10)])
async def find_workspace(body: EmailBody) -> Any:
    """Always answers the same, whether or not the address has an account (no account discovery)."""
    await per_value("find-workspace", body.email, limit=5, window_seconds=600)
    challenge, code = await challenges.create_challenge(purpose="find", email=str(body.email), channel="email",
                                                        channels=["email"])
    emails.send(str(body.email), "signin_code", None, {"workspace": "Formalie", "name": "", "code": code,
                                                         "minutes": challenge.ttl_ms // 60_000})
    return ok(challenges.describe(challenge))


class VerifyBody(BaseModel):
    challenge_id: str = Field(max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


async def workspaces_for(email: str) -> list[dict[str, str]]:
    """Every active workspace this (already verified) email belongs to, with a link to its sign-in page."""
    async with db_session("read") as db:
        rows = (await db.execute(text("SELECT name, subdomain FROM platform.workspaces_for_email(:e)"),
                                 {"e": email})).all()
    return [{"name": name, "subdomain": sub, "url": workspace_url(sub, f"/auth/login?email={quote(email)}")}
            for name, sub in rows]


@router.post("/tenants/find-workspace/verify", dependencies=[rate_limit("find-workspace-verify", per_minute=20)])
async def find_workspace_verify(body: VerifyBody) -> Any:
    """Every active workspace this email belongs to, with a link to its sign-in page."""
    challenge = await challenges.verify_code(body.challenge_id, body.code, "find")
    await challenges.consume(challenge.id)
    return ok(await workspaces_for(challenge.email))

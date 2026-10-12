"""Workspace address and own domain (port of the mock's routes/address.ts; API-CONTRACT → Settings). Admins only.

    GET    /settings/address                     subdomain, portal address, old addresses, own domain
    POST   /settings/address/subdomain           { subdomain, confirm } (confirm = the new subdomain again)
    PUT    /settings/address/domain              { domain } → the DNS records to add
    POST   /settings/address/domain/check        looks the records up in DNS (really) → status
    DELETE /settings/address/domain

The old subdomain keeps leading here for 90 days (`platform.change_subdomain`, the tenant directory). A verified own
domain is claimed in the directory and then answers like the subdomain (TenantDirectory.by_domain) while the plan
includes it. Every change is in the audit trail (`settings.updated`, "Address and domain").
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core import dns
from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.ids import uuid7
from app.core.middleware.tenant import is_valid_subdomain
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.address.models import CustomDomain
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.billing.service import require_feature
from app.modules.tenants.service import TenantDirectory

router = APIRouter(tags=["address"])

DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None


async def _body(request: Request) -> Any:
    raw = await request.body()
    return (await request.json()) if raw else None


async def _audit(db: Any, principal: Principal, field: str, before: Any, after: Any) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                 action="settings.updated", actor=Actor.user(principal.user),
                 resource={"type": "setting", "id": None, "name": "Address and domain"},
                 changes=[{"field": field, "before": before, "after": after}])


async def _domain_row(db: Any, tenant_id: Any) -> CustomDomain | None:
    return (await db.execute(select(CustomDomain).where(CustomDomain.tenant_id == tenant_id,
                                                        CustomDomain.deleted_at.is_(None)))).scalar_one_or_none()


def _domain_view(row: CustomDomain | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {"domain": row.domain, "status": row.status, "records": row.records, "added_at": _iso(row.added_at),
            "checked_at": _iso(row.checked_at), "problem": row.problem}


async def _view(db: Any, principal: Principal) -> dict[str, Any]:
    subdomain = (await db.execute(text("SELECT subdomain FROM platform.tenant_profile()"))).scalar_one()
    previous = (await db.execute(text("SELECT subdomain, until FROM platform.subdomain_history_of()"))).all()
    return {"subdomain": subdomain, "url": f"https://{subdomain}.{get_settings().root_domain}",
            "previous": [{"subdomain": s, "until": _iso(until)} for s, until in previous],
            "domain": _domain_view(await _domain_row(db, principal.tenant.id))}


@router.get("/settings/address", dependencies=[rate_limit("settings-address", per_minute=120)])
async def get_address(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await _view(db, principal))


subdomain_schema = z.obj(subdomain=z.string().trim().lower().min(3).max(63), confirm=z.string().trim().lower())


@router.post("/settings/address/subdomain", dependencies=[rate_limit("settings-address-subdomain", per_minute=10)])
async def change_subdomain(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = subdomain_schema.parse(await _body(request))
    if body["confirm"] != body["subdomain"]:
        raise FrmError("FRM-GEN-1002", [{"field": "confirm", "message": "confirm"}])
    new = body["subdomain"]
    if not is_valid_subdomain(new):
        raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "invalid"}])
    async with db_session("write", **_scope(principal)) as db:
        current = (await db.execute(text("SELECT subdomain FROM platform.tenant_profile()"))).scalar_one()
        if new == current:
            return ok(await _view(db, principal))
        try:
            async with db.begin_nested():
                # Its own old address may come back; anything else in use (now or as someone's old one) is taken
                await db.execute(text("SELECT platform.change_subdomain(:new, :id)"), {"new": new, "id": uuid7()})
        except DBAPIError:
            raise FrmError("FRM-TEN-1004", [{"field": "subdomain", "message": "taken"}]) from None
        await _audit(db, principal, "subdomain", current, new)
        view = await _view(db, principal)
    directory = TenantDirectory()
    for name in (current, new):
        await directory.forget(name)
    return ok(view)


def _clean_domain(value: str) -> str:
    return re.sub(r"\.$", "", re.sub(r"/.*$", "", re.sub(r"^https?://", "", value)))


domain_schema = z.obj(domain=z.string().trim().lower().transform(_clean_domain))


@router.put("/settings/address/domain", dependencies=[rate_limit("settings-address", per_minute=30)])
async def add_domain(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    require_feature(principal.tenant.plan_id, "custom_domain")
    domain = domain_schema.parse(await _body(request))["domain"]
    root = get_settings().root_domain
    if not DOMAIN.match(domain) or domain == root or domain.endswith(f".{root}") or domain.endswith(".formalie.com"):
        raise FrmError("FRM-GEN-1002", [{"field": "domain", "message": "domain"}])
    token = f"formalie-verify={secrets.token_hex(12)}"
    async with db_session("write", **_scope(principal)) as db:
        old = await _domain_row(db, principal.tenant.id)
        if old is not None:
            old.soft_delete(principal.user.id)
            await db.execute(text("SELECT platform.release_domain(:d)"), {"d": old.domain})
            await db.flush()
        db.add(CustomDomain(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                            domain=domain, status="pending", token=token, created_by=principal.user.id,
                            records=[{"type": "CNAME", "name": domain, "value": f"custom.{root}", "found": False},
                                     {"type": "TXT", "name": f"_formalie.{domain}", "value": token, "found": False}]))
        await db.flush()
        await _audit(db, principal, "domain", None, domain)
        view = await _view(db, principal)
    if old is not None:
        await TenantDirectory().forget_domain(old.domain)
    return ok(view)


@router.post("/settings/address/domain/check", dependencies=[rate_limit("settings-address-check", per_minute=20)])
async def check_domain(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        row = await _domain_row(db, principal.tenant.id)
        if row is None:
            raise FrmError("FRM-GEN-1004")
        domain, token, records = row.domain, row.token, [dict(r) for r in row.records]
    cname, txt = records[0], records[1]
    try:  # outside the transaction: DNS can be slow
        targets = [dns.clean(t) for t in await dns.lookup(cname["name"], "CNAME")]
        cname["found"] = cname["value"] in targets
        txt["found"] = token in await dns.lookup(txt["name"], "TXT")
        problem = None if cname["found"] and txt["found"] else ("wrong_target" if targets and not cname["found"]
                                                               else "not_found")
    except dns.DnsError:
        problem = "dns_error"
    status = ("failed" if problem == "wrong_target" else "pending") if problem else "verified"
    async with db_session("write", **_scope(principal)) as db:
        row = await _domain_row(db, principal.tenant.id)
        if row is None or row.domain != domain:
            raise FrmError("FRM-GEN-1004")
        before = row.status
        row.records, row.status, row.problem = records, status, problem
        row.checked_at, row.updated_by = datetime.now(UTC), principal.user.id
        # Proven by its DNS records: this workspace answers on it now (whoever held it before)
        await db.execute(text("SELECT platform.claim_domain(:d)" if status == "verified"
                              else "SELECT platform.release_domain(:d)"), {"d": domain})
        await db.flush()
        if before != status:
            await _audit(db, principal, "domain_status", before, status)
        view = await _view(db, principal)
    await TenantDirectory().forget_domain(domain)
    return ok(view)


@router.delete("/settings/address/domain", dependencies=[rate_limit("settings-address", per_minute=30)])
async def remove_domain(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        row = await _domain_row(db, principal.tenant.id)
        if row is not None:
            row.soft_delete(principal.user.id)
            await db.execute(text("SELECT platform.release_domain(:d)"), {"d": row.domain})
            await db.flush()
            await _audit(db, principal, "domain", row.domain, None)
        view = await _view(db, principal)
    if row is not None:
        await TenantDirectory().forget_domain(row.domain)
    return ok(view)

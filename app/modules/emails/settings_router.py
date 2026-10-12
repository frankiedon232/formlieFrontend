"""Settings → Emails (port of the mock's routes/emails.ts and routes/emailSending.ts). Admins only.

    GET    /settings/emails/templates/{key}?language=   default and own text, the placeholders
    POST   /settings/emails/preview                    { key, language, subject, body } → rendered with sample values
    POST   /settings/emails/test                       the same, sent to the admin (lands in the sent log)
    GET    /settings/emails/sent?q=&page=&page_size=   the sent log, newest first (no bodies)
    GET    /settings/emails/sent/{id}                  one email with its HTML and text

    GET    /settings/emails/sending                    mode, the address used now, own domain, own mail server
    PUT    /settings/emails/sending/domain             { address } → the DNS records to add
    POST   /settings/emails/sending/domain/check       looks the records up in DNS (really) → status
    DELETE /settings/emails/sending/domain
    PUT    /settings/emails/sending/smtp               SmtpSaveRequest (password write-only)
    POST   /settings/emails/sending/smtp/test          connects, signs in, checks sender and recipient (really)
    DELETE /settings/emails/sending/smtp
    POST   /settings/emails/sending/mode               { mode } (domain: verified first; smtp: working first)

Every change to the sending address is audited (`settings.updated`, resource "Sending address").
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.core import outbound
from app.core import zod as z
from app.core.config import get_settings
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.core.validation import ZOD_EMAIL
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.billing.service import require_feature
from app.modules.emails import sending
from app.modules.emails import workspace as mail
from app.modules.emails.catalogue import EMAIL_VARIABLES
from app.modules.emails.models import SentEmail
from app.modules.settings.catalogues import EMAIL_TEMPLATES
from app.modules.settings.schemas import email_text
from app.modules.settings.service import get_section
from app.modules.tenants.router import workspace_url

router = APIRouter(tags=["emails"])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _key(value: str | None) -> str:
    if not value or value not in EMAIL_TEMPLATES:
        raise FrmError("FRM-GEN-1004")
    return value


async def _body(request: Request) -> Any:
    raw = await request.body()
    return (await request.json()) if raw else None


# ── Templates, preview, test, the sent log ──────────────────────────────────────────

@router.get("/settings/emails/templates/{key}", dependencies=[rate_limit("settings-emails", per_minute=120)])
async def get_template(key: str, language: str | None = None, principal: Principal = Depends(require_admin)) -> Any:
    key = _key(key)
    async with db_session("read", **_scope(principal)) as db:
        lang = await mail.email_language(db, principal.tenant.id, language)
        custom = ((await get_section(db, principal.tenant.id, "emails")).get("custom") or {}).get(key, {}).get(lang)
    return ok({"key": key, "language": lang, "default": mail.defaults(lang)["templates"][key], "custom": custom or None,
               "variables": EMAIL_VARIABLES[key]})


async def _sample(db: Any, principal: Principal, key: str, language: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Believable values for a preview or test, in the email's language (the mock's sampleValues)."""
    texts = mail.defaults(language)
    user = principal.user
    form = "Customer feedback"
    new = texts["events"]["response_new"]
    values: dict[str, Any] = {
        "name": user.first_name, "code": "483921", "minutes": 5, "inviter": f"{user.first_name} {user.last_name}".strip(),
        "form": form, "number": 128, "days": 30 if key == "resume_link" else 7,
        "reason": "Only people from our organisation can join this workspace.",
        "date": await mail.email_date(db, principal.tenant.id, language),
        "link": workspace_url(principal.tenant.subdomain, "/auth/login" if key == "invitation" else "/"),
        "title": new["title"].replace("{{form}}", form), "message": new["message"].replace("{{form}}", form),
        "summary": "\n".join([new["title"].replace("{{form}}", form), texts["events"]["export_ready"]["title"]]),
    }
    answers = [{"label": "Full name", "value": "Ada Visitor"}, {"label": "Email", "value": "ada@example.com"},
               {"label": "How likely are you to recommend us?", "value": "9"},
               {"label": "Anything else?", "value": "Quick and friendly service."}] \
        if key in ("response_notification", "response_receipt") else []
    return values, answers


preview_schema = z.obj(subject=email_text.shape["subject"], body=email_text.shape["body"],
                       key=z.enum(list(EMAIL_TEMPLATES)), language=z.string().max(10))


@router.post("/settings/emails/preview", dependencies=[rate_limit("settings-emails-preview", per_minute=60)])
async def preview_email(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = preview_schema.parse(await _body(request))
    async with db_session("read", **_scope(principal)) as db:
        lang = await mail.email_language(db, principal.tenant.id, body["language"])
        values, answers = await _sample(db, principal, body["key"], lang)
        rendered = await mail.render(db, principal.tenant.id, principal.tenant.name, body["key"], lang, values,
                                     text={"subject": body["subject"], "body": body["body"]}, answers=answers,
                                     footer="form" if body["key"] == "response_receipt" else "account")
        row = await sending.row_of(db, principal.tenant.id)
    address = sending.from_address(row, principal.tenant.plan_id)
    return ok({"subject": rendered["subject"], "html": rendered["html"], "from": f"{rendered['from_name']} <{address}>",
               "reply_to": rendered["reply_to"] or None})


@router.post("/settings/emails/test", dependencies=[rate_limit("settings-emails-test", per_minute=10)])
async def test_email(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    body = preview_schema.parse(await _body(request))
    async with db_session("write", **_scope(principal)) as db:
        lang = await mail.email_language(db, principal.tenant.id, body["language"])
        values, answers = await _sample(db, principal, body["key"], lang)
        sent = await mail.send(db, principal.tenant.id, principal.tenant.name, to=principal.user.email, key=body["key"],
                               values=values, reason="test", language=lang, answers=answers,
                               text={"subject": body["subject"], "body": body["body"]},
                               footer="form" if body["key"] == "response_receipt" else "account")
        if not sent or not sent.get("id"):
            raise FrmError("FRM-GEN-5000")
    return ok(sent)


def _like(q: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", q) + "%"


@router.get("/settings/emails/sent", dependencies=[rate_limit("settings-emails-sent", per_minute=120)])
async def list_sent(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = request.query_params
    params = PageParams.from_query(query.get("page"), query.get("page_size") or query.get("per_page"))
    q = (query.get("q") or "").strip().lower()
    where = [SentEmail.tenant_id == principal.tenant.id, SentEmail.deleted_at.is_(None)]
    if q:
        where.append((SentEmail.to_email + " " + func.lower(SentEmail.subject)).like(_like(q), escape="\\"))
    async with db_session("read", **_scope(principal)) as db:
        total = (await db.execute(select(func.count()).select_from(SentEmail).where(*where))).scalar_one()
        rows = (await db.execute(select(SentEmail).where(*where).order_by(SentEmail.sent_at.desc(), SentEmail.id.desc())
                                 .offset(params.offset).limit(params.page_size))).scalars().all()
    return ok([mail.sent_item(r) for r in rows], params.meta(total))


@router.get("/settings/emails/sent/{sent_id}", dependencies=[rate_limit("settings-emails-sent", per_minute=120)])
async def get_sent(sent_id: str, principal: Principal = Depends(require_admin)) -> Any:
    try:
        wanted = uuid.UUID(sent_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    async with db_session("read", **_scope(principal)) as db:
        row = (await db.execute(select(SentEmail).where(SentEmail.tenant_id == principal.tenant.id,
                                                        SentEmail.id == wanted, SentEmail.deleted_at.is_(None))
                                )).scalar_one_or_none()
    if row is None:
        raise FrmError("FRM-GEN-1004")
    return ok(mail.sent_item(row, with_bodies=True))


# ── Where emails come from ──────────────────────────────────────────────────────────

async def _audit(db: Any, principal: Principal, field: str, before: Any, after: Any) -> None:
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                 action="settings.updated", actor=Actor.user(principal.user),
                 resource={"type": "setting", "id": None, "name": "Sending address"},
                 changes=[{"field": field, "before": before, "after": after}])


@router.get("/settings/emails/sending", dependencies=[rate_limit("settings-sending", per_minute=120)])
async def get_sending(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(sending.view(await sending.row_of(db, principal.tenant.id), principal.tenant.plan_id))


def _is_email(value: str) -> bool:
    return bool(ZOD_EMAIL.match(value))


address_schema = z.obj(address=z.string().trim().lower().max(200).refine(_is_email, "Invalid email address"))


@router.put("/settings/emails/sending/domain", dependencies=[rate_limit("settings-sending", per_minute=30)])
async def add_sending_domain(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    require_feature(principal.tenant.plan_id, "custom_email")
    address = address_schema.parse(await _body(request))["address"]
    domain = address.rsplit("@", 1)[-1]
    if sending.blocked_domain(domain):
        raise FrmError("FRM-GEN-1002", [{"field": "address", "message": "domain"}])
    key, records = sending.domain_records(domain)
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_for_change(db, principal.tenant.id, principal.tenant.organisation_id, principal.user.id)
        before = (row.domain or {}).get("address")
        row.domain = {"address": address, "domain": domain, "status": "pending", "records": records,
                      "added_at": sending.iso(), "checked_at": None, "problem": None, "key": key}
        row.updated_by = principal.user.id
        sending.settle(row)
        await _audit(db, principal, "sending_domain", before, address)
        await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


@router.post("/settings/emails/sending/domain/check", dependencies=[rate_limit("settings-sending-check", per_minute=20)])
async def check_sending_domain(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        entry = dict(row.domain) if row is not None and row.domain else None
    if entry is None:
        raise FrmError("FRM-GEN-1004")
    records, problem = await sending.check_records(entry["records"])  # outside the transaction: DNS can be slow
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        if row is None or not row.domain or row.domain.get("address") != entry["address"]:
            raise FrmError("FRM-GEN-1004")
        before = row.domain.get("status")
        status = ("failed" if problem == "wrong_value" else "pending") if problem else "verified"
        row.domain = {**row.domain, "records": records, "status": status, "problem": problem,
                      "checked_at": sending.iso()}
        row.updated_by = principal.user.id
        sending.settle(row)
        if before != status:
            await _audit(db, principal, "sending_domain_status", before, status)
        await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


@router.delete("/settings/emails/sending/domain", dependencies=[rate_limit("settings-sending", per_minute=30)])
async def remove_sending_domain(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        if row is not None and row.domain:
            address = row.domain.get("address")
            row.domain, row.updated_by = None, principal.user.id
            sending.settle(row)
            await _audit(db, principal, "sending_domain", address, None)
            await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


_HOST = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

smtp_schema = z.obj(
    host=z.string().trim().lower().max(253).refine(lambda v: bool(_HOST.match(v)), "host"),
    port=z.number().int().min(1).max(65535),
    security=z.enum(["starttls", "tls", "none"]),
    username=z.string().trim().max(200).nullable().transform(lambda v: v or None),
    password=z.string().max(500).nullable().optional(),
    from_address=z.string().trim().lower().max(200).refine(_is_email, "Invalid email address"),
)


@router.put("/settings/emails/sending/smtp", dependencies=[rate_limit("settings-sending", per_minute=30)])
async def save_smtp(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    require_feature(principal.tenant.plan_id, "custom_email")
    raw = await _body(request)
    body = smtp_schema.parse(raw)
    # A new one replaces (null or empty removes it); left out keeps the one there
    password_given = "password" in raw
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_for_change(db, principal.tenant.id, principal.tenant.organisation_id, principal.user.id)
        current = dict(row.smtp) if row.smtp else None
        if password_given:
            row.smtp_password_enc = sending.encrypt_password(body.get("password") or None)
        changed = current is None or password_given or any(
            current.get(k) != body[k] for k in ("host", "port", "security", "username"))
        row.smtp = {
            "host": body["host"], "port": body["port"], "security": body["security"], "username": body["username"],
            "has_password": bool(row.smtp_password_enc), "from_address": body["from_address"],
            # A different server or sign-in needs a new test
            "status": "untested" if changed else current.get("status", "untested"),  # type: ignore[union-attr]
            "checked_at": None if changed else current.get("checked_at"),  # type: ignore[union-attr]
            "problem": None if changed else current.get("problem"),  # type: ignore[union-attr]
        }
        row.updated_by = principal.user.id
        sending.settle(row)
        await _audit(db, principal, "smtp_server", f"{current['host']}:{current['port']}" if current else None,
                     f"{body['host']}:{body['port']}")
        await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


@router.post("/settings/emails/sending/smtp/test", dependencies=[rate_limit("settings-sending-check", per_minute=20)])
async def test_smtp(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        server = dict(row.smtp) if row is not None and row.smtp else None
        password = sending.password_of(row.smtp_password_enc) if row is not None else None
    if server is None:
        raise FrmError("FRM-GEN-1004")
    try:
        address = await outbound.public_address(server["host"], server["port"], allow_local=outbound.local_allowed(
            get_settings().email_smtp_allow_local))
        problem = await asyncio.to_thread(sending.probe, address, server["host"], server["port"], server["security"],
                                          server.get("username"), password, server["from_address"],
                                          principal.user.email)
    except (outbound.Refused, outbound.Unresolved):
        problem = "unreachable"
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        if row is None or not row.smtp:
            raise FrmError("FRM-GEN-1004")
        before = row.smtp.get("status")
        status = "failed" if problem else "working"
        row.smtp = {**row.smtp, "status": status, "problem": problem,
                    "checked_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
        row.updated_by = principal.user.id
        sending.settle(row)
        if before != status:
            await _audit(db, principal, "smtp_status", before, status)
        await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


@router.delete("/settings/emails/sending/smtp", dependencies=[rate_limit("settings-sending", per_minute=30)])
async def remove_smtp(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_of(db, principal.tenant.id)
        if row is not None and row.smtp:
            before = f"{row.smtp['host']}:{row.smtp['port']}"
            row.smtp, row.smtp_password_enc, row.updated_by = None, None, principal.user.id
            sending.settle(row)
            await _audit(db, principal, "smtp_server", before, None)
            await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))


mode_schema = z.obj(mode=z.enum(["formalie", "domain", "smtp"]))


@router.post("/settings/emails/sending/mode", dependencies=[rate_limit("settings-sending", per_minute=30)])
async def set_sending_mode(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    mode = mode_schema.parse(await _body(request))["mode"]
    if mode != "formalie":
        require_feature(principal.tenant.plan_id, "custom_email")
    async with db_session("write", **_scope(principal)) as db:
        row = await sending.row_for_change(db, principal.tenant.id, principal.tenant.organisation_id, principal.user.id)
        if (mode == "domain" and (row.domain or {}).get("status") != "verified") or \
                (mode == "smtp" and (row.smtp or {}).get("status") != "working"):
            raise FrmError("FRM-SET-1001", [{"field": "mode", "message": mode}])
        before = row.mode
        row.mode, row.updated_by = mode, principal.user.id
        sending.settle(row)
        if before != mode:
            await _audit(db, principal, "sending_mode", before, mode)
        await db.flush()
        return ok(sending.view(row, principal.tenant.plan_id))

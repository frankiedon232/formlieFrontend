"""My profile (mock: routes/me.ts, API-CONTRACT → My profile): every signed-in person, about themselves.

    GET    /me/profile                  MyProfile
    PATCH  /me/profile                  { first_name?, last_name?, photo?, language?, time_zone?, date_format?, notifications? }
    POST   /me/password                 { current, password } (the workspace's password rules)
    POST   /me/two-step/app             → { secret, uri } to scan; confirmed by
    POST   /me/two-step/app/confirm     { code } → { recovery_codes } (shown once)
    POST   /me/two-step/app/remove      { password }
    POST   /me/two-step/recovery        { password } → { recovery_codes } (the old ones stop working)
    POST   /me/two-step/phone           { phone } → a code by text message
    POST   /me/two-step/phone/confirm   { code }
    DELETE /me/two-step/phone
    GET    /me/sessions · DELETE /me/sessions/{id} · POST /me/sessions/sign-out-others
    GET · PATCH /me/tours               tips on new pages

The photo arrives as a small data URL, like the mock's; it is kept as an upload (purpose `avatar`) and shown by its
file address. The pending authenticator secret and phone code wait in Redis (15 and 10 minutes).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import pyotp
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import storage
from app.core import zod as z
from app.core.cache.redis import get_redis
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.fernet_tokens import encrypt_secret
from app.core.security.limits import rate_limit
from app.core.security.passwords import hash_password, verify_password
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, active_sessions, require_auth, revoke_sessions
from app.modules.notifications import sms
from app.modules.people import service
from app.modules.settings.catalogues import DATE_FORMATS
from app.modules.settings.schemas import is_time_zone
from app.modules.settings.service import get_section
from app.modules.uploads.models import Upload
from app.modules.uploads.service import looks_like
from app.modules.users.models import User, UserPasswordHistory, UserRecoveryCode, UserTour, UserTwoStep

router = APIRouter(tags=["me"])

NOTIFICATIONS = ("responses", "digest", "mentions", "product")
NOTIFY_DEFAULTS = {"responses": True, "digest": False, "mentions": True, "product": False}
PENDING = "fm:v1:me:"
_PHONE = r"^\+[1-9][\d\s-]{6,18}$"

profile_schema = z.obj(
    first_name=z.string().trim().min(1).max(60).optional(),
    last_name=z.string().trim().min(1).max(60).optional(),
    photo=z.string().max(280_000).regex(r"^data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$").nullable().optional(),
    language=z.string().max(10).nullable().optional(),
    time_zone=z.string().max(64).refine(is_time_zone).nullable().optional(),
    date_format=z.enum(DATE_FORMATS).nullable().optional(),
    notifications=z.obj({k: z.boolean().optional() for k in NOTIFICATIONS}).optional(),
)
password_schema = z.obj(current=z.string().min(1).max(200), password=z.string().min(1).max(200))
code_schema = z.obj(code=z.string().trim().regex(r"^\d{6}$"))
password_only = z.obj(password=z.string().min(1).max(200))
phone_schema = z.obj(phone=z.string().trim().regex(_PHONE))
tours_schema = z.obj(seen=z.string().trim().min(1).max(60).optional(), enabled=z.boolean().optional(),
                     reset=z.literals([True]).optional())


def mask_phone(phone: str) -> str:
    """"+44 •••• ••0001": the country code and the last four digits."""
    digits = re.sub(r"\D", "", phone)
    return f"+{digits[:2]} {'•' * max(0, len(digits) - 6)}{digits[-4:]}"


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _hash_recovery(code: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", "", code.strip().lower()).encode()).hexdigest()


async def _two_step(db: Any, user: User) -> UserTwoStep | None:
    return (await db.execute(select(UserTwoStep).where(UserTwoStep.tenant_id == user.tenant_id,
                                                       UserTwoStep.user_id == user.id,
                                                       UserTwoStep.deleted_at.is_(None)))).scalar_one_or_none()


async def _recovery_left(db: Any, user: User) -> int:
    return len((await db.execute(select(UserRecoveryCode.id).where(
        UserRecoveryCode.tenant_id == user.tenant_id, UserRecoveryCode.user_id == user.id,
        UserRecoveryCode.used_at.is_(None), UserRecoveryCode.deleted_at.is_(None)))).all())


async def _profile(db: Any, principal: Principal) -> dict[str, Any]:
    user = await db.get(User, principal.user.id)
    row = (await service.rows_of(db, user.tenant_id, only=user.id))[0]
    two_step = await _two_step(db, user)
    sms_on = bool((await get_section(db, user.tenant_id, "signin"))["code"].get("sms"))
    return {
        "id": str(user.id), "first_name": user.first_name, "last_name": user.last_name, "email": user.email,
        "photo": row["photo"], "language": user.language, "time_zone": user.time_zone, "date_format": user.date_format,
        "role": row["role"], "role_name": row["role_name"], "departments": row["departments"],
        "job_titles": row["job_titles"], "manager": row["manager"],
        "password_changed_at": service.iso(user.password_changed_at),
        "two_step": {"app": bool(two_step and two_step.totp_confirmed_at),
                     "recovery_left": await _recovery_left(db, user),
                     "phone": mask_phone(user.phone) if user.phone and two_step and two_step.sms_confirmed_at else None,
                     "sms_allowed": sms_on},
        "notifications": {**NOTIFY_DEFAULTS, **{k: v for k, v in (user.notifications or {}).items() if k in NOTIFICATIONS}},
    }


async def _audit(db: Any, principal: Principal, action: str, metadata: dict[str, str] | None = None) -> None:
    user = principal.user
    await record(db, tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, action=action,
                 actor=Actor.user(user), metadata=metadata or {},
                 resource={"type": "user", "id": str(user.id), "name": f"{user.first_name} {user.last_name}".strip()})


@router.get("/me/profile", dependencies=[rate_limit("me-get", per_minute=120)])
async def get_profile(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await _profile(db, principal))


async def _store_photo(db: Any, user: User, data_url: str) -> uuid.UUID:
    """A profile photo (data URL) kept as a finished upload; the bytes must be the image they say they are."""
    head, _, payload = data_url.partition(",")
    content_type = head[len("data:"):-len(";base64")]
    raw = base64.b64decode(payload, validate=False)
    if not looks_like(content_type, raw):
        raise FrmError("FRM-GEN-1002", [{"field": "photo", "message": "Invalid image"}])
    now = datetime.now(UTC)
    upload = Upload(tenant_id=user.tenant_id, organisation_id=user.organisation_id, purpose="avatar",
                    file_name="photo", content_type=content_type, size=len(raw), max_bytes=len(raw),
                    expires_at=now, stored_at=now, completed_at=now, scan_status="clean", created_by=user.id)
    db.add(upload)
    await db.flush()
    upload.file_key = storage.key_for(user.tenant_id, user.organisation_id, "avatars", upload.id)
    storage.put(upload.file_key, raw)
    return upload.id


@router.patch("/me/profile", dependencies=[rate_limit("me-update", per_minute=30)])
async def update_profile(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = profile_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        fields = []
        for key in ("first_name", "last_name", "language", "time_zone", "date_format"):
            if key in body:
                setattr(user, key, body[key])
                fields.append(key)
        if "photo" in body:
            user.photo_upload_id = await _store_photo(db, user, body["photo"]) if body["photo"] else None
            fields.append("photo")
        if "notifications" in body:
            user.notifications = {**(user.notifications or {}), **body["notifications"]}
            fields.append("notifications")
        principal.user = user
        await _audit(db, principal, "users.profile_updated", {"fields": ", ".join(fields)})
        await db.flush()
        return ok(await _profile(db, principal))


async def _check_password(user: User, value: str, field: str) -> None:
    if not user.password_hash or not verify_password(user.password_hash, value):
        raise FrmError("FRM-AUTH-1001", [{"field": field, "message": "wrong"}])


@router.post("/me/password", dependencies=[rate_limit("me-password", per_minute=10)])
async def change_password(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.auth.router import check_new_password

    body = password_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        await _check_password(user, body["current"], "current")
        await check_new_password(db, principal.tenant, user, body["password"])
        db.add(UserPasswordHistory(tenant_id=user.tenant_id, organisation_id=user.organisation_id, user_id=user.id,
                                   password_hash=user.password_hash))
        user.password_hash, user.password_changed_at = hash_password(body["password"]), datetime.now(UTC)
        user.must_change_password = False
        # Other devices sign in again with the new password
        await revoke_sessions(db, user.tenant_id, ids=None, keep=principal.session_id, user_id=user.id,
                              reason="password_changed")
        await _audit(db, principal, "auth.password.changed")
    return ok({"changed": True})


# ── Two-step sign-in ─────────────────────────────────────────────────────────────

async def _pending(kind: str, user_id: uuid.UUID, value: dict[str, Any] | None = None, ttl: int = 900) -> Any:
    key = f"{PENDING}{kind}:{user_id}"
    if value is None:
        raw = await get_redis().get(key)
        return json.loads(raw) if raw else None
    await get_redis().set(key, json.dumps(value), ex=ttl)
    return value


async def _forget(kind: str, user_id: uuid.UUID) -> None:
    await get_redis().delete(f"{PENDING}{kind}:{user_id}")


async def _new_recovery(db: Any, user: User) -> list[str]:
    """Ten codes like "k7q2-9xmd", shown once; only their hashes are kept. The old set stops working."""
    now = datetime.now(UTC)
    for row in (await db.execute(select(UserRecoveryCode).where(
            UserRecoveryCode.tenant_id == user.tenant_id, UserRecoveryCode.user_id == user.id,
            UserRecoveryCode.deleted_at.is_(None)))).scalars():
        row.deleted_at = now
    codes = []
    for _ in range(10):
        raw = secrets.token_hex(4)
        code = f"{raw[:4]}-{raw[4:]}"
        codes.append(code)
        db.add(UserRecoveryCode(tenant_id=user.tenant_id, organisation_id=user.organisation_id, user_id=user.id,
                                code_hash=_hash_recovery(code)))
    return codes


async def _two_step_row(db: Any, user: User) -> UserTwoStep:
    row = await _two_step(db, user)
    if row is None:
        row = UserTwoStep(tenant_id=user.tenant_id, organisation_id=user.organisation_id, user_id=user.id)
        db.add(row)
    return row


@router.post("/me/two-step/app", dependencies=[rate_limit("me-two-step", per_minute=10)])
async def start_app(principal: Principal = Depends(require_auth)) -> Any:
    secret = pyotp.random_base32(32)
    await _pending("totp", principal.user.id, {"secret": secret})
    issuer = f"Formalie ({principal.tenant.name})" if principal.tenant.name else "Formalie"
    uri = (f"otpauth://totp/{quote(f'{issuer}:{principal.user.email}', safe='')}?secret={secret}"
           f"&issuer={quote(issuer, safe='')}&algorithm=SHA1&digits=6&period=30")
    return ok({"secret": secret, "uri": uri})


@router.post("/me/two-step/app/confirm", dependencies=[rate_limit("me-two-step", per_minute=10)])
async def confirm_app(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = code_schema.parse(await request.json())
    pending = await _pending("totp", principal.user.id)
    if not pending or not pyotp.TOTP(pending["secret"]).verify(body["code"], valid_window=1):
        raise FrmError("FRM-AUTH-1003")
    await _forget("totp", principal.user.id)
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        row = await _two_step_row(db, user)
        row.totp_secret_enc, row.totp_confirmed_at = encrypt_secret(pending["secret"]), datetime.now(UTC)
        codes = await _new_recovery(db, user)
        await _audit(db, principal, "auth.two_step.enabled", {"method": "app"})
    return ok({"recovery_codes": codes})


@router.post("/me/two-step/app/remove", dependencies=[rate_limit("me-two-step", per_minute=10)])
async def remove_app(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = password_only.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        await _check_password(user, body["password"], "password")
        row = await _two_step(db, user)
        if row is not None:
            row.totp_secret_enc, row.totp_confirmed_at = None, None
        now = datetime.now(UTC)
        for code in (await db.execute(select(UserRecoveryCode).where(
                UserRecoveryCode.tenant_id == user.tenant_id, UserRecoveryCode.user_id == user.id,
                UserRecoveryCode.deleted_at.is_(None)))).scalars():
            code.deleted_at = now
        await _audit(db, principal, "auth.two_step.disabled", {"method": "app"})
        await db.flush()
        return ok(await _profile(db, principal))


@router.post("/me/two-step/recovery", dependencies=[rate_limit("me-two-step", per_minute=10)])
async def new_recovery(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = password_only.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        await _check_password(user, body["password"], "password")
        row = await _two_step(db, user)
        if row is None or not row.totp_confirmed_at:
            raise FrmError("FRM-GEN-1004")
        codes = await _new_recovery(db, user)
        await _audit(db, principal, "auth.recovery_codes.created")
    return ok({"recovery_codes": codes})


@router.post("/me/two-step/phone", dependencies=[rate_limit("me-phone", per_minute=5)])
async def start_phone(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        sms_on = bool((await get_section(db, principal.tenant.id, "signin"))["code"].get("sms"))
    if not sms_on:
        raise FrmError("FRM-GEN-1002", [{"field": "phone", "message": "sms_off"}])
    body = phone_schema.parse(await request.json())
    phone = re.sub(r"[\s-]", "", body["phone"])
    code = f"{100000 + secrets.randbelow(900000)}"
    await _pending("phone", principal.user.id, {"phone": phone, "code_hash": _hash_recovery(code)}, ttl=600)
    sms.send(phone, f"Your Formalie code is {code}. It works for 10 minutes.")
    return ok({"masked": mask_phone(phone)})


@router.post("/me/two-step/phone/confirm", dependencies=[rate_limit("me-phone", per_minute=10)])
async def confirm_phone(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = code_schema.parse(await request.json())
    pending = await _pending("phone", principal.user.id)
    if not pending or not secrets.compare_digest(pending["code_hash"], _hash_recovery(body["code"])):
        raise FrmError("FRM-AUTH-1003")
    await _forget("phone", principal.user.id)
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        row = await _two_step_row(db, user)
        row.sms_phone_enc, row.sms_confirmed_at = encrypt_secret(pending["phone"]), datetime.now(UTC)
        user.phone = pending["phone"]
        await _audit(db, principal, "auth.two_step.enabled", {"method": "sms"})
        await db.flush()
        return ok(await _profile(db, principal))


@router.delete("/me/two-step/phone", dependencies=[rate_limit("me-phone", per_minute=10)])
async def remove_phone(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        user = await db.get(User, principal.user.id)
        row = await _two_step(db, user)
        if row is not None:
            row.sms_phone_enc, row.sms_confirmed_at = None, None
        user.phone = None
        await _audit(db, principal, "auth.two_step.disabled", {"method": "sms"})
        await db.flush()
        return ok(await _profile(db, principal))


# ── My sessions ───────────────────────────────────────────────────────────────────

async def _my_sessions(db: Any, principal: Principal) -> list[dict[str, Any]]:
    mine = [s for s in await active_sessions(db, principal.tenant.id, principal.session_id)
            if s["user"]["email"] == principal.user.email]
    return [{k: s[k] for k in ("id", "current", "started_at", "last_active_at", "ip", "device")} for s in mine]


@router.get("/me/sessions", dependencies=[rate_limit("me-sessions", per_minute=60)])
async def my_sessions(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(await _my_sessions(db, principal))


@router.delete("/me/sessions/{session_id}", dependencies=[rate_limit("me-sessions", per_minute=30)])
async def end_my_session(session_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        ids = {s["id"] for s in await _my_sessions(db, principal)}
        if session_id not in ids:
            raise FrmError("FRM-GEN-1004")
        if session_id == str(principal.session_id):
            raise FrmError("FRM-USER-1005")
        await revoke_sessions(db, principal.tenant.id, ids=[uuid.UUID(session_id)], keep=principal.session_id,
                              reason="signed_out")
        await _audit(db, principal, "auth.session.revoked", {"sessions": "1"})
        await db.flush()
        return ok(await _my_sessions(db, principal))


@router.post("/me/sessions/sign-out-others", dependencies=[rate_limit("me-sessions", per_minute=30)])
async def end_other_sessions(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        ended = await revoke_sessions(db, principal.tenant.id, ids=None, keep=principal.session_id,
                                      user_id=principal.user.id, reason="signed_out")
        await _audit(db, principal, "auth.session.revoked", {"sessions": str(len(ended))})
        await db.flush()
        return ok(await _my_sessions(db, principal))


# ── Tips on new pages ─────────────────────────────────────────────────────────────

async def _tours(db: Any, user_id: uuid.UUID, tenant_id: uuid.UUID) -> UserTour | None:
    return (await db.execute(select(UserTour).where(UserTour.tenant_id == tenant_id, UserTour.user_id == user_id,
                                                    UserTour.deleted_at.is_(None)))).scalar_one_or_none()


def _tours_view(row: UserTour | None) -> dict[str, Any]:
    return {"enabled": not (row and row.tours_off), "seen": list(row.seen) if row else []}


@router.get("/me/tours", dependencies=[rate_limit("me-tours", per_minute=120)])
async def my_tours(principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok(_tours_view(await _tours(db, principal.user.id, principal.tenant.id)))


@router.patch("/me/tours", dependencies=[rate_limit("me-tours", per_minute=60)])
async def update_my_tours(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    body = tours_schema.parse(await request.json())
    async with db_session("write", **_scope(principal)) as db:
        row = await _tours(db, principal.user.id, principal.tenant.id)
        if row is None:
            row = UserTour(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                           user_id=principal.user.id, seen=[])
            db.add(row)
        seen = list(row.seen or [])
        if "enabled" in body:
            row.tours_off = not body["enabled"]
        if body.get("reset"):
            seen = []
        if body.get("seen") and body["seen"] not in seen:
            seen.append(body["seen"])
        row.seen = seen[-100:]
        await db.flush()
        return ok(_tours_view(row))



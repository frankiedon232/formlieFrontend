"""Public form routes (mock: routes/publicForms.ts; API-CONTRACT → Public), no sign-in. Enveloped like every call
(anonymous handshake + pre-session CSRF); the workspace comes from the host, or on `forms.*` from the form key.

    GET  /public/forms/{key}                      the published form, its state, SEO and workspace branding
    POST /public/forms/{key}/unlock               password · invitation · member pass → unlock cookie (12 h)
    POST /public/forms/{key}/challenge            spam check (proof of work)
    POST /public/forms/{key}/verify (+ /confirm)  a code to the respondent's email → a token for the submission
    POST /public/forms/{key}/sessions             save and resume (PUT / GET …/sessions/{token})
    POST /public/forms/{key}/uploads              a pre-signed link for one file (+ /{id}/complete)
    GET  /public/forms/{key}/options              a long list's options as people type
    POST /public/forms/{key}/submit               one response per fill-in session (Formalie-Key)
    GET  /public/short/{code}                     where a short link leads (the visit is counted)
    GET  /internal/public-forms/{key}             the server-rendered page's read (server-only token, plain)
    GET  /internal/short/{code}                   the server-rendered short link (server-only token, plain)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, update

from app.core import js
from app.core import zod as z
from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.fernet_tokens import make_token, read_token
from app.core.security.limits import per_value, rate_limit
from app.core.security.passwords import verify_password
from app.core.security.refs import get_codec
from app.modules.audit.service import Actor, record
from app.modules.emails import service as emails
from app.modules.forms.answers import file_answers, max_file_bytes
from app.modules.forms.models import Form, FormVersion
from app.modules.links import directory, urls
from app.modules.links.access_tokens import UNLOCK_TTL_S, hash_token, read_pass, unlock_value
from app.modules.links.models import FormInvitation
from app.modules.public import rules, service
from app.modules.public.models import RespondentVerification, ResumeDraft
from app.modules.public.pow import check_work
from app.modules.public.submit import all_fields, check_submission, is_locked
from app.modules.responses.models import Response as StoredResponse
from app.modules.responses.models import ResponseSubmission
from app.modules.settings.service import get_section
from app.modules.uploads import service as uploads
from app.modules.users.models import User

router = APIRouter(tags=["public"])

RESPONDENT = Actor("user", None, "Respondent", None)
DEVICE_COOKIE = "formalie_device"
SUBMISSION_ID = r"[A-Za-z0-9-]{16,64}"
CHALLENGE_DIFFICULTY = 14
CHALLENGE_TTL_S = 4 * 3600
MIN_FILL_MS = 3_000
RESUME_DAYS = 30
VERIFY_TTL_S = 10 * 60
VERIFY_TOKEN_TTL_S = 30 * 60
FILE_FIELDS = ("file_upload", "image_upload")

unlock_schema = z.union([z.obj(password=z.string().min(1).max(100)), z.obj(invite=z.string().min(10).max(100)),
                         z.obj(**{"pass": z.string().min(10).max(200)})])
submit_schema = z.obj(
    data=z.record(z.string(), z.unknown()), channel=z.enum(["link", "embed"]).optional(),
    language=z.string().max(10).optional(), for_someone_else=z.boolean().optional(),
    confirmed_different=z.boolean().optional(), verification_token=z.string().max(80).optional(),
    resume_token=z.string().max(80).optional(),
    challenge=z.obj(token=z.string().max(400), nonce=z.number().int().min(0)).optional(),
    trap=z.string().max(500).optional(),
)
verify_schema = z.obj(email=z.string().email().max(200))
confirm_schema = z.obj(email=z.string().email().max(200), code=z.string().regex(r"^\d{6}$"))
draft_schema = z.obj(data=z.record(z.string(), z.unknown()), page=z.number().int().min(0).max(500).optional(),
                     email=z.string().email().max(200).optional())
upload_schema = z.obj(field=z.string().min(1).max(64), file_name=z.string().min(1).max(200),
                      content_type=z.string().max(120), size=z.number().int().positive())


def _ip() -> str:
    ctx = get_context()
    return (ctx.client_ip if ctx else None) or "unknown"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ── The form ────────────────────────────────────────────────────────────────────

@router.get("/public/forms/{key}", dependencies=[rate_limit("public-form", per_minute=120)])
async def get_public_form(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("read", **service.scope_of(tenant)) as db:
        return ok(await service.public_view(db, request, tenant, key, service.channel_of(request)))


def _internal_allowed(request: Request) -> bool:
    expected = get_settings().internal_token
    given = request.headers.get("x-formalie-internal") or ""
    return bool(expected) and hmac.compare_digest(given, expected.get_secret_value())  # type: ignore[union-attr]


@router.get("/internal/public-forms/{key}", include_in_schema=False)
async def internal_public_form(key: str, request: Request) -> Any:
    """The server-rendered page's read: the same PublicForm, plain JSON, only with the server-only token."""
    if not _internal_allowed(request):
        return JSONResponse({"error": {"code": "FRM-PERM-1001"}}, status_code=403)
    try:
        tenant = await service.workspace_for(key)
        async with db_session("read", **service.scope_of(tenant)) as db:
            view = await service.public_view(db, request, tenant, key, service.channel_of(request))
    except FrmError as error:
        status = 404 if error.code == "FRM-FORM-1001" else 500
        return JSONResponse({"error": {"code": error.code}}, status_code=status)
    return JSONResponse(get_codec().encode_ids(view))


# ── Who may open it ─────────────────────────────────────────────────────────────

@router.post("/public/forms/{key}/unlock", dependencies=[rate_limit("public-unlock", per_minute=30)])
async def unlock_form(key: str, request: Request, response: Response) -> Any:
    """The password, a personal invitation token or a member's sign-in pass → an unlock cookie for this browser
    (12 hours; SameSite=None so embeds work too). At most 10 tries per 10 minutes from one address for one form."""
    tenant = await service.workspace_for(key)
    body = await request.json()
    async with db_session("write", **service.scope_of(tenant)) as db:
        form = await service.find_form(db, tenant, key, None)
        if form.access == "public":
            return ok({"unlocked": True})
        await per_value("public-unlock-tries", f"{form.id}:{_ip()}", limit=10, window_seconds=600)
        data = unlock_schema.parse(body)
        who = None
        if form.access == "password" and "password" in data and form.password_hash:
            if not verify_password(form.password_hash, data["password"]):
                raise FrmError("FRM-FORM-1017")
            who = "pw"
        elif form.access == "invite" and "invite" in data:
            invite = (await db.execute(select(FormInvitation).where(
                FormInvitation.tenant_id == tenant.id, FormInvitation.form_id == form.id,
                FormInvitation.token_hash == hash_token(data["invite"]), FormInvitation.revoked_at.is_(None),
                FormInvitation.deleted_at.is_(None)))).scalar_one_or_none()
            if invite is None:
                raise FrmError("FRM-FORM-1018")
            if invite.opened_at is None:
                invite.opened_at = datetime.now(UTC)
            who = f"inv~{invite.id}"
        elif form.access == "organisation" and "pass" in data:
            user_id = read_pass(form, data["pass"])
            user = await db.get(User, user_id) if user_id else None
            if user is None or user.tenant_id != tenant.id or user.status != "active" or user.deleted_at:
                raise FrmError("FRM-FORM-1019")
            who = f"usr~{user.id}"
        if who is None:
            raise FrmError("FRM-FORM-1005")
        response.set_cookie(service.unlock_cookie(form), unlock_value(form, who), max_age=UNLOCK_TTL_S, httponly=True,
                            secure=True, samesite="none", path="/")
        return ok({"unlocked": True})


# ── Spam check (decision 89) ────────────────────────────────────────────────────

@router.post("/public/forms/{key}/challenge", dependencies=[rate_limit("public-challenge", per_minute=60)])
async def issue_challenge(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("read", **service.scope_of(tenant)) as db:
        form, _, _ = await service.taking_responses(db, request, tenant, key)
    salt = secrets.token_urlsafe(16)
    token = make_token({"t": "pow", "k": form.public_key, "s": salt, "i": int(datetime.now(UTC).timestamp() * 1000),
                        "d": CHALLENGE_DIFFICULTY})
    return ok({"token": token, "salt": salt, "difficulty": CHALLENGE_DIFFICULTY, "min_wait_ms": MIN_FILL_MS})


def _proven_salt(form: Form, proof: dict[str, Any] | None) -> str | None:
    """The challenge's salt when the proof is valid for this form: signed, old enough, not expired, solved."""
    if not proof:
        return None
    data = read_token(proof["token"], CHALLENGE_TTL_S)
    if not data or data.get("t") != "pow" or data.get("k") != form.public_key:
        return None
    age = datetime.now(UTC).timestamp() * 1000 - float(data.get("i", 0))
    if age < MIN_FILL_MS:
        return None
    salt = str(data.get("s", ""))
    return salt if salt and check_work(salt, int(data.get("d", 99)), proof["nonce"]) else None


async def _reserve_challenge(salt: str) -> bool:
    """One solved challenge, one submission (Redis: taken until it expires)."""
    try:
        return bool(await get_redis().set(f"pow:used:{salt}", "1", nx=True, ex=CHALLENGE_TTL_S))
    except Exception:  # noqa: BLE001 (Redis down: the signed, timed proof still stands)
        return True


async def _release_challenge(salt: str) -> None:
    try:
        await get_redis().delete(f"pow:used:{salt}")
    except Exception:  # noqa: BLE001
        pass


# ── Verify the respondent's email ───────────────────────────────────────────────

@router.post("/public/forms/{key}/verify", dependencies=[rate_limit("public-verify", per_minute=20)])
async def send_verification(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form, schema, _ = await service.taking_responses(db, request, tenant, key)
        email = rules.normalise_email(verify_schema.parse(await request.json())["email"])
        if not email:
            raise FrmError("FRM-GEN-1002", [{"field": "email", "message": "Enter a valid email."}])
        try:
            await per_value("public-verify-codes", f"{form.id}:{email}", limit=5, window_seconds=3600)
        except FrmError:
            raise FrmError("FRM-AUTH-1004") from None
        code = f"{secrets.randbelow(900000) + 100000}"
        now = datetime.now(UTC)
        db.add(RespondentVerification(tenant_id=tenant.id, organisation_id=tenant.organisation_id, form_id=form.id,
                                      email_hash=_sha(email), code_hash=_sha(f"{form.id}:{email}:{code}"),
                                      expires_at=now + timedelta(seconds=VERIFY_TTL_S)))
        emails.send(email, "respondent_code", rules.main_language(schema), {
            "code": code, "minutes": VERIFY_TTL_S // 60, "form": form.name, "workspace": tenant.name})
        dev = {} if get_settings().is_production else {"dev_code": code}
        return ok({"sent_to": rules.mask_email(email), "expires_in": VERIFY_TTL_S}, dev)


async def _latest_verification(db: Any, form: Form, email: str) -> RespondentVerification | None:
    return (await db.execute(select(RespondentVerification).where(
        RespondentVerification.tenant_id == form.tenant_id, RespondentVerification.form_id == form.id,
        RespondentVerification.email_hash == _sha(email), RespondentVerification.deleted_at.is_(None))
        .order_by(RespondentVerification.created_at.desc()).limit(1))).scalar_one_or_none()


@router.post("/public/forms/{key}/verify/confirm", dependencies=[rate_limit("public-verify", per_minute=20)])
async def confirm_verification(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form, _, _ = await service.taking_responses(db, request, tenant, key)
        data = confirm_schema.parse(await request.json())
        email = rules.normalise_email(data["email"]) or ""
        entry = await _latest_verification(db, form, email)
        now = datetime.now(UTC)
        if entry is None or entry.expires_at < now or entry.used_at is not None:
            raise FrmError("FRM-AUTH-1003")
        if entry.attempts >= 5:
            raise FrmError("FRM-AUTH-1004")
        if not hmac.compare_digest(entry.code_hash, _sha(f"{form.id}:{email}:{data['code']}")):
            entry.attempts += 1
            raise FrmError("FRM-AUTH-1003", commit=True)
        token = secrets.token_urlsafe(24)
        entry.token_hash, entry.token_expires_at = _sha(token), now + timedelta(seconds=VERIFY_TOKEN_TTL_S)
        return ok({"token": token})


async def _use_verification(db: Any, form: Form, email: str, token: str | None) -> bool:
    """A confirmed email for this form (the token from /verify/confirm), used once."""
    entry = await _latest_verification(db, form, email)
    now = datetime.now(UTC)
    if entry is None or not token or not entry.token_hash or entry.used_at is not None \
            or (entry.token_expires_at or now) < now or not hmac.compare_digest(entry.token_hash, _sha(token)):
        return False
    entry.used_at = now
    return True


# ── Save and resume ─────────────────────────────────────────────────────────────

async def _resumable(db: Any, request: Request, tenant: Any, key: str) -> Form:
    form, schema, _ = await service.taking_responses(db, request, tenant, key)
    if not (schema.get("settings") or {}).get("save_resume"):
        raise FrmError("FRM-PERM-1001")
    return form


async def _draft(db: Any, form: Form, token: str) -> ResumeDraft:
    draft = (await db.execute(select(ResumeDraft).where(
        ResumeDraft.tenant_id == form.tenant_id, ResumeDraft.form_id == form.id, ResumeDraft.token_hash == _sha(token),
        ResumeDraft.deleted_at.is_(None)))).scalar_one_or_none()
    if draft is None or draft.expires_at < datetime.now(UTC):
        raise FrmError("FRM-GEN-1004")
    if draft.closed_at is not None:
        raise FrmError("FRM-RESP-1003")
    return draft


def _resume_link(form: Form, tenant: Any, token: str) -> str:
    from urllib.parse import quote

    return f"{urls.form_link(tenant.subdomain, form.custom_link or form.public_key)}?resume={quote(token, safe='')}"


def _send_resume(tenant: Any, form: Form, email: str, link: str, language: str) -> None:
    emails.send(email, "resume_link", language, {"form": form.name, "link": link, "days": RESUME_DAYS,
                                                  "workspace": tenant.name})


@router.post("/public/forms/{key}/sessions", status_code=201, dependencies=[rate_limit("public-drafts", per_minute=30)])
async def start_draft(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form = await _resumable(db, request, tenant, key)
        data = draft_schema.parse(await request.json())
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(days=RESUME_DAYS)
        db.add(ResumeDraft(tenant_id=tenant.id, organisation_id=tenant.organisation_id, form_id=form.id,
                           token_hash=_sha(token), data=data["data"], page=data.get("page") or 0,
                           email=data.get("email"), expires_at=expires))
        meta: dict[str, Any] = {}
        if data.get("email"):
            link = _resume_link(form, tenant, token)
            _send_resume(tenant, form, data["email"], link, rules.main_language(form.draft_schema))
            meta = {} if get_settings().is_production else {"dev_resume_url": link}
        return ok({"resume_token": token, "expires_at": _iso(expires),
                   "sent_to": rules.mask_email(data["email"]) if data.get("email") else None}, meta)


@router.put("/public/forms/{key}/sessions/{token}", dependencies=[rate_limit("public-drafts", per_minute=120)])
async def save_draft(key: str, token: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form = await _resumable(db, request, tenant, key)
        draft = await _draft(db, form, token)
        data = draft_schema.parse(await request.json())
        draft.data, draft.page = data["data"], data.get("page") or 0
        if data.get("email"):
            draft.email = data["email"]
        now = datetime.now(UTC)
        draft.updated_at = now
        meta: dict[str, Any] = {}
        if data.get("email"):
            link = _resume_link(form, tenant, token)
            _send_resume(tenant, form, data["email"], link, rules.main_language(form.draft_schema))
            meta = {} if get_settings().is_production else {"dev_resume_url": link}
        return ok({"saved_at": _iso(now), "expires_at": _iso(draft.expires_at),
                   "sent_to": rules.mask_email(data["email"]) if data.get("email") else None}, meta)


@router.get("/public/forms/{key}/sessions/{token}", dependencies=[rate_limit("public-drafts", per_minute=60)])
async def get_draft(key: str, token: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("read", **service.scope_of(tenant)) as db:
        form = await _resumable(db, request, tenant, key)
        draft = await _draft(db, form, token)
        return ok({"data": draft.data, "page": draft.page, "updated_at": _iso(draft.updated_at),
                   "expires_at": _iso(draft.expires_at)})


# ── Files for file questions ────────────────────────────────────────────────────

@router.post("/public/forms/{key}/uploads", status_code=201, dependencies=[rate_limit("public-uploads", per_minute=60)])
async def request_upload(key: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form, schema, _ = await service.taking_responses(db, request, tenant, key)
        data = upload_schema.parse(await request.json())
        fld = next((f for f in all_fields(schema) if f["key"] == data["field"]), None)
        if fld is None or fld["type"] not in FILE_FIELDS or is_locked(fld):
            raise FrmError("FRM-GEN-1002", [{"field": "field", "message": "This question takes no files."}])
        await per_value("public-upload-files", f"{form.id}:{_ip()}", limit=60, window_seconds=600)
        props = fld.get("props") or {}
        raw_accept = props.get("accept", js.UNDEFINED)
        accept = "" if js.nullish(raw_accept) else js.to_string(raw_accept)
        image = fld["type"] == "image_upload"
        if image:
            accept = rules.picture_accept(accept)
        if not rules.accepts_file(accept, data["file_name"], data["content_type"]) or (
                image and not rules.looks_like_picture(data["file_name"], data["content_type"])):
            raise FrmError("FRM-GEN-1002", [{"field": "content_type", "message": "This file type is not allowed."}])
        limit = max_file_bytes(props)
        if data["size"] > limit:
            raise FrmError("FRM-GEN-1002", [{"field": "size", "message": f"The file is larger than {js.number_to_string(js.math_round(limit / 1024 / 1024))} MB."}])
        return ok(await uploads.create_respondent_ticket(
            db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, form_id=form.id, field_key=fld["key"],
            file_name=data["file_name"], content_type=data["content_type"], size=data["size"], max_bytes=limit,
            kind="image" if image else "file", listed=[t for t in rules.parse_accept(accept) if t.startswith(".")]))


@router.post("/public/forms/{key}/uploads/{upload_id}/complete", dependencies=[rate_limit("public-uploads", per_minute=60)])
async def complete_upload(key: str, upload_id: str, request: Request) -> Any:
    tenant = await service.workspace_for(key)
    async with db_session("write", **service.scope_of(tenant)) as db:
        form, _, _ = await service.taking_responses(db, request, tenant, key)
        answer = await uploads.complete_respondent_upload(db, tenant.id, upload_id, form.id)
        if answer is None:
            raise FrmError("FRM-GEN-1004")
        return ok(answer)


# ── Long lists ──────────────────────────────────────────────────────────────────

@router.get("/public/forms/{key}/options", dependencies=[rate_limit("public-options", per_minute=240)])
async def lookup_options(key: str, request: Request) -> Any:
    """A long list's options as people type, from the published form (open forms, same access as the page)."""
    tenant = await service.workspace_for(key)
    query = request.query_params
    async with db_session("read", **service.scope_of(tenant)) as db:
        form = await service.find_form(db, tenant, key, service.channel_of(request))
        if service.state_of(tenant, form) != "open":
            raise FrmError("FRM-GEN-1004")
        if await service.visitor_of(db, request, form) is None:
            raise FrmError("FRM-PERM-1001")
        published = await service.live_schema(db, form)
    if published is None:
        raise FrmError("FRM-GEN-1004")
    own = next((f for f in all_fields(published) if f["key"] == str(query.get("field") or "")), None)
    if own is None or not rules.served_remotely(own):
        raise FrmError("FRM-GEN-1004")
    language = query.get("language")
    fld = own
    if language and language in rules.form_languages(published):
        fld = next(f for f in all_fields(rules.translate_schema(published, language)) if f["key"] == own["key"])

    def csv(value: str | None) -> list[str] | None:
        return value.split(",")[:500] if value else None
    parents = (csv(query.get("parents")) or []) if fld.get("option_parent") else None
    return ok(rules.lookup_options(fld.get("options") or [], str(query.get("q") or ""), csv(query.get("values")), parents))


# ── Submit ──────────────────────────────────────────────────────────────────────

def _thank_you(schema: dict[str, Any], language: str | None) -> dict[str, Any]:
    thanks = rules.translate_schema(schema, language or rules.main_language(schema)).get("thank_you") or {}
    return {"title": thanks.get("title") or "", "message": thanks.get("message") or "",
            "redirect_url": thanks.get("redirect_url")}


def _device(request: Request, response: Response) -> str:
    """This browser's device id (a random cookie set on the first submission; not personal data)."""
    import re

    existing = request.cookies.get(DEVICE_COOKIE)
    if existing and re.fullmatch(r"[A-Za-z0-9-]{20,64}", existing):
        return existing
    fresh = str(uuid.uuid4())
    response.set_cookie(DEVICE_COOKIE, fresh, max_age=365 * 86400, httponly=True, secure=True, samesite="none", path="/")
    return fresh


@router.post("/public/forms/{key}/submit", dependencies=[rate_limit("public-submit", per_minute=60)])
async def submit_public_form(key: str, request: Request, response: Response) -> Any:
    import re

    submission_id = request.headers.get("formalie-key") or ""
    if not re.fullmatch(SUBMISSION_ID, submission_id):
        raise FrmError("FRM-GEN-1002", [{"field": "Formalie-Key", "message": "Send the fill-in session id as Formalie-Key."}])
    data = submit_schema.parse(await request.json())
    channel = data.get("channel") or "link"
    tenant = await service.workspace_for(key)
    salt: str | None = None
    stored = False
    try:
        async with db_session("write", **service.scope_of(tenant)) as db:
            form, schema, visitor = await service.taking_responses(db, request, tenant, key, ignore_limit=True, channel=channel)
            thank_you = _thank_you(schema, data.get("language"))

            # The same session again (double click, retry, back button): the response it already made
            earlier = (await db.execute(select(ResponseSubmission).where(
                ResponseSubmission.tenant_id == tenant.id, ResponseSubmission.form_id == form.id,
                ResponseSubmission.submission_id == submission_id))).scalar_one_or_none()
            if earlier is not None:
                return ok({"response_id": str(earlier.response_id), "duplicate": True, "thank_you": thank_you})
            if service.limit_reached(tenant, form):
                raise FrmError("FRM-FORM-1003")

            # Spam: a filled-in trap looks accepted but stores nothing; too many from one address slows down;
            # without a solved challenge (or sent within seconds of opening) it is refused
            if js.trim(data.get("trap") or ""):
                response.status_code = 201
                return ok({"response_id": str(uuid.uuid4()), "duplicate": False, "thank_you": thank_you})
            await per_value("public-submits", f"{form.id}:{_ip()}", limit=20, window_seconds=600)
            salt = _proven_salt(form, data.get("challenge"))
            if not salt or not await _reserve_challenge(salt):
                salt = None
                raise FrmError("FRM-RESP-1009")

            issues, answers = check_submission(schema, data["data"])
            files: list[Any] = []
            for fld in all_fields(schema):
                if fld["type"] not in FILE_FIELDS or fld["key"] not in answers:
                    continue
                value = answers[fld["key"]]
                if js.nullish(value) or (isinstance(value, list) and not value):
                    continue
                found = [await uploads.respondent_file(db, tenant.id, f["id"], form.id, fld["key"])
                         for f in file_answers(value)]
                if not isinstance(value, list) or len(found) != len(value) or any(f is None for f in found):
                    issues.append({"key": fld["key"], "code": "file"})
                else:
                    answers[fld["key"]] = [uploads.answer_of(f) for f in found]  # type: ignore[arg-type]
                    files.extend(found)
            if issues:
                raise FrmError("FRM-RESP-1001", [{"field": i["key"], "message": i["code"]} for i in issues])

            # Telling people apart (decision 85): with the respondent's own email, same → refused, a typo away →
            # asked and flagged; without one, one per browser. The exact same answers never twice.
            device = _device(request, response)
            known = visitor.identity()
            identity = rules.identity_of(schema)
            if identity["verify"] and identity["email"]:
                email = rules.normalise_email(answers.get(identity["email"]))
                if not email:
                    raise FrmError("FRM-RESP-1001", [{"field": identity["email"], "message": "required"}])
                if not await _use_verification(db, form, email, data.get("verification_token")):
                    raise FrmError("FRM-RESP-1008", [{"field": identity["email"],
                                                      "message": rules.mask_email(answers.get(identity["email"]))}])
            live = (StoredResponse.tenant_id == tenant.id, StoredResponse.form_id == form.id,
                    StoredResponse.deleted_at.is_(None))
            possible: dict[str, Any] | None = None
            repeat = bool((schema.get("settings") or {}).get("repeat"))
            import json as _json

            def hint(at: Any, email: Any) -> str:
                return _json.dumps({"at": at, "email": rules.mask_email(email)}, ensure_ascii=False, separators=(",", ":"))
            if repeat:
                pass
            elif known:
                prior = (await db.execute(select(StoredResponse.submitted_at).where(
                    *live, StoredResponse.respondent_kind == known["kind"],
                    StoredResponse.respondent_ref_id == known["id"]).limit(1))).scalar_one_or_none()
                if prior is not None:
                    raise FrmError("FRM-RESP-1006", [{"field": "", "message": hint(_iso(prior), known["email"])}])
            elif identity["email"]:
                key_ = identity["email"]
                rows = (await db.execute(select(StoredResponse.id, StoredResponse.submitted_at, StoredResponse.data)
                                         .where(*live).order_by(StoredResponse.submitted_at.desc()))).all()
                earlier_records = [{"id": str(r.id), "submitted_at": _iso(r.submitted_at), "data": r.data} for r in rows]
                match = rules.match_identity(schema, answers, earlier_records, identity)
                if match["level"] != "none":
                    found_record = match["record"]
                    message = hint(found_record["submitted_at"], found_record["data"].get(key_))
                    if match["level"] == "clear":
                        raise FrmError("FRM-RESP-1006", [{"field": key_, "message": message}])
                    if not data.get("confirmed_different"):
                        raise FrmError("FRM-RESP-1007", [{"field": key_, "message": message}])
                    possible = {"of": found_record["id"], "reason": match["reason"]}
            elif not data.get("for_someone_else"):
                same_device = (await db.execute(select(StoredResponse.id).where(
                    *live, StoredResponse.device_hash == _sha(device)).limit(1))).scalar_one_or_none()
                if same_device is not None:
                    raise FrmError("FRM-RESP-1004")
            fingerprint = rules.fingerprint_of(answers)
            same = (await db.execute(select(StoredResponse.id).where(
                *live, StoredResponse.fingerprint == fingerprint).limit(1))).scalar_one_or_none()
            if same is not None:
                raise FrmError("FRM-RESP-1005")

            # Stored: the form's next number (row locked), the version answered, the session, the files
            locked = (await db.execute(select(Form).where(Form.id == form.id).with_for_update())).scalar_one()
            number = locked.next_response_number
            version = await db.get(FormVersion, locked.published_version_id) if locked.published_version_id else None
            now = datetime.now(UTC)
            language = data.get("language")
            ctx = get_context()
            stored_response = StoredResponse(
                tenant_id=tenant.id, organisation_id=tenant.organisation_id, submitted_at=now, form_id=form.id,
                form_version_no=version.number if version else None, number=number, data=answers,
                language=language if language and language in rules.form_languages(schema) else rules.main_language(schema),
                channel=channel, submission_id=submission_id, device_hash=_sha(device), fingerprint=fingerprint,
                identity_email=rules.normalise_email(answers.get(identity["email"])) if identity["email"] else None,
                respondent_kind=known["kind"] if known else None, respondent_ref_id=known["id"] if known else None,
                respondent_email=known["email"] if known else None, respondent_name=known["name"] if known else None,
                possible_duplicate=possible, ip=_ip() if _ip() != "unknown" else None,
                user_agent=((ctx.user_agent if ctx else None) or "")[:300] or None)
            db.add(stored_response)
            await db.flush()
            db.add(ResponseSubmission(tenant_id=tenant.id, organisation_id=tenant.organisation_id, form_id=form.id,
                                      submission_id=submission_id, response_id=stored_response.id,
                                      response_submitted_at=now))
            for upload in files:
                upload.response_id, upload.response_submitted_at = stored_response.id, now
            if visitor.kind == "invite" and visitor.invite is not None:
                visitor.invite.responded_at = now
            if data.get("resume_token"):
                draft = (await db.execute(select(ResumeDraft).where(
                    ResumeDraft.tenant_id == tenant.id, ResumeDraft.form_id == form.id,
                    ResumeDraft.token_hash == _sha(data["resume_token"])))).scalar_one_or_none()
                if draft is not None:
                    draft.closed_at, draft.data = now, {}
            await db.execute(update(Form).where(Form.id == form.id).values(
                responses_count=Form.responses_count + 1, next_response_number=Form.next_response_number + 1))
            from app.core.events.outbox import record_event

            await record_event(db, "response.created", {"form_id": str(form.id), "response_id": str(stored_response.id),
                                                         "submitted_at": _iso(now)},
                               tenant_id=tenant.id, organisation_id=tenant.organisation_id)
            from app.modules.destinations.service import response_stored

            await response_stored(db, locked, stored_response)  # the form's database table, when it has one
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="responses.submitted",
                         actor=RESPONDENT, resource={"type": "form", "id": str(form.id), "name": form.name},
                         changes=[{"field": "channel", "before": None, "after": channel}])
            stored, stored_id = True, stored_response.id
            response.status_code = 201
            return ok({"response_id": str(stored_response.id), "duplicate": False, "thank_you": thank_you})
    finally:
        if salt and not stored:
            await _release_challenge(salt)
        if stored:  # emails and notifications, after the response is committed
            from app.modules.responses import after

            after.dispatch(tenant, form.id, stored_id)


# ── Short links ─────────────────────────────────────────────────────────────────

async def resolve_short_link(code: str) -> str:
    """Where a short link leads (the visit is counted): the form's current link on its own host."""
    if not urls.SHORT_CODE_PATTERN.fullmatch(code):
        raise FrmError("FRM-FORM-1001")
    async with db_session("read") as db:
        found = await directory.resolve_short_code(db, code)
    if found is None or found.status == "suspended":
        raise FrmError("FRM-FORM-1001")
    async with db_session("write", tenant_id=found.tenant_id, organisation_id=found.organisation_id) as db:
        form = await db.get(Form, found.form_id)
        channels = list(form.channels) if form and form.channels else ["link", "embed", "api"]
        if form is None or form.deleted_at or form.purged_at or form.short_code != code or "link" not in channels:
            raise FrmError("FRM-FORM-1001")
        await db.execute(update(Form).where(Form.id == form.id).values(short_clicks=Form.short_clicks + 1))
        return urls.form_link(found.subdomain, form.custom_link or form.public_key)


@router.get("/public/short/{code}", dependencies=[rate_limit("public-short", per_minute=120)])
async def get_short_link(code: str) -> Any:
    return ok({"target": await resolve_short_link(code)})


@router.get("/internal/short/{code}", include_in_schema=False)
async def internal_short_link(code: str, request: Request) -> Any:
    if not _internal_allowed(request):
        return JSONResponse({"error": {"code": "FRM-PERM-1001"}}, status_code=403)
    try:
        return JSONResponse({"target": await resolve_short_link(code)})
    except FrmError as error:
        return JSONResponse({"error": {"code": error.code}}, status_code=404 if error.code == "FRM-FORM-1001" else 500)


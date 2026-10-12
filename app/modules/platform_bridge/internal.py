"""The internal admin API's gate, idempotency and audit (PLATFORM-ADMIN-INTEGRATION §2).

Every call to /internal/admin/v1 passes `platform_call` first, in this order:
  1. the feature is configured (PLATFORM_ADMIN_KEYS), and in production mutual TLS is required  → FRM-SEC-1007
  2. the caller is on Formalie's private network (PLATFORM_ADMIN_NETWORKS)                      → FRM-SEC-1007
  3. mutual TLS: Nginx verified the platform's client certificate, a known fingerprint
     (PLATFORM_ADMIN_REQUIRE_MTLS; always on in production)                                      → FRM-SEC-1007
  4. the signing headers are there and the key is known                                          → FRM-SEC-1005 / 1007
  5. the timestamp is within the window                                                          → FRM-SEC-1002
  6. the signature matches (method, path, timestamp, nonce, body hash, staff headers)            → FRM-SEC-1005
  7. the nonce was not seen before (Redis; Redis down: refused)                                  → FRM-SEC-1003 / GEN-5003
  8. a change (POST) names the staff member, the reason and an idempotency key                   → FRM-GEN-1002

`run_change` then makes the call idempotent (platform.admin_calls: the same key and the same request get the same
answer again, marked `Idempotent-Replayed: true`; the same key with another request: FRM-BILL-1005; while the
first is still running: FRM-GEN-1009) and logs every call with who did it. Changes to a workspace are written to its
audit trail as Formalie support with the staff member's name (`audit()`).

Answers are Formalie's usual `{ success, data, meta }` / `{ success, error }`, plain JSON (no browser envelope).
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import unquote

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis import get_redis
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.errors.exceptions import error_body
from app.core.ids import uuid7
from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.modules.audit.service import Actor, record
from app.modules.platform_bridge import signing as sg
from app.modules.platform_bridge.models import AdminCall

log = logging.getLogger("formalie.platform.internal")

PREFIX = "/internal/admin/v1"
NONCE_PREFIX = "fm:v1:platform:nonce:"
STALE_AFTER = timedelta(minutes=2)  # a call still "running" after this is taken as failed (its worker died)


@dataclass
class PlatformCall:
    key_id: str
    staff_id: str | None
    staff_name: str | None
    approval_id: str | None
    reason: str | None
    idempotency_key: str | None
    body: bytes
    method: str
    path: str
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def actor(self) -> Actor:
        return Actor.support(self.staff_id, self.staff_name, self.approval_id)

    def json(self) -> dict[str, Any]:
        if not self.body:
            return {}
        try:
            data = json.loads(self.body)
        except ValueError:
            raise FrmError("FRM-GEN-1001", [{"field": "body", "message": "json"}]) from None
        if not isinstance(data, dict):
            raise FrmError("FRM-GEN-1001", [{"field": "body", "message": "object"}])
        return data


def _refuse(code: str, why: str, details: list[dict[str, str]] | None = None) -> FrmError:
    ctx = get_context()
    if ctx is not None:
        ctx.flags.add("platform_refused")
    return FrmError(code, details, log_context={"security_event": "platform_call_refused", "why": why})


def _on_network(ip: str | None, networks: list[str]) -> bool:
    try:
        address = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    for network in networks:
        try:
            if address in ipaddress.ip_network(network, strict=False):
                return True
        except ValueError:
            continue
    return False


def _signed_path(request: Request) -> str:
    raw = request.scope.get("raw_path") or request.url.path.encode()
    path = raw.decode("latin-1") if isinstance(raw, bytes) else str(raw)
    query = request.scope.get("query_string") or b""
    return f"{path}?{query.decode('latin-1')}" if query else path


def _text(value: str | None, limit: int) -> str | None:
    if value is None or value == "":
        return None
    try:
        decoded = unquote(value, encoding="utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        raise FrmError("FRM-GEN-1002", [{"field": "headers", "message": "invalid"}]) from None
    if not decoded or len(decoded) > limit or any(ord(c) < 32 for c in decoded):
        raise FrmError("FRM-GEN-1002", [{"field": "headers", "message": "invalid"}])
    return decoded


async def platform_call(request: Request) -> PlatformCall:
    """FastAPI dependency: a verified call from the platform admin, or the reason it is refused."""
    settings = get_settings()
    ctx = get_context()
    keys = sg.keys_of([k.get_secret_value() for k in settings.platform_admin_keys])
    if not keys:
        raise _refuse("FRM-SEC-1007", "not_configured")
    if settings.is_production and not settings.platform_admin_require_mtls:
        log.critical("internal admin API refused: mutual TLS must be required in production")
        raise _refuse("FRM-SEC-1007", "mtls_not_required_in_production")
    if not _on_network(ctx.client_ip if ctx else None, settings.platform_admin_networks):
        raise _refuse("FRM-SEC-1007", "network")
    if settings.platform_admin_require_mtls:
        if not (ctx and ctx.proxy_trusted) or not sg.mtls_ok(
                request.headers.get(settings.platform_admin_verify_header),
                request.headers.get(settings.platform_admin_fingerprint_header),
                settings.platform_admin_cert_fingerprints):
            raise _refuse("FRM-SEC-1007", "client_certificate")

    h = request.headers
    key_id, timestamp, nonce, given = h.get(sg.H_KEY, ""), h.get(sg.H_TS, ""), h.get(sg.H_NONCE, ""), h.get(sg.H_SIG, "")
    if not (key_id and timestamp and nonce and given) or not sg.NONCE.match(nonce):
        raise _refuse("FRM-SEC-1005", "headers", [{"field": "headers", "message": "signature headers"}])
    secret = keys.get(key_id)
    if secret is None:
        raise _refuse("FRM-SEC-1007", "unknown_key")
    if not sg.fresh(timestamp, settings.platform_admin_window_seconds):
        raise _refuse("FRM-SEC-1002", "timestamp")
    body = await request.body()
    method = request.method.upper()
    path = _signed_path(request)
    if not sg.matches(secret, sg.canonical(method, path, timestamp, nonce, body, dict(h)), given):
        raise _refuse("FRM-SEC-1005", "signature")
    try:
        first = await get_redis().set(f"{NONCE_PREFIX}{key_id}:{nonce}", "1", nx=True,
                                      ex=settings.platform_admin_window_seconds * 2)
    except RedisError:
        log.error("FRM-GEN-5003 nonce store unavailable for an internal admin call", extra={"error_code": "FRM-GEN-5003"})
        raise FrmError("FRM-GEN-5003") from None
    if not first:
        raise _refuse("FRM-SEC-1003", "replay")

    call = PlatformCall(
        key_id=key_id, staff_id=_text(h.get(sg.H_STAFF_ID), 64), staff_name=_text(h.get(sg.H_STAFF_NAME), 200),
        approval_id=_text(h.get(sg.H_APPROVAL), 64), reason=_text(h.get(sg.H_REASON), 1000),
        idempotency_key=h.get(sg.H_IDEMPOTENCY) or None, body=body, method=method, path=request.url.path)
    if method != "GET":
        missing = [name for name, value in (("X-Platform-Staff-Id", call.staff_id),
                                            ("X-Platform-Staff-Name", call.staff_name),
                                            ("X-Platform-Reason", call.reason),
                                            ("Idempotency-Key", call.idempotency_key)) if not value]
        if missing:
            raise FrmError("FRM-GEN-1002", [{"field": name, "message": "required"} for name in missing])
        if not sg.IDEMPOTENCY_KEY.match(call.idempotency_key or ""):
            raise FrmError("FRM-GEN-1002", [{"field": "Idempotency-Key", "message": "invalid"}])
    if ctx is not None:
        ctx.extra["platform_staff"] = call.staff_id
    return call


# ── Idempotency and the call log ────────────────────────────────────────────────

Work = Callable[[], Awaitable[tuple[dict[str, Any], uuid.UUID | None]]]


def _answer(status: int, body: dict[str, Any], replayed: bool = False) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers={"Idempotent-Replayed": "true"} if replayed else None)


def _request_hash(call: PlatformCall) -> str:
    return hashlib.sha256(b"\n".join([call.method.encode(), call.path.encode(), call.body or b""])).hexdigest()


async def run_change(call: PlatformCall, work: Work) -> JSONResponse:
    """Runs a change once per idempotency key and records the call. `work()` returns (data, tenant_id)."""
    request_hash = _request_hash(call)
    now = datetime.now(UTC)
    call_id = uuid7()
    async with db_session("write") as db:
        inserted = (await db.execute(insert(AdminCall).values(
            id=call_id, created_at=now, key_id=call.key_id, idempotency_key=call.idempotency_key,
            request_hash=request_hash, method=call.method, path=call.path[:300], staff_id=call.staff_id,
            staff_name=call.staff_name, approval_id=call.approval_id, reason=call.reason,
        ).on_conflict_do_nothing(index_elements=["idempotency_key"],
                                 index_where=AdminCall.idempotency_key.isnot(None)).returning(AdminCall.id))).first()
        if inserted is None:
            earlier = (await db.execute(select(AdminCall).where(
                AdminCall.idempotency_key == call.idempotency_key).with_for_update())).scalar_one()
            if earlier.request_hash != request_hash:
                raise FrmError("FRM-BILL-1005", [{"field": "Idempotency-Key", "message": "used_for_another_request"}])
            if earlier.completed_at is not None and earlier.status_code is not None and earlier.status_code < 500:
                stored = json.loads(decrypt_secret(earlier.response_enc)) if earlier.response_enc else {}
                return _answer(earlier.status_code, stored, replayed=True)
            if earlier.completed_at is None and now - earlier.created_at < STALE_AFTER:
                raise FrmError("FRM-GEN-1009", [{"field": "Idempotency-Key", "message": "in_progress"}])
            call_id = earlier.id  # failed before (5xx) or abandoned: run it again under the same key
            earlier.completed_at, earlier.status_code, earlier.error_code = None, None, None
            earlier.created_at = now

    status, body, tenant_id, code = 200, {}, None, None
    try:
        data, tenant_id = await work()
        body = {"success": True, "data": data, "meta": {}}
    except FrmError as exc:
        ctx = get_context()
        status, code = exc.status, exc.code
        body = error_body(exc.code, ctx.trace_id if ctx else None, exc.details)
    except Exception:
        log.exception("internal admin call failed", extra={"path": call.path})
        ctx = get_context()
        status, code = 500, "FRM-GEN-5000"
        body = error_body("FRM-GEN-5000", ctx.trace_id if ctx else None)
    async with db_session("write") as db:
        await db.execute(update(AdminCall).where(AdminCall.id == call_id).values(
            completed_at=datetime.now(UTC), status_code=status, error_code=code, tenant_id=tenant_id,
            response_enc=encrypt_secret(json.dumps(body, default=str)) if call.idempotency_key else None))
    return _answer(status, body)


async def log_read(call: PlatformCall, status: int = 200) -> None:
    """GET calls: in the call log too (no idempotency key)."""
    async with db_session("write") as db:
        await db.execute(insert(AdminCall).values(
            id=uuid7(), created_at=datetime.now(UTC), completed_at=datetime.now(UTC), key_id=call.key_id,
            request_hash=_request_hash(call), method=call.method, path=call.path[:300], staff_id=call.staff_id,
            staff_name=call.staff_name, approval_id=call.approval_id, reason=call.reason, status_code=status))


async def audit(db: AsyncSession, call: PlatformCall, tenant_id: uuid.UUID, organisation_id: uuid.UUID,
                action: str, *, resource: dict[str, Any] | None = None,
                changes: list[dict[str, Any]] | None = None, metadata: dict[str, Any] | None = None,
                severity: str | None = None) -> None:
    """The workspace's audit trail: Formalie support, under the staff member's name, with the reason."""
    await record(db, tenant_id=tenant_id, organisation_id=organisation_id, action=action, actor=call.actor,
                 resource=resource, changes=changes, severity=severity,
                 metadata={"via": "platform_admin", "platform_action": call.path.removeprefix(PREFIX),
                           "staff_reason": call.reason or "", "key_id": call.key_id,
                           **({"approval_id": call.approval_id} if call.approval_id else {}), **(metadata or {})})

"""The public API service (port of the mock's server/mock/publicApi.ts; API-CONTRACT → API service → Calling an endpoint;
SECURITY-PROTOCOL §9): what apps and Postman call on `api.formalie.*`. Plain HTTPS + JSON, no portal envelope, no CSRF.

    POST   /{apiKey}/token                      client id + secret → short-lived access token
    GET    /{apiKey}/{endpoint}                 list (page, per_page, sort, filters)
    GET    /{apiKey}/{endpoint}/{recordId}      one
    POST   /{apiKey}/{endpoint}                 a new response (Formalie-Key replays)
    PUT    /{apiKey}/{endpoint}/{recordId}      change accepted answers
    DELETE /{apiKey}/{endpoint}/{recordId}      remove (kept in the audit trail)
    POST   /{apiKey}/{endpoint}/files?field=    one file (multipart/form-data, field "file") → its id for the JSON
    OPTIONS any of them                         a browser's preflight (allowed websites only)

Order of checks (keep it, ENDPOINTS.md): address key → endpoint → access rules (IP, Origin domain, country, anonymous
networks) → rate limit per IP → token → rate limits per token and endpoint → switched on → method → scope → required
headers (Formalie-Key) → the form's rules. Browsers: an Origin from the service's allowed websites gets CORS
headers (that origin, `Vary: Origin`, never `*`) and its preflight a 204; other websites' preflights → FRM-API-1015.
Test tokens never touch real responses: writes are checked and answered, nothing is stored. Every call (not a
preflight) goes to the workspace's request log (`traffic.record_call`), never its token; bodies only when switched on.

Record ids are encrypted references, like everywhere (SECURITY-PROTOCOL §10). The reads and writes are in
gateway_records.py; tokens in gateway_auth.py; the caller (IP, country, networks) in callers.py.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.context import TenantInfo, get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.errors.codes import ERROR_CODES
from app.core.middleware.rate_limit import RateLimiterUnavailable, SlidingWindowLimiter
from app.core.middleware.tenant import BLOCKED_STATUSES
from app.modules.api_service import access as A
from app.modules.api_service import gateway_auth as AUTH
from app.modules.api_service import traffic as TR
from app.modules.api_service.callers import caller_of
from app.modules.api_service.choices import choices_in
from app.modules.api_service.endpoints import all_fields, endpoint_fields_of
from app.modules.api_service.models import ApiAccessRule, ApiEndpoint, ApiService, ApiSettings
from app.modules.api_service.origins import normalise_origin, origin_allowed
from app.modules.api_service.service import schema_of
from app.modules.api_service.tokens import check_call_key, scope_allows
from app.modules.forms.models import Form

log = logging.getLogger("formalie.api.gateway")

JSON_MAX_BYTES = 1_000_000
UPLOAD_MAX_BYTES = 26 * 1024 * 1024  # the largest file a question takes (25 MB) and the multipart around it
KEPT_RAW = 20_000
METHODS = ("GET", "POST", "PUT", "DELETE")
EXPOSED = "Formalie-Token-Expires, Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
PERSONAL_TYPES = TR.PERSONAL_TYPES
_KEY = re.compile(r"[A-Za-z0-9]{6,16}")  # address handles are 10 characters; shorter is never one

limiter = SlidingWindowLimiter()


class GatewayError(Exception):
    """A refused call: its FRM code, details (field and message, plus plain extra facts) and headers."""

    def __init__(self, code: str, details: list[dict[str, Any]] | None = None, headers: dict[str, str] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details or []
        self.headers = headers or {}


class Raced(Exception):
    """Another call with the same Formalie-Key stored its record first: answer as its replay."""


@dataclass
class Call:
    """What a call turned out to be, for the request log and the answer (mock: CallContext)."""

    method: str
    path: str
    tenant: TenantInfo | None = None
    # Plain facts, not rows: a refused call's transaction is rolled back before the answer and the log are written
    endpoint_id: uuid.UUID | None = None
    service_id: uuid.UUID | None = None
    token_id: uuid.UUID | None = None
    token_label: tuple[str, str] | None = None  # the Docs console's (name, mode)
    token_expires: datetime | None = None
    caller: A.AccessCaller | None = None
    raw: bytes = b""
    too_big: bool | None = None  # None until the body is read (once: a raced retry reads it again from here)
    upload: bool = False  # a file upload: its body is the file, never kept in the log
    call_key: str | None = None
    names: dict[str, str] | None = None  # question key → API name, so details name what the app sent
    unknown: set[str] = field(default_factory=set)  # names the endpoint does not know, reported as sent
    rule_id: uuid.UUID | None = None
    rate_limited: bool = False
    personal: set[str] = field(default_factory=set)
    secret_headers: set[str] = field(default_factory=set)
    headers: dict[str, str] = field(default_factory=dict)  # added to the answer, refused or not


@dataclass
class Work:
    """Everything the reads and writes need once the checks passed (gateway_records.py)."""

    db: Any
    request: Request
    call: Call
    tenant: TenantInfo
    endpoint: ApiEndpoint
    form: Form
    schema: dict[str, Any]
    choices: list[dict[str, Any]]
    fields: dict[str, dict[str, Any]]
    label_defs: dict[str, dict[str, Any]]
    key_of: dict[str, str]
    body: dict[str, Any]
    record_ref: str | None
    token: AUTH.Caller
    test: bool
    digest: str = ""  # the POST body's hash, for the Formalie-Key replay


def now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dumps(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


# ── The workspace behind the address key ─────────────────────────────────────────

async def workspace_of(key: str) -> TenantInfo | None:
    """platform.resolve_api_key: the current handle, or the previous one while its grace lasts."""
    if not _KEY.fullmatch(key):
        return None
    async with db_session("read") as db:
        row = (await db.execute(text("SELECT subdomain, status FROM platform.resolve_api_key(:k)"), {"k": key})).first()
    if row is None or row.status in BLOCKED_STATUSES:
        return None
    from app.modules.public.service import _tenant_by_subdomain

    tenant = await _tenant_by_subdomain(row.subdomain)
    return None if tenant is None or tenant.status in BLOCKED_STATUSES else tenant


# ── Rate limits (per IP, token and endpoint; calls per minute) ───────────────────

async def rate_limit(call: Call, kind: str, bucket: str, limit: int | None) -> tuple[int, int] | None:
    """Counts a call against a per-minute limit; over it → 429 with Retry-After. Returns (limit, left)."""
    settings = get_settings()
    if limit is None or not settings.rate_limit_enabled:
        return None
    try:
        result = await limiter.hit(f"api:{bucket}", limit, 60)
    except RateLimiterUnavailable as exc:
        if settings.rate_limit_fail_open:
            log.warning("API rate limiter unavailable, allowing the call", extra={"error": str(exc)})
            return None
        raise GatewayError("FRM-GEN-5003") from exc
    if not result.allowed:
        call.rate_limited = True
        reset = math.ceil(time.time() + result.retry_after)
        raise GatewayError("FRM-GEN-1029", [{"field": kind, "message": f"limit {limit} per minute"}], {
            "Retry-After": str(result.retry_after), "X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset)})
    return limit, result.remaining


# ── Reading the body ─────────────────────────────────────────────────────────────

async def read_body(request: Request, cap: int) -> tuple[bytes, bool]:
    """The body, read up to `cap` bytes; True when there was more (the rest is not read)."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > cap:
            return b"".join(chunks), True
        chunks.append(chunk)
    return b"".join(chunks), False


def parse_json(raw: bytes) -> dict[str, Any]:
    """A JSON object, whatever the Content-Type (owner, 2026-10-06), or FRM-GEN-1001."""
    if not raw:
        return {}

    def refuse(_: str) -> Any:
        raise ValueError("not JSON")
    try:
        parsed = json.loads(raw.decode("utf-8"), parse_constant=refuse)
    except (ValueError, UnicodeDecodeError):
        parsed = None
    if not isinstance(parsed, dict):
        raise GatewayError("FRM-GEN-1001", [{"field": "body", "message": "Send a JSON object."}])
    return parsed


# ── One call ─────────────────────────────────────────────────────────────────────

async def handle_request(request: Request) -> Response:
    """Handles a call and writes it to the workspace's request log (mock: handlePublicApi)."""
    started = time.perf_counter()
    method = request.method.upper()
    path = request.url.path
    call = Call(method=method, path=path)
    status, body = await _answer(request, call)
    if call.token_id is not None:
        # The token's expiry with every answer (owner, 2026-10-06: an expiry tracker in the data, never a surprise)
        expires = call.token_expires
        call.headers["Formalie-Token-Expires"] = iso(expires) if expires else "never"
        if isinstance(body, dict) and "data" in body:
            days = max(0, math.ceil((expires - now()).total_seconds() / 86_400)) if expires else None
            body["meta"] = {**(body.get("meta") or {}), "token_expires_at": iso(expires) if expires else None,
                            "token_expires_in_days": days}
    request_id = str(uuid.uuid4())
    headers = {**call.headers, "Cache-Control": "no-store", "X-Request-Id": request_id}
    if status == 204:
        response = Response(status_code=204, headers=headers)
    else:
        response = Response(dumps(body), status_code=status, headers=headers,
                            media_type="application/json; charset=utf-8")
    ctx = get_context()
    if ctx is not None:
        ctx.tenant = call.tenant
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            ctx.error_code = body["error"].get("code")
        ctx.rate_limited = ctx.rate_limited or call.rate_limited
    # A browser's preflight is not a call: it stays out of the logs and the counts
    if call.tenant is not None and method != "OPTIONS":
        await _log(request, call, status, body, request_id, started)
    return response


async def _answer(request: Request, call: Call) -> tuple[int, Any]:
    for attempt in range(2):
        try:
            return await _handle(request, call)
        except Raced:
            if attempt:
                break
        except GatewayError as error:
            call.headers.update(error.headers)
            return _failure(call, error)
        except FrmError as error:
            return _failure(call, GatewayError(error.code, list(error.details)))
        except Exception:
            log.exception("FRM-GEN-5000 public API call failed", extra={"error_code": "FRM-GEN-5000"})
            return _failure(call, GatewayError("FRM-GEN-5000"))
    return _failure(call, GatewayError("FRM-GEN-5000"))


def _failure(call: Call, error: GatewayError) -> tuple[int, Any]:
    """Details name what the app sent: the API name, not the question key (an unknown name exactly as sent)."""
    names = call.names
    details = [{**d, "field": d["field"] if d["field"] in call.unknown else names.get(d["field"], d["field"])}
               for d in error.details] if names else error.details
    definition = ERROR_CODES[error.code]
    return definition.status, {"error": {"code": error.code, "message": definition.message, "details": details}}


async def _log(request: Request, call: Call, status: int, body: Any, request_id: str, started: float) -> None:
    tenant = call.tenant
    assert tenant is not None
    caller = call.caller
    ctx = get_context()
    error = body.get("error") if isinstance(body, dict) else None
    entry = TR.ApiCall(
        method=call.method, path=call.path, status=status, duration_ms=int((time.perf_counter() - started) * 1000),
        ip=(caller.ip if caller else None) or (ctx.client_ip if ctx else None) or "0.0.0.0",
        request_id=call.call_key or request_id, code=error.get("code") if isinstance(error, dict) else None,
        endpoint_id=call.endpoint_id, service_id=call.service_id, token_id=call.token_id, token_label=call.token_label,
        rule_id=call.rule_id, rate_limited=call.rate_limited, country=caller.country if caller else None,
        origin=request.headers.get("origin"), user_agent=(request.headers.get("user-agent") or "")[:200],
        headers=dict(request.headers.items()), secret_headers=call.secret_headers,
        request_raw=call.raw[:KEPT_RAW].decode("utf-8", "replace") if call.raw and not call.upload else None,
        response_body=body,
        personal=call.personal)
    try:
        async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
            await TR.record_call(db, tenant.id, tenant.organisation_id, entry)
    except Exception:  # noqa: BLE001 (the answer is given; a lost log line must never fail the call)
        log.exception("API request log write failed")


async def _handle(request: Request, call: Call) -> tuple[int, Any]:
    parts = request.url.path.strip("/").split("/")
    key = parts[0] if parts else ""
    name = parts[1] if len(parts) > 1 else ""
    record_ref = parts[2] if len(parts) > 2 else None
    method = call.method
    tenant = await workspace_of(key)
    call.tenant = tenant
    if tenant is None:
        raise GatewayError("FRM-API-1006", [{"field": "address_key", "message": "unknown"}])
    if len(parts) > 3:
        raise GatewayError("FRM-API-1006", [{"field": "path", "message": "too_long"}])
    async with db_session("write", tenant_id=tenant.id, organisation_id=tenant.organisation_id) as db:
        settings = (await db.execute(select(ApiSettings).where(ApiSettings.tenant_id == tenant.id))).scalar_one_or_none()
        services = list((await db.execute(select(ApiService).where(
            ApiService.tenant_id == tenant.id, ApiService.deleted_at.is_(None)))).scalars())
        endpoints = list((await db.execute(select(ApiEndpoint).where(
            ApiEndpoint.tenant_id == tenant.id, ApiEndpoint.deleted_at.is_(None)))).scalars())
        target = next((e for e in endpoints if e.name == name), None) if name != "token" else None

        # Browsers (leftovers L6): only the service's allowed websites get CORS answers; their preflights stop here.
        # Calls without an Origin (server apps, mobile apps, Postman) go on as before.
        origin = request.headers.get("origin")
        if origin:
            if target is not None:
                own = next((s for s in services if s.id == target.service_id), None)
                allowed = list(own.allowed_origins or []) if own else []
            else:
                allowed = [o for s in services for o in (s.allowed_origins or [])]
            if origin_allowed(origin, allowed):
                call.headers.update({"Access-Control-Allow-Origin": normalise_origin(origin) or "", "Vary": "Origin",
                                     "Access-Control-Expose-Headers": EXPOSED})
                if method == "OPTIONS":
                    call.headers.update({
                        "Access-Control-Allow-Methods": ", ".join([*target.methods, "OPTIONS"]) if target else "POST, OPTIONS",
                        "Access-Control-Allow-Headers": ", ".join(["Authorization", "Content-Type", "Formalie-Key",
                                                                   "X-Formalie-Signature", "X-Formalie-Timestamp",
                                                                   *[h["name"] for h in (target.headers if target else []) or []]]),
                        "Access-Control-Max-Age": "600",
                    })
                    return 204, None
            elif method == "OPTIONS":
                raise GatewayError("FRM-API-1015", [{"field": "origin", "message": "not an allowed website"}])

        # A file upload carries multipart/form-data, every other write a JSON object (1 MB at most)
        upload = record_ref == "files" and method == "POST"
        call.upload = upload
        body: dict[str, Any] = {}
        too_big = False
        if method in ("POST", "PUT"):
            if call.too_big is None:
                call.raw, call.too_big = await read_body(request, UPLOAD_MAX_BYTES if upload else JSON_MAX_BYTES)
            too_big = call.too_big
            if too_big and not upload:
                raise GatewayError("FRM-API-1018", [{"field": "body", "message": "1 MB"}])
            if not upload:
                body = parse_json(call.raw)

        if name == "token" and record_ref is None:
            if method != "POST":
                raise GatewayError("FRM-API-1008")
            # The token address: only rules for everything apply, and the per-IP limit
            caller = caller_of(request.headers)
            call.caller = caller
            rules = [_rule(r) for r in await _rules(db, tenant.id) if r.scope_type == "all"]
            decision = A.decide_access(rules, caller)
            if not decision["allowed"]:
                raise GatewayError("FRM-API-1015", [{"field": decision["reason"], "message": (decision["rule"] or {}).get("value") or "no allow rule matched"}])
            await rate_limit(call, "ip", f"{tenant.id}:ip:{caller.ip}", settings.rate_per_ip if settings else None)
            try:
                return 200, await AUTH.issue_access_token(db, tenant.id, request.headers, body)
            except AUTH.Refused as refused:
                raise GatewayError(refused.code, refused.details) from None

        endpoint = target
        if endpoint is None:
            raise GatewayError("FRM-API-1006", [{"field": "endpoint", "message": "unknown"}])
        call.endpoint_id, call.service_id = endpoint.id, endpoint.service_id
        call.secret_headers = {h["name"] for h in endpoint.headers or []}
        # Access rules: a block refuses; when allow rules apply, one must match
        caller = caller_of(request.headers)
        call.caller = caller
        all_rules = await _rules(db, tenant.id)
        applies = A.rules_for([_rule(r) for r in all_rules], str(endpoint.id), str(endpoint.service_id))
        decision = A.decide_access(applies, caller)
        if decision["rule"]:
            call.rule_id = uuid.UUID(decision["rule"]["id"])
        if not decision["allowed"]:
            raise GatewayError("FRM-API-1015", [{"field": decision["reason"], "message": (decision["rule"] or {}).get("value") or "no allow rule matched"}])
        await rate_limit(call, "ip", f"{tenant.id}:ip:{caller.ip}", settings.rate_per_ip if settings else None)
        try:
            token = await AUTH.caller_token(db, tenant.id, request.headers)
        except AUTH.Refused as refused:
            raise GatewayError(refused.code, refused.details) from None
        if isinstance(token, AUTH.ConsoleToken):
            call.token_label = (token.name, token.mode)
        else:
            call.token_id, call.token_expires = token.id, token.expires_at
        left = await rate_limit(call, "token", f"{tenant.id}:token:{token.id}", settings.rate_per_token if settings else None)
        await rate_limit(call, "endpoint", f"{tenant.id}:endpoint:{endpoint.id}", settings.rate_per_endpoint if settings else None)
        if left:
            call.headers.update({"X-RateLimit-Limit": str(left[0]), "X-RateLimit-Remaining": str(left[1])})

        service = next((s for s in services if s.id == endpoint.service_id), None)
        form = (await db.execute(select(Form).where(Form.tenant_id == tenant.id, Form.id == endpoint.form_id,
                                                    Form.deleted_at.is_(None), Form.purged_at.is_(None)))).scalar_one_or_none()
        schema = await schema_of(db, tenant.id, form, endpoint.version) if form is not None else None
        if schema is not None:
            from app.modules.lists.service import full_schema

            schema = await full_schema(db, tenant.id, schema)
        if service is None or service.status != "active":
            raise GatewayError("FRM-API-1007", [{"field": "service", "message": "switched_off"}])
        if form is None or form.status != "published" or schema is None:
            raise GatewayError("FRM-API-1007", [{"field": "form", "message": "not_published"}])
        if "api" not in (list(form.channels) if form.channels else ["link", "embed", "api"]):
            raise GatewayError("FRM-API-1007", [{"field": "form", "message": "not_for_api"}])
        # Not live yet: only test tokens get through, so it can be tried before going live (owner, 2026-10-06)
        if endpoint.status != "active" and token.mode != "test":
            raise GatewayError("FRM-API-1007", [{"field": "endpoint", "message": "not_live"}])

        # The choices as the portal shows them, worked out from the form; API names ↔ question keys
        choices = endpoint_fields_of(schema, endpoint.fields)
        key_of = {f["name"]: f["key"] for f in choices}
        call.names = {f["key"]: f["name"] for f in choices}
        fields = {f["key"]: f for f in all_fields(schema)}
        personal = {k for k, f in fields.items() if f.get("type") in PERSONAL_TYPES}
        call.personal = personal | {call.names[k] for k in personal if k in call.names}
        call.unknown = {n for n in body if n not in key_of}
        body = {key_of[n]: v for n, v in body.items() if n in key_of}

        if method not in METHODS or method not in endpoint.methods or (
                method == "POST" if record_ref is not None and not upload else method in ("PUT", "DELETE")):
            raise GatewayError("FRM-API-1008")
        if not _scope_allows(token, endpoint, method):
            scopes = token.scopes
            if scopes["methods"] and method not in scopes["methods"]:
                part = {"field": "method", "message": "not_allowed_for_token"}
            elif scopes["endpoints"] and str(endpoint.id) not in scopes["endpoints"]:
                part = {"field": "endpoint", "message": "not_allowed_for_token"}
            else:
                known = {str(s.id) for s in services}
                part = {"field": "service", "message": "token_service_deleted" if any(i not in known for i in scopes["services"])
                        else "not_allowed_for_token"}
            raise GatewayError("FRM-API-1009", [part])
        # The headers (owner, 2026-10-06): Authorization (checked above), Content-Type (JSON by default) and the
        # Formalie-Key, a new unique id: required on POST, checked on GET, PUT and DELETE when sent. No other headers.
        call_key = (request.headers.get("formalie-key") or "").strip()
        if method == "POST" or call_key:
            problem = check_call_key(call_key)
            if problem:
                raise GatewayError("FRM-API-1011", [{"field": "Formalie-Key", "message": problem}])
        call.call_key = call_key or None
        # Choices may be sent by label as records show them (owner 2026-10-08): labels become option values
        body = choices_in(list(fields.values()), body)
        work = Work(db=db, request=request, call=call, tenant=tenant, endpoint=endpoint, form=form, schema=schema,
                    choices=choices, fields=fields, label_defs=await _label_defs(db, tenant.id, fields), key_of=key_of,
                    body=body, record_ref=record_ref, token=token, test=token.mode == "test")
        from app.modules.api_service import gateway_records as RECORDS

        if upload:
            return await RECORDS.upload(work, too_big)
        if method == "GET":
            return await RECORDS.read(work)
        return await RECORDS.write(work)


def _scope_allows(token: AUTH.Caller, endpoint: ApiEndpoint, method: str) -> bool:
    return scope_allows(token.scopes, str(endpoint.id), str(endpoint.service_id), method)


async def _rules(db: Any, tenant_id: uuid.UUID) -> list[ApiAccessRule]:
    return list((await db.execute(select(ApiAccessRule).where(
        ApiAccessRule.tenant_id == tenant_id, ApiAccessRule.deleted_at.is_(None)).order_by(
        ApiAccessRule.created_at.desc()))).scalars())


def _rule(rule: ApiAccessRule) -> dict[str, Any]:
    return {"id": str(rule.id), "enabled": rule.enabled, "action": rule.action, "kind": rule.kind,
            "values": list(rule.values or []),
            "scope": {"type": rule.scope_type, "id": str(rule.scope_id) if rule.scope_id else None}}


async def _label_defs(db: Any, tenant_id: uuid.UUID, fields: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Labels for records: the form's options, plus options of its lists the form no longer offers (retired since),
    so older answers still read as what was chosen."""
    from app.modules.lists.service import lists_by_id

    ids = {str(f["option_set_id"]) for f in fields.values() if f.get("option_set_id")}
    lists = await lists_by_id(db, tenant_id, ids) if ids else {}
    out: dict[str, dict[str, Any]] = {}
    for key, fld in fields.items():
        lst = lists.get(str(fld.get("option_set_id"))) if fld.get("option_set_id") else None
        known = {o.get("value") for o in fld.get("options") or []}
        older = [{"value": o["value"], "label": o["label"]} for o in (lst["options"] if lst else [])
                 if o.get("value") not in known]
        out[key] = {**fld, "options": [*(fld.get("options") or []), *older]} if older else fld
    return out


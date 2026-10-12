"""The Docs console (mock: routes/apiDocs.ts, F13 M5): `POST /api-endpoints/{id}/try` sends one call through the
public API service with a test token that lives a minute. Every check runs (access rules from the admin's own
address, limits, the Formalie-Key, the form's rules); a test token stores nothing. The call is in the request log as
the Docs console's. Admins only.

The call goes to the API service's own app in this process (app/gateway.py), exactly as an app's call would arrive.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.core.security.refs import get_codec
from app.modules.api_service import service as S
from app.modules.api_service.gateway_auth import issue_console_token
from app.modules.api_service.models import ApiEndpoint, ApiSettings
from app.modules.api_service.router import scope
from app.modules.auth.sessions import Principal, require_admin

router = APIRouter(tags=["api service"])

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
SHOWN = ("x-request-id", "x-ratelimit-limit", "x-ratelimit-remaining", "retry-after", "content-type",
         "formalie-token-expires")
try_schema = z.obj(
    method=z.enum(list(S.API_METHODS)),
    record_id=z.string().trim().max(100).nullable().optional(),
    body=z.unknown().optional(),
    headers=z.record(z.string().max(64), z.string().max(500)).optional(),
)

_gateway: Any = None


def gateway_app() -> Any:
    """The API service's app, made once per process (no request log of its own: this route is logged)."""
    global _gateway
    if _gateway is None:
        from app.gateway import create_gateway_app

        _gateway = create_gateway_app(get_settings(), request_log_shipper=None, configure=False)
    return _gateway


def set_gateway_app(app: Any) -> None:
    """Tests: the gateway made with their settings."""
    global _gateway
    _gateway = app


@router.post("/api-endpoints/{endpoint_id}/try", dependencies=[rate_limit("api-try", per_minute=60)])
async def try_endpoint(endpoint_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    import json

    values = try_schema.parse(await request.json())
    wanted = S.path_uuid(endpoint_id)
    async with db_session("read", **scope(principal)) as db:
        endpoint = (await db.execute(select(ApiEndpoint).where(
            ApiEndpoint.tenant_id == principal.tenant.id, ApiEndpoint.id == wanted,
            ApiEndpoint.deleted_at.is_(None)))).scalar_one_or_none() if wanted else None
        settings = (await db.execute(select(ApiSettings).where(
            ApiSettings.tenant_id == principal.tenant.id))).scalar_one_or_none()
    if endpoint is None or settings is None:
        raise FrmError("FRM-GEN-1004")
    # The portal turns references into ids on the way in; the public API expects the reference again
    record = values.get("record_id") or ""
    if record and UUID.match(record):
        record = get_codec().encode_id(record)
    headers: dict[str, str] = {**(values.get("headers") or {}), "authorization": f"Bearer {issue_console_token(principal.tenant.id)}"}
    # The three headers every call sends: Content-Type (always) and a Formalie-Key when the console did not give one
    headers = {k: v for k, v in headers.items() if k.lower() not in ("content-type", "host", "content-length")}
    headers["content-type"] = "application/json"
    if not any(k.lower() == "formalie-key" for k in headers):
        headers["formalie-key"] = str(uuid.uuid4())
    writes = values["method"] in ("POST", "PUT")
    path = f"/{settings.api_key}/{endpoint.name}" + (f"/{record}" if record else "")
    ctx = get_context()
    caller_ip = (ctx.client_ip if ctx else None) or "0.0.0.0"
    transport = httpx.ASGITransport(app=gateway_app(), client=(caller_ip, 0))
    started = time.perf_counter()
    async with httpx.AsyncClient(transport=transport, base_url=f"https://api.{get_settings().root_domain}") as client:
        response = await client.request(values["method"], path, headers=headers,
                                        content=json.dumps(values.get("body") if values.get("body") is not None else {})
                                        if writes else None)
    try:
        body = response.json() if response.content else None
    except ValueError:
        body = None
    return ok({
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "headers": {name: response.headers[name] for name in SHOWN if response.headers.get(name)},
        "body": body,
    })

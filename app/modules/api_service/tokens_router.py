"""API tokens (mock: routes/apiService.ts → Tokens, F13 M2; API-CONTRACT → API service).

    GET    /api-tokens                    list (q, sort, filter[status|mode|kind]) · /insights · /{id}
    POST   /api-tokens                    a token; its secrets come back once     · PATCH · DELETE (revoked / expired)
    POST   /api-tokens/{id}/rotate        new secrets (shown once); the old ones work for a grace period
    POST   /api-tokens/{id}/revoke        stops it at once
    POST   /api-tokens/{id}/reveal        its secret again, after the password (owner, 2026-10-06)

Only a SHA-256 hash of each secret is looked up; the secret itself is kept encrypted so it can be shown again after
the password. A webhook token is live and calls nothing (owner, 2026-10-06).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.core.security.limits import rate_limit
from app.modules.api_service import service as S
from app.modules.api_service import tokens as T
from app.modules.api_service.models import ApiToken
from app.modules.api_service.router import audit, page, scope
from app.modules.auth.confirm import confirm_password
from app.modules.auth.sessions import Principal, require_admin

router = APIRouter(tags=["api service"])

ISO_DATETIME = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?Z\Z"
_scopes = z.obj(services=z.array(z.string()).max(100), endpoints=z.array(z.string()).max(500),
                methods=z.array(z.enum(list(T.API_METHODS))).max(4))
_lifetime = z.number().int().refine(lambda n: n in T.TOKEN_LIFETIMES).nullable().optional()
_expires = z.string().regex(ISO_DATETIME, "Invalid ISO datetime").nullable()
token_schema = z.obj(name=z.string().trim().min(1).max(80), kind=z.enum(list(T.API_TOKEN_KINDS)),
                     mode=z.enum(list(T.API_TOKEN_MODES)), scopes=_scopes, expires_at=_expires, lifetime_minutes=_lifetime)
token_patch_schema = z.obj(name=z.string().trim().min(1).max(80).optional(), scopes=_scopes.optional(),
                           expires_at=_expires.optional(), lifetime_minutes=_lifetime)
rotate_schema = z.obj(grace_hours=z.number().int().refine(lambda n: n in T.ROTATION_GRACE_HOURS))


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _check(store: S.Store, scopes: dict[str, list[str]], expires_at: str | None, *, saved: bool = False) -> dict[str, list[str]]:
    """Scopes name services and endpoints of this workspace (sent as references, or the token's saved ones); an
    expiry is in the future and within 2 years. Returns the scopes with every id in its one form."""
    read = S.path_uuid if saved else S.ref_uuid
    services = [read(i) for i in scopes["services"]]
    if any(i is None or store.service(i) is None for i in services):
        raise FrmError("FRM-GEN-1002", [{"field": "scopes", "message": "services"}])
    endpoints = [read(i) for i in scopes["endpoints"]]
    if any(i is None or store.endpoint(i) is None for i in endpoints):
        raise FrmError("FRM-GEN-1002", [{"field": "scopes", "message": "endpoints"}])
    if expires_at:
        at, now = _at(expires_at), datetime.now(UTC)
        if at <= now or at > now + timedelta(days=731):
            raise FrmError("FRM-GEN-1002", [{"field": "expires_at", "message": "range"}])
    return {"services": [str(i) for i in services], "endpoints": [str(i) for i in endpoints],
            "methods": list(scopes["methods"])}


def _issue(token: ApiToken) -> dict[str, str]:
    """New secrets for a token: the bearer token or client secret."""
    secret = T.new_secret(token.kind, token.mode)
    token.secret_hash, token.secret_enc, token.preview = T.hash_secret(secret), encrypt_secret(secret), T.secret_preview(secret)
    token.signing_secret_enc = None
    return {"client_secret": secret} if token.kind == "client" else {"token": secret}


def _find(store: S.Store, raw: str) -> ApiToken:
    wanted = S.path_uuid(raw)
    found = next((t for t in store.tokens if t.id == wanted), None)
    if found is None:
        raise FrmError("FRM-GEN-1004")
    return found


def _resource(token: ApiToken) -> dict[str, Any]:
    return {"type": "api_token", "id": str(token.id), "name": token.name}


@router.get("/api-tokens", dependencies=[rate_limit("api-tokens", per_minute=120)])
async def list_api_tokens(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    rows = [S.token_view(store, t) for t in store.tokens]
    rows = [r for r in rows if S.in_list(query.get("filter[status]"), r["status"])
            and S.in_list(query.get("filter[mode]"), r["mode"]) and S.in_list(query.get("filter[kind]"), r["kind"])]
    rows = S.sort_rows(rows, query.get("sort") or "-created_at")
    return page(query, rows, lambda r, q: q in f"{r['name']} {r['preview']}".lower())


@router.get("/api-tokens/insights", dependencies=[rate_limit("api-tokens", per_minute=60)])
async def api_token_insights(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    views = [S.token_view(store, t) for t in store.tokens]
    use = S.usage()
    cutoff = datetime.now(UTC) - timedelta(days=90)
    return ok({
        "total": len(views), "by_status": {s: sum(1 for v in views if v["status"] == s) for s in T.API_TOKEN_STATUSES},
        "by_mode": {m: sum(1 for v in views if v["mode"] == m) for m in T.API_TOKEN_MODES},
        "calls_30d": use["calls_30d"], "previous_30d": use["previous_30d"], "daily": use["daily"],
        # Tokens unused for 90 days (worth revoking)
        "unused_90d": sum(1 for t in store.tokens if S.token_status(t) in ("active", "expiring")
                          and (t.last_used_at or t.created_at) < cutoff),
    })


@router.get("/api-tokens/{token_id}", dependencies=[rate_limit("api-tokens", per_minute=240)])
async def get_api_token(token_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
    return ok(S.token_view(store, _find(store, token_id)))


@router.post("/api-tokens", status_code=201, dependencies=[rate_limit("api-tokens-write", per_minute=30)])
async def create_api_token(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    values = token_schema.parse(await request.json())
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        scopes = _check(store, values["scopes"], values.get("expires_at"))
        kind = values["kind"]
        # A webhook token is live and calls nothing: no scope at all (owner, 2026-10-06)
        mode = "live" if kind == "webhook" else values["mode"]
        token = ApiToken(tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id, name=values["name"],
                         kind=kind, mode=mode, secret_hash="", preview="",
                         client_id=T.new_secret("client_id", mode) if kind == "client" else None,
                         lifetime_minutes=(values.get("lifetime_minutes") or 15) if kind == "client" else None,
                         signing=False, scopes={"services": [], "endpoints": [], "methods": []} if kind == "webhook" else scopes,
                         expires_at=_at(values["expires_at"]) if values.get("expires_at") else None,
                         created_by=principal.user.id, updated_by=principal.user.id)
        secrets = _issue(token)
        db.add(token)
        await db.flush()
        await audit(db, principal, "api.token_created", _resource(token), metadata={"kind": token.kind, "mode": token.mode})
        store.tokens.insert(0, token)
        return ok({"token": S.token_view(store, token), "secrets": secrets})


@router.patch("/api-tokens/{token_id}", dependencies=[rate_limit("api-tokens-write", per_minute=60)])
async def update_api_token(token_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        token = _find(store, token_id)
        if token.revoked_at:
            raise FrmError("FRM-API-1004")
        values = token_patch_schema.parse(await request.json())
        scopes = _check(store, values["scopes"] if "scopes" in values else token.scopes, values.get("expires_at"),
                        saved="scopes" not in values)
        before = token.name
        if "name" in values:
            token.name = values["name"]
        if "scopes" in values:
            token.scopes = scopes
        if "expires_at" in values:
            token.expires_at = _at(values["expires_at"]) if values["expires_at"] else None
        if values.get("lifetime_minutes") is not None and token.kind == "client":
            token.lifetime_minutes = values["lifetime_minutes"]
        token.updated_at, token.updated_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.token_updated", _resource(token),
                    changes=[{"field": "name", "before": before, "after": token.name}] if before != token.name else [])
        await db.flush()
        return ok(S.token_view(store, token))


@router.post("/api-tokens/{token_id}/rotate", dependencies=[rate_limit("api-tokens-write", per_minute=20)])
async def rotate_api_token(token_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        token = _find(store, token_id)
        if token.revoked_at:
            raise FrmError("FRM-API-1004")
        grace = rotate_schema.parse(await request.json())["grace_hours"]
        token.previous_hash = token.secret_hash if grace else None
        token.rotating_until = datetime.now(UTC) + timedelta(hours=grace) if grace else None
        secrets = _issue(token)
        token.updated_at, token.updated_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.token_rotated", _resource(token), metadata={"grace_hours": str(grace)})
        await db.flush()
        return ok({"token": S.token_view(store, token), "secrets": secrets})


@router.post("/api-tokens/{token_id}/revoke", dependencies=[rate_limit("api-tokens-write", per_minute=30)])
async def revoke_api_token(token_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        token = _find(store, token_id)
        if not token.revoked_at:
            token.revoked_at = datetime.now(UTC)
            token.previous_hash, token.rotating_until = None, None
            token.updated_by = principal.user.id
            await audit(db, principal, "api.token_revoked", _resource(token))
            await db.flush()
        return ok(S.token_view(store, token))


@router.delete("/api-tokens/{token_id}", dependencies=[rate_limit("api-tokens-write", per_minute=30)])
async def delete_api_token(token_id: str, principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        token = _find(store, token_id)
        if S.token_status(token) not in ("revoked", "expired"):
            raise FrmError("FRM-API-1005")
        token.deleted_at, token.deleted_by = datetime.now(UTC), principal.user.id
        await audit(db, principal, "api.token_deleted", _resource(token))
    return ok({"deleted": True})


@router.post("/api-tokens/{token_id}/reveal", dependencies=[rate_limit("api-tokens-reveal", per_minute=10)])
async def reveal_api_token(token_id: str, request: Request, principal: Principal = Depends(require_admin)) -> Any:
    """The token's secret again, after the password (owner, 2026-10-06)."""
    body = await request.json()
    async with db_session("write", **scope(principal)) as db:
        store = await S.Store(principal.tenant.id).load(db, forms=False)
        token = _find(store, token_id)
        if token.revoked_at:
            raise FrmError("FRM-API-1004")
        await confirm_password(principal.user, body.get("password") if isinstance(body, dict) else None)
        if not token.secret_enc:
            raise FrmError("FRM-API-1016")
        await audit(db, principal, "api.token_revealed", _resource(token))
        secret = decrypt_secret(token.secret_enc)
    return ok({"token": secret} if token.kind == "static" else {"client_secret": secret})

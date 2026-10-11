"""10. RequestLog: every request in full, recorded when its response is done (BACKEND-SPEC §8.1; owner 2026-10-11).

Sits just inside RequestContext, so requests refused by the rate limit, tenant or envelope layers are recorded too.
One record per request: who (workspace, user, session), what (method, host, path, route, query, every header,
the body), the outcome (status, sizes, duration, error code, response headers, the response body of errors),
where from (real client IP, peer, forwarding chain; location and device are added by the writer) and security
flags. Secrets are masked at capture (app/modules/logs/capture.py). The record goes to the request-log shipper
(database, Celery or file; never blocking), and a one-line summary goes to the normal log files.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from app.core.config import Settings, get_settings
from app.core.context import get_context
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send, header
from app.core.middleware.tenant import resolve_host_context
from app.modules.logs.capture import attack_flags, body_record, mask_headers, parse_query, response_body

log = logging.getLogger("formalie.request")


def route_template(scope: Scope) -> str | None:
    """The matched route with its prefix, e.g. /api/v1/forms/{id} (FastAPI keeps a nested router's own path)."""
    route = scope.get("route")
    template = getattr(route, "path_format", None) or getattr(route, "path", None)
    if not template:
        return None
    path: str = scope.get("path", "")
    try:
        concrete = template.format(**{k: str(v) for k, v in (scope.get("path_params") or {}).items()})
    except (KeyError, IndexError, ValueError):
        return template
    return path[: len(path) - len(concrete)] + template if path.endswith(concrete) else template


def _masked_url(url: str | None, path: str) -> str | None:
    """A referer keeps its query, with secret values (tickets, tokens, codes) masked."""
    if not url or "?" not in url:
        return url
    base, query = url.split("?", 1)
    masked = parse_query(query, path) or {}
    return f"{base}?{urlencode(masked, doseq=True)}"


class _BodyTap:
    """Hashes every byte that passes, keeps the first `limit` bytes."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.size = 0
        self.kept = bytearray()
        self.sha = hashlib.sha256()

    def add(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.size += len(chunk)
        self.sha.update(chunk)
        room = self.limit - len(self.kept)
        if room > 0:
            self.kept += chunk[:room]

    @property
    def truncated(self) -> bool:
        return self.size > len(self.kept)


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp, shipper: Any | None = None, settings: Settings | None = None) -> None:
        self.app = app
        self.shipper = shipper
        self.settings = settings or get_settings()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        occurred_at = datetime.now(UTC)
        limit = self.settings.request_log_body_max_bytes
        request_tap = _BodyTap(limit)
        response_tap = _BodyTap(limit)
        response: dict[str, Any] = {"status": 500, "headers": []}
        keep_response = self.settings.request_log_response_bodies

        # Read the whole body first, so it is recorded even when no route reads it (404, refused requests),
        # then hand the same messages to the app. API bodies are small: files go straight to storage.
        buffered: list[Message] = []
        if scope.get("method") in ("POST", "PUT", "PATCH", "DELETE"):
            while True:
                message = await receive()
                buffered.append(message)
                if message["type"] != "http.request":
                    break
                request_tap.add(message.get("body", b""))
                if not message.get("more_body"):
                    break

        async def tapped_receive() -> Message:
            if buffered:
                return buffered.pop(0)
            message = await receive()
            if message["type"] == "http.request":
                request_tap.add(message.get("body", b""))
            return message

        async def tapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if keep_response == "all" or (keep_response == "errors" and response["status"] >= 400):
                    response_tap.add(body)
                else:
                    response_tap.size += len(body)
            await send(message)

        try:
            await self.app(scope, tapped_receive, tapped_send)
        finally:
            try:
                self._record(scope, occurred_at, request_tap, response_tap, response)
            except Exception:  # noqa: BLE001 (logging must never break a request)
                log.exception("request log record failed")

    def _record(self, scope: Scope, occurred_at: datetime, request_tap: _BodyTap, response_tap: _BodyTap,
                response: dict[str, Any]) -> None:
        ctx = get_context()
        path: str = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode("latin-1")
        status: int = response["status"]
        request_headers = mask_headers(scope.get("headers") or [])
        if "referer" in request_headers:  # its query may carry tickets or tokens
            request_headers["referer"] = _masked_url(request_headers["referer"], path) or ""
        response_headers = mask_headers(response["headers"])
        decrypted = ctx.decrypted_payload if ctx else None
        body = body_record(request_headers.get("content-type"), bytes(request_tap.kept), request_tap.size,
                           request_tap.sha.hexdigest(), request_tap.truncated, path, decrypted)
        if decrypted is not None and isinstance(decrypted.get("query"), dict):
            query: Any = parse_query(urlencode(decrypted["query"], doseq=True), path)
        else:
            query = parse_query(query_string, path)

        flags = set(ctx.flags) if ctx else set()
        flags |= attack_flags(path, query_string, bytes(request_tap.kept).decode("utf-8", "replace"))
        if request_tap.truncated:
            flags.add("oversized")
        client = request_headers.get("x-formalie-client") or ""
        client_app, _, client_version = client.partition("/")
        host_context = ctx.extra.get("host_context") if ctx else None
        if host_context is None and ctx is not None and ctx.host:
            # Refused before the tenant layer (rate limit): still record which workspace host it was for.
            host_context = resolve_host_context(ctx.host, root_domain=self.settings.root_domain,
                                                manage_subdomain=self.settings.manage_subdomain)
        tenant = ctx.tenant if ctx else None

        record: dict[str, Any] = {
            "id": ctx.trace_id if ctx else None,
            "occurred_at": occurred_at.isoformat(),
            "trace_id": ctx.trace_id if ctx else "",
            "tenant_id": str(tenant.id) if tenant else None,
            "organisation_id": str(tenant.organisation_id) if tenant else None,
            "user_id": str(ctx.user_id) if ctx and ctx.user_id else None,
            "session_id": str(ctx.session_id) if ctx and ctx.session_id else None,
            "scheme": scope.get("scheme"),
            "http_version": scope.get("http_version"),
            "method": scope.get("method", ""),
            "host": ctx.host if ctx else request_headers.get("host"),
            "host_kind": (ctx.host_kind if ctx else None) or getattr(host_context, "kind", None),
            "subdomain": (tenant.subdomain if tenant else getattr(host_context, "subdomain", None)),
            "path": path,
            "route": route_template(scope),
            "query": query,
            "status": status,
            "duration_ms": round((time.perf_counter() - ctx.started_at) * 1000, 2) if ctx else None,
            "request_bytes": request_tap.size,
            "response_bytes": response_tap.size,
            "error_code": ctx.error_code if ctx else None,
            "rate_limited": ctx.rate_limited if ctx else False,
            "flags": sorted(flags) or None,
            "client_ip": ctx.client_ip if ctx else None,
            "peer_ip": ctx.peer_ip if ctx else None,
            "forwarded_for": request_headers.get("x-forwarded-for"),
            "proxy_trusted": ctx.proxy_trusted if ctx else False,
            "user_agent": request_headers.get("user-agent"),
            "referer": request_headers.get("referer"),
            "origin": request_headers.get("origin"),
            "client_app": client_app[:100] or None,
            "client_version": client_version[:50] or None,
            "request_headers": request_headers,
            **body,
            "response_headers": response_headers,
            "response_content_type": response_headers.get("content-type"),
            "response_body": response_body(response_headers.get("content-type"), bytes(response_tap.kept),
                                           response_tap.truncated) if response_tap.kept else None,
        }
        if self.shipper is not None and self.settings.request_log_enabled:
            self.shipper.submit(record)

        level = logging.ERROR if status >= 500 else logging.WARNING if status in (401, 403, 429) else logging.INFO
        log.log(level, "%s %s %s", record["method"], path, status, extra={"request": {
            "route": record["route"], "status": status, "duration_ms": record["duration_ms"],
            "client_ip": record["client_ip"], "host": record["host"], "error_code": record["error_code"],
            "flags": record["flags"],
        }})

"""10. RequestLog: one structured line per request, written when the response is done (BACKEND-SPEC §8.1).

Sits just inside RequestContext so requests refused by the rate limit, tenant or envelope layers are logged too.
B2 adds the `request_logs` table (through the `logs` Celery queue, file fallback when the broker is down),
geo from MaxMind and the body summary. Never logs bodies, tokens or the query string's values.
"""

from __future__ import annotations

import logging
import time

from app.core.context import get_context
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send, header

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


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        status = 500
        response_bytes = 0

        async def send_and_measure(message: Message) -> None:
            nonlocal status, response_bytes
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                response_bytes += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_and_measure)
        finally:
            ctx = get_context()
            entry = {
                "method": scope.get("method"),
                "path": scope.get("path"),
                "route": route_template(scope),
                "query_keys": sorted({p.split("=")[0] for p in scope.get("query_string", b"").decode("latin-1").split("&") if p}),
                "status": status,
                "duration_ms": round((time.perf_counter() - ctx.started_at) * 1000, 2) if ctx else None,
                "request_bytes": int(length) if (length := header(scope, "content-length") or "0").isdigit() else None,
                "response_bytes": response_bytes,
                "client_ip": ctx.client_ip if ctx else None,
                "user_agent": ctx.user_agent if ctx else None,
                "host": ctx.host if ctx else None,
                "host_kind": ctx.host_kind if ctx else None,
                "origin": header(scope, "origin"),
                "referer": (header(scope, "referer") or "").split("?")[0] or None,  # queries may carry tickets
                "client_app": header(scope, "x-formalie-client"),
                "error_code": ctx.error_code if ctx else None,
                "rate_limited": ctx.rate_limited if ctx else False,
            }
            level = logging.ERROR if status >= 500 else logging.WARNING if status in (401, 403, 429) else logging.INFO
            log.log(level, "%s %s %s", entry["method"], entry["path"], status, extra={"request": entry})

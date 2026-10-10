"""Helpers for the pure ASGI middleware: header access and writing an FRM error from outside FastAPI."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from app.core.context import current_trace_id, get_context
from app.core.errors.codes import ERROR_CODES
from app.core.errors.exceptions import error_body

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def header(scope: Scope, name: str) -> str | None:
    """First value of a request header (case-insensitive), decoded as latin-1."""
    target = name.lower().encode("latin-1")
    for key, value in scope.get("headers") or []:
        if key == target:
            return value.decode("latin-1")
    return None


def route_path(scope: Scope) -> str:
    """Path without the root path (mounts), as routes see it."""
    path: str = scope.get("path", "")
    root: str = scope.get("root_path", "")
    return path[len(root):] if root and path.startswith(root) else path


async def send_error(
    send: Send,
    code: str,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    ctx = get_context()
    if ctx is not None:
        ctx.error_code = code
    body = json.dumps(error_body(code, current_trace_id(), details)).encode("utf-8")
    raw_headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    raw_headers += [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    await send({"type": "http.response.start", "status": ERROR_CODES[code].status, "headers": raw_headers})
    await send({"type": "http.response.body", "body": body})

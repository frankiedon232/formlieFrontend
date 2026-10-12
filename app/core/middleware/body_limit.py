"""Body size ceiling (B17 review M12): a request body larger than REQUEST_BODY_MAX_BYTES is refused with 413
FRM-FILE-1002 before anything holds it.

- A declared Content-Length over the ceiling is refused at once, nothing is read.
- A body without a length (chunked) is counted as the app reads it; past the ceiling the app is told the client
  went away (`http.disconnect`), whatever it answers is dropped and the 413 is sent instead.
- Uploads (`/storage/{token}`, raw bytes with a single-use token) stream to their own route, which checks its own,
  larger limit (uploads.router.store_upload); the API service's gateway checks its own limits too (1 MB JSON, 26 MB
  files).
"""

from __future__ import annotations

import logging
import re

from app.core.config import Settings
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send, header, send_error

log = logging.getLogger("formalie.request")

TOO_LARGE = "FRM-FILE-1002"


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.max_bytes = settings.request_body_max_bytes
        self.uploads = re.compile(rf"^{re.escape(settings.api_prefix)}/storage/[^/]+$")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.uploads.match(scope.get("path", "")):
            await self.app(scope, receive, send)
            return
        declared = header(scope, "content-length")
        if declared and declared.strip().isdigit() and int(declared) > self.max_bytes:
            log.warning("FRM-FILE-1002 request body over the ceiling", extra={"error_code": TOO_LARGE,
                                                                             "declared_bytes": int(declared)})
            await send_error(send, TOO_LARGE)
            return

        size = 0
        over = False
        started = False

        async def counted_receive() -> Message:
            nonlocal size, over
            if over:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    over = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if over and not started:  # the app's answer to a cut-off body is replaced by the 413
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counted_receive, guarded_send)
        except Exception:
            if not over:
                raise
        if over and not started:
            log.warning("FRM-FILE-1002 request body over the ceiling", extra={"error_code": TOO_LARGE,
                                                                             "read_bytes": size})
            await send_error(send, TOO_LARGE)

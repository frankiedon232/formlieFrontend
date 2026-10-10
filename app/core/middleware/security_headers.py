"""2. SecurityHeaders: HSTS, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, frame rules.

The API serves JSON only, so its CSP is the strictest one. The interactive docs (/docs, /redoc, development
only) load Swagger UI / ReDoc from jsDelivr and get a CSP that allows exactly that.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.middleware.asgi import ASGIApp, Message, Receive, Scope, Send

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "worker-src blob:; frame-ancestors 'none'"
)
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        common = [
            (b"strict-transport-security", b"max-age=63072000; includeSubDomains; preload"),
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"no-referrer"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"),
            (b"x-frame-options", b"DENY"),
            (b"cross-origin-opener-policy", b"same-origin"),
            (b"cross-origin-resource-policy", b"same-origin"),
        ]
        self.api_headers = [*common, (b"content-security-policy", API_CSP.encode()), (b"cache-control", b"no-store")]
        self.docs_headers = [*common, (b"content-security-policy", DOCS_CSP.encode())]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        extra = self.docs_headers if scope.get("path", "").startswith(DOCS_PATHS) else self.api_headers

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = [*message.get("headers", []), *[(k, v) for k, v in extra if k not in existing]]
            await send(message)

        await self.app(scope, receive, send_with_headers)

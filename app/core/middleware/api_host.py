"""0. ApiHost: requests for `api.<ROOT_DOMAIN>` go to the public API service's own app (app/gateway.py), before any
portal layer (envelope, workspace host, CSRF). In production the API service runs as its own process behind its own
host; this keeps one development server answering both, so the frontend's dev proxy and Postman work unchanged.

The host is the request's Host, or X-Forwarded-Host from a trusted proxy (the same rule as request_context.py).
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.middleware.asgi import ASGIApp, Receive, Scope, Send
from app.core.middleware.request_context import TrustedProxies
from app.core.middleware.tenant import normalise_host


class ApiHostMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings, gateway: ASGIApp | None = None,
                 request_log_shipper: Any | None = None) -> None:
        self.app = app
        self.settings = settings
        self.proxies = TrustedProxies(settings.trusted_proxies)
        self.api_host = f"api.{settings.root_domain}".lower()
        self.gateway = gateway
        self.shipper = request_log_shipper

    def _gateway(self) -> ASGIApp:
        if self.gateway is None:
            from app.gateway import create_gateway_app

            self.gateway = create_gateway_app(self.settings, request_log_shipper=self.shipper, configure=False)
        return self.gateway

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            peer = scope["client"][0] if scope.get("client") else None
            host = self.proxies.host(peer, scope)
            if host and normalise_host(host) == self.api_host:
                await self._gateway()(scope, receive, send)
                return
        await self.app(scope, receive, send)

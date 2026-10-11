"""A test client that speaks the protocol like the frontend's app/utils/api/client.ts:
handshake → CSRF token before state-changing calls → sealed request (header for GET/DELETE, body otherwise)
→ open the sealed reply (checking its kid and freshness, as the client does)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.security import envelope as env

BASE = "/api/v1"
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


class SecureClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http
        self.kid: str | None = None
        self.key: bytes | None = None
        self.csrf: str | None = None
        self.access_token: str | None = None

    async def handshake(self) -> dict[str, Any]:
        private = env.generate_key_pair()
        response = await self.http.post(f"{BASE}/crypto/handshake",
                                         json={"client_public_key": env.raw_public_key(private), "client_ts": 1})
        data = response.json()["data"]
        self.kid = data["key_id"]
        self.key = env.derive_session_key(private, data["server_public_key"], data["salt"])
        return data

    def seal(self, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None,
             **overrides: Any) -> dict[str, Any]:
        payload = {"method": method, "path": f"{BASE}{path}", "query": query or {}, "body": body}
        payload.update(overrides.pop("payload", {}))
        assert self.key is not None and self.kid is not None
        return env.seal(self.key, overrides.pop("kid", self.kid), payload, **overrides)

    async def send(self, method: str, path: str, envelope: dict[str, Any] | None, *,
                   csrf: str | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
        h = dict(headers or {})
        if csrf:
            h["x-csrf-token"] = csrf
        if self.access_token:
            h["authorization"] = f"Bearer {self.access_token}"
        if method in ("GET", "DELETE"):
            if envelope is not None:
                h[env.ENVELOPE_HEADER] = env.encode_header(envelope)
            return await self.http.request(method, f"{BASE}{path}", headers=h)
        h["content-type"] = env.ENVELOPE_CONTENT_TYPE
        return await self.http.request(method, f"{BASE}{path}", headers=h, content=json.dumps(envelope or {}))

    def open(self, response: httpx.Response) -> dict[str, Any]:
        """The reply as the client sees it: sealed replies are opened, plain errors returned as they are."""
        body = response.json()
        if env.is_envelope(body):
            assert body["kid"] == self.kid and env.is_fresh(body["ts"]), "reply not for this channel or not fresh"
            assert self.key is not None
            return env.open_envelope(self.key, body)
        return body

    async def request(self, method: str, path: str, *, query: dict[str, Any] | None = None,
                      body: Any = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        if self.key is None:
            await self.handshake()
        csrf = None
        if method in STATE_CHANGING:
            if self.csrf is None:
                status, reply = await self.request("GET", "/auth/csrf")
                assert status == 200, reply
                self.csrf = reply["data"]["csrf_token"]
            csrf = self.csrf
        response = await self.send(method, path, self.seal(method, path, query, body), csrf=csrf, headers=headers)
        return response.status_code, self.open(response)

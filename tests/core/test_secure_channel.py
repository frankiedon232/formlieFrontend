"""The secure channel end to end: handshake, every envelope check in the mock's order, CSRF, references."""

from __future__ import annotations

import time
import uuid
from typing import Any

import pytest
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.refs_types import RefId
from app.core.responses import ok
from app.core.security import envelope as env
from app.core.security.refs import get_codec
from tests.conftest import build_app, client_for
from tests.secure_client import SecureClient

ID = "0190f0b2-1111-7222-8333-444455556666"


class EchoBody(BaseModel):
    form_id: RefId
    note: str = ""


def _app(settings):  # noqa: ANN001, ANN202
    app = build_app(settings)
    router = APIRouter()

    @router.get("/check/echo")
    async def echo_get(page: int = 1, q: str = "") -> Any:
        return ok({"page": page, "q": q, "id": ID})

    @router.post("/check/echo")
    async def echo_post(body: EchoBody) -> Any:
        return ok({"form_id": str(body.form_id), "note": body.note})

    @router.get("/check/cookie")
    async def cookie() -> Any:
        from fastapi.responses import JSONResponse

        response = JSONResponse({"success": True, "data": {"ok": True}, "meta": {}})
        response.set_cookie("formalie_rt", "abc", httponly=True, secure=True, samesite="strict", path="/api/v1/auth")
        return response

    @router.get("/check/forms/{form_id}")
    async def one_form(form_id: RefId) -> Any:
        return ok({"id": str(form_id)})

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
async def secure(settings, redis):  # noqa: ANN001
    async with client_for(_app(settings)) as http:
        yield SecureClient(http)


async def test_handshake_and_a_sealed_round_trip(secure: SecureClient) -> None:
    data = await secure.handshake()
    assert uuid.UUID(data["key_id"]) and data["expires_at"].endswith("Z") and len(env.b64decode(data["salt"])) == 32
    status, reply = await secure.request("GET", "/check/echo", query={"page": 3, "q": "café"})
    assert status == 200 and reply["data"]["page"] == 3 and reply["data"]["q"] == "café"
    assert reply["data"]["id"] == get_codec().encode_id(ID)  # ids leave as references


async def test_handshake_validation(secure: SecureClient) -> None:
    short = await secure.http.post("/api/v1/crypto/handshake", json={"client_public_key": "abc", "client_ts": 1})
    assert short.json()["error"]["code"] == "FRM-GEN-1002"
    bad_point = await secure.http.post("/api/v1/crypto/handshake",
                                       json={"client_public_key": env.b64encode(b"\x04" + bytes(64)), "client_ts": 1})
    assert bad_point.json()["error"]["code"] == "FRM-GEN-1001"
    assert bad_point.json()["error"]["details"][0]["field"] == "client_public_key"


async def test_handshake_works_on_an_unknown_workspace_host(settings, redis) -> None:  # noqa: ANN001
    async with client_for(_app(settings), host="nobody.formalie.dev") as http:
        client = SecureClient(http)
        await client.handshake()
        status, reply = await client.request("GET", "/check/echo")
        assert (status, reply["error"]["code"]) == (404, "FRM-TEN-1001")


async def test_post_needs_csrf_and_takes_references(secure: SecureClient) -> None:
    await secure.handshake()
    ref = get_codec().encode_id(ID)
    envelope = secure.seal("POST", "/check/echo", body={"form_id": ref})
    no_csrf = secure.open(await secure.send("POST", "/check/echo", envelope))
    assert no_csrf["error"]["code"] == "FRM-SEC-1006"
    status, reply = await secure.request("POST", "/check/echo", body={"form_id": ref, "note": "hi"})
    assert status == 200 and reply["data"] == {"form_id": get_codec().encode_id(ID), "note": "hi"}


async def test_raw_ids_are_refused_in_body_and_address(secure: SecureClient) -> None:
    status, reply = await secure.request("POST", "/check/echo", body={"form_id": ID})
    assert (status, reply["error"]["code"]) == (422, "FRM-GEN-1002")
    assert reply["error"]["details"][0]["field"] == "form_id"
    status, reply = await secure.request("GET", f"/check/forms/{ID}")
    assert (status, reply["error"]["code"]) == (404, "FRM-GEN-1004")
    status, reply = await secure.request("GET", f"/check/forms/{get_codec().encode_id(ID)}")
    assert status == 200 and reply["data"]["id"] == get_codec().encode_id(ID)


async def test_csrf_token_of_another_channel_is_refused(secure: SecureClient) -> None:
    status, reply = await secure.request("GET", "/auth/csrf")
    assert status == 200 and reply["data"]["expires_at"].endswith("Z")
    foreign_token = reply["data"]["csrf_token"]
    await secure.handshake()  # a new channel
    envelope = secure.seal("POST", "/check/echo", body={"form_id": get_codec().encode_id(ID)})
    reply = secure.open(await secure.send("POST", "/check/echo", envelope, csrf=foreign_token))
    assert reply["error"]["code"] == "FRM-SEC-1006"


async def test_each_check_in_order(secure: SecureClient) -> None:
    await secure.handshake()
    # 1. no envelope → plain 1001
    r = await secure.http.get("/api/v1/check/echo")
    assert (r.status_code, r.json()["error"]["code"]) == (400, "FRM-SEC-1001")
    # 2. unknown key → plain 1004
    r = await secure.send("GET", "/check/echo", secure.seal("GET", "/check/echo", kid="0190ffff-0000-4000-8000-000000000000"))
    assert (r.status_code, r.json()["error"]["code"]) == (401, "FRM-SEC-1004") and "kid" not in r.json()
    # 3. too old → sealed 1002
    r = await secure.send("GET", "/check/echo", secure.seal("GET", "/check/echo", ts=int(time.time() * 1000) - 61_000))
    assert env.is_envelope(r.json()) and secure.open(r)["error"]["code"] == "FRM-SEC-1002"
    # 4. replay → sealed 1003
    envelope = secure.seal("GET", "/check/echo")
    assert (await secure.send("GET", "/check/echo", envelope)).status_code == 200
    r = await secure.send("GET", "/check/echo", envelope)
    assert secure.open(r)["error"]["code"] == "FRM-SEC-1003"
    # 5. sealed for another address or method, or tampered → sealed 1005
    r = await secure.send("GET", "/check/echo", secure.seal("GET", "/check/other"))
    assert secure.open(r)["error"]["code"] == "FRM-SEC-1005"
    r = await secure.send("GET", "/check/echo", secure.seal("DELETE", "/check/echo"))
    assert secure.open(r)["error"]["code"] == "FRM-SEC-1005"
    tampered = secure.seal("GET", "/check/echo")
    tampered["ct"] = env.b64encode(bytes(len(env.b64decode(tampered["ct"]))))
    assert secure.open(await secure.send("GET", "/check/echo", tampered))["error"]["code"] == "FRM-SEC-1005"


async def test_a_key_only_works_on_the_host_it_was_made_for(settings, redis) -> None:  # noqa: ANN001
    app = _app(settings)
    async with client_for(app, host="acme.formalie.dev") as acme:
        client = SecureClient(acme)
        await client.handshake()
        assert (await client.request("GET", "/check/echo"))[0] == 200
    async with client_for(app, host="manage.formalie.dev") as manage:
        client.http = manage  # same key, other host
        r = await client.send("GET", "/check/echo", client.seal("GET", "/check/echo"))
        assert r.json()["error"]["code"] == "FRM-SEC-1004"


async def test_request_log_records_the_decrypted_request(settings, redis) -> None:  # noqa: ANN001
    from tests.conftest import MemoryShipper

    shipper = MemoryShipper()
    app = build_app(settings, shipper)
    router = APIRouter()

    @router.post("/check/login")
    async def login(body: dict) -> Any:
        return ok({"seen": sorted(body)})

    app.include_router(router, prefix="/api/v1")
    async with client_for(app) as http:
        client = SecureClient(http)
        await client.request("POST", "/check/login", body={"email": "ada@example.com", "password": "Secret-1"})
    record = shipper.records[-1]
    assert record["request_body"] == {"body": {"email": "ada@example.com", "password": "***"}, "envelope": True}
    assert record["request_body_keys"] == ["email", "password"] and record["status"] == 200
    assert "Secret-1" not in str(record)


async def test_sealed_replies_keep_the_routes_own_headers(secure: SecureClient) -> None:
    await secure.handshake()
    response = await secure.send("GET", "/check/cookie", secure.seal("GET", "/check/cookie"))
    assert secure.open(response)["data"] == {"ok": True}
    cookie = response.headers["set-cookie"]
    assert "formalie_rt=abc" in cookie and "HttpOnly" in cookie and "Path=/api/v1/auth" in cookie
    assert response.headers["content-type"] == "application/vnd.formalie.enc+json"

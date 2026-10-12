"""Webhooks (B10 step 2) end to end: creating one (address checks, forms, a webhook token made for it), the test ping,
deliveries from response events with answers named like the API, retries after 1, 5, 15, 60 and 360 minutes, the
pause after repeated failures (notification and audit), Send again, no usable token, refused private addresses, the
lists, insights and filters, deleting, another workspace seeing none of it; and the Celery tasks against a real HTTP
receiver on this machine."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest

from app.modules.public import router as public_router
from app.modules.webhooks import tasks
from tests.conftest import client_for
from tests.db.test_api_service import errors, job_form
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_destinations import real, submit
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


class Receiver:
    """A webhook receiver: answers with the next status of `answers` (the last one again when they run out)."""

    def __init__(self, *answers: int) -> None:
        self.answers = list(answers) or [200]
        self.requests: list[httpx.Request] = []
        self.addresses = ["203.0.113.50"]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return httpx.Response(status, json={"received": status < 300}, headers={"Server": "test", "X-Other": "no"})

    async def resolve(self, host: str, port: int) -> list[str]:
        if host.endswith(".invalid"):
            raise OSError("name not found")
        return self.addresses


@pytest.fixture
def receiver(monkeypatch: pytest.MonkeyPatch) -> Receiver:
    got = Receiver()
    monkeypatch.setattr(tasks, "transport", httpx.MockTransport(got.handle))
    monkeypatch.setattr(tasks, "resolver", got.resolve)
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    return got


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """No Celery here: deliveries wait until the test sends them."""
    jobs: list[tuple] = []
    monkeypatch.setattr(tasks, "dispatch_delivery", lambda t, o, d, w: jobs.append((t, o, d, w)))
    return jobs


async def send_all(jobs: list[tuple]) -> None:
    while jobs:
        t, o, d, w = jobs.pop(0)
        await tasks.attempt(t, o, d, w)


async def test_webhooks_from_start_to_finish(app, superuser, receiver, queued) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant_id = superuser.execute("SELECT id FROM platform.tenants WHERE subdomain = %s", (sub,)).fetchone()[0]
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Job application", job_form)
        other_form = await publish(owner, "Other", job_form)

        # The address and the forms are checked; a webhook token is made for it and shown once
        body = {"name": "CRM sync", "url": "https://hooks.example.com/crm", "events": ["response.created"],
                "form_ids": [form["id"]], "token_id": "new"}
        for url, problem in [("", "required"), ("http://hooks.example.com/x", "https"), ("https://api.formalie.com/x", "host"),
                             ("https://10.0.0.1/x", "private"), ("https://user:pw@hooks.example.com", "url"),
                             ("http://localhost:3000/x", "https")]:
            _, reply = await owner.request("POST", "/webhooks", body={**body, "url": url})
            assert errors(reply) == ("FRM-GEN-1002", {"url": problem}), url
        _, reply = await owner.request("POST", "/webhooks", body={**body, "form_ids": [str(real(form["id"]))]})
        assert errors(reply) == ("FRM-GEN-1002", {"form_ids": "form"})
        _, reply = await owner.request("POST", "/webhooks", body={**body, "events": []})
        assert reply["error"]["code"] == "FRM-GEN-1002"
        _, reply = await owner.request("POST", "/webhooks", body={**body, "token_id": form["id"]})
        assert errors(reply) == ("FRM-GEN-1002", {"token_id": "webhook_token"})
        status, reply = await owner.request("POST", "/webhooks", body=body)
        assert status == 201, reply
        hook, token = reply["data"]["webhook"], reply["data"]["token"]
        assert token["name"] == "CRM sync · webhook" and token["secret"].startswith("formalie_hook_live_")
        assert hook["token"] == {"id": token["id"], "name": "CRM sync · webhook",
                                 "preview": f"formalie_hook_live_…{token['secret'][-4:]}", "status": "active"}
        assert hook["forms"] == [{"id": form["id"], "name": "Job application"}] and hook["status"] == "active"
        assert hook["deliveries_30d"] == 0 and hook["success_rate"] is None and hook["last_delivery"] is None
        assert len(hook["daily"]) == 30 and hook["created_by"]["name"] == "Olu Ade" and hook["paused_reason"] is None
        assert set(hook) == {"id", "name", "url", "events", "forms", "enabled", "status", "paused_reason", "token",
                             "deliveries_30d", "failed_30d", "success_rate", "avg_ms", "last_delivery",
                             "consecutive_failures", "daily", "created_by", "created_at", "updated_at"}
        # A second webhook sends the same token
        _, reply = await owner.request("POST", "/webhooks", body={**body, "name": "Warehouse", "token_id": token["id"],
                                                                  "form_ids": [], "events": list(("response.created",
                                                                                                  "response.deleted"))})
        warehouse = reply["data"]["webhook"]
        assert reply["data"]["token"] is None and warehouse["token"]["id"] == token["id"]

        # The test ping waits for the receiver's answer
        status, reply = await owner.request("POST", f"/webhooks/{hook['id']}/test")
        assert status == 200, reply
        ping = reply["data"]
        assert ping["event"] == "ping" and ping["test"] is True and ping["status"] == "delivered" and ping["attempts"] == 1
        assert ping["status_code"] == 200 and ping["form"] == {"id": form["id"], "name": "Job application"}
        sent = receiver.requests[-1]
        assert sent.url.host == "203.0.113.50" and sent.headers["host"] == "hooks.example.com"
        assert sent.headers["authorization"] == f"Bearer {token['secret']}"
        assert sent.headers["user-agent"] == "Formalie-Webhooks/1.0" and sent.headers["formalie-key"] == f"dlv_{ping['id']}"
        payload = json.loads(sent.content)
        assert payload["id"] == f"evt_{ping['id']}" and payload["type"] == "ping" and payload["test"] is True
        assert payload["data"]["response"]["answers"] == {"full_name": "Alex Morgan", "email": "alex.morgan@example.com"}
        assert ping["request"]["headers"]["Authorization"] == f"Bearer formalie_hook_live_…{token['secret'][-4:]}"
        logged = json.loads(ping["request"]["body"])
        assert logged["data"]["response"]["answers"] == {"full_name": "A•••n", "email": "a•••m"}
        assert ping["response"] == {"headers": {"server": "test", "content-type": "application/json",
                                                "content-length": ping["response"]["headers"]["content-length"]},
                                    "body": '{"received":true}'}
        assert token["secret"] not in json.dumps(ping)

        # A response becomes a delivery (only to the webhooks listening to the event and the form)
        receiver.answers = [500]
        response_id = await submit(http, form["public_key"], {"first_name": "Ana", "email": "ana@example.org"})
        await submit(http, other_form["public_key"], {"first_name": "Bo", "email": "bo@example.org"})
        assert len(queued) == 3  # CRM sync once, the warehouse twice
        await send_all(queued)
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"filter[webhook]": hook["id"],
                                                                           "filter[event]": "response.created"})
        assert reply["meta"]["total"] == 1
        first = reply["data"][0]
        assert first["status"] == "retrying" and first["attempts"] == 1 and first["status_code"] == 500
        assert first["response_id"] == response_id and first["form"]["id"] == form["id"]
        wait = datetime.fromisoformat(first["next_retry_at"].replace("Z", "+00:00")) - datetime.now(UTC)
        assert timedelta(seconds=50) < wait <= timedelta(minutes=1)
        delivered = json.loads(receiver.requests[-3].content)
        assert delivered["type"] == "response.created" and delivered["data"]["form"] == {"id": form["id"],
                                                                                          "name": "Job application"}
        answers = delivered["data"]["response"]["answers"]
        assert answers["first_name"] == "Ana" and answers["email"] == "ana@example.org"
        assert delivered["data"]["response"]["id"] == response_id and delivered["data"]["response"]["channel"] == "link"
        _, reply = await owner.request("GET", f"/webhook-deliveries/{first['id']}")
        detail = reply["data"]
        assert json.loads(detail["request"]["body"])["data"]["response"]["answers"]["email"] == "a•••g"
        assert detail["history"][0]["error"] == "HTTP 500" and detail["response"]["body"] == '{"received":false}'
        _, reply = await owner.request("GET", f"/webhooks/{hook['id']}")
        assert reply["data"]["status"] == "failing" and reply["data"]["consecutive_failures"] == 1
        assert reply["data"]["last_delivery"]["ok"] is False and reply["data"]["last_delivery"]["status_code"] == 500

        # Retries after 1, 5, 15, 60 and 360 minutes, then failed for good (the sweep takes those due)
        waits = []
        for _ in range(5):
            superuser.execute("UPDATE formaly.webhook_deliveries SET next_retry_at = now() - interval '1 second' "
                              "WHERE id = %s", (real(first["id"]),))
            assert await tasks.sweep() >= 1
            row = superuser.execute("SELECT status, attempts, next_retry_at FROM formaly.webhook_deliveries WHERE id = %s",
                                    (real(first["id"]),)).fetchone()
            waits.append(round((row[2] - datetime.now(UTC)).total_seconds() / 60) if row[2] else None)
        assert waits == [5, 15, 60, 360, None] and row[:2] == ("failed", 6)
        assert await tasks.sweep() == 0  # nothing due any more

        # Send again: a new delivery with the same body; this time it arrives
        receiver.answers = [200]
        _, reply = await owner.request("POST", f"/webhook-deliveries/{first['id']}/resend")
        again = reply["data"]
        assert again["id"] != first["id"] and again["status"] == "delivered" and again["event"] == "response.created"
        assert json.loads(receiver.requests[-1].content)["data"]["response"]["answers"]["email"] == "ana@example.org"
        assert json.loads(again["request"]["body"])["id"] == f"evt_{again['id']}"
        _, reply = await owner.request("GET", f"/webhooks/{hook['id']}")
        assert reply["data"]["status"] == "active" and reply["data"]["consecutive_failures"] == 0

        # Send again while it is still being retried: the retry happens now
        receiver.answers = [503, 503, 200]  # both webhooks' first tries fail
        await submit(http, form["public_key"], {"first_name": "Cy", "email": "cy@example.org"})
        await send_all(queued)
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"filter[status]": "retrying",
                                                                           "filter[webhook]": hook["id"]})
        waiting = reply["data"][0]
        _, reply = await owner.request("POST", f"/webhook-deliveries/{waiting['id']}/resend")
        assert reply["data"]["id"] == waiting["id"] and reply["data"]["status"] == "delivered" and reply["data"]["attempts"] == 2

        # After 20 failures in a row the webhook pauses itself: notification and audit trail
        superuser.execute("UPDATE formaly.webhooks SET consecutive_failures = 19 WHERE id = %s", (real(hook["id"]),))
        receiver.answers = [500]
        await submit(http, form["public_key"], {"first_name": "Di", "email": "di@example.org"})
        await send_all(queued)
        _, reply = await owner.request("GET", f"/webhooks/{hook['id']}")
        assert reply["data"]["status"] == "paused" and reply["data"]["paused_reason"] == "failures"
        assert reply["data"]["enabled"] is False
        assert superuser.execute("SELECT count(*) FROM formaly.notifications WHERE tenant_id = %s AND event = 'webhook_failing'",
                                 (tenant_id,)).fetchone()[0] >= 1
        paused = superuser.execute("SELECT actor_type, metadata FROM formaly.audit_logs WHERE tenant_id = %s "
                                   "AND action = 'integrations.webhook_paused'", (tenant_id,)).fetchall()
        assert paused == [("system", {"reason": "20 failed deliveries in a row"})]
        await submit(http, form["public_key"], {"first_name": "Ed", "email": "ed@example.org"})
        assert len(queued) == 1  # only the warehouse listens now
        await send_all(queued)
        _, reply = await owner.request("PATCH", f"/webhooks/{hook['id']}", body={"enabled": True})
        assert reply["data"]["status"] == "active" and reply["data"]["paused_reason"] is None

        # No usable token: nothing is sent, the try fails with `token`
        sent_before = len(receiver.requests)
        _, reply = await owner.request("POST", f"/api-tokens/{token['id']}/revoke")
        assert reply["success"], reply
        _, reply = await owner.request("POST", f"/webhooks/{hook['id']}/test")
        assert reply["data"]["status"] == "failed" and reply["data"]["history"][0]["error"] == "token"
        assert reply["data"]["request"]["headers"]["Authorization"].startswith("Bearer formalie_hook_live_…")
        assert len(receiver.requests) == sent_before
        _, reply = await owner.request("GET", f"/webhooks/{hook['id']}")
        assert reply["data"]["token"]["status"] == "revoked"

        # A new token, then an address that turns out private, or doesn't exist, is never called
        _, reply = await owner.request("PATCH", f"/webhooks/{hook['id']}", body={**body, "token_id": "new"})
        assert reply["data"]["token"]["name"] == "CRM sync · webhook 2"
        receiver.addresses = ["10.1.2.3"]
        _, reply = await owner.request("POST", f"/webhooks/{hook['id']}/test")
        assert reply["data"]["history"][0]["error"] == "refused" and len(receiver.requests) == sent_before
        receiver.addresses = ["203.0.113.50"]
        _, reply = await owner.request("PATCH", f"/webhooks/{hook['id']}", body={**body, "url": "https://gone.invalid/x"})
        assert reply["data"]["url"] == "https://gone.invalid/x"
        _, reply = await owner.request("POST", f"/webhooks/{hook['id']}/test")
        assert reply["data"]["history"][0]["error"] == "dns"

        # Switching off and on, and the audit trail
        _, reply = await owner.request("PATCH", f"/webhooks/{warehouse['id']}", body={"enabled": False})
        assert reply["data"]["status"] == "paused" and reply["data"]["paused_reason"] == "manual"
        actions = [r[0] for r in superuser.execute(
            "SELECT action FROM formaly.audit_logs WHERE tenant_id = %s AND (action LIKE 'integrations.webhook%%' "
            "OR action = 'api.token_created') ORDER BY occurred_at", (tenant_id,)).fetchall()]
        assert actions == ["integrations.webhook_created", "api.token_created", "integrations.webhook_created",
                           "integrations.webhook_resent", "integrations.webhook_paused", "integrations.webhook_enabled",
                           "integrations.webhook_updated", "integrations.webhook_updated",
                           "integrations.webhook_disabled"]
        changes = superuser.execute("SELECT changes FROM formaly.audit_logs WHERE tenant_id = %s AND "
                                    "action = 'integrations.webhook_updated' ORDER BY occurred_at", (tenant_id,)).fetchall()
        assert changes[0][0] == [{"field": "token", "before": "CRM sync · webhook", "after": "CRM sync · webhook 2"}]
        assert changes[1][0][0]["field"] == "url"

        # Lists, filters and insights
        _, reply = await owner.request("GET", "/webhooks", query={"filter[status]": "paused"})
        assert [w["name"] for w in reply["data"]] == ["Warehouse"]
        _, reply = await owner.request("GET", "/webhooks", query={"filter[event]": "response.deleted"})
        assert [w["name"] for w in reply["data"]] == ["Warehouse"]
        _, reply = await owner.request("GET", "/webhooks", query={"sort": "name", "q": "SYNC"})
        assert [w["name"] for w in reply["data"]] == ["CRM sync"]
        _, reply = await owner.request("GET", "/webhooks", query={"sort": "-deliveries_30d"})
        assert [w["name"] for w in reply["data"]] == ["Warehouse", "CRM sync"]
        crm = reply["data"][1]
        # Ana's (failed for good), Send again (delivered), Cy's (delivered on its retry), Di's (paused it, still retrying)
        assert crm["deliveries_30d"] == 4 and crm["failed_30d"] == 1 and crm["success_rate"] == 2 / 3
        assert crm["avg_ms"] is not None and crm["daily"][-1]["count"] == 4
        _, reply = await owner.request("GET", "/webhooks/insights")
        insights = reply["data"]
        assert insights["total"] == 2 and insights["by_status"] == {"active": 1, "failing": 0, "paused": 1}
        assert insights["deliveries_30d"] == 9 and insights["previous_30d"] == 0
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"q": "warehouse", "sort": "attempts"})
        assert reply["meta"]["total"] == 5 and all(d["webhook"]["name"] == "Warehouse" for d in reply["data"])
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"filter[event]": "ping"})
        assert reply["meta"]["total"] == 4 and all(d["test"] for d in reply["data"])
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"from": "2020-01-01", "to": "2020-01-02"})
        assert reply["meta"]["total"] == 0

        # A response deleted: only ids
        receiver.answers = [200]
        _, reply = await owner.request("PATCH", f"/webhooks/{warehouse['id']}", body={"enabled": True})
        _, reply = await owner.request("DELETE", f"/responses/{response_id}")
        assert reply["success"], reply
        await send_all(queued)
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"filter[event]": "response.deleted"})
        _, reply = await owner.request("GET", f"/webhook-deliveries/{reply['data'][0]['id']}")
        gone = json.loads(reply["data"]["request"]["body"])
        assert gone["type"] == "response.deleted" and gone["data"]["response"] == {"id": response_id}
        assert reply["data"]["history"][0]["error"] == "token"  # the warehouse still sends the revoked token

        # Deleting a webhook: gone from every list, its deliveries too
        _, reply = await owner.request("DELETE", f"/webhooks/{hook['id']}")
        assert reply["data"] == {"deleted": True}
        _, reply = await owner.request("GET", f"/webhooks/{hook['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("GET", f"/webhook-deliveries/{first['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await owner.request("GET", "/webhook-deliveries", query={"filter[webhook]": hook["id"]})
        assert reply["meta"]["total"] == 0
        assert superuser.execute("SELECT deleted_at IS NOT NULL FROM formaly.webhooks WHERE id = %s",
                                 (real(hook["id"]),)).fetchone() == (True,)

    # Another workspace sees none of it
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other_sub}.formalie.dev") as http:
        other = SecureClient(http)
        await sign_in(other, other_email, PASSWORD)
        _, reply = await other.request("GET", "/webhooks")
        assert reply["data"] == []
        for path in (f"/webhooks/{warehouse['id']}", f"/webhook-deliveries/{again['id']}"):
            _, reply = await other.request("GET", path)
            assert reply["error"]["code"] == "FRM-GEN-1004", path
        _, reply = await other.request("POST", f"/webhook-deliveries/{again['id']}/resend")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await other.request("GET", "/webhook-deliveries")
        assert reply["meta"]["total"] == 0
        _, reply = await other.request("GET", "/webhooks/insights")
        assert reply["data"]["total"] == 0 and reply["data"]["deliveries_30d"] == 0


async def test_a_webhook_never_stops_a_response(app, superuser, receiver, queued, monkeypatch) -> None:  # noqa: ANN001, F811
    """A failure while queueing deliveries leaves the response saved."""
    from app.modules.webhooks import service as W

    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Job application", job_form)
        _, reply = await owner.request("POST", "/webhooks", body={
            "name": "Hook", "url": "https://hooks.example.com/x", "events": ["response.created"], "form_ids": []})
        assert reply["success"], reply

        async def broken(*_: object) -> None:
            raise RuntimeError("boom")
        monkeypatch.setattr(W, "answer_names", broken)
        response_id = await submit(http, form["public_key"], {"first_name": "Ana", "email": "ana@example.org"})
        assert queued == []
        assert superuser.execute("SELECT count(*) FROM formaly.responses WHERE id = %s",
                                 (real(response_id),)).fetchone() == (1,)


# ── The Celery tasks against a real HTTP receiver ───────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    answers: list[int] = []
    seen: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        _Handler.seen.append({"headers": dict(self.headers), "body": self.rfile.read(length).decode()})
        status = _Handler.answers.pop(0) if len(_Handler.answers) > 1 else _Handler.answers[0]
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok" if status < 300 else b"nope")

    def log_message(self, *_: object) -> None:
        pass


def test_celery_tasks_deliver_retry_and_pause(db_settings, owner, redis, monkeypatch, superuser) -> None:  # noqa: ANN001
    """deliver_task and sweep_task (as the worker runs them) against an HTTP server on this machine."""
    from app.core.db import engines as E
    from app.core.db.session import db_session
    from tests.db.conftest import make_workspace

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _Handler.answers, _Handler.seen = [500], []
    url = f"http://127.0.0.1:{server.server_address[1]}/hook"
    monkeypatch.setattr(tasks, "allow_local", lambda: True)
    engines = E.Engines(db_settings)
    E.set_engines(engines)

    async def keep() -> None:  # the worker disposes its engines after each task; here they stay the test database's
        await engines.dispose()
    monkeypatch.setattr(E, "dispose_engines", keep)
    try:
        ws = make_workspace(owner)

        async def setup() -> tuple[uuid.UUID, uuid.UUID]:
            from app.modules.webhooks import service as W
            from app.modules.webhooks.models import Webhook

            async with db_session("write", tenant_id=ws.tenant_id, organisation_id=ws.organisation_id) as db:
                token, secret = await W.make_token(db, ws.tenant_id, ws.organisation_id, "Local", None)
                hook = Webhook(tenant_id=ws.tenant_id, organisation_id=ws.organisation_id, name="Local", url=url,
                               events=["response.created"], form_ids=[], enabled=True, token_id=token.id,
                               consecutive_failures=19)
                db.add(hook)
                await db.flush()
                delivery = W.new_delivery(hook, event="response.created", test=False, form_id=None, response_id=None,
                                          body={"type": "response.created", "data": {"answers": {"email": "x@example.org"}}},
                                          personal={"email"})
                db.add(delivery)
                await db.flush()
                _Handler.secret = secret  # type: ignore[attr-defined]
                ids = hook.id, delivery.id
            await engines.dispose()  # each asyncio.run has its own loop, like each task in the worker
            return ids
        hook_id, delivery_id = asyncio.run(setup())
        workspace = {"name": "Test", "subdomain": ws.subdomain}
        tasks.deliver_task.apply(args=[str(ws.tenant_id), str(ws.organisation_id), str(delivery_id), workspace])
        row = superuser.execute("SELECT status, attempts, next_retry_at FROM formaly.webhook_deliveries WHERE id = %s",
                                (delivery_id,)).fetchone()
        assert row[0] == "retrying" and row[1] == 1
        assert _Handler.seen[0]["headers"]["Authorization"] == f"Bearer {_Handler.secret}"  # type: ignore[attr-defined]
        assert json.loads(_Handler.seen[0]["body"])["data"]["answers"] == {"email": "x@example.org"}
        # 20 failures in a row: paused
        assert superuser.execute("SELECT enabled, paused_reason, consecutive_failures FROM formaly.webhooks WHERE id = %s",
                                 (hook_id,)).fetchone() == (False, "failures", 20)
        # The same task again does nothing until the retry is due; the sweep sends it when it is
        tasks.deliver_task.apply(args=[str(ws.tenant_id), str(ws.organisation_id), str(delivery_id), workspace])
        assert len(_Handler.seen) == 1
        _Handler.answers = [200]
        superuser.execute("UPDATE formaly.webhook_deliveries SET next_retry_at = now() - interval '1 second' WHERE id = %s",
                          (delivery_id,))
        tasks.sweep_task.apply()
        row = superuser.execute("SELECT status, attempts, status_code, response FROM formaly.webhook_deliveries "
                                "WHERE id = %s", (delivery_id,)).fetchone()
        assert row[:3] == ("delivered", 2, 200) and row[3]["body"] == "ok"
        assert superuser.execute("SELECT consecutive_failures FROM formaly.webhooks WHERE id = %s",
                                 (hook_id,)).fetchone() == (0,)
    finally:
        server.shutdown()
        asyncio.run(engines.dispose())
        E.set_engines(None)


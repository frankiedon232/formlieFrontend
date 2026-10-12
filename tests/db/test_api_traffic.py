"""API traffic (B10 step 2) end to end: the gateway's write path (traffic.record_call) into the request log, the log
with its filters, search, sort and pages, one call with masked headers and kept bodies, the log settings, insights and
analytics, the real counts on services, endpoints, tokens and access rules, bodies cleared after their days, the audit
trail, and another workspace seeing none of it."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.db.session import db_session
from app.modules.api_service import traffic as TR
from tests.conftest import client_for
from tests.db.test_api_service import errors, job_form
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_destinations import real
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def setup(owner: SecureClient) -> dict:
    """A service, a live endpoint on a published form, a live token and a block rule."""
    _, reply = await owner.request("POST", "/api-services", body={"name": "Website"})
    service = reply["data"]
    form = await publish(owner, "Job application", job_form)
    _, reply = await owner.request("GET", "/api-endpoints/form-fields", query={"form_id": form["id"]})
    choices = [{"key": f["key"], "accept": f["accept"], "required": f["required"], "returned": True, "filter": False}
               for f in reply["data"]["fields"]]
    _, reply = await owner.request("POST", "/api-endpoints", body={
        "name": "apply", "service_id": service["id"], "form_id": form["id"], "version": None, "methods": ["POST", "GET"],
        "fields": choices, "page_size": 50, "status": "active"})
    endpoint = reply["data"]
    _, reply = await owner.request("POST", "/api-tokens", body={
        "name": "Website sign-ups", "kind": "static", "mode": "live",
        "scopes": {"services": [], "endpoints": [], "methods": []}, "expires_at": None})
    token, secret = reply["data"]["token"], reply["data"]["secrets"]["token"]
    _, reply = await owner.request("POST", "/api-access-rules", body={
        "action": "block", "kind": "ip", "values": ["192.0.2.66"], "scope": {"type": "all", "id": None}})
    rule = reply["data"]
    return {"service": service, "endpoint": endpoint, "token": token, "secret": secret, "rule": rule}


async def write(tenant: tuple[uuid.UUID, uuid.UUID], **values: object) -> uuid.UUID:
    async with db_session("write", tenant_id=tenant[0], organisation_id=tenant[1]) as db:
        return await TR.record_call(db, tenant[0], tenant[1], TR.ApiCall(**values))  # type: ignore[arg-type]


async def test_request_log_from_start_to_finish(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    tenant = superuser.execute("SELECT t.id, t.primary_organisation_id FROM platform.tenants t WHERE subdomain = %s",
                               (sub,)).fetchone()
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
        endpoint_id, token_id, rule_id = real(made["endpoint"]["id"]), real(made["token"]["id"]), real(made["rule"]["id"])
        _, reply = await owner.request("GET", "/api-service/settings")
        key = reply["data"]["api_key"]

        # Nothing yet: real zeros, the same shapes
        _, reply = await owner.request("GET", "/api-logs")
        assert reply["data"] == [] and reply["meta"]["total"] == 0
        _, reply = await owner.request("GET", "/api-logs/settings")
        assert reply["data"] == {"keep_bodies": False, "days": 7}

        # The gateway writes calls (bodies are not kept yet)
        path = f"/{key}/apply"
        now = datetime.now(UTC)
        headers = {"Authorization": f"Bearer {made['secret']}", "Cookie": "a=b", "Host": "api.formalie.dev",
                   "X-Formalie-Signature": "sha256=abc", "sec-fetch-mode": "cors", "User-Agent": "curl/8.7.1"}
        ok_id = await write(tenant, method="POST", path=f"{path}?debug=1", status=201, duration_ms=40, ip="203.0.113.9",
                            request_id="req-ok-1", endpoint_id=endpoint_id, token_id=token_id, country="gb",
                            user_agent="curl/8.7.1", headers=headers, request_raw='{"email": "ana@example.org"}',
                            response_body={"id": "rsp_1"}, personal={"email"}, at=now - timedelta(minutes=5))
        await write(tenant, method="POST", path=path, status=422, code="FRM-RESP-1001", duration_ms=80, ip="203.0.113.9",
                    request_id="req-bad-1", endpoint_id=endpoint_id, token_id=token_id, country="GB",
                    at=now - timedelta(minutes=4))
        await write(tenant, method="GET", path=path, status=200, duration_ms=120, ip="198.51.100.4", request_id="req-get-1",
                    endpoint_id=endpoint_id, token_id=token_id, country="BR", at=now - timedelta(minutes=3))
        await write(tenant, method="POST", path=path, status=403, code="FRM-API-1015", duration_ms=6, ip="192.0.2.66",
                    request_id="req-blocked", endpoint_id=endpoint_id, rule_id=rule_id, at=now - timedelta(minutes=2))
        await write(tenant, method="POST", path=path, status=429, code="FRM-GEN-1029", duration_ms=3, ip="203.0.113.9",
                    request_id="req-limited", endpoint_id=endpoint_id, token_id=token_id, rate_limited=True,
                    at=now - timedelta(minutes=1))
        await write(tenant, method="POST", path=f"/{key}/nowhere", status=500, code="FRM-GEN-5000", duration_ms=900,
                    ip="203.0.113.10", request_id="req-crash", at=now - timedelta(seconds=30))
        await write(tenant, method="POST", path=path, status=201, duration_ms=50, ip="203.0.113.9", request_id="req-old",
                    endpoint_id=endpoint_id, token_id=token_id, at=now - timedelta(days=40))

        # The log: the last 7 days by default, newest first, never the token itself
        _, reply = await owner.request("GET", "/api-logs")
        assert [r["request_id"] for r in reply["data"]] == ["req-crash", "req-limited", "req-blocked", "req-get-1",
                                                            "req-bad-1", "req-ok-1"]
        first = reply["data"][-1]
        assert first["path"] == path and first["status"] == 201 and first["country"] == "GB" and first["code"] is None
        assert first["endpoint"] == {"id": made["endpoint"]["id"], "name": "apply"}
        assert first["service"] == {"id": made["service"]["id"], "name": "Website"}
        assert first["token"] == {"id": made["token"]["id"], "name": "Website sign-ups", "mode": "live"}
        assert set(first) == {"id", "at", "method", "path", "status", "code", "duration_ms", "endpoint", "service", "token",
                              "ip", "country", "user_agent", "request_id"}
        assert reply["data"][0]["endpoint"] is None and reply["data"][2]["token"] is None
        _, reply = await owner.request("GET", "/api-logs", query={"from": (now - timedelta(days=60)).date().isoformat(),
                                                                  "to": now.date().isoformat()})
        assert reply["meta"]["total"] == 7
        for query, wanted in [({"filter[class]": "4xx"}, ["req-limited", "req-blocked", "req-bad-1"]),
                              ({"filter[class]": "5xx,2xx"}, ["req-crash", "req-get-1", "req-ok-1"]),
                              ({"filter[method]": "GET"}, ["req-get-1"]),
                              ({"filter[mode]": "live", "filter[class]": "2xx"}, ["req-get-1", "req-ok-1"]),
                              ({"filter[token]": made["token"]["id"], "filter[method]": "GET"}, ["req-get-1"]),
                              ({"filter[endpoint]": made["endpoint"]["id"], "q": "frm-gen"}, ["req-limited"]),
                              ({"q": "WEBSITE SIGN", "filter[class]": "4xx"}, ["req-limited", "req-bad-1"]),
                              ({"q": "192.0.2.66"}, ["req-blocked"]),
                              ({"sort": "-duration_ms", "page_size": "2"}, ["req-crash", "req-get-1"]),
                              ({"sort": "status", "page": "2", "page_size": "4"}, ["req-limited", "req-crash"])]:
            _, reply = await owner.request("GET", "/api-logs", query=query)
            assert [r["request_id"] for r in reply["data"]] == wanted, query
        assert reply["meta"] == {"page": 2, "page_size": 4, "total": 6, "total_pages": 2}

        # One call: headers as the log keeps them (the bearer as its preview, secrets as dots, no cookies)
        _, reply = await owner.request("GET", f"/api-logs/{first['id']}")
        detail = reply["data"]
        assert detail["request_headers"] == {"authorization": f"Bearer formalie_live_…{made['secret'][-4:]}",
                                             "x-formalie-signature": "••••", "user-agent": "curl/8.7.1"}
        assert detail["request_body"] is None and detail["response_body"] is None and detail["bodies_kept"] is False
        assert made["secret"] not in str(superuser.execute(
            "SELECT request_headers FROM formaly.api_request_logs WHERE id = %s", (ok_id,)).fetchone())
        _, reply = await owner.request("GET", f"/api-logs/{made['service']['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        # Keeping bodies: personal answers masked; the settings change is in the audit trail
        _, reply = await owner.request("PUT", "/api-logs/settings", body={"keep_bodies": True, "days": 3})
        assert errors(reply)[0] == "FRM-GEN-1002"
        _, reply = await owner.request("PUT", "/api-logs/settings", body={"keep_bodies": True, "days": 1})
        assert reply["data"] == {"keep_bodies": True, "days": 1}
        kept = await write(tenant, method="POST", path=path, status=201, duration_ms=30, ip="203.0.113.9",
                           request_id="req-kept", endpoint_id=endpoint_id, token_id=token_id,
                           request_raw='{"email": "ana@example.org", "first_name": "Ana"}',
                           response_body={"id": "rsp_2", "email": "ana@example.org"}, personal={"email"})
        broken = await write(tenant, method="POST", path=path, status=400, duration_ms=30, ip="203.0.113.9",
                             request_id="req-text", endpoint_id=endpoint_id, request_raw="not json " + "x" * 3000)
        _, reply = await owner.request("GET", "/api-logs", query={"q": "req-kept"})
        _, reply = await owner.request("GET", f"/api-logs/{reply['data'][0]['id']}")
        assert reply["data"]["request_body"] == {"email": "a•••g", "first_name": "Ana"}
        assert reply["data"]["response_body"] == {"id": "rsp_2", "email": "a•••g"} and reply["data"]["bodies_kept"] is True
        assert len(superuser.execute("SELECT request_body #>> '{}' FROM formaly.api_request_logs WHERE id = %s",
                                     (broken,)).fetchone()[0]) == 2000
        actions = superuser.execute("SELECT action, changes FROM formaly.audit_logs WHERE tenant_id = %s AND "
                                    "action = 'api.logging_changed'", (tenant[0],)).fetchall()
        assert [a[0] for a in actions] == ["api.logging_changed"]
        assert actions[0][1] == [{"field": "keep_bodies", "before": False, "after": True},
                                 {"field": "days", "before": 7, "after": 1}]

        # Bodies older than the workspace keeps them are cleared; the call stays
        superuser.execute("UPDATE formaly.api_request_logs SET at = at - interval '2 days' WHERE id = %s", (kept,))
        async with db_session("write", tenant_id=tenant[0], organisation_id=tenant[1]) as db:
            assert await TR.prune_bodies(db, tenant[0], 1) == 1
        assert superuser.execute("SELECT request_body, response_body FROM formaly.api_request_logs WHERE id = %s",
                                 (kept,)).fetchone() == (None, None)

        # Insights and analytics
        _, reply = await owner.request("GET", "/api-logs/insights")
        insights = reply["data"]
        assert insights["calls_30d"] == 8 and insights["previous_30d"] == 1 and insights["errors_30d"] == 5
        assert insights["by_class"] == {"2xx": 3, "4xx": 4, "5xx": 1} and len(insights["daily"]) == 30
        assert insights["daily"][-1]["date"] == now.date().isoformat() and insights["avg_ms"] == 35
        _, reply = await owner.request("GET", "/api-analytics", query={"period": "7d"})
        stats = reply["data"]
        assert stats["from"] == (now.date() - timedelta(days=6)).isoformat() and stats["to"] == now.date().isoformat()
        assert stats["totals"]["calls"] == 8 and stats["totals"]["errors"] == 5 and stats["totals"]["tokens_used"] == 1
        assert stats["previous"]["calls"] == 0 and stats["previous"]["p50_ms"] is None
        assert len(stats["daily"]) == 7 and sum(d["calls"] for d in stats["daily"]) == 8
        assert stats["endpoints"][0]["name"] == "apply" and stats["endpoints"][0]["calls"] == 7
        assert stats["endpoints"][0]["service"] == "Website" and len(stats["endpoints"][0]["trend"]) == 7
        assert stats["tokens"] == [{"id": made["token"]["id"], "name": "Website sign-ups", "mode": "live", "calls": 5,
                                    "errors": 2}]
        assert stats["countries"] == [{"code": "GB", "calls": 2}, {"code": "BR", "calls": 1}]
        assert stats["methods"] == {"GET": 1, "POST": 7, "PUT": 0, "DELETE": 0}
        _, reply = await owner.request("GET", "/api-analytics", query={"period": "anything"})
        assert len(reply["data"]["daily"]) == 30 and reply["data"]["previous"]["calls"] == 1

        # The lists count real calls now (step 1's zeros)
        _, reply = await owner.request("GET", f"/api-endpoints/{made['endpoint']['id']}")
        use = reply["data"]
        assert use["calls_30d"] == 7 and use["previous_30d"] == 1 and use["errors_30d"] == 4 and use["avg_ms"] == 30
        assert use["last_call_at"] is not None and use["daily"][-1]["count"] == 6  # one call moved two days back above
        _, reply = await owner.request("GET", "/api-services")
        assert reply["data"][0]["calls_30d"] == 7 and reply["data"][0]["errors_30d"] == 4
        _, reply = await owner.request("GET", "/api-services/insights")
        assert reply["data"]["calls_30d"] == 7 and reply["data"]["previous_30d"] == 1
        _, reply = await owner.request("GET", "/api-endpoints/insights")
        assert reply["data"]["calls_30d"] == 7 and reply["data"]["avg_ms"] == 30
        _, reply = await owner.request("GET", f"/api-tokens/{made['token']['id']}")
        assert reply["data"]["calls_30d"] == 5 and reply["data"]["last_used_at"] is not None
        assert reply["data"]["last_call_at"] == reply["data"]["last_used_at"]
        _, reply = await owner.request("GET", "/api-tokens/insights")
        assert reply["data"]["calls_30d"] == 5 and reply["data"]["unused_90d"] == 0
        _, reply = await owner.request("GET", f"/api-access-rules/{made['rule']['id']}")
        assert reply["data"]["hits_30d"] == 1 and reply["data"]["last_hit_at"] is not None
        _, reply = await owner.request("GET", "/api-access-rules/insights")
        assert reply["data"]["refused_30d"] == 1 and reply["data"]["limited_30d"] == 1
        assert sum(d["count"] for d in reply["data"]["daily"]) == 1

    # Another workspace sees none of it
    other_sub, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other_sub}.formalie.dev") as http:
        other = SecureClient(http)
        await sign_in(other, other_email, PASSWORD)
        _, reply = await other.request("GET", "/api-logs", query={"from": "2020-01-01"})
        assert reply["data"] == [] and reply["meta"]["total"] == 0
        _, reply = await other.request("GET", f"/api-logs/{first['id']}")
        assert reply["error"]["code"] == "FRM-GEN-1004"
        _, reply = await other.request("GET", "/api-logs/insights")
        assert reply["data"]["calls_30d"] == 0 and reply["data"]["avg_ms"] is None
        _, reply = await other.request("GET", "/api-analytics")
        assert reply["data"]["totals"]["calls"] == 0 and reply["data"]["countries"] == []


async def test_the_log_is_tenant_isolated_in_the_database(engines, two_workspaces) -> None:  # noqa: ANN001
    """RLS: a row written in one workspace is invisible to the other and can't be written into it."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    a, b = two_workspaces
    await write((a.tenant_id, a.organisation_id), method="GET", path="/k/x", status=200, duration_ms=1, ip="203.0.113.1",
                request_id="iso-1")
    async with db_session("read", tenant_id=b.tenant_id, organisation_id=b.organisation_id) as db:
        assert (await db.execute(text("SELECT count(*) FROM api_request_logs WHERE request_id = 'iso-1'"))).scalar_one() == 0
    with pytest.raises(DBAPIError, match="row-level security"):
        async with db_session("write", tenant_id=a.tenant_id, organisation_id=a.organisation_id) as db:
            await db.execute(text("INSERT INTO api_request_logs (id, at, tenant_id, organisation_id, method, path, status, "
                                  "duration_ms, ip, request_id) VALUES (gen_random_uuid(), now(), :t, :o, 'GET', '/', 200, "
                                  "1, '1.1.1.1', 'x')"), {"t": b.tenant_id, "o": b.organisation_id})


def test_masking_and_headers() -> None:
    assert TR.mask_answers({"a": [{"email": "ab"}, {"email": 5}], "email": {"x": "hello"}, "n": None}, {"email"}) == {
        "a": [{"email": "••"}, {"email": "•••"}], "email": {"x": "h•••o"}, "n": None}
    assert TR.masked_headers({"Authorization": "bearer formalie_test_abcdefgh", "X-Secret": "s", "Connection": "x",
                              "Accept": "y" * 300}, {"X-Secret"}) == {
        "authorization": "Bearer formalie_test_…efgh", "x-secret": "••••", "accept": "y" * 200}
    assert TR.js_round(2.5) == 3 and TR.js_round(-2.5) == -2



async def test_sample_traffic_and_seeded_webhooks(app, superuser) -> None:  # noqa: ANN001, F811
    """The development seed's sample traffic (60 days on the live endpoints, refused calls) and the seeded
    workspaces' sample webhooks, like the mock."""
    from app.modules.api_service.traffic_samples import seed_sample_traffic
    from scripts.seed_dev import MOCK_PASSWORD

    sub, email = await new_workspace(app)
    tenant = superuser.execute("SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s",
                               (sub,)).fetchone()
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)
        superuser.execute("UPDATE formaly.api_endpoints SET created_at = now() - interval '90 days' WHERE tenant_id = %s",
                          (tenant[0],))
        superuser.execute("UPDATE formaly.api_access_rules SET created_at = now() - interval '90 days' WHERE tenant_id = %s",
                          (tenant[0],))
        async with db_session("write", tenant_id=tenant[0], organisation_id=tenant[1]) as db:
            added = await seed_sample_traffic(db, tenant[0], tenant[1])
        async with db_session("write", tenant_id=tenant[0], organisation_id=tenant[1]) as db:
            assert await seed_sample_traffic(db, tenant[0], tenant[1]) == 0  # once
        assert added > 100
        _, reply = await owner.request("GET", "/api-logs/insights")
        assert reply["data"]["calls_30d"] > 0 and reply["data"]["previous_30d"] > 0
        _, reply = await owner.request("GET", "/api-access-rules/insights")
        assert reply["data"]["refused_30d"] > 0
        _, reply = await owner.request("GET", f"/api-endpoints/{made['endpoint']['id']}")
        assert reply["data"]["calls_30d"] > 0 and reply["data"]["avg_ms"] is not None
        _, reply = await owner.request("GET", "/api-logs", query={"filter[class]": "2xx"})
        assert all(r["path"].startswith("/") and r["token"]["name"] == "Website sign-ups" for r in reply["data"])

    async with client_for(app, host="remedylegal.formalie.dev") as http:
        admin = SecureClient(http)
        await sign_in(admin, "admin@remedylegal.test", MOCK_PASSWORD)
        _, reply = await admin.request("GET", "/webhooks", query={"sort": "name"})
        assert [(w["name"], w["status"]) for w in reply["data"]] == [
            ("CRM sync", "active"), ("Data warehouse", "failing"), ("Old ticketing bridge", "paused")]
        assert all(w["token"]["name"] == f"{w['name']} · webhook" for w in reply["data"])
        _, reply = await admin.request("GET", "/webhook-deliveries")
        assert reply["meta"]["total"] > 0
        _, reply = await admin.request("GET", f"/webhook-deliveries/{reply['data'][0]['id']}")
        assert reply["data"]["request"]["headers"]["Authorization"] == "Bearer formalie_hook_live_…"

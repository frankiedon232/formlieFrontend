"""Address and domain, privacy requests, retention and the data region (B11) on new workspaces: the subdomain change
(the old one answering for 90 days, taken ones refused), an own domain verified through an injected DNS resolver and
answering like the subdomain, a person's data found, exported and erased in place (rows kept, personal data gone),
retention preview and apply, the audit trail and another workspace."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.security.refs import get_codec
from app.modules.public import router as public_router
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import on_plan
from tests.db.test_email_settings import FakeDns, fake_dns  # noqa: F401  (fixture)
from tests.db.test_public_forms import publish, session, solved
from tests.db.test_responses import build
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


async def test_subdomain_change_keeps_the_old_one(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    taken, _ = await new_workspace(app)
    new = f"n{sub}"
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        status, reply = await owner.request("GET", "/settings/address")
        assert status == 200
        assert reply["data"] == {"subdomain": sub, "url": f"https://{sub}.formalie.dev", "previous": [], "domain": None}
        _, reply = await owner.request("POST", "/settings/address/subdomain", body={"subdomain": new, "confirm": "other"})
        assert reply["error"]["details"] == [{"field": "confirm", "message": "confirm"}]
        _, reply = await owner.request("POST", "/settings/address/subdomain", body={"subdomain": taken, "confirm": taken})
        assert (reply["error"]["code"], reply["error"]["details"]) == ("FRM-TEN-1004", [{"field": "subdomain", "message": "taken"}])
        _, reply = await owner.request("POST", "/settings/address/subdomain", body={"subdomain": "manage", "confirm": "manage"})
        assert reply["error"]["details"] == [{"field": "subdomain", "message": "invalid"}]

        status, reply = await owner.request("POST", "/settings/address/subdomain", body={"subdomain": f" {new.upper()} ",
                                                                                         "confirm": new})
        assert status == 200, reply
        view = reply["data"]
        assert view["subdomain"] == new and view["url"] == f"https://{new}.formalie.dev"
        assert [p["subdomain"] for p in view["previous"]] == [sub]
        until = datetime.fromisoformat(view["previous"][0]["until"].replace("Z", "+00:00"))
        assert timedelta(days=89) < until - datetime.now(UTC) <= timedelta(days=90)
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        assert trail["data"][0]["resource"]["name"] == "Address and domain"
        assert trail["data"][0]["changes"] == [{"field": "subdomain", "before": sub, "after": new}]

    # Both addresses lead to the workspace; nobody else can take the old one
    # (each process keeps a resolved host up to 30 seconds, so the old host may still name the old subdomain a moment)
    for host in (sub, new):
        async with client_for(app, host=f"{host}.formalie.dev") as http:
            status, reply = await SecureClient(http).request("GET", "/tenants/public")
            assert status == 200 and reply["data"]["name"] == "Settings Co", host
            assert reply["data"]["subdomain"] in (sub, new) if host == sub else reply["data"]["subdomain"] == new
    async with client_for(app, host="manage.formalie.dev") as http:
        _, reply = await SecureClient(http).request("GET", "/tenants/subdomain-availability", query={"subdomain": sub})
        assert reply["data"]["available"] is False
    # Its own old address may come back
    async with client_for(app, host=f"{new}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("POST", "/settings/address/subdomain", body={"subdomain": sub, "confirm": sub})
        assert reply["data"]["subdomain"] == sub and [p["subdomain"] for p in reply["data"]["previous"]] == [new]
    assert superuser.execute("SELECT subdomain FROM platform.tenants WHERE subdomain IN (%s, %s)", (sub, new)).fetchall() == [(sub,)]


async def test_own_domain(app, owner_dsn, fake_dns, superuser) -> None:  # noqa: ANN001, F811
    starter, starter_email = await new_workspace(app)
    async with client_for(app, host=f"{starter}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, starter_email, PASSWORD)
        status, reply = await owner.request("PUT", "/settings/address/domain", body={"domain": "forms.acme.test"})
        assert (status, reply["error"]["code"]) == (402, "FRM-PLAN-1002")

    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    domain = f"forms.{sub}.example"
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("PUT", "/settings/address/domain", body={"domain": "intra.formalie.dev"})
        assert reply["error"]["details"] == [{"field": "domain", "message": "domain"}]
        status, reply = await owner.request("PUT", "/settings/address/domain", body={"domain": f" HTTPS://{domain.upper()}./x "})
        assert status == 200, reply
        entry = reply["data"]["domain"]
        assert entry["domain"] == domain and entry["status"] == "pending" and "token" not in entry
        cname, txt = entry["records"]
        assert (cname["type"], cname["name"], cname["value"]) == ("CNAME", domain, "custom.formalie.dev")
        assert txt["name"] == f"_formalie.{domain}" and txt["value"].startswith("formalie-verify=")

        _, reply = await owner.request("POST", "/settings/address/domain/check")
        assert (reply["data"]["domain"]["status"], reply["data"]["domain"]["problem"]) == ("pending", "not_found")
        fake_dns.records[(domain, "CNAME")] = ["somewhere.else.example."]
        _, reply = await owner.request("POST", "/settings/address/domain/check")
        assert (reply["data"]["domain"]["status"], reply["data"]["domain"]["problem"]) == ("failed", "wrong_target")
        fake_dns.records[(domain, "CNAME")] = ["custom.formalie.dev."]
        fake_dns.records[(f"_formalie.{domain}", "TXT")] = [txt["value"]]
        _, reply = await owner.request("POST", "/settings/address/domain/check")
        assert reply["data"]["domain"]["status"] == "verified" and reply["data"]["domain"]["checked_at"]

    # The domain answers like the workspace's own address
    async with client_for(app, host=domain) as http:
        status, reply = await SecureClient(http).request("GET", "/tenants/public")
        assert status == 200 and reply["data"]["subdomain"] == sub
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("DELETE", "/settings/address/domain")
        assert reply["data"]["domain"] is None
    held = superuser.execute("SELECT released_at IS NOT NULL FROM platform.custom_domains_directory WHERE domain = %s",
                             (domain,)).fetchone()
    assert held == (True,)


async def _submit(http, key: str, data: dict) -> str:  # noqa: ANN001
    visitor = SecureClient(http)
    status, reply = await visitor.request("POST", f"/public/forms/{key}/submit", body={
        "data": data, "challenge": await solved(visitor, key)}, headers=session())
    assert status == 201, reply
    return reply["data"]["response_id"]


async def test_privacy_requests_retention_and_region(app, monkeypatch, superuser) -> None:  # noqa: ANN001
    monkeypatch.setattr(public_router, "MIN_FILL_MS", 0)
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Signups", build)
        key = form["public_key"]
        ana = await _submit(http, key, {"full_name": "Ana Silva", "email": "ana@example.org", "plan": "basic", "score": 5})
        await _submit(http, key, {"full_name": "Ana S", "email": "other@example.org", "notes": " ANA@example.org "})
        ben = await _submit(http, key, {"full_name": "Ben Okoro", "email": "ben@example.org", "plan": "pro"})
        await owner.request("POST", f"/responses/{ana}/notes", body={"text": "Called Ana"})

        status, reply = await owner.request("POST", "/privacy/requests/search", body={"email": "Ana@Example.org"})
        assert status == 200, reply
        found = reply["data"]
        assert found["email"] == "ana@example.org" and found["total"] == 2
        assert [(f["id"], f["name"], f["count"]) for f in found["forms"]] == [(form["id"], "Signups", 2)]
        _, reply = await owner.request("POST", "/privacy/requests/search", body={"email": "nope"})
        assert reply["error"]["details"] == [{"field": "email", "message": "Invalid email address"}]

        _, reply = await owner.request("POST", "/privacy/requests/export", body={"email": "ana@example.org"})
        export = reply["data"]
        assert export["email"] == "ana@example.org" and len(export["responses"]) == 2
        first = export["responses"][0]
        assert first["form"] == "Signups" and first["number"] == 1 and first["language"]
        assert first["answers"]["Full name"] == "Ana Silva" and first["answers"]["Plan"] == "Basic"

        _, reply = await owner.request("POST", "/privacy/requests/delete", body={"email": "ana@example.org", "confirm": "x"})
        assert reply["error"]["details"] == [{"field": "confirm", "message": "confirm"}]
        status, reply = await owner.request("POST", "/privacy/requests/delete", body={"email": "ana@example.org",
                                                                                      "confirm": " ANA@example.org"})
        assert status == 200 and reply["data"] == {"responses": 2, "forms": 1}
        _, reply = await owner.request("POST", "/privacy/requests/search", body={"email": "ana@example.org"})
        assert reply["data"]["total"] == 0
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.data_deleted"})
        assert trail["data"][0]["resource"]["name"] == "a•••@example.org"
        assert trail["data"][0]["metadata"] == {"responses": "2", "forms": "1"}
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.data_exported"})
        assert trail["data"][0]["metadata"] == {"responses": "2"}
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses")
        assert reply["meta"]["total"] == 1

        # Retention: what a limit would remove now, and applying it
        _, reply = await owner.request("GET", "/settings/privacy/retention-preview", query={"days": "7"})
        assert reply["error"]["details"] == [{"field": "days", "message": "retention"}]
        _, reply = await owner.request("GET", "/settings/privacy/retention-preview", query={"days": "180"})
        assert reply["data"] == {"days": 180, "responses": 0, "forms": 0, "oldest_kept": None}
        superuser.execute("SELECT platform.ensure_monthly_partitions_back('formaly.responses'::regclass, 8)")
        superuser.execute("UPDATE formaly.responses SET submitted_at = now() - interval '200 days' WHERE id = %s",
                          (get_codec().decode_id(ben),))
        _, reply = await owner.request("GET", "/settings/privacy/retention-preview", query={"days": "180"})
        preview = reply["data"]
        assert (preview["responses"], preview["forms"]) == (1, 1) and preview["oldest_kept"]
        _, current = await owner.request("GET", "/settings/privacy")
        status, reply = await owner.request("PATCH", "/settings/privacy", body={**current["data"], "retention_days": 180})
        assert status == 200, reply
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses")
        assert reply["meta"]["total"] == 0
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.retention_applied"})
        assert trail["data"][0]["metadata"] == {"responses": "1", "forms": "1"}

        # The region: read only
        _, reply = await owner.request("GET", "/settings/data-region")
        assert reply["data"] == {"region": "default", "regions": ["default", "eu", "uk", "us", "ca", "au", "in", "sg", "br"],
                                 "residency": False}

    # Erased in place: the rows stay, the personal data is gone
    rows = superuser.execute(
        "SELECT r.data, r.respondent_email, r.ip, r.fingerprint, r.deleted_at IS NOT NULL FROM formaly.responses r "
        "JOIN platform.tenants t ON t.id = r.tenant_id WHERE t.subdomain = %s ORDER BY r.number", (sub,)).fetchall()
    assert [(r[0], r[1], r[2], r[3], r[4]) for r in rows] == [({}, None, None, "", True)] * 3
    notes = superuser.execute("SELECT n.text, n.deleted_at IS NOT NULL FROM formaly.response_notes n JOIN platform.tenants t "
                              "ON t.id = n.tenant_id WHERE t.subdomain = %s", (sub,)).fetchall()
    assert notes == [("", True)]

    # Another workspace finds nothing of it
    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("POST", "/privacy/requests/search", body={"email": "ben@example.org"})
        assert reply["data"]["total"] == 0

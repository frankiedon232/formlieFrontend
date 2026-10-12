"""Settings → Emails (B11) on a new workspace: templates, preview, test, the sent log (codes and personal links never
kept), the sending address (own domain with DNS records checked through an injected resolver, the workspace's own
mail server against a fake SMTP server), the plan, the audit trail, delivery by the chosen route, and another
workspace."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core import dns
from app.core.config import get_settings
from app.modules.emails import service as email_service
from app.modules.emails.service import SENT
from tests.conftest import client_for
from tests.db.test_auth_flows import app, last_code, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_data_sources import on_plan
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient
from tests.smtp_fake import FakeSmtp

pytestmark = pytest.mark.db


class FakeDns:
    """name, type → values; a name in `broken` raises like a DNS time-out."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str], list[str]] = {}
        self.broken: set[str] = set()

    async def __call__(self, name: str, rdtype: str) -> list[str]:
        if name in self.broken:
            raise dns.DnsError("Timeout")
        return list(self.records.get((name, rdtype), []))


@pytest.fixture
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeDns]:
    fake = FakeDns()
    monkeypatch.setattr(dns, "resolver", fake)
    yield fake


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeSmtp]:
    server = FakeSmtp().start()
    monkeypatch.setattr(get_settings(), "email_smtp_allow_local", True)
    yield server
    server.stop()


async def test_templates_preview_test_and_the_sent_log(app, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        code = last_code(email)

        status, reply = await owner.request("GET", "/settings/emails/templates/signin_code", query={"language": "zz"})
        assert status == 200, reply
        view = reply["data"]
        assert view["key"] == "signin_code" and view["language"] == "en"  # not one of its languages: its own
        assert view["custom"] is None and view["variables"] == ["name", "code", "minutes", "workspace"]
        assert "{{code}}" in view["default"]["body"]
        _, reply = await owner.request("GET", "/settings/emails/templates/nope")
        assert reply["error"]["code"] == "FRM-GEN-1004"

        # The workspace's own text: preview with sample values, From its name
        status, reply = await owner.request("POST", "/settings/emails/preview", body={
            "key": "response_notification", "language": "en", "subject": " New on {{form}} #{{number}} ",
            "body": "Hello {{workspace}}\n\n{{answers}}"})
        assert status == 200, reply
        preview = reply["data"]
        assert preview["subject"] == "New on Customer feedback #128"
        assert "Ada Visitor" in preview["html"] and preview["from"] == "Settings Co <no-reply@formalie.dev>"
        assert preview["reply_to"] is None
        _, reply = await owner.request("POST", "/settings/emails/preview", body={"key": "nope", "language": "en",
                                                                                 "subject": "", "body": "x"})
        assert {d["field"] for d in reply["error"]["details"]} == {"subject", "key"}

        # A test lands in the admin's inbox and the sent log
        sent_before = len(SENT)
        status, reply = await owner.request("POST", "/settings/emails/test", body={
            "key": "invitation", "language": "en", "subject": "Join {{workspace}}", "body": "By {{inviter}}"})
        assert status == 200, reply
        item = reply["data"]
        assert item["to"] == email and item["template"] == "invitation" and item["reason"] == "test"
        assert item["subject"] == "Join Settings Co" and "html" not in item
        assert SENT[sent_before]["to"] == email

        status, reply = await owner.request("GET", "/settings/emails/sent")
        assert status == 200 and reply["meta"]["total"] >= 2
        rows = reply["data"]
        assert rows[0]["id"] == item["id"] and set(rows[0]) == {"id", "at", "to", "subject", "template", "language", "reason"}
        signin = next(r for r in rows if r["template"] == "signin_code")
        assert signin["reason"] == "login"
        _, reply = await owner.request("GET", f"/settings/emails/sent/{signin['id']}")
        kept = reply["data"]
        assert "••••••" in kept["html"] and code not in kept["html"] and code not in kept["text"]
        _, reply = await owner.request("GET", "/settings/emails/sent", query={"q": "join settings"})
        assert [r["id"] for r in reply["data"]] == [item["id"]]

    # Another workspace sees none of it
    other, other_email = await new_workspace(app)
    async with client_for(app, host=f"{other}.formalie.dev") as http:
        stranger = SecureClient(http)
        await sign_in(stranger, other_email, PASSWORD)
        _, reply = await stranger.request("GET", f"/settings/emails/sent/{item['id']}")
        assert reply["error"]["code"] in ("FRM-GEN-1004", "FRM-SEC-1002")
        _, reply = await stranger.request("GET", "/settings/emails/sent")
        assert all(r["to"] != email for r in reply["data"])
    rows_db = superuser.execute("SELECT count(*) FROM formaly.sent_emails s JOIN platform.tenants t ON t.id = s.tenant_id "
                                "WHERE t.subdomain = %s AND s.deleted_at IS NULL", (sub,)).fetchone()
    assert rows_db[0] >= 2


async def test_own_domain_with_dns_records(app, owner_dsn, fake_dns, superuser) -> None:  # noqa: ANN001
    starter, starter_email = await new_workspace(app)
    async with client_for(app, host=f"{starter}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, starter_email, PASSWORD)
        # Starter: no own sending address
        for path, body in (("/settings/emails/sending/domain", {"address": "forms@acme.test"}),
                           ("/settings/emails/sending/smtp", {"host": "smtp.acme.test", "port": 587, "security": "starttls",
                                                              "username": None, "from_address": "a@acme.test"}),
                           ("/settings/emails/sending/mode", {"mode": "domain"})):
            status, reply = await owner.request("POST" if path.endswith("mode") else "PUT", path, body=body)
            assert (status, reply["error"]["code"]) == (402, "FRM-PLAN-1002"), path
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("GET", "/settings/emails/sending")
        assert reply["data"] == {"mode": "formalie", "from_address": "no-reply@formalie.dev",
                                 "formalie_address": "no-reply@formalie.dev", "domain": None, "smtp": None}
        _, reply = await owner.request("PUT", "/settings/emails/sending/domain", body={"address": "x@formalie.com"})
        assert reply["error"]["details"] == [{"field": "address", "message": "domain"}]
        _, reply = await owner.request("PUT", "/settings/emails/sending/domain", body={"address": "nope"})
        assert reply["error"]["code"] == "FRM-GEN-1002"

        status, reply = await owner.request("PUT", "/settings/emails/sending/domain", body={"address": " Forms@Acme.TEST "})
        assert status == 200, reply
        domain = reply["data"]["domain"]
        assert domain["address"] == "forms@acme.test" and domain["status"] == "pending" and "key" not in domain
        records = domain["records"]
        assert [(r["type"], r["name"]) for r in records] == [
            ("TXT", "acme.test"), ("CNAME", "fm1._domainkey.acme.test"), ("CNAME", "fm2._domainkey.acme.test"),
            ("CNAME", "fm-bounces.acme.test"), ("TXT", "_dmarc.acme.test")]
        assert records[0]["value"] == "v=spf1 include:spf.formalie.com ~all" and records[4]["optional"] is True
        assert records[3]["value"] == "bounces.formalie.com"

        # Nothing in DNS yet
        _, reply = await owner.request("POST", "/settings/emails/sending/domain/check")
        assert reply["data"]["domain"]["status"] == "pending" and reply["data"]["domain"]["problem"] == "not_found"
        _, reply = await owner.request("POST", "/settings/emails/sending/mode", body={"mode": "domain"})
        assert (reply["error"]["code"], reply["error"]["details"]) == ("FRM-SET-1001", [{"field": "mode", "message": "domain"}])

        # An SPF record without Formalie's include: the wrong value
        fake_dns.records[("acme.test", "TXT")] = ["v=spf1 include:other.example ~all"]
        _, reply = await owner.request("POST", "/settings/emails/sending/domain/check")
        assert reply["data"]["domain"]["status"] == "failed" and reply["data"]["domain"]["problem"] == "wrong_value"

        # DNS failing
        fake_dns.broken.add("acme.test")
        _, reply = await owner.request("POST", "/settings/emails/sending/domain/check")
        assert reply["data"]["domain"]["problem"] == "dns_error"
        fake_dns.broken.clear()

        # Everything in place (DMARC optional, SPF merged into their own record)
        fake_dns.records[("acme.test", "TXT")] = ["google-site-verification=x", "v=spf1 include:_spf.example include:spf.formalie.com -all"]
        for r in records[1:4]:
            fake_dns.records[(r["name"], "CNAME")] = [r["value"].upper() + "."]
        _, reply = await owner.request("POST", "/settings/emails/sending/domain/check")
        domain = reply["data"]["domain"]
        assert domain["status"] == "verified" and domain["problem"] is None and domain["checked_at"]
        assert [r["found"] for r in domain["records"]] == [True, True, True, True, False]
        _, reply = await owner.request("POST", "/settings/emails/sending/mode", body={"mode": "domain"})
        assert reply["data"]["mode"] == "domain" and reply["data"]["from_address"] == "forms@acme.test"

        # Emails now go out from the workspace's address through Formalie's relay
        sent_before = len(SENT)
        _, reply = await owner.request("POST", "/settings/emails/test", body={
            "key": "notification", "language": "en", "subject": "Hi", "body": "Body"})
        assert reply["success"], reply
        message = SENT[sent_before]
        assert message["route"] == {"mode": "domain", "address": "forms@acme.test", "domain": "acme.test"}
        _, reply = await owner.request("POST", "/settings/emails/preview", body={
            "key": "notification", "language": "en", "subject": "Hi", "body": "Body"})
        assert reply["data"]["from"] == "Settings Co <forms@acme.test>"

        # A record removed: the next check falls back to Formalie's address
        fake_dns.records.pop(("fm-bounces.acme.test", "CNAME"))
        _, reply = await owner.request("POST", "/settings/emails/sending/domain/check")
        assert reply["data"]["mode"] == "formalie" and reply["data"]["domain"]["status"] == "pending"

        _, reply = await owner.request("DELETE", "/settings/emails/sending/domain")
        assert reply["data"]["domain"] is None
        _, trail = await owner.request("GET", "/audit-logs", query={"filter[action]": "settings.updated"})
        fields = [c["field"] for entry in trail["data"] if entry["resource"]["name"] == "Sending address"
                  for c in entry["changes"]]
        assert {"sending_domain", "sending_domain_status", "sending_mode"} <= set(fields)


async def test_own_mail_server(app, owner_dsn, smtp, monkeypatch, superuser) -> None:  # noqa: ANN001
    sub, email = await new_workspace(app)
    await on_plan(owner_dsn, sub, "business")
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        server = {"host": "127.0.0.1", "port": smtp.port, "security": "none", "username": "mailer",
                  "password": "wrong", "from_address": "Team@Acme.test"}
        _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={**server, "host": "bad host!"})
        assert reply["error"]["details"] == [{"field": "host", "message": "host"}]
        status, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body=server)
        assert status == 200, reply
        saved = reply["data"]["smtp"]
        assert saved == {"host": "127.0.0.1", "port": smtp.port, "security": "none", "username": "mailer",
                         "has_password": True, "from_address": "team@acme.test", "status": "untested",
                         "checked_at": None, "problem": None}
        assert "wrong" not in str(reply)
        stored = superuser.execute("SELECT smtp_password_enc FROM formaly.email_sending e JOIN platform.tenants t "
                                   "ON t.id = e.tenant_id WHERE t.subdomain = %s", (sub,)).fetchone()[0]
        assert stored and "wrong" not in stored

        # A wrong password: the server refuses the sign-in
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["status"] == "failed" and reply["data"]["smtp"]["problem"] == "auth_failed"
        # The right one (left out keeps the stored one; given replaces it)
        _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={**server, "password": "s3cret-pass"})
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["status"] == "working", reply
        assert smtp.logins[-1] == "mailer" and smtp.messages == []  # signed in and checked, nothing sent
        _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={
            k: v for k, v in {**server, "from_address": "hello@acme.test"}.items() if k != "password"})
        assert reply["data"]["smtp"]["status"] == "working"  # same server and sign-in: still tested
        _, reply = await owner.request("POST", "/settings/emails/sending/mode", body={"mode": "smtp"})
        assert reply["data"]["from_address"] == "hello@acme.test"

        # Workspace emails now leave through the workspace's server, from its address
        sent_before = len(SENT)
        await owner.request("POST", "/settings/emails/test", body={
            "key": "notification", "language": "en", "subject": "Through yours", "body": "Body"})
        message = SENT[sent_before]
        assert message["route"]["mode"] == "smtp" and "s3cret" not in str(message["route"])
        email_service.deliver(message)
        got = smtp.messages[-1]
        assert got.sender == "hello@acme.test" and got.recipients == [email] and "Through yours" in got.data

        # The server refusing our sender, a closed port, something that isn't a mail server
        smtp.refuse_sender = True
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["problem"] == "sender_refused" and reply["data"]["mode"] == "formalie"
        smtp.refuse_sender = False
        other = FakeSmtp(greeting=b"HTTP/1.1 400 Bad Request\r\n").start()
        try:
            _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={**server, "port": other.port})
            _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
            assert reply["data"]["smtp"]["problem"] == "not_smtp"
        finally:
            other.stop()
        _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={**server, "port": 1})
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["problem"] == "unreachable"
        # Only public addresses outside development
        monkeypatch.setattr(get_settings(), "email_smtp_allow_local", False)
        _, reply = await owner.request("PUT", "/settings/emails/sending/smtp", body={**server, "port": smtp.port})
        _, reply = await owner.request("POST", "/settings/emails/sending/smtp/test")
        assert reply["data"]["smtp"]["problem"] == "unreachable"

        _, reply = await owner.request("DELETE", "/settings/emails/sending/smtp")
        assert reply["data"]["smtp"] is None and reply["data"]["mode"] == "formalie"

"""Unsubscribe links (owner, 2026-10-12): the token, the page's routes, the plain one-click address, the check before
sending, the headers, the audit entries, and that one workspace's links never touch another."""

from __future__ import annotations

import uuid

import psycopg

from app.modules.emails import unsubscribe as unsub
from app.modules.emails.service import SENT, send
from tests.conftest import client_for
from tests.db.test_auth_flows import app, seeded  # noqa: F401  (fixtures)
from tests.secure_client import SecureClient


def _tenant(superuser: psycopg.Connection, subdomain: str) -> tuple[uuid.UUID, uuid.UUID]:
    row = superuser.execute("SELECT id, primary_organisation_id FROM platform.tenants WHERE subdomain = %s",
                            (subdomain,)).fetchone()
    assert row, subdomain
    return row[0], row[1] or row[0]


def test_token_round_trip_and_tampering() -> None:
    target = unsub.Target(uuid.uuid4(), "remedylegal", "Someone@Example.TEST", "notification", "form_limit")
    token = unsub.token_for(target)
    back = unsub.read_token(token)
    assert back is not None and back.email == "someone@example.test" and back.ref == "form_limit"
    payload, mac = token.split(".")
    assert unsub.read_token(f"{payload}.{'A' * len(mac)}") is None  # a forged signature
    assert unsub.read_token(f"{payload[:-2]}xx.{mac}") is None  # a changed payload
    assert unsub.read_token("nonsense") is None and unsub.read_token(None) is None


def test_link_carries_the_list_unsubscribe_headers() -> None:
    link = unsub.link_for(unsub.Target(uuid.uuid4(), "remedylegal", "a@b.test", "daily_digest", ""))
    assert link.page_url.endswith(f"/email/unsubscribe?t={link.token}")
    assert "/api/v1/email/one-click?t=" in link.headers["List-Unsubscribe"]
    assert link.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    sent_before = len(SENT)
    send("a@b.test", "daily_digest", "en", {"workspace": "Remedy Legal", "name": "A", "summary": "S",
                                           "link": "https://x.test"}, unsubscribe=link)
    message = SENT[sent_before]
    assert message["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert link.page_url in message["html"]  # the footer's Unsubscribe link


async def test_page_routes_stop_and_undo_with_audit(app, superuser) -> None:  # noqa: ANN001
    tenant_id, _ = _tenant(superuser, "remedylegal")
    email = f"unsub-{uuid.uuid4().hex[:6]}@example.test"
    token = unsub.token_for(unsub.Target(tenant_id, "remedylegal", email, "notification", "form_limit"))
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        page = SecureClient(http)
        status, view = await page.request("GET", "/public/unsubscribe", query={"t": token})
        assert status == 200, view
        assert view["data"]["kind"] == "notification" and view["data"]["subject"] == "form_limit"
        assert view["data"]["unsubscribed"] is False and "@" in view["data"]["email"] and email not in view["data"]["email"]
        _, done = await page.request("POST", "/public/unsubscribe", body={"t": token})
        assert done["data"]["unsubscribed"] is True
        _, again = await page.request("POST", "/public/unsubscribe", body={"t": token})
        assert again["data"]["unsubscribed"] is True  # twice changes nothing more
        _, undone = await page.request("POST", "/public/unsubscribe/undo", body={"t": token})
        assert undone["data"]["unsubscribed"] is False
        _, bad = await page.request("GET", "/public/unsubscribe", query={"t": token[:-3] + "AAA"})
        assert bad["error"]["code"] == "FRM-GEN-1004"
    actions = [r[0] for r in superuser.execute(
        "SELECT action FROM formaly.audit_logs WHERE actor_email = %s ORDER BY occurred_at", (email,)).fetchall()]
    assert actions == ["settings.email_unsubscribed", "settings.email_resubscribed"]
    rows = superuser.execute("SELECT deleted_at IS NOT NULL FROM formaly.email_unsubscribes WHERE email = %s",
                             (email,)).fetchall()
    assert rows == [(True,)]  # undo keeps the history (soft delete)


async def test_one_click_is_plain_and_prepare_then_skips(app, superuser) -> None:  # noqa: ANN001
    from app.core.db.session import db_session

    tenant_id, organisation_id = _tenant(superuser, "remedylegal")
    email = f"click-{uuid.uuid4().hex[:6]}@example.test"
    target = unsub.Target(tenant_id, "remedylegal", email, "daily_digest", "")
    async with client_for(app, host="manage.formalie.dev:2202") as http:
        reply = await http.post(f"/api/v1/email/one-click?t={unsub.token_for(target)}",
                                content="List-Unsubscribe=One-Click",
                                headers={"content-type": "application/x-www-form-urlencoded"})
        assert reply.status_code == 200, reply.text
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        assert await unsub.prepare(db, tenant_id=tenant_id, subdomain="remedylegal", email=email,
                                   kind="daily_digest") is None  # stopped: not sent
        other = await unsub.prepare(db, tenant_id=tenant_id, subdomain="remedylegal", email=email,
                                    kind="notification", ref="form_limit")
        assert other is not None and other.page_url  # other kinds still go out, with their own link
        alert = await unsub.prepare(db, tenant_id=tenant_id, subdomain="remedylegal", email=email,
                                    kind="notification", ref="security_alert")
        assert alert is not None and not alert.page_url  # security alerts: always sent, no link


async def test_a_link_never_reaches_another_workspace(app, superuser) -> None:  # noqa: ANN001
    remedy_id, _ = _tenant(superuser, "remedylegal")
    # A token for remedylegal's id but naming another subdomain is refused
    token = unsub.token_for(unsub.Target(remedy_id, "samathtax", "x@example.test", "daily_digest", ""))
    async with client_for(app, host="manage.formalie.dev") as http:
        _, reply = await SecureClient(http).request("POST", "/public/unsubscribe", body={"t": token})
    assert reply["error"]["code"] == "FRM-GEN-1004"
    assert superuser.execute("SELECT count(*) FROM formaly.email_unsubscribes WHERE email = 'x@example.test'"
                             ).fetchone() == (0,)

"""The platform bridge's pure parts (B16): request signing, mutual TLS checks, the event wire format with personal
data stripped, feature switch rollouts and the reader's hidden columns."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.core.context import TenantInfo
from app.core.events.schemas import EventEnvelope
from app.core.events.wire import PLATFORM_EVENTS, clean_properties, to_wire
from app.modules.platform_bridge import signing as sg
from app.modules.platform_bridge.globals import flag_on
from app.modules.platform_bridge.grants import is_hidden

SECRET = "s3cret-" + "x" * 40


def test_canonical_string_and_signature_cover_every_signed_part() -> None:
    headers = {"X-Platform-Staff-Id": "st-1", "X-Platform-Staff-Name": "Ada%20Lovelace", "Idempotency-Key": "k-12345678"}
    text = sg.canonical("post", "/internal/admin/v1/tenants/x/suspend?a=1", "1760000000", "n" * 20, b'{"a":1}', headers)
    lines = text.split("\n")
    assert lines[:5] == ["FORMALIE-PLATFORM-V1", "POST", "/internal/admin/v1/tenants/x/suspend?a=1", "1760000000", "n" * 20]
    assert lines[5] == sg.body_hash(b'{"a":1}') and lines[6:] == ["st-1", "Ada%20Lovelace", "", "", "k-12345678"]
    signed = sg.signature(SECRET, text)
    assert signed.startswith("v1=") and len(signed) == 67 and sg.matches(SECRET, text, signed)
    # Any change to the body, the path, a staff header or the secret breaks it
    for changed in (sg.canonical("POST", "/internal/admin/v1/tenants/x/suspend?a=1", "1760000000", "n" * 20, b'{"a":2}', headers),
                    sg.canonical("POST", "/internal/admin/v1/tenants/y/suspend?a=1", "1760000000", "n" * 20, b'{"a":1}', headers),
                    sg.canonical("POST", "/internal/admin/v1/tenants/x/suspend?a=1", "1760000000", "n" * 20, b'{"a":1}',
                                 {**headers, "X-Platform-Staff-Name": "Someone%20Else"})):
        assert not sg.matches(SECRET, changed, signed)
    assert not sg.matches("another-" + "y" * 40, text, signed)


def test_keys_window_and_client_certificates() -> None:
    assert sg.keys_of(["plat1:" + "a" * 32, "short:abc", "nocolon", "plat2:" + "b" * 40]) == {"plat1": "a" * 32, "plat2": "b" * 40}
    assert sg.fresh("1000", 300, now=1200) and sg.fresh("1300", 300, now=1000) and not sg.fresh("1000", 300, now=1301)
    assert not sg.fresh("soon", 300)
    fp = "AB:CD:" + "12" * 30
    assert sg.mtls_ok("SUCCESS", fp.lower().replace(":", ""), [fp])
    assert not sg.mtls_ok("FAILED:unknown ca", fp, [fp]) and not sg.mtls_ok("SUCCESS", "ff" * 32, [fp])
    assert not sg.mtls_ok("SUCCESS", None, [fp]) and not sg.mtls_ok("SUCCESS", fp, [])


def test_sign_headers_are_what_the_server_checks() -> None:
    headers = sg.sign_headers("plat1", SECRET, "GET", "/internal/admin/v1/health/services", timestamp=1760000000, nonce="n" * 24)
    text = sg.canonical("GET", "/internal/admin/v1/health/services", "1760000000", "n" * 24, b"", headers)
    assert sg.matches(SECRET, text, headers["X-Platform-Signature"]) and sg.NONCE.match(headers["X-Platform-Nonce"])


def _event(type_: str, payload: dict) -> EventEnvelope:
    return EventEnvelope(type=type_, tenant_id=uuid.uuid4(), organisation_id=uuid.uuid4(), actor_id=uuid.uuid4(),
                         occurred_at=datetime(2026, 10, 12, tzinfo=UTC), payload=payload)


def test_events_leave_without_personal_data() -> None:
    shaped = _event("response.created", {
        "_shape": "platform", "source": "public", "country": "GB", "city": "London", "device": "mobile",
        "browser": "Safari", "os": "iOS", "plan": "starter", "session_ref": None, "language": "en",
        "properties": {"form_id": "f1", "response_id": "r1", "channel": "link", "data": {"q1": "secret answer"},
                       "email": "ada@example.org", "respondent_name": "Ada", "duration_seconds": 42}})
    wire = to_wire(shaped)
    assert set(wire) == {"id", "type", "occurred_at", "tenant_ref", "organisation_ref", "actor_ref", "session_ref",
                         "source", "country", "region", "city", "device", "browser", "os", "language", "plan",
                         "properties", "version", "trace_id"}
    assert wire["properties"] == {"form_id": "f1", "response_id": "r1", "channel": "link", "duration_seconds": 42}
    assert wire["source"] == "public" and wire["country"] == "GB" and wire["occurred_at"] == "2026-10-12T00:00:00.000Z"
    # Older plain payloads: their keys are the properties, still filtered; never an email or an IP anywhere
    legacy = to_wire(_event("security.alert", {"email": "ada@example.org", "reason": "ip_not_allowed",
                                                "who": "ada@example.org", "ip": "203.0.113.9", "from": "203.0.113.9"}))
    assert legacy["properties"] == {"reason": "ip_not_allowed"} and legacy["source"] == "worker"
    dumped = json.dumps([wire, legacy])
    assert "@" not in dumped and "203.0.113" not in dumped and "secret answer" not in dumped and "Ada" not in dumped
    # Listed events keep only their own keys; objects never pass
    assert clean_properties("tenant.signed_up", {"plan": "starter", "subdomain": "acme", "x": 1}) == {"plan": "starter"}
    assert clean_properties("custom.thing", {"nested": {"a": 1}, "count": 3}) == {"count": 3}
    assert "auth.signed_in" in PLATFORM_EVENTS and "response.created" in PLATFORM_EVENTS


def test_feature_switch_rollout_is_stable_and_respects_plans_and_workspaces() -> None:
    tenants = [TenantInfo(id=uuid.uuid4(), subdomain=f"t{i}", name="T", status="active", organisation_id=uuid.uuid4(),
                          plan_id="starter" if i % 2 else "business") for i in range(400)]
    half = {"key": "new_builder", "enabled": True, "plans": [], "tenant_ids": [], "rollout_percent": 50}
    on = [t for t in tenants if flag_on(half, t)]
    assert 140 < len(on) < 260 and all(flag_on(half, t) for t in on)  # stable for the same workspace
    assert not any(flag_on({**half, "enabled": False}, t) for t in tenants)
    business = {**half, "plans": ["business"], "rollout_percent": 100}
    assert all(flag_on(business, t) == (t.plan_id == "business") for t in tenants)
    chosen = {**half, "plans": ["enterprise"], "rollout_percent": 0, "tenant_ids": [str(tenants[0].id)]}
    assert flag_on(chosen, tenants[0]) and not flag_on(chosen, tenants[1])


def test_reader_hides_secrets_and_answers() -> None:
    for table, column in (("users", "password_hash"), ("api_tokens", "secret_enc"), ("responses", "data"),
                          ("request_logs", "request_body"), ("support_sessions", "ticket_hash"),
                          ("admin_calls", "response_enc"), ("form_versions", "schema"), ("ai_requests", "prompt")):
        assert is_hidden(table, column), (table, column)
    for table, column in (("users", "email"), ("responses", "submitted_at"), ("forms", "name"), ("tenants", "plan_id")):
        assert not is_hidden(table, column), (table, column)


def test_the_published_consumer_drops_caches_and_dead_letters_bad_messages(redis) -> None:  # noqa: ANN001
    """platform.published from the bus: the named tables' cache versions move on; a malformed message is rejected
    (to the dead letters), never requeued."""
    import asyncio

    from app.core.cache.tiers import version_key
    from app.modules.platform_bridge.consumer import PublishedConsumer, published_queue

    class Message:
        def __init__(self) -> None:
            self.acked = self.rejected = False

        def ack(self) -> None:
            self.acked = True

        def reject(self, requeue: bool) -> None:
            assert requeue is False
            self.rejected = True

    consumer = PublishedConsumer.__new__(PublishedConsumer)
    consumer.loop = asyncio.new_event_loop()
    try:
        good = Message()
        consumer.on_message({"table": "platform_settings", "ids": ["legal"], "version": 4}, good)
        assert good.acked
        consumer.on_message(json.dumps({"tables": ["feature_flags", "nothing_we_cache"]}), Message())
        versions = consumer.loop.run_until_complete(redis.mget(version_key(None, "global:platform_settings"),
                                                               version_key(None, "global:feature_flags")))
        assert versions == ["1", "1"]
        bad = Message()
        consumer.on_message("[not an object]", bad)
        assert bad.rejected and not bad.acked
    finally:
        consumer.loop.close()
    queue = published_queue()
    assert queue.routing_key == "platform.published" and queue.exchange.name == "formalie.events" and queue.durable

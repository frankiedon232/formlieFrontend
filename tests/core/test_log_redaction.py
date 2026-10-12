"""B17 security review M8, M9, M10, M12, M15, L14, L18: what the logs keep, body ceilings and rate-limit keys."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.context import RequestContext, reset_context, set_context
from app.core.logging.redact import SECRET_PATH_PARAMS, mask_path, redact_text
from app.core.logging.setup import JsonFormatter, mask
from app.core.net import ip_bucket
from app.modules.logs.capture import body_policy, body_record, names_only, parse_query, response_body
from tests.conftest import MemoryShipper, build_app, client_for

FERNET = "gAAAAABn" + "x" * 80
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijkl"


@pytest.fixture
def shipper() -> MemoryShipper:
    return MemoryShipper()


# ── Redaction by value ───────────────────────────────────────────────────────────

def test_secret_values_are_redacted_whatever_their_field() -> None:
    assert redact_text(f"refresh {FERNET} done") == "refresh *** done"
    assert redact_text(f"id_token={JWT}") == "id_token=***"
    assert redact_text("key formalie_secret_live_AbCdEf123456") == "key ***"
    assert redact_text("postgresql://app:hunter2@db.example.com/x") == "postgresql://app:***@db.example.com/x"
    assert redact_text("Authorization: Bearer abcdefgh12345678") == "Authorization: Bearer ***"
    assert redact_text("-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----") == "***"
    plain = "The token expired for formalie_worker on https://acme.formalie.dev/forms"
    assert redact_text(plain) == plain  # ordinary words, role names and addresses stay
    assert mask({"note": f"sent {FERNET}", "nested": [{"dsn": "x"}]}) == {"note": "sent ***", "nested": [{"dsn": "***"}]}


# ── Tokens in paths (M9) ─────────────────────────────────────────────────────────

def test_path_parameters_named_like_a_credential_are_masked() -> None:
    assert mask_path("/api/v1/public/invites/abc123/accept", "/api/v1/public/invites/{token}/accept") == \
        "/api/v1/public/invites/***/accept"
    assert mask_path("/api/v1/public/forms/k1/sessions/s3cr3t", "/api/v1/public/forms/{key}/sessions/{token}") == \
        "/api/v1/public/forms/k1/sessions/***"
    assert mask_path("/api/v1/forms/f1", "/api/v1/forms/{form_id}") == "/api/v1/forms/f1"
    # No route matched (refused before routing, the JSON formatter): the known token addresses
    assert mask_path("/api/v1/response-files/tok") == "/api/v1/response-files/***"
    assert mask_path("/api/v1/public/short/AbC12") == "/api/v1/public/short/***"
    assert mask_path("/api/v1/forms/f1") == "/api/v1/forms/f1"


def test_every_route_with_a_credential_in_its_path_is_covered_without_its_template(settings, redis) -> None:  # noqa: ANN001
    """When a request is refused before routing only the fallback applies: it must know every such address."""
    app = build_app(settings)
    found = 0
    for template in app.openapi()["paths"]:
        params = [p.split(":")[0] for p in template.replace("}", "{").split("{")[1::2]]
        if not any(p.lower() in SECRET_PATH_PARAMS for p in params):
            continue
        found += 1
        concrete = template
        for p in params:
            concrete = concrete.replace(f"{{{p}}}", f"VALUE{p}x").replace(f"{{{p}:path}}", f"VALUE{p}x")
        masked = mask_path(concrete)
        for p in params:
            if p.lower() in SECRET_PATH_PARAMS:
                assert f"VALUE{p}x" not in masked, (template, masked)
    assert found >= 5


async def test_the_request_log_and_the_log_line_never_carry_a_path_token(settings, redis, shipper, caplog) -> None:  # noqa: ANN001
    caplog.set_level(logging.INFO, logger="formalie.request")
    async with client_for(build_app(settings, shipper)) as c:
        await c.get("/api/v1/public/invites/INVITE-SECRET-1", headers={
            "referer": "https://manage.formalie.dev/auth/welcome?ticket=t0p"})
        await c.get("/api/v1/response-files/FILE-SECRET-2")
    dumped = json.dumps(shipper.records)
    assert "INVITE-SECRET-1" not in dumped and "FILE-SECRET-2" not in dumped
    assert shipper.records[0]["path"] == "/api/v1/public/invites/***"
    assert not any("SECRET" in r.getMessage() for r in caplog.records if r.name.startswith("formalie"))


def test_the_json_formatter_masks_the_path(settings) -> None:  # noqa: ANN001
    ctx = RequestContext(trace_id="t", started_at=0.0, method="GET", path="/api/v1/public/invites/PENDING-INVITE")
    token = set_context(ctx)
    try:
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "Bearer abcdefgh12345678 used", (), None)
        line = json.loads(JsonFormatter(settings).format(record))
    finally:
        reset_context(token)
    assert line["path"] == "/api/v1/public/invites/***" and line["message"] == "Bearer *** used"


# ── Bodies by route (M8) ─────────────────────────────────────────────────────────

def test_routes_with_answers_or_secrets_keep_field_names_only() -> None:
    assert body_policy("/api/v1/public/forms/abc/submit") == "names"
    assert body_policy("/api/v1/responses/r1") == "names"
    assert body_policy("/api/v1/api-endpoints/e1") == "names"
    assert body_policy("/api/v1/datasources/d1/query") == "names"
    assert body_policy("/api/v1/storage/tok") == "none"
    assert body_policy("/api/v1/forms/f1") == "masked"
    answers = {"answers": {"iban": "GB33BUKB20201555555555", "diagnosis": "flu"}, "page": 2}
    record = body_record("application/json", json.dumps(answers).encode(), 10, "h", False,
                         "/api/v1/public/forms/abc/submit")
    assert record["request_body"] == {"answers": {"iban": "***", "diagnosis": "***"}, "page": "***"}
    assert record["request_body_keys"] == ["answers", "page"]
    # Enveloped: the decrypted body follows the same policy
    record = body_record(None, b"", 10, "h", False, "/api/v1/responses/r1",
                         {"body": {"note": "private"}, "method": "PATCH"})
    assert record["request_body"] == {"body": {"note": "***"}, "envelope": True}
    assert names_only([{"a": None}]) == [{"a": None}]


def test_value_is_masked_next_to_a_name_and_queries_on_answer_routes() -> None:
    headers = {"name": "endpoint", "headers": [{"name": "X-Shop-Key", "value": "s3cret-value"}]}
    record = body_record("application/json", json.dumps(headers).encode(), 10, "h", False, "/api/v1/forms/f1")
    assert record["request_body"]["headers"] == [{"name": "X-Shop-Key", "value": "***"}]
    assert parse_query("t=UNSUB-TOKEN&page=2", "/api/v1/public/unsubscribe") == {"t": "***", "page": "2"}
    error = json.dumps({"success": False, "error": {"code": "FRM-GEN-1002", "details": []}}).encode()
    assert response_body("application/json", error, False, "names")["error"]["code"] == "FRM-GEN-1002"
    data = json.dumps({"success": True, "data": {"email": "ada@example.com"}}).encode()
    assert response_body("application/json", data, False, "names") == {"success": "***", "data": {"email": "***"}}


async def test_a_public_submit_body_is_logged_without_its_answers(settings, redis, shipper) -> None:  # noqa: ANN001
    async with client_for(build_app(settings, shipper)) as c:
        await c.post("/api/v1/public/forms/abc/submit", json={"answers": {"passport_number": "X1234567"}})
    r = shipper.records[0]
    assert "X1234567" not in json.dumps(r)
    assert r["request_body"] == {"answers": {"passport_number": "***"}}


# ── Body ceiling and streaming (M12) ─────────────────────────────────────────────

async def test_a_body_over_the_ceiling_is_refused_before_it_is_held(settings, redis, shipper) -> None:  # noqa: ANN001
    app = build_app(settings, shipper, request_body_max_bytes=1000)
    async with client_for(app) as c:
        response = await c.post("/api/v1/crypto/handshake", content=b"x" * 5000,
                                headers={"content-type": "application/json"})
        assert response.status_code == 413 and response.json()["error"]["code"] == "FRM-FILE-1002"

        async def chunks():  # noqa: ANN202 (no Content-Length: counted as it is read)
            for _ in range(10):
                yield b"y" * 500

        response = await c.post("/api/v1/crypto/handshake", content=chunks(),
                                headers={"content-type": "application/json"})
        assert response.status_code == 413 and response.json()["error"]["code"] == "FRM-FILE-1002"
        small = await c.post("/api/v1/crypto/handshake", json={"a": 1})
        assert small.status_code != 413
    assert shipper.records[0]["error_code"] == "FRM-FILE-1002" and shipper.records[0]["status"] == 413


async def test_uploads_keep_their_own_limit_and_no_body_in_the_log(settings, redis, shipper) -> None:  # noqa: ANN001
    app = build_app(settings, shipper, request_body_max_bytes=1000)
    async with client_for(app) as c:
        response = await c.put("/api/v1/storage/not-a-token", content=b"z" * 5000)
    assert response.status_code != 413  # the storage route decides (here: an unknown link)
    r = shipper.records[0]
    assert r["request_body"] is None and r["request_body_text"] is None


async def test_an_unread_body_is_kept_only_up_to_the_log_limit(settings, redis, shipper) -> None:  # noqa: ANN001
    app = build_app(settings, shipper, request_log_body_max_bytes=100)
    sent: list[int] = []

    async def chunks():  # noqa: ANN202
        for _ in range(50):
            sent.append(1)
            yield b"q" * 1000

    async with client_for(app) as c:
        await c.post("/api/v1/billing/webhooks/payoneer", content=chunks(), headers={"content-type": "text/plain"})
    r = shipper.records[0]
    assert r["status"] == 404 and r["request_body_truncated"] is True and "oversized" in r["flags"]
    assert r["request_bytes"] < 50_000  # the rest was never read into the log


# ── Rate-limit keys and the window (M15, L14) ───────────────────────────────────

def test_ipv6_callers_count_per_64() -> None:
    assert ip_bucket("2001:db8:1:2::1") == ip_bucket("2001:db8:1:2:abcd::9") == "2001:db8:1:2::/64"
    assert ip_bucket("2001:db8:1:3::1") != ip_bucket("2001:db8:1:2::1")
    assert ip_bucket("::ffff:198.51.100.1") == "198.51.100.1"
    assert ip_bucket("203.0.113.7") == "203.0.113.7" and ip_bucket(None) == "unknown"


async def test_the_ip_tier_counts_one_ipv6_network_once(settings, redis) -> None:  # noqa: ANN001
    app = build_app(settings, rate_limit_ip_per_minute=2)
    statuses = []
    for n in range(3):
        async with client_for(app, peer=f"2001:db8:aa:bb::{n + 1}") as c:
            statuses.append((await c.get("/api/v1/health")).status_code)
    assert statuses == [200, 200, 429]


async def test_a_parallel_burst_cannot_pass_the_window(redis) -> None:  # noqa: ANN001
    from app.core.middleware.rate_limit import SlidingWindowLimiter

    limiter = SlidingWindowLimiter(redis)
    bucket = f"burst:{uuid.uuid4().hex}"
    results = await asyncio.gather(*(limiter.hit(bucket, 5, 60) for _ in range(20)))
    assert sum(r.allowed for r in results) == 5
    assert await redis.zcard(f"fm:v1:rl:{bucket}") == 5  # refused hits are not counted


async def test_sign_in_and_code_limits_fail_closed_without_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.errors import FrmError
    from app.core.middleware.rate_limit import RateLimiterUnavailable
    from app.core.security import limits

    async def down(*_: object) -> None:
        raise RateLimiterUnavailable("down")

    monkeypatch.setattr(limits._limiter, "hit", down)  # noqa: SLF001
    with pytest.raises(FrmError) as refused:
        await limits.check("route:otp-verify:ip:203.0.113.7", 20, 60)
    assert refused.value.code == "FRM-GEN-5003"
    with pytest.raises(FrmError):
        await limits.per_value("login", "ada@example.com", limit=10, window_seconds=600)
    await limits.check("route:forms-list:ip:203.0.113.7", 20, 60)  # everything else: allowed


# ── Retention and engines (M8, L18) ─────────────────────────────────────────────

def test_request_log_retention_cutoff_and_task(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.db import tasks

    now = datetime(2026, 10, 12, tzinfo=UTC)
    assert tasks.retention_cutoff(30, now) == now - timedelta(days=30)
    assert tasks.retention_cutoff(2, now) == now - timedelta(days=7)  # never under a week
    assert tasks.retention_cutoff(0, now) is None
    calls: list[dict] = []

    class Result:
        def scalar_one(self) -> int:
            return 2

    class FakeSession:
        def __init__(self, *_: object) -> None:
            pass

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_: object) -> None:
            pass

        def begin(self):  # noqa: ANN202
            return self

        def execute(self, statement, params):  # noqa: ANN001, ANN202
            calls.append({"sql": str(statement), **params})
            return Result()

    monkeypatch.setattr(tasks, "Session", FakeSession)
    monkeypatch.setattr(tasks, "worker_engine", lambda: None)
    assert tasks.drop_expired_partitions.run() == 2
    assert "platform.drop_expired_partitions" in calls[0]["sql"] and calls[0]["t"].endswith(".request_logs")
    assert datetime.now(UTC) - calls[0]["before"] >= timedelta(days=30) - timedelta(minutes=1)
    from app.workers.celery_app import celery_app

    # Off until the owner approves the hard delete (2026-10-12)
    assert not any(e["task"] == "db.drop_expired_partitions" for e in celery_app.conf.beat_schedule.values())


def test_engines_hide_bound_parameters(settings) -> None:  # noqa: ANN001
    from app.core.db.engines import make_engine

    engine = make_engine("postgresql://u:p@127.0.0.1:5432/x", settings, name="primary")
    assert engine.sync_engine.hide_parameters is True


# ── The API service's own log (M10) ─────────────────────────────────────────────

def test_the_api_log_never_keeps_secrets_in_bodies() -> None:
    from app.modules.api_service.traffic import mask_secrets

    body = {"client_id": "formalie_client_live_x", "client_secret": "abc", "data": {"access_token": "t", "name": "Ada"},
            "note": "formalie_access_live_ABCDEFGH1234"}
    assert mask_secrets(body) == {"client_id": "formalie_client_live_x", "client_secret": "••••",
                                  "data": {"access_token": "••••", "name": "Ada"}, "note": "***"}

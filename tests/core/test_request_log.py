"""The request log: one full record per request, secrets masked, written off the request path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.logs import service
from app.modules.logs.capture import attack_flags, mask_headers
from app.modules.logs.service import RequestLogShipper, device_fields, enrich, to_row
from app.core.logging.geo import GeoLookup
from tests.conftest import MemoryShipper, build_app, client_for

CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/131.0.0.0 Safari/537.36")


@pytest.fixture
def shipper() -> MemoryShipper:
    return MemoryShipper()


@pytest.fixture
async def logged(settings, redis, shipper):  # noqa: ANN001
    async with client_for(build_app(settings, shipper)) as c:
        yield c, shipper.records


async def test_every_request_is_recorded_in_full(logged) -> None:  # noqa: ANN001
    client, records = logged
    response = await client.get("/api/v1/health?lang=en&ticket=abc123", headers={
        "user-agent": CHROME, "authorization": "Bearer secret-token", "cookie": "formalie_rt=abc; theme=dark",
        "origin": "https://acme.formalie.dev", "referer": "https://manage.formalie.dev/auth/welcome?ticket=t0p",
        "x-formalie-client": "portal/1.4.2",
    })
    assert len(records) == 1
    r = records[0]
    assert r["id"] == r["trace_id"] == response.headers["x-trace-id"]
    assert (r["method"], r["path"], r["route"], r["status"]) == ("GET", "/api/v1/health", "/api/v1/health", 200)
    assert r["host"] == "manage.formalie.dev" and r["host_kind"] == "manage" and r["scheme"] == "https"
    assert r["query"] == {"lang": "en", "ticket": "***"}
    assert r["client_ip"] == "203.0.113.7" and r["peer_ip"] == "203.0.113.7" and r["proxy_trusted"] is False
    assert r["request_headers"]["authorization"] == "Bearer ***"
    assert r["request_headers"]["cookie"] == "formalie_rt=***; theme=***"
    assert r["request_headers"]["user-agent"] == CHROME
    assert r["referer"] == "https://manage.formalie.dev/auth/welcome?ticket=%2A%2A%2A"
    assert (r["client_app"], r["client_version"]) == ("portal", "1.4.2")
    assert r["response_headers"]["content-type"] == "application/json" and r["response_content_type"] == "application/json"
    assert r["response_body"] is None  # successful bodies are not kept ("errors")
    assert r["duration_ms"] >= 0 and r["response_bytes"] > 0
    assert "secret-token" not in json.dumps(r) and "t0p" not in json.dumps(r) and "abc123" not in json.dumps(r)


async def test_json_bodies_are_kept_with_secrets_masked(logged) -> None:  # noqa: ANN001
    client, records = logged
    await client.post("/api/v1/billing/webhooks/payoneer", json={  # plaintext route without a handler yet: 404
        "client_public_key": "BAAA", "client_ts": 1, "password": "hunter2", "profile": {"api_key": "k", "name": "Ada"},
    })
    r = records[0]
    assert r["request_body"] == {"client_public_key": "BAAA", "client_ts": 1, "password": "***",
                                 "profile": {"api_key": "***", "name": "Ada"}}
    assert r["request_body_keys"] == ["client_public_key", "client_ts", "password", "profile"]
    assert r["request_body_fields"] == 4 and r["request_body_truncated"] is False
    assert len(r["request_body_sha256"]) == 64 and r["request_content_type"] == "application/json"
    assert r["response_body"]["error"]["code"] == "FRM-GEN-1004"  # error bodies are kept
    assert "hunter2" not in json.dumps(r)


async def test_one_time_codes_are_masked_on_sign_in_paths(logged) -> None:  # noqa: ANN001
    client, records = logged
    await client.post("/api/v1/auth/otp/verify", json={"challenge_id": "c1", "code": "123456"})
    assert records[0]["request_body"] == {"challenge_id": "c1", "code": "***"}
    assert "invalid_envelope" in records[0]["flags"] and records[0]["error_code"] == "FRM-SEC-1001"


async def test_refused_requests_are_recorded_with_their_reason(settings, redis, shipper) -> None:  # noqa: ANN001
    app = build_app(settings, shipper, rate_limit_ip_per_minute=1)
    async with client_for(app, host="nobody.formalie.dev") as c:
        await c.get("/api/v1/forms")
        await c.get("/api/v1/forms")
    first, second = shipper.records
    assert (first["status"], first["error_code"], first["host_kind"]) == (404, "FRM-TEN-1001", "tenant")
    assert first["subdomain"] == "nobody"
    assert (second["status"], second["error_code"], second["rate_limited"]) == (429, "FRM-GEN-1029", True)
    assert (second["subdomain"], second["host_kind"]) == ("nobody", "tenant")  # known even though refused early


async def test_workspace_is_recorded(settings, redis, shipper) -> None:  # noqa: ANN001
    async with client_for(build_app(settings, shipper), host="acme.formalie.dev") as c:
        await c.get("/api/v1/forms")
    r = shipper.records[-1]
    assert r["tenant_id"] == "01900000-0000-7000-8000-00000000000a" and r["subdomain"] == "acme"


async def test_attack_patterns_are_flagged(logged) -> None:  # noqa: ANN001
    client, records = logged
    await client.get("/api/v1/forms?q=' or 1=1 --")
    await client.get("/api/v1/forms?q=<script>alert(1)</script>")
    await client.get("/api/v1/files/..%2f..%2fetc/passwd")
    assert "sqli" in records[0]["flags"]
    assert "xss" in records[1]["flags"]
    assert "path_traversal" in records[2]["flags"]
    assert attack_flags("/api/v1/datasources/x/query", "", "select * from t union select 1") == set()


async def test_oversized_bodies_are_cut_but_hashed_in_full(settings, redis, shipper) -> None:  # noqa: ANN001
    async with client_for(build_app(settings, shipper, request_log_body_max_bytes=10)) as c:
        await c.post("/api/v1/crypto/handshake", json={"a": "x" * 100})
    r = shipper.records[0]
    assert r["request_body_truncated"] is True and r["request_body"] is None and "oversized" in r["flags"]
    assert r["request_bytes"] > 100


async def test_real_client_ip_through_the_trusted_proxy(settings, redis, shipper) -> None:  # noqa: ANN001
    async with client_for(build_app(settings, shipper), host="formalie.dev", peer="127.0.0.1") as c:
        await c.get("/api/v1/health", headers={"x-forwarded-for": "198.51.100.23, 127.0.0.1",
                                               "x-forwarded-host": "acme.formalie.dev", "cf-ipcountry": "GB"})
    r = shipper.records[0]
    assert (r["client_ip"], r["peer_ip"], r["proxy_trusted"]) == ("198.51.100.23", "127.0.0.1", True)
    assert r["forwarded_for"] == "198.51.100.23, 127.0.0.1" and r["host"] == "acme.formalie.dev"


# ── Enrichment ────────────────────────────────────────────────────────────────

def test_device_from_user_agent() -> None:
    fields = device_fields(CHROME)
    assert (fields["device_type"], fields["browser"], fields["os"]) == ("desktop", "Chrome", "Windows")
    assert device_fields("Googlebot/2.1 (+http://www.google.com/bot.html)")["device_type"] == "bot"
    iphone = device_fields("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                           "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    assert (iphone["device_type"], iphone["os"]) == ("mobile", "iOS")


def test_location_sources(tmp_path: Path) -> None:
    geo = GeoLookup(tmp_path)  # no MaxMind files here
    assert geo.lookup("10.1.2.3")["geo_source"] == "private"
    assert geo.lookup("127.0.0.1")["geo_source"] == "private"
    assert geo.lookup(None)["geo_source"] == "none"
    cf = {"cf-ipcountry": "GB", "cf-ipcity": "London", "cf-region": "England", "cf-iplatitude": "51.5",
          "cf-iplongitude": "-0.12", "cf-timezone": "Europe/London"}
    assert geo.lookup("81.2.69.160", cf, trusted_proxy=False)["geo_source"] == "none"  # headers from anyone: ignored
    found = geo.lookup("81.2.69.160", cf, trusted_proxy=True)
    assert found["geo_source"] == "cloudflare" and found["country"] == "GB" and found["city"] == "London"
    assert found["latitude"] == 51.5


def test_enrich_and_row_conversion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.modules.logs.service.get_geo", lambda: GeoLookup(tmp_path))
    record = {"id": "01900000-0000-7000-8000-000000000001", "occurred_at": "2026-10-11T10:00:00+00:00",
              "trace_id": "t", "method": "GET", "path": "/", "status": 200, "client_ip": "10.0.0.1",
              "user_agent": CHROME, "tenant_id": None, "not_a_column": 1}
    row = to_row(enrich(record))
    assert row["geo_source"] == "private" and row["browser"] == "Chrome"
    assert "not_a_column" not in row and row["occurred_at"].year == 2026 and row["id"].version == 7


def test_header_masking_keeps_shape_not_secrets() -> None:
    headers = mask_headers([(b"Authorization", b"Basic dXNlcjpwYXNz"), (b"X-CSRF-Token", b"abc"),
                            (b"X-Formalie-Envelope", b"eyJ" * 50), (b"Accept", b"application/json"),
                            (b"Set-Cookie", b"formalie_rt=zzz; Path=/api/v1/auth; HttpOnly")])
    assert headers["authorization"] == "Basic ***" and headers["x-csrf-token"] == "***"
    assert headers["x-formalie-envelope"] == "<envelope 150 chars>" and headers["accept"] == "application/json"
    assert headers["set-cookie"] == "formalie_rt=***; Path=/api/v1/auth; HttpOnly"


# ── Shipper ───────────────────────────────────────────────────────────────────

async def test_shipper_falls_back_to_file_when_the_sink_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(service, "fallback_dir", lambda: tmp_path)

    async def broken(records):  # noqa: ANN001, ANN202
        raise ConnectionError("database down")

    monkeypatch.setattr(service, "write_batch_async", broken)
    shipper = RequestLogShipper("database")
    await shipper.ship([{"id": "1", "path": "/a"}, {"id": "2", "path": "/b"}])
    lines = next(tmp_path.glob("*.jsonl")).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["1", "2"] and shipper.fallback == 2


async def test_shipper_batches_in_the_background(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    written: list[list[dict]] = []

    async def capture(records):  # noqa: ANN001, ANN202
        written.append(records)
        return len(records)

    monkeypatch.setattr(service, "write_batch_async", capture)
    shipper = RequestLogShipper("database")
    shipper.flush_seconds = 0.05
    for i in range(5):
        shipper.submit({"id": str(i)})
    await asyncio.sleep(0.2)
    assert sum(len(b) for b in written) == 5 and shipper.written == 5
    shipper._task.cancel()  # noqa: SLF001

"""A small load test for Formalie's API (B17). Development only: it refuses any host that is not a development host
unless `--i-know-this-is-production` is passed, and it must never be pointed at production without the owner.

Only libraries already in requirements.txt: httpx (HTTP), cryptography (through app/core/security/envelope.py, the
same envelope code the API uses), and the standard library.

Scenarios
    form      the public form page's data: handshake once per worker, then sealed GET /public/forms/{key}
    submit    the whole public submit: form data, CSRF, challenge, proof of work, the 3 s fill wait, sealed submit
              (each step is timed on its own). Answers are made up from the form's questions, or read from --answers.
    gateway   the API service: GET https://api.../{apiKey}/{endpoint} with a bearer token (plain JSON, no envelope)
    portal    signed-in list calls (sealed GETs with an access token copied from a signed-in browser, 15 minutes)

Examples (dev backend on https://formalie.dev:5004, the frontend's proxy host passed as X-Forwarded-Host)
    fmly\\Scripts\\python.exe scripts\\loadtest.py form --host jjumax.formalie.dev:2202 --form-key feedback -c 10 -d 20
    fmly\\Scripts\\python.exe scripts\\loadtest.py submit --host jjumax.formalie.dev:2202 --form-key feedback -c 10 -d 20
    fmly\\Scripts\\python.exe scripts\\loadtest.py gateway --api-key KEY --endpoint contacts --token TOKEN -c 20 -d 20
    fmly\\Scripts\\python.exe scripts\\loadtest.py portal --host jjumax.formalie.dev:2202 --bearer TOKEN \\
        --path /forms --path /responses --path /audit-logs -c 10 -d 20

Rate limits: the API limits every route per client address (public form 120 per minute, submit 60). From one
machine a run measures the limiter, not the server. `--spread-ips` sends each worker's calls with its own
X-Forwarded-For address from the benchmarking range 198.18.0.0/15 (RFC 2544); the API only believes it when this
machine is one of its trusted proxies (TRUSTED_PROXIES, 127.0.0.1 in development).

Output: per step, calls, calls per second, p50 / p95 / p99 / max latency, and errors by HTTP status and FRM code.
`--json FILE` also writes the numbers as JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import random
import secrets
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.core.security import envelope as env  # noqa: E402

API = "/api/v1"
DEV_SUFFIXES = (".dev", ".test", ".localhost", ".local")
DEV_HOSTS = {"localhost", "127.0.0.1", "::1"}
BENCH_NET = ipaddress.ip_network("198.18.0.0/15")


# ── Guard: development hosts only ───────────────────────────────────────────────

def bare_host(value: str) -> str:
    value = value.strip().lower()
    if "://" in value:
        value = urlsplit(value).hostname or ""
    if value.startswith("["):
        return value[1:value.find("]")]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def is_dev_host(host: str) -> bool:
    host = bare_host(host)
    if host in DEV_HOSTS or host.endswith(DEV_SUFFIXES) or host in {s.lstrip(".") for s in DEV_SUFFIXES}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private


def guard(args: argparse.Namespace) -> None:
    hosts = [args.base_url] + [h for h in (args.host, args.api_host) if h]
    foreign = [h for h in hosts if not is_dev_host(h)]
    if not foreign:
        return
    if not args.i_know_this_is_production:
        sys.exit(f"Refused: {', '.join(foreign)} is not a development host. Load tests run against development only; "
                 "production needs the owner and --i-know-this-is-production.")
    print(f"WARNING: running against {', '.join(foreign)} (not a development host). Ctrl+C within 10 s to stop.",
          file=sys.stderr)
    time.sleep(10)


# ── Numbers ─────────────────────────────────────────────────────────────────────

@dataclass
class Step:
    latencies: list[float] = field(default_factory=list)
    errors: Counter[str] = field(default_factory=Counter)
    ok: int = 0

    def add(self, seconds: float, problem: str | None) -> None:
        self.latencies.append(seconds)
        if problem:
            self.errors[problem] += 1
        else:
            self.ok += 1


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def summary(steps: dict[str, Step], elapsed: float) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, step in steps.items():
        values = sorted(step.latencies)
        out[name] = {
            "calls": len(values), "ok": step.ok, "errors": dict(step.errors.most_common()),
            "per_second": round(len(values) / elapsed, 1) if elapsed else 0.0,
            "p50_ms": round(percentile(values, 50) * 1000, 1), "p95_ms": round(percentile(values, 95) * 1000, 1),
            "p99_ms": round(percentile(values, 99) * 1000, 1), "max_ms": round((values[-1] if values else 0) * 1000, 1),
        }
    return out


def print_summary(scenario: str, args: argparse.Namespace, elapsed: float, table: dict[str, Any]) -> None:
    print(f"\nscenario={scenario} concurrency={args.concurrency} duration={elapsed:.1f}s spread_ips={args.spread_ips}")
    print(f"{'step':<22}{'calls':>7}{'ok':>7}{'/s':>8}{'p50 ms':>9}{'p95 ms':>9}{'p99 ms':>9}{'max ms':>9}  errors")
    for name, row in table.items():
        errors = ", ".join(f"{k} x{v}" for k, v in row["errors"].items()) or "-"
        print(f"{name:<22}{row['calls']:>7}{row['ok']:>7}{row['per_second']:>8}{row['p50_ms']:>9}{row['p95_ms']:>9}"
              f"{row['p99_ms']:>9}{row['max_ms']:>9}  {errors}")


# ── The portal channel (envelope, CSRF), as tests/secure_client.py and the frontend's client.ts ──

class Channel:
    def __init__(self, http: httpx.AsyncClient, headers: dict[str, str], steps: dict[str, Step]) -> None:
        self.http, self.headers, self.steps = http, headers, steps
        self.kid: str | None = None
        self.key: bytes | None = None
        self.csrf: str | None = None
        self.bearer: str | None = None

    async def handshake(self) -> None:
        private = env.generate_key_pair()
        started = time.perf_counter()
        problem = None
        try:
            reply = await self.http.post(f"{API}/crypto/handshake", headers=self.headers,
                                         json={"client_public_key": env.raw_public_key(private),
                                               "client_ts": int(time.time() * 1000)})
            if reply.status_code != 200:
                problem = f"{reply.status_code} {code_of(reply.json())}"
            else:
                data = reply.json()["data"]
                self.kid = data["key_id"]
                self.key = env.derive_session_key(private, data["server_public_key"], data["salt"])
                self.csrf = None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            problem = type(exc).__name__
        self.steps["handshake"].add(time.perf_counter() - started, problem)
        if problem:
            raise RuntimeError(problem)

    async def call(self, step: str, method: str, path: str, *, query: dict[str, Any] | None = None, body: Any = None,
                   headers: dict[str, str] | None = None, retried: bool = False) -> tuple[int, Any]:
        if self.key is None:
            await self.handshake()
        h = {**self.headers, **(headers or {})}
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if self.csrf is None:
                status, reply = await self.call("csrf", "GET", "/auth/csrf")
                if status != 200:
                    return status, reply
                self.csrf = reply["data"]["csrf_token"]
            h["x-csrf-token"] = self.csrf
        if self.bearer:
            h["authorization"] = f"Bearer {self.bearer}"
        assert self.key is not None and self.kid is not None
        sealed = env.seal(self.key, self.kid, {"method": method, "path": f"{API}{path}", "query": query or {},
                                               "body": body})
        started = time.perf_counter()
        status, data, problem = 0, None, None
        try:
            if method in ("GET", "DELETE"):
                h[env.ENVELOPE_HEADER] = env.encode_header(sealed)
                reply = await self.http.request(method, f"{API}{path}", headers=h)
            else:
                h["content-type"] = env.ENVELOPE_CONTENT_TYPE
                reply = await self.http.request(method, f"{API}{path}", headers=h, content=json.dumps(sealed))
            status = reply.status_code
            raw = reply.json()
            data = env.open_envelope(self.key, raw) if env.is_envelope(raw) else raw
            if status >= 400:
                problem = f"{status} {code_of(data)}"
        except (httpx.HTTPError, ValueError, env.EnvelopeError) as exc:
            problem = type(exc).__name__
        self.steps[step].add(time.perf_counter() - started, problem)
        if code_of(data) in ("FRM-SEC-1004", "FRM-SEC-1006") and not retried:  # key or CSRF expired: once more
            self.key = None if code_of(data) == "FRM-SEC-1004" else self.key
            self.csrf = None
            return await self.call(step, method, path, query=query, body=body, headers=headers, retried=True)
        return status, data


def code_of(data: Any) -> str:
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        return str(data["error"].get("code") or "")
    return ""


# ── Made-up answers for the submit scenario ─────────────────────────────────────

def made_up_answers(schema: dict[str, Any] | None) -> dict[str, Any]:
    """Plausible answers for common question types (fictional, neutral); anything else is left out."""
    answers: dict[str, Any] = {}
    n = secrets.randbelow(10**6)

    def fields(node: Any) -> list[dict[str, Any]]:  # pages → rows → fields (and any nesting), in form order
        if isinstance(node, dict):
            own = [node] if isinstance(node.get("type"), str) and isinstance(node.get("key"), str) else []
            return own + [f for value in node.values() for f in fields(value)]
        return [f for value in node for f in fields(value)] if isinstance(node, list) else []

    for fld in fields((schema or {}).get("pages") or []):
        kind, key = fld.get("type"), fld.get("key")
        options = [o.get("value") for o in fld.get("options") or [] if isinstance(o, dict)]
        if not key:
            continue
        if kind == "email":
            answers[key] = f"loadtest+{n}@example.test"
        elif kind in ("short_text", "text"):
            answers[key] = f"Load test {n}"
        elif kind == "long_text":
            answers[key] = "Load test answer. " * 3
        elif kind == "full_name":
            answers[key] = {"first": "Load", "last": f"Test {n}"}
        elif kind == "phone":
            answers[key] = f"+447700900{n % 1000:03d}"
        elif kind in ("number", "currency", "percentage", "slider"):
            answers[key] = n % 100
        elif kind in ("rating", "scale"):
            answers[key] = 1 + n % 5
        elif kind == "nps":
            answers[key] = n % 11
        elif kind in ("radio", "dropdown") and options:
            answers[key] = random.choice(options)
        elif kind in ("checkbox", "multi_select") and options:
            answers[key] = [random.choice(options)]
        elif kind == "toggle":
            answers[key] = True
        elif kind == "date":
            answers[key] = "2026-01-15"
    return answers


def solve(salt: str, difficulty: int) -> int:
    nonce = 0
    full, rest = divmod(difficulty, 8)
    while True:
        digest = hashlib.sha256(f"{salt}:{nonce}".encode()).digest()
        if digest[:full] == b"\0" * full and (rest == 0 or digest[full] >> (8 - rest) == 0):
            return nonce
        nonce += 1


# ── Scenarios ───────────────────────────────────────────────────────────────────

def worker_headers(args: argparse.Namespace, worker: int, host: str | None) -> dict[str, str]:
    h = {"user-agent": "formalie-loadtest/1"}
    if host:
        h["x-forwarded-host"] = host
        h["x-forwarded-proto"] = "https"
    if args.spread_ips:
        h["x-forwarded-for"] = str(BENCH_NET[1 + (worker * 7919 + os.getpid()) % (BENCH_NET.num_addresses - 2)])
    return h


async def scenario_form(http: httpx.AsyncClient, args: argparse.Namespace, worker: int, steps: dict[str, Step],
                        until: float) -> None:
    channel = Channel(http, worker_headers(args, worker, args.host), steps)
    while time.perf_counter() < until:
        try:
            await channel.call("public form", "GET", f"/public/forms/{args.form_key}")
        except RuntimeError:
            await asyncio.sleep(0.5)


async def scenario_submit(http: httpx.AsyncClient, args: argparse.Namespace, worker: int, steps: dict[str, Step],
                          until: float) -> None:
    channel = Channel(http, worker_headers(args, worker, args.host), steps)
    fixed = json.loads(Path(args.answers).read_text(encoding="utf-8")) if args.answers else None
    while time.perf_counter() < until:
        try:
            status, view = await channel.call("public form", "GET", f"/public/forms/{args.form_key}")
            if status != 200:
                await asyncio.sleep(1)
                continue
            status, challenge = await channel.call("challenge", "POST", f"/public/forms/{args.form_key}/challenge",
                                                   body={})
            if status != 200:
                await asyncio.sleep(1)
                continue
            c = challenge["data"]
            started = time.perf_counter()
            nonce = await asyncio.to_thread(solve, c["salt"], int(c["difficulty"]))
            steps["proof of work (client)"].add(time.perf_counter() - started, None)
            await asyncio.sleep(max(0.0, c.get("min_wait_ms", 3000) / 1000 - (time.perf_counter() - started)) + 0.2)
            answers = fixed if fixed is not None else made_up_answers((view.get("data") or {}).get("schema"))
            await channel.call("submit", "POST", f"/public/forms/{args.form_key}/submit",
                               body={"data": answers, "channel": "link",
                                     "challenge": {"token": c["token"], "nonce": nonce}},
                               headers={"formalie-key": str(uuid.uuid4())})
        except RuntimeError:
            await asyncio.sleep(0.5)


async def scenario_gateway(http: httpx.AsyncClient, args: argparse.Namespace, worker: int, steps: dict[str, Step],
                           until: float) -> None:
    headers = worker_headers(args, worker, args.api_host)
    if args.token:
        headers["authorization"] = f"Bearer {args.token}"
    path = f"/{args.api_key}/{args.endpoint}" + (f"?per_page={args.per_page}" if args.per_page else "")
    while time.perf_counter() < until:
        started = time.perf_counter()
        problem = None
        try:
            reply = await http.get(path, headers=headers)
            if reply.status_code >= 400:
                try:
                    problem = f"{reply.status_code} {code_of(reply.json())}"
                except ValueError:
                    problem = str(reply.status_code)
        except httpx.HTTPError as exc:
            problem = type(exc).__name__
        steps["gateway GET"].add(time.perf_counter() - started, problem)


async def scenario_portal(http: httpx.AsyncClient, args: argparse.Namespace, worker: int, steps: dict[str, Step],
                          until: float) -> None:
    channel = Channel(http, worker_headers(args, worker, args.host), steps)
    channel.bearer = args.bearer
    paths = args.path or ["/forms", "/responses", "/audit-logs"]
    i = worker
    while time.perf_counter() < until:
        path = paths[i % len(paths)]
        i += 1
        try:
            await channel.call(f"GET {path}"[:22], "GET", path, query={"page": "1", "page_size": "25"})
        except RuntimeError:
            await asyncio.sleep(0.5)


SCENARIOS = {"form": scenario_form, "submit": scenario_submit, "gateway": scenario_gateway, "portal": scenario_portal}


def default_ca() -> str | bool:
    """mkcert's root CA when mkcert is installed (the dev certificates are made with it), else the system store."""
    try:
        root = subprocess.run(["mkcert", "-CAROOT"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return True
    pem = Path(root) / "rootCA.pem"
    return str(pem) if root and pem.exists() else True


async def run(args: argparse.Namespace) -> dict[str, Any]:
    steps: dict[str, Step] = defaultdict(Step)
    verify: str | bool = args.ca or default_ca()
    limits = httpx.Limits(max_connections=args.concurrency * 2, max_keepalive_connections=args.concurrency * 2)
    async with httpx.AsyncClient(base_url=args.base_url, verify=verify, timeout=args.timeout, limits=limits) as http:
        started = time.perf_counter()
        until = started + args.duration
        work = SCENARIOS[args.scenario]
        await asyncio.gather(*(work(http, args, w, steps, until) for w in range(args.concurrency)))
        elapsed = time.perf_counter() - started
    table = summary(steps, elapsed)
    print_summary(args.scenario, args, elapsed, table)
    return {"scenario": args.scenario, "concurrency": args.concurrency, "duration_s": round(elapsed, 1),
            "spread_ips": args.spread_ips, "steps": table}


def parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Formalie load test (development only).",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("scenario", choices=sorted(SCENARIOS))
    p.add_argument("--base-url", default="https://formalie.dev:5004", help="the backend (default the dev backend)")
    p.add_argument("-c", "--concurrency", type=int, default=10)
    p.add_argument("-d", "--duration", type=float, default=20.0, help="seconds")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--host", help="workspace or forms host sent as X-Forwarded-Host, e.g. jjumax.formalie.dev:2202")
    p.add_argument("--form-key", help="form: the public key or custom link")
    p.add_argument("--answers", help="submit: a JSON file of answers instead of made-up ones")
    p.add_argument("--api-host", default="api.formalie.dev", help="gateway: the API service host (X-Forwarded-Host)")
    p.add_argument("--api-key", help="gateway: the address key")
    p.add_argument("--endpoint", default="records", help="gateway: the endpoint name")
    p.add_argument("--token", help="gateway: a bearer token (static or short-lived)")
    p.add_argument("--per-page", type=int)
    p.add_argument("--bearer", help="portal: an access token from a signed-in browser")
    p.add_argument("--path", action="append", help="portal: a list path (repeat), default /forms /responses /audit-logs")
    p.add_argument("--spread-ips", action="store_true", help="one X-Forwarded-For address per worker (198.18.0.0/15)")
    p.add_argument("--ca", help="CA bundle to trust (default mkcert's root CA when found)")
    p.add_argument("--json", help="also write the numbers to this file")
    p.add_argument("--i-know-this-is-production", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    needs = {"form": ["form_key"], "submit": ["form_key"], "gateway": ["api_key"], "portal": ["bearer", "host"]}
    missing = [n for n in needs[args.scenario] if not getattr(args, n)]
    if missing:
        p.error(f"{args.scenario} needs --{', --'.join(m.replace('_', '-') for m in missing)}")
    if not 1 <= args.concurrency <= 500 or not 1 <= args.duration <= 3600:
        p.error("concurrency 1 to 500, duration 1 to 3600 s")
    return args


def main() -> None:
    args = parse()
    guard(args)
    result = asyncio.run(run(args))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

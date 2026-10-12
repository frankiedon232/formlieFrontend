# Load test (B17, 2026-10-12)

## Setup

**Tool.** `scripts/loadtest.py` uses only packages already in requirements.txt (httpx, plus cryptography through `app/core/security/envelope.py`).
- It speaks the portal protocol the way the frontend does: ECDH handshake, sealed requests, CSRF, opening sealed replies.
- For the submit scenario it also solves the proof-of-work challenge and waits out the 3-second minimum fill time.
- It refuses any host that is not a development host unless `--i-know-this-is-production` is given. It must never be pointed at production without the owner.

**Target.** The local development backend: `https://formalie.dev:5004`, one uvicorn process started by `dev-up.ps1`.
- Windows 11 machine. PostgreSQL, Redis and RabbitMQ run on the same machine.
- TLS uses the mkcert root CA, which the tool finds with `mkcert -CAROOT`.
- The workspace host was sent as `X-Forwarded-Host`, as the frontend's dev proxy does. This works because 127.0.0.1 is a trusted proxy in development.

**Data.**
- The development database has almost nothing in it.
- The only published form is `feedback`, in the owner's own workspace `jjumax`. It has one page with 9 questions and requires the respondent's email to be verified.
- No workspace has an API endpoint, so there was no published endpoint and token pair to call.
- Nothing was created for this test: no workspace, form, token or response.

**Client addresses.** Every route has a per-IP limit (public form 120 per minute, submit 60, challenge 60), so from one machine the limiter is what gets measured.
- `--spread-ips` gives each worker its own `X-Forwarded-For` address from the benchmarking range 198.18.0.0/15.
- The API believes it only from a trusted proxy. That is the case in development; it never is from the internet.

**Scope.** Each run lasted about 20 seconds, at concurrency 10 or 20.

## Results

Latencies are client-side and include TLS. "ok" means HTTP 2xx.

### 1. Public form data, one client address (rate limiter)

`loadtest.py form --host jjumax.formalie.dev:2202 --form-key feedback -c 10 -d 20`

| Step | Calls | ok | per s | p50 ms | p95 ms | p99 ms | max ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| handshake | 10 | 10 | 0.5 | 67.7 | 82.1 | 84.9 | 85.6 | |
| public form | 9380 | 0 | 468.6 | 19.6 | 30.9 | 52.0 | 235.3 | 429 FRM-GEN-1029 x9380 |

The bucket had already been used by a smoke run a moment earlier, so every call was refused. A refusal costs about 2 ms of server time: it is answered after the envelope is opened, and before any database work.

### 2. Public form data, 20 clients (one address each)

`loadtest.py form ... -c 20 -d 20 --spread-ips`

| Step | Calls | ok | per s | p50 ms | p95 ms | p99 ms | max ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| handshake | 20 | 20 | 1.0 | 140.6 | 161.2 | 163.0 | 163.4 | |
| public form | 1232 | 1232 | 60.8 | 312.7 | 472.6 | 591.0 | 655.8 | |

And with 10 clients (`-c 10 --spread-ips`; each address ran into its 120 per minute limit after about 15 s):

| Step | Calls | ok | per s | p50 ms | p95 ms | p99 ms | max ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| handshake | 10 | 10 | 0.5 | 211.9 | 230.6 | 239.6 | 241.9 | |
| public form | 1677 | 1200 | 83.7 | 131.1 | 180.7 | 222.7 | 238.9 | 429 FRM-GEN-1029 x477 |

### 3. Public submit, the whole flow, 10 clients

`loadtest.py submit ... -c 10 -d 20 --spread-ips`

Each iteration reads the form, gets a challenge (CSRF on first use), solves the proof of work, waits 3 s, then submits made-up answers.

| Step | Calls | ok | per s | p50 ms | p95 ms | p99 ms | max ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| handshake | 10 | 10 | 0.4 | 44.2 | 66.9 | 78.8 | 81.8 | |
| public form | 63 | 63 | 2.7 | 34.4 | 103.6 | 115.2 | 117.3 | |
| csrf | 10 | 10 | 0.4 | 35.4 | 38.0 | 38.3 | 38.4 | |
| challenge | 63 | 63 | 2.7 | 28.7 | 157.4 | 176.7 | 183.7 | |
| proof of work (client) | 63 | 63 | 2.7 | 12.4 | 57.3 | 107.7 | 121.8 | |
| submit | 63 | 0 | 2.7 | 30.0 | 87.8 | 94.7 | 95.1 | 403 FRM-RESP-1008 x63 |

**Every submit stopped at "verify your email first" (FRM-RESP-1008).** The form requires a verified email, and verifying needs a code from a mailbox.

- **What was measured:** the submit path up to and including the answer checks and the email check: handshake, envelope, CSRF, challenge reservation in Redis, validation of all nine answers.
- **What was not measured:**
  - the duplicate checks;
  - the per-form row lock;
  - the insert;
  - the outbox, destinations, webhooks and audit;
  - the after-commit emails.
- **Nothing was stored.** No response was written to the owner's form.

The first run, before the tool read questions inside `pages[].rows[]`, stopped earlier with FRM-RESP-1001 (required answers missing). That is fixed in the tool.

The 3 s minimum fill time limits each client to about one submit every 3.5 s, so this scenario measures latency, not throughput. More clients give more throughput.

### 4. API service gateway, 20 clients

`loadtest.py gateway --api-key nokey --endpoint anything -c 20 -d 20 --spread-ips`

| Step | Calls | ok | per s | p50 ms | p95 ms | p99 ms | max ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| gateway GET | 2241 | 0 | 110.9 | 181.2 | 223.7 | 242.1 | 259.7 | 500 FRM-GEN-5000 x2241 |

**These numbers are not valid.** Every call failed with an `ImportError` (`BLOCKED_STATUSES` missing from `app.core.middleware.tenant`). That comes from the other helper's work in progress on the gateway entry point (`app/gateway.py`, `app/modules/api_service/gateway.py`, uncommitted at the time). It was still failing at the end of this review.

Once that work is in, re-run the scenario against a real endpoint:

```
fmly\Scripts\python.exe scripts\loadtest.py gateway --api-key <the workspace's address key> --endpoint <name> \
    --token <a test or live static token> -c 20 -d 20 --spread-ips
```

That needs a published endpoint and a token, which the owner can create in a test workspace. Note the token here once it exists.

### 5. Signed-in lists (not run)

The `portal` scenario is ready:

```
loadtest.py portal --host jjumax.formalie.dev:2202 --bearer <access token> --path /forms --path /responses --path /audit-logs
```

It needs an access token from a signed-in browser. That means signing in with a code from the mailbox, which the owner does. It was not run.

With an almost empty database it would only show the framework cost anyway. The query review (Q1, Q6) shows the lists will be the first thing to slow down with real data.

## What the numbers say

1. **About 13 to 16 ms of server work per public form read, on one process.** At 20 clients the single dev process served 61 reads per second at a p50 of 313 ms. That is 20 / 61 ≈ 330 ms in the system per call, almost all of it queueing.
   - Each read does:
     - envelope open and seal (AES-GCM, base64, JSON);
     - Redis for the nonce and the key;
     - host and workspace resolution;
     - three or four small queries (form, published version, lists, theme);
     - a deep copy of the schema;
     - the request log.
   - The development process has one worker (and reload); production plans `--workers 4` per app server. The same code should give roughly 4 × 60 to 80 reads per second per app server before database limits. That is enough for launch.
   - The first hot form will want a cache of the public view per (form, published version, language) in Redis.
2. **The handshake is the slowest single call (45 to 210 ms):** an ECDH P-256 key pair and derivation, plus a Redis write. It happens once per visitor per 30 minutes, so it is fine. Under load it competes for the same CPU, as the 140 to 210 ms values with 10 to 20 busy clients show.
3. **The challenge and submit steps had p95 values of 80 to 160 ms,** with almost no data. The part of submit that was not reached grows with the form's responses:
   - the identity email check reads every earlier response of the form (query review Q2);
   - every submit to one form waits for one row lock (Q4).
   
   Measure those before launch with a seeded form of 100k responses in the test database.
4. **The per-IP limits work and cost little** (about 2 ms per refusal). They also mean a load test from one address measures nothing else, hence `--spread-ips`.
5. **Proof of work on the client** (difficulty 14) took 12 ms at p50 and up to 120 ms in Python. That is in line with what a phone's browser will spend. It adds no server cost.

## Bottlenecks to fix or re-test

- **The single process.** Run the next load test with `--workers 4` (as production does) to see where the database or Redis becomes the limit.
- **Response lists, the inbox and insights are built in memory** (query review Q1). Re-test the `portal` scenario after seeding 100k to 1M responses.
- **Submit to a form that asks for an email:** the full-table read (Q2) and the per-form lock (Q4). Re-test with a form without verification, in a test workspace the owner sets aside, so responses can be written.
- **Gateway GET** loads the whole form (Q3). Re-test with a real endpoint and token.
- **Request bodies are buffered whole before any limit** (security review M12). A large-body test should be part of the next round, once that is fixed.

## Running it again

```
fmly\Scripts\python.exe scripts\loadtest.py --help
fmly\Scripts\python.exe scripts\loadtest.py form   --host <sub>.formalie.dev:2202 --form-key <key> -c 20 -d 20 --spread-ips --json out.json
fmly\Scripts\python.exe scripts\loadtest.py submit --host <sub>.formalie.dev:2202 --form-key <key> -c 10 -d 20 --spread-ips
```

- `--answers file.json` sends fixed answers instead of made-up ones.
- `--json` writes the numbers to a file.
- The tool refuses non-development hosts. Production runs need the owner present and `--i-know-this-is-production`, and should target a dedicated test workspace and form.

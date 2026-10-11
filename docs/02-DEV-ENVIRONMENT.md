# 02, Local Development Environment

## Current setup (as done by Frankie)

| Item             | Value                                                                                                                               |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Frontend project | `formalieFrontend` (Nuxt 4.5.2, @nuxt/ui 4.11.1, tailwindcss 4.3.3, vue 3.5.43, vue-router 5.3.1), pnpm                             |
| Frontend URL     | `https://formalie.dev:2202/`                                                                                                        |
| Frontend run     | `pnpm dev --host 0.0.0.0 --port 2202 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formalie-key.pem`        |
| Backend project  | `formlyBackend`, Python 3.11.9, venv, `pip install fastapi[all]`                                                                    |
| Backend run      | `uvicorn app.run:app --host 0.0.0.0 --port 5004 --no-proxy-headers --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formalie-key.pem` (or `fmly\Scripts\python.exe -m app.run`). **`--no-proxy-headers` is required:** the app reads `X-Forwarded-*` itself, only from `TRUSTED_PROXIES`; uvicorn's own handling would hide the real proxy, and workspaces would no longer be found from `X-Forwarded-Host` |
| API docs         | `https://formalie.dev:5004/docs`, `https://formalie.dev:5004/redoc`                                                                 |
| Certificate      | mkcert: `formalie.dev *.formalie.dev localhost *.localhost 127.0.0.1 ::1 <LAN IP>` (see Access matrix)                              |

## Fixes before subdomain work (1–2 done 2026-10-02)

1. **Domain mismatch.** The hosts entries use `manage.medique.dev`, `remedylegal.medique.dev`, `samathtax.medique.dev`, but the portal runs on `formalie.dev`. Use `formalie.dev` subdomains so cookies, CORS and tenant detection all line up.
2. **Certificate does not cover subdomains.** The current cert is only for `formalie.dev`. Regenerate it with a wildcard:
   ```powershell
   mkcert -cert-file C:\devcerts\formalie.pem -key-file C:\devcerts\formalie-key.pem formalie.dev "*.formalie.dev" localhost 127.0.0.1
   ```
3. **Venv name.** It was created as `fmly` but activated as `fmly\scripts\activate.ps1`. Pick one name (suggest `fmly`) and use it consistently.

## Hosts file (`C:\Windows\System32\drivers\etc\hosts`)

Windows hosts does not support wildcards, so add one line per test subdomain:

```
127.0.0.1   formalie.dev
127.0.0.1   manage.formalie.dev
127.0.0.1   forms.formalie.dev
127.0.0.1   api.formalie.dev
127.0.0.1   remedylegal.formalie.dev
127.0.0.1   samathtax.formalie.dev
```

Add more lines as new test tenants are created.

## Dev URLs

- Default entry: `https://manage.formalie.dev:2202/`
- Public form links (from F10): `https://forms.formalie.dev:2202/{formKey}/fill` · `/embed`, or `https://{sub}.formalie.dev:2202/{formKey}/fill` (production drops the port; see 01-ARCHITECTURE → Public URLs)
- API service (from F13): `https://api.formalie.dev/{apiKey}/{endpoint}`, served by the backend API service; the wildcard certificate already covers `api.` and `forms.`
- Tenant workspaces: `https://remedylegal.formalie.dev:2202/`, `https://samathtax.formalie.dev:2202/`
- API (direct): `https://formalie.dev:5004/`, the browser should call `/api/...` on its own origin; Nuxt proxies it (below).

## Nuxt dev settings to add

- Allow the subdomains in Vite: `vite.server.allowedHosts: ['.formalie.dev']`.
- Proxy `/api` to the backend, preserving the original host so the backend can read the subdomain:
  `nitro.devProxy` / `routeRules: { '/api/**': { proxy: 'https://formalie.dev:5004/api/**' } }` with `X-Forwarded-Host` forwarded (implemented in Phase F0).
- Node must trust the mkcert root when proxying: set `NODE_EXTRA_CA_CERTS` to the mkcert `rootCA.pem` (find it with `mkcert -CAROOT`).

## Backend dev services (Phase B0)

Installed directly on the machine, **no Docker** (owner, 2026-10-10). Production runs on AWS or dedicated servers (decided per deployment); Docker only if a real need comes up.

| Service | Where (development) | Port | Notes |
| --- | --- | --- | --- |
| PostgreSQL **18** primary | Windows service `postgresql-x64-18` (already installed) | 5432 | Owner, 2026-10-10: develop on 18, write SQL that also runs on 16 (no PG 17/18-only features; UUIDv7 is made in the app) |
| PostgreSQL 18 replica | Windows, second cluster (streaming replication) | 5433 | Optional until reports and lists need it; `DB_REPLICA_URLS` empty = reads go to the primary |
| Redis 7 | WSL (Ubuntu) | 6379 | cache, rate limits, nonces, session keys |
| RabbitMQ 3 + management UI | WSL | 5672, 15672 | Celery broker and the `formalie.events` exchange |
| PgBouncer | WSL | 6432 | transaction pooling; then `DB_PGBOUNCER=true` |
| Object storage (S3) | chosen in B3 | | uploads and exports (from B3). MinIO's download server stopped serving its binary (410 Gone, 2026-10-11), so the server is picked when storage is built |
| Mailpit | WSL | 1025 (SMTP), 8025 (UI) | catches OTP and other emails (from B1) |

### 1. PostgreSQL: roles and databases (once)

1. Copy `.env.example` to `.env` and fill the four `DB_*_URL` lines: the `postgres` superuser password in `DB_SUPERUSER_URL`, and a password of your choice for `formalie_owner`, `formalie_app` and `formalie_worker` (the user names are fixed).
2. `fmly\Scripts\python.exe scripts\db_bootstrap.py` creates the roles and the `formalie` and `formalie_test` databases (safe to run again; it updates passwords).
3. `fmly\Scripts\alembic.exe upgrade head` and `fmly\Scripts\alembic.exe -x db=test upgrade head`.
4. `fmly\Scripts\python.exe -m pytest` now also runs `tests/db` (RLS, cross-tenant, outbox).

### 2. WSL services (when we reach them)

1. PowerShell as administrator: `wsl --install -d Ubuntu-24.04`, restart, create the Linux user.
2. Let Windows and WSL share `127.0.0.1`: create `%UserProfile%\.wslconfig` with
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   then `wsl --shutdown`. (Windows 11 22H2 or later. Without it, use the WSL address from `wsl hostname -I`.)
3. In Ubuntu: `bash /mnt/c/UNETPROJECTS/formlyBackend/scripts/wsl/setup-services.sh` installs and starts Redis, RabbitMQ (with a `formalie` vhost and user), PgBouncer and Mailpit as systemd services. It prints the values to put in `.env`.
4. Workers on Windows: Celery has no official Windows pool, so run them with `--pool=solo` (or `--pool=threads`):
   `fmly\Scripts\celery.exe -A app.workers.celery_app worker -Q scheduled --pool=solo -l info` and `fmly\Scripts\celery.exe -A app.workers.celery_app beat -l info`.

### After a restart (every day)

The setup script runs once only. Everything else is in the README's "Every day" section:
- `scripts\dev-up.ps1` starts the services, API, worker, Beat and Flower hidden, with no windows (`-NoApi`, `-NoApp`).
- `scripts\dev-logs.ps1` follows their logs live in one terminal (`api`, `worker`, `beat`, `flower`, `-Errors`).
- `scripts\dev-down.ps1` stops them.

### Dashboards (development)

| What | Address | Sign in |
| --- | --- | --- |
| RabbitMQ (queues, exchanges, messages) | http://127.0.0.1:15672 | user `formalie`, the password inside `RABBITMQ_URL` in `.env` (between `formalie:` and `@`) |
| Celery (workers, tasks, failures): Flower | http://127.0.0.1:5555 | none (bound to 127.0.0.1 only) |
| Emails caught in development: Mailpit | http://127.0.0.1:8025 | none |
| Redis (keys, memory): Redis Insight desktop app (redis.io/insight) | connect to `127.0.0.1:6379` | none |

Started by `scripts\dev-up.ps1` (hidden). By hand, each in its own terminal from the project folder:

```powershell
fmly\Scripts\celery.exe -A app.workers.celery_app worker -Q scheduled,logs,notifications --pool=solo -E -n worker1@%h -l info
fmly\Scripts\celery.exe -A app.workers.celery_app beat -s logs/celerybeat-schedule -l info
fmly\Scripts\celery.exe -A app.workers.celery_app flower --address=127.0.0.1 --port=5555
```

(`-E` sends task events, so Flower shows each task. Redis from Ubuntu without an app: `redis-cli --scan --pattern 'fm:v1:*'` lists Formalie's keys.)

### 3. Locations for the request log (MaxMind GeoLite2)

1. Create a free account at maxmind.com, then make a license key (GeoLite2).
2. Put `MAXMIND_ACCOUNT_ID` and `MAXMIND_LICENSE_KEY` in `.env`.
3. `fmly\Scripts\python.exe scripts\geoip_update.py` downloads City + ASN into `data/geoip/` (Celery Beat refreshes them weekly).

Without them requests are still logged; only the location fields stay empty. Local addresses (`127.0.0.1`, your LAN) never have a location.

### 4. Replica on Windows (optional, later)

As administrator, with the primary running: allow replication for `formalie_replicator` in `pg_hba.conf`, then
`"C:\Program Files\PostgreSQL\18\bin\pg_basebackup.exe" -h 127.0.0.1 -p 5432 -U formalie_replicator -D C:\pgdata\replica18 -R -X stream`,
set `port = 5433` in `C:\pgdata\replica18\postgresql.conf`, register it with `pg_ctl register -N postgresql-x64-18-replica -D C:\pgdata\replica18`, start it, and add `postgresql://formalie_app:…@127.0.0.1:5433/formalie` to `DB_REPLICA_URLS`.

## Access matrix (verified 2026-10-02)

Every way of opening the dev server must work. Host classification is one shared function, `resolveHostContext()` in `shared/utils/tenant/host.ts` (unit-tested), used by the tenant middleware, SSR and the mock API.

| How you open it                                                                | Served                               | Trusted TLS                                                                                                                                            | Resolves to                                             |
| ------------------------------------------------------------------------------ | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| `https://manage.formalie.dev:2202`                                             | ✅                                   | ✅                                                                                                                                                     | manage (default entry)                                  |
| `https://formalie.dev:2202`                                                    | ✅                                   | ✅                                                                                                                                                     | manage (root)                                           |
| `https://{sub}.formalie.dev:2202` (needs hosts line)                           | ✅                                   | ✅                                                                                                                                                     | tenant `{sub}`                                          |
| `https://localhost:2202` / `https://127.0.0.1:2202`                            | ✅                                   | ✅                                                                                                                                                     | manage (local); `?tenant={sub}` in dev opens a tenant   |
| `https://{sub}.localhost:2202` (no hosts line, Chrome/Edge/Firefox resolve it) | ✅                                   | ⚠ wildcards over single-label `localhost` are rejected by Windows/Chrome, add explicit names (`acme.localhost`) to mkcert, or use `{sub}.formalie.dev` | tenant `{sub}`                                          |
| `https://192.168.x.x:2202` (phone on Wi-Fi)                                    | ✅                                   | ✅ (cert includes 192.168.0.180; phone needs the mkcert root CA)                                                                                       | manage; `?tenant={sub}` in dev                          |
| `https://[::1]:2202`                                                           | ❌ with `--host 0.0.0.0` (IPv4 only) | ✅                                                                                                                                                     | manage, start with `--host ::` to listen on IPv4 + IPv6 |

Current cert (regenerated 2026-10-02) covers all of the above; regenerate when your LAN IP changes:

```powershell
mkcert -cert-file C:\devcerts\formalie.pem -key-file C:\devcerts\formalie-key.pem formalie.dev "*.formalie.dev" localhost "*.localhost" 127.0.0.1 ::1 192.168.0.180
```

Phones need the mkcert root CA installed to trust it (`mkcert -CAROOT` → `rootCA.pem`). The language cookie is per host, so a language chosen on `localhost` is not carried to `manage.formalie.dev` (F3: the manage → tenant redirect passes the locale along).

## Test accounts (mock API)

Seeded in `server/mock/data/tenants.ts` (mock only, in memory): workspaces **remedylegal** and **samathtax** (active), **oldco** (suspended). Accounts and password: see README → Test accounts. The code screen shows the mock's code in dev; it is also logged in the dev-server console (`[mock-otp]`). On localhost / an IP use `?tenant=remedylegal` (dev only).

## Data sources in the mock (F12)

Seeded workspaces have five connections in every state (connected read + write, connected read only, needs attention, failing, disabled). Nothing connects to a real database: a test's outcome comes from what you type, so every path can be tried.

| To see                                                            | Type                                             |
| ----------------------------------------------------------------- | ------------------------------------------------ |
| Can't reach the server (`FRM-DEST-1001`) / time-out (`1011`)      | a host containing `unreachable` / `timeout`      |
| SSH tunnel fails (`1004`)                                         | an SSH server containing `unreachable`           |
| Certificate problem (`1003`)                                      | a host containing `badcert` (with encryption on) |
| Sign-in refused (`1002`)                                          | password or client secret `wrong`                |
| Database not found (`1005`)                                       | a database / service name containing `missing`   |
| Can't create Formalie's tables (`1012`, the test fails: required) | a user name containing `nocreate`                |
| Missing write on your other tables (needs attention)              | a user name containing `readonly`                |
| Missing row counts (needs attention)                              | a user name containing `limited`                 |

`localhost`, `127.*`, `169.254.*` and similar are refused as server addresses (by design).

Response storage (M2): seeded workspaces have two forms storing in a database (a table Formalie created on Case management, all delivered; the `leads` table on Website leads, failing like its connection). Each connection shows a believable set of tables by its purpose plus the response tables. Delivery status is worked out per response when read (sent a few seconds after submitting; failed while the connection fails; held while paused), so new submissions show up as pending, then sent.

## API service from Postman (F13, mock)

With `NUXT_PUBLIC_API_MOCK=true` the mock answers real calls to your endpoints (`server/mock/publicApi.ts`), so you can try them before the backend exists.

1. Address: `https://api.formalie.dev:2202/{apiKey}/{endpoint}` (needs the hosts line `127.0.0.1 api.formalie.dev`) or `https://localhost:2202/public-api/{apiKey}/{endpoint}`. The endpoint panel shows the full address; the key is in Tokens & headers → Headers.
2. A token: Tokens & headers → New token (Live stores real responses in the mock, Test checks everything but stores nothing). Copy it when it is shown; it is not shown again.
3. Postman: Authorization → Bearer Token, or a header `Authorization: Bearer formalie_live_…`. For POST / PUT: Body → raw → JSON with the question keys from the endpoint's Example call. Add the endpoint's required headers, if any.
4. Postman checks certificates: turn off "SSL certificate verification" (Settings → General) or add the mkcert root CA (`mkcert -CAROOT` → `rootCA.pem`) under Settings → Certificates.
5. Client id + secret: `POST …/{apiKey}/token` with `{ "client_id": "…", "client_secret": "…" }`, then use the `access_token` as the bearer.

6. Access rules and rate limits apply in the mock too (anonymous networks: `X-Debug-Network: vpn`, `proxy`, `tor` or `hosting`). To try them from Postman, these mock-only headers stand in for what the real service reads from the connection: `X-Forwarded-For: 203.0.113.10` (the caller's IP) and `X-Debug-Country: GB` (the caller's country). `Origin: https://shop.example.com` acts as a browser caller for domain rules. A refused call answers 403 `FRM-API-1015`; over a rate limit 429 with `Retry-After`.

7. Files: first `POST …/{endpoint}/files?field={question key}` with Body → form-data, key `file` (type File). The answer has an `id`; send it in the JSON under that question, e.g. `"cv_resume": ["<id>"]`. The question must be accepted by the endpoint.
8. API Documentation has every call ready as code and a Download OpenAPI button (Postman: Import → the file).

9. Management API: API service → API keys → New API key, then `GET https://localhost:2202/public-api/v1/forms` with `Authorization: Bearer formalie_key_…` (see API-CONTRACT → Management API).
10. Webhooks: a receiver on your machine works while developing (`http://localhost:{port}/…`); any small server that logs the request and answers 200 will do. Send a test from the webhook's panel, then check the signature with the code under Checking the signature.

A response sent with a live token shows up under the form's Responses (channel API). The mock keeps tokens and responses in `.data/mock`.

## Project env (`.env`, copy from `.env.example`)

| Variable                           | Purpose                                                                                   |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| `NUXT_PUBLIC_API_MOCK`             | `true` = in-repo mock API, `false` = proxy to FastAPI. Restart dev after changing.        |
| `NUXT_API_PROXY_TARGET`            | Backend for the dev proxy (default `https://formalie.dev:5004`).                          |
| `DEV_HTTPS_CERT` / `DEV_HTTPS_KEY` | Optional: mkcert files so plain `pnpm dev` serves HTTPS on :2202.                         |
| `NODE_EXTRA_CA_CERTS`              | mkcert `rootCA.pem` (`mkcert -CAROOT`), needed when the proxy talks HTTPS to the backend. |

Quality checks: `pnpm typecheck` · `pnpm lint` · `pnpm format` · `pnpm test`. `typecheck`/`build` regenerate `.nuxt` (restart a running dev server afterwards); `pnpm typecheck:dev` reuses it and is safe while dev runs.

## Production equivalent

Cloudflare wildcard DNS `*.formalie.com` → Nginx → Nuxt + FastAPI. Same subdomain logic as dev.

## Server-only secrets (F10)

- `NUXT_INTERNAL_TOKEN`, shared between the Nuxt server and the API for the server-rendered public form pages (`/_ssr/public-forms/{key}` → API `/internal/public-forms/{key}`). Development makes a random one per start; production must set the same value on both sides. Never exposed to browsers.

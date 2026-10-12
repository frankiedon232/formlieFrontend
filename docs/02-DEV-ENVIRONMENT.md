# 02, Local Development Environment

Same machine and tools as Formalie (Windows, PowerShell, mkcert, pnpm, Python 3.11.9). **No Docker** (owner, 2026-10-10): services are installed directly on the machine, the same ones Formalie uses. The platform runs next to Formalie on its own ports and hosts.

## Projects

| Item | Value |
| --- | --- |
| Front end project | `formaliePlatformFront` (Nuxt 4.5, @nuxt/ui 4, tailwindcss 4, vue 3.5, TypeScript 6), pnpm |
| Front end URL | `https://platformadm.formalie.dev:2203/` |
| Front end run | `pnpm dev --host 0.0.0.0 --port 2203 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formalie-key.pem` |
| Backend project | `formaliePlatformBack`, Python 3.11.9, venv `padm`, `pip install -r requirements.txt` |
| Backend run | `uvicorn app.run:app --host 0.0.0.0 --port 5601 --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formalie-key.pem` |
| API URL | `https://platformapi.formalie.dev:5601/` |
| API docs (dev only) | `https://platformapi.formalie.dev:5601/docs`, `/redoc` (switched off in production) |
| Formalie API (internal admin) | `https://formalie.dev:5004/internal/admin/v1/` |

## Certificate (mkcert)

The existing Formalie certificate already covers `*.formalie.dev`, so `platformadm.formalie.dev` and `platformapi.formalie.dev` are trusted. If you regenerate it, keep both names in:

```powershell
mkcert -cert-file C:\devcerts\formalie.pem -key-file C:\devcerts\formalie-key.pem formalie.dev "*.formalie.dev" platformadm.formalie.dev platformapi.formalie.dev localhost "*.localhost" 127.0.0.1 ::1 <LAN IP>
```

Node must trust the mkcert root when the Nuxt dev proxy calls the API: set `NODE_EXTRA_CA_CERTS` to `rootCA.pem` (`mkcert -CAROOT`). Python must trust it for calls to Formalie's internal API: set `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` to the same file (or point httpx at it).

Production always uses a valid certificate (never mkcert).

## Hosts file (`C:\Windows\System32\drivers\etc\hosts`)

```
127.0.0.1   platformadm.formalie.dev
127.0.0.1   platformapi.formalie.dev
```

(Formalie's own lines stay as they are.)

## Local services (installed, shared with Formalie in development)

In development the platform uses the services already installed for Formalie, each kept apart by its own database, vhost, index or bucket. In production every one of them is the platform's own (docs/04-HOSTING.md).

| Service | Install on Windows | The platform uses |
| --- | --- | --- |
| PostgreSQL 16 | the EDB installer (same server as Formalie) | its own database `formalie_platform` and login `platform`; Formalie's database through `platform_reader` / `platform_writer` (created by Formalie's migrations, FORMALIE-INTEGRATION.md) |
| PgBouncer | optional in development (the API connects to PostgreSQL directly); always in production | |
| Redis 7 | Memurai (Redis-compatible Windows service) or Redis in WSL, same as Formalie | its own database index `2` (Formalie keeps its own) |
| RabbitMQ 3 (+ Erlang) | the Windows installer, management plugin on (UI on 15672) | its own vhost `platform` (Celery) and a read-only user `platform_events` on Formalie's vhost (events) |
| S3-compatible storage | MinIO for Windows (`minio.exe server`), same as Formalie | its own bucket `platform-dev` |
| Mail catcher | Mailpit for Windows (`mailpit.exe`), same as Formalie | staff invitations and two-step codes in development |

Ports are whatever those services already use on the machine (PostgreSQL 5432, Redis 6379, RabbitMQ 5672, MinIO 9000 / 9001, Mailpit 8025 / 1025 by default); only the platform's own front end (2203) and API (5601) are new.

## Front end settings

- `vite.server.allowedHosts: ['platformadm.formalie.dev']`.
- Dev proxy `/api/**` → `https://platformapi.formalie.dev:5601/api/**`, forwarding the host.
- `routeRules: { '/**': { ssr: false } }`: the platform admin is a client-rendered app, never server-rendered, never indexed (`robots: noindex, nofollow`, `X-Robots-Tag`).
- Mock layer (`server/mock/**`, `NUXT_PUBLIC_API_MOCK=true`) exactly like Formalie, returning the shapes in API-CONTRACT.md, so the front end can be built before the backend.

## Front end env (`.env`, copy from `.env.example`)

| Variable | Purpose |
| --- | --- |
| `NUXT_PUBLIC_API_MOCK` | `true` = in-repo mock, `false` = proxy to the platform API |
| `NUXT_API_PROXY_TARGET` | default `https://platformapi.formalie.dev:5601` |
| `NUXT_PUBLIC_FORMALIE_PORTAL_URL` | `https://manage.formalie.dev:2202` (links "open in Formalie") |
| `DEV_HTTPS_CERT` / `DEV_HTTPS_KEY` | mkcert files |
| `NODE_EXTRA_CA_CERTS` | mkcert `rootCA.pem` |

## Backend env (`.env`, copy from `.env.example`)

| Variable | Purpose |
| --- | --- |
| `PLATFORM_ENV` | `development` · `staging` · `production` |
| `PLATFORM_DATABASE_URL` | `postgresql+asyncpg://platform:…@localhost:5432/formalie_platform` (PgBouncer's port in production) |
| `PLATFORM_DATABASE_REPLICA_URL` | read replica (same as primary in development) |
| `PLATFORM_REDIS_URL` | `redis://localhost:6379/2` |
| `PLATFORM_BROKER_URL` | `amqp://platform:…@localhost:5672/platform` (Celery) |
| `FORMALIE_EVENTS_URL` | `amqp://platform_events:…@localhost:5672/formalie` (read-only consumer) |
| `FORMALIE_READER_URL` | `postgresql+asyncpg://platform_reader:…@localhost:<formalie port>/formalie` |
| `FORMALIE_WRITER_URL` | `postgresql+asyncpg://platform_writer:…@localhost:<formalie port>/formalie` (global tables only) |
| `FORMALIE_ADMIN_API_URL` | `https://formalie.dev:5004/internal/admin/v1` |
| `FORMALIE_ADMIN_API_KEY_ID` / `FORMALIE_ADMIN_API_SECRET` | HMAC signing of internal admin calls |
| `FORMALIE_ADMIN_API_CLIENT_CERT` / `_KEY` | mTLS client certificate (production; optional in development) |
| `FERNET_KEYS` | platform token keys (MultiFernet, never Formalie's keys) |
| `ID_REF_KEY` | encrypted id references (platform's own key) |
| `S3_*` | MinIO in development, S3 or S3-compatible storage in production |
| `SMTP_*` | Mailpit in development |
| `GEOIP_DB_PATH` | local GeoLite-style database file for country / city from IP (no external call) |
| `ALLOWED_STAFF_IPS` | optional allowlist (comma list, CIDR) |

Never commit `.env`; `.env.example` lists every key with placeholders.

## First run

1. Services: create the database and login (`createdb formalie_platform`, login `platform`), the RabbitMQ vhost `platform` and the user `platform_events` (read-only on Formalie's vhost), and the MinIO bucket `platform-dev`.
2. Backend: `python -m venv padm`, `padm\Scripts\activate`, `pip install -r requirements.txt`, `alembic upgrade head`, `python -m app.cli seed-owner` (creates the first platform owner; prints a one-time activation link to the console, no password ever printed), run uvicorn.
3. Front end: `pnpm install`, `pnpm dev …` as above, open `https://platformadm.formalie.dev:2203`.
4. Formalie: its backend must have the internal admin API and the two database roles (FORMALIE-INTEGRATION.md). Until then the platform runs on its mock and on the replica alone.

## Quality checks

Front end: `pnpm typecheck` · `pnpm lint` · `pnpm format` · `pnpm test`. Backend: `ruff check` · `ruff format --check` · `mypy app` · `pytest`. All green before every commit.

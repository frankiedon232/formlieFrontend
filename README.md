# Formalie API (formlyBackend)

The backend of Formalie. It replaces the mock API the finished frontend (`C:\UNETPROJECTS\formalieFrontend`) runs against today. Python 3.11, FastAPI, PostgreSQL 18, Redis, RabbitMQ, Celery.

- **Where the work stands:** [docs/PROGRESS.md](docs/PROGRESS.md) (phase by phase), [docs/BACKEND-ROADMAP.md](docs/BACKEND-ROADMAP.md), [docs/ENDPOINTS.md](docs/ENDPOINTS.md) (every endpoint, ticked when done).
- **Rules and design:** [CLAUDE.md](CLAUDE.md) and everything in [docs/](docs/).

---

## Every day: start, watch, stop

Everything runs **quietly in the background, no windows open**. From `C:\UNETPROJECTS\formlyBackend`, in PowerShell:

### Start: `scripts\dev-up.ps1`

| Command | Starts |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1` | **Everything:** the services, the API (https://formalie.dev:5004), the Celery worker, Celery Beat and Flower |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApi` | Everything **except the API**, when you prefer to run the API yourself in your terminal (see below) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApp` | **Services only** (Ubuntu with Redis, RabbitMQ, PgBouncer and Mailpit; PostgreSQL), no API and no workers |

What it does:
1. **Wakes Ubuntu (WSL)** and keeps it running in the background. Redis, RabbitMQ, PgBouncer and Mailpit start with Ubuntu; PostgreSQL starts with Windows.
2. **Checks every service answers.** If one doesn't, it says which and how to fix it.
3. **Starts the API, worker, Beat and Flower hidden**, writing their output to `logs\dev\{api,worker,beat,flower}.log`.

It's **safe to run again**: anything already running is left as it is. If port 5004 is already taken (an API you started yourself), it leaves it alone and says so.

### Watch the logs live: `scripts\dev-logs.ps1`

It runs in the terminal you start it from, with no other windows. Each line starts with where it came from (`api`, `worker`, `beat`, `flower`). It shows the last 20 lines first, then new lines as they happen. **Ctrl+C** stops watching; the services keep running.

| Command | Shows |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1` | **All:** API, worker, Beat and Flower together |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api` | Only the API (every request, one line each) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 worker` | Only the Celery worker (emails, request-log writes, events) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api worker` | Any mix of `api`, `worker`, `beat`, `flower` |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 -Errors` | Only problems (ERROR, CRITICAL, tracebacks) from all of them |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api -Errors` | Only the API's problems |

### Stop: `scripts\dev-down.ps1`

| Command | Stops |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1` | The API (if dev-up started it), the worker, Beat, Flower, and the keep-alive. Ubuntu then stops on its own. **Data is never touched.** An API you started yourself is left alone (Ctrl+C it). |

### Running the API yourself instead

Use `dev-up.ps1 -NoApi`, then in your own terminal:

```powershell
uvicorn app.run:app --host 0.0.0.0 --port 5004 --no-proxy-headers --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formalie-key.pem
```

or `fmly\Scripts\python.exe -m app.run`, which does the same with the host, port and certificates from `.env`. **`--no-proxy-headers` is required.** The API reads the forwarded headers itself, and only from trusted proxies; without the flag, workspaces are not found from their subdomain behind the Nuxt dev proxy.

### Every log there is

| Where | What |
| --- | --- |
| `scripts\dev-logs.ps1`, or `logs\dev\*.log` | The live output of the API, worker, Beat and Flower: one readable line per entry, with details after the message (`{name}.err.log` holds Python warnings and crashes) |
| `logs\{level}\{date}.log`, for example `logs\error\2026-10-11.log` | Everything, as JSON lines, per level and day, kept 90 days; also when you run the API yourself |
| The `formaly.request_logs` table | Every request in full: headers, body, response, real IP, location, device |
| The `formaly.audit_logs` table | Who did what: sign-ins (failed ones too), changes; in the app under Audit trail |
| The `formaly.error_logs` table | Every warning, error and critical line of every process, loaded from the files above every 30 seconds by Beat (search by `trace_id`). Critical ones are also emailed to `ALERT_EMAILS` |
| Flower, http://127.0.0.1:5555 | Every background task: what ran, how long it took, what failed |
| Mailpit, http://127.0.0.1:8025 | Every email the backend sent (sign-in codes and others) |

The console format is set with `LOG_CONSOLE_FORMAT` in `.env`: empty or `pretty` for readable lines, `json` for raw JSON.

If a service is down, `dev-up` says which one. To fix it:
- Redis, RabbitMQ, PgBouncer or Mailpit: in an Ubuntu window, `sudo systemctl restart redis-server rabbitmq-server pgbouncer mailpit`.
- PostgreSQL: in PowerShell as administrator, `Restart-Service postgresql-x64-18`.

The setup script `scripts/wsl/setup-services.sh` was a one-time install. Don't run it again unless you set up a new machine.

## Addresses

| What | Address | Sign in |
| --- | --- | --- |
| API | https://formalie.dev:5004 | |
| API docs (development only) | https://formalie.dev:5004/docs and /redoc | |
| Celery dashboard: Flower | http://127.0.0.1:5555 | none |
| RabbitMQ | http://127.0.0.1:15672 | user `formalie`, the password inside `RABBITMQ_URL` in `.env` (between `formalie:` and `@`) |
| Emails caught in development: Mailpit | http://127.0.0.1:8025 | none |
| Redis | the Redis Insight desktop app (redis.io/insight), connect to `127.0.0.1:6379` | none |
| Frontend | https://formalie.dev:2202 (run from the frontend project) | |

## Settings: `.env`

- `.env` holds the real values and passwords. The app reads only this file, and git never stores it.
- `.env.example` is the committed template with `CHANGE_ME` placeholders. Never put real passwords in it.
- A new setting goes into both: the real value in `.env`, a placeholder in `.env.example`.
- Secret keys (references, tokens): `fmly\Scripts\python.exe scripts\gen_keys.py --write` adds any missing ones to `.env` and keeps existing ones.

## Common commands

All from the project folder:

| What | Command |
| --- | --- |
| Run all tests | `fmly\Scripts\python.exe -m pytest` |
| Tests without the database | `fmly\Scripts\python.exe -m pytest -m "not db"` |
| Apply database migrations (development, then test) | `fmly\Scripts\alembic.exe upgrade head`, then `fmly\Scripts\alembic.exe -x db=test upgrade head` |
| Create roles and databases (new machine, or to change their passwords) | `fmly\Scripts\python.exe scripts\db_bootstrap.py` |
| Add the test workspaces and accounts (same as the frontend's mock; safe to repeat) | `fmly\Scripts\python.exe scripts\seed_dev.py` |
| Refresh the location databases (MaxMind; Beat also does it weekly) | `fmly\Scripts\python.exe scripts\geoip_update.py` |
| Load request logs that went to the fallback files | `fmly\Scripts\python.exe scripts\replay_request_logs.py` |
| Check the encryption against the frontend's own code | `fmly\Scripts\python.exe scripts\check_envelope_vectors.py` |
| Record the frontend's rules again after its `shared/` changed, then rebuild the catalogues | `fmly\Scripts\python.exe scripts\dump_frontend_rules.py`, `fmly\Scripts\python.exe scripts\dump_settings_rules.py`, `fmly\Scripts\python.exe scripts\dump_forms_rules.py`, then `fmly\Scripts\python.exe scripts\gen_frontend_catalogues.py` |
| Rebuild error codes after the frontend added some | `fmly\Scripts\python.exe scripts\gen_error_codes.py` |
| Install packages (new machine) | `fmly\Scripts\python.exe -m pip install -r requirements-dev.txt` |

## Test workspaces and accounts (development)

`scripts/seed_dev.py` creates the same ones as the frontend's mock, with the mock's sample departments and job titles in Remedy Legal and Samath Tax:
- **Workspaces:** `remedylegal` (Business plan), `samathtax` (Starter), `oldco` (suspended) and `formalie-team` (Formalie's own).
- **Accounts:** `admin@remedylegal.test` (owner), `admin@samathtax.test` (owner) and `james.carter@carterpartners.test` (a member of both, for "find my workspace").
- **Password:** the mock's test password, `MOCK_PASSWORD` in the frontend's `server/mock/data/tenants.ts`.
- **Sign-in codes:** they arrive in Mailpit (http://127.0.0.1:8025).

## Social sign-in (Google, Microsoft, Facebook)

- **Keys:** `OAUTH_GOOGLE_*`, `OAUTH_MICROSOFT_*` and `OAUTH_FACEBOOK_*` in `.env`. A provider with empty keys shows "not available yet" on its button, like the mock. Restart the API after changing them.
- **Address registered at each provider** (development): `https://manage.formalie.dev:2202/api/v1/auth/oauth/{google|microsoft|facebook}/callback`. Every provider sends people back to `manage.`; the API then sends them to the page they started on. `OAUTH_REDIRECT_BASE` changes the first part if needed.
- **Sign-up** (https://manage.formalie.dev:2202/auth/signup): the button skips the email code (the provider checked the address) and goes straight to naming the workspace.
- **Sign-in** on a workspace: only for someone who already has an account there with the same email, and it still asks for the 6-digit code. The test accounts are `.test` addresses, so add your own address first:
  `fmly\Scripts\python.exe scripts\seed_dev.py --person you@gmail.com` adds it to Remedy Legal as an Admin and switches on all three buttons there. Then sign in at https://remedylegal.formalie.dev:2202/auth/login with the button.
- **Starter plan** has no social sign-in for new people, but whoever came in with Google, Microsoft or Facebook (the Owner who signed up with it) keeps using it, with no password.

## How the pieces fit

- **PostgreSQL 18** (Windows, port 5432): databases `formalie` (development) and `formalie_test` (tests). Workspace tables live in the `formaly` schema, global tables in `platform`. Every workspace table has row-level security forced. Nothing is ever hard deleted.
- **Redis** (Ubuntu, 6379): cache, rate limits and secure-channel keys. If it goes down, the API keeps working: it falls back and logs the outage once.
- **RabbitMQ** (Ubuntu, 5672): Celery jobs and the `formalie.events` exchange, fed by the event outbox.
- **Celery** (Windows, `--pool=solo`): worker queues `scheduled` (outbox relay, partitions, GeoIP refresh, error log loading), `logs` (request log), `notifications` (emails) and `exports` (export files), plus Beat for the timers.
- **Stored files** (uploads such as logos, and exports): `data/storage/tenants/{workspace}/orgs/{organisation}/{module}/{id}` (not in git). Object storage replaces the folder before going live (to choose: see PROGRESS, open questions).
- **Request log** (`formaly.request_logs`): every request in full (headers, body, response, real IP, location, device), with secrets masked.
- **Mailpit** (Ubuntu, 8025): catches every email in development, such as sign-in codes, so nothing is really sent.
- **MaxMind GeoLite2** (`data/geoip/`, not in git): locations for the request log.

## Setting up a new machine

The full steps are in [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md):
1. Install the packages into the `fmly` venv.
2. Copy `.env.example` to `.env`, fill in the passwords, and run `gen_keys.py --write`.
3. Run `db_bootstrap.py` and the migrations.
4. Install Ubuntu in WSL with mirrored networking, and run `scripts/wsl/setup-services.sh` once.
5. Run `geoip_update.py`.
6. Run `dev-up.ps1`.

## Resuming work with Claude Code

Start a new session in this folder with:

```
Read CLAUDE.md and docs/BACKEND-ROADMAP.md. Tell me which phase we are on
and what is left in it, then continue from there.
```

`docs/PROGRESS.md` holds the details: what's done, what's next, and any open questions.

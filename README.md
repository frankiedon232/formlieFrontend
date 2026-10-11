# Formalie API (formlyBackend)

The backend of Formalie. It replaces the mock API the finished frontend (`C:\UNETPROJECTS\formalieFrontend`) runs against today. Python 3.11, FastAPI, PostgreSQL 18, Redis, RabbitMQ, Celery.

- **Where the work stands:** [docs/PROGRESS.md](docs/PROGRESS.md) (phase by phase), [docs/BACKEND-ROADMAP.md](docs/BACKEND-ROADMAP.md), [docs/ENDPOINTS.md](docs/ENDPOINTS.md) (every endpoint, ticked when done).
- **Rules and design:** [CLAUDE.md](CLAUDE.md) and everything in [docs/](docs/).

---

## Every day: start after a restart

Open PowerShell in `C:\UNETPROJECTS\formlyBackend` and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1
```

It wakes Ubuntu (WSL) and keeps it running in the background, checks that every service answers, then opens one window each for the API, the Celery worker, Celery Beat and Flower. Nothing else to do: the services start by themselves (Redis, RabbitMQ, PgBouncer and Mailpit with Ubuntu; PostgreSQL with Windows).

| To | Run |
| --- | --- |
| Start services only (no API or workers) | `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApp` |
| Stop the API, workers and the keep-alive (data is never touched) | `powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1` |
| Start only the API | `fmly\Scripts\python.exe -m app.run` |

The setup script `scripts/wsl/setup-services.sh` was a one-time install. Don't run it again unless you set up a new machine.

If a service is down, `dev-up` says which one. To fix it:
- Redis, RabbitMQ, PgBouncer or Mailpit: in an Ubuntu window, `sudo systemctl restart redis-server rabbitmq-server pgbouncer mailpit`.
- PostgreSQL: in PowerShell as administrator, `Restart-Service postgresql-x64-18`.

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
| Refresh the location databases (MaxMind; Beat also does it weekly) | `fmly\Scripts\python.exe scripts\geoip_update.py` |
| Load request logs that went to the fallback files | `fmly\Scripts\python.exe scripts\replay_request_logs.py` |
| Check the encryption against the frontend's own code | `fmly\Scripts\python.exe scripts\check_envelope_vectors.py` |
| Rebuild error codes after the frontend added some | `fmly\Scripts\python.exe scripts\gen_error_codes.py` |
| Install packages (new machine) | `fmly\Scripts\python.exe -m pip install -r requirements-dev.txt` |

## How the pieces fit

- **PostgreSQL 18** (Windows, port 5432): databases `formalie` (development) and `formalie_test` (tests). Workspace tables live in the `formaly` schema, global tables in `platform`. Every workspace table has row-level security forced. Nothing is ever hard deleted.
- **Redis** (Ubuntu, 6379): cache, rate limits and secure-channel keys. If it goes down, the API keeps working: it falls back and logs the outage once.
- **RabbitMQ** (Ubuntu, 5672): Celery jobs and the `formalie.events` exchange, fed by the event outbox.
- **Celery** (Windows, `--pool=solo`): worker queues `scheduled` (outbox relay, partitions, GeoIP refresh) and `logs` (request log), plus Beat for the timers.
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

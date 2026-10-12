# CLAUDE.md, formaliePlatformBack (Formalie Platform Admin, backend)

Read `README.md`, `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/BACKEND-ARCHITECTURE.md`, `docs/DATA-MODEL.md`, `docs/API-CONTRACT.md`, `docs/SECURITY-PROTOCOL.md`, `docs/FORMALIE-INTEGRATION.md`, `docs/ANALYTICS.md` and `docs/ERROR-CODES.md` before any task. Work through the phases in [`PROGRESS.md`](PROGRESS.md) in order and tick tasks there when done.

## What this is

The Formalie team's own system: analytics over the whole platform (Google Analytics style), full management of workspaces, accounts, subscriptions, payments, help content, default data and platform settings, and its own staff with roles and access. **It is not the customer portal.** Customers never sign in here; Formalie staff only.

Two projects make it up: this one (the FastAPI backend, its own database) and **formaliePlatformFront** (the Nuxt front end, its own folder and repository). They talk only through the API in `docs/API-CONTRACT.md`. This backend also reads and acts on Formalie's database and system, only in the ways `docs/FORMALIE-INTEGRATION.md` allows.

## Brand

Every email (staff invitations, two-step codes, sign-in notices, reports) uses the Formalie mark (Field F, owner 2026-10-10) from `docs/brand/png/`, with the rules in `docs/brand/BRAND.md`:
- the header uses `formalie-lockup-light@2x.png` (shown 300 × 64);
- small places use `formalie-mark-64.png`.

Use PNG, not SVG, because many mail apps block SVG. The full kit, with the SVGs and web icons, is in formaliePlatformFront `docs/brand/`.

## Keep docs in sync

`PROGRESS.md` is this project's tracker (every task per phase, overview table, new-requests log, progress log). Every milestone: tick the task, add a Progress log line, update the overview table and "Last updated"; any new request goes into the right phase **and** the New requests log immediately. Update any doc whose facts changed (decisions → `03-DECISIONS-AND-NOTES.md`, contract → `API-CONTRACT.md`, setup → `02-DEV-ENVIRONMENT.md`, tables → `DATA-MODEL.md`, anything Formalie must provide → `FORMALIE-INTEGRATION.md`, hosting → `04-HOSTING.md` and `infra/`).

**Shared docs** (the same file in both projects): `00-OVERVIEW`, `01-ARCHITECTURE`, `02-DEV-ENVIRONMENT`, `03-DECISIONS-AND-NOTES`, `04-HOSTING`, `API-CONTRACT`, `SECURITY-PROTOCOL`, `ERROR-CODES`, `ANALYTICS`, `FORMALIE-INTEGRATION`. When one changes here, say so in the commit message and tell the owner, so the same change is made in formaliePlatformFront. The contract is changed together with the front end, never only on one side.

**Commit and push** after each verified milestone (ruff + mypy + pytest green); stop for the owner's review at the end of each phase.

## Stack (fixed, same as formlyBackend, no deviation)

Python 3.11 · FastAPI · Uvicorn · SQLAlchemy 2 (async, asyncpg) · Alembic · Pydantic 2 + pydantic-settings · PostgreSQL 16 + PgBouncer · Redis 7 · RabbitMQ 3 + Celery / Celery Beat · httpx (calls to Formalie, mTLS) · cryptography (ECDH, AES-GCM, HKDF, Fernet) · argon2-cffi · boto3-compatible S3 client. Dev tooling: pytest, pytest-asyncio, ruff, mypy. If `formlyBackend` already chose a different library for the same job (for example its S3 client or its TOTP helper), use the same one. **Ask before adding anything else.**

**No Docker** (owner, 2026-10-10): services are installed directly (development: the same installed services as Formalie, kept apart by database, vhost, Redis index and bucket); production on AWS or dedicated servers with systemd and Nginx (`docs/04-HOSTING.md`, `infra/`).

Run: `uvicorn app.run:app --host 0.0.0.0 --port 5601 --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formalie-key.pem` (venv `padm`). Workers: `celery -A app.workers.celery_app worker -Q ingest,rollups,publish,actions,reports,mail,maintenance`, `celery -A app.workers.celery_app beat`. API URL `https://platformapi.formalie.dev:5601/`.

## Hard rules

1. **The contract is the spec.** Implement exactly what `API-CONTRACT.md` says (shapes, codes, paging); change the contract first when something must differ, together with the front end.
2. **Staff only, strongest security.** Two-step sign-in mandatory; step-up on sensitive actions (`PLT-AUTH-1020` when stale, SECURITY-PROTOCOL §5); approvals (maker-checker) for the actions in §6: they never run on the first request, they create an approval and run only when another permitted staff member approves.
3. **Envelope on everything** except the handshake and `/api/health` (SECURITY-PROTOCOL §1), with the platform's own keys and HKDF info `formalie-platform-envelope-v1`.
4. **Every route checks permission** by address (`permission_for`) and per item in the service; no route without a permission rule (a test enforces it).
5. **Every change writes its audit record in the same transaction** (append-only, hash chained); failed and refused attempts too.
6. **Formalie access only through `modules/formalie_bridge`**: reads via `reader` on the replica (read-only role, time-outs, row caps, paging in the database, no answer content, no secrets), changes via `admin_client` (mTLS, HMAC, idempotency key, staff id, approval id, reason), global tables via `publisher` (then `platform.published`). Never write Formalie tenant tables. Formalie stays the owner of its rules.
7. **Least data:** never return or log answers, passwords, tokens, secrets, card data or full IPs; mask personal data unless the call is a reveal (permission + step-up, audited).
8. **Database paging** for every list; counts aggregated in SQL; analytics reports read rollups, not raw events, for ranges longer than a day.
9. **Async and safe:** no blocking calls in request handlers; slow or heavy work goes to Celery; every external call has a time-out and a retry policy.
10. **Migrations with Alembic only**; never edit the database by hand; seeds through `app/cli.py`.
11. **Errors** only with `PLT-*` codes from `ERROR-CODES.md` (add new ones there first), one error shape, trace ids.
12. **Secrets** from the environment / secret store only; `.env` never committed; keys rotatable (MultiFernet, versioned id-reference keys).
13. **Global product, no em dashes.** Messages and seed data stay international and neutral; never "—" in messages, comments or docs.

## Done means

Tests for services, routes (through the envelope), permissions (every route × role), approvals, audit chain, bridge (against a fake Formalie), analytics rollups · ruff, mypy, pytest green · `PROGRESS.md` and docs updated · committed and pushed.

## Git

This project is the branch `formaliePlatformBack` of https://github.com/frankiedon232/formlieFrontend (one branch per project, like `formalieFrontend` and `formalieBackend`). Commit and push there after each verified milestone: `git push origin formaliePlatformBack`.

## Going live

`docs/PRODUCTION-CHECKLIST.md` (the same file in all five Formalie projects) lists everything that changes for production. Whenever you add a setting, key, address or service that differs between development and production, add it there, in every project's copy. Before any production deployment, walk the owner through it.

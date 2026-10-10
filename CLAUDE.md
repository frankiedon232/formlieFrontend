# CLAUDE.md, formlyBackend (Formalie API)

Read `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/02-DEV-ENVIRONMENT.md`, `docs/03-DECISIONS-AND-NOTES.md`, `docs/BACKEND-SPEC.md`, `docs/DATABASE-DESIGN.md`, `docs/SECURITY-PROTOCOL.md`, `docs/API-CONTRACT.md`, `docs/ERROR-CODES.md`, `docs/OPTION-LISTS.md`, `docs/FRONTEND-REFERENCE.md`, `docs/ENDPOINTS.md` and `docs/PLATFORM-ADMIN-INTEGRATION.md` before any task. Follow `docs/BACKEND-ROADMAP.md` in order.

## Where this project stands (2026-10-10)

The frontend, **formalieFrontend** (`C:\UNETPROJECTS\formalieFrontend`), is finished. It runs against a mock API (`server/mock/**`) that returns exactly what this backend must return. Only the Payoneer connection and the switch to this backend are left on its side. This backend replaces the mock:
- **Endpoints:** `docs/ENDPOINTS.md` lists every endpoint, with its mock file, guards, permissions and audit actions. Tick each one when it's done.
- **Rules to port:** `docs/FRONTEND-REFERENCE.md` lists the rules in the frontend's `shared/` folder that must give the same answers here (validation, logic, formulas, permissions, plans, error codes, envelope), with parity tests.
- **The frontend is read only from here.** Never change it. When the contract has to change, write it into `docs/API-CONTRACT.md` here, and tell the owner so the frontend's copy is updated too.

The platform admin (`formaliePlatformFront` + `formaliePlatformBack`) and the website (`formalieSite`) are separate projects that come after this one. What this backend owes the platform admin is in `docs/PLATFORM-ADMIN-INTEGRATION.md` §5.

## Keep docs in sync

- **Roadmap:** tick tasks in `docs/BACKEND-ROADMAP.md` and boxes in `docs/ENDPOINTS.md` as they're done.
- **Shared docs:** these are the same files as in the frontend: `00-OVERVIEW`, `01-ARCHITECTURE`, `02-DEV-ENVIRONMENT`, `03-DECISIONS-AND-NOTES`, `API-CONTRACT`, `ERROR-CODES`, `SECURITY-PROTOCOL` and `OPTION-LISTS`. A change to one is a change to both.
- **Phase end:** stop for the owner's review at the end of each phase.

## Stack (fixed)

Python 3.11 · FastAPI · Pydantic v2 + pydantic-settings · SQLAlchemy 2.0 async (asyncpg) · Alembic · PostgreSQL 16 (primary + read replicas, PgBouncer) · Redis 7 (`redis.asyncio`) · Celery 5 + RabbitMQ · cryptography (Fernet/MultiFernet, ECDH, AES-GCM, HKDF) · argon2-cffi · pyotp · Authlib (OAuth/OIDC) · geoip2 · openpyxl/xlsxwriter · structlog or std logging · pytest + httpx + pytest-asyncio.

Entry point: `uvicorn app.run:app --host 0.0.0.0 --port 5004 --ssl-certfile ... --ssl-keyfile ...` (venv `fmly`). Dev URL `https://formalie.dev:5004` (docs at `/docs`, `/redoc`; disable both in production or protect them). Development services run directly on the machine, **no Docker** (owner, 2026-10-10; see 02-DEV-ENVIRONMENT).

## Hard rules

1. **Tenant isolation is absolute.** Every tenant table has `tenant_id` + `organisation_id`, **PostgreSQL RLS enabled and FORCED**, and the app connects as a non-owner role without `BYPASSRLS`. Every transaction sets `app.tenant_id`, `app.organisation_id`, `app.user_id` with `set_config(..., true)`. Repositories also filter by tenant explicitly (defence in depth). Write a cross-tenant test for every new table/endpoint.
2. **Subdomain identifies context; the token identifies the user.** They must agree or the request fails (`FRM-TEN-1003`) and a security event is logged.
3. **All traffic uses the encryption envelope** (`SECURITY-PROTOCOL.md`) via pure ASGI middleware; only documented exceptions are plaintext.
4. **Auth:** Bearer Fernet access tokens (15 min) + rotated single-use Fernet refresh tokens (7 days) with reuse detection; OTP on every login; MFA enforced for admins; CSRF tokens with expiry on state-changing requests.
5. **Rate limiting on every endpoint** (Redis sliding window: IP, user, tenant, route).
6. **Soft delete only** (`deleted_at`, `deleted_by`). No hard deletes, no `ON DELETE CASCADE`. Unique constraints are partial (`WHERE deleted_at IS NULL`).
7. **UUIDs** (UUIDv7) for all IDs; never expose sequential integers. **No id leaves the server as it is:** every id in every response is an encrypted reference, decrypted at the edge (SECURITY-PROTOCOL §10). Public form links use the form's random public key.
8. **Heavy work goes to Celery** via events on RabbitMQ (exports, destinations, webhooks, emails/OTP, analytics, file processing, log persistence). Requests stay fast.
9. **Read/write split:** writes and read-after-write go to the primary; list/report/analytics reads go to replicas via the session router.
10. **Cache-aside in Redis** with tenant-prefixed, versioned keys; invalidate on change events.
11. **Every endpoint:** Pydantic request/response models, custom error codes (`FRM-<DOMAIN>-<NNNN>`), `try/except/finally` around external I/O, structured logging with `trace_id`.
12. **Log everything** per BACKEND-SPEC §8 (requests with geo, audit trail, errors by level to DB + dated files). Never log secrets.
13. Tenant-aware file paths: `tenants/{tenant_id}/orgs/{organisation_id}/{module}/{uuid}`.
14. Modules are self-contained (`models, schemas, repository, service, router, events, tasks`); no module reaches into another's tables directly, call its service.
15. **Permissions on every route** (from B4): the role's grant for the action with its scope (Own, Shared, Own & shared, All) checked against the item, exactly like the mock (BACKEND-SPEC §11).
16. **Audit every change** with the action keys in the frontend's `shared/utils/audit/events.ts` (BACKEND-SPEC §12). A feature isn't done until its actions are recorded.
17. **Same answers as the frontend.** Rules that exist in the frontend's `shared/` are ported with parity tests (FRONTEND-REFERENCE.md). Errors are `FRM-*` codes, never translated text: the frontend translates them into 20 languages.
18. **Money rules** in SECURITY-PROTOCOL §11 (Payoneer, idempotency, signed webhooks). Card details never touch Formalie.
19. **Global product:** sample and seed data stay international and neutral (fictional phone ranges such as +44 7700 900xxx). Compliance wording promises controls, never certifications we don't hold.
20. **No em dashes** in any text, docs or messages: use a comma, a colon or a full stop.

## Layout

```
app/
  run.py                      # create_app(); app = create_app()
  core/
    config.py                 # Settings (pydantic-settings, .env)
    db/        base.py (mixins) · engines.py (primary/replica) · session.py (router + RLS context) · rls.py
    security/  fernet_tokens.py · envelope.py · passwords.py · otp.py · csrf.py · oauth.py
    middleware/ request_context.py · tenant.py · envelope.py · rate_limit.py · request_log.py · security_headers.py
    errors/    codes.py · exceptions.py · handlers.py
    logging/   setup.py · sinks.py · geo.py
    cache/     redis.py · tiers.py
    events/    bus.py · schemas.py
  modules/
    platform/ tenants/ organisations/ auth/ users/ forms/ themes/ templates/ responses/
    sharing/ links/ option_sets/ destinations/ webhooks/ api_keys/ files/ exports/
    analytics/ settings/ billing/ audit/ logs/ rbac/ dashboard/
    people/ onboarding/ org/ public/ api_service/ data_sources/ query/ ai/ help/
    emails/ notifications/ privacy/ sso/ address/ page_designs/ platform_bridge/
  api/v1/router.py
  workers/ celery_app.py · queues.py
alembic/  tests/  scripts/  logs/ (gitignored)
```

# CLAUDE.md — formalieBackend (formalie API)

Read `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/BACKEND-SPEC.md`, `docs/DATABASE-DESIGN.md`, `docs/SECURITY-PROTOCOL.md`, `docs/API-CONTRACT.md`, `docs/ERROR-CODES.md` before any task. Follow `docs/BACKEND-ROADMAP.md` in order. The API contract is shared with the frontend: **any change to it must be written back into `API-CONTRACT.md`**.

## Stack (fixed)

Python 3.11 · FastAPI · Pydantic v2 + pydantic-settings · SQLAlchemy 2.0 async (asyncpg) · Alembic · PostgreSQL 16 (primary + read replicas, PgBouncer) · Redis 7 (`redis.asyncio`) · Celery 5 + RabbitMQ · cryptography (Fernet/MultiFernet, ECDH, AES-GCM, HKDF) · argon2-cffi · pyotp · Authlib (OAuth/OIDC) · geoip2 · openpyxl/xlsxwriter · structlog or std logging · pytest + httpx + pytest-asyncio.

Entry point: `uvicorn app.run:app --host 0.0.0.0 --port 5004 --ssl-certfile ... --ssl-keyfile ...`. Dev URL `https://formalie.dev:5004` (docs at `/docs`, `/redoc`; disable both in production or protect them).

## Hard rules

1. **Tenant isolation is absolute.** Every tenant table has `tenant_id` + `organisation_id`, **PostgreSQL RLS enabled and FORCED**, and the app connects as a non-owner role without `BYPASSRLS`. Every transaction sets `app.tenant_id`, `app.organisation_id`, `app.user_id` with `set_config(..., true)`. Repositories also filter by tenant explicitly (defence in depth). Write a cross-tenant test for every new table/endpoint.
2. **Subdomain identifies context; the token identifies the user.** They must agree or the request fails (`FRM-TEN-1003`) and a security event is logged.
3. **All traffic uses the encryption envelope** (`SECURITY-PROTOCOL.md`) via pure ASGI middleware; only documented exceptions are plaintext.
4. **Auth:** Bearer Fernet access tokens (15 min) + rotated single-use Fernet refresh tokens (7 days) with reuse detection; OTP on every login; MFA enforced for admins; CSRF tokens with expiry on state-changing requests.
5. **Rate limiting on every endpoint** (Redis sliding window: IP, user, tenant, route).
6. **Soft delete only** (`deleted_at`, `deleted_by`). No hard deletes, no `ON DELETE CASCADE`. Unique constraints are partial (`WHERE deleted_at IS NULL`).
7. **UUIDs** (UUIDv7) for all IDs; never expose sequential integers.
8. **Heavy work goes to Celery** via events on RabbitMQ (exports, destinations, webhooks, emails/OTP, analytics, file processing, log persistence). Requests stay fast.
9. **Read/write split:** writes and read-after-write go to the primary; list/report/analytics reads go to replicas via the session router.
10. **Cache-aside in Redis** with tenant-prefixed, versioned keys; invalidate on change events.
11. **Every endpoint:** Pydantic request/response models, custom error codes (`FRM-<DOMAIN>-<NNNN>`), `try/except/finally` around external I/O, structured logging with `trace_id`.
12. **Log everything** per BACKEND-SPEC §8 (requests with geo, audit trail, errors by level to DB + dated files). Never log secrets.
13. Tenant-aware file paths: `tenants/{tenant_id}/orgs/{organisation_id}/{module}/{uuid}`.
14. Modules are self-contained (`models, schemas, repository, service, router, events, tasks`); no module reaches into another's tables directly — call its service.

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
  api/v1/router.py
  workers/ celery_app.py · queues.py
alembic/  tests/  scripts/  docker/  logs/ (gitignored)
```

# Backend Roadmap — formalieBackend

Every phase ends with: tests (unit + API + **cross-tenant isolation tests**), migrations reviewed, OpenAPI updated, API-CONTRACT.md updated, error codes registered.

## B0 — Foundation

- [ ] Project layout per CLAUDE.md, `app/run.py` app factory, settings from `.env`, requirements pinned.
- [ ] `docker-compose.dev.yml`: Postgres primary + replica, PgBouncer, Redis, RabbitMQ, MinIO, Mailpit.
- [ ] Logging setup (level files by date, structured, trace_id), error codes + exception handlers, standard response models.
- [ ] Middleware chain: request context, security headers, IP rate limit, tenant, envelope, request log.
- [ ] DB: engines (primary/replica), session router, RLS context, mixins, Alembic with `enable_tenant_rls` helper, DB roles.
- [ ] Redis cache tiers, Celery app + queues, event bus + outbox relay.
- [ ] CI test asserting RLS forced on every tenant table.

## B1 — Crypto + auth

- [ ] Handshake (ECDH P-256 + HKDF + AES-GCM), nonce store, test vectors shared with frontend.
- [ ] Fernet tokens (MultiFernet), refresh rotation + reuse detection, session deny-list, CSRF.
- [ ] Signup (tenant + org + admin + subdomain), login, OTP (email via Mailpit in dev), resend, find workspace, forgot/reset, logout, sessions, TOTP.
- [ ] OAuth providers (Google, Microsoft, Apple, Facebook) + per-tenant provider config.
- [ ] Rate limits and lockouts on auth.

## B2 — Platform data + tenant public profile + onboarding + settings base

## B3 — Forms core

- [ ] Folders, forms CRUD, draft autosave with row_version, publish/unpublish/close, versions + restore, duplicate, soft delete/restore, slug.
- [ ] FormSchema validation (Pydantic), publish checks.

## B4 — Themes, templates, option sets

## B5 — Public forms

- [ ] Cached published form, password unlock, sessions/resume, pre-signed uploads + scanning, submit with schema validation, captcha, limits, schedule, short links, embed rules (CSP frame-ancestors), SEO data.

## B6 — Responses + exports (XLSX/CSV/PDF workers) + notifications

## B7 — Destinations (own DB writers), webhooks (HMAC, retries, DLQ), API keys

## B8 — Analytics rollups and endpoints

## B9 — Sharing grants (edit/view/responses)

## B10 — Users and invitations (can be pulled earlier)

## B11 — Subscription and plan enforcement (billing integration)

## B12 — Audit trail endpoints + security events (audit capture itself starts once B3 lands)

## B13 — Live collaboration backend (optional: Yjs WebSocket provider)

## B14 — Last: RBAC (roles, permissions, enforcement on all routes), dashboard aggregates

## B15 — Hardening

- [ ] Load tests, query review, backups + restore drill, security review/pen test, production Nginx + Cloudflare config, observability dashboards.

## Hand-over pack (when switching projects)

OpenAPI JSON, final API-CONTRACT.md, ERROR-CODES.md, env variable list, security test vectors, open issues list.

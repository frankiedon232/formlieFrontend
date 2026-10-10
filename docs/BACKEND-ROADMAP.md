# Backend Roadmap, formlyBackend

Rewritten on 2026-10-10, after the frontend (formalieFrontend) was finished against its mock API. The order follows how the frontend was built, so every phase can be switched on in the frontend as soon as it's done.

**Every phase is done when:**
- the phase's endpoints in `ENDPOINTS.md` are ticked, with the same shapes as the mock, the same permission checks and the same audit actions;
- the tests pass: unit, API, **cross-tenant isolation**, and parity with the frontend's rules (FRONTEND-REFERENCE.md);
- migrations have been reviewed;
- OpenAPI is updated, and any contract change is written back into `API-CONTRACT.md` (in both projects);
- new error codes are registered in `ERROR-CODES.md`;
- the frontend runs that area against the real backend: `NUXT_PUBLIC_API_MOCK=false`, or that area's routes through the dev proxy.

Then stop for the owner's review.

## B0, Foundation

- [ ] Project layout per CLAUDE.md, `app/run.py` app factory, settings from `.env` (+ `.env.example`), requirements pinned.
- [ ] Development services installed directly on the machine, **no Docker** (owner, 2026-10-10; 02-DEV-ENVIRONMENT): PostgreSQL 16 (primary + replica), PgBouncer, Redis 7 (Memurai or WSL), RabbitMQ, MinIO, Mailpit.
- [ ] Logging (files by level and date, structured, trace_id), error codes from `shared/utils/errors/codes.ts`, exception handlers, standard response models.
- [ ] Middleware chain (BACKEND-SPEC §1): request context, security headers, IP rate limit, tenant, envelope, encrypted references, request log.
- [ ] DB: primary / replica engines, session router, RLS context, mixins, Alembic with the `enable_tenant_rls` helper, DB roles (including `platform_reader` / `platform_writer`).
- [ ] Redis cache tiers, the Celery app and queues, the event bus and the outbox relay.
- [ ] CI test asserting RLS is forced on every tenant table.

## B1, Secure channel, workspaces and sign-in (F2, F3)

- [ ] Handshake (ECDH P-256 + HKDF + AES-GCM), nonce store, test vectors shared with the frontend (`shared/utils/crypto/*`).
- [ ] Encrypted references (SECURITY-PROTOCOL §10) on every id in and out.
- [ ] Tenant public profile, subdomain availability, find workspace.
- [ ] Sign-up (tenant + organisation + admin + subdomain), login, OTP (Mailpit), resend, forgot / reset, logout, refresh rotation with reuse detection, CSRF, sessions, TOTP and recovery codes.
- [ ] OAuth providers (Google, Microsoft, Apple, Facebook) and per-workspace provider settings; rate limits and lockouts.
- [ ] Development seed with the same test workspaces and accounts as the mock (`server/mock/data/tenants.ts`), so the frontend's flows work unchanged.

## B2, Audit trail and logs (F4)

- [ ] `audit_logs` with the catalogue from `shared/utils/audit/events.ts`, `record()` used by B1 sign-in events and every later phase.
- [ ] Audit list, filters, detail, export (`routes/audit.ts`), request logs with geo (MaxMind), error logs, security events.

## B3, Onboarding, settings base and default data (F5, F14 base)

- [ ] Onboarding steps and status; company, branding (logo, dark logo, tab icon, colour, welcome), localisation.
- [ ] Platform reference data (countries, languages, currencies, timezones, regions) and **Formalie default data** seeded for each new workspace: system lists, default folders, roles, email templates, system templates (FRONTEND-REFERENCE → Default data).
- [ ] Uploads (pre-signed, scanned), organisations (`routes/org.ts`), navigation counts.

## B4, People, roles and access (F16, F22 brought forward)

- [ ] Roles with the permission catalogue and scopes, Owner built in (`shared/utils/auth/permissions.ts`).
- [ ] People: profiles with departments, job titles and role, invitations, enable / disable, reset, force MFA; my profile (`/me`, tips and tours seen).
- [ ] The permission dependency on every route from here on (BACKEND-SPEC §11).

## B5, Forms core (F6, F7)

- [ ] Folders, forms list with its two chart cards' data, lifecycle (draft, publish, close, reopen, archive, trash, restore), duplicate.
- [ ] Draft autosave with `row_version`, versions and restore, publish checks (`forms/validate.ts`), FormSchema models (`forms/schema.ts`), logic and formulas (`forms/logic.ts`, `forms/formula.ts`, `forms/details.ts`).
- [ ] Form overview and the directory.

## B6, Design, templates and lists (F8, F9, F15)

- [ ] Themes (light / dark, 21 fonts), page designs and landing pages.
- [ ] Templates (system and workspace, save as, use).
- [ ] Option lists: simple, with levels, large lists up to 200,000 items loaded level by level (OPTION-LISTS.md); details used in formulas and logic.

## B7, Public forms, sharing and links (F10)

- [ ] Internal published-form endpoint for server-rendered `/{formKey}/fill` and `/embed` (server-only token), short links `/s/{code}`.
- [ ] Share settings, form invites, who can see this form (`/forms/{id}/access`), embed rules (frame-ancestors), SEO.
- [ ] Sessions and resume, pre-signed uploads, submit with the ported validation, proof of work, availability and limits.

## B8, Responses (F11)

- [ ] Responses list and inbox, filters per field, detail, review status, notes, answer edits with history, files and the file viewer.
- [ ] Exports (XLSX, CSV, PDF) as Celery jobs with progress; response emails and in-app notifications.

## B9, Data sources and destinations (F12)

- [ ] Connections per engine (plan-limited), encrypted credentials, test.
- [ ] Response storage in Formalie's prefixed tables in the customer's database (`datasources/ddl.ts`), Celery writers, retries, failures surfaced.
- [ ] Explorer (schema, rows, edits), query editor with safety checks and limits, saved queries, activity.
- [ ] Destinations and webhooks (HMAC, retries, dead-letter queue).

## B10, API service (F13)

- [ ] Management: services, endpoints, field choices, tokens (static and client credentials), access rules, allowed websites, traffic, docs.
- [ ] The public gateway on `api.formalie.*` as its own service: the order of checks in ENDPOINTS.md, CORS preflights, idempotent POST, signing, rate limits, traffic logs.

## B11, Settings, the rest (F14)

- [ ] Emails: templates, preview, test, sent log; sending as the Formalie address, an own domain (DNS checks) or SMTP.
- [ ] SSO (SAML / OIDC), address (subdomain change, own domain), appearance (light / dark colours, default mode), form defaults.
- [ ] Security (sessions, sign out everywhere, activity, IP allowlist, idle timeout), privacy (retention with preview, find / export / delete a person's data), data region.

## B12, Analytics and dashboard (F18, F21)

- [ ] Per-form analytics rollups (views, starts, completions, drop-off, timing) and insights.
- [ ] Dashboard: Workspace, Forms, Data sources and API service views with period, folder and owner filters and first steps.

## B13, AI assistant (F19)

- [ ] Settings and allowance, create / assist / analyse / write / translate with the chosen provider, request history and removal, everything audited.

## B14, Help centre and tours (F25)

- [ ] Help categories and articles, search, the 12 tours and who has seen them, all read from global tables the platform admin edits.

## B15, Subscriptions and payments (F24)

- [ ] Plans, preview, change, cancel, resume, scheduled changes, invoices, billing settings, payment method.
- [ ] Payoneer checkout, the signed webhook, every rule in SECURITY-PROTOCOL §11, daily reconciliation. Plan limits enforced across all modules.

## B16, Platform admin bridge

- [ ] Everything in PLATFORM-ADMIN-INTEGRATION.md §5: DB roles, global tables (announcements, feature flags, platform settings, help, default data) with cache invalidation, the internal admin API (mTLS, HMAC, idempotency), support access with consent, events, health.

## B17, Hardening and switch-over

- [ ] The frontend's mock turned off for good (every ENDPOINTS.md box ticked).
- [ ] Load tests, query review, backups and a restore drill, security review / pen test, production Nginx and Cloudflare, observability dashboards.

## Hand-over pack

OpenAPI JSON, the final API-CONTRACT.md, ERROR-CODES.md, the env variable list, security test vectors, the open issues list.

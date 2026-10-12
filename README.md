# Formalie Platform Admin, front end (formaliePlatformFront)

The Nuxt front end of the Formalie Platform Admin. Its backend is the separate project **formaliePlatformBack** (FastAPI, own database).


The Formalie team's own system for running the whole Formalie platform. A separate project from the Formalie portal (`formalieFrontend` / `formlyBackend`), with its **own front end, own backend and own database**, that can also **read and act on Formalie's database and system**.

Decided by the owner on 2026-10-10 (it was phase F23 inside the Formalie portal; it is now its own project).

## What it is for

| Area | In short |
| --- | --- |
| **Analytics** | A Google Analytics-style portal over the whole platform: accounts, workspaces, access and sign-in history, sessions, pages, devices, countries, funnels (sign-up → first form → first response → paid), retention, usage (forms, responses, API calls, storage), revenue |
| **Workspaces and accounts** | Every workspace and person on Formalie: plan, status, usage, suspend / restore, change subdomain, sessions, reset two-step, support access (only with the workspace's consent, time-limited, audited) |
| **Subscriptions and payments** | Plans and prices, every subscription and payment, invoices, refunds through the processor, **manual activation or extension of a subscription** |
| **Help centre content** | Write and publish the help centre that Formalie's portal shows (articles, FAQs, glossary, videos, GIFs, guided tours) in all 20 languages, with feedback and "searched but not found" |
| **Formalie default data** | System lists, default folders, roles, email templates, system templates, themes and landing pages that every workspace receives (usable, locked) |
| **Platform settings** | Legal links, support links, branding on Formalie surfaces, feature switches, announcements and maintenance banners |
| **Operations** | Health of services and queues, error and request logs, security events, rate-limit hits |
| **Platform staff** | The Formalie team's own accounts, profiles, roles and permissions (granular, with approval steps for dangerous actions), and an audit trail of everything they do |

## Addresses

| | Development | Production (to decide) |
| --- | --- | --- |
| Platform admin (front end) | `https://platformadm.formalie.dev:2203` | `https://platformadm.formalie.com/`, a separate domain, or a separate IP |
| Platform API (backend) | `https://platformapi.formalie.dev:5601/` | `https://platformapi.formalie.com/` or a separate domain |

Development uses **mkcert** certificates; production always uses a valid certificate. See [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md).

## Stack (same as Formalie, no deviation)


- **Front end:** Nuxt 4.5 · Nuxt UI 4 · Tailwind CSS 4 · Vue 3.5 · TypeScript 6 (strict) · pnpm, with the same allowed extras as Formalie (zod, @vueuse, @nuxtjs/i18n, vue-draggable-plus, …).
- **Backend:** FastAPI on Python 3.11 · SQLAlchemy 2 · Alembic · Pydantic 2 · PostgreSQL 16 · PgBouncer · Redis 7 · RabbitMQ 3 + Celery (Beat) · S3-compatible storage (MinIO in development) · Nginx · systemd. No Docker: services are installed directly; production on AWS or dedicated servers ([docs/04-HOSTING.md](docs/04-HOSTING.md)).
- Same security model as Formalie (encrypted request envelope over TLS, Fernet tokens, CSRF, Argon2id, rate limits), with stricter rules for staff. See [docs/SECURITY-PROTOCOL.md](docs/SECURITY-PROTOCOL.md).

## Getting started

1. Put the contents of this folder at the root of `C:\UNETPROJECTS\formaliePlatformFront\`.
2. Open Claude Code there and paste the prompt from [STARTUP-PROMPT.md](STARTUP-PROMPT.md).
3. The Nuxt project is created in this same folder (next to `docs/`), following [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md), and runs on its mock layer until the backend is ready.
4. Work through [PROGRESS.md](PROGRESS.md) phase by phase, starting with P0.

## Folder map (before the Nuxt project is created)

```
formaliePlatformFront/
  README.md                      this file
  CLAUDE.md                      rules for every session
  STARTUP-PROMPT.md              the first prompt for Claude Code
  PROGRESS.md                    front end progress tracker (phases, tasks, logs)
  docs/
    00-OVERVIEW.md               product: who uses it, every module in detail
    01-ARCHITECTURE.md           the whole system, how it reaches Formalie
    02-DEV-ENVIRONMENT.md        hosts, certificates, ports, run commands, env
    03-DECISIONS-AND-NOTES.md    decisions and open questions
    04-HOSTING.md                production on AWS or dedicated servers, deploying a release
    API-CONTRACT.md              the platform API (v0 draft)
    SECURITY-PROTOCOL.md         envelope, staff sign-in, approvals, audit
    ERROR-CODES.md               PLT-* error codes
    ANALYTICS.md                 the Google Analytics-style part: events, metrics, reports
    FORMALIE-INTEGRATION.md      what Formalie's backend must provide, and how the two talk
    FRONTEND-SPEC.md             page map, navigation, shared components (front end only)
    design/                      design references (same look as Formalie)
```

Shared docs are the same files as in formaliePlatformBack; a change to one is made in both (see CLAUDE.md).

## Brand assets

- `docs/brand/`: the Formalie brand kit (logo, icons, favicon, manifest, OG image) with `BRAND.md`. Use these files as they are, see CLAUDE.md → Brand.

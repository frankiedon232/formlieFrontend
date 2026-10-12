# 01, Platform Admin Architecture

## High-level picture

```
Staff browser (Nuxt 4 platform admin, SPA)
   │  HTTPS (TLS) + app-layer encrypted envelope (SECURITY-PROTOCOL.md)
   ▼
Cloudflare / firewall (WAF, optional IP allowlist, TLS)          ← separate host from the portal
   ▼
Nginx (platform)
   ├── platformadm.formalie.com      → Nuxt (static SPA + Nitro server for the dev proxy only)
   └── platformapi.formalie.com      → Platform API: FastAPI cluster (stateless)
                                         ├── Platform PostgreSQL (primary + replica) via PgBouncer
                                         │      staff, roles, sessions, platform audit, analytics,
                                         │      help drafts, notes, approvals, reports
                                         ├── Platform Redis (sessions, nonces, rate limits, cache)
                                         ├── Platform RabbitMQ vhost + Celery workers / Beat
                                         ├── Platform object storage (help media drafts, exports)
                                         │
                                         ├──▶ Formalie READ replica (read-only role)      reads
                                         ├──▶ Formalie global tables (platform_writer role) writes, limited
                                         ├──▶ Formalie internal admin API (mTLS + signed)  actions
                                         └──◀ Formalie event bus (RabbitMQ, read-only queue) events
```

## Why a separate system

The platform admin can see and change everything, so it is kept apart from the customer portal: its own host (never a `*.formalie.com` workspace host, never shared cookies), its own database, its own staff accounts and secrets, its own deployment. If the portal is compromised the admin is not, and the other way round.

## The platform's own data (Platform PostgreSQL)

Owned only by the platform (DATA-MODEL.md in formaliePlatformBack): staff, profiles, roles and permissions, sessions, approvals, the platform audit trail, analytics events and rollups, saved reports, help content drafts and history, staff notes on workspaces, communications, support-access grants (mirror), settings drafts.

No tenant columns: this database is the platform's, not a workspace's. Row-Level Security is used for staff-level restrictions where a role sees only part of the data (for example a regional support role).

## How the platform reaches Formalie (FORMALIE-INTEGRATION.md has the full contract)

| Need | Path | Why |
| --- | --- | --- |
| Read anything for lists, details and analytics | **Formalie read replica**, role `platform_reader` (read-only, `BYPASSRLS` on the replica only, statement time-out, row caps) | Fast, no load on Formalie's primary, no write risk |
| Change a workspace, account, subscription, form state | **Formalie internal admin API** (`/internal/admin/v1/...` on Formalie's backend, private network, mTLS + HMAC-signed requests, idempotency keys) | Formalie keeps its own rules, caches, events and its own audit trail; one source of truth for business logic |
| Publish platform-owned global data (plans, default lists, help articles, platform settings, announcements, feature switches) | **Formalie global tables**, role `platform_writer` limited to those tables (no tenant tables), then an event `platform.published` so Formalie drops its caches | These tables belong to the platform; Formalie only reads them |
| Analytics stream | **Formalie event bus** (RabbitMQ exchange `formalie.events`), a read-only queue bound for the platform | Near real-time analytics without polling |

The platform never writes to Formalie's tenant tables directly. Every change made through the internal admin API carries the staff member's id, the approval id (if any) and the reason, so Formalie's own audit trail shows "Formalie support (name) did X" in the workspace.

## Service style

Like Formalie: a **modular monolith API plus independent workers**. Modules: auth, staff, rbac, approvals, audit, formalie_bridge (reader, admin client, publisher, event consumer), workspaces, accounts, support_access, subscriptions, payments, analytics (ingest, rollups, reports), help, defaults, settings, operations, communications. Heavy work (rollups, exports, scheduled reports, publishing to Formalie, broadcasts) runs in Celery workers.

## Analytics pipeline (ANALYTICS.md)

```
Formalie API / workers ──events──▶ RabbitMQ formalie.events ──▶ platform consumer (Celery)
                                                                  │ validate, drop personal fields,
                                                                  │ geo + device enrichment
                                                                  ▼
                                         platform analytics_events (partitioned by day)
                                                                  │ Celery Beat: every minute / hour / day
                                                                  ▼
                                  rollups (minute, hour, day) by metric × dimensions
                                                                  ▼
                                         reports, dashboards, explorer, exports
```

Realtime numbers read the last minutes of raw events from Redis counters; everything else reads rollups. Historical backfill reads Formalie's audit and request logs from the replica once.

## Request handling

1. Nginx passes the host; only `platformadm.*` / `platformapi.*` are served. Optional IP allowlist at the edge and again in the API.
2. Every request: envelope decrypt, expiry and replay checks, Fernet access token, CSRF on changes, rate limit.
3. Each call checks the staff member's permission (by address, then per item), runs in a transaction, writes its audit record in the same transaction.
4. Calls that need an approval create a pending approval instead of acting (SECURITY-PROTOCOL §6); the action runs when a second staff member approves.

## Environments

| | Dev | Production (to decide) |
| --- | --- | --- |
| Front end | `https://platformadm.formalie.dev:2203` | `https://platformadm.formalie.com/` or a separate domain / IP |
| API | `https://platformapi.formalie.dev:5601/` | `https://platformapi.formalie.com/` or a separate domain |
| Formalie API (to call) | `https://formalie.dev:5004/internal/admin/v1/` | Formalie's private network address, never public |
| Formalie replica | Formalie's local PostgreSQL (its dev database) | private network (AWS VPC peering / PrivateLink, or a private link / WireGuard between dedicated servers) |
| Hosting | the developer's machine, installed services, no Docker | AWS or dedicated servers (docs/04-HOSTING.md) |

## Scaling and resilience

Stateless API instances; PgBouncer; analytics tables partitioned by day with retention (raw events 13 months, rollups kept); rollups recomputable from raw; consumer is idempotent (event id dedup) and can replay from a cursor; the platform keeps working read-only if Formalie's internal API is down (actions queued with a clear "waiting for Formalie" state, never silently dropped).

# Backend Architecture (`formaliePlatformBack`, FastAPI)

Same conventions as `formlyBackend`. A modular monolith API plus Celery workers; each module owns its models, services, routes and events and can be split out later.

## Project layout

```
formaliePlatformBack/
  app/
    run.py                      FastAPI app factory, middleware order, routers
    core/
      config.py                 settings (pydantic-settings, .env)
      db.py                     async engines: platform primary / replica, formalie_reader, formalie_writer
      security/
        envelope.py             ECDH handshake, AES-GCM envelope (info "formalie-platform-envelope-v1")
        tokens.py               Fernet access / refresh / CSRF (platform keys)
        passwords.py            Argon2id, breached-password check (local list)
        totp.py                 RFC 6238, recovery codes
        ids.py                  encrypted id references (platform key)
        stepup.py               step-up confirmation (5 min)
      errors/
        codes.py                PLT-* codes (ERROR-CODES.md)
        handlers.py             one error shape, trace ids
      middleware/
        host.py                 only platformadm / platformapi hosts
        ipallow.py              staff IP allowlist
        envelope.py             decrypt / encrypt, expiry, replay
        ratelimit.py            Redis sliding window
        audit_context.py        request id, staff, IP → country / device
      permissions.py            catalogue, needs, permission_for(method, path)
      audit.py                  append-only, hash chain
      pagination.py             database paging, counts, cursors
    modules/
      auth/                     sign-in, TOTP, recovery, sessions, refresh, CSRF
      staff/                    profiles, invitations, activation, my profile
      rbac/                     roles, grants, checks
      approvals/                request, approve, reject, execute (dispatch to modules)
      audit/                    platform audit trail list, verify chain, export
      formalie_bridge/
        reader.py               read-only queries on Formalie's replica (one place)
        admin_client.py         internal admin API client (mTLS, HMAC, idempotency, retries)
        publisher.py            writes to Formalie global tables + platform.published event
        consumer.py             formalie.events consumer (Celery)
      workspaces/               lists, detail, actions (via admin_client), notes, tags
      accounts/                 people across Formalie, actions, reveal
      support_access/           requests, sessions (consent from Formalie)
      subscriptions/            plans (drafts, publish), subscriptions, billing actions
      payments/                 payments, invoices, refunds (read + actions)
      analytics/
        ingest.py               validation, enrichment, batch writes
        rollups.py              minute / hour / day, sessions, daily snapshots
        reports.py              report queries (rollups only), explorer, exports, schedules
        backfill.py
      help/                     categories, articles, versions, translations, media, publish, feedback
      defaults/                 default lists, folders, email templates, catalogue changes, publish
      settings/                 platform settings, feature flags, announcements (drafts, publish)
      operations/               health, queues, failed jobs, error / request logs, security events
      communications/           messages, audiences, scheduling, sending via admin_client
    workers/
      celery_app.py             queues: ingest, rollups, publish, actions, reports, exports, mail
      beat.py                   schedules (rollups, audit chain check, report schedules, retention)
    cli.py                      seed-owner, rotate-keys, backfill, verify-audit
  migrations/                   Alembic
  tests/                        pytest, mirrors app/
  requirements.txt · .env.example
```

## Request pipeline (middleware order)

host check → IP allowlist → rate limit → envelope decrypt (+ expiry, replay) → auth (Fernet) → CSRF (changes) → permission by address → route → per-item permission → service (transaction + audit) → envelope encrypt.

## Layers in each module

- `routes.py`: FastAPI router, Pydantic request / response models, no business logic.
- `service.py`: business rules, permission per item, approval check, audit write, transaction.
- `models.py`: SQLAlchemy 2 models (platform database).
- `queries.py`: read queries (platform DB or `formalie_bridge.reader`).
- `events.py`: events the module publishes on the platform bus.

## Data access rules

- Platform DB: the API's role has DML on its tables, **insert only** on `audit_log` and `analytics_events`.
- Formalie reads only through `formalie_bridge.reader` (one place, reviewed queries, statement time-out, row caps, paging in the database, never `SELECT *` on tables with personal data).
- Formalie changes only through `formalie_bridge.admin_client`; global tables only through `formalie_bridge.publisher`.
- No ORM lazy loading in routes; explicit queries; async throughout (asyncpg).

## Approvals flow

`service.request(action, params, reason)` → if the action needs approval: store `approvals` row, audit `approval.requested`, return `202 { approval }`; else execute. `approvals.approve(id)` checks the approver ≠ requester, has the permission, step-up fresh, not expired → executes the same service function with `approval_id` → audit both. Execution through Formalie goes via `pending_actions` with retries when Formalie is unavailable.

## Jobs (Celery)

| Queue | Jobs |
| --- | --- |
| `ingest` | consume `formalie.events`, batch insert, realtime counters |
| `rollups` | minute / hour / day rollups, sessions, daily snapshots, recompute |
| `publish` | help, defaults, plans, settings, flags, announcements → Formalie global tables |
| `actions` | pending Formalie admin calls with retry / backoff |
| `reports` | scheduled reports (email to staff), exports |
| `mail` | staff invitations, sign-in notices, report emails (platform SMTP) |
| `maintenance` | audit chain verification, partition creation and retention, key rotation reminders |

## Observability

Structured JSON logs with request ids (no secrets, no personal data), error log table + alerts, metrics (request rate, latency, errors, queue depth) exposed for the operations module, health endpoint `/api/health` (plaintext) and `/api/v1/operations/health` (staff).

## Testing

pytest + pytest-asyncio; unit tests per service; API tests through the envelope; a fake Formalie (admin API stub + replica fixture database) for bridge tests; permission matrix tests (every route × role); audit chain tests; analytics rollup tests with fixed events.

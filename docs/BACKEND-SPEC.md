# Backend Specification, formlyBackend (Formalie API)

Updated 2026-10-10 after the frontend was finished. The frontend's mock (`C:/UNETPROJECTS/formalieFrontend/server/mock`) is the reference implementation; `ENDPOINTS.md` lists every route and `FRONTEND-REFERENCE.md` the rules to port.

## 1. Request pipeline (pure ASGI middleware, in this order)

1. **RequestContext**, `trace_id` (UUIDv7, returned as `X-Trace-Id`), start time, real client IP (trust `X-Forwarded-For`/`CF-Connecting-IP` only from Nginx), user agent.
2. **SecurityHeaders**, HSTS, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, frame rules.
3. **RateLimit (IP tier)**, cheap rejection before any decryption.
4. **Tenant**, resolve subdomain from `X-Forwarded-Host`/`Host` → tenant (L1 → Redis → DB). Unknown/suspended → error. `manage` host → platform context.
5. **Envelope**, verify `kid`, `ts` (±60 s), nonce (Redis `SET NX`), decrypt AES-GCM, check bound method+path, replace body/query; encrypt response.
5b. **References**: decrypt every encrypted reference in the route params, query and body back to its id; reject a bad tag before any lookup, and never accept a raw id (SECURITY-PROTOCOL §10). Responses encrypt every id on the way out.
6. **Auth dependency** (per route, not middleware), Fernet bearer decrypt with TTL, session deny-list check, tenant/org match with subdomain, MFA flag, loads principal.
7. **CSRF dependency** on state-changing routes.
7b. **Permission dependency**: the role's grant for the action and its scope against the item (§11).
8. **RateLimit (user/tenant/route tier).**
9. **DB session**, opens transaction on primary or replica, sets RLS context.
10. **RequestLog** (on response), publishes log event to the logging queue (file fallback if the broker is down).

## 2. Tenancy and RLS

- Model: shared DB + shared schema + `tenant_id` + `organisation_id`.
- Roles: `formalie_owner` (migrations only), `formalie_app` (runtime, `NOBYPASSRLS`), `formalie_readonly` (replicas/reporting), `formalie_platform` (tenant directory lookups only).
- For each tenant table:
  ```sql
  ALTER TABLE forms ENABLE ROW LEVEL SECURITY;
  ALTER TABLE forms FORCE ROW LEVEL SECURITY;
  CREATE POLICY forms_isolation ON forms
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid
           AND organisation_id = current_setting('app.organisation_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid
           AND organisation_id = current_setting('app.organisation_id', true)::uuid);
  ```
  If the setting is missing, `current_setting(..., true)` returns NULL and **no rows match** (fail closed).
- Session setup per transaction: `SELECT set_config('app.tenant_id', :t, true), set_config('app.organisation_id', :o, true), set_config('app.user_id', :u, true)`, transaction-local, safe with PgBouncer transaction pooling.
- Tenant lookup by subdomain before tenant context exists uses a `SECURITY DEFINER` function `platform.resolve_tenant(subdomain)` returning only public fields.
- Composite foreign keys `(tenant_id, parent_id) → parent(tenant_id, id)` make cross-tenant references impossible at the DB level.
- Alembic helper `enable_tenant_rls(table)` used in every migration that creates a tenant table; CI test asserts every table with `tenant_id` has RLS forced.

## 3. Database read/write segregation

- Two async engines: `primary` (writes) and `replica` (list, search, reports, analytics, exports). Multiple replicas behind PgBouncer or round-robin.
- `get_session(intent="read"|"write")` dependency. **Read-your-writes:** after a write, the user is pinned to the primary for 5 s (Redis flag `rw:{user_id}`).
- asyncpg behind PgBouncer transaction mode: disable prepared statement cache (`statement_cache_size=0`, unique prepared statement names).
- Pool sizes per instance from settings; `pool_pre_ping`; statement timeout per role (e.g. 15 s app, 120 s reports).

## 4. Caching tiers

- **L1** in-process TTL cache (seconds): tenant directory, feature flags.
- **L2** Redis (minutes–hours): tenant public profile, published form versions, themes, option sets, permission sets, plan limits, analytics counters, short links.
- Keys: `fm:v1:t:{tenant_id}:{module}:{id}:{version}`. Cache-aside; invalidation via domain events; stampede protection with short locks; never cache secrets.
- Target: absorb the bulk of read traffic (public form loads, lookups) so the primary handles writes.

## 5. Event-driven processing

- RabbitMQ topic exchange `formalie.events`; routing keys `domain.action` (`form.published`, `response.created`, `export.requested`, `user.invited`, `auth.login_succeeded`, `security.suspicious_request`, `billing.payment_paid`, `api.call`, `datasource.write_failed`…). Events for the platform admin are listed in PLATFORM-ADMIN-INTEGRATION.md §4 (personal data stripped)..
- Event envelope: `{event_id, type, occurred_at, tenant_id, organisation_id, actor_id, trace_id, payload, version}`.
- Celery queues (separate worker services): `notifications` (email/SMS/OTP), `destinations`, `webhooks`, `exports`, `analytics`, `files`, `logs`, `scheduled` (Beat: form open/close schedules, cleanup, partitions, backups checks).
- Idempotent consumers (store processed `event_id`), retries with exponential backoff, dead-letter queues, outbox table for events published inside DB transactions (`event_outbox` → relay).

## 6. Security coverage

- Data isolation: RLS + composite FKs + explicit filters + tests.
- MFA: OTP on every login; TOTP option; enforced for all admin roles.
- Encryption: TLS everywhere (client→Nginx→API, API→Postgres `sslmode=verify-full`, Redis TLS, RabbitMQ TLS in prod); app-layer envelope; encryption at rest (disk/volume encryption + column-level encryption with MultiFernet for secrets such as customer DB credentials, webhook secrets, TOTP secrets).
- Tokens: per SECURITY-PROTOCOL.md; key rotation via MultiFernet.
- CSRF with expiry; OAuth state/nonce/PKCE.
- Rate limiting everywhere; account lockout with backoff; bot protection on public submit (Turnstile/hCaptcha) and honeypot fields.
- Input validation (Pydantic strict), output encoding, upload scanning (ClamAV worker), MIME sniffing, size limits.
- Daily backups: continuous WAL archiving + daily full backup (pgBackRest), encrypted, off-site, 30-day retention, monthly restore drill.
- Secrets in environment/secret manager, never in code.

## 7. Authentication flows

- Email/password signup on manage.\* → OTP → create tenant + organisation + admin user + subdomain (transaction) → issue tokens.
- Workspace single sign-on (`/settings/sso`: SAML or OIDC, test, switch on / off; mock `routes/sso.ts`).
- OAuth (Google, Microsoft, Apple, Facebook) via Authlib; per-tenant provider configs (client id/secret encrypted) shown on that tenant's login page; OAuth login still requires OTP unless the tenant enables IdP-MFA trust.
- Find-my-workspace: email → OTP → list of tenants → redirect.
- Sessions table (device, IP, geo, last seen) with remote revoke.

## 8. Logging, errors, audit

### 8.1 Request logs (`request_logs`, partitioned monthly)

trace_id, timestamp (UTC, ms), tenant_id, organisation_id, user_id, session_id, method, path, route template, query (masked), status, duration_ms, request/response size, client IP, country, region/state, city, timezone, lat/long (approx), ASN/ISP, user agent, parsed device/OS/browser, referer, origin, host/subdomain, client app & version header, **body summary** (content type, size, SHA-256, top-level keys, field count, first 512 chars with sensitive keys masked, flags: oversized, malformed, invalid envelope, SQLi/XSS/path-traversal patterns, replay attempt), rate-limit hits, error code.
Geo: MaxMind GeoLite2 City + ASN databases (auto-updated weekly by a Celery Beat job); Cloudflare headers used when present.

### 8.2 Audit trail (`audit_logs`, partitioned monthly)

Who (user, role, impersonation), what (action, entity type, entity id), before/after diff (masked), when, where (IP + geo), how (endpoint, trace_id, client), result. Recorded for every create/update/delete/publish/share/export/login/permission change. Immutable (no update/delete grants).

### 8.3 Errors (`error_logs` + files)

- Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (emergency). Separate files per level: `logs/{level}/{YYYY-MM-DD}.log`, daily rotation, 90-day local retention, shipped to central storage.
- Every entry: timestamp, level, error code, message, trace_id, tenant/org/user, endpoint, input summary, stack trace (server only), what the user was doing (route + action), environment, release version.
- Central DB table for search in an admin console later; CRITICAL also alerts (email/Slack).
- API error response (never leaks internals):
  ```json
  {
    "success": false,
    "error": {
      "code": "FRM-AUTH-1003",
      "message": "Invalid or expired code.",
      "trace_id": "…",
      "details": []
    }
  }
  ```

## 9. Optimisation checklist

Tenant-leading composite indexes `(tenant_id, organisation_id, …)` · partial indexes on `deleted_at IS NULL` · GIN on JSONB response data and full-text columns · keyset pagination for large lists (offset only for small) · `EXPLAIN ANALYZE` reviews for every new heavy query · connection pooling (PgBouncer) · partitioning (responses by month with tenant index; logs by month) · read replicas · Redis caching · async I/O everywhere · Celery offloading · horizontal FastAPI scaling (stateless) · response compression (gzip/brotli at Nginx) · materialised analytics rollups refreshed by workers · archival of old partitions · slow-query logging and pg_stat_statements · load tests (k6/Locust) before launch.

## 10. Subscription, plans and payments (F24)

- **Plans:** from `shared/utils/billing/plans.ts`: Starter (free), Professional, Business, Enterprise (contact us), billed Monthly, Quarterly or Annually.
- **Limits:** services check limits and features (the mock's `requireFeature`, `requireFormSlot` and `requireDatabase` in `core/plan.ts`): live forms, responses per month, seats, storage, own-database engines, data residency, SSO and own sending domain. **No custom CSS** in any plan (owner, 2026-10-10).
- **Processor:** **Payoneer**, with every money rule in SECURITY-PROTOCOL §11:
  - the server decides the amount;
  - request keys;
  - one billing change at a time;
  - one open checkout;
  - payments saved as pending first;
  - states only move forward;
  - only the signed webhook confirms a payment;
  - daily reconciliation;
  - refunds by staff only.

  Mock: `routes/billing.ts`, `routes/billingCheckout.ts`, `billing/*`.
- **Usage counters:** kept in Redis, saved to the database daily.

## 11. Roles, permissions and scope (F16 / F22)

- **Catalogue:** `shared/utils/auth/permissions.ts` (areas, groups, actions). A grant carries a scope: Own, Shared, Own & shared or All (None = not granted). Owner is built in, holds everything and can't be changed.
- **Two checks on every route:** first the permission for the address, then the action against the item (who made it, whom it is shared with, which folder it's in). Form sharing (edit / view / responses) never goes beyond the role. Mock: `data/formPermissions.ts`, `data/resourceAccess.ts`, `data/rolesStore.ts`.
- **Partly visible lists:** filtered in the query, never after paging.

## 12. Audit trail (F4, first-class)

- **What's recorded:** every change and every sign-in event, with the action keys in `shared/utils/audit/events.ts`: actor, IP, device, request id, before / after with masking, severity and outcome. Mock: `core/audit.ts`. Search, filters and export: `routes/audit.ts`.
- **When:** built in the same phase as sign-in. Every later module writes to it as part of its definition of done.

## 13. Public forms (F10)

- **Links:** `/{formKey}/fill` and `/{formKey}/embed` on `forms.formalie.*` or the workspace subdomain, and `/s/{code}` short links (01-ARCHITECTURE → Public URLs). Nuxt renders them on the server through an internal endpoint, guarded by a server-only token (`x-formalie-internal`).
- **Submit:**
  - validation with the ported rules (`forms/submission.ts`, logic, formula);
  - proof of work (`forms/proof-of-work.ts`);
  - availability: schedule, limits, one response per person, invites;
  - save and resume;
  - pre-signed uploads with virus scanning.

## 14. API service (F13)

- **Service:** a separate service on `api.formalie.*` with its own deployment and rate limits. Plain HTTPS + JSON, without the envelope (SECURITY-PROTOCOL §9).
- **Protections:**
  - tokens, static or client credentials;
  - optional HMAC signing;
  - access rules: IP, Origin, country, and anonymous networks via GeoIP;
  - allowed websites for CORS;
  - scopes and least data;
  - idempotent POST (`Formalie-Key`);
  - traffic logs.
- **Order of checks:** in ENDPOINTS.md. Mock: `publicApi.ts`, `routes/api*.ts`.

## 15. Data sources and response storage (F12)

- **Connections:** a workspace connects its own databases (engines in `shared/utils/datasources/engines.ts`, limited by plan). Credentials are encrypted with MultiFernet, and connections go out through an allow-listed egress.
- **Response storage:** responses go into **Formalie's own prefixed tables** in that database (DDL from `datasources/ddl.ts`), written by Celery workers with retries. Other tables are optional.
- **Tools:**
  - **Explorer:** browse and edit rows.
  - **Query editor:** read-only by default, statement checks from `datasources/sql.ts`, time and row limits, saved queries.
  - **Activity log.**

## 16. AI assistant (F19)

- **Kinds:** listed in `shared/utils/ai/kinds.ts` (create, assist, analyse, write, translate…).
- **Control:** switched on per workspace, with an allowance per plan (`requireAi`). Every request is audited and can be removed.
- **Provider:** the mock's local engines (`server/mock/ai/*`) are replaced by the chosen provider, with the same shapes.
- **Personal data:** answers containing personal data are only sent when the workspace allows it.

## 17. Emails, sending and notifications

- **Templates:** email templates per workspace (defaults in the mock's `data/emailDefaults/`), with preview, test and a sent log.
- **Sending:** as the Formalie address, from an own domain (DNS records checked), or through the workspace's SMTP. All sending goes through Celery.
- **Notifications:** in-app notifications per person.

## 18. Settings, privacy and residency

Settings sections are validated with `shared/utils/settings/schemas.ts`. They cover:
- **Appearance:** light / dark colours, default mode, fonts.
- **Address:** subdomain change, own domain.
- **Security:** sessions, IP allowlist, idle timeout.
- **Privacy:** retention with a preview; requests to find, export or delete a person's data.
- **Data region:** `shared/utils/platform/regions.ts` (Enterprise).

## 19. Platform admin bridge

The platform admin is a separate system (formaliePlatformFront / formaliePlatformBack). This backend provides for it:
- database roles and the global tables;
- an internal admin API with mTLS and HMAC;
- support access, with the workspace's consent;
- events.

The task list is in PLATFORM-ADMIN-INTEGRATION.md §5.

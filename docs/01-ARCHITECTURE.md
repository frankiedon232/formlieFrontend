# 01 — Formalie Architecture

## High-level picture

```
Browser (Nuxt 4 portal / public form renderer)
   │  HTTPS (TLS) + app-layer encrypted envelope (see SECURITY-PROTOCOL.md)
   ▼
Cloudflare (DNS, wildcard *.formalie.com, WAF, DDoS, TLS)
   ▼
Nginx (TLS, reverse proxy, routes by host and path, forwards X-Forwarded-Host)
   ├── /            → Nuxt (SSR/SPA) for {subdomain}.formalie.com and manage.formalie.com
   └── /api/        → FastAPI cluster (N instances, stateless)
                         ├── PostgreSQL primary (writes)  ──replication──▶ read replicas (reads)
                         │        via PgBouncer (transaction pooling)
                         ├── Redis (cache tiers, rate limits, nonces, sessions, pub/sub)
                         ├── RabbitMQ (event bus / Celery broker)
                         └── Object storage (S3-compatible, tenant-aware paths)
Celery workers (separate services per queue): exports, destinations, webhooks, email/OTP,
analytics aggregation, logging pipeline, file processing, scheduled jobs (Celery Beat)
```

**Same-origin API:** in production the API is served at `https://{sub}.formalie.com/api/...` or seperate API URL like `https://api.formalie.com/....` through Nginx, so browser requests are same-origin (simpler CSRF/cookies, no CORS). In development, Nuxt proxies `/api` to `https://formalie.dev:5004` (see 02-DEV-ENVIRONMENT.md).

## Service style

Start as a **modular monolith API + independent worker services** connected by RabbitMQ events. Each domain module (auth, tenancy, forms, responses, exports, destinations, logging, billing) owns its models, services and events, so any of them can be split into its own microservice later without rewrites. Heavy or slow work is never done in the request: the API publishes an event and returns.

## Tenancy model (mandatory)

**Shared database + shared schema + `tenant_id` + `organisation_id`.** Not schema-per-tenant, not database-per-tenant.

- **Tenant** = the subscribing account, identified by its subdomain (billing and isolation boundary).
- **Organisation** = an organisation unit inside a tenant (the first one is created at signup; tenants on higher plans may have several, e.g. subsidiaries or branches).
- Every table holding tenant data carries `tenant_id` and `organisation_id`, enforced by **PostgreSQL Row-Level Security** plus application-level filters (defence in depth).
- Global platform tables (countries, states, currencies, timezones, plans, system templates, permissions catalogue, error codes) have no tenant columns.
- Tenant isolation follows the data everywhere: DB rows, cache keys (`t:{tenant_id}:...`), file paths (`tenants/{tenant_id}/orgs/{organisation_id}/...`), queue messages, logs, exports, search indexes.

## Subdomain flow

| URL                                                | Role                                                                                                                                                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manage.formalie.com`                              | Default entry. Sign up (creates tenant + subdomain + first admin), sign in for users who forgot their subdomain ("find my workspace" by email → redirect), auto-redirect to known subdomain |
| `{company}.formalie.com`                           | Tenant workspace: login page shows that tenant's branding and enabled auth providers; portal; public forms                                                                                  |
| `{company}.formalie.com/{formKey}/fill` · `/embed` | Published public form (workspaces with their own subdomain)                                                                                                                                 |
| `forms.formalie.com/{formKey}/fill` · `/embed`     | Published public form (workspaces without their own subdomain)                                                                                                                              |
| `api.formalie.com/{apiKey}/{endpoint}`             | API service endpoints built from forms (F13)                                                                                                                                                |
| `forms.formalie.com/s/{code}`                      | Short link → redirects to the form                                                                                                                                                          |
| `formalie.com`                                     | Product website (separate project)                                                                                                                                                          |

## Public URLs (decided 2026-10-03)

| What                              | Development (now)                                      | Production                                             |
| --------------------------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| Form link — no own subdomain      | `https://forms.formalie.dev/{formKey}/fill`            | `https://forms.formalie.com/{formKey}/fill`            |
| Form embed — no own subdomain     | `https://forms.formalie.dev/{formKey}/embed`           | `https://forms.formalie.com/{formKey}/embed`           |
| Form link / embed — own subdomain | `https://{sub}.formalie.dev/{formKey}/fill` · `/embed` | `https://{sub}.formalie.com/{formKey}/fill` · `/embed` |
| API service endpoint              | `https://api.formalie.dev/{apiKey}/{endpoint}`         | `https://api.formalie.com/{apiKey}/{endpoint}`         |

- `{formKey}`: the form's short public key (random, 10 letters / digits; a custom slug may replace it, unique per host). Never a database id. Public keys never clash with portal routes (reserved words).
- `{apiKey}`: a short random public handle per organisation (10 letters / digits). It is **not** the tenant / organisation id and is **not** encrypted — see 03-DECISIONS → 61. The backend maps it to tenant + organisation; tokens are bound to the same organisation.
- `{endpoint}`: lower-case words with hyphens (`register-account`); `/{recordId}` is appended for GET one, PUT and DELETE.
- `forms` and `api` are reserved subdomains (`shared/utils/tenant/host.ts`); every link is built by `shared/utils/urls/public.ts`. In local development the Nuxt dev port is added (`:2202`).
- The API service runs as its own backend service (own deployment, scaling and rate limits), separate from form operations; both write through the same response pipeline.

Request handling:

1. Nginx passes the host; FastAPI **TenantMiddleware** extracts the subdomain, looks it up (Redis cache → DB), rejects unknown/suspended subdomains (`FRM-TEN-1001`).
2. **Never trust the subdomain alone.** After authentication, the token's `tenant_id`/`organisation_id` must match the subdomain's tenant, otherwise `FRM-TEN-1003` and the attempt is logged as a security event.
3. Each DB transaction sets `app.tenant_id`, `app.organisation_id`, `app.user_id` so RLS policies apply.

Reserved subdomains (cannot be registered): `www, manage, api, app, admin, mail, static, cdn, docs, status, help, support, blog, s, auth, login, billing, dev, staging, test`.

## Data flow examples

**Publish a form:** API validates draft → creates immutable `form_versions` row → updates form status → invalidates Redis cache → emits `form.published` → workers warm public cache, generate OG image, update short link.

**Submit a response:** public renderer fetches published version (Redis cached) → submits encrypted envelope → API validates against schema, rate limits, spam check → writes response (primary) → emits `response.created` → workers: destinations (own DB/webhook/email), analytics counters, notifications.

**Export:** API creates `export_jobs` row → emits `export.requested` → worker builds XLSX/CSV/PDF to tenant-aware storage path → notifies user → signed, expiring download URL.

## Scaling

Stateless FastAPI instances behind Nginx (horizontal scale); PgBouncer; primary + read replicas with read/write routing; Redis tiers; Celery queues scaled independently; partitioned high-volume tables (responses, request logs, audit logs, error logs); CDN for static assets and public form assets.

# Formalie Integration (what Formalie provides, how the two talk)

The platform admin reads Formalie through its read replica, changes Formalie through an internal admin API, writes only the platform-owned global tables, and listens to Formalie's events. Everything here must exist in **formlyBackend** before the platform's bridge phases (PROGRESS P4 onward). Copy the "Formalie tasks" list at the end into Formalie's PROGRESS when its backend work starts.

## 1. Database access

### `platform_reader` (read-only)

- On Formalie's **read replica** only. `SELECT` on every table the platform lists or analyses (tenants, organisations, users, memberships, roles, sessions, sign-in attempts, forms, form versions (metadata only), responses (counts and timestamps, **not answers**), files (sizes only), data source connections (metadata), API service objects (metadata), subscriptions, invoices, payments (processor references, amounts, status), audit logs, request logs, error logs, global tables).
- `BYPASSRLS` on the replica (it reads across tenants), `statement_timeout = 15s`, `default_transaction_read_only = on`, connection limit.
- Column-level privileges exclude secrets (password hashes, TOTP secrets, recovery hashes, connection credentials, token hashes, webhook secrets) and answer content (`responses.data`, file contents).

### `platform_writer` (global tables only)

`INSERT`, `UPDATE` (no `DELETE`; retire with a flag) on the platform-owned **global** tables, none of which have tenant columns:

| Table (Formalie) | What the platform manages |
| --- | --- |
| `platform_settings` | legal links, support links, status page, branding on Formalie surfaces, reserved subdomains |
| `feature_flags` | switches per plan, per workspace, percentage rollout |
| `announcements` | portal banners and maintenance notices (audience, period, 20 languages) |
| `plans`, `plan_prices`, `plan_limits` | the plan catalogue |
| `system_option_lists`, `system_option_items` | Formalie's default lists (simple and with levels, translations, Large) |
| `system_folders` | default folders |
| `system_email_templates` | default email templates (20 languages) |
| `system_templates`, `system_themes`, `system_page_designs` | catalogue items (publish, retire) |
| `help_categories`, `help_articles`, `help_article_translations`, `help_faqs`, `help_glossary`, `help_tours` | published help centre |

After writing, the platform publishes `platform.published { table, ids, version }` on the bus; Formalie drops its caches for those keys. Every write carries `published_by_staff_id` and `published_at`.

## 2. Internal admin API (Formalie backend)

- Base `/internal/admin/v1`, on Formalie's private network only (never through the public Nginx), mutual TLS with the platform's client certificate, HMAC-SHA256 signing (`X-Platform-Key-Id`, `X-Platform-Timestamp`, `X-Platform-Nonce`, `X-Platform-Signature` over method, path, timestamp, nonce and body hash; 5-minute window; nonce replay check).
- Every change sends `X-Platform-Staff-Id`, `X-Platform-Staff-Name`, `X-Platform-Approval-Id` (when approved), `X-Platform-Reason` and `Idempotency-Key`. Formalie records the action in **its** audit trail as `platform_support` with these values, so the workspace sees what Formalie staff did.
- Responses: Formalie's normal `{ success, data, error }` shapes, plain JSON over mTLS (no browser envelope).

| Method | Path | Does |
| --- | --- | --- |
| POST | `/tenants/{id}/suspend` · `/restore` | Suspend (reason shown to the workspace) or restore |
| POST | `/tenants/{id}/subdomain` | Change subdomain (old one redirects for 30 days) |
| POST | `/tenants/{id}/read-only` · `/close` · `/cancel-close` | Read-only mode; close with a deletion date; undo |
| POST | `/tenants/{id}/plan` | Change plan / limits / trial end (from the platform's subscription actions) |
| POST | `/tenants/{id}/export` | Start a full data export for the workspace (download for the workspace owner) |
| POST | `/users/{id}/sign-out` | End every session |
| POST | `/users/{id}/two-step/reset` · `/password-reset` · `/disable` · `/enable` · `/unlock` | Account actions |
| POST | `/subscriptions/{id}/activate` · `/extend` · `/credit` · `/cancel` | Manual subscription actions (also tells the processor where needed) |
| POST | `/payments/{id}/refund` | Refund through the processor |
| POST | `/support-access/requests` | Ask a workspace for support access (owner gets a notice) |
| POST | `/support-access/{grant_id}/session` | Start a consented, time-limited, read-only support session; returns a one-time ticket for a support view |
| POST | `/communications/send` | Send a message to workspace owners / admins through Formalie's email and in-app notifications |
| POST | `/cache/invalidate` | Drop caches for global tables (fallback when the bus is down) |
| GET | `/health/services` | Health of Formalie's services, queues and workers (operations module) |

## 3. Support access (consent in Formalie)

Formalie's portal gets (Settings → Security → Formalie support access): "Allow Formalie support to view this workspace" with duration (1 h, 24 h, 7 days), read-only by default, optional write; requests from Formalie appear as a notice the owner approves or declines; an active support session shows a banner to everyone in the workspace; every support action is in the workspace's audit trail. The platform only starts a support session against an active grant.

## 4. Events (Formalie → platform)

Formalie publishes on RabbitMQ exchange `formalie.events` (topic). The platform binds a durable queue `platform.analytics` with routing keys below. Every event: `{ id (uuid), type, occurred_at, tenant_ref, organisation_ref, actor_ref, session_ref, source: portal|public|api|worker, country, region, city, device, browser, os, language, plan, properties }`, **never answers, passwords, tokens or full IPs**.

| Routing key | When |
| --- | --- |
| `auth.signed_in` · `auth.sign_in_failed` · `auth.signed_out` · `auth.two_step_used` | Every sign-in attempt and result |
| `session.page_viewed` | Portal page views (path template, not ids), for engagement |
| `tenant.signed_up` · `tenant.setup_completed` · `tenant.suspended` · `tenant.closed` | Workspace lifecycle (sign-up with UTM source / referrer) |
| `user.invited` · `user.joined` · `user.approved` · `user.disabled` | People |
| `form.created` · `form.published` · `form.closed` · `form.deleted` | Forms |
| `response.created` | One per response (form ref, channel, duration, no answers) |
| `export.completed` · `destination.failed` · `webhook.failed` | Operations |
| `api.called` (sampled or aggregated per minute) | API service usage |
| `subscription.*` · `payment.*` · `invoice.*` | Billing (from F24) |
| `feature.used` | Named feature uses (builder, designer, AI, data explorer …) |

Delivery: at least once; the platform deduplicates by `id`. Formalie keeps 7 days of events for replay.

## 5. Formalie tasks (add to Formalie's backend plan)

- [ ] Database roles `platform_reader` (replica) and `platform_writer` (global tables) with the privileges above, created by migrations.
- [ ] Global tables listed in §1, read by the portal with caching and invalidation on `platform.published`.
- [ ] Internal admin API (§2) with mTLS, HMAC signing, idempotency and `platform_support` audit entries.
- [ ] Support access consent in Settings → Security, support session tickets, banner (§3).
- [ ] Event publishing on `formalie.events` (§4), personal data stripped.
- [ ] Health endpoint for the operations module.
- [ ] Portal screens read announcements, feature flags, platform settings and help articles from the global tables (most already exist as mocks: legal links, default lists).

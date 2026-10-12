# Formalie Integration (what Formalie provides, how the two talk)

The platform admin reads Formalie through its read replica, changes Formalie through an internal admin API, writes only the platform-owned global tables, and listens to Formalie's events. Everything here must exist in **formlyBackend** before the platform's bridge phases (PROGRESS P4 onward). Copy the "Formalie tasks" list at the end into Formalie's PROGRESS when its backend work starts.

## 1. Database access

### `platform_reader` (read-only)

- On Formalie's **read replica** only. `SELECT` on every table the platform lists or analyses (tenants, organisations, users, memberships, roles, sessions, sign-in attempts, forms, form versions (metadata only), responses (counts and timestamps, **not answers**), files (sizes only), data source connections (metadata), API service objects (metadata), subscriptions, invoices, payments (processor references, amounts, status), audit logs, request logs, error logs, global tables).
- `BYPASSRLS` on the replica (it reads across tenants), `statement_timeout = 15s`, `default_transaction_read_only = on`, connection limit.
- **Request logs** (`formaly.request_logs`, BACKEND-SPEC §8.1): every request with headers, location, device and flags, for traffic analytics and investigations. The body columns (`request_body`, `request_body_text`, `response_body`) are excluded because answers can sit in them.
- **Error logs** (`formaly.error_logs`, BACKEND-SPEC §8.3): warning, error and critical lines of every process with level, error code, security event, trace id, workspace, user, method, path, stack and context; search by `trace_id` to match a request log.
- Column-level privileges exclude secrets (password hashes, TOTP secrets, recovery hashes, connection credentials, token hashes, webhook secrets) and answer content (`responses.data`, file contents).
- **Built (B16, migration 0034):** `platform_reader` has column privileges on every table of `formaly` and `platform` (never table-wide), without any column ending in `_hash` or `_enc` and without: `responses.data / identity_email / respondent_email / respondent_name`, `resume_drafts.data / email`, `response_changes.before / after`, `response_notes.text`, the bodies of `request_logs`, `api_request_logs`, `webhook_deliveries` (`logged_body`, `response`) and `api_idempotency.answer`, `sent_emails.html / text`, `ai_requests.prompt / result / output`, `query_history.sql`, `saved_queries.sql`, `forms.draft_schema`, `form_versions.schema` (metadata only), `custom_domains.token`. The list lives in `app/modules/platform_bridge/grants.py`; every later tenant table gets the same rule from `enable_tenant_rls()`, and `tests/db/test_platform_grants.py` fails when a secret or answer column becomes readable or any write privilege appears. `scripts/db_bootstrap.py` gives both roles LOGIN when `DB_PLATFORM_READER_URL` / `DB_PLATFORM_WRITER_URL` carry their passwords (reader: 10 connections, read only, 15 s statements; writer: 5 connections).

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
| `help_categories`, `help_articles`, `help_article_translations`, `help_faqs`, `help_faq_translations`, `help_glossary`, `help_glossary_translations`, `help_tours`, `help_tour_translations` | published help centre (shape fixed in B14, below) |

**Help centre tables (B14, migration 0033; schema `platform`, text ids such as `first-form`).** Structure once, words per language (`language` is one of the 20 codes; English is the source and the fallback):

| Table | Columns the platform writes |
| --- | --- |
| `help_categories` | key (one of `HELP_CATEGORIES`), sort |
| `help_articles` | id, category, route (page pattern, `/forms/:id/build`, or null), related text[] (article ids), start_order ("New here?" order or null), popular, minutes, sort, retired_at |
| `help_article_translations` | (article_id, language), title, summary, keywords text[], blocks jsonb (`HelpBlock[]`, shared/types/help.ts). `body` and `search` are generated: never written |
| `help_faqs` · `help_faq_translations` | id, category, article_id, sort, retired_at · (faq_id, language), question, answer (`search` generated) |
| `help_glossary` · `help_glossary_translations` | id, article_id, sort, retired_at · (term_id, language), term, definition (`search` generated) |
| `help_tours` · `help_tour_translations` | id, route, targets text[] (the `data-help` controls, in step order), sort, retired_at · (tour_id, language), title, steps jsonb `[{ title, text }]` in the targets' order |

Every one also has `created_at`, `updated_at` (set it when publishing: articles show the later of the article's and the translation's), `published_at` and `published_by_staff_id`. Retire with `retired_at` (no deletes). Formalie's seeder never overwrites a row with `published_by_staff_id` set. The platform reads (with `platform_reader`) what people send back: `formaly.help_feedback` (tenant table: tenant, person, article, language, helpful, comment, one row per person and article) and `platform.help_search_misses` (language, query_norm, count, first_at, last_at). After publishing help tables, send `platform.published` with the table names; Formalie drops its help cache (`app/modules/platform/published.py`).

After writing, the platform publishes `platform.published { table, ids, version }` on the bus; Formalie drops its caches for those keys. Every write carries `published_by_staff_id` and `published_at`.

**The other global tables (B16, migration 0034; schema `platform`).** Every one has `created_at`, `updated_at`, `published_at`, `published_by_staff_id`; all but the translation, price and limit tables have `retired_at`. A trigger (`platform.stamp_published`) refuses an insert or update by `platform_writer` without `published_by_staff_id` and stamps `published_at = now()` and `updated_at`. Rows shipped by Formalie have `published_by_staff_id` empty.

| Table | Key · columns the platform writes | Read by Formalie |
| --- | --- | --- |
| `platform_settings` | key · value jsonb, description. Keys: `legal` `{ terms_url, privacy_url }`, `support` `{ email, url }`, `egress_ips` `[ip, ...]`, `status_page` `{ url }` (more keys may be added: branding) | Yes. A row published by staff wins (an object fills in what it leaves out from the server's value); shipped rows mirror the server's `.env` values, which keep answering until the platform publishes |
| `reserved_subdomains` | subdomain (lower case) · reason | Yes: sign-up, subdomain availability, Settings → Address and the internal subdomain change refuse them (on top of the host rules' own list) |
| `feature_flags` | key · description, enabled, plans text[] (empty: every plan), tenant_ids uuid[], rollout_percent 0 to 100 | Yes: on for listed workspaces; otherwise the plan must be listed and the workspace inside the percentage (stable hash of key and workspace). Portal: `GET /platform/feature-flags` |
| `announcements` · `announcement_translations` | id · kind (`banner`, `maintenance`, `news`), tone (`info`, `warning`, `critical`), audience (`all`, `plans`, `tenants`), plans, tenant_ids, starts_at, ends_at, link_url, dismissible · (announcement_id, language), title, body | Yes: `GET /platform/announcements` (showing now, this workspace, the reader's language, else English) |
| `plans` · `plan_prices` · `plan_limits` · `plan_features` | id · currency, recommended, sort · (plan_id, period `monthly` / `quarterly` / `annually`), amount · plan_id, forms, responses_per_form, databases text[], sso, custom_domains, custom_email, data_residency, ai_credits, languages (null: no limit) · (plan_id, feature) | Shipped from the frontend's plans; the portal switches its reads to these with B15 (subscriptions) |
| `system_option_lists` · `system_option_items` | key · name, description, levels, columns, large, sort · (list_key, value), label, level, parent_value, translations, attrs, sort_order, active | Shipped (Formalie's sample lists); read when default lists move to the database (B17) |
| `system_folders` | key · name_key, color, sort | Empty: new workspaces start without folders, like the mock's |
| `system_email_templates` | (key, language) · subject, body | Shipped (20 languages); read when default emails move to the database (B17) |
| `system_templates` · `system_template_translations` | key · category, icon, tags, minutes, design, schema (FormSchema v1), sort · (template_key, language), name, description, content | Shipped (English names; the other languages come from Formalie's dictionaries); read with B17 |
| `system_themes` · `system_page_designs` | key · name_key, tokens (the preset's theme patch), sort | Shipped; read with B17 |

How Formalie caches them: Redis keys `fm:v1:platform:global:{table}:...` (10 minutes); `platform.published` (consumer `python -m app.modules.platform_bridge.consumer`, durable queue `formalie.platform_published` bound to `formalie.events` with routing key `platform.published`, dead letters to `formalie.dlx`) or `POST /internal/admin/v1/cache/invalidate` drop them at once. The message may be `{ table, ids, version }`, `{ tables: [...], version }`, or the same inside `properties` / `payload`; help tables are handed to the help centre's cache.

## 2. Internal admin API (Formalie backend)

- Base `/internal/admin/v1`, on Formalie's private network only (never through the public Nginx), mutual TLS with the platform's client certificate, HMAC-SHA256 signing (`X-Platform-Key-Id`, `X-Platform-Timestamp`, `X-Platform-Nonce`, `X-Platform-Signature` over method, path, timestamp, nonce and body hash; 5-minute window; nonce replay check).
- Every change sends `X-Platform-Staff-Id`, `X-Platform-Staff-Name`, `X-Platform-Approval-Id` (when approved), `X-Platform-Reason` and `Idempotency-Key`. Formalie records the action in **its** audit trail as `platform_support` with these values, so the workspace sees what Formalie staff did.
- Responses: Formalie's normal `{ success, data, error }` shapes, plain JSON over mTLS (no browser envelope).

**Built (B16).** `app/modules/platform_bridge/` (`internal.py` the gate, `admin_routes.py` the routes, `signing.py` the reference signer). Settings: `PLATFORM_ADMIN_KEYS` (`key_id:secret`, comma separated, secrets of 32 characters or more), `PLATFORM_ADMIN_WINDOW_SECONDS` (300), `PLATFORM_ADMIN_NETWORKS` (private ranges), `PLATFORM_ADMIN_REQUIRE_MTLS` (always on in production: otherwise every call is refused), `PLATFORM_ADMIN_CERT_FINGERPRINTS`, `PLATFORM_ADMIN_VERIFY_HEADER` / `_FINGERPRINT_HEADER`.

*Mutual TLS.* Nginx on the private listener only: `ssl_verify_client on; ssl_client_certificate <the platform's CA>;`, `proxy_set_header X-Client-Verify $ssl_client_verify;` and `proxy_set_header X-Client-Cert-Fingerprint $ssl_client_fingerprint;`. `PLATFORM_ADMIN_CERT_FINGERPRINTS` lists the platform certificate's fingerprint exactly as Nginx passes it (hex; colons and case ignored). Formalie believes these headers only from `TRUSTED_PROXIES` and needs `SUCCESS` plus a listed fingerprint.

*Signing (headers).* `X-Platform-Key-Id`, `X-Platform-Timestamp` (Unix seconds), `X-Platform-Nonce` (16 to 64 of `A-Z a-z 0-9 _ -`, used once), `X-Platform-Signature: v1=<hex HMAC-SHA256(secret, canonical)>`. Changes (POST) also send `X-Platform-Staff-Id` (64), `X-Platform-Staff-Name` (200, percent-encoded UTF-8), `X-Platform-Reason` (1000, percent-encoded), `X-Platform-Approval-Id` (optional) and `Idempotency-Key` (8 to 200 of `A-Z a-z 0-9 _ . : -`).

*Canonical string* (lines joined with `\n`; a header not sent is an empty line): `FORMALIE-PLATFORM-V1`, METHOD (upper case), the path as sent with `?query` when there is one, the timestamp, the nonce, the hex SHA-256 of the raw body (also for an empty body), then the staff id, staff name (still percent-encoded), approval id, reason (still percent-encoded) and idempotency key. The staff headers are signed, so the name in the workspace's audit trail is the one the platform signed.

*Order of checks and answers:* keys configured (and mTLS required in production) → `403 FRM-SEC-1007`; private network → `FRM-SEC-1007`; client certificate → `FRM-SEC-1007`; signing headers present → `400 FRM-SEC-1005`; known key → `FRM-SEC-1007`; timestamp within the window → `400 FRM-SEC-1002`; signature → `FRM-SEC-1005`; nonce new (Redis; Redis down → `503 FRM-GEN-5003`) → `400 FRM-SEC-1003`; staff headers on a change → `422 FRM-GEN-1002` (details name the headers). Unknown routes answer `404 FRM-GEN-1004` only after the signature.

*Idempotency.* The same key and the same request (method, path, body) answers the first answer again with `Idempotent-Replayed: true`; the same key with another request: `409 FRM-BILL-1005`; while the first is still running: `409 FRM-GEN-1009` (`details: in_progress`); a first attempt that failed with a 5xx runs again. Every call is logged in `platform.admin_calls` (who, path, status, the workspace; the answer encrypted for replays).

*Audit.* Changes to a workspace are written to its audit trail as actor type `platform_support` (name `Formalie support (<staff name>)`, `staff_id`, `staff_name`, `approval_id` columns; the workspace's audit list shows them as Formalie under the staff member's name), with `metadata.via = platform_admin`, `metadata.platform_action` (the path) and `metadata.staff_reason`. The frontend's audit catalogue has no keys of their own for these yet, so they use: `workspace.updated` (status, plan, limits, trial; support requests and sessions issued; messages), `settings.updated` (subdomain), `settings.data_exported` (export), `users.signed_out`, `users.two_step_reset`, `users.password_requested`, `users.disabled`, `users.enabled`, `users.updated` (unlock).

*Ids* are Formalie's own UUIDs as text, the same the platform reads from the replica (this is a server channel; browsers never see them).

| Call | Body | Answer `data` |
| --- | --- | --- |
| `POST /tenants/{id}/suspend` | `{ reason }` (500; shown on the workspace's sign-in page as `status_reason`) | TenantAdmin: `{ id, subdomain, name, status, status_reason, plan_id, plan_limits, trial_ends_at, close_at, data_region, setup_completed_at, created_at }`. Ends live support sessions. Event `tenant.suspended` |
| `POST /tenants/{id}/restore` | none (from `suspended` or `read_only`, else `409 FRM-GEN-1009`) | TenantAdmin |
| `POST /tenants/{id}/read-only` | `{ reason }` | TenantAdmin. People sign in, look and export; changes answer `403 FRM-PERM-1001` with `details: [{ field: "workspace", message: "read_only" }]` (their own profile, notifications, billing and support access still work) |
| `POST /tenants/{id}/close` | `{ reason, close_at }` (at least a day ahead) | TenantAdmin (`status: closing`, read only until then). Event `tenant.closed`. Deleting on the date: B17 |
| `POST /tenants/{id}/cancel-close` | none (from `closing`) | TenantAdmin |
| `POST /tenants/{id}/subdomain` | `{ subdomain }` | TenantAdmin. The old one keeps leading to the workspace for 90 days. `409 FRM-TEN-1004` with `invalid`, `reserved` or `taken` |
| `POST /tenants/{id}/plan` | `{ plan_id?, limits?, trial_ends_at? }`; `limits` keys: forms, responses_per_form, databases, sso, custom_domains, custom_email, data_residency, ai_credits, languages; `null` clears limits or trial | TenantAdmin (limits stored on the workspace; enforced with B15) |
| `POST /tenants/{id}/export` | none | `{ export_id, status, file_name }`. A ZIP of JSON files (settings, people without secrets, roles, organisation, folders, forms and versions, responses, lists, themes, page designs, saved fields, templates); the Owners get "Your export is ready" with a one-time link valid 7 days |
| `POST /users/{id}/sign-out` · `/password-reset` · `/disable` | none | `{ id, tenant_id, status, must_change_password, sessions_ended, changed }`; password-reset asks for a new password at the next sign-in and signs out; disable signs out |
| `POST /users/{id}/two-step/reset` · `/enable` · `/unlock` | none | the same; unlock clears the sign-in and forgotten-password limits on the person's address |
| `POST /subscriptions/{id}/activate` · `/extend` · `/credit` · `/cancel`, `POST /payments/{id}/refund` | per the platform | Until B15: `404 FRM-GEN-1004`, `details: [{ field: "subscription" or "payment", message: "billing_not_available_yet" }]` |
| `POST /support-access/requests` | `{ tenant_id, reason, mode: read or write, hours: 1, 24 or 168 }` | `{ request_id, status: "pending", expires_at }`; the workspace's admins get an in-app notice (event `support_request`) |
| `POST /support-access/{grant_id}/session` | `{ mode? }` (`write` only on a write grant: `403 FRM-PERM-1001 grant_read_only`; no active grant: `not_active`) | `{ session_id, ticket, mode, ticket_expires_at, ends_at, tenant: { id, subdomain }, redeem_url }` (`https://{sub}.formalie.dev/support#ticket=...`) |
| `POST /communications/send` | `{ tenant_ids? (500 at most), plans?, to: owners or admins, channels: [email, in_app], subject: { lang: text }, body: { lang: text }, link_url? (https), essential }` (English required) | `{ workspaces, emails, notices }`. Each person in their language, else the workspace's, else English; non-essential emails respect Unsubscribe; in-app notice event `platform_message` |
| `POST /cache/invalidate` | `{ table }` or `{ tables: [...] }`, `version?` | `{ tables }` the caches dropped |
| `GET /health/services` | none (no staff headers needed) | `{ status: ok, degraded or down, checked_at, release, environment, services: [{ name, status, latency_ms, ... }] }`: `database_primary`, `database_replica_N`, `redis`, `rabbitmq` (`queues: [{ name, waiting, workers, dead }]`), `event_outbox` (`waiting`, `retrying`, `oldest_age_seconds`; degraded past 60 s) |

| Method | Path | Does |
| --- | --- | --- |
| POST | `/tenants/{id}/suspend` · `/restore` | Suspend (reason shown to the workspace) or restore |
| POST | `/tenants/{id}/subdomain` | Change subdomain (old one keeps working for 90 days, 03-DECISIONS F14 M7) |
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

**Built (B16).** Tables `support_access_grants`, `support_access_requests`, `support_sessions` (tenant tables, RLS forced). The flow:

1. The workspace allows it (or approves Formalie's request): a grant with a mode and an end. Changing it extends or changes the open grant in place; turning it off revokes it and ends every support session at once.
2. The platform calls `POST /support-access/{grant_id}/session` and gets a one-time ticket (valid `SUPPORT_TICKET_SECONDS`, 120). The staff member's browser opens `redeem_url` (`https://{sub}.formalie.dev/support#ticket=...`: the ticket is in the fragment, never sent to a server or kept in logs); the portal page posts it to `POST /api/v1/auth/support/redeem` and gets a support token that lasts until the session's end (the grant's end or `SUPPORT_SESSION_MINUTES`, 60, whichever is first). There is no refresh: a new session needs a new ticket.
3. In the session: what the workspace's Owner can see; changes only when both the grant and the session are `write` (else `403 FRM-PERM-1001 read_only`). Never: the staff member's own profile (`/me/...`), the consent itself, privacy requests, single sign-on settings, revealing secrets. What the session makes belongs to the Owner's account; the audit trail says `Formalie support (<name>)`. Nobody is added to People.
4. Everyone in the workspace sees the banner (`GET /api/v1/support-access/status`, also `support_session` in `GET /me`).
5. Expiry: access stops at the end by itself; a Beat job every minute closes grants, sessions and unused tickets and expires requests nobody answered (`SUPPORT_REQUEST_DAYS`, 7), with audit entries.

Audit: the consent (`settings.updated`, by the person), Formalie's request and each session issued (`workspace.updated`, Formalie support), the session's sign-in (`auth.login.succeeded`, method `support`), its end (`auth.logout`, or `auth.session.revoked` by the system on expiry), and every change in a write session. Pages a session viewed are in the request log (`user_id` is the Owner's, `session_id` the support session's).

## 4. Events (Formalie → platform)

Formalie publishes on RabbitMQ exchange `formalie.events` (topic). The platform binds a durable queue `platform.analytics` with routing keys below. Every event: `{ id (uuid), type, occurred_at, tenant_ref, organisation_ref, actor_ref, session_ref, source: portal|public|api|worker, country, region, city, device, browser, os, language, plan, properties }`, **never answers, passwords, tokens or full IPs**.

| Routing key | When |
| --- | --- |
| `auth.signed_in` · `auth.sign_in_failed` · `auth.signed_out` · `auth.two_step_used` | Every sign-in attempt and result. `properties.method`: `password`, `google`, `facebook` (social sign-in, Formalie's own apps; `microsoft` only in events before 2026-10-12), `sso` (the workspace's own single sign-on) or `signup_handoff` (first sign-in after creating a workspace) |
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

**Built (B16).** Every message on `formalie.events` has this shape (the outbox relay writes it, `app/core/events/wire.py`): `{ id, type, occurred_at, tenant_ref, organisation_ref, actor_ref, session_ref, source, country, region, city, device, browser, os, language, plan, properties, version, trace_id }`. References are Formalie's UUIDs as text; country / region / city come from the address, which never leaves. `properties` of the listed types carry only their own keys:

| Type | properties |
| --- | --- |
| `auth.signed_in` · `auth.two_step_used` | method, channel (`email`, `totp`, `sms`) |
| `auth.sign_in_failed` | method, reason (`FRM-*` code), outcome (`failure`, `blocked`) |
| `auth.signed_out` | none |
| `tenant.signed_up` | plan, method (`password`, `google`, `facebook`) |
| `tenant.setup_completed` | none |
| `tenant.suspended` · `tenant.closed` | previous_status, status · previous_status, close_at |
| `user.invited` · `user.joined` · `user.approved` · `user.disabled` | user_id (invited also counts profiles an admin made) |
| `form.created` · `form.published` · `form.closed` · `form.deleted` | form_id |
| `response.created` | form_id, response_id, channel (`link`, `embed`, `api`), submitted_at (source `public` or `api`) |
| `export.completed` | export_id, kind, format, rows, bytes |
| `destination.failed` | destination_id, failed, sent (per delivery batch) |
| `webhook.failed` | webhook_id, delivery_id, attempts, status_code (after the last retry) |
| `api.called` | endpoint_id, service_id, method, status, duration_ms, token_mode, sample_rate (`PLATFORM_EVENTS_API_SAMPLE`, 1 = every call) |
| `feature.used` | feature (`ai`, `query_editor`, `data_explorer`, `designer`, `page_designer`, `templates`, `response_exports`, `api_service`, `webhooks`, `destinations`) |

Every event, listed or not, loses keys that carry personal data or content (email, name, phone, ip, data, answers, body, text, message, password, token, secret, code ...) and any text that looks like an email address or an IP address; objects never pass. A support session's sign-in is not counted as a sign-in. Not sent yet: `session.page_viewed` (needs a call from the portal, which has none today) and `subscription.*`, `payment.*`, `invoice.*` (B15).

## 5. Formalie tasks (add to Formalie's backend plan)

- ✅ Database roles `platform_reader` (replica) and `platform_writer` (global tables) with the privileges above, created by migrations (B16, 0034; CI test `tests/db/test_platform_grants.py`).
- ✅ Global tables listed in §1, read by the portal with caching and invalidation on `platform.published` (help: B14; the rest and the bus consumer: B16). Plans and the default catalogues are shipped into their tables; the portal reads plans from them with B15 and the default lists, emails, templates, themes and page designs with B17.
- ✅ Internal admin API (§2) with mTLS, HMAC signing, idempotency and `platform_support` audit entries (B16; subscriptions and payments answer "not available yet" until B15).
- ✅ Support access consent in Settings → Security, support session tickets, banner (§3): backend built in B16; the portal screen and the `/support` ticket page are the frontend's to build.
- ✅ Event publishing on `formalie.events` (§4), personal data stripped (B16; `session.page_viewed` waits for a portal call, billing events for B15).
- ✅ Health endpoint for the operations module (B16).
- ✅ Portal reads platform settings (legal links on public forms, outgoing addresses on Data sources, the support contact for the help centre), reserved subdomains, announcements and feature switches from the global tables (B16); help articles (B14). The portal screens for announcements and switches are the frontend's to build.

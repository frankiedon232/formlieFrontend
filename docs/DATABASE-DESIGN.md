# Database Design, Formalie (PostgreSQL 16)

Rewritten 2026-10-10 from the finished portal (`C:\UNETPROJECTS\formalieFrontend`): entity shapes in `shared/types/*.ts`, catalogues in `shared/utils/**`, per-workspace stores in `server/mock/data/*.ts`, and `docs/API-CONTRACT.md`, `OPTION-LISTS.md`, `03-DECISIONS-AND-NOTES.md`, `SECURITY-PROTOCOL.md`. Global tables and DB roles for the platform admin follow `formaliePlatformBack/docs/FORMALIE-INTEGRATION.md`. Columns listed are the key ones, not full DDL. Dropped since the first draft: `form_collab_docs` (live collaboration removed, F20), custom CSS (removed, L5).

## Conventions

- IDs: `uuid` (UUIDv7, generated in app) everywhere. Names: snake_case, plural tables. Enums are `text` with a `CHECK` (values listed below come from the frontend catalogues).
- **Tenant mixin** (all tenant tables): `tenant_id uuid not null`, `organisation_id uuid not null`, composite unique `(tenant_id, id)` for composite FKs, **RLS enabled and FORCED**. Policy: `tenant_id = current_setting('app.tenant_id')::uuid`; the API sets `app.tenant_id` / `app.organisation_id` per transaction (`SET LOCAL`).
- **Audit mixin:** `created_at timestamptz default now()`, `updated_at`, `created_by uuid`, `updated_by uuid`.
- **Soft delete mixin:** `deleted_at timestamptz null`, `deleted_by uuid null`. Default queries exclude deleted rows. Uniques are partial `WHERE deleted_at IS NULL`. Forms in Trash are purged after 30 days (`TRASH_RETENTION_DAYS`).
- **Optimistic locking:** `row_version int not null default 1` on editable entities (forms, roles, themes, page designs, lists, settings sections, destinations); a stale version → `FRM-GEN-1009`.
- FKs: `ON DELETE RESTRICT` (never cascade). Tenant-aware: `FOREIGN KEY (tenant_id, form_id) REFERENCES forms (tenant_id, id)`.
- Timestamps in UTC; the person's or workspace's time zone and date format are applied in presentation.
- Large JSON in `jsonb`; GIN indexes only where queried.
- **Encrypted references (SECURITY-PROTOCOL §10):** no database id leaves the server. Every id in a response is an AES-256 block plus a 4-byte HMAC tag (27 chars, base64url), decrypted at the API edge; the keys live in the secret manager, never in the database. Public addresses use separate random keys (`forms.public_key`, short codes, API keys), never ids.
- **Secrets:** columns ending `_enc` are envelope-encrypted (KMS data key, versioned). Tokens, passwords, codes and recovery codes are stored only as hashes (`_hash`: Argon2id for passwords, SHA-256 for random tokens). Write-only in the API.
- **Built-in items:** rows that come from Formalie (`source = 'system'` or a `system_key`) are use-only in every workspace; the API refuses edit and delete.

## DB roles

| Role | Grants |
| --- | --- |
| `formalie_owner` | Owns the schema; used only by migrations (Alembic). |
| `formalie_app` | API and Celery workers. `NOBYPASSRLS`; CRUD on tenant tables, `SELECT` on global tables, `INSERT` only on log tables (`audit_logs`, `request_logs`, `error_logs`, `api_request_logs`, `form_fill_events`). Cannot list `tenants` except through `platform.resolve_tenant(host)` (SECURITY DEFINER). |
| `platform_reader` | Read replica only. `BYPASSRLS`, `default_transaction_read_only = on`, `statement_timeout = 15s`, connection limit. Column privileges exclude secrets (`*_hash`, `*_enc`, TOTP secrets, recovery codes, connection credentials, webhook secrets) and answer content (`responses.data`, file contents, `resume_drafts.data`). |
| `platform_writer` | `INSERT`, `UPDATE` (no `DELETE`; retire with `retired_at`) on the platform-owned global tables marked **(P)** below. Every write carries `published_by_staff_id`, `published_at`; then `platform.published { table, ids, version }` on the bus drops Formalie's caches. |

## Platform / global tables (schema `platform`, no tenant, no RLS)

Source: `shared/utils/platform/*`, `shared/utils/billing/plans.ts`, `shared/utils/auth/permissions.ts`, `shared/utils/audit/events.ts`, `server/mock/data/platformStore.ts`, `helpStore.ts`, `emailDefaults/`, `help/`.

| Table | Key columns |
| --- | --- |
| `countries` | code (ISO-2), currency (ISO 4217); names come from `Intl` in the viewer's language |
| `currencies`, `timezones` | code; IANA zone |
| `languages` | code (the 20 portal and form languages of `shared/utils/i18n/locales.ts`), rtl, is_active |
| `data_regions` | code (`default`, `eu`, `uk`, `us`, `ca`, `au`, `in`, `sg`, `br`), name, is_active |
| `plans` **(P)** | id (`starter`, `professional`, `business`, `enterprise`), currency, recommended, sort, retired_at |
| `plan_prices` **(P)** | plan_id, period (`monthly`, `quarterly`, `annually`), amount numeric(12,2); none = "Contact us" (Enterprise) |
| `plan_limits` **(P)** | plan_id, forms, responses_per_form, databases text[], social_signin, sso, custom_domains, custom_email, data_residency, ai_credits, languages (null = no limit) |
| `plan_features` **(P)** | plan_id, feature (`PLAN_FEATURES`: analytics, templates, lists, themes, explorer, query, destinations, api, webhooks, apiDocs, ai, branding, subdomain, languages, visits, versions, folders, fillLater, socialSignin, sso, customDomain, customEmail, dataResidency, prioritySupport, dedicatedSupport, securityReview) |
| `permissions` | code (`forms.publish`, `data.query_write` …), area, group, scopes text[] (`own`, `shared`, `own_shared`, `all`; empty = on/off), needs text[] (`PERMISSION_NEEDS`). Mirror of the catalogue, seeded by migration |
| `audit_event_types` | action (`forms.published` …), area (`auth`, `workspace`, `forms`, `responses`, `settings`, `users`, `integrations`, `api`, `data`, `ai`, `audit`), severity |
| `error_codes` | code (`FRM-*`), http_status, message_key |
| `platform_settings` **(P)** | key, value jsonb: legal (terms_url, privacy_url), support (email, url), egress_ips (shown on Data sources), status page, branding on Formalie surfaces |
| `reserved_subdomains` **(P)** | subdomain, reason |
| `feature_flags` **(P)** | key, enabled, plans text[], tenant_ids uuid[], rollout_percent, retired_at |
| `announcements`, `announcement_translations` **(P)** | audience (all / plans / tenants), kind (banner, maintenance), starts_at, ends_at; language, title, body |
| `system_option_lists` **(P)** | key, name_key, description_key, levels jsonb, columns jsonb, large bool, retired_at |
| `system_option_items` **(P)** | list_id, level, parent_value, value, label, translations jsonb, attrs jsonb, sort_order, active |
| `system_folders` **(P)** | key (operations, customers, compliance, marketing, leads, projects), name_key, color, sort |
| `system_email_templates` **(P)** | key (`signin_code`, `password_reset`, `invitation`, `response_notification`, `response_receipt`, `notification`, `daily_digest`), language, subject, body |
| `system_templates`, `system_template_translations` **(P)** | key, category, icon, tags, minutes, schema jsonb (FormSchema v1); language, name, description, content jsonb |
| `system_themes`, `system_page_designs` **(P)** | key, name_key, tokens jsonb, retired_at |
| `help_categories` **(P)** | key (`HELP_CATEGORIES`: start, forms, builder, design, templates, sharing, responses, analytics, lists, data, api, people, settings, audit, ai), sort |
| `help_articles`, `help_article_translations` **(P)** | id, category, route, related text[], keywords text[], start_order, popular, minutes, updated_at; language, title, summary, blocks jsonb (`HelpBlock[]`: p, h, steps, list, tip / note / warning, show, media) |
| `help_faqs`, `help_glossary` **(P)** | category, article_id, per language question / answer or term / definition |
| `help_tours` **(P)** | id, route pattern (`/forms/:id/build`), per language title, steps jsonb (target, title, text) |
| `help_feedback` | article_id, tenant_id, user_id, helpful, comment, at; one row per person and article (written by Formalie, read by the platform) |
| `help_search_misses` | language, query_norm, count, last_at |
| `billing_webhook_events` | event_id (unique), type (`payment.succeeded`, `payment.failed`, `payment.refunded`), received_at, tenant_id (resolved from the payment reference), outcome, payload jsonb. Each event handled once |

## Tenant directory (schema `platform`, restricted)

Source: `server/mock/data/tenants.ts`, `addressStore.ts`, `shortCodeStore.ts`, `formStore.ts` (`findByPublicKey`, `findByShortCode`), `routes/dataRegion.ts`.

| Table | Key columns |
| --- | --- |
| `tenants` | id, subdomain (unique, lowercase), name, status (`active`, `suspended`, plus `read_only`, `closing` for platform actions), suspended_reason, close_at, primary_organisation_id, data_region (default `default`; changed only by a platform migration), plan_id (mirror of the subscription), created_at, setup_completed_at, deleted_at |
| `tenant_subdomain_history` | tenant_id, subdomain, until (the old one keeps working 90 days; unique while active) |
| `tenant_domains` | tenant_id, domain (unique), status (`pending`, `verified`, `failed`), records jsonb (`DnsRecord[]`), verify_token, problem (`not_found`, `wrong_target`, `dns_error`), added_at, checked_at |
| `public_form_routes` | public_key (10 chars, unique), custom_link (unique on the shared `forms.*` host), tenant_id, form_id. Lets `forms.*` find the workspace from a key |
| `short_link_codes` | code (unique), tenant_id, form_id, retired_at. A retired code is never reused, even after the form is purged |
| `api_keys_directory` | api_key (unique, path part of `api.formalie.*/{apiKey}/…`), tenant_id, previous_key, previous_until |
| `signup_tickets` | ticket_hash, tenant_id, user_id, expires_at (2 min), used_at (cross-host sign-up and social sign-up tokens) |

Access only through `platform.resolve_tenant()`, `platform.resolve_form_key()` and platform services; `formalie_app` cannot list tenants.

## Tenant tables (tenant_id + organisation_id + RLS)

### Identity and sessions

Source: `shared/types/auth.ts`, `profile.ts`, `server/mock/data/peopleStore.ts`, `tenants.ts` (`MockUser`), `core/auth.ts`, `routes/auth.ts`, `routes/me.ts`.

| Table | Key columns |
| --- | --- |
| `organisations` | name, legal_name, is_primary (company details live in `workspace_settings.company`) |
| `users` | email (unique per tenant, lower), first_name, last_name, phone, photo_upload_id, status (`active`, `not_activated`, `invited`, `pending`, `disabled`), role_id, manager_id, password_hash, password_changed_at, must_change_password, language, time_zone, date_format (null = workspace's), notifications jsonb (`responses`, `digest`, `mentions`, `product`), request_via (`invite`, `link`), requested_at, joined_at, last_active_at, deleted_at |
| `user_password_history` | user_id, password_hash, created_at (for `security.password.reuse_last`) |
| `user_identities` | user_id, provider (`google`, `microsoft`, `apple`, `facebook`, `sso`), provider_user_id, email |
| `user_two_step` | user_id, totp_secret_enc, totp_confirmed_at, sms_phone_enc, sms_confirmed_at |
| `user_recovery_codes` | user_id, code_hash, used_at (ten per set; a new set replaces the old) |
| `user_sessions` | user_id, started_at, last_active_at, ip, device jsonb (type, browser, os), city, country, revoked_at |
| `refresh_tokens` | session_id, family_id, token_hash, issued_at, expires_at, used_at, revoked_at, replaced_by. Reuse → family revoked (`FRM-AUTH-1012`) |
| `otp_challenges` | user_id or email, purpose (`login`, `signup`, `reset`, `find_workspace`, `phone_verify`), channel (`email`, `sms`, `totp`), code_hash, attempts, max_attempts, resend_after, expires_at, consumed_at |

Session encryption keys (ECDH) and access tokens are not stored in PostgreSQL (Redis with TTL; Fernet tokens are checked against `user_sessions.revoked_at`). Sign-in attempts, lockouts and blocked IPs are `audit_logs` rows (area `auth`), which feed Settings → Security activity.

### People, roles and access

Source: `shared/types/people.ts`, `org.ts`, `shared/utils/auth/permissions.ts`, `server/mock/data/rolesStore.ts`, `orgStore.ts`, `signupLinkStore.ts`, `formPermissions.ts`, `resourceAccess.ts`.

| Table | Key columns |
| --- | --- |
| `roles` | name, description, built_in (`owner`, `admin`, `member` or null), grants jsonb (`{ "forms.edit": "own_shared", "people.manage": "all" }`: scope per action, a missing action = None), row_version. Owner is fixed; one role per person (`users.role_id`) |
| `org_units` | kind (`departments`, `job_titles`), name, code, description, archived_at; unique (tenant_id, kind, lower(name)) while active |
| `org_unit_members` | org_unit_id, user_id |
| `user_invites` | user_id, kind (`invite`, `activation`), token_hash, sent_at, expires_at (7 days), invited_by, message, revoked_at. A new link replaces the old one |
| `signup_links` | one per tenant: enabled, token_enc (shown again in People, so encrypted, not hashed), domains text[], updated_at. A new link stops the old |
| `folder_access` | folder_id, restricted, role_ids uuid[], org_unit_ids uuid[], user_ids uuid[] |
| `form_grants` | form_id, user_id, level (`responses`, `view`, `edit`), granted_at; `forms.team_access` holds the workspace default |
| `user_tours` | user_id, tours_off, seen text[] (tour ids from `help_tours`) |

Access is computed per request (role scope, maker, form grants, folder access) and returned as `can`; nothing is denormalised.

### Forms and versions

Source: `shared/types/forms.ts`, `shared/utils/forms/schema.ts`, `server/mock/data/formStore.ts`, `forms.ts`, `formSeo.ts`, `libraryStore.ts` (saved fields).

| Table | Key columns |
| --- | --- |
| `folders` | name, color (`FOLDER_COLORS` key or `#rrggbb`), system_key (seeded defaults, locked), created_by, deleted_at |
| `forms` | folder_id, name, slug (unique per tenant), public_key, custom_link, status (`draft`, `published`, `closed`, `archived`), previous_status, draft_schema jsonb (FormSchema v1: pages, logic, calculations, theme tokens, theme_id, page_design_id, translations, settings, thank_you), published_version_id, has_unpublished_changes, template_key, owner_id, tags text[], channels text[] (`link`, `embed`, `api`), access (`public`, `password`, `invite`, `organisation`), password_hash, password_version, password_changed_at, response_limit, opens_at, closes_at, embed_domains text[], team_access (`edit`, `view`, `none`), seo jsonb (title, description, image_upload_id, noindex), responses_count, next_response_number, row_version, published_at, closed_at, archived_at, deleted_at |
| `form_versions` | form_id, number, schema jsonb, published_by, published_at, change_summary, fields_count. **Immutable** |
| `form_field_refs` | form_id, scope (`draft`, `live`), field_key, ref_type (`option_list`, `department`, `job_title`), ref_id, in_sync. Derived index rebuilt on draft save and publish; answers list usage, org-unit usage and "live forms follow the list" |
| `saved_fields` | name, field jsonb (a field without id), created_by |

### Design: themes, page designs, fonts, appearance

Source: `shared/types/forms.ts` (`SavedTheme`, `PageDesign`), `shared/utils/forms/theme.ts`, `page-design.ts`, `fonts.ts`, `shared/types/appearance.ts`, `libraryStore.ts`.

| Table | Key columns |
| --- | --- |
| `themes` | name, source (`saved`, `created`), tokens jsonb (`FormTheme`), created_by, row_version, deleted_at. System themes are `system_themes`; forms keep a copy of the tokens in their schema |
| `page_designs` | name, source (`saved`, `created`), tokens jsonb (`PageDesignTokens`), created_by, row_version, deleted_at |

Fonts are a fixed self-hosted catalogue in the frontend (`fonts.ts`), referenced by key in tokens; no table. Portal appearance is `workspace_settings.appearance`. No custom CSS anywhere.

### Templates

Source: `shared/types/templates.ts`, `server/mock/data/templateStore.ts`, `libraryStore.ts` (`WorkspaceTemplate`).

| Table | Key columns |
| --- | --- |
| `workspace_templates` | name, description, category, icon, schema jsonb, source_form_id, created_by, deleted_at. Formalie's catalogue is `system_templates`; usage counts come from `forms.template_key` |

### Lists (option sets)

Source: `shared/types/forms.ts` (`OptionList`, `OptionItem`), `docs/OPTION-LISTS.md`, `server/mock/data/libraryStore.ts`, `largeLists.ts`, `shared/utils/forms/options.ts`.

| Table | Key columns |
| --- | --- |
| `option_lists` | name, description, levels jsonb (2 to 4 named levels, null = plain), columns jsonb (up to 10 detail columns), large bool, system_list_key (seeded copy, locked), active_count, level_counts int[], created_by, row_version, deleted_at |
| `option_items` | list_id, level (0 = top), parent_value, value, label, score, active (retired items stay for old answers), translations jsonb, attrs jsonb (detail values), sort_order. Unique (list_id, level, parent_value, value) |

Standard lists hold up to 20,000 options, Large lists up to 200,000. Lists with more than 20 active options, and every Large list, are never copied into forms: forms reference them (`option_set_id`, `option_level`, `option_parent`) and the public page loads one level at a time for the choice above, searched as people type. Lists of 20 or fewer are copied into the schema and updated with Update forms.

### Sharing, links, invites, embed

Source: `shared/types/forms.ts` (`FormShareSettings`, `FormInvitation`), `server/mock/data/formAccess.ts`, `shortCodeStore.ts`, `shared/utils/urls/*`.

| Table | Key columns |
| --- | --- |
| `form_short_links` | form_id (one active), code (also in `short_link_codes`), clicks, created_at, removed_at |
| `form_invitations` | form_id, email, name, token_hash, status (`invited`, `opened`, `responded`, `revoked`), sent_at, opened_at, responded_at, revoked_at. One person, one response |

Embed allow-list, custom link, password and access mode are columns on `forms`. Unlock cookies are signed with the form's access version (mode + password version), so there is no unlock table. People sign-up links are under People.

### Public filling: sessions, resume, uploads, spam checks

Source: `server/mock/routes/publicForms.ts`, `resumeStore.ts`, `routes/uploads.ts`, `shared/utils/forms/proof-of-work.ts`, `submission.ts`.

| Table | Key columns |
| --- | --- |
| `resume_drafts` | form_id, token_hash, data jsonb, page, email, created_at, updated_at, expires_at (30 days), closed_at |
| `respondent_verifications` | form_id, email_hash, code_hash, attempts, expires_at, token_hash (30 min, single use), used_at |
| `uploads` | purpose (`logo`, `form_image`, `share_image`, `response_file`), form_id, field_key, file_name, content_type, size, sha256, storage_key, status (`pending`, `complete`, `attached`), response_id, scan_status, expires_at, completed_at. One upload belongs to at most one response |

Proof-of-work challenges, submission rate limits and unlock attempt counters live in Redis with TTL. The `Formalie-Key` of a fill-in session is `responses.submission_id`; the device cookie is stored hashed on the response.

### Responses, files and review

Source: `shared/types/responses.ts`, `server/mock/data/responseStore.ts`, `responseReview.ts`, `responseData.ts`, `routes/responseFiles.ts`.

| Table | Key columns |
| --- | --- |
| `responses` | **partitioned by range (`submitted_at`, monthly)**; PK (tenant_id, id, submitted_at). form_id, form_version_no, number (per form), data jsonb, language, channel (`link`, `embed`, `api`), submission_id (unique per form), api_token_id, device_hash, fingerprint (SHA-256 of answers), respondent_kind (`invite`, `member`), respondent_ref_id, respondent_email, respondent_name, possible_duplicate jsonb (of, reason), duplicate_cleared, status (`new`, `reviewed`, `approved`, `rejected`), tags text[], edited, duration_seconds, ip (masked per settings), user_agent, country, device, deleted_at |
| `response_notes` | response_id, response_submitted_at, author_id, text |
| `response_changes` | response_id, response_submitted_at, by, field, before jsonb, after jsonb, at. The original answer stays here when `responses.data` is corrected |

Child tables carry `response_submitted_at` so composite FKs reach the partitioned parent. Files are `uploads` with `purpose = response_file`; answers hold `FileAnswer { id, name, size, type }`; viewing issues a 5-minute `download_tokens` row.

### Exports and downloads

Source: `shared/types/responses.ts` (`ResponseExport`), `audit.ts` (`ExportJob`), `explorer.ts` (`TableExport`), `routes/responseExports.ts`.

| Table | Key columns |
| --- | --- |
| `export_jobs` | kind (`responses`, `audit`, `table`, `query`), form_id or datasource_id, format (`xlsx`, `csv`, `pdf`, `json`, `sql`), scope (`all`, `filtered`, `selected`, `page`), filters jsonb, status (`queued`, `running`, `ready`, `failed`, `expired`), progress, rows, columns, capped, file_name, storage_key, size, created_by, expires_at (responses 7 days) |
| `download_tokens` | token_hash, export_job_id or upload_id, host_tenant_id, expires_at (5 to 10 min), used_at. Single use |

### Data sources, response storage, explorer and query

Source: `shared/types/datasources.ts`, `destinations.ts`, `query.ts`, `explorer.ts`, `shared/utils/datasources/*`, `server/mock/data/dataSourceStore.ts`, `destinationStore.ts`, `savedQueryStore.ts`, `routes/query.ts`.

| Table | Key columns |
| --- | --- |
| `datasources` | name, engine (`mysql`, `postgresql`, `sqlserver`, `oracle`, `mariadb`), settings jsonb (host, port, database, TLS, SSH …), secrets_enc, secrets_changed_at, access jsonb (table_prefix `formalie_` / `fmly_` / `form_`, tables_schema, other `none` / `read` / `read_write`, schemas), enabled, last_test_id, created_by, deleted_at |
| `datasource_tests` | datasource_id (null before save), status, steps jsonb (network, ssh, tls, sign_in, database, permissions), permissions jsonb, findings text[], server_version, latency_ms, schemas text[], tables_count, started_at, finished_at |
| `datasource_checks` | datasource_id, at, status (`passed`, `warning`, `failed`), latency_ms, error_code. Health checks; uptime and status (`connected`, `attention`, `failing`, `disabled`, `untested`) derive from them |
| `response_destinations` | form_id (one per form), datasource_id, table_schema, table_name, table_created, columns jsonb (`DestinationColumn[]`: column, type, source field or meta, nullable, existing), settings jsonb (write_mode `insert` / `upsert`, key_column, multi_value `json` / `text`, choices `value` / `label`), paused_at, covers_from, row_version |
| `destination_deliveries` | destination_id, response_id, status (`pending`, `sent`, `failed`, `held`, `not_sent`), attempts, error_code, next_retry_at, sent_at |
| `destination_backfills` | destination_id, from, to, total, done, status (`running`, `done`), started_at, finished_at |
| `saved_queries` | name, description, sql, datasource_id, shared, owner_id, last_run_at |
| `saved_query_runs_daily` | saved_query_id, day, runs |
| `query_history` | user_id, datasource_id, sql, kind, ran_at, duration_ms, rows, ok, error_code. Last 50 per person and connection |

**In the customer's database** (not Formalie's): one table per form named `{prefix}{form}` in `tables_schema`, with the meta columns `response_id` (key), `submitted_at`, `form_version`, `language`, `response_number`, `respondent_email`, `review_status`, then one column per mapped question. Explorer row edits and structure changes (create, alter, truncate, drop) run directly against the customer's database; Formalie keeps no copy, only the `audit_logs` entry (area `data`, before / after) that feeds Data sources → Activity.

### API service

Source: `shared/types/apiService.ts`, `shared/utils/apiService/*`, `server/mock/data/apiStore.ts`, `apiTraffic.ts`.

| Table | Key columns |
| --- | --- |
| `api_settings` | one per tenant: api_key (also in `api_keys_directory`), previous_key, previous_until, rotated_at, rate_per_token, rate_per_ip, rate_per_endpoint, log_keep_bodies, log_days (1, 7, 30) |
| `api_services` | name, description, status (`active`, `disabled`), allowed_origins text[] (CORS), created_by, deleted_at |
| `api_endpoints` | service_id, name (lower-case words with hyphens, unique per service), description, form_id, pinned_version (null = latest), methods text[], fields jsonb (key, name, accept, required, returned, filter), page_size (≤ 100), required_headers jsonb (name, value_enc), status |
| `api_tokens` | name, kind (`static`, `client`, `webhook`), mode (`live`, `test`), secret_hash, previous_hash, rotating_until, preview, client_id, lifetime_minutes, signing, signing_secret_enc, scopes jsonb (services, endpoints, methods), expires_at, last_used_at, revoked_at, created_by |
| `api_access_rules` | action (`allow`, `block`), kind (`ip`, `domain`, `country`, `region`, `network`), values text[], scope_type (`all`, `service`, `endpoint`), scope_id, note, enabled, last_hit_at |
| `api_rule_hits_daily`, `api_rate_limited_daily` | rule_id or limit kind, day, count |
| `api_idempotency` | endpoint_id, formalie_key, body_hash, response_id, answer jsonb (test tokens store nothing else), at. Kept 24 hours; unique (tenant_id, endpoint_id, formalie_key) |
| `api_request_logs` | **partitioned daily**; at, method, path, status, code, duration_ms, endpoint_id, service_id, token_id, ip, country, user_agent, request_id, request_headers jsonb, request_body / response_body jsonb (only with `log_keep_bodies`, personal answers masked). Dropped after `log_days` |

### Webhooks and the event outbox

Source: `shared/types/integrations.ts`, `shared/utils/integrations/webhooks.ts`, `server/mock/data/integrationStore.ts`.

| Table | Key columns |
| --- | --- |
| `webhooks` | name, url, events text[] (`response.created`, `response.updated`, `response.status_changed`, `response.deleted`), enabled, paused_reason (`manual`, `failures`), token_id (an `api_tokens` row of kind `webhook` that signs), consecutive_failures, created_by |
| `webhook_forms` | webhook_id, form_id |
| `webhook_deliveries` | **partitioned monthly**; webhook_id, event (or `ping`), test, form_id, response_id, status (`delivered`, `retrying`, `failed`), attempts, history jsonb (at, status_code, duration_ms, error), next_retry_at (retries after 1, 5, 15, 60, 360 min), request_headers jsonb, body, response jsonb |
| `event_outbox` | **partitioned monthly**; type (`response.created`, `form.published` …), routing_key, payload jsonb (refs only, never answers), created_at, published_at. Feeds webhooks, destinations and the `formalie.events` exchange; kept 7 days for replay |
| `processed_events` | consumer, event_id, processed_at |

### Emails, sending and notifications

Source: `shared/types/emails.ts`, `notifications.ts`, `server/mock/data/sendingStore.ts`, `outboxStore.ts`, `notificationStore.ts`, `responseEmails.ts`.

| Table | Key columns |
| --- | --- |
| `email_templates` | key, language, subject, body. Only the workspace's own text; defaults are `system_email_templates` |
| `email_sending` | one per tenant: mode (`formalie`, `domain`, `smtp`), from_address |
| `sending_domains` | address, domain, status (`pending`, `verified`, `failed`), records jsonb (TXT / CNAME / MX), token, problem, added_at, checked_at |
| `smtp_servers` | host, port, security (`starttls`, `tls`, `none`), username, password_enc, from_address, status (`untested`, `working`, `failed`), problem, checked_at |
| `sent_emails` | **partitioned monthly**; to, template, language, subject, reason (`response`, `response_outside`, `invite` …), html, text, status, provider_message_id, sent_at |
| `notifications` | user_id, event (`response_new`, `response_duplicate`, `form_limit`, `form_closing`, `export_ready`, `webhook_failing`, `security_alert`), params jsonb, link, created_at, read_at. Last 100 per person |
| `notification_digest_lines` | email, name, line, created_at (daily digest queue); plus `notification_once` (key, at) for things announced once |

Per-event rules (in-app, email, audience) are `workspace_settings.notifications`; personal email choices are `users.notifications`.

### Settings, privacy, retention, residency, SSO, onboarding

Source: `shared/types/settings.ts`, `privacy.ts`, `appearance.ts`, `sso.ts`, `onboarding.ts`, `shared/utils/settings/schemas.ts`, `server/mock/data/settingsStore.ts`, `ssoStore.ts`, `retentionStore.ts`, `routes/onboarding.ts`, `routes/dataPrivacy.ts`.

| Table | Key columns |
| --- | --- |
| `workspace_settings` | section (`company`, `branding`, `localisation`, `signin`, `security`, `notifications`, `emails`, `privacy`, `form_defaults`, `appearance`), value jsonb, row_version, updated_at, updated_by. Unique (tenant_id, section). Holds password policy, session limits, IP allow-list, sign-in methods and code rules, retention_days (0, 30, 90, 180, 365, 730, 1825), consent, form defaults, portal appearance |
| `sso_connections` | one per tenant: provider (`okta`, `entra`, `google_workspace`, `onelogin`, `saml`, `oidc`), protocol, label, saml jsonb (metadata_url, entity_id, sso_url, certificate), oidc_issuer, oidc_client_id, oidc_client_secret_enc, domains text[], enforce, auto_create, default_role_id (never owner), status (`draft`, `tested`, `active`), tested_at, problem |
| `onboarding` | one per tenant: status, current_step (`company`, `branding`, `localisation`, `team`, `first_form`), steps jsonb, invites jsonb, first_form jsonb, completed_at |
| `retention_runs` | ran_at, retention_days, responses_removed, forms_affected |
| `support_access_grants` | (required by FORMALIE-INTEGRATION §3, not yet in the portal) requested_by_staff, duration, write_allowed, status, approved_by, starts_at, ends_at |

Data residency: `tenants.data_region` (read in Settings, Enterprise only, moved by a platform migration). Privacy requests (search, export, delete by email) leave only audit entries with the address masked.

### Billing (Payoneer)

Source: `shared/types/billing.ts`, `shared/utils/billing/plans.ts`, `server/mock/data/billingStore.ts`, `billingLifecycle.ts`, `server/mock/billing/{safety,guard,webhook}.ts`, SECURITY-PROTOCOL §11.

| Table | Key columns |
| --- | --- |
| `subscriptions` | one per tenant: plan_id, period (`monthly`, `quarterly`, `annually`), status (`active`, `past_due`, `grace`, `cancelled`, `expired`), started_at, current_period_start, current_period_end, auto_renew, cancel_at_period_end, scheduled_plan, scheduled_period, scheduled_at, grace_until, card_brand, card_last4, card_exp_month, card_exp_year, card_reference (Payoneer's), card_added_at, reminders jsonb (before_renewal days, payment_failed, card_expiring, extra_emails), row_version. Locked with `SELECT … FOR UPDATE` during a change (`FRM-BILL-1004`) |
| `payments` | reference (unique: `checkout:{id}`, `upgrade:{key}`, `renew:{tenant}:{period_end}`), kind (`subscribe`, `upgrade`, `renewal`, `card`), plan_id, period, amount numeric(12,2), currency, status (`pending`, `paid`, `failed`, `refunded`; forward only), invoice_id, processor_txn_id, created_at, settled_at |
| `invoices` | number (unique), issued_at, plan_id, period, period_start, period_end, amount, currency, status (`paid`, `open`, `failed`, `refunded`), card_label, payment_id |
| `checkout_sessions` | purpose (`subscribe`, `add_card`), plan_id, period, amount, currency, url, status (`open`, `completed`, `cancelled`, `expired`), expires_at (30 min). Partial unique: one `open` per tenant |
| `billing_idempotency_keys` | key, scope, request_hash, result jsonb, created_at. Unique (tenant_id, key); kept 24 hours (`FRM-BILL-1005`) |
| `billing_reminders_sent` | reminder_key (kind + period end), sent_at |

Card numbers never reach Formalie. Usage against limits (forms, responses per form, databases, AI credits) is counted live from the tables above. Form payments (F24 second part) are not designed yet.

### Analytics and dashboard rollups

Source: `shared/types/analytics.ts`, `dashboard.ts`, `shared/utils/dashboard/*`, `server/mock/data/responseInsights.ts`, `routes/analytics.ts`, `routes/dashboard*.ts`.

| Table | Key columns |
| --- | --- |
| `form_fill_events` | **partitioned daily**; form_id, session_id, kind (`view`, `start`, `page`, `stop`), page, field_key, channel, at. One view and one start per session; nothing names a respondent |
| `form_analytics_daily` | form_id, day, views, starts, completions, median_seconds, channels jsonb (link, embed, api) |
| `form_funnel_daily` | form_id, day, page or field_key, reached, answered, left, seconds_median |
| `api_usage_daily` | service_id, endpoint_id, token_id, day, calls, errors, avg_ms |
| `datasource_ops_daily` | datasource_id, day, kind (queries, rows, structure, exports, storage, connections), count |

Workers roll events up nightly (and the current day on read). The dashboard (Workspace, Forms, Data sources, API service views) is computed from these rollups, `responses`, `subscriptions` and `audit_logs`; it stores nothing of its own.

### AI usage

Source: `shared/types/ai.ts`, `shared/utils/ai/kinds.ts`, `server/mock/data/aiStore.ts`.

| Table | Key columns |
| --- | --- |
| `ai_settings` | one per tenant: enabled, sources jsonb (forms, responses, data), mask_personal, keep_days (30, 90, 180, 365), updated_at, updated_by |
| `ai_requests` | kind (`form`, `template`, `theme`, `builder`, `analysis`, `question`, `summary`, `translate`, `rewrite`), status (`proposed`, `applied`, `discarded`, `failed`), title, title_key jsonb, user_id, target_type (`form`, `template`, `theme`, `response`), target_id, target_name, credits, prompt (masked), result, output jsonb, notes jsonb, stats jsonb, read_sources text[], masked, model, created_at, applied_at. Purged after `keep_days` |

Monthly credits come from `plan_limits.ai_credits`; used credits are summed from `ai_requests` for the period.

### Help and tours

Source: `shared/types/help.ts`, `server/mock/data/helpStore.ts`, `shared/utils/platform/forms.ts`.

Help content is read from the global `help_*` tables (cached, dropped on `platform.published`). Per person: `user_tours` (People section). Feedback and missed searches go to the global `help_feedback` and `help_search_misses`. Contact support and the Enterprise enquiry are published forms of Formalie's own workspace (`PLATFORM_FORMS`); what people send is an ordinary `responses` row there, so there is no support table.

### Audit and logs

Source: `shared/types/audit.ts`, `shared/utils/audit/events.ts`, `server/mock/data/audit.ts`, `server/mock/core/audit.ts`.

| Table | Key columns |
| --- | --- |
| `audit_logs` | **partitioned monthly**, insert-only; occurred_at, action, area, outcome (`success`, `failure`, `blocked`), severity (`info`, `notice`, `warning`, `critical`), actor_type (`user`, `api_key`, `system`, `platform_support`), actor_id, actor_name, actor_email, resource_type, resource_id, resource_name, ip, city, country, device jsonb, changes jsonb (field, before, after), metadata jsonb, reason (FRM code), request_id; for `platform_support`: staff_id, staff_name, approval_id |
| `request_logs` | **partitioned monthly**; nullable tenant_id (failures before the tenant is known), method, path template, status, duration_ms, request_id, ip, at |
| `error_logs` | **partitioned monthly**; nullable tenant_id, code, message, stack, request_id, at |

RLS lets a workspace read only its own `audit_logs`; `platform_reader` reads all. Every state-changing endpoint and every sign-in attempt writes one `audit_logs` row.

## Index starters

- `forms (tenant_id, organisation_id, status, updated_at desc) WHERE deleted_at IS NULL`; `forms (tenant_id, slug) UNIQUE WHERE deleted_at IS NULL`; `forms (tenant_id, folder_id)`; GIN `forms (tags)`
- `users (tenant_id, lower(email)) UNIQUE WHERE deleted_at IS NULL`; `users (tenant_id, role_id)`, `users (tenant_id, status)`
- `responses (tenant_id, form_id, submitted_at desc)` per partition; `(tenant_id, form_id, status)`; `(tenant_id, form_id, submission_id)`; `(tenant_id, form_id, lower(respondent_email))`; `(tenant_id, form_id, fingerprint)`; GIN `responses (data jsonb_path_ops)`
- `option_items (tenant_id, list_id, level, parent_value, sort_order)`; GIN trigram `option_items (label)` for search as people type
- `form_field_refs (tenant_id, ref_type, ref_id)`
- `refresh_tokens (token_hash)`, `otp_challenges (tenant_id, user_id, purpose, expires_at)`, `user_invites (token_hash)`, `form_invitations (token_hash)`, `resume_drafts (token_hash)`, `download_tokens (token_hash)`
- `api_tokens (secret_hash)`, `api_tokens (client_id)`, `api_endpoints (tenant_id, service_id, name) UNIQUE`, `api_request_logs (tenant_id, at desc)`
- `destination_deliveries (tenant_id, status, next_retry_at)`, `webhook_deliveries (tenant_id, webhook_id, at desc)`, `event_outbox (published_at) WHERE published_at IS NULL`
- `notifications (tenant_id, user_id, read_at, created_at desc)`
- `audit_logs (tenant_id, occurred_at desc)`, `(tenant_id, area, occurred_at desc)`, `(tenant_id, actor_id, occurred_at desc)`, `(tenant_id, resource_type, resource_id)`; `request_logs (created_at desc, tenant_id)`
- `payments (reference) UNIQUE`, `checkout_sessions (tenant_id) UNIQUE WHERE status = 'open'`, `billing_idempotency_keys (tenant_id, key) UNIQUE`

## Partitioning and maintenance

| Table | Partition | Kept |
| --- | --- | --- |
| `responses` (+ notes, changes by FK) | monthly on `submitted_at` | per workspace `privacy.retention_days` (0 = forever); a nightly job deletes due rows and records `retention_runs` and `settings.retention_applied` |
| `audit_logs`, `request_logs`, `error_logs` | monthly | 12 months hot, then detached to cold storage |
| `api_request_logs` | daily | `api_settings.log_days` (1, 7, 30) |
| `form_fill_events` | daily | 90 days (rolled up into `form_analytics_daily` and `form_funnel_daily` first) |
| `webhook_deliveries`, `sent_emails` | monthly | 90 days |
| `event_outbox` | monthly | 7 days after publish |

Celery Beat creates the next 3 periods ahead and detaches expired ones. Other scheduled jobs: Trash purge (30 days); expired resume drafts, invites, OTP challenges, download tokens and idempotency keys (24 h); AI requests after `keep_days`; renewals and reminders; daily Payoneer reconciliation; destination and webhook retries; datasource health checks; domain and sending-domain checks; the daily digest.

## Seeded default data

Global (migrations or the platform admin): countries, currencies, time zones, the 20 languages, data regions, plans with prices, limits and features, the permission catalogue, audit event types, error codes, reserved subdomains, Formalie's system lists (simple: countries, regions, cities, languages, currencies; with levels: Countries → States → Cities, Countries → Cities → Regions; Large where needed), system folders, system email templates (20 languages), system templates, themes and page designs, help content.

Per new workspace (backend, at sign-up, one transaction): the primary organisation; roles `owner`, `admin`, `member` with `DEFAULT_ROLE_GRANTS`; the founding user as Owner; `workspace_settings` sections with Formalie's defaults (language `en`, timezone `UTC`, currency `USD`, password policy, sessions 60 min idle and 168 h max, notification rules, retention 0, appearance `formalie`); default folders (Operations, Customers, Compliance, Marketing, Leads, Projects) with `system_key`; locked copies or references of the system lists; `subscriptions` on Starter (active at once); `ai_settings` (forms and responses on, data off, masking on, 90 days); `api_settings` with a new API key; `signup_links` off; `onboarding` not started; `email_sending` mode `formalie`; `tenants.data_region = 'default'`. Defaults are use-only: no edit, no delete.

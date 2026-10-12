# Database Design, Formalie (PostgreSQL 16)

Rewritten 2026-10-10 from the finished portal (`C:\UNETPROJECTS\formalieFrontend`): entity shapes in `shared/types/*.ts`, catalogues in `shared/utils/**`, per-workspace stores in `server/mock/data/*.ts`, and `docs/API-CONTRACT.md`, `OPTION-LISTS.md`, `03-DECISIONS-AND-NOTES.md`, `SECURITY-PROTOCOL.md`. Global tables and DB roles for the platform admin follow `formaliePlatformBack/docs/FORMALIE-INTEGRATION.md`. Columns listed are the key ones, not full DDL. Dropped since the first draft: `form_collab_docs` (live collaboration removed, F20), custom CSS (removed, L5).

## Conventions

- **Schemas** (owner, 2026-10-10): every workspace (tenant) table and the outbox live in the **`formaly`** schema (`DB_SCHEMA`); global and directory tables in `platform`; nothing in `public` (no one may create objects there). Each role's `search_path` is `formaly, platform`.
- IDs: `uuid` (UUIDv7, generated in app) everywhere. Names: snake_case, plural tables. Enums are `text` with a `CHECK` (values listed below come from the frontend catalogues).
- **Tenant mixin** (all tenant tables): `tenant_id uuid not null`, `organisation_id uuid not null`, composite unique `(tenant_id, id)` for composite FKs, **RLS enabled and FORCED**. Policy on both `tenant_id` and `organisation_id` (BACKEND-SPEC §2, `enable_tenant_rls()`); the API sets `app.tenant_id` / `app.organisation_id` / `app.user_id` per transaction (`set_config(…, true)`).
- **No hard deletes** (owner, 2026-10-10): `formalie_app` has no DELETE or TRUNCATE privilege on any Formalie table, and the ORM refuses `session.delete()`. Purges, trash emptying and retention mark rows (`deleted_at`, `purged_at`), they never remove them.
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
| `formalie_owner` | Owns the schema; used only by migrations (Alembic). Roles are created once per cluster by `scripts/db_bootstrap.py`. |
| `formalie_app` | API and Celery workers. `NOBYPASSRLS`; SELECT, INSERT, UPDATE on tenant tables (no DELETE: soft delete only), INSERT only on `event_outbox`, `SELECT` on global tables, `INSERT` only on log tables (`audit_logs`, `request_logs`, `error_logs`, `form_fill_events`); `api_request_logs` also UPDATE (bodies cleared after their days). Cannot list `tenants` except through `platform.resolve_tenant(host)` (SECURITY DEFINER). |
| `formalie_worker` | Outbox relay, partition upkeep and log writing only. `BYPASSRLS`, SELECT and UPDATE on `event_outbox`, INSERT on `request_logs`, EXECUTE on `platform.ensure_monthly_partitions`; nothing else. |
| `formalie_readonly` | Reporting on replicas: SELECT, `default_transaction_read_only = on`, `NOBYPASSRLS`. |
| `platform_reader` | Read replica only. `BYPASSRLS`, `default_transaction_read_only = on`, `statement_timeout = 15s`, connection limit 10 (LOGIN through `DB_PLATFORM_READER_URL`, `scripts/db_bootstrap.py`). Column privileges on every table of both schemas (B16, migration 0034; later tables through `enable_tenant_rls`), excluding secrets (every `*_hash` and `*_enc` column: password, token, code and secret hashes, TOTP secrets, encrypted credentials) and answer content (`responses.data` and the respondent's name and emails, `resume_drafts.data` and email, `response_changes.before / after`, `response_notes.text`, request / API / webhook bodies, `api_idempotency.answer`, `sent_emails.html / text`, `ai_requests.prompt / result / output`, saved and run SQL, `forms.draft_schema`, `form_versions.schema`, `custom_domains.token`). The list: `app/modules/platform_bridge/grants.py`; CI: `tests/db/test_platform_grants.py`. |
| `platform_writer` | `INSERT`, `UPDATE` (no `DELETE`; retire with `retired_at`) on the platform-owned global tables marked **(P)** below, nothing else (connection limit 5, LOGIN through `DB_PLATFORM_WRITER_URL`). Every write carries `published_by_staff_id` (the trigger `platform.stamp_published` refuses one without it and stamps `published_at`; B14's help tables are stamped by the platform); then `platform.published { table, ids, version }` on the bus drops Formalie's caches. |

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
| `plan_limits` **(P)** | plan_id, forms, responses_per_form, databases text[], sso, custom_domains, custom_email, data_residency, ai_credits, languages (null = no limit) |
| `plan_features` **(P)** | plan_id, feature (`PLAN_FEATURES`: analytics, templates, lists, themes, explorer, query, destinations, api, webhooks, apiDocs, ai, branding, subdomain, languages, visits, versions, folders, fillLater, socialSignin, sso, customDomain, customEmail, dataResidency, prioritySupport, dedicatedSupport, securityReview) |
| `permissions` | code (`forms.publish`, `data.query_write` …), area, group, scopes text[] (`own`, `shared`, `own_shared`, `all`; empty = on/off), needs text[] (`PERMISSION_NEEDS`). Mirror of the catalogue, seeded by migration |
| `audit_event_types` | action (`forms.published` …), area (`auth`, `workspace`, `forms`, `responses`, `settings`, `users`, `integrations`, `api`, `data`, `ai`, `audit`), severity |
| `error_codes` | code (`FRM-*`), http_status, message_key |
| `platform_settings` **(P)** | key, value jsonb, description: legal (terms_url, privacy_url), support (email, url), egress_ips (shown on Data sources), status_page (url), later branding. Shipped rows mirror the server's settings; a row published by staff wins (B16) |
| `reserved_subdomains` **(P)** | subdomain, reason |
| `feature_flags` **(P)** | key, description, enabled, plans text[], tenant_ids uuid[], rollout_percent (0 to 100), retired_at |
| `announcements`, `announcement_translations` **(P)** | id, kind (banner, maintenance, news), tone (info, warning, critical), audience (all / plans / tenants), plans, tenant_ids, starts_at, ends_at, link_url, dismissible, retired_at; (announcement_id, language), title, body |
| `system_option_lists` **(P)** | key, name, description, levels jsonb, columns jsonb, large bool, sort, retired_at |
| `system_option_items` **(P)** | (list_key, value), label, level, parent_value, translations jsonb, attrs jsonb, sort_order, active |
| `system_folders` **(P)** | key (operations, customers, compliance, marketing, leads, projects), name_key, color, sort |
| `system_email_templates` **(P)** | key (`signin_code`, `password_reset`, `invitation`, `response_notification`, `response_receipt`, `notification`, `daily_digest`), language, subject, body |
| `system_templates`, `system_template_translations` **(P)** | key, category, icon, tags, minutes, design jsonb, schema jsonb (FormSchema v1), sort, retired_at; (template_key, language), name, description, content jsonb |
| `system_themes`, `system_page_designs` **(P)** | key, name_key, tokens jsonb (the preset's patch), sort, retired_at |

**Built in B16 (migration 0034):** every **(P)** table above except the help ones (B14), each with created_at, updated_at, `published_at`, `published_by_staff_id`, and seeded from what Formalie ships (`app/modules/platform_bridge/seed.py`: the server's platform settings, the host rules' reserved subdomains, the plans, the sample lists, the email templates in 20 languages, the template catalogue with English names, the theme and page presets; no default folders). The portal reads `platform_settings`, `reserved_subdomains`, `feature_flags` and `announcements` now (Redis, `fm:v1:platform:global:{table}:…`, dropped on `platform.published`); the plans with B15, the default catalogues with B17. Also global: `admin_calls` (every internal admin API call: key id, idempotency key (unique), request hash, method, path, tenant_id, staff id and name, approval id, reason, status, error code, the answer encrypted in `response_enc`; written by `formalie_app`).
| `help_categories` **(P)** | key (`HELP_CATEGORIES`: start, forms, builder, design, templates, sharing, responses, analytics, lists, data, api, people, settings, audit, ai), sort |
| `help_articles`, `help_article_translations` **(P)** | id (text, e.g. `first-form`), category, route (page pattern, `/forms/:id/build`), related text[], start_order ("New here?" order), popular, minutes, sort, retired_at; per (article_id, language): title, summary, keywords text[], blocks jsonb (`HelpBlock[]`: p, h, steps, list, tip / note / warning, show, media), generated `body` (the readable text) and `search` (tsvector: title A, keywords B, summary C, body D, in the language's text search configuration) |
| `help_faqs`, `help_faq_translations` **(P)** | id, category, article_id, sort, retired_at; per language question, answer, generated `search` (question A, answer D) |
| `help_glossary`, `help_glossary_translations` **(P)** | id, article_id, sort, retired_at; per language term, definition, generated `search` (term A, definition D) |
| `help_tours`, `help_tour_translations` **(P)** | id, route pattern, targets text[] (the controls the steps point at, `data-help`), sort, retired_at; per language title, steps jsonb ([{ title, text }], in the targets' order) |
| `help_search_misses` **(P)** | language, query_norm (lower case, at most 120 characters), count, first_at, last_at; unique (language, query_norm). Written by `formalie_app`, read by the platform |

Every `help_*` content table also has created_at, updated_at, `published_at` and `published_by_staff_id` (null: shipped with Formalie). Helpers for the generated columns: `platform.help_fold()`, `help_join()`, `help_blocks_text()`, `help_search_config()` (migration 0033).
| `billing_webhook_events` | event_id (unique), type (`payment.succeeded`, `payment.failed`, `payment.refunded`), received_at, tenant_id (resolved from the payment reference), outcome, payload jsonb. Each event handled once |

## Tenant directory (schema `platform`, restricted)

Source: `server/mock/data/tenants.ts`, `addressStore.ts`, `shortCodeStore.ts`, `formStore.ts` (`findByPublicKey`, `findByShortCode`), `routes/dataRegion.ts`.

| Table | Key columns |
| --- | --- |
| `tenants` | id, subdomain (unique, lowercase), name, status (`active`, `suspended`, plus `read_only`, `closing` for platform actions), suspended_reason (the reason for any status but active), close_at, primary_organisation_id, data_region (default `default`; changed only by a platform migration), plan_id (mirror of the subscription), trial_ends_at and plan_limits jsonb (set by the platform admin, B16; limits enforced with B15), created_at, setup_completed_at, deleted_at. Changed by the internal admin API through `platform.admin_set_status()` / `admin_set_plan()` / `change_subdomain()` for the workspace in context; read by id with `platform.admin_tenant()` |
| `tenant_subdomain_history` | tenant_id, subdomain, until (the old one keeps working 90 days; unique while active) |
| `custom_domains_directory` | domain (primary key, lower case), tenant_id, verified_at, released_at (null = answering). A verified own web domain → its workspace; one holder at a time (the one whose DNS records prove it, B11). Set-up and checks are the tenant table `custom_domains`. Reached through `platform.claim_domain()`, `release_domain()`, `resolve_domain()` (migration 0031) |
| `public_form_routes` | public_key (10 chars, unique), custom_link (unique on the shared `forms.*` host), tenant_id, form_id. Lets `forms.*` find the workspace from a key |
| `short_link_codes` | code (unique), tenant_id, form_id, retired_at. A retired code is never reused, even after the form is purged |
| `api_keys_directory` | api_key (primary key, path part of `api.formalie.*/{apiKey}/…`), tenant_id, created_at, retired_at (null = current; set = answers until then). One row per handle a workspace ever had, so none is handed out twice. Reached through `platform.claim_api_key()`, `retire_api_key()`, `resolve_api_key()` (migration 0027) |
| `signup_tickets` | ticket_hash, tenant_id, user_id, expires_at (2 min), used_at (cross-host sign-up and social sign-up tokens) |

Access only through `platform.resolve_tenant()`, `platform.resolve_form_key()`, `platform.resolve_api_key()`, `platform.resolve_domain()` and platform services; `formalie_app` cannot list tenants. For the current workspace only (B11, migration 0031): `platform.tenant_profile()` (subdomain, name, plan, data region), `platform.subdomain_history_of()` (old subdomains still answering), `platform.change_subdomain(new, id)` (the old one answers 90 days; the five latest are kept; another workspace's current or old subdomain is refused); `platform.retention_workspaces()` lists every live workspace for the daily retention job.

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
| (sign-in codes) | **In Redis, not a table** (backend, 2026-10-11): `fm:v1:auth:ch:{id}` with purpose, email, channel(s), code hash, attempts, resends, expiry; 30 minutes at most. They are short-lived and often exist before any workspace is known (sign-up, find my workspace). One-time hand-off tickets likewise (`fm:v1:auth:ticket:{hash}`, 2 minutes). Every code sent, failed or locked is in `audit_logs`. |

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
| `help_feedback` | user_id, article_id (→ `platform.help_articles`), language, helpful, comment; one row per person and article while not deleted (a new answer replaces the old); read by the platform for the Formalie team |

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
| `destination_deliveries` | destination_id, response_id, response_submitted_at, status (`pending`, `sent`, `failed`, `held`), attempts, error_code, at (last attempt), sent_at, next_attempt_at. Recorded with the response (same transaction); a response without one is `not_sent` (before the destination covered it). Retries wait 1 min, 5 min, 15 min, 1 h, then 6 h |
| `destination_backfills` | destination_id, range_from, range_to, total, done, status (`running`, `done`), started_at, finished_at |
| `saved_queries` | name, description, sql, datasource_id, shared, owner_id, last_run_at, deleted_at |
| `saved_query_runs_daily` | saved_query_id, day, runs |
| `query_history` | user_id, datasource_id, sql, kind, ran_at, duration_ms, rows, ok, error_code, deleted_at (cleared). The editor shows the last 50 per person and connection |

**In the customer's database** (not Formalie's): one table per form named `{prefix}{form}` in `tables_schema`, with the meta columns `response_id` (key), `submitted_at`, `form_version`, `language`, `response_number`, `respondent_email`, `review_status`, then one column per mapped question. Explorer row edits and structure changes (create, alter, truncate, drop) run directly against the customer's database; Formalie keeps no copy, only the `audit_logs` entry (area `data`, before / after) that feeds Data sources → Activity.

### API service

Source: `shared/types/apiService.ts`, `shared/utils/apiService/*`, `server/mock/data/apiStore.ts`, `apiTraffic.ts`.

| Table | Key columns |
| --- | --- |
| `api_settings` | one per tenant (unique tenant_id): api_key (also in `api_keys_directory`), previous_key, previous_until, rotated_at, rate_per_token, rate_per_ip, rate_per_endpoint (calls a minute, null = no limit; 600, 120, 1200 to start), limits_updated_at, log_keep_bodies, log_days (1, 7, 30; 7 to start) |
| `api_services` | name (unique per tenant, case-insensitive, while not deleted), description, status (`active`, `disabled`), allowed_origins jsonb (CORS), created_by, deleted_at |
| `api_endpoints` | service_id, name (lower-case words with hyphens, unique per tenant while not deleted: it is the address), description, form_id, version (pinned form version, null = latest), methods jsonb, fields jsonb (key, name, accept, required, returned, filter), page_size (≤ 100), headers jsonb (name, value_enc; empty since custom headers were dropped, owner 2026-10-06), status, deleted_at |
| `api_tokens` | name, kind (`static`, `client`, `webhook`), mode (`live`, `test`), secret_hash (SHA-256, looked up), secret_enc (Fernet, only for Reveal after the password), previous_hash, rotating_until, preview (prefix and last 4), client_id (unique per tenant), lifetime_minutes, signing, signing_secret_enc, scopes jsonb (services, endpoints, methods; ids kept after a delete so a token never widens), expires_at, last_used_at, revoked_at, created_by, deleted_at |
| `api_access_rules` | action (`allow`, `block`), kind (`ip`, `domain`, `country`, `region`, `network`), values jsonb, scope_type (`all`, `service`, `endpoint`), scope_id, note, enabled, last_hit_at, deleted_at (also when its service or endpoint is deleted) |
| `api_idempotency` | endpoint_id, formalie_key, body_hash (SHA-256 of the canonical JSON), response_id, answer jsonb (test tokens store nothing else), at, deleted_at. Written in the same transaction as the record; unique (tenant_id, endpoint_id, formalie_key) while not deleted, so two retries at once make one record. Kept 24 hours: Beat (`api_service.expire_call_keys`, hourly) soft deletes older keys in the workspaces `platform.api_idempotency_expired()` lists (migration 0030, B10 step 3) |
| `api_request_logs` | **partitioned monthly** on `at`, key (tenant_id, id, at); one row per call to the public API, written by the gateway (`traffic.record_call`): at, method, path, status, code, duration_ms, endpoint_id + endpoint_name, service_id + service_name, token_id + token_name + token_mode (as they were at the call; never the token), rule_id (the access rule that decided it), rate_limited, ip, country, origin, user_agent, request_id, request_headers jsonb (secrets masked), request_body / response_body jsonb (only with `log_keep_bodies`, personal answers masked, cleared after `log_days`). Every count of calls, errors, answer times, rule hits and limited calls is read from it (B10 step 2) |

### Webhooks and the event outbox

Source: `shared/types/integrations.ts`, `shared/utils/integrations/webhooks.ts`, `server/mock/data/integrationStore.ts`.

| Table | Key columns |
| --- | --- |
| `webhooks` | name, url, events jsonb (`response.created`, `response.updated`, `response.status_changed`, `response.deleted`), form_ids jsonb (empty = every form), enabled, paused_reason (`manual`, `failures`), token_id (an `api_tokens` row of kind `webhook`, sent as Bearer), consecutive_failures, created_by, deleted_at |
| `webhook_deliveries` | **partitioned monthly** on `at`, key (tenant_id, id, at); webhook_id, event (or `ping`), test, form_id, response_id, status (`delivered`, `retrying`, `failed`), attempts, status_code and duration_ms of the last try, history jsonb (at, status_code, duration_ms, error), next_retry_at (retries after 1, 5, 15, 60, 360 min), claimed_until (a worker has it), body_enc (the body as sent, Fernet, for retries and Send again), logged_body (personal answers masked), request_headers jsonb (the token as its preview), response jsonb (headers and the first 2,000 characters). `platform.webhook_deliveries_due(n)` lists those due for the sweep |
| `event_outbox` | **partitioned monthly**; type (`response.created`, `form.published` …), routing_key, payload jsonb (refs only, never answers), created_at, published_at. Feeds webhooks, destinations and the `formalie.events` exchange; kept 7 days for replay |
| `processed_events` | consumer, event_id, processed_at |

### Emails, sending and notifications

Source: `shared/types/emails.ts`, `notifications.ts`, `server/mock/data/sendingStore.ts`, `outboxStore.ts`, `notificationStore.ts`, `responseEmails.ts`.

| Table | Key columns |
| --- | --- |
| `email_templates` | key, language, subject, body. Only the workspace's own text; defaults are `system_email_templates` |
| `email_sending` | one per tenant (B11): mode (`formalie`, `domain`, `smtp`), domain jsonb (`SendingDomain`: address, domain, status, records, added_at, checked_at, problem, plus the DKIM key part), smtp jsonb (`SmtpServer` without the password), smtp_password_enc (Fernet, write-only). The own domain and the own server live here (one each), not in separate tables |
| `sent_emails` | the sent log (B11): sent_at, to_email, subject, template, language, reason (`login`, `reset`, `invitation`, `approval`, `form_invitation`, `respondent_code`, `resume_link`, `response`, `response_outside`, `receipt`, an event key, `daily_digest`, `test`), html, text. The last 200 per workspace; older entries are soft deleted with their bodies cleared on each new one. One-time codes and personal links are kept as dots. Not partitioned (200 live rows per workspace) |
| `notifications` | user_id, event (`response_new`, `response_duplicate`, `form_limit`, `form_closing`, `export_ready`, `webhook_failing`, `security_alert`), params jsonb, link, created_at, read_at. Last 100 per person |
| `notification_digest_lines` | email, name, line, created_at (daily digest queue); plus `notification_once` (key, at) for things announced once |

Per-event rules (in-app, email, audience) are `workspace_settings.notifications`; personal email choices are `users.notifications`.

### Settings, privacy, retention, residency, SSO, onboarding

Source: `shared/types/settings.ts`, `privacy.ts`, `appearance.ts`, `sso.ts`, `onboarding.ts`, `shared/utils/settings/schemas.ts`, `server/mock/data/settingsStore.ts`, `ssoStore.ts`, `retentionStore.ts`, `routes/onboarding.ts`, `routes/dataPrivacy.ts`.

| Table | Key columns |
| --- | --- |
| `workspace_settings` | section (`company`, `branding`, `localisation`, `signin`, `security`, `notifications`, `emails`, `privacy`, `form_defaults`, `appearance`), value jsonb, row_version, updated_at, updated_by. Unique (tenant_id, section). Holds password policy, session limits, IP allow-list, sign-in methods and code rules, retention_days (0, 30, 90, 180, 365, 730, 1825), consent, form defaults, portal appearance |
| `sso_connections` | one per tenant (B11): provider (`okta`, `entra`, `google_workspace`, `onelogin`, `saml`, `oidc`), protocol, label, saml jsonb (metadata_url, entity_id, sso_url, certificate), oidc jsonb (issuer, client_id), client_secret_enc (Fernet, write-only), idp jsonb (what the last passing test read: SAML entity id, sign-in address and certificates, refreshed daily from a metadata address; OIDC endpoints), domains jsonb, enforce, auto_create, default_role (a built-in key or a role id, never owner), status (`draft`, `tested`, `active`), tested_at, problem. Removing it soft deletes the row and clears the secret |
| `custom_domains` | one per tenant (B11): domain, status (`pending`, `verified`, `failed`), records jsonb (`DnsRecord[]`: CNAME → `custom.{root}`, TXT `_formalie.{domain}`), token, problem (`not_found`, `wrong_target`, `dns_error`), added_at, checked_at. Verified: claimed in `platform.custom_domains_directory` |
| `onboarding` | one per tenant: status, current_step (`company`, `branding`, `localisation`, `team`, `first_form`), steps jsonb, invites jsonb, first_form jsonb, completed_at |
| `support_access_grants` | (B16) mode (`read`, `write`), hours (1, 24, 168), starts_at, expires_at, granted_by_name, created_by (the person who allowed it), request_id, revoked_at, revoked_by, revoked_reason (`turned_off`, `expired`). One open at a time; changing it extends it in place |
| `support_access_requests` | (B16) staff_id, staff_name, reason, mode, hours, status (`pending`, `approved`, `declined`, `expired`), expires_at (7 days), approval_id, decided_at, decided_by, decided_by_name, grant_id |
| `support_sessions` | (B16) grant_id, staff_id, staff_name, approval_id, mode, ticket_hash (single use, cleared when redeemed; unique), ticket_expires_at, redeemed_at, ends_at (the grant's end or 60 minutes), ended_at, ended_reason (`signed_out`, `expired`, `access_ended`, `not_used`), last_seen_at. `platform.support_grant_workspace()` and `platform.support_due()` (formalie_directory) find a grant's workspace and what has to expire |

Data residency: `tenants.data_region` (read in Settings, Enterprise only, moved by a platform migration). Privacy requests (search, export, delete by email) leave only audit entries with the address masked.

**Erasure without hard deletes (B11, 03-DECISIONS 2026-10-12):** a person's data request and retention erase responses in place: `data` becomes `{}`, the respondent's name and emails, IP, browser, device, country, fingerprint and tags are cleared, the response is deleted (`deleted_at`) and counted out of its form; its notes are emptied and deleted, the answers in `response_changes` cleared (the only UPDATE `formalie_app` has there: `before`, `after`), its respondent files removed from storage (the `uploads` rows stay, deleted, file name cleared), the bodies of webhook deliveries about it cleared. A person's saved drafts lose their answers and address; emails sent to them stay in the sent log as a line with the address masked. The rows, their numbers and the audit entries stay. Retention runs are recorded as `settings.retention_applied` audit entries (no separate table).

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
| `api_usage_daily` | service_id, endpoint_id, token_id, day, calls, errors, avg_ms (not built: B10 reads `api_request_logs` directly; a rollup if the log grows large) |
| `datasource_ops_daily` | datasource_id, day, kind (queries, rows, structure, exports, storage, connections), count |

Workers roll events up nightly (and the current day on read). The dashboard (Workspace, Forms, Data sources, API service views) is computed from these rollups, `responses`, `subscriptions` and `audit_logs`; it stores nothing of its own.

### AI usage

Source: `shared/types/ai.ts`, `shared/utils/ai/kinds.ts`, `server/mock/data/aiStore.ts`. Migration 0032 (B13).

| Table | Key columns |
| --- | --- |
| `ai_settings` | one per tenant (unique while not deleted): enabled, sources jsonb (forms, responses, data), mask_personal, keep_days (30, 90, 180, 365), monthly_credits (the agreed amount for a plan without one), updated_by_name, updated_at, updated_by. No row = the defaults (on; forms and responses read, data not; masking on; 90 days); the row is written on the first change |
| `ai_requests` | kind (`form`, `template`, `theme`, `builder`, `analysis`, `question`, `summary`, `translate`, `rewrite`), status (`proposed`, `applied`, `discarded`, `failed`), title, title_key jsonb, by_id, by_name, target jsonb { type (`form`, `template`, `theme`, `response`), id, name }, credits, prompt (masked when the workspace asks), result, read jsonb (the sources it read), masked, applied_at, output jsonb (the draft while it waits for a person), notes jsonb, stats jsonb, engine (`model`, `standin`, `fallback`), model, fallback_reason, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens. Index (tenant_id, created_at), (tenant_id, by_id). Past `keep_days`, or removed by a person: soft deleted with prompt, result, output and notes emptied (Beat hourly through `platform.ai_requests_expired()`, which lists workspaces only) |
| `ai_usage` | one per tenant and month (`month` = its first day, UTC; unique): requests, credits, model_calls, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens (bigint). Never deleted |

Monthly credits come from `plan_limits.ai_credits` (else `ai_settings.monthly_credits`); the credits used are read from `ai_usage` for the month, so a removed or expired request still counts.

### Help and tours

Source: `shared/types/help.ts`, `server/mock/data/helpStore.ts`, `shared/utils/platform/forms.ts`.

Help content is read from the global `help_*` tables (cached in Redis, dropped on `platform.published`), item by item in the reader's language with English for what isn't translated yet. They are filled from the shipped help files (`app/modules/help/data`, the mock's) by migration 0033 and `scripts/seed_help.py`, which never overwrite rows the Formalie team published. Search is PostgreSQL full text search on the generated `search` vectors. Per person, in tenant tables with RLS: `user_tours` and `help_feedback` (People section). Searches that found nothing go to the global `help_search_misses` (no person in them). Contact support and the Enterprise enquiry are published forms of Formalie's own workspace (`PLATFORM_FORMS`); what people send is an ordinary `responses` row there, so there is no support table.

### Audit and logs

Source: `shared/types/audit.ts`, `shared/utils/audit/events.ts`, `server/mock/data/audit.ts`, `server/mock/core/audit.ts`.

| Table | Key columns |
| --- | --- |
| `audit_logs` | **partitioned monthly**, insert-only; occurred_at, action, area, outcome (`success`, `failure`, `blocked`), severity (`info`, `notice`, `warning`, `critical`), actor_type (`user`, `api_key`, `system`, `platform_support`), actor_id, actor_name, actor_email, resource_type, resource_id, resource_name, ip, city, country, device jsonb, changes jsonb (field, before, after), metadata jsonb, reason (FRM code), request_id; for `platform_support`: staff_id, staff_name, approval_id |
| `request_logs` | schema `formaly`, **partitioned monthly** on `occurred_at`; id = trace_id; nullable tenant_id (failures before the tenant is known). Every request in full: who, method, host, path, route, query, all headers, body (JSON / text, masked, capped) and its SHA-256, status, sizes, duration, error code, response headers and error bodies, real client IP, peer, forwarding chain, location (MaxMind / Cloudflare), device, flags. BACKEND-SPEC §8.1. INSERT only (`formalie_app`, `formalie_worker`); `platform_reader` reads all but the body columns |
| `error_logs` | **partitioned monthly**; nullable tenant_id, code, message, stack, request_id, at |

RLS lets a workspace read only its own `audit_logs`; `platform_reader` reads all. Every state-changing endpoint and every sign-in attempt writes one `audit_logs` row.

## Index starters

- `forms (tenant_id, organisation_id, status, updated_at desc) WHERE deleted_at IS NULL`; `forms (tenant_id, slug) UNIQUE WHERE deleted_at IS NULL`; `forms (tenant_id, folder_id)`; GIN `forms (tags)`
- `users (tenant_id, lower(email)) UNIQUE WHERE deleted_at IS NULL`; `users (tenant_id, role_id)`, `users (tenant_id, status)`
- `responses (tenant_id, form_id, submitted_at desc)` per partition; `(tenant_id, form_id, status)`; `(tenant_id, form_id, submission_id)`; `(tenant_id, form_id, lower(respondent_email))`; `(tenant_id, form_id, fingerprint)`; GIN `responses (data jsonb_path_ops)`
- `option_items (tenant_id, list_id, level, parent_value, sort_order)`; GIN trigram `option_items (label)` for search as people type
- `form_field_refs (tenant_id, ref_type, ref_id)`
- `refresh_tokens (token_hash)`, `otp_challenges (tenant_id, user_id, purpose, expires_at)`, `user_invites (token_hash)`, `form_invitations (token_hash)`, `resume_drafts (token_hash)`, `download_tokens (token_hash)`
- `api_tokens (tenant_id, secret_hash)`, `api_tokens (tenant_id, previous_hash)`, `api_tokens (tenant_id, client_id) UNIQUE`, `api_endpoints (tenant_id, name) UNIQUE WHERE deleted_at IS NULL`, `api_request_logs (tenant_id, at desc)`
- `destination_deliveries (tenant_id, status, next_retry_at)`, `webhook_deliveries (tenant_id, webhook_id, at)`, `(tenant_id, id)`, `(next_retry_at) WHERE status = 'retrying'`; `api_request_logs (tenant_id, endpoint_id, at)`, `(tenant_id, token_id, at)`, `(tenant_id, rule_id, at) WHERE rule_id IS NOT NULL`, `event_outbox (published_at) WHERE published_at IS NULL`
- `notifications (tenant_id, user_id, read_at, created_at desc)`
- `audit_logs (tenant_id, occurred_at desc)`, `(tenant_id, area, occurred_at desc)`, `(tenant_id, actor_id, occurred_at desc)`, `(tenant_id, resource_type, resource_id)`; `request_logs (created_at desc, tenant_id)`
- `payments (reference) UNIQUE`, `checkout_sessions (tenant_id) UNIQUE WHERE status = 'open'`, `billing_idempotency_keys (tenant_id, key) UNIQUE`

## Partitioning and maintenance

| Table | Partition | Kept |
| --- | --- | --- |
| `responses` (+ notes, changes by FK) | monthly on `submitted_at` | per form `settings.retention_days`, else the workspace's `privacy.retention_days` (0 = forever); applied when the setting is saved and daily (Beat `privacy.apply_retention`): due responses are erased in place (above) and `settings.retention_applied` recorded |
| `audit_logs`, `request_logs`, `error_logs` | monthly | 12 months hot, then detached to cold storage |
| `api_request_logs` | monthly | calls: 12 months like the other logs; bodies only `api_settings.log_days` (1, 7, 30), cleared hourly |
| `form_fill_events` | daily | 90 days (rolled up into `form_analytics_daily` and `form_funnel_daily` first) |
| `webhook_deliveries` | monthly | 90 days |
| `event_outbox` | monthly | 7 days after publish |

Celery Beat creates the next 3 periods ahead and detaches expired ones. Other scheduled jobs: Trash purge (30 days); expired resume drafts, invites, OTP challenges, download tokens and idempotency keys (24 h); AI requests after `keep_days`; renewals and reminders; daily Payoneer reconciliation; destination and webhook retries; datasource health checks; domain and sending-domain checks; the daily digest.

## Seeded default data

Global (migrations or the platform admin): countries, currencies, time zones, the 20 languages, data regions, plans with prices, limits and features, the permission catalogue, audit event types, error codes, reserved subdomains, Formalie's system lists (simple: countries, regions, cities, languages, currencies; with levels: Countries → States → Cities, Countries → Cities → Regions; Large where needed), system folders, system email templates (20 languages), system templates, themes and page designs, help content.

Per new workspace (backend, at sign-up, one transaction): the primary organisation; roles `owner`, `admin`, `member` with `DEFAULT_ROLE_GRANTS`; the founding user as Owner; `workspace_settings` sections with Formalie's defaults (language `en`, timezone `UTC`, currency `USD`, password policy, sessions 60 min idle and 168 h max, notification rules, retention 0, appearance `formalie`); default folders (Operations, Customers, Compliance, Marketing, Leads, Projects) with `system_key`; locked copies or references of the system lists; `subscriptions` on Starter (active at once); `ai_settings` defaults (forms and responses on, data off, masking on, 90 days; the row is written on the first change); `api_settings` with a new API key; `signup_links` off; `onboarding` not started; `email_sending` mode `formalie`; `tenants.data_region = 'default'`. Defaults are use-only: no edit, no delete.

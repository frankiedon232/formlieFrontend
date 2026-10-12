# Data Model, Platform Database (`formalie_platform`)

PostgreSQL 16. UUID primary keys (`uuid` v7 for time order), `created_at` / `updated_at` (timestamptz, UTC), soft delete (`deleted_at`) on editable records, `row_version` for optimistic locking on editable records. Never sent to browsers as raw ids (encrypted references, SECURITY-PROTOCOL §9). Migrations with Alembic only.

Formalie's own tables are **not** here; they are read through `platform_reader` and the global ones written through `platform_writer` (FORMALIE-INTEGRATION.md).

## Staff and access

| Table | Columns (main) |
| --- | --- |
| `staff` | id, email (unique, lower-case), first_name, last_name, photo_key, phone, language, time_zone, date_format, status (`invited` · `active` · `locked` · `disabled`), role_id, password_hash (Argon2id), password_changed_at, password_history (hashes), totp_secret (encrypted at rest), recovery_hashes, failed_attempts, locked_until, last_sign_in_at, invited_by, created_at, updated_at, deleted_at |
| `staff_invites` | id, staff_id, token_hash, expires_at, sent_at, used_at |
| `roles` | id, name, description, built_in (`platform_owner` or null), grants (jsonb: permission → scope), ip_allowlist (cidr[] or null), version, created_at, updated_at |
| `sessions` | id, staff_id, refresh_family_id, refresh_hash, started_at, last_active_at, ended_at, end_reason, ip_country, ip_city, device, browser, os |
| `step_up` | session_id, confirmed_at (last TOTP re-check) |
| `approvals` | id, action (e.g. `tenant.suspend`), params (jsonb, exact), target_type, target_ref, reason, requested_by, requested_at, expires_at, status (`pending` · `approved` · `rejected` · `expired` · `executed` · `failed`), decided_by, decided_at, decision_reason, result (jsonb), formalie_request_id |
| `audit_log` | id, occurred_at, staff_id, staff_name, role_name, action, area, target_type, target_ref, target_name, changes (jsonb before / after), reason, approval_id, outcome (`success` · `failure` · `blocked`), ip_country, ip_city, device, request_id, prev_hash, hash. **Append-only** (insert-only privileges), partitioned by month |
| `security_events` | id, occurred_at, kind (failed sign-in, lockout, replay, bad signature, IP refused …), staff_id, details (jsonb), ip_country |

## Analytics (ANALYTICS.md)

| Table | Columns (main) |
| --- | --- |
| `analytics_events` | occurred_on (date, partition key), id (event uuid), occurred_at, type, tenant_ref, organisation_ref, actor_ref, session_ref, source, country, region, city, language, device, browser, os, plan, properties (jsonb, no personal data). Unique (occurred_on, id) |
| `analytics_rollup_minute` / `_hour` / `_day` | bucket (timestamptz / date), metric, dims (jsonb, normalised keys), dims_hash, value (numeric), updated_at. Unique (bucket, metric, dims_hash) |
| `analytics_sessions` | id, actor_ref, tenant_ref, started_at, ended_at, pages, device, browser, os, country, language |
| `analytics_daily_tenant` | day, tenant_ref, plan, status, active_people, forms, published_forms, responses, api_calls, storage_bytes, mrr_cents, currency |
| `analytics_daily_user` | day, actor_ref, tenant_ref, sessions, pages, features (text[]) |
| `analytics_reports` | id, owner_staff_id, name, definition (jsonb: metrics, dimensions, filters, range, chart), shared (bool), schedule (cron-like text or null), recipients (staff ids), last_sent_at |
| `ingest_cursor` | stream, last_event_at, last_event_id, updated_at |

## Workspaces, accounts and support (platform-side records)

| Table | Columns (main) |
| --- | --- |
| `workspace_notes` | id, tenant_ref, staff_id, body, pinned, created_at, updated_at, deleted_at |
| `workspace_tags` | tenant_ref, tag (e.g. enterprise, at risk, partner), added_by |
| `support_sessions` | id, tenant_ref, grant_ref (Formalie consent), staff_id, mode (`read` · `write`), approval_id, started_at, ends_at, ended_at |
| `pending_actions` | id, approval_id, formalie_call (jsonb), status (`queued` · `sent` · `done` · `failed`), attempts, last_error, next_try_at (for when Formalie's internal API is down) |

Lists of workspaces, people, subscriptions and payments are read live from Formalie's replica, never copied (except the daily analytics snapshot).

## Content (help centre, published to Formalie)

| Table | Columns (main) |
| --- | --- |
| `help_categories` | id, key, area, order, icon, status (`draft` · `published` · `retired`), published_version |
| `help_articles` | id, category_id, key (slug), status, current_version, published_version, author_id, reviewer_id, updated_at |
| `help_article_versions` | id, article_id, number, language, title, summary, body (TipTap JSON), media (jsonb list of media keys), source_hash (for "changed since translated"), created_by, created_at |
| `help_faqs` | id, area, order, status, translations (jsonb: language → { question, answer }) |
| `help_glossary` | id, term_key, translations (jsonb), status |
| `help_tours` | id, key, steps (jsonb: portal route, target selector key, text per language), status |
| `help_media` | id, kind (`image` · `gif` · `video`), storage_key, captions (jsonb per language), size, created_by |
| `help_feedback` | id (copied from Formalie events), article_key, language, helpful (bool), comment, created_at |
| `help_missed_searches` | day, language, query (normalised), count |
| `publish_jobs` | id, kind (`help` · `defaults` · `plans` · `settings` · `announcements` · `flags`), payload (jsonb), approval_id, status, started_at, finished_at, error |

## Formalie default data (drafts, published to Formalie's global tables)

| Table | Columns (main) |
| --- | --- |
| `default_lists` | id, key, name_translations, description_translations, levels (jsonb), columns (jsonb), large (bool), status, published_version |
| `default_list_items` | id, list_id, value, label, translations (jsonb), level, parent_value, details (jsonb), active, order |
| `default_folders` | id, key, name_translations, color, status |
| `default_email_templates` | id, key, translations (jsonb: language → { subject, body }), status |
| `default_catalogue_changes` | id, kind (`template` · `theme` · `page_design`), key, action (`publish` · `retire` · `update`), payload, status |

## Subscriptions and payments (platform-side records)

Plans live in Formalie's global tables (written on publish); subscriptions, invoices and payments live in Formalie (and the processor). The platform keeps only:

| Table | Columns (main) |
| --- | --- |
| `plan_drafts` | id, key, name_translations, features (jsonb), limits (jsonb), prices (jsonb: currency → { monthly, yearly }), trial_days, status, published_version |
| `billing_actions` | id, kind (`activate` · `extend` · `credit` · `refund` · `change_plan` · `cancel`), tenant_ref, subscription_ref, amount_cents, currency, reason, approval_id, staff_id, status, formalie_request_id, created_at |

## Settings and communications

| Table | Columns (main) |
| --- | --- |
| `settings_drafts` | key, value (jsonb), status, published_at, published_by |
| `feature_flag_drafts` | key, description, rule (jsonb: plans, tenants, percentage), status |
| `announcement_drafts` | id, kind (`banner` · `maintenance` · `news`), audience (jsonb), starts_at, ends_at, translations (jsonb), status |
| `messages` | id, subject_translations, body_translations, audience (jsonb), channel (`email` · `in_app` · both), essential (bool), status (`draft` · `scheduled` · `sending` · `sent`), scheduled_at, sent_count, approval_id |

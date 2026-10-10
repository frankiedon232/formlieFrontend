# Database Design — Formalie (PostgreSQL 16)

## Conventions

- IDs: `uuid` (UUIDv7, generated in app) everywhere. Names: snake_case, plural tables.
- **Tenant mixin** (all tenant tables): `tenant_id uuid not null`, `organisation_id uuid not null`, composite unique `(tenant_id, id)` for composite FKs, RLS enabled + forced.
- **Audit mixin:** `created_at timestamptz default now()`, `updated_at`, `created_by uuid`, `updated_by uuid`.
- **Soft delete mixin:** `deleted_at timestamptz null`, `deleted_by uuid null`. Default queries exclude deleted rows. Uniques are partial `WHERE deleted_at IS NULL`.
- **Optimistic locking:** `row_version int` on editable entities (forms, themes, settings).
- FKs: `ON DELETE RESTRICT` (never cascade). Tenant-aware: `FOREIGN KEY (tenant_id, form_id) REFERENCES forms (tenant_id, id)`.
- Timestamps in UTC; tenant timezone applied in presentation.
- Large JSON in `jsonb`; GIN indexes where queried.

## Platform tables (no tenant, no RLS)

| Table                                      | Purpose                                                    |
| ------------------------------------------ | ---------------------------------------------------------- |
| `countries`, `states`, `cities` (optional) | Geo reference                                              |
| `currencies`, `timezones`, `languages`     | Reference                                                  |
| `plans`, `plan_features`                   | Subscription plans and limits                              |
| `permissions`                              | Permission catalogue (`forms.create`, `responses.export`…) |
| `system_templates`                         | Platform templates                                         |
| `error_codes`                              | Error catalogue mirror of ERROR-CODES.md                   |
| `reserved_subdomains`                      | Blocked subdomains                                         |
| `field_types`                              | Field type catalogue (optional, mirrors frontend registry) |

## Tenant directory (platform schema, restricted)

| `tenants` | id, subdomain (unique, lowercase), name, status (pending/active/suspended/closed), plan_id, primary_organisation_id, branding jsonb (logo, colours), settings jsonb, created_at, deleted_at |
Access only through `platform.resolve_tenant()` and platform services; the app role cannot list tenants.

## Tenant tables (tenant_id + organisation_id + RLS)

### Identity and access

| Table                   | Key columns                                                                                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `organisations`         | name, legal_name, country_id, timezone, currency, address jsonb, logo_path, is_primary                                                                      |
| `users`                 | email (unique per tenant), phone, first_name, last_name, avatar_path, password_hash, status, is_tenant_admin, mfa_required, last_login_at, locale, timezone |
| `user_identities`       | user_id, provider (google/microsoft/apple/facebook/oidc), provider_user_id, email                                                                           |
| `auth_provider_configs` | provider, enabled, client_id, client_secret_enc, settings jsonb                                                                                             |
| `user_sessions`         | user_id, device, user_agent, ip, geo jsonb, created_at, last_seen_at, revoked_at                                                                            |
| `refresh_tokens`        | session_id, family_id, token_hash, issued_at, expires_at, used_at, revoked_at, replaced_by                                                                  |
| `otp_challenges`        | user_id, purpose (login/signup/reset/workspace), channel, code_hash, expires_at, attempts, consumed_at                                                      |
| `mfa_totp`              | user_id, secret_enc, confirmed_at, recovery_codes_hash                                                                                                      |
| `password_resets`       | user_id, token_hash, expires_at, used_at                                                                                                                    |
| `invitations`           | email, role_ids, token_hash, expires_at, accepted_at                                                                                                        |
| `roles`                 | name, description, is_system                                                                                                                                |
| `role_permissions`      | role_id, permission_code                                                                                                                                    |
| `user_roles`            | user_id, role_id                                                                                                                                            |
| `resource_grants`       | resource_type (form), resource_id, grantee_user_id, access (edit/view/responses)                                                                            |

### Forms

| Table                      | Key columns                                                                                                                                                                                                                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `folders`                  | name, parent_id                                                                                                                                                                                                                                                                                          |
| `forms`                    | folder_id, name, slug (unique per tenant), status (draft/published/closed/archived), current_draft jsonb (FormSchema), draft_row_version, published_version_id, theme_id, settings jsonb (access, limits, schedule, notifications, thank-you), seo jsonb, tags text[], owner_id, published_at, closed_at |
| `form_versions`            | form_id, version_no, schema jsonb, theme_snapshot jsonb, published_by, published_at, change_summary — **immutable**                                                                                                                                                                                      |
| `themes`                   | name, tokens jsonb, is_default                                                                                                                                                                                                                                                                           |
| `templates`                | name, category, description, schema jsonb, theme jsonb, preview_path, source_form_id                                                                                                                                                                                                                     |
| `option_sets`              | name, key, description                                                                                                                                                                                                                                                                                   |
| `option_set_items`         | option_set_id, label, value, sort_order, is_active, meta jsonb                                                                                                                                                                                                                                           |
| `short_links`              | code (globally unique — lives in platform table `short_link_codes` mapping code → tenant_id + link id), form_id, target_url, expires_at, clicks                                                                                                                                                          |
| `form_embeds`              | form_id, allowed_domains text[], settings jsonb                                                                                                                                                                                                                                                          |
| `form_collab_docs` (later) | form_id, yjs_state bytea, updated_at                                                                                                                                                                                                                                                                     |

### Responses

| Table              | Key columns                                                                                                                                                                                                                              |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `responses`        | **partitioned by range (`submitted_at`, monthly)**; form_id, form_version_id, data jsonb, status, tags, respondent jsonb (ip, geo, ua — masked per settings), started_at, submitted_at, duration_ms, source (link/embed/api), is_partial |
| `response_files`   | response_id, field_key, storage_path, mime, size, scan_status                                                                                                                                                                            |
| `response_notes`   | response_id, author_id, body                                                                                                                                                                                                             |
| `response_history` | response_id, changed_by, diff jsonb                                                                                                                                                                                                      |
| `form_sessions`    | form_id, resume_token_hash, partial_data jsonb, expires_at (save-and-resume)                                                                                                                                                             |

### Integrations and jobs

| `destinations` | type (postgres/mysql/mssql/webhook/email/sheets), name, config_enc, mapping jsonb, enabled |
| `destination_deliveries` | destination_id, response_id, status, attempts, last_error, delivered_at |
| `webhooks`, `webhook_deliveries` | url, secret_enc, events[], status, attempts |
| `api_keys` | name, prefix, key_hash, scopes[], expires_at, last_used_at, revoked_at |
| `export_jobs` | form_id, format, filters jsonb, status, progress, file_path, expires_at |
| `files` | module, storage_path, mime, size, checksum, scan_status |

### Settings, billing, analytics

| `tenant_settings` | key, value jsonb (company, security policy, localisation, retention, notification templates, embed defaults) |
| `tenant_subscriptions` | plan_id, status, period_start/end, provider, provider_ref |
| `invoices` | amount, currency, status, provider_ref |
| `usage_counters` | metric, period, value |
| `form_analytics_daily` | form_id, day, views, starts, completions, avg_duration_ms, drop_off jsonb |
| `notifications` | user_id, type, payload, read_at |

### Logs (partitioned monthly; insert-only grants)

`request_logs`, `audit_logs`, `error_logs`, `security_events`, `event_outbox`, `processed_events`. Request/error logs carry nullable tenant_id (pre-tenant failures); RLS lets tenants see only their own audit logs; platform role sees all.

## Index starters

- `forms (tenant_id, organisation_id, status, updated_at desc) WHERE deleted_at IS NULL`
- `forms (tenant_id, slug) UNIQUE WHERE deleted_at IS NULL`
- `responses (tenant_id, organisation_id, form_id, submitted_at desc)` per partition; GIN `responses (data jsonb_path_ops)`
- `users (tenant_id, lower(email)) UNIQUE WHERE deleted_at IS NULL`
- `refresh_tokens (token_hash)`, `otp_challenges (user_id, purpose, expires_at)`
- `audit_logs (tenant_id, created_at desc)`, `request_logs (created_at desc, tenant_id)`

## Partition maintenance

Celery Beat creates next 3 months of partitions, detaches/archives partitions past retention (logs 12 months hot, then cold storage; responses kept per tenant retention setting).

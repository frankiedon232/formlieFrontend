# API Contract v0 (draft), Platform Admin

Shared by the front end (mock) and the backend. Bump the version and update this file on every change; the final contract is generated from FastAPI's OpenAPI at hand-over.

## Conventions (same as Formalie)

- Base `/api/v1` on `platformapi.*`. Every request and response uses the platform envelope (SECURITY-PROTOCOL §1); shapes below are the decrypted payloads.
- `Authorization: Bearer <fernet>`; `X-CSRF-Token` on POST / PUT / PATCH / DELETE.
- Success `{ "success": true, "data": …, "meta": {…} }`; error `{ "success": false, "error": { "code", "message", "trace_id", "details": [{ "field", "message" }] } }` with `PLT-*` codes.
- Lists: `page`, `page_size` (≤ 100), `q`, `sort`, `filter[key]=a,b`, `from`, `to`; meta `{ page, page_size, total, total_pages }` (or `next_cursor`). Paging in the database.
- Ids are encrypted references (27 characters); Formalie references (`tenant_ref`, `user_ref` …) are passed through as Formalie issues them.
- Editable resources carry `row_version`; mismatch → `PLT-GEN-1009`.
- Actions that need approval answer `202 { approval }` (`PLT-APPR-1001`) instead of acting.
- Step-up needed → `401 PLT-AUTH-1020`; the client asks for the code, calls `POST /auth/step-up`, retries once.

## Crypto, auth, profile

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/crypto/handshake` | plaintext ECDH |
| GET | `/auth/csrf` | CSRF token |
| POST | `/auth/login` | `{ email, password }` → `{ challenge_id }` (always a TOTP challenge) |
| POST | `/auth/two-step` | `{ challenge_id, code }` or `{ challenge_id, recovery_code }` → `{ access_token, staff }` + refresh cookie |
| POST | `/auth/refresh` · `/auth/logout` | rotate / end |
| POST | `/auth/step-up` | `{ code }` → `{ confirmed_until }` |
| GET | `/auth/activate/{token}` · POST `/auth/activate/{token}` | invitation preview; `{ password }` → `{ totp_uri, secret_display }`; then `POST /auth/activate/{token}/totp { code }` → `{ recovery_codes }` (shown once) |
| GET / PATCH | `/me` | profile (name, photo, language, time zone, date format) |
| POST | `/me/password` · `/me/totp/reset` · `/me/recovery-codes` | change password, move authenticator, new codes (step-up) |
| GET / DELETE | `/me/sessions`, `/me/sessions/{id}` | sessions |

## Staff, roles, approvals, audit

| Method | Path | Notes |
| --- | --- | --- |
| GET / POST | `/staff` | list (`StaffRow { id, name, email, role, role_name, status, last_sign_in_at, two_step: true, photo }`); add `{ first_name, last_name, email, role_id }` (approval when the role is Platform owner) |
| GET / PATCH | `/staff/{id}` | detail; change role (approval), name |
| POST | `/staff/{id}/disable` · `/enable` · `/sign-out` · `/unlock` · `/resend-invite` | |
| GET / POST | `/roles` | `RoleRow { id, name, description, built_in, grants, people_count }` |
| GET / PATCH / DELETE | `/roles/{id}` | grants changes need approval |
| GET | `/approvals?filter[status]=pending&filter[mine]=requested` (or `to_decide`) | `Approval { id, action, params, target, reason, requested_by, requested_at, expires_at, status, decided_by, decision_reason, result }` |
| POST | `/approvals/{id}/approve` · `/reject` | `{ reason }`, step-up |
| GET | `/audit` | `AuditRow { id, occurred_at, staff, action, target, changes, reason, approval_id, outcome, ip_country, device }`; filters staff, action, area, target, outcome, from, to |
| GET | `/audit/verify` | hash chain status `{ verified_until, ok, broken_at? }` |
| POST | `/audit/export` | approval, background job |

## Workspaces and accounts (read from Formalie's replica; actions through Formalie's internal admin API)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/workspaces` | `WorkspaceRow { ref, name, subdomain, owner { ref, name_masked, email_masked }, plan, status, country, created_at, last_active_at, people, forms, responses_30d, usage { forms, responses, seats, storage } against limits, mrr }`; filters status, plan, country, tag, created / active range |
| GET | `/workspaces/insights` | two chart cards (sign-ups daily, status overview) |
| GET | `/workspaces/{ref}` | detail + tabs `/people`, `/usage`, `/billing`, `/activity` (Formalie audit, read-only), `/notes`, `/support` |
| POST | `/workspaces/{ref}/suspend` · `/restore` · `/read-only` · `/close` · `/cancel-close` · `/subdomain` · `/export` | `{ reason, … }`; approval where SECURITY-PROTOCOL §6 says |
| POST / PATCH / DELETE | `/workspaces/{ref}/notes[/{id}]` · `/tags` | staff notes and tags |
| GET | `/accounts` · `/accounts/{ref}` | people across Formalie (masked), workspaces, sessions, sign-ins |
| POST | `/accounts/{ref}/reveal` | `{ fields: [email, phone, name] }` step-up, audited → values |
| POST | `/accounts/{ref}/sign-out` · `/two-step/reset` · `/password-reset` · `/disable` · `/enable` · `/unlock` | actions |
| POST | `/support/requests` · `/support/sessions` | ask a workspace for access; start a consented session → `{ ticket_url, ends_at }` |

## Billing

| Method | Path | Notes |
| --- | --- | --- |
| GET / POST / PATCH | `/plans`, `/plans/{id}` | drafts; `POST /plans/{id}/publish` (approval) |
| GET | `/subscriptions` · `/subscriptions/{ref}` | from Formalie |
| POST | `/subscriptions/{ref}/activate` · `/extend` · `/credit` · `/change-plan` · `/cancel` | `{ reason, amount?, currency?, until? }` manual actions (approval above the threshold) |
| GET | `/payments` · `/invoices` · `/refunds` | from Formalie / the processor |
| POST | `/payments/{ref}/refund` | approval |
| GET | `/billing/actions` | platform billing actions log |

## Analytics

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/analytics/overview` · `/realtime` · `/acquisition` · `/engagement` · `/activation` · `/retention` · `/usage` · `/revenue` · `/geography` · `/technology` | `from`, `to`, `compare`, `interval`, `filter[plan]`, `filter[country]`, `filter[status]` → cards, series, tables |
| GET | `/analytics/access` | access history (sign-ins), paged, masked |
| POST | `/analytics/explore` | `{ metrics[], dimensions[] (≤3), filters, from, to, interval }` → `{ columns, rows, series, total }` (`PLT-AN-1001` when too large) |
| GET / POST / PATCH / DELETE | `/analytics/reports[/{id}]` | saved reports, schedules |
| POST | `/analytics/exports` | CSV / XLSX job |

## Content, defaults, settings, communications, operations

| Method | Path | Notes |
| --- | --- | --- |
| CRUD | `/help/categories`, `/help/articles`, `/help/articles/{id}/versions`, `/help/faqs`, `/help/glossary`, `/help/tours`, `/help/media` | drafts; translations per language; `POST …/publish` |
| GET | `/help/feedback` · `/help/missed-searches` | |
| CRUD | `/defaults/lists` (+ items, import, translations), `/defaults/folders`, `/defaults/email-templates`, `/defaults/catalogue` | `POST …/publish` (approval), usage `GET /defaults/lists/{id}/usage` |
| GET / PUT | `/settings` (+ `/publish`) · `/feature-flags` · `/announcements` | drafts and publish |
| CRUD | `/messages` (+ `/schedule`, `/send`, approval) | audience preview `POST /messages/audience-count` |
| GET | `/operations/health` · `/queues` · `/jobs?status=failed` · `/errors` · `/requests` · `/security-events` · `/rate-limits` | `POST /operations/jobs/{id}/retry` |

## Roles & access (permission catalogue)

Like Formalie's F22: each action its own permission, with a reach where it applies; needs added automatically; the Platform owner role has everything.

| Area | Permissions |
| --- | --- |
| `overview` | view |
| `analytics` | view, explore, reports (save / schedule), export, access_history |
| `workspaces` | view, notes, suspend, restore, read_only, close, subdomain, export, plan |
| `accounts` | view, reveal, sign_out, two_step_reset, password_reset, disable, unlock |
| `support` | request, session_read, session_write |
| `billing` | view, plans, plans_publish, activate, extend, credit, refund, cancel |
| `content` | view, edit, translate, publish, media |
| `defaults` | view, edit, publish |
| `settings` | view, edit, publish, flags, announcements |
| `communications` | view, compose, send |
| `operations` | view, retry_jobs, logs |
| `staff` | view, manage, roles, approvals |
| `audit` | view, export |

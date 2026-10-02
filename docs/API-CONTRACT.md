# API Contract v0 (draft) — Formalie

Shared by frontend (mocks) and backend (implementation). Bump the version and update this file on every change. Final contract is generated from FastAPI OpenAPI at hand-over.

## Conventions

- Base: `/api/v1`. All requests/responses use the encryption envelope (SECURITY-PROTOCOL.md); shapes below are the **decrypted** payloads.
- Auth: `Authorization: Bearer <fernet>`; `X-CSRF-Token` on POST/PUT/PATCH/DELETE; tenant from host.
- Success: `{ "success": true, "data": …, "meta": {…} }`
- Error: `{ "success": false, "error": { "code", "message", "trace_id", "details": [{ "field", "message" }] } }`
- Lists: query `page`, `page_size` (≤100), `q`, `sort` (`-updated_at`), `filter[status]=published`, `from`, `to` (ISO dates); meta `{ page, page_size, total, total_pages }`. Large sets: `cursor` instead of `page`, meta `{ next_cursor }`.
- IDs are UUID strings; timestamps ISO-8601 UTC.
- Optimistic locking: editable resources return `row_version`; updates send it; mismatch → `FRM-GEN-1009`.

## Crypto / session

| Method | Path                | Notes                    |
| ------ | ------------------- | ------------------------ |
| POST   | `/crypto/handshake` | plaintext; ECDH exchange |
| GET    | `/auth/csrf`        | CSRF token               |
| GET    | `/health`           | plaintext                |

## Tenants and onboarding

| GET | `/tenants/public` | public profile of current host: `{ mode: manage\|tenant, name, subdomain, logo_url, colors: { primary }, auth_providers[], status }`; unknown host → FRM-TEN-1001, suspended → FRM-TEN-1002 |
| GET | `/tenants/subdomain-availability?subdomain=` | `{ available, reason: taken\|reserved\|invalid\|null }` |
| POST | `/tenants/find-workspace` | `{ email }` → challenge (same answer whether or not the email exists) |
| POST | `/tenants/find-workspace/verify` | `{ challenge_id, code }` → `[{ name, subdomain, url }]` (url = that workspace's `/auth/login?email=`) |
| GET/PATCH | `/onboarding` | progress + steps data |

## Auth

| POST | `/auth/signup` | manage.* only. `{ first_name, last_name, email, password }` or provider token → challenge |
| POST | `/auth/signup/complete` | `{ challenge_id, company_name, subdomain }` (challenge already verified via `/auth/otp/verify`) → `{ redirect_url }` on the new subdomain carrying a one-time `ticket` |
| POST | `/auth/exchange-ticket` | `{ ticket }` (≤ 2 min, single use, must match the host's tenant) → tokens + refresh cookie |
| POST | `/auth/login` | `{ email, password }` → challenge `{ challenge_id, channels[], channel, masked_destination, resend_after, expires_at }` |
| GET | `/auth/oauth/{provider}/start?intent=login\|signup` | plain redirect to the provider. `login` (workspace host): callback → challenge as for password login. `signup` (manage.* only, any of google / microsoft / apple / facebook): callback redirects to manage `/auth/signup?social=<one-time token>`; the email is provider-verified, so the Verify step is skipped and `/auth/signup/complete` accepts `{ social_token, company_name, subdomain }` instead of `challenge_id`. The new workspace enables `password` + the provider used; admins enable more in Settings → Authentication |
| POST | `/auth/otp/verify` | `{ challenge_id, code }` → login: `{ access_token, expires_in, user, tenant, organisation }` + refresh cookie; signup: `{ verified: true }`. Wrong code → FRM-AUTH-1003 with `details: [{ field: "attempts_left", message: "<n>" }]`; out of attempts → FRM-AUTH-1004 |
| POST | `/auth/otp/resend` | `{ challenge_id, channel }` |
| POST | `/auth/refresh` | cookie → same shape as otp/verify (tokens + user/tenant/organisation), rotated cookie; reused token → FRM-AUTH-1012 (family revoked) |
| POST | `/auth/logout` | revokes session |
| POST | `/auth/password/forgot` | `{ email }` → challenge (same answer whether or not the email exists) |
| POST | `/auth/password/reset` | `{ challenge_id, code, password }` → `{ reset: true }` |
| GET | `/me` · PATCH `/me` · POST `/me/password` · `/me/mfa/totp/*` · GET/DELETE `/me/sessions/{id}` | |

**`user`** (in tokens and `/me`): `{ id, first_name, last_name, email, avatar_url, role: owner|admin|member }`. `role` is the simple workspace role until Roles & access (F19); owner and admin manage the workspace (e.g. the audit trail).

**Refresh cookie:** `formalie_rt`, `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` (covers refresh + logout).
**Mock only:** challenge responses carry `meta.dev_code` so the dev code screen can show it; the real API never returns codes. The mock honours the dev header `X-Formalie-Dev-Tenant` (localhost / LAN-IP testing).

## Audit trail

Owners / admins only (members → FRM-PERM-1001) until permissions arrive with Roles & access (F19). Every state-changing endpoint and every sign-in event writes one entry; action keys and areas are listed once in `shared/utils/audit/events.ts`.

| Method | Path                 | Notes                                                                                                                                                                                                                                                           |
| ------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/audit-logs`        | list, default `sort=-occurred_at`; filters `area`, `action`, `outcome`, `actor_id`, `country`, `resource_type`, `resource_id` (comma = any of); `from` / `to` on `occurred_at`; `q` searches person, email, item, IP, city, request id, action → `AuditEvent[]` |
| GET    | `/audit-logs/{id}`   | one `AuditEvent`                                                                                                                                                                                                                                                |
| GET    | `/audit-logs/facets` | `{ actors: [{ id, name }], countries: [ISO-2] }` for the filter menus                                                                                                                                                                                           |
| POST   | `/audit-logs/export` | `{ format: xlsx\|csv, filters: { q?, from?, to?, "filter[…]"? } }` → 202 `ExportJob`; the export itself is recorded (`audit.exported`)                                                                                                                          |
| GET    | `/exports/{id}`      | `ExportJob { id, status: queued\|running\|done\|failed, progress (0–100), rows, format, file_name, download_url\|null, expires_at\|null }` — poll until `done`                                                                                                  |
| GET    | `/downloads/{token}` | **plain** file response (a browser download cannot carry the envelope). The token is the permission: random 256-bit, single use, 10 minutes, bound to the workspace host that created it; `Cache-Control: no-store`; expired / used → 410                       |

`AuditEvent`: `{ id, occurred_at, action, area, outcome: success|failure|blocked, severity: info|notice|warning|critical, actor: { type: user|api_key|system, id|null, name, email|null }, resource: { type, id|null, name|null }|null, organisation: { id, name }|null, location: { ip, city|null, country|null }, device: { type: desktop|mobile|tablet|unknown, browser|null, os|null }, changes: [{ field, before, after }], metadata: { [key]: string }, reason: FRM-code|null, request_id }`. `actor.id` is null for attempts by someone who is not signed in (name = the email typed). CSV / Excel exports neutralise cells starting with `= + - @` (formula injection) and are UTF-8 with a byte-order mark.

**Mock only:** the mock writes CSV for both formats (the backend produces a real .xlsx); local / private IPs have no city or country (the backend resolves them with GeoIP).

## Forms

| GET | `/forms` | list (filters: status, folder_id, owner_id, tag — comma = any of; from/to on `updated_at`; archived only when `filter[status]` asks) → `FormSummary[]`: `{ id, name, slug, status, has_unpublished_changes, folder: {id,name}\|null, owner: {id,name}, tags[], responses_count, completion_rate (0–100), created_at, updated_at }` |
| POST | `/forms` | `{ name, folder_id?, template_id?, schema? }` |
| GET | `/forms/{id}` | `{ id, name, slug, status, has_unpublished_changes, draft: FormSchema, row_version, theme_id, settings, seo, published_version, updated_at }` |
| PATCH | `/forms/{id}` | name, folder, tags, settings, seo |
| PUT | `/forms/{id}/draft` | `{ schema: FormSchema, row_version }` (autosave) |
| POST | `/forms/{id}/publish` | `{ change_summary? }` → version |
| POST | `/forms/{id}/unpublish` · `/close` · `/reopen` · `/duplicate` · `/archive` | |
| DELETE | `/forms/{id}` | soft delete; POST `/forms/{id}/restore` |
| GET | `/forms/{id}/versions` · GET `/forms/{id}/versions/{vid}` · POST `/forms/{id}/versions/{vid}/restore` (into draft) | |
| GET/POST/PATCH/DELETE | `/folders` | |

## Design, templates, option sets

| CRUD | `/themes` | `{ name, tokens }` |
| GET | `/templates` (system + org; filter category) · POST `/templates` (save as) · POST `/templates/{id}/use` | |
| CRUD | `/option-sets`, `/option-sets/{id}/items` (bulk upsert, reorder) | |

## Sharing, links, embed

| GET/PUT | `/forms/{id}/share` | access mode, password, expiry, limits, schedule |
| GET/POST/DELETE | `/forms/{id}/grants` | `{ user_id, access: edit|view|responses }` |
| GET/PUT | `/forms/{id}/slug` | availability + set |
| POST | `/forms/{id}/short-link` | `{ code, url }` |
| GET/PUT | `/forms/{id}/embed` | allowed domains, settings, snippet |

## Public (respondent, no login; tenant from host)

| GET | `/public/forms/{slug}` | published schema + theme + seo (cached) |
| POST | `/public/forms/{slug}/unlock` | password-protected |
| POST | `/public/forms/{slug}/sessions` | start/resume → `resume_token` |
| POST | `/public/forms/{slug}/uploads` | pre-signed upload URL |
| POST | `/public/forms/{slug}/submit` | `{ data, resume_token?, captcha_token }` → `{ response_id, thank_you }` |
| GET | `/public/s/{code}` | short link resolve (root domain) |

## Responses

| GET | `/forms/{id}/responses` | filters per field (`filter[field_key][op]=value`), status, tag, from, to |
| GET/PATCH/DELETE | `/responses/{id}` | status, tags, edit (history kept) |
| GET/POST | `/responses/{id}/notes` | |
| GET | `/responses` | inbox across forms |
| POST | `/forms/{id}/exports` | `{ format: xlsx|csv|pdf, scope: all|filtered|selected, filters, ids }` → job |
| GET | `/exports/{job_id}` | `{ status, progress, download_url? }` |

## Integrations, settings, analytics

| CRUD | `/destinations` (+ POST `/destinations/test`) · `/webhooks` · `/api-keys` | |
| GET/PATCH | `/settings/{section}` | company, branding, auth, security, localisation, notifications, retention, embed |
| GET | `/forms/{id}/analytics?from=&to=` | summary, timeseries, per-field stats, drop-off |
| GET | `/platform/countries`, `/platform/states?country=`, `/platform/timezones`, `/platform/currencies` | |

## Later (last phases)

`/users`, `/invitations`, `/roles`, `/permissions`, `/dashboard?from=&to=`, `/billing/*`. (The audit trail moved up — see Audit trail.)

## FormSchema (v1)

```json
{
  "schema_version": 1,
  "settings": { "progress_bar": true, "save_resume": false, "language": "en" },
  "pages": [
    {
      "id": "pg_…",
      "title": "Page 1",
      "rows": [
        {
          "id": "row_…",
          "fields": [
            {
              "id": "fld_…",
              "key": "full_name",
              "type": "short_text",
              "label": "Full name",
              "placeholder": "",
              "help": "",
              "width": 12,
              "required": true,
              "validation": {
                "min_length": 2,
                "max_length": 120,
                "pattern": null
              },
              "options": null,
              "option_set_id": null,
              "default": null,
              "props": {}
            }
          ]
        }
      ]
    }
  ],
  "logic": [
    {
      "id": "rule_…",
      "when": { "all": [{ "field": "fld_a", "op": "eq", "value": "yes" }] },
      "then": [{ "action": "show", "target": "fld_b" }]
    }
  ],
  "calculations": [],
  "thank_you": { "title": "Thank you!", "message": "", "redirect_url": null }
}
```

Theme tokens (`themes.tokens`): `{ layout, page: { bg, bg_image, overlay }, container: { width, padding, radius, border, shadow, bg }, typography: { font, base_size, heading_weight }, colors: { primary, text, muted, input_bg, input_border, error }, inputs: { radius, size, style }, buttons: { radius, variant, full_width }, header: { image, logo, align } }`.

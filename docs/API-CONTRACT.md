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

| GET | `/tenants/public` | public profile of current host: `{ name, subdomain, logo_url, colors, auth_providers[], status }` |
| GET | `/tenants/subdomain-availability?subdomain=` | `{ available, reason }` |
| POST | `/tenants/find-workspace` | `{ email }` → OTP sent |
| POST | `/tenants/find-workspace/verify` | `{ challenge_id, code }` → `[{ name, subdomain, url }]` |
| GET/PATCH | `/onboarding` | progress + steps data |

## Auth

| POST | `/auth/signup` | `{ first_name, last_name, email, password }` or provider token → `{ challenge_id, channels }` |
| POST | `/auth/signup/complete` | `{ challenge_id, code, company_name, subdomain }` → tokens + redirect url |
| POST | `/auth/login` | `{ email, password }` → `{ challenge_id, channels, masked_destination }` |
| GET | `/auth/oauth/{provider}/start` | redirect; `/auth/oauth/{provider}/callback` → challenge |
| POST | `/auth/otp/verify` | `{ challenge_id, code }` → `{ access_token, expires_in, user, tenant, organisation }` + refresh cookie |
| POST | `/auth/otp/resend` | `{ challenge_id, channel }` |
| POST | `/auth/refresh` | cookie → new access token, rotated refresh cookie |
| POST | `/auth/logout` | revokes session |
| POST | `/auth/password/forgot` · `/auth/password/reset` | |
| GET | `/me` · PATCH `/me` · POST `/me/password` · `/me/mfa/totp/*` · GET/DELETE `/me/sessions/{id}` | |

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

`/users`, `/invitations`, `/roles`, `/permissions`, `/audit-logs`, `/dashboard?from=&to=`, `/billing/*`.

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

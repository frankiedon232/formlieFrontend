# Frontend reference: what the backend must reproduce

The frontend (`C:\UNETPROJECTS\formalieFrontend`, read only, never change it) was built first, against a mock API that behaves like the real backend. Three parts of it are the backend's specification:

1. **`shared/`** holds code the frontend and the mock both run. Every rule in it must give the same answer on the server, because the server is the one that decides (the browser only checks first, for speed).
2. **`server/mock/`** is the reference implementation: what each endpoint stores, checks, returns and records. `docs/ENDPOINTS.md` lists every route with its mock file.
3. **`i18n/locales/en.json`** holds the user-facing wording. Error messages come from the codes (`ERROR-CODES.md`); the frontend translates them, so the backend returns codes, never translated text.

## Port these with parity tests

Port each file to Python under the named module. For each one, write a test that runs the same inputs as the frontend's tests (`test/**` in the frontend), so both sides agree. Where the frontend has no test, take examples from the mock data.

| Frontend file (`shared/utils/…`) | What it decides | Backend module |
| --- | --- | --- |
| `crypto/envelope.ts`, `crypto/encoding.ts` | The encryption envelope (SECURITY-PROTOCOL §1 to §3) | `core/security/envelope.py` (shared test vectors) |
| `errors/codes.ts` | Every `FRM-*` code, HTTP status and level | `core/errors/codes.py` (generated from or checked against it) |
| `auth/permissions.ts` | The permission catalogue: areas, groups, actions and scopes (None, Own, Shared, Own & shared, All) | `modules/rbac` (seed + checks) |
| `auth/password.ts` | Password policy | `core/security/passwords.py` |
| `audit/events.ts` | Every audit action key, its area and severity | `modules/audit` (catalogue + `record()`) |
| `forms/schema.ts`, `forms/fields.ts`, `forms/build.ts`, `forms/catalogues.ts` | The FormSchema and field types | `modules/forms/schema.py` (Pydantic) |
| `forms/validate.ts` | Publish checks | `modules/forms/publish.py` |
| `forms/submission.ts`, `forms/masks.ts`, `forms/file-types.ts`, `forms/file-answers.ts` | Submission validation: types, masks, required, files | `modules/public/submit.py` |
| `forms/logic.ts`, `forms/details.ts`, `forms/cascade.ts` | Show / hide / skip / require logic, list details, cascading lists | `modules/forms/logic.py` |
| `forms/formula.ts` | Calculations (`{field}`, `{field.detail}`) | `modules/forms/formula.py` |
| `forms/availability.ts`, `forms/access.ts`, `forms/identity.ts`, `forms/fills.ts` | Whether a form is open, who may fill it, one response per person | `modules/public/availability.py` |
| `forms/proof-of-work.ts` | The anti-bot proof of work on public submit | `modules/public/pow.py` |
| `forms/prefill.ts` | URL prefill | `modules/public` |
| `forms/answer-edit.ts`, `forms/answer-filter.ts`, `forms/answer-text.ts` | Editing answers, response filters, answers as text (exports) | `modules/responses` |
| `forms/options.ts`, `forms/translations.ts`, `forms/emails.ts`, `forms/theme.ts`, `forms/page-design.ts`, `forms/fonts.ts`, `forms/folders.ts` | Options, form translations, response emails, theme and page design tokens, the 21 font keys, folders | matching modules |
| `apiService/*` (`access`, `choices`, `endpoints`, `origins`, `tokens`, `snippets`) | The public API service: access rules, choices in and out, endpoint shapes, allowed websites (CORS), tokens | `modules/api_service` |
| `datasources/*` (`ddl`, `engines`, `sql`, `tables`, `values`, `permissions`, `activity`, `exportFormats`) | Response storage tables in the customer's database, engines, SQL safety, value mapping | `modules/data_sources` |
| `integrations/databases.ts`, `integrations/webhooks.ts` | Database connections and webhook signing | `modules/destinations`, `modules/webhooks` |
| `billing/plans.ts` | Plans, prices per period, limits and features | `modules/billing` (seed + enforcement) |
| `platform/regions.ts`, `platform/countries.ts`, `platform/forms.ts` | Data residency regions, countries, Formalie's own forms (support, enquiries) | platform seeds |
| `settings/schemas.ts`, `settings/appearance-ink.ts` | Settings validation per section, appearance contrast | `modules/settings` |
| `dashboard/buckets.ts`, `dashboard/scope.ts` | Dashboard periods and folder / owner scope | `modules/dashboard` |
| `templates/starters.ts`, `help/categories.ts`, `help/routes.ts`, `ai/kinds.ts` | Template starters, help categories, tour pages, AI kinds | matching modules |
| `tenant/host.ts`, `urls/public.ts`, `urls/embed.ts`, `urls/embed-domains.ts` | Tenant from the host, public link building, embed rules | `core/middleware/tenant.py`, `modules/links` |
| `i18n/locales.ts` | The 20 languages | platform seed |

The types in `shared/types/*.ts` are the response shapes. The Pydantic models must produce exactly these fields (snake_case, the same nullability).

## Default data to seed (from the mock)

Every new workspace starts from Formalie's default data, which the backend seeds. Read the shapes in the mock:
- `server/mock/data/libraryStore.ts`: system lists, simple ones and ones with levels, large lists.
- `rolesStore.ts`: built-in roles. Owner is fixed and holds everything.
- `formStore.ts` / `forms.ts`: default folders.
- `emailDefaults/`: email templates.
- `templateStore.ts`: system templates.
- `helpStore.ts` and `help/`: help articles and the 12 tours. The platform admin later edits these through the global tables (PLATFORM-ADMIN-INTEGRATION.md).
- `platformStore.ts`: platform settings, such as legal links.

## Things the mock fakes that the real backend does for real

| In the mock | Real backend |
| --- | --- |
| OTP code returned as `meta.dev_code` | Sent by email (Mailpit in development). Never returned. |
| `X-Forwarded-For`, `X-Debug-Country`, `X-Debug-Network` headers on the public API | The connection's address and GeoIP (MaxMind) |
| Data source connections simulated (`dataSourceSim.ts`, `databaseRows.ts`, `queryEngine.ts`) | Real connections to Postgres, MySQL, SQL Server and the other engines in `datasources/engines.ts`, through Celery writers |
| AI answers from local engines (`server/mock/ai/*`) | The chosen AI provider. Same request and response shapes, same allowance (`requireAi`) |
| Payoneer checkout and webhook simulated (`billingCheckout.ts`, `billing/webhook.ts`) | The real Payoneer API, with the same idempotency rules (SECURITY-PROTOCOL §11) |
| In-memory stores, lost on restart | PostgreSQL (DATABASE-DESIGN.md) |
| Emails written to a list (`responseEmails.ts`, `emails.ts`) | Sent through the workspace's sending setup (Formalie address, own domain or SMTP) by Celery |
| Fixed seeded test workspaces and accounts (`data/tenants.ts`) | Real sign-up. Keep a development seed with the same workspaces so the frontend's tests still work |

## How the frontend switches over

`NUXT_PUBLIC_API_MOCK=false` sends every `/api/**` call through the dev proxy (`server/proxy/api.ts`) to `https://formalie.dev:5004`, keeping the host so the backend sees the subdomain. Switch area by area as the ENDPOINTS.md boxes get ticked, then turn the mock off for good.

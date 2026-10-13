# What the website reads from Formalie

The website has **no backend of its own**. It reads a few public endpoints of the Formalie API and shows Formalie's own published forms.

**`{API}`** is `NUXT_PUBLIC_API_URL`: `https://formalie.dev:5004/api/v1` in development, `https://services.formalie.com/api/v1` in production (never `api.formalie.com`, which is customers' own API service). The public routes are live in development since 2026-10-13 (formlyBackend `docs/API-CONTRACT.md`). Every answer is plain JSON `{ success, data, meta }` (no encryption envelope), served on any host with `Access-Control-Allow-Origin: *`. Read `data`. Everything is public, read only and cacheable. No tokens or secrets live in the site.

## 1. Plans and prices

```
GET {API}/public/plans               → Plan[] (same shape as the app's shared/types/billing.ts)
```

```ts
interface Plan {
  id: 'starter' | 'professional' | 'business' | 'enterprise'
  prices: { monthly: number; quarterly: number; annually: number } | null // null = contact us
  currency: string // 'USD'
  limits: { forms: number | null; responses_per_form: number | null; databases: ('mysql' | 'postgresql' | 'sqlserver' | 'oracle' | 'mariadb')[]; social_signin: boolean; sso: boolean; custom_domains: number | null; custom_email: boolean; data_residency: boolean; ai_credits: number | null; languages: number }
  features: string[] // comparison rows the plan includes (PRICING.md)
  recommended?: boolean
}
```

- **Edited by:** the owner, in the platform admin.
- **Live** (published by the platform admin, else the backend's catalogue). `features` uses the backend's keys (`analytics`, `templates`, `lists`, `themes`, `explorer`, `query`, `destinations`, `api`, `webhooks`, `apiDocs`, `ai`, `branding`, `subdomain`, `languages`, `visits`, `versions`, `folders`, `fillLater`, `sso`, `customDomain`, `customEmail`, `prioritySupport` and more); unknown keys are ignored. `limits.social_signin` may be missing (it is on every plan).
- **Fallback:** when the API doesn't answer, the site uses a copy of `docs/PRICING.md` (`app/data/plans.json`), clearly marked as samples.
- **Payments:** Paddle, the merchant of record. The site never takes payments: "Payments handled by Paddle" near the prices.

## 2. Legal documents

```
GET {API}/public/legal                → [{ slug, title, version, updated_at, languages[], status: 'published' | 'draft' }]
GET {API}/public/legal/{slug}?lang=   → { slug, title, version, updated_at, summary_of_changes, language, status, sections[{ id, heading, body_markdown }] }   (unknown slug: 404 FRM-GEN-1004)
```

- **Edited by:** the owner, in the platform admin. See `LEGAL-PAGES.md`.

## 3. Platform settings (contact details, social links)

```
GET {API}/public/platform             → { support_email, sales_email, status_url, social: { linkedin?, x?, youtube?, github? }, legal_entity: { name, address } }
```

- **Edited by:** the owner, in the platform admin (the same "platform settings" the portal reads).

## 4. Formalie's own forms (collect data with our own product)

The website never builds its own forms. Contact, sales and newsletter are **published forms in Formalie's own workspace**, shown embedded with the portal's embed script (auto-height, prefill through the address):

| Use | Form key | Embed (dev) | Prefill the site may pass |
|---|---|---|---|
| Enterprise enquiry ("Talk to sales", `/enterprise`) | `FormalieEn` | `https://forms.formalie.dev:2202/FormalieEn/embed` | `plan`, `period`, `needs=residency`, `residency`, `company`, `email` |
| Contact support (`/contact`) | `FormalieHp` | `https://forms.formalie.dev:2202/FormalieHp/embed` | `topic`, `subject`, `email` |
| Newsletter (footer, later) | to be created by the owner | `…/{key}/embed` | `email`, `language` |

- The keys are defined in the app at `shared/utils/platform/forms.ts`. Production uses `https://forms.formalie.com/{key}/embed`.
- The embed sends `formalie:resize` (`{ type, key, height }`), `formalie:typing` and `formalie:submitted` (`{ type, key }`) to the page. `SiteFormEmbed` reads only messages from the forms origin about its own form, sizes the frame, and shows a thank-you toast. It adds `?lang={locale}` so the form opens in the visitor's language, and only the prefill fields listed above.
- **Answers:** they arrive as normal responses in Formalie's workspace and show in the platform admin. The owner said "we will handle the linking to the portal forms later", so wire the frames in phase S6 (`PROGRESS.md`).

## 5. Sign-up and sign-in links

See `SIGNUP-FLOW.md`. These are only links to the portal (`NUXT_PUBLIC_PORTAL_URL`), never API calls.

## Rules

- Call the API only from `useFetch` / `$fetch` inside composables (`usePlans`, `useLegal`, `usePlatform`), with a timeout and a fallback, so the page still renders if the API is slow.
- Cache: plans and platform settings for 5 minutes; legal documents for 1 hour (or until the version changes).
- Never send personal data from the site to anything except Formalie's own forms.

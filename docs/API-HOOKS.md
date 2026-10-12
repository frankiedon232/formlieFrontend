# What the website reads from Formalie

The website has **no backend of its own**. It reads a few public endpoints of the Formalie API and shows Formalie's own published forms. Everything is public, read only and cacheable. No tokens or secrets live in the site.

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
- **Today:** the portal's mock serves `GET /billing/plans` behind sign-in. **The backend adds the public `/public/plans`.** Until then, the site uses a copy of `docs/PRICING.md` as a fallback file (`app/data/plans.json`), clearly marked as samples.

## 2. Legal documents

```
GET {API}/public/legal                → [{ slug, title, version, updated_at, languages[] }]
GET {API}/public/legal/{slug}?lang=   → { slug, title, version, updated_at, summary_of_changes, sections[{ id, heading, body_markdown }] }
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
- The embed sends `formalie:resize` (height) and `formalie:submitted` messages to the page. Listen for them to size the frame and show a thank-you toast.
- **Answers:** they arrive as normal responses in Formalie's workspace and show in the platform admin. The owner said "we will handle the linking to the portal forms later", so wire the frames in phase S6 (`PROGRESS.md`).

## 5. Sign-up and sign-in links

See `SIGNUP-FLOW.md`. These are only links to the portal (`NUXT_PUBLIC_PORTAL_URL`), never API calls.

## Rules

- Call the API only from `useFetch` / `$fetch` inside composables (`usePlans`, `useLegal`, `usePlatform`), with a timeout and a fallback, so the page still renders if the API is slow.
- Cache: plans and platform settings for 5 minutes; legal documents for 1 hour (or until the version changes).
- Never send personal data from the site to anything except Formalie's own forms.

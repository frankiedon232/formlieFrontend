# PROGRESS, formalieSite

**Last updated:** 2026-10-13 (S0 done, waiting for the owner's review; backend public endpoints, legal pages, /trust, security.txt and Paddle recorded)

| Phase | What | Status | Done |
|---|---|---|---|
| S0 | Project set-up | ✅ (review) | 100% |
| S1 | Layout, header, footer, theme, languages | ⬜ | 0% |
| S2 | Home page with the data-flow hero | ⬜ | 0% |
| S3 | Features and solutions pages | ⬜ | 0% |
| S4 | Pricing | ⬜ | 0% |
| S5 | Legal pages (documentation layout) and /trust | ⬜ | 0% |
| S6 | Formalie forms, portal links, contact and enterprise | ⬜ | 0% |
| S7 | SEO, performance, accessibility, launch checks | ⬜ | 5% |

**Every phase is only done when:**
- phone, tablet and desktop are checked;
- light and dark are checked, and Arabic right to left;
- it is keyboard-only usable;
- every string is in all 20 languages;
- it matches `docs/DESIGN.md` (compared with the references);
- typecheck, lint and tests are green;
- the docs are updated, and the work is committed and pushed.

---

## S0, Project set-up
- ✅ Nuxt 4.5, Nuxt UI 4, Tailwind 4, TypeScript strict, pnpm, ESLint and Prettier (same settings as the app), Vitest
- ✅ `@nuxtjs/i18n` with the 20 languages (same list and flags as the app), `@nuxt/content`, `@vueuse/nuxt`
- ✅ Dev server on `https://formalie.dev:3033` with the dev certificate (`docs/02-DEV-ENVIRONMENT.md`)
- ✅ Theme tokens copied from the app (`docs/reference/main.css.excerpt`): Manrope self-hosted, monochrome ink, radius, animations
- ✅ `useSiteLinks()` (portal, forms, API addresses from the runtime config)
- ✅ Screenshots copied to `public/screenshots/` as WebP (light and dark), `pnpm screenshots`
- ✅ Brand files from `docs/brand/web/` in `public/`; the Field F glyph as the `i-formalie-mark` icon
- ✅ `/.well-known/security.txt` (formlyBackend `docs/legal/security.txt`), 2026-10-13 request
- ✅ `pnpm generate` prerenders every language (static files, `.output/public`)

## S1, Layout
- ⬜ Header (logo, Product and Solutions dropdowns, Pricing, Integrations, Resources, Contact, language, theme, Sign in, Start free); phone slide-over
- ⬜ Footer (four columns, legal row with Refunds and cancellation, language, ©)
- ⬜ Language switch (flags), right to left for Arabic, `hreflang`
- ⬜ A self-hosted fallback font for the scripts Manrope lacks (Arabic, Devanagari, Bengali, CJK)
- ⬜ 404 page

## S2, Home
- ⬜ Hero: headline, subline, two buttons, and the **data-flow animation, website version** (`docs/DESIGN.md`); the hub always shows Formalie
- ⬜ Trust strip (sectors, until real logos)
- ⬜ Answers from everywhere (four cards)
- ⬜ Product tabs (Build, Design, Responses, Data, API) with screenshots
- ⬜ What sets Formalie apart (six cards)
- ⬜ Security band (dark)
- ⬜ Integrations orbit
- ⬜ Languages strip
- ⬜ Pricing teaser · FAQ · final call to action

## S3, Features and solutions
- ⬜ `/features` overview and the 11 feature pages (`docs/FEATURES.md`)
- ⬜ The 7 solution pages, with the templates to start from
- ⬜ `/integrations`, `/security`, `/about`

## S4, Pricing
- ⬜ `usePlans()` reading `GET {API}/public/plans` (live at `https://formalie.dev:5004/api/v1`, `{ success, data, meta }`), with the fallback file (samples, `docs/PRICING.md`) when the API doesn't answer
- ⬜ Period toggle (Monthly · Quarterly −10% · Annually −20%), four plan cards (Starter free, Professional and Business with three periods, Enterprise "Contact us"), "Most popular"
- ⬜ "Payments handled by Paddle" near the prices (no logo yet); refunds FAQ links to `/legal/refunds`
- ⬜ Full comparison table (grouped), pricing FAQ, structured data with offers
- ⬜ Buttons lead to the portal sign-up with `plan` and `period`; Enterprise leads to the enquiry

## S5, Legal pages and trust
- ⬜ `legal` layout: documents navigator, article, "On this page", last updated, version, print and PDF
- ⬜ `useLegal()` reading `GET {API}/public/legal…` (`docs/LEGAL-PAGES.md`), English fallback with a notice; a small "Draft" note while `status` is `draft`
- ⬜ Fallback copy in `content/legal/` from formlyBackend `docs/legal/` for when the API doesn't answer (no invented wording)
- ⬜ Privacy policy · Terms and conditions · Data protection · Cookie policy · Acceptable use · Subprocessors · Refunds and cancellation (7th, after subprocessors)
- ⬜ Redirects `/terms`, `/privacy`, `/refunds` → `/legal/terms`, `/legal/privacy`, `/legal/refunds`
- ⬜ `/trust` "Trust and security" from formlyBackend `docs/legal/trust-and-security.md`, without "Independent checks (when ready)"

## S6, Formalie forms and portal links (owner: "we will handle the linking to the portal forms later")
- ⬜ Embedded Enterprise enquiry (`FormalieEn`) on `/enterprise` and from pricing, with prefill
- ⬜ Embedded Contact support (`FormalieHp`) on `/contact`
- ⬜ Newsletter form (when the owner creates it)
- ⬜ Portal links checked (sign-up with plan and period, sign-in → find workspace)
- ⬜ The portal links back to the legal pages (privacy on every form, terms on sign-up)

## S7, Launch checks
- ⬜ SEO (`docs/SEO.md`): titles, descriptions, OG images, sitemap, robots, structured data
- ⬜ Lighthouse 95+ on mobile, no layout shift, images sized
- ⬜ Accessibility: keyboard, focus, headings, contrast, reduced motion
- ⬜ Security headers and CSP (`docs/SECURITY.md`; `connect-src https://services.formalie.com`); ✅ `security.txt` (S0)
- ⬜ Production build (`nuxt generate`) and deployment notes

---

## New requests log

| Date | Request | Phase | Status |
|---|---|---|---|
| 2026-10-10 | Website after the owner's three reference screens; the hero grows from the sign-in data-flow animation in its own way; legal pages look like documentation; legal text comes from the platform admin later; links to the portal forms later; only cropped, watermarked screens of the app | S0 to S6 | ⬜ |
| 2026-10-13 | Backend ready: read `/public/plans`, `/public/legal`, `/public/legal/{slug}?lang=`, `/public/platform` at `NUXT_PUBLIC_API_URL` (`https://formalie.dev:5004/api/v1`; production `https://services.formalie.com/api/v1`, never `api.formalie.com`), plain `{ success, data, meta }`; keep fallback data | S4, S5 | ⬜ |
| 2026-10-13 | Legal pages from formlyBackend `docs/legal/`; a 7th slug `refunds` after subprocessors; "Draft" note while a document is a draft; Paddle is the merchant of record; redirect `/terms`, `/privacy`, `/refunds` | S5 | ⬜ |
| 2026-10-13 | `/trust` "Trust and security" page from `docs/legal/trust-and-security.md`, without "Independent checks (when ready)" | S5 | ⬜ |
| 2026-10-13 | Serve formlyBackend `docs/legal/security.txt` at `/.well-known/security.txt` | S0 | ✅ |
| 2026-10-13 | Pricing from `/public/plans`; "Payments handled by Paddle" near the prices, no logo yet | S4 | ⬜ |
| 2026-10-13 | Copy formlyBackend `docs/PRODUCTION-CHECKLIST.md` over this project's copy | Docs | ✅ (already identical; DEPLOYMENT-GUIDE synced too) |

## Progress log

| Date | Phase | What |
|---|---|---|
| 2026-10-10 | Package | Docs, references, 25 screenshots (light and dark, cropped, watermarked, sample data) and the app's animation prepared from formalieFrontend |
| 2026-10-13 | Docs | Backend hand-over recorded: API address (`services.formalie.com`, never `api.formalie.com`), Paddle instead of Payoneer, the `refunds` legal page, redirects, `/trust`, `security.txt`; PRODUCTION-CHECKLIST already identical to formlyBackend's, DEPLOYMENT-GUIDE synced |
| 2026-10-13 | S0 | Nuxt 4.5.2, Nuxt UI 4.11, Tailwind 4, strict TypeScript, ESLint and Prettier (the app's settings), Vitest (47 tests: links, 20 locale files with every key and no em dashes); i18n with 20 languages (prefix strategy, Arabic right to left, `hreflang`); `@nuxt/content` (blog, changelog, legal collections); `@nuxt/image`; Manrope self-hosted; the app's theme tokens; `useSiteLinks()`; 25 screenshots as WebP; brand files; `security.txt`; dev server on `https://formalie.dev:3033`; `pnpm generate` prerenders all 20 languages |

# PROGRESS, formalieSite

**Last updated:** 2026-10-13 (S5 done, waiting for the owner's review)

| Phase | What | Status | Done |
|---|---|---|---|
| S0 | Project set-up | ✅ | 100% |
| S1 | Layout, header, footer, theme, languages | ✅ | 100% |
| S2 | Home page with the data-flow hero | ✅ | 100% |
| S3 | Features and solutions pages | ✅ | 100% |
| S4 | Pricing | ✅ | 100% |
| S5 | Legal pages (documentation layout) and /trust | ✅ (review) | 100% |
| S6 | Formalie forms, portal links, contact and enterprise | ⬜ | 0% |
| S7 | SEO, performance, accessibility, launch checks | ⬜ | 30% |

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
- ✅ Header (logo, Product and Solutions panels with icon tiles, Pricing, Integrations, Resources, Contact, language, theme, Sign in, Start free); phone and tablet slide-over below 1280 px
- ✅ Footer (four columns, legal row with Subprocessors and Refunds and cancellation, language, theme, ©)
- ✅ Language switch (flags, remembers the choice), right to left for Arabic, `hreflang`
- ✅ Self-hosted fallback fonts for the scripts Manrope lacks (Noto Sans Arabic, Devanagari, Bengali; CJK uses system fonts)
- ✅ 404 and error page inside the site layout, in every language; skip-to-content link

## S2, Home
- ✅ Hero: headline, subline, two buttons, and the **data-flow animation, website version** (`docs/DESIGN.md`, `components/flow/Hero.vue`): five live source cards (a field typing, an embed frame, a QR being scanned, an API call, a mobile app), the Formalie hub (inverse mark, lock, "Encrypted on the way", a pulse per answer), five destinations that light up (the database cycles its engine logos, the dashboard grows a bar), drifting response cards, illustrative counters; phones stack top to bottom; still for reduced motion, paused off screen (`useSectionMotion`)
- ✅ Trust strip (sectors, until real logos)
- ✅ Answers from everywhere (four cards, each with a small live picture, lines into "All in one place")
- ✅ Product tabs (Build, Design, Responses, Data, API) with screenshots in a browser frame (dark screens in dark mode)
- ✅ What sets Formalie apart (six cards with ink icon tiles)
- ✅ Security band (dark, with a live audit trail of sample entries)
- ✅ Integrations orbit (two counter-rotating rings of database and sign-in logos)
- ✅ Languages strip (`UMarquee`, the 20 names in their own scripts)
- ✅ Pricing teaser (live plans, "Payments handled by Paddle", "Sample prices" badge on fallback) · FAQ (with FAQPage data) · final call to action

## S3, Features and solutions
- ✅ `/features` overview (alternating blocks with the real screens) and the 11 feature pages (`docs/FEATURES.md`): hero with the screen or a drawn visual (the AI assistant drafting a form; one question turning through seven languages), feature cards, "How it works" with a travelling point, related features, call to action
- ✅ The 7 solution pages: the problem, the two templates to start from, where the data goes, a flow visual (templates → Formalie → destinations), the features used
- ✅ `/integrations` (logo marquee, databases, API and webhooks, sign-in, open standards), `/security` (dark hero with packets crossing a shield, the controls, responsible disclosure, links), `/about` (mission, beliefs, global by design)
- ✅ SEO on every page as it is built (owner 2026-10-13): `usePageSeo()`, breadcrumbs, structured data, `sitemap.xml` and `robots.txt`

## S4, Pricing
- ✅ `usePlans()` reading `GET {API}/public/plans` (live at `https://formalie.dev:5004/api/v1`, `{ success, data, meta }`), with the fallback file (samples, `docs/PRICING.md`) when the API doesn't answer
- ✅ Period toggle (Monthly · Quarterly · Annually, the saving read from the prices), four plan cards (Starter free, Professional and Business per period with the monthly price struck through, Enterprise "Custom" and "Contact us"), "Most popular"
- ✅ "Payments handled by Paddle" near the prices (no logo yet) and the tax note; the FAQ links to Refunds and cancellation and the Terms
- ✅ Full comparison table (grouped, from each plan's limits and features), pricing FAQ, structured data with one offer per plan and period, FAQPage, breadcrumbs
- ✅ Buttons lead to the portal sign-up with `plan` and `period`; Enterprise leads to `/enterprise?plan=enterprise&period=…#enquiry`

## S5, Legal pages and trust
- ✅ `legal` layout: documents navigator with search across the text, the article (numbered sections, anchors, copy link), "On this page", last updated, version, "What changed", print or save as PDF, previous and next; a drawer on phones
- ✅ `useLegal()` reading `GET {API}/public/legal/{slug}?lang=` (`docs/LEGAL-PAGES.md`), refreshed after load; "This document is shown in English" for other languages; a "Draft" badge and note while `status` is `draft`
- ✅ Fallback copy `app/data/legal.json` from formlyBackend `docs/legal/` (`pnpm legal:sync`), in the API's shape (no invented wording)
- ✅ Privacy policy · Terms and conditions · Data protection · Cookie policy · Acceptable use · Subprocessors · Refunds and cancellation (7th, after subprocessors)
- ✅ Redirects `/terms`, `/privacy`, `/refunds` (and `/legal`) → `/legal/…`
- ✅ `/trust` "Trust and security" from formlyBackend `docs/legal/trust-and-security.md`, without "Independent checks (when ready)", in 20 languages

## S6, Formalie forms and portal links (owner: "we will handle the linking to the portal forms later")
- ⬜ Embedded Enterprise enquiry (`FormalieEn`) on `/enterprise` and from pricing, with prefill
- ⬜ Embedded Contact support (`FormalieHp`) on `/contact`
- ⬜ Newsletter form (when the owner creates it)
- ⬜ Portal links checked (sign-up with plan and period, sign-in → find workspace)
- ⬜ The portal links back to the legal pages (privacy on every form, terms on sign-up)

## S7, Launch checks
- ⬜ SEO (`docs/SEO.md`): ✅ titles, descriptions, OG and Twitter, canonical, hreflang, breadcrumbs, structured data, sitemap, robots (S3); ⬜ OG images per page, Search Console
- ⬜ Lighthouse 95+ on mobile, no layout shift, images sized
- ⬜ Accessibility: keyboard, focus, headings, contrast, reduced motion
- ⬜ Security headers and CSP (`docs/SECURITY.md`; `connect-src https://services.formalie.com`); ✅ `security.txt` (S0)
- ⬜ Production build (`nuxt generate`) and deployment notes
- ⬜ Prerender `failOnError: true` again in `nuxt.config.ts` (off since S2 while later pages don't exist), and no broken links

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
| 2026-10-13 | Every section draws on the reference screens, with clean, modern, tech-style "communication" animations (data moving between systems) | S2 to S6 | ⬜ |
| 2026-10-13 | (S2 finding) The `api-docs` screenshot shows an `api.formalie.dev` address with a key-like string; the home page uses `api-service` instead until the owner confirms or a new shot is made | S2 | ⏸ |
| 2026-10-13 | Sample names are English ("Emma Clarke"), nothing Nigeria-themed on marketing pages | S2 | ✅ |
| 2026-10-13 | SEO built into every page as it is made: "this is the real central page, so it must be loaded with SEO" | S3 to S7 | ✅ (ongoing) |
| 2026-10-13 | Tighter spacing site-wide (hero closer to the header, less space between sections), nicer cards, and a richer "Built for teams in every sector" with movement | S2 to S4 | ✅ |
| 2026-10-13 | Copy formlyBackend `docs/PRODUCTION-CHECKLIST.md` over this project's copy | Docs | ✅ (already identical; DEPLOYMENT-GUIDE synced too) |

## Progress log

| Date | Phase | What |
|---|---|---|
| 2026-10-10 | Package | Docs, references, 25 screenshots (light and dark, cropped, watermarked, sample data) and the app's animation prepared from formalieFrontend |
| 2026-10-13 | Docs | Backend hand-over recorded: API address (`services.formalie.com`, never `api.formalie.com`), Paddle instead of Payoneer, the `refunds` legal page, redirects, `/trust`, `security.txt`; PRODUCTION-CHECKLIST already identical to formlyBackend's, DEPLOYMENT-GUIDE synced |
| 2026-10-13 | S0 | Nuxt 4.5.2, Nuxt UI 4.11, Tailwind 4, strict TypeScript, ESLint and Prettier (the app's settings), Vitest (47 tests: links, 20 locale files with every key and no em dashes); i18n with 20 languages (prefix strategy, Arabic right to left, `hreflang`); `@nuxt/content` (blog, changelog, legal collections); `@nuxt/image`; Manrope self-hosted; the app's theme tokens; `useSiteLinks()`; 25 screenshots as WebP; brand files; `security.txt`; dev server on `https://formalie.dev:3033`; `pnpm generate` prerenders all 20 languages |
| 2026-10-13 | S1 | Header with Product, Solutions and Resources panels (ink icon tiles), Pricing, Integrations, Contact, language and theme switches, Sign in and Start free (portal links); slide-over below 1280 px; footer with four columns, the seven legal links, language, theme, ©; Noto fallbacks for Arabic, Hindi and Bengali; 404 and error page; skip link. 73 new strings in 20 languages. Checked on phone, 1024 and 1280 px, light and dark, Arabic right to left, keyboard, and the longest languages (no header overflow) |
| 2026-10-13 | S2 | Home page: hero with the data-flow panel, trust strip, channels, product tabs with real screens, six cards, dark security band with a live audit trail, integrations orbit, languages marquee, pricing teaser from the live API (`usePlans`, zod-checked, sample fallback), FAQ, call to action. Motion tokens in `main.css`, all still for reduced motion and paused off screen. 150 new strings in 20 languages. Prerender now lists every language and lets links to unbuilt pages through until S7. Checked at 375, 1280 and 1440 px, light and dark, Arabic. 51 tests |
| 2026-10-13 | S2 | Sample names in English: Emma Clarke types in the hero, James W. in the audit trail |
| 2026-10-13 | S3 | `/features` and 11 feature pages, 7 solution pages, `/integrations`, `/security`, `/about`; shared `SiteScreenFrame`, `SiteCta`, `FeaturesSteps`, `FeaturesRelated`, drawn visuals for the AI assistant and languages, a solution flow; `usePageSeo()` with breadcrumbs and structured data on every page, `sitemap.xml` (460 addresses: 23 pages in 20 languages) and `robots.txt`; RTL arrows mirrored. 362 new strings in 20 languages. Checked at 375 and 1280 px, light, Arabic |
| 2026-10-13 | Polish | Global theme in `app.config.ts`: heroes closer to the header, one section rhythm, cards with 1rem radius and a soft lift, plan cards and table that never cut text; sector strip with 18 sectors in two gliding rows with live pulses |
| 2026-10-13 | S4 | `/pricing`: period toggle (opens on Annually), four plans from the live API, comparison table (`UPricingTable`), Paddle and tax notes, pricing FAQ, structured data; `usePricing()`, `app/utils/pricing.ts` with tests (55); in the sitemap. Checked at 375 and 1280 px, light and dark |
| 2026-10-13 | S5 | Seven legal pages in the documentation layout from the live API (Draft badge, English notice, offline fallback from formlyBackend's drafts), search, print, copy links; `/trust`; redirects; legal and trust copy in 20 languages; plans and legal now refresh after hydration (`onNuxtReady`) and the dev server trusts the local certificate (`--use-system-ca`). Sitemap 640 addresses. 59 tests |

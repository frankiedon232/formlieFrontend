# 01, Architecture

## Stack

- **Nuxt 4.5** with **Nuxt UI 4**: use its marketing components (`UPageHero`, `UPageSection`, `UPageGrid`, `UPageCard`, `UPageFeature`, `UPricingPlans`, `UPricingTable`, `UPageCTA`, `UPageLogos` / `UMarquee`, `UFooter`, `UContentNavigation`, `UContentToc`).
- **Tailwind CSS 4** for layout only; the theme tokens are copied from the app (`docs/reference/main.css.excerpt`, `docs/DESIGN.md`).
- **@nuxt/content** for the blog, the changelog and the legal fallbacks.
- **@nuxtjs/i18n** with the 20 app languages, prefix strategy (`/fr/pricing`), English without a prefix, and `hreflang` on every page.
- **Rendering:** `nuxt generate` (prerendered static pages) for every public page. The pricing data and legal text are fetched at build time **and** refreshed on the client (`useFetch` with a short cache), so prices and legal changes from the platform admin show without a rebuild.

## Pages and routes

See `SITEMAP.md`. Every route exists in the 20 languages.

## Data the site reads

See `API-HOOKS.md`: public plans, public legal documents, and Formalie's own published forms (contact, enterprise, newsletter). No sign-in on the website, no cookies except the language and theme choice. Analytics, if added, must be cookie-less and owner-approved.

## Hosting

- **Static output** (`.output/public`) behind the same reverse proxy as the app, on `formalie.com` (production) or `formalie.dev:3033` (development).
- **Security headers:**
  - HSTS, `X-Content-Type-Options`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy`;
  - a CSP allowing `self`, the Formalie form origins for the embedded forms (`frame-src https://forms.formalie.com`) and `connect-src https://api.formalie.com`.
- **Images:** WebP or AVIF from `public/screenshots`, `NuxtImg` with explicit sizes.

## Shared look with the app

The website and the app must feel like one product: the same font (Manrope), the same monochrome ink with black or white actions, the same radius, borders and shadows, and the same data-flow animation family. `docs/reference/` holds the app's animation (`AuthFlow.vue`) and showcase (`AuthShowcase.vue`) to start from. The site's hero is a **larger, richer variant** (see `DESIGN.md`), not a copy of the sign-in panel.

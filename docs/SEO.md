# SEO

## How it is built (owner, 2026-10-13: "this is the real central page, so it must be loaded with SEO")

SEO is part of every page from the moment it is built, not a launch step:
- **`usePageSeo()`** (`app/composables/usePageSeo.ts`) on every page: title "{Page} · Formalie", description, Open Graph (type, site name, 1200 × 630 image with size and alt), Twitter card, robots (`index, follow, max-image-preview:large`), a `BreadcrumbList`, and the page's own structured data.
- **`useLocaleHead`** (app.vue): `<html lang dir>`, the canonical address, `hreflang` for the 20 languages plus `x-default`, `og:url`, `og:locale` and its alternates.
- **Structured data today:** home: `Organization`, `WebSite`, `SoftwareApplication` with one `Offer` per plan and period (from `/public/plans`) and `FAQPage`; `/features`: `ItemList`; feature pages: `SoftwareApplication` with the feature list; solution pages: `WebPage`; About: `AboutPage`.
- **`/sitemap.xml`** (`server/routes/sitemap.xml.ts`, prerendered): every built page in every language with its alternates. **Add each new page to `SITE_PATHS`.**
- **`/robots.txt`** (`server/routes/robots.txt.ts`, prerendered): everything allowed and the sitemap named. `/_nuxt` is **not** blocked (a change from the first plan): search engines need the CSS and scripts to render the pages.
- **Check before each commit:** the prerendered HTML in `.output/public` has the tags above and one `h1`.

## Every page

- `useSeoMeta`:
  - a title of 60 characters or fewer, in the pattern "{Page} · Formalie";
  - a description of 150 to 160 characters, `ogTitle`, `ogDescription`, `ogImage` (1200 × 630, from `public/og/`), `twitterCard: 'summary_large_image'`.
- Canonical URL, and `hreflang` alternates for the 20 languages plus `x-default` (English).
- One `h1`, then headings in order.
- Translated slugs are not used: the address stays English (`/fr/pricing`), only the content is translated.

## Structured data (`useSchemaOrg` or `useHead` JSON-LD)

- **Home:** `Organization` (name, logo, url, sameAs from the platform settings) and `WebSite` with a `SearchAction` pointing to the help centre search.
- **Pricing:** `SoftwareApplication` with `offers` (one `Offer` per plan and period, `price`, `priceCurrency`), and `FAQPage` for the pricing FAQ.
- **Feature and solution pages:** `SoftwareApplication` (applicationCategory `BusinessApplication`) with the feature list.
- **Blog:** `Article`. **Legal:** `WebPage` with `dateModified` from the document version.

## Files

- `sitemap.xml` with every page in every language and `lastmod`.
- `robots.txt` allowing everything except `/_nuxt` internals, and pointing to the sitemap.
- `manifest.webmanifest` with the icons.

## Titles and descriptions (English starting set)

| Page | Title | Description |
|---|---|---|
| Home | Formalie · Forms, data and access under your control | Build any form, collect answers by link, embed, QR or API, keep them in your own database and control who sees what. Free to start. |
| Pricing | Pricing · Formalie | Start free with Starter. Professional, Business and Enterprise plans, billed monthly, quarterly or yearly. Compare every feature. |
| Form builder | Form builder · Formalie | Drag-and-drop questions, pages, logic and calculations, in 20 languages, with versions and one-click publishing. |
| Data sources | Bring your own database · Formalie | Send every response to MySQL, MariaDB, PostgreSQL, SQL Server or Oracle as it arrives, or keep it in Formalie's encrypted storage. |
| API service | API service · Formalie | Turn any form into secure API endpoints with tokens, access rules, rate limits, logs and generated documentation. |
| Security | Security · Formalie | Encryption, roles and access control, an audit trail of every action, two-step sign-in, single sign-on and data residency. |
| Enterprise | Formalie for Enterprise | Dedicated infrastructure, data in the region you choose, single sign-on, security reviews and a dedicated team. |

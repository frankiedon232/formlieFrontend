# SEO

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

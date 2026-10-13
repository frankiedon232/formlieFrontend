# Sitemap

Every page exists in the 20 languages (`/fr/…`, `/ar/…`; English without a prefix). The header and footer appear on every page except the legal pages, which have their own documentation layout with the same header.

## Header

- **Left:** the Formalie mark and name.
- **Centre menu:**
  - Product: a dropdown with icon tiles for Form builder, Design and templates, Responses and analytics, Data sources, API service, Access and security, AI assistant, and Languages.
  - Solutions: a dropdown with HR and people, Customer feedback, Events and bookings, Health and safety, Education, Operations and compliance, and Developers.
  - Pricing · Integrations · Resources (a dropdown: Help centre, Blog, Changelog, API documentation) · Contact.
  - The Help centre is the portal's own (`{portal}/help`, people sign in to read it, opens in a new tab). API documentation links to `/features/api-service` until public API docs exist.
  - The panels are two columns of ink icon tiles (one column for Resources). The full menu shows from 1280 px wide (longer languages need the room); below that, the slide-over.
- **Right:**
  - language switch (a flag);
  - theme switch;
  - **Sign in**, an outline button opening the portal's find-workspace page;
  - **Start free**, a solid black button opening the portal sign-up.
- **Phones:** a slide-over menu.

## Pages

| Route | Purpose | Sections (top to bottom) |
|---|---|---|
| `/` | Home | Hero (headline, subline, Start free + Talk to sales, the data-flow hero animation) · trust strip · "Answers from everywhere" (link, embed, QR, API) · product tabs (Builder · Design · Responses · Data · API, each with a screenshot and three points, after reference 3) · feature grid "What sets Formalie apart" (6 cards, after reference 1) · security band (dark) · integrations orbit (after reference 2: logos around a centre) · 20 languages strip · pricing teaser (three plans) · FAQ · final call to action |
| `/features` | All features | Hero · one block per area with a screenshot (alternating sides) · CTA |
| `/features/[slug]` | One area | `form-builder`, `design`, `templates`, `responses`, `analytics`, `data-sources`, `api-service`, `access-control`, `ai-assistant`, `languages`, `help-and-tours`: hero with the screenshot, 3 to 6 feature cards, a how-it-works strip, related features, CTA |
| `/solutions/[slug]` | Use cases | `hr`, `customer-feedback`, `events`, `health-and-safety`, `education`, `operations`, `developers`: the problem, the forms to start from (templates), what happens to the data, CTA |
| `/pricing` | Plans | Period toggle (Monthly · Quarterly −10% · Annually −20%) · four plan cards (Starter, Professional with the "Most popular" badge, Business, Enterprise with "Contact us") · full comparison table (grouped like the app: Forms and responses, Insight, Your data, API service, Brand and address, Sign-in, Support) · pricing FAQ · CTA |
| `/integrations` | Connections | Databases (MySQL, MariaDB, PostgreSQL, SQL Server, Oracle) · API service and webhooks · email and sign-in providers · "Built on open standards" |
| `/security` | Trust | Encryption, access control, audit trail, two-step sign-in and single sign-on, data residency, backups, the responsible disclosure contact; links to Data protection and Privacy |
| `/enterprise` | Enterprise | Dedicated infrastructure, data residency, single sign-on, an uptime agreement, a security review, custom limits, invoices · **the Enterprise enquiry form** (Formalie's own form, embedded) |
| `/contact` | Contact | Sales (the Enterprise form), Support (the Contact support form, embedded), Help centre link, response times |
| `/about` | Company | Mission, what Formalie believes in (privacy, ownership of data, simplicity), global by design |
| `/blog`, `/blog/[slug]` | Articles | From `@nuxt/content` |
| `/changelog` | Releases | From `@nuxt/content`, newest first |
| `/legal/[slug]` | Legal | `privacy`, `terms`, `data-protection`, `cookies`, `acceptable-use`, `subprocessors`, `refunds`: documentation layout (`LEGAL-PAGES.md`). `/terms`, `/privacy` and `/refunds` redirect here |
| `/trust` | Trust and security | From formlyBackend `docs/legal/trust-and-security.md`: how Formalie protects data, your rights and our commitments, report a problem. The "Independent checks (when ready)" section stays out until the owner adds it |
| `/.well-known/security.txt` | Security contact | formlyBackend `docs/legal/security.txt`, renewed before its Expires date |
| `/404` | Not found | A friendly message, search for help, a link home |

## Footer

- Four columns: Product · Solutions · Resources · Company.
- A legal row: Privacy policy · Terms and conditions · Data protection · Cookie policy · Acceptable use · Subprocessors · Refunds and cancellation.
- The Company column: About · Security · Trust and security · Enterprise · Contact.
- The language switch, "© 2026 Formalie" and a newsletter field (Formalie's own form, later).
- Layout after reference 2: a clean white footer with muted links.

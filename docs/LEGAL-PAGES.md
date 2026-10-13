# Legal pages

Privacy policy, Terms and conditions, Data protection, Cookie policy, Acceptable use policy, Subprocessors and Refunds and cancellation are on the website at `/legal/{slug}` in every language.

## Look: documentation, not a marketing page (owner)

```
┌────────────────────────── header (same as the site) ─────────────────────────┐
│ Legal                    │ Privacy policy                       │ On this page │
│  ▸ Privacy policy        │ Last updated 10 October 2026 · v3    │  1. Who we are│
│  ▸ Terms and conditions  │ [Download PDF] [Print] [Language ▾]  │  2. What we…  │
│  ▸ Data protection       │                                      │  3. …         │
│  ▸ Cookie policy         │ 1. Who we are                        │               │
│  ▸ Acceptable use        │ …                                    │               │
│  ▸ Subprocessors         │ 2. What we collect                   │               │
│  ▸ Refunds and cancel…   │ …                                    │               │
│                          │ …                                    │               │
│  (search the legal text) │ ◂ Previous · Next ▸                  │               │
└──────────────────────────┴──────────────────────────────────────┴───────────────┘
```

- **Left (`UContentNavigation`):** the legal documents, with the current one marked and a search box. On phones it's a drawer.
- **Centre:** the document.
  - Its title, "Last updated" and the version.
  - Numbered sections with anchor links (copy link on hover).
  - Download PDF and Print.
  - Previous and next document at the bottom.
- **Right (`UContentToc`):** "On this page", the sections, highlighted while scrolling. Hidden on small screens.
- **Reading width:** about 72 characters, a calm type scale, no animations.
- **Changes:** a small "What changed" note at the top when the version is new (from the API).

## Content source

The text is written and versioned in the **platform admin** (formaliePlatformFront / formaliePlatformBack) and read by the site from the public API:

```
GET {API}/public/legal                       → [{ slug, title, version, updated_at, languages[] }]
GET {API}/public/legal/{slug}?lang=fr        → { slug, title, version, updated_at, summary_of_changes, sections: [{ id, heading, body_markdown }] }
```

The fields are:
- `slug`: `privacy` · `terms` · `data-protection` · `cookies` · `acceptable-use` · `subprocessors` · `refunds` ("Refunds and cancellation", added 2026-10-13, after subprocessors in the navigation; Paddle is the merchant of record);
- `status`: `draft` until the owner publishes the document from the platform admin, then `published`. While it is a draft, the page shows a small "Draft" note;
- `language`: the language actually served (English when the requested one is missing);
- `body_markdown`: plain Markdown (headings, lists, tables and links only). Render it with `@nuxt/content`'s Markdown renderer or `MDC`, never `v-html` on raw HTML.

When a language is missing, show the English version with a notice in the reader's language ("This document is shown in English").

**The endpoint is live (2026-10-13)** at `{API}`: `https://formalie.dev:5004/api/v1` (development) or `https://services.formalie.com/api/v1` (production). Answers are plain `{ success, data, meta }` (no encryption envelope), on any host, with `Access-Control-Allow-Origin: *`. The first version of the text is formlyBackend's `docs/legal/` (drafts for a lawyer's review).

**When the API doesn't answer:**
- The site falls back to its own copy in `content/legal/{slug}.md`, taken from formlyBackend's `docs/legal/` (same sections and anchors), shown with the "Draft" note while the backend's copy is a draft.
- Never invent legal wording.

**Short addresses:** `/terms`, `/privacy` and `/refunds` redirect to `/legal/terms`, `/legal/privacy` and `/legal/refunds` (emails and older links use them).

## How it is built (S5, 2026-10-13)

- **Data:** `useLegal(slug)` reads `GET {API}/public/legal/{slug}?lang={locale}` while the page is prerendered and again in the browser after it loads (`onNuxtReady`), checked with zod (`app/utils/legal.ts`). When the API doesn't answer, `app/data/legal.json` is shown with a small notice. That file is a copy of formlyBackend's `docs/legal/*.md` in the API's shape: refresh it with `pnpm legal:sync` whenever the backend's drafts change.
- **Page:** `app/pages/legal/[slug].vue` in `layouts/legal.vue` (the site's header and footer, hidden when printing). Start side: `LegalNav` (the seven documents and a search across the text that jumps to a section); a drawer on phones. Centre: title, the Draft badge and note, last updated (or "Not published yet"), version, "What changed", "This document is shown in English" when the page's language has no translation, numbered sections with anchors and a copy-link button, the text rendered from Markdown with `MDC` (never `v-html`), previous and next. End side: `UContentToc` "On this page".
- **Print or save as PDF:** one button (the browser's print, which also saves as PDF); only the document prints.
- **Redirects:** `/terms`, `/privacy`, `/refunds` and `/legal` (to the privacy policy), in `nuxt.config.ts` `routeRules`, prerendered.
- **SEO:** a description per document (translated), `WebPage` with the version and `dateModified` once published, breadcrumbs; every document in the sitemap.

## Links

- The portal and the public form pages link here: the privacy link on every form, and the terms on sign-up. Those links are set later, when the owner connects the portal (`PROGRESS.md` phase S6).
- Each document has a stable address (`/legal/privacy`) and anchors per section (`/legal/privacy#what-we-collect`), so the portal can link to a section.

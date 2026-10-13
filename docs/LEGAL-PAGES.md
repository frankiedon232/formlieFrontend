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

## Links

- The portal and the public form pages link here: the privacy link on every form, and the terms on sign-up. Those links are set later, when the owner connects the portal (`PROGRESS.md` phase S6).
- Each document has a stable address (`/legal/privacy`) and anchors per section (`/legal/privacy#what-we-collect`), so the portal can link to a section.

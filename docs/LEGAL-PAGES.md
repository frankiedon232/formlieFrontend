# Legal pages

Privacy policy, Terms and conditions, Data protection, Cookie policy, Acceptable use policy and Subprocessors are on the website at `/legal/{slug}` in every language.

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
- `slug`: `privacy` · `terms` · `data-protection` · `cookies` · `acceptable-use` · `subprocessors`;
- `body_markdown`: plain Markdown (headings, lists, tables and links only). Render it with `@nuxt/content`'s Markdown renderer or `MDC`, never `v-html` on raw HTML.

When a language is missing, show the English version with a notice in the reader's language ("This document is shown in English").

**Until the endpoint exists:**
- Put placeholder files in `content/legal/{slug}.md` with section headings only.
- Mark each one clearly: "This text is a placeholder. The final policy will be published here."
- Never invent legal wording.

## Links

- The portal and the public form pages link here: the privacy link on every form, and the terms on sign-up. Those links are set later, when the owner connects the portal (`PROGRESS.md` phase S6).
- Each document has a stable address (`/legal/privacy`) and anchors per section (`/legal/privacy#what-we-collect`), so the portal can link to a section.

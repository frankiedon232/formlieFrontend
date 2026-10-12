# CLAUDE.md, formaliePlatformFront (Formalie Platform Admin, front end)

Read `README.md`, `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/FRONTEND-SPEC.md`, `docs/SECURITY-PROTOCOL.md`, `docs/API-CONTRACT.md` and `docs/design/README.md` before any task. Work through the phases in [`PROGRESS.md`](PROGRESS.md) in order and tick tasks there when done.

## What this is

The Formalie team's own system: analytics over the whole platform (Google Analytics style), full management of workspaces, accounts, subscriptions, payments, help content, default data and platform settings, and its own staff with roles and access. **It is not the customer portal.** Customers never sign in here; Formalie staff only.

Two projects make it up: this one (the Nuxt front end) and **formaliePlatformBack** (the FastAPI backend, its own folder and repository). They talk only through the API in `docs/API-CONTRACT.md`. The Formalie portal's source (`C:\UNETPROJECTS\formalieFrontend`) is read for reuse, never changed from here.

## Brand

The Formalie mark (Field F, chosen by the owner on 2026-10-10) is the logo here too. The kit is in `docs/brand/`: the SVG sources, PNG sizes, web icons, manifest and OG image, with the rules in `BRAND.md`. Use these files as they are:
- copy `docs/brand/web/*` into `public/`, with the same `app.head` links as Formalie: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png` and `site.webmanifest`. In the manifest, set `name` to "Formalie Platform".
- add the mark as the icon `i-formalie-mark`: put `docs/brand/svg/formalie-glyph.svg` in `app/assets/icons/mark.svg` with `currentColor` fills, plus the Nuxt Icon `customCollections` entry with the prefix `formalie`.
- the menu header shows the mark and "Formalie Platform"; the loading screen shows the mark.

Never redraw the mark or use another logo.

## Keep docs in sync

`PROGRESS.md` is this project's tracker (every task per phase, overview table, new-requests log, progress log). Every milestone: tick the task, add a Progress log line, update the overview table and "Last updated"; any new request goes into the right phase **and** the New requests log immediately. Update any doc whose facts changed (decisions → `03-DECISIONS-AND-NOTES.md`, contract → `API-CONTRACT.md`, setup → `02-DEV-ENVIRONMENT.md`).

**Shared docs** (the same file in both projects): `00-OVERVIEW`, `01-ARCHITECTURE`, `02-DEV-ENVIRONMENT`, `03-DECISIONS-AND-NOTES`, `04-HOSTING`, `API-CONTRACT`, `SECURITY-PROTOCOL`, `ERROR-CODES`, `ANALYTICS`, `FORMALIE-INTEGRATION`. When one changes here, say so in the commit message and tell the owner, so the same change is made in formaliePlatformBack. The contract is changed together with the backend, never only on one side.

**Commit and push** after each verified milestone (typecheck + lint + tests green); stop for the owner's review at the end of each phase.

## Stack (fixed, same as Formalie, no deviation)

Nuxt 4.5 · Nuxt UI 4 · Tailwind CSS 4 · Vue 3.5 · TypeScript 6 (strict) · pnpm. Allowed extras: `zod`, `@vueuse/core` + `@vueuse/nuxt`, `@nuxtjs/i18n`, `vue-draggable-plus`, `@iconify-json/circle-flags`, `@internationalized/date`, `uqr`, `@tiptap/extension-text-align` (help article editor, with Nuxt UI's `UEditor`), CodeMirror 6 only if a code / query editor is needed. Charts are built like Formalie's (`ChartsMiniBars`, `ChartsLines`, SVG with Nuxt UI tokens), no chart library unless the owner approves one. Dev tooling: `@nuxt/eslint`, `prettier`, `vitest`, `@nuxt/test-utils`, `vue-tsc`. **Ask before adding anything else.** No Docker.

Scripts: `pnpm dev` · `pnpm typecheck` · `pnpm lint` · `pnpm format` · `pnpm test` (and `pnpm typecheck:dev` while the dev server runs). Dev URL `https://platformadm.formalie.dev:2203/`, API `https://platformapi.formalie.dev:5601/`.

## Start from Formalie

Copy Formalie's foundation from `C:\UNETPROJECTS\formalieFrontend` (FRONTEND-SPEC → first paragraph): shell, DataView, charts, envelope client, composables, i18n, loading template, progress plugin, modals, context menu, Roles & access editor. Keep their APIs so the two products stay alike; change only what the platform needs (product name "Formalie Platform", no tenants, platform permissions, `PLT-*` error map, HKDF info `formalie-platform-envelope-v1`).

## Hard rules

1. **Staff only, strongest security.** Two-step sign-in is mandatory; sensitive actions ask to confirm again (step-up, `PLT-AUTH-1020`); dangerous actions need a second person's approval (`PLT-APPR-1001` "sent for approval", SECURITY-PROTOCOL §6); every action is in the platform audit trail.
2. **Nuxt UI first.** Build every UI from Nuxt UI components; Tailwind for layout only; no hand-written component styling Nuxt UI provides; `main.css` holds only `@import "tailwindcss"; @import "@nuxt/ui";` and `@theme` tokens. All dialogs use `AppModal` (draggable, arrow keys, docked on phones).
3. **Never import composables or components** (auto-imports, path-prefixed component names). Only third-party libraries and types are imported.
4. **Mobile first**, then `sm: md: lg: xl:`; every page, table and dialog works on phone, tablet, desktop.
5. **Every async action uses `try / catch / finally`**; errors through `useErrorHandler()` (maps `PLT-*` codes to friendly toasts, handles step-up and "sent for approval").
6. **Always show progress**: first-load screen, top and in-page bars on navigation and every API call (`useActivity`), skeletons mirroring the layout, `:loading` on async buttons (`useBusy`), busy rows, `UProgress` with percentage for long work, empty and error states with the next step.
7. **Lists:** `DataView` with Table / Grid, filters, search, sort, date range, server paging; the two chart cards on top; task-style cards; rich detail panels (same discipline as Formalie's rule 21).
8. **Keyboard accessible** everywhere, visible focus, Esc closes overlays, shortcuts with `defineShortcuts` and `UKbd`, keyboard alternative for every drag.
9. **Breadcrumbs on every page** in the header bar; title, subtitle and page buttons always in the header bar (`AppPanel`), never in the content.
10. **Theme switch** always available (sidebar SYSTEM group, navbar on small screens, user menu).
11. **All API calls through `useApi()`** (envelope, bearer token, CSRF, refresh on 401, re-handshake, step-up retry). Never `$fetch` / `fetch` in pages or components.
12. **Permissions everywhere:** every menu item, page, button, row action, shortcut and bulk action follows the staff member's grants (`useCan()`) and the per-item `can` the API sends; the API checks again.
13. **Least data, masked by default:** analytics never show what respondents answered, never passwords, tokens or secrets; personal data masked, revealed on purpose (step-up, audited). Never log or store personal data in the browser.
14. **No secrets or tokens in localStorage**; access token and session key in a module-level ref (never `useState`); refresh token in the HttpOnly cookie scoped to the platform host.
15. **Every user-facing string translated** (`useI18n`), all 20 locales (same list as Formalie), English as fallback; RTL with logical Tailwind utilities; dates, numbers and currency through `useFormat()`.
16. **Mock first:** `server/mock/**` (toggled by `NUXT_PUBLIC_API_MOCK=true`) returns exactly the API-CONTRACT shapes until the backend is ready; seed believable, international, neutral data (fictional workspaces, reserved phone ranges, `example.org` emails).
17. **Client-rendered only**, `noindex`; no public pages.
18. **Global product, no em dashes.** Copy stays international and neutral; compliance wording promises controls, never certifications we don't hold. Never "—" in copy, comments or docs; use a comma, full stop or colon.

## Design

Same look as Formalie: check `docs/design/` and its README before building any page, and compare against the images before calling a page done. Monochrome, black primary actions, the same shell (icon rail, grouped sidebar, header bar with title, subtitle, breadcrumbs and actions). Only the product name and the content differ.

## Folder conventions

Same as Formalie: `app/` with `components/{app,data,charts,analytics,workspaces,accounts,billing,content,defaults,operations,communications,staff,audit}`, `composables/{api,auth,ui,data,i18n,…}` (max two levels), `utils/`, `pages/` per FRONTEND-SPEC, `i18n/locales/{code}.json`, `shared/` for types and utils used by the mock and the app, `server/mock/` for the mock API, `test/` mirroring the source. Components under ~250 lines.

## Done means

Phone / tablet / desktop checked · keyboard only · light and dark · Arabic RTL · loading feedback complete · empty and error states · every string in 20 languages · matches `docs/design` · permissions followed everywhere · typecheck, lint, tests green · `PROGRESS.md` and docs updated · committed and pushed. Check every UI change in the browser yourself before reporting it.

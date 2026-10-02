# Frontend Roadmap — formalieFrontend

Work top to bottom. Each phase ends with: responsive check (phone/tablet/desktop), keyboard check, light/dark check, RTL check (Arabic), loading/empty/error states present, all new strings in every locale. Commit + push after each verified milestone.

## Status at a glance

✅ done · 🟡 in progress · ⬜ not started — same table in the [README](../README.md#progress).

| F0  | F1  | F2  | F3  | F4  | F5  | F6  | F7  | F8  | F9  | F10 | F11 | F12 | F13 | F14 | F15 | F16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ✅  | ✅  | ✅  | 🟡  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  | ⬜  |

**Currently:** F3 — sign-in redesigned and verified in the browser; remaining: polish signup / find workspace / reset screens, RTL + keyboard pass.

## Progress log

| Date       | Phase | Milestone                                                                                                                                                                                                                                                                                                                 |
| ---------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-02 | F0    | Foundation: config, i18n (20 languages), mock API with real envelope, tooling.                                                                                                                                                                                                                                            |
| 2026-10-02 | F0    | Phase check passed: phone/desktop, light/dark, Arabic RTL, keyboard-only language switch, live encrypted mock round-trip. Locale search by English name.                                                                                                                                                                  |
| 2026-10-02 | F0    | Access matrix verified on every host (manage., root, tenants, localhost, 127.0.0.1, *.localhost, LAN IP); shared `resolveHostContext()` + 11 tests ready for F3.                                                                                                                                                          |
| 2026-10-02 | F1    | App shell done: sidebar rail/peek/drawer, navbar, breadcrumbs, command palette, shortcuts, draggable `AppModal`, error + workspace-not-found pages, 49 new strings × 20 languages. Checked desktop/phone, light/dark, Arabic RTL, keyboard-only (peek tab order), real mouse drag.                                        |
| 2026-10-02 | F1    | Shell rebuilt to match docs/design exactly: rail (⋯, +, workspaces) + menu column (MAIN MENU / RESOURCES / SYSTEM, status dots, Dark mode switch, user card), search-left top bar, `AppPageHeader` (title, meta, outline + black actions), monochrome primary; icon endpoint moved out of /api.                           |
| 2026-10-02 | F1    | Owner feedback: language flags (circle-flags) on every switcher, breadcrumbs moved into the top bar, font Manrope (identified from the design).                                                                                                                                                                           |
| 2026-10-02 | F1    | Menu detail per owner: timeline children, square bullets, clean dark text.                                                                                                                                                                                                                                                |
| 2026-10-02 | F2    | Core plumbing done: API client + useApi, error handling (48 codes × 20 languages), useBusy, useFormat, DataView (forms list live on the encrypted mock), confirm dialog, copy field. Checked desktop/phone, Arabic RTL (Arabic-Indic digits), error state + retry, URL-synced search/sort/paging/date range, view memory. |
| 2026-10-02 | F2    | Owner feedback: title/subtitle/crumbs/page buttons moved into the header bar (content area clear, phone = icons), footer added; DataView flow approved and frozen.                                                                                                                                                        |
| 2026-10-02 | F3    | Auth built (mock + client + pages); mock flow verified live (login, OTP attempts, tokens, protected call, refresh rotation, reuse → revoke). Browser check pending dev-server restart.                                                                                                                                    |
| 2026-10-02 | F3    | Owner feedback: sign-in redesigned (inset dark showcase with live product preview, workspace chip, roomy form, security note); verified login → code → portal → logout in browser, desktop / phone / dark. Test accounts + progress table added to README.                                                                |
| 2026-10-02 | F3    | Owner feedback: global positioning on the sign-in showcase (headline + platform description, supplier-onboarding form with consent, "synced to your database", access visibility, compliance/database/access badges); mock data made international; CLAUDE.md rule 20 (global product).                                   |
| 2026-10-02 | F3    | Owner feedback: database card shows the launch set (MySQL, MariaDB, Oracle, PostgreSQL, SQL Server — \"5+ databases\") or encrypted Formalie storage; badge \"5+ databases or secure storage\".                                                                                                                           |

## F0 — Foundation

- [x] Fix dev env per `02-DEV-ENVIRONMENT.md` (wildcard cert, `*.formalie.dev` hosts, `vite.server.allowedHosts`, `/api` proxy with `X-Forwarded-Host`, `NODE_EXTRA_CA_CERTS`). _Repo side done (allowedHosts, proxy, `.env.example`); hosts + wildcard cert are on the machine._
- [x] `main.css` (`@import "tailwindcss"; @import "@nuxt/ui";` + theme tokens), `app.config.ts` colours (primary indigo, neutral zinc), fonts (Inter via `@nuxt/fonts`).
- [x] `app.vue` with `UApp` (Nuxt UI locale follows the app language), `NuxtLoadingIndicator`, layouts `default` · `auth` · `public` · `blank`.
- [x] `routeRules`: portal client-rendered, `/f/**` and `/s/**` SSR; security headers (HSTS, nosniff, Referrer-Policy, Permissions-Policy, COOP, X-Frame-Options; CSP in production).
- [x] runtimeConfig: `public.apiBase`, `public.apiMock`, `public.rootDomain` (`formalie.dev`), `public.manageSubdomain` (`manage`); server-only `apiProxyTarget`.
- [x] Mock API scaffold in `server/mock/` following `API-CONTRACT.md`: real ECDH handshake, envelope checks (expiry, replay, integrity, method/path binding), CSRF, `/health`, `/crypto/handshake`, `/auth/csrf`, `paginate()` helper.
- [x] ESLint (`@nuxt/eslint`, rule blocking `.vue`/composable imports), TypeScript strict, Prettier, Vitest (envelope unit tests).
- [x] i18n (`@nuxtjs/i18n`): 20 languages — en, fr, es, pt, de, it, nl, pl, ru, uk, tr, ar (RTL), hi, bn, zh-CN, ja, ko, id, vi, sw; cookie-remembered, browser detection, `AppLocaleSwitch`.

## F1 — App shell

- [x] `layouts/default.vue` with `UDashboardGroup`, sidebar rail + menu, collapse (cookie), hover/focus-peek when collapsed (rail `inert` while open), mobile drawer. One nav definition (`useNavigation`) feeds sidebar, search and shortcuts.
- [x] Navbar (`AppNavbar` inside `AppPanel`): breadcrumbs (`definePageMeta({ breadcrumb })`, all clickable, no dead links), command palette (`Ctrl/⌘+K`: pages, actions, language, theme), theme switch, language switch (+ in user menu for phones), notifications slide-over (empty state), user menu (profile, settings, theme, language, shortcuts, log out — wired in F3).
- [x] Draggable modal pattern: `AppModal` (mouse/touch drag by header, grip button with arrow keys / Shift = big steps / Home re-centres, docked below `sm`). Use `AppModal`, never bare `UModal`.
- [x] Error page (`error.vue`, translated 404 / generic), `/workspace-not-found` (links to manage. on the same port).
- [x] Global shortcuts and help modal: `?` help, `Ctrl/⌘+K` search, `[` sidebar, `g` then `f/t/r/a/o/s` go to section, `Esc` closes the top-most layer.
- [x] Placeholder pages for every menu entry (`AppComingSoon`) so no link 404s; locale completeness test (`test/i18n/locales.test.ts`).

## F2 — Core plumbing

- [x] Envelope crypto (ECDH P-256, HKDF, AES-GCM) in `shared/utils/crypto/` + framework-free client `utils/api/client.ts` (handshake, envelope, CSRF, re-handshake, refresh, abort); 13 unit tests incl. a fake protocol server. _Backend test vectors: add when FastAPI exists._
- [x] `useApi` (get/post/put/patch/del/list, bearer from `useSession` memory ref, client-only) and `useErrorHandler` (translated `FRM-*` toasts, copyable trace reference, `fieldErrors()` for UForm).
- [x] `useBusy` (busy + no double submit + try/catch/finally + success toast), `useBreadcrumbs`, toasts pattern; 48 error messages × 20 languages (test keeps catalogue and translations in sync).
- [x] Locale-aware formatters `useFormat()` (date, dateTime, relative, number, compact, percent, currency, fileSize) via Intl.
- [x] `DataView` + `useDataView` (Table/Grid remembered per page, toolbar: search with `/`, Filter popover + chips, date range presets + calendar, Sort; sortable headers, row selection + bulk bar, ⋯ row actions, skeletons, empty / no-results / error + retry, server pagination, URL sync), `AppPageHeader`, `AppConfirmDialog` + `useConfirm()`, empty states via `UEmpty`, `DataStatusBadge`, `AppCopyField`. Demo: `/forms` list on mock `GET /forms` + `/folders`.

## F3 — Tenant detection + auth

- [x] `tenant.global.ts` middleware, `useTenant` (public profile, branding, providers) — built on `resolveHostContext()` (done early, see progress log); dev-only `?tenant=` override; pass the locale along on manage → tenant redirect. _Done: `01.tenant.global.ts`, `useTenant`, dev `?tenant=`, last-workspace cookie._
- [ ] Login, OTP (every login), signup + subdomain availability, find workspace, forgot/reset password, social buttons per tenant config, logout, session expiry handling. _Built + flow verified (login → code → portal → logout). Login redesigned per owner. Remaining: polish signup / find workspace / reset screens, RTL + keyboard pass._

## F4 — Onboarding wizard

## F5 — Forms list and lifecycle

- [ ] `/forms` DataView, folders/tags, create, duplicate, rename, archive, trash/restore, status badges.

## F6 — Builder (largest phase)

- [ ] Field registry + all field types (renderer + inspector).
- [ ] Canvas with `vue-draggable-plus`: palette → canvas, reorder fields/rows/sections/pages, column widths.
- [ ] Keyboard alternatives for all moves; multi-select; duplicate; delete with undo.
- [ ] Undo/redo history, autosave to draft, version conflict handling.
- [ ] Multi-page, sections, validation rules UI.
- [ ] Logic editor (`/logic`).
- [ ] Publish flow (change summary) and draft-on-reedit behaviour; versions page with restore.

## F7 — Designer (themes)

## F8 — Renderer, preview, share, embed, short links, SEO

- [ ] Shared renderer component used by preview, `/f/[slug]`, `/f/[slug]/embed`.
- [ ] Public form SSR with SEO meta; closed/expired/password states; save-and-resume.
- [ ] Share page: slug, short URL, QR, access options, people grants (edit/view), iframe snippet + auto-resize.

## F9 — Responses

- [ ] Per-form and inbox DataViews, filters per field type, date ranges, single response view, status/tags/notes, export jobs (XLSX/CSV/PDF).

## F10 — Templates gallery + save as template

## F11 — Settings (all sections) + option sets + integrations (destinations, webhooks, API keys)

## F12 — Profile (password, MFA/TOTP setup, sessions/devices)

## F13 — Users (can be pulled earlier if needed)

## F14 — Analytics (per form)

## F15 — Live collaboration (optional, Yjs)

## F16 — Last: Roles & access (RBAC UI), audit trail UI, **Dashboard** (date ranges, filters, KPIs, charts)

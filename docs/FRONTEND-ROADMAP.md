# Frontend Roadmap — formalieFrontend

Work top to bottom. Each phase ends with: responsive check (phone/tablet/desktop), keyboard check, light/dark check, RTL check (Arabic), loading/empty/error states present, all new strings in every locale. Commit + push after each verified milestone.

## Progress log

| Date       | Phase | Milestone                                                                                                                                                                                                                                                                                       |
| ---------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-02 | F0    | Foundation: config, i18n (20 languages), mock API with real envelope, tooling.                                                                                                                                                                                                                  |
| 2026-10-02 | F0    | Phase check passed: phone/desktop, light/dark, Arabic RTL, keyboard-only language switch, live encrypted mock round-trip. Locale search by English name.                                                                                                                                        |
| 2026-10-02 | F0    | Access matrix verified on every host (manage., root, tenants, localhost, 127.0.0.1, *.localhost, LAN IP); shared `resolveHostContext()` + 11 tests ready for F3.                                                                                                                                |
| 2026-10-02 | F1    | App shell done: sidebar rail/peek/drawer, navbar, breadcrumbs, command palette, shortcuts, draggable `AppModal`, error + workspace-not-found pages, 49 new strings × 20 languages. Checked desktop/phone, light/dark, Arabic RTL, keyboard-only (peek tab order), real mouse drag.              |
| 2026-10-02 | F1    | Shell rebuilt to match docs/design exactly: rail (⋯, +, workspaces) + menu column (MAIN MENU / RESOURCES / SYSTEM, status dots, Dark mode switch, user card), search-left top bar, `AppPageHeader` (title, meta, outline + black actions), monochrome primary; icon endpoint moved out of /api. |

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

- [ ] `useCrypto` (ECDH P-256 handshake, HKDF, AES-GCM envelope) + unit tests against backend test vectors (once available).
- [ ] `useApi` (envelope, bearer, CSRF, refresh, re-handshake, abort, try/catch/finally) and `useErrorHandler` with error-code map.
- [ ] `useBusy`, `useBreadcrumbs`, toasts pattern; translated error messages (`errors.FRM-*` keys in all locales).
- [ ] Locale-aware formatters (`utils/format/`: dates, numbers, currency, relative time).
- [ ] `DataView` (table/grid switch, FilterBar, DateRangePicker, pagination, URL sync, skeletons, empty/error), `PageHeader`, `ConfirmDialog`, `EmptyState`, `StatusBadge`, `CopyField`.

## F3 — Tenant detection + auth

- [ ] `tenant.global.ts` middleware, `useTenant` (public profile, branding, providers) — built on `resolveHostContext()` (done early, see progress log); dev-only `?tenant=` override; pass the locale along on manage → tenant redirect.
- [ ] Login, OTP (every login), signup + subdomain availability, find workspace, forgot/reset password, social buttons per tenant config, logout, session expiry handling.

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

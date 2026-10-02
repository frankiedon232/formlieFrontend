# Frontend Roadmap — formalieFrontend

Work top to bottom. Each phase ends with: responsive check (phone/tablet/desktop), keyboard check, light/dark check, loading/empty/error states present.

## F0 — Foundation

- [ ] Fix dev env per `02-DEV-ENVIRONMENT.md` (wildcard cert, `*.formalie.dev` hosts, `vite.server.allowedHosts`, `/api` proxy with `X-Forwarded-Host`, `NODE_EXTRA_CA_CERTS`).
- [ ] `main.css` (`@import "tailwindcss"; @import "@nuxt/ui";` + theme tokens), `app.config.ts` colours, fonts.
- [ ] `app.vue` with `UApp`, `NuxtLoadingIndicator`, layouts.
- [ ] `routeRules`: portal client-rendered, `/f/**` and `/s/**` SSR; security headers.
- [ ] runtimeConfig: `public.apiBase`, `public.apiMock`, `public.rootDomain` (`formalie.dev`), `public.manageSubdomain` (`manage`).
- [ ] Mock API scaffold in `server/mock/` following `API-CONTRACT.md`.
- [ ] ESLint (`@nuxt/eslint`), TypeScript strict, Prettier.

## F1 — App shell

- [ ] `layouts/default.vue` with `UDashboardGroup`, sidebar rail + menu, collapse, hover-peek when collapsed, mobile drawer.
- [ ] Navbar: breadcrumbs (route-meta driven, all clickable), command palette, theme switch, notifications placeholder, user menu.
- [ ] Error page (`error.vue`), 404, workspace-not-found.
- [ ] Global shortcuts and shortcut help modal (`?`).

## F2 — Core plumbing

- [ ] `useCrypto` (ECDH P-256 handshake, HKDF, AES-GCM envelope) + unit tests against backend test vectors (once available).
- [ ] `useApi` (envelope, bearer, CSRF, refresh, re-handshake, abort, try/catch/finally) and `useErrorHandler` with error-code map.
- [ ] `useBusy`, `useBreadcrumbs`, toasts pattern.
- [ ] `DataView` (table/grid switch, FilterBar, DateRangePicker, pagination, URL sync, skeletons, empty/error), `PageHeader`, `ConfirmDialog`, `EmptyState`, `StatusBadge`, `CopyField`.

## F3 — Tenant detection + auth

- [ ] `tenant.global.ts` middleware, `useTenant` (public profile, branding, providers).
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

# CLAUDE.md — formalieFrontend (Formalie portal)

Read `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/FRONTEND-SPEC.md`, `docs/SECURITY-PROTOCOL.md` and `docs/API-CONTRACT.md` before starting any task. Work through `docs/FRONTEND-ROADMAP.md` in order and tick items when done.

**Keep docs in sync.** Every milestone: tick it in `FRONTEND-ROADMAP.md`, add a line to its Progress log, and update any doc whose facts changed (decisions → `03-DECISIONS-AND-NOTES.md`, contract → `API-CONTRACT.md`, setup → `02-DEV-ENVIRONMENT.md`). **Commit and push** to the working branch (`formalieFrontend`) after each verified milestone (typecheck + lint + tests green); stop for review at the end of each phase.

**Design references:** before building any page, check `docs/design/` and `docs/design/README.md` for reference images for UI idea of what it should look and feel and notes. Match the layout and feel with Nuxt UI components; don't copy colours or branding unless the note says so.

## Stack (fixed)

Nuxt 4.5 · Nuxt UI 4 · Tailwind CSS 4 · Vue 3.5 · TypeScript 6 (strict; TS 7 not yet supported by typescript-eslint) · pnpm. Extra deps allowed only when Nuxt UI has no equivalent: `vue-draggable-plus` (drag and drop), `zod` (schemas), `@vueuse/core` + `@vueuse/nuxt`, `@nuxtjs/i18n` (languages). Dev tooling: `@nuxt/eslint`, `prettier`, `vitest`, `@nuxt/test-utils`, `vue-tsc`. Ask before adding anything else.

Scripts: `pnpm dev` · `pnpm typecheck` · `pnpm lint` · `pnpm format` · `pnpm test`. While the dev server runs use `pnpm typecheck:dev` (reuses `.nuxt`); `nuxt prepare`/`typecheck`/`build` regenerate `.nuxt` and need a dev-server restart afterwards.

Dev URL: `https://formalie.dev:2202/` (tenants: `https://{sub}.formalie.dev:2202/`, default entry `https://manage.formalie.dev:2202/`).

## Hard rules

1. **Nuxt UI first.** Build every UI from Nuxt UI components (`UDashboardGroup`, `UDashboardSidebar`, `UDashboardPanel`, `UDashboardNavbar`, `UNavigationMenu`, `UBreadcrumb`, `UTable`, `UPagination`, `UForm`, `UFormField`, `UInput`, `USelectMenu`, `UModal`, `USlideover`, `UDrawer`, `USkeleton`, `UProgress`, `UTabs`, `UCommandPalette`, `UDashboardSearch`, `UColorModeButton`, `UKbd`, `UToast` etc. …). Tailwind utilities for layout only. **No custom CSS frameworks, no hand-written component styling that Nuxt UI already provides.** `app/assets/css/main.css` only holds `@import "tailwindcss"; @import "@nuxt/ui";` plus `@theme` tokens. **All modals are draggable** (by their header, via `@vueuse/core` `useDraggable`) with an arrow-key alternative, so users can move them around; on phones they stay docked.
2. **Never import composables or components.** Nuxt 4 auto-imports `app/composables/**` (configured in `imports.dirs`), `app/utils`, Vue APIs, Nuxt APIs and all components (path-prefixed names, e.g. `components/forms/builder/Canvas.vue` → `<FormsBuilderCanvas />`). Never write `import X from '...vue'`. Only import third-party libraries and types where needed.
3. **Mobile first.** Design for small screens first, then `sm: md: lg: xl:`. Every page, table, builder panel and modal must work on phone, tablet, desktop.
4. **Every async action uses `try / catch / finally`.** `finally` always resets loading state. Errors go through `useErrorHandler()` (maps `FRM-*` codes to friendly toasts).
5. **Always show progress.** `<NuxtLoadingIndicator />` at the top for navigation; `USkeleton` while data loads; `:loading` on every action button (busy state, disabled while busy); progress bars for uploads/exports.
6. **Every list page offers Table and Grid views** (switch remembered per page), filters, search, sort, date range where relevant, and server-side pagination. Use the shared `DataView` component — don't rebuild per page.
7. **Keyboard accessible everywhere.** All interactive elements reachable by Tab, visible focus rings, Enter/Space activate, Esc closes overlays, shortcuts via `defineShortcuts` and shown with `UKbd`. Every drag action has a keyboard alternative (move up/down, move to page).
8. **Breadcrumbs on every page, every segment clickable** (`UBreadcrumb` driven by route meta).
9. **Theme switch** (light/dark/system) always available in the navbar.
10. **All API calls go through `useApi()`** which applies the encryption envelope, bearer token, CSRF header, refresh-on-401, retry-on-key-expiry. Never call `$fetch`/`fetch` directly in pages or components.
11. **Secure every form** (zod validation client-side, CSRF, enveloped submission, disabled double submit).
12. **No secrets or tokens in localStorage.** Access token and session key live in client-only in-memory state (a plain module-level ref in `useSession`, never `useState`, so they are never serialised into an SSR payload); the refresh token is an HttpOnly cookie set by the server.
13. **Simple UX.** No unnecessary steps; sensible defaults; empty states with a clear next action; confirm destructive actions.
14. Until the backend exists, use the mock layer (`server/mock/**`, toggled by `NUXT_PUBLIC_API_MOCK=true`) that returns exactly the shapes in `API-CONTRACT.md`.
15. **Rendering:** portal routes are client-rendered (`routeRules: { '/**': { ssr: false } }`); public form routes `/f/**` and `/s/**` are server-rendered for SEO and fast first paint.
16. Dashboard, users/roles/RBAC and audit UI come **last** (see roadmap).
17. **Every user-facing string is translated** (`@nuxtjs/i18n`, `const { t } = useI18n()`). No hard-coded copy in templates. Add each new key to **all** files in `i18n/locales/` (English is the fallback so a missing key never breaks the UI, but ship real translations). Languages are defined once in `shared/utils/i18n/locales.ts`. Layouts must work in RTL (Arabic): use logical Tailwind utilities (`ms-/me-/ps-/pe-/start-/end-`) instead of `ml-/mr-/left-/right-`. Format dates, numbers and currency with `Intl` / `useI18n().d/n` in the active locale.

## Folder conventions (Nuxt 4 `app/` dir)

Group files by domain in sub-folders — **max two levels** (e.g. `composables/api/useApi.ts`, `utils/i18n/ui-locales.ts`). `imports.dirs` scans `composables/**`, `utils/**` and `shared/utils/**`, so nested files are still auto-imported.

```
app/
  app.vue                 # <UApp><NuxtLoadingIndicator/><NuxtLayout><NuxtPage/></NuxtLayout></UApp>
  assets/css/main.css
  layouts/  default.vue (dashboard shell) · auth.vue · public.vue (form renderer) · blank.vue
  pages/    (see FRONTEND-SPEC.md page map)
  components/
    app/      shell: Sidebar, Navbar, Breadcrumbs, ThemeSwitch, UserMenu
    data/     DataView, FilterBar, DateRangePicker, ViewSwitch, EmptyState
    forms/    builder/, designer/, renderer/, logic/, share/, responses/
    settings/ auth/ templates/
  composables/
    api/      useApi, useCrypto, useCsrf
    auth/     useAuth, useSession, useOtp
    tenant/   useTenant
    ui/       useDataView, useBusy, useErrorHandler, useBreadcrumbs
    i18n/     useAppLocale
    forms/    useFormBuilder, useFormHistory (undo/redo), useFormTheme
  middleware/ tenant.global.ts · auth.ts · guest.ts
  plugins/    crypto.client.ts
  utils/      grouped: i18n/, format/, forms/ (field-registry) …
  types/
i18n/
  i18n.config.ts            # vue-i18n options (fallback = en)
  locales/{code}.json       # one file per language (20 today)
shared/                     # used by BOTH app and server (Nuxt 4 shared dir)
  types/    api.ts, crypto.ts
  utils/    crypto/ (envelope, encoding) · errors/ (FRM-* codes) · i18n/ (locale list) · tenant/ (host resolution)
server/
  mock/     index.ts (router) · core/ (envelope route wrapper, respond, store) · routes/ (one file per domain)
  proxy/    api.ts (dev proxy to FastAPI when the mock is off)
test/       vitest unit tests, mirroring source folders
```

## Code style

TypeScript strict, `<script setup lang="ts">`, small components, composables for logic, descriptive names, no `any` without a comment. Keep components under ~250 lines; split otherwise.

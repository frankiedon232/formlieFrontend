# CLAUDE.md — formalieFrontend (Formalie portal)

Read `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/FRONTEND-SPEC.md`, `docs/SECURITY-PROTOCOL.md` and `docs/API-CONTRACT.md` before starting any task. Work through `docs/FRONTEND-ROADMAP.md` in order and tick items when done.

**Design references:** before building any page, check `docs/design/` and `docs/design/README.md` for reference images for UI idea of what it should look and feel and notes. Match the layout and feel with Nuxt UI components; don't copy colours or branding unless the note says so.

## Stack (fixed)

Nuxt 4.5 · Nuxt UI 4 · Tailwind CSS 4 · Vue 3.5 · TypeScript (strict) · pnpm. Extra deps allowed only when Nuxt UI has no equivalent: `vue-draggable-plus` (drag and drop), `zod` (schemas), `@vueuse/core`. Ask before adding anything else.

Dev URL: `https://formalie.dev:2202/` (tenants: `https://{sub}.formalie.dev:2202/`, default entry `https://manage.formalie.dev:2202/`).

## Hard rules

1. **Nuxt UI first.** Build every UI from Nuxt UI components (`UDashboardGroup`, `UDashboardSidebar`, `UDashboardPanel`, `UDashboardNavbar`, `UNavigationMenu`, `UBreadcrumb`, `UTable`, `UPagination`, `UForm`, `UFormField`, `UInput`, `USelectMenu`, `UModal`, `USlideover`, `UDrawer`, `USkeleton`, `UProgress`, `UTabs`, `UCommandPalette`, `UDashboardSearch`, `UColorModeButton`, `UKbd`, `UToast` etc. …). Tailwind utilities for layout only. **No custom CSS frameworks, no hand-written component styling that Nuxt UI already provides.** `app/assets/css/main.css` only holds `@import "tailwindcss"; @import "@nuxt/ui";` plus `@theme` tokens. and all models should be draggable, so users can move it arround.
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

## Folder conventions (Nuxt 4 `app/` dir)

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
    forms/    useFormBuilder, useFormHistory (undo/redo), useFormTheme
  middleware/ tenant.global.ts · auth.ts · guest.ts
  plugins/    crypto.client.ts
  utils/      constants, formatters, field-registry
  types/
server/mock/  mock API (temporary)
```

## Code style

TypeScript strict, `<script setup lang="ts">`, small components, composables for logic, descriptive names, no `any` without a comment. Keep components under ~250 lines; split otherwise.

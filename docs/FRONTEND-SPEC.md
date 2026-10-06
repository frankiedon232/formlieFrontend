# Frontend Specification, Formalie Portal

## 1. Design principles

Clean, calm, professional. Font: Manrope (300–700). Generous spacing, clear hierarchy, one primary action per screen, consistent placement (primary action top-right of the panel header), human copy, no clutter. Everything from Nuxt UI; brand primary colour set in `app.config.ts` (`ui.colors.primary`), neutral `zinc`/`slate`. Font via `@nuxt/fonts` (ships with Nuxt UI).

## 2. App shell (`layouts/default.vue`)

Built with `UDashboardGroup` → `UDashboardSidebar` + `UDashboardPanel`.

### Sidebar: rail + menu (exactly as docs/design)

- **Rail** (68 px, always visible on desktop): ⋯ more menu, black **+** create menu, separator, workspace avatars (active has a ring). Collapsed: also section icons with tooltips, » expand, account avatar.
- **Menu column**: logo + name + « collapse; MAIN MENU (Forms with status children + colour dots, Responses, Analytics, Integrations); separator; RESOURCES with **+** (coloured folder icons); SYSTEM pinned to the bottom (Dark mode switch, Settings, Help & support); user card (avatar, name, email, ⇅). Active top-level item: grey row + black bar on the rail border; active child: bold text.

- **Expanded:** full menu (icon + label + groups), resizable within limits.
- **Collapsed:** only the **rail** (icons with tooltips) remains.
- **Hover-to-peek:** only when collapsed, hovering the rail opens the full menu as an overlay; leaving it closes it again. Clicking the pin/collapse button switches between expanded and collapsed permanently (remembered in a cookie).
- Implementation: `UDashboardSidebar` with `collapsible` and `v-model:collapsed`; a `peek` state set on `mouseenter`/`mouseleave` (with ~150 ms delay to avoid flicker) renders the expanded content over the page without shifting layout. Keyboard: `[` toggles collapse; focus entering the rail also opens the peek.
- While the peek is open the rail behind it is `inert`, so Tab goes peek → page and Shift+Tab from the page lands on the peek's last item. Esc closes the top-most layer first (dialog/menu before peek).
- **Mobile:** sidebar becomes a slide-over drawer opened from the navbar menu button.
- Top: tenant logo/name switcher (organisation switcher if several). Bottom: help, theme switch, user menu.

### Menu structure

Forms · Templates · Responses · Analytics · Option Sets · Data sources (own rail area) · API service (own rail area) · Webhooks · Settings · Audit Trail (early, F4) · (later) Users · Dashboard · Roles & Access.

### Navbar (`UDashboardNavbar`) and page header

Header bar = page header (owner, 2026-10-02): **left** page title with a small line under it (breadcrumbs on nested pages · subtitle); **right** search (`Ctrl/⌘+K`), the page's own buttons (outline secondary, solid black primary), language, notifications, theme (below `lg`). The content area holds only content. Phones: ☰ + title, search icon, page buttons as icons, notifications, theme.

### Footer

`AppFooter` at the bottom of every page (and auth pages): © year · version; Help & support, Keyboard shortcuts. Phones: one line (© · version).

Breadcrumbs (all segments clickable), search / command palette (`⌘K`/`Ctrl+K` via `UDashboardSearch`: pages, actions, language, theme), notifications, language switch (`sm`+; on phones via user menu / search), theme switch (`UColorModeButton`). User menu sits at the bottom of the sidebar (design reference).

### Keyboard shortcuts

`?` help · `Ctrl/⌘+K` search · `[` collapse sidebar · `g` then `f` Forms, `t` Templates, `r` Responses, `a` Analytics, `o` Option sets, `s` Settings · `Esc` close. Shortcuts never fire while typing in an input.

### Global loading and feedback

`<NuxtLoadingIndicator color>` top bar on navigation; page skeletons that mirror the final layout; `UButton :loading` busy state; `UProgress` for uploads/exports; toasts for success/error; inline field errors.

## 3. Shared building blocks

- **`DataView`**, props: `columns`, `fetcher`, `gridCard` slot, `filters` schema, `defaultView`. Provides: Table (`UTable`, TanStack-based sorting, column visibility, row selection, sticky header) ↔ Grid (responsive `UCard` grid) switch; `FilterBar` (search, select filters, status chips, **date range**, reset); server-side pagination (`UPagination`, page-size selector); empty, loading (skeleton rows/cards) and error states; URL-synced query (`?page=&q=&status=&from=&to=&sort=`) so views are shareable and back-button safe.
- **`ConfirmDialog`**, **`EmptyState`**, **`PageHeader`** (title, description, actions), **`StatusBadge`**, **`CopyField`**, **`QrCode`**.
- **Forms:** `UForm` + zod schemas; submit button busy; prevent double submit; dirty-state warning on leave.
- **`useApi`**, envelope encrypt/decrypt (WebCrypto), bearer, CSRF, refresh on `FRM-AUTH-1001`, re-handshake on `FRM-SEC-1004`, typed responses, `try/catch/finally` inside, cancellation via `AbortController`.
- **`useErrorHandler`**, maps error codes (see ERROR-CODES.md) to messages; shows trace ID for support.

## 4. Tenant detection and auth screens

- `middleware/tenant.global.ts` reads `window.location.host`: `manage.*` → default entry mode; `{sub}.*` → fetch tenant public profile (`GET /api/v1/tenants/public`): name, logo, colours, enabled auth providers, status. Unknown subdomain → friendly "workspace not found" page with link to manage.
- **Login** (`/auth/login`): tenant branding; email + password; enabled providers as buttons (Google, Microsoft, Apple, Facebook, SAML/OIDC later) only those the tenant enabled; "forgot password"; on manage.\* also "find my workspace".
- **OTP** (`/auth/otp`): 6-box input (`UPinInput`), auto-advance, paste support, resend countdown, switch channel, attempts left. Required on **every** login.
- **Signup** (`/auth/signup`, on manage.\* only): name, email, password (strength meter) or social signup → OTP → choose subdomain (live availability check, reserved names blocked) → workspace created → redirect to `{sub}` → onboarding.
- **Onboarding wizard** (`/onboarding`): company details, logo/branding, country/timezone/currency, team invites (optional), first form from a template. Skippable steps, progress indicator.
- Forgot / reset password, find workspace (email → list of workspaces → redirect).

## 5. Page map (portal)

| Route                                                                                                                  | Page                                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                                                                                                                    | redirect → `/forms` (Dashboard later)                                                                                                                           |
| `/forms`                                                                                                               | All forms, DataView; filters: status, folder, owner, tags, date range; actions: new, duplicate, move, archive, delete (trash)                                  |
| `/forms/new`                                                                                                           | Start blank / from template / import JSON                                                                                                                       |
| `/forms/[id]/build`                                                                                                    | Builder                                                                                                                                                         |
| `/forms/[id]/design`                                                                                                   | Designer (theme)                                                                                                                                                |
| `/forms/[id]/logic`                                                                                                    | Logic rules                                                                                                                                                     |
| `/forms/[id]/settings`                                                                                                 | Form settings (submission rules, notifications, destinations, limits, schedule, thank-you, SEO)                                                                 |
| `/forms/[id]/share`                                                                                                    | Share, links, short URL, QR, embed (iframe), access grants                                                                                                      |
| `/forms/[id]/responses`                                                                                                | Responses DataView + single response slide-over                                                                                                                 |
| `/forms/[id]/analytics`                                                                                                | Form analytics                                                                                                                                                  |
| `/forms/[id]/preview`                                                                                                  | Preview in device frames (desktop / tablet / phone, sideways), draft or live, jump to any page; read only                                                     |
| `/forms/[id]/versions`                                                                                                 | Version history, compare, restore                                                                                                                               |
| `/forms/[id]/preview`                                                                                                  | Preview (desktop/tablet/mobile frames)                                                                                                                          |
| `/forms/trash`                                                                                                         | Soft-deleted forms, restore                                                                                                                                     |
| `/templates` · `/templates/category/{key}` · `/templates/mine` · `/templates/{key}`                                | Formalie's categories (counts + use) → one category's templates; your own templates apart; one template (preview, use)                                              |
| `/responses`                                                                                                           | Cross-form responses inbox                                                                                                                                      |
| `/option-sets`                                                                                                         | Predefined select lists                                                                                                                                         |
| `/api-service/webhooks`                                                                                                | Webhooks (F13; old `/integrations/*` links redirect; API keys folded into tokens 2026-10-06)                                                                                |
| `/data-sources`                                                                                                        | Data sources area (own rail icon, own menu, F12): overview of the sections                                                                                      |
| `/data-sources/connections` · `/explorer` · `/query` · `/saved-queries` · `/destinations` · `/transfers` · `/activity` | Connections, database explorer, query editor, saved queries, destinations (form data → tables), imports & exports, activity (placeholders until F12)            |
| `/api-service`                                                                                                         | API service area (own rail icon, own menu, F13): overview, link · embed · API channels, example endpoint                                                       |
| `/api-service/services` · `/endpoints` · `/auth` · `/access` · `/logs` · `/analytics` · `/docs`                        | Services (containers), endpoints from forms, tokens & headers, allow / block rules, request logs, analytics, docs & testing (placeholders until F13)            |
| `/settings/*`                                                                                                          | Company, branding, domain & subdomain, authentication, security, localisation, notifications & email templates, themes, data retention, embed defaults, billing |
| `/settings/themes` · `/settings/themes/new` · `/settings/themes/[id]`                                                  | Themes library (system / saved / created) and the theme editor (designer on a sample form)                                                                      |
| `/profile/*`                                                                                                           | My profile, password, MFA, sessions/devices                                                                                                                     |
| `/audit`                                                                                                               | Audit trail: every action (who, what, when, where, before / after), filters, export, **early (F4)**                                                            |
| `/users`, `/roles`, `/dashboard`                                                                                       | **Last**                                                                                                                                                        |

Public (SSR, `layouts/public.vue`) on `forms.formalie.*` and workspace subdomains: `/[formKey]/fill` form renderer, `/[formKey]/embed` (chrome-less for iframe), `/s/[code]` short link redirect, closed/expired/not-found states.

## 6. Form builder (`/forms/[id]/build`)

Three panes on desktop: **Field palette** (left, searchable; tabs Fields by category · Saved fields · Lists) · **Canvas** (centre, pages as tabs/stack) · **Inspector** (right, field properties, validation, logic shortcut). On tablet: palette and inspector become slide-overs; on phone: canvas with bottom `UDrawer` for palette/inspector (editing works on phone, comfortable on desktop).

- Drag from palette to canvas; reorder fields, rows, sections, pages; drop indicators; auto-scroll; multi-column rows (12-col grid widths: full, 1/2, 1/3, 2/3, 1/4).
- Select (click/Enter), multi-select (Shift/Ctrl), duplicate (`Ctrl+D`), delete (`Del` with undo toast), move up/down (`Alt+↑/↓`), undo/redo (`Ctrl+Z`/`Ctrl+Shift+Z`).
- Autosave to draft (debounced), "Saved · 2s ago" indicator, conflict detection (version number).
- Top bar: form name (inline edit), status badge (Draft/Published/Changes not published), Preview, Publish (with change summary), more menu.
- Field registry (`utils/field-registry.ts`): one definition per field type → palette entry, default props, inspector schema, renderer component, validation builder. Adding a field type = one registry entry + components.
- Schema is JSON (see API-CONTRACT `FormSchema`); the same renderer is used in preview, public form and embed.

## 7. Designer (`/forms/[id]/design`)

Live preview on the right, controls on the left in collapsible groups: Page (frame around the form on its link: branded · spotlight · side panel · minimal) · Layout · Background · Form container (border, radius, shadow, padding, max width) · Typography · Colours · Inputs · Buttons · Header/cover · Thank-you page · Custom CSS (paid plans, sanitised). Device preview toggle. Save as theme / apply theme. Implemented as CSS variables applied on the renderer root only.

## 8. Share and embed (`/forms/[id]/share`)

- Public link with custom slug (availability check), short URL, QR (download PNG/SVG), copy buttons.
- Access: public / password / invite-only / organisation only; expiry; response limit; schedule.
- People access: add users with **Edit** or **View** (and responses view).
- Embed: iframe snippet with auto-resize script, width/height options, allowed domains list; live preview.
- SEO: title, description, OG image (upload or auto), noindex toggle; preview of the link card.

## 9. Responses

DataView with dynamic columns from the form schema; filters per field type; date range; status/tags; single response slide-over with keyboard next/prev (`J`/`K`); export dialog (XLSX/CSV/PDF, selected/all/filtered) with job progress and download.

## 10. Languages (i18n)

- `@nuxtjs/i18n`, strategy `no_prefix` (URLs stay the same in every language). Choice stored in the `formalie_locale` cookie; first visit uses the browser language, fallback English.
- 20 languages: English, Français, Español, Português (BR), Deutsch, Italiano, Nederlands, Polski, Русский, Українська, Türkçe, العربية (RTL), हिन्दी, বাংলা, 简体中文, 日本語, 한국어, Bahasa Indonesia, Tiếng Việt, Kiswahili. Defined once in `shared/utils/i18n/locales.ts`; messages in `i18n/locales/{code}.json`.
- `<html lang dir>` follow the active language; Nuxt UI's own component strings use the matching `@nuxt/ui/locale` (English where Nuxt UI has none, e.g. Swahili).
- Language switch (`AppLocaleSwitch`, searchable `USelectMenu`) in the navbar and on auth pages; later also a per-user default in Profile and a tenant default in Settings → Localisation.
- Public forms (`/{formKey}/fill` · `/embed`): the form's own language setting (`schema.settings.language`) wins; respondents can switch when the form owner enables several languages (F10).
- RTL: logical Tailwind utilities only (`ms-/me-/ps-/pe-/start-/end-`).
- Dates, numbers, currency via `Intl` with the active locale and tenant timezone/currency.

## 11. Accessibility

WCAG 2.2 AA target: labels on every input, aria-live for toasts and async status, focus trapping in overlays (Nuxt UI does this), sufficient contrast in both themes, reduced-motion respected.

## 12. Performance

Lazy-load heavy routes (builder, designer, analytics charts); `useAsyncData` with stable keys wrapping `useApi` calls (never raw `useFetch`); keep payloads paginated; virtualise very long tables and builder canvases.

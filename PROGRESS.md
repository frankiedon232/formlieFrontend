# Formalie Portal — Progress

The single place to see **what we are building, what is done and what is next**. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-02 · **Current phase:** F4 — Audit trail

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ waiting on backend

## Overview

| Phase | Name                                              | Status | Done |
| ----- | ------------------------------------------------- | ------ | ---- |
| F0    | Foundation                                        | ✅     | 100% |
| F1    | App shell                                         | ✅     | 100% |
| F2    | Core plumbing                                     | ✅     | 100% |
| F3    | Workspace detection + sign-in                     | ✅     | 100% |
| F4    | Audit trail                                       | ⬜     | 0%   |
| F5    | Onboarding wizard                                 | ⬜     | 0%   |
| F6    | Forms list and lifecycle                          | ⬜     | 10%  |
| F7    | Form builder                                      | ⬜     | 0%   |
| F8    | Designer (themes)                                 | ⬜     | 0%   |
| F9    | Renderer, preview, share, embed, short links, SEO | ⬜     | 0%   |
| F10   | Responses                                         | ⬜     | 0%   |
| F11   | Templates gallery                                 | ⬜     | 0%   |
| F12   | Settings                                          | ⬜     | 0%   |
| F13   | Option sets & integrations                        | ⬜     | 0%   |
| F14   | Profile                                           | ⬜     | 0%   |
| F15   | Users                                             | ⬜     | 0%   |
| F16   | Analytics                                         | ⬜     | 0%   |
| F17   | Live collaboration (optional)                     | ⬜     | 0%   |
| F18   | Dashboard                                         | ⬜     | 0%   |
| F19   | Roles & access (last)                             | ⬜     | 0%   |

**Every phase is only done when:** phone / tablet / desktop checked · keyboard-only checked · light + dark checked · Arabic RTL checked · every new action recorded in the audit trail (from F4 on) · loading, empty and error states present · every new string in all 20 languages · matches [docs/design](docs/design/README.md) · typecheck, lint and tests green · this file and the docs updated · committed and pushed.

---

## F0 — Foundation ✅

**Goal:** a correctly configured Nuxt 4 project that runs on every dev host, speaks the secure protocol and supports 20 languages.

### Dev environment

- ✅ Wildcard certificate covering `formalie.dev`, `*.formalie.dev`, `localhost`, `*.localhost`, `127.0.0.1`, `::1`, LAN IP
- ✅ Hosts entries for `manage.` and test workspaces
- ✅ `vite.server.allowedHosts` for `.formalie.dev`
- ✅ `/api/**` dev proxy to FastAPI with `X-Forwarded-Host` (when the mock is off)
- ✅ `.env.example` (mock switch, proxy target, certificate paths, `NODE_EXTRA_CA_CERTS`)
- ✅ Access matrix verified on every host (manage, root, workspaces, localhost, 127.0.0.1, LAN IP)

### Look and feel

- ✅ `main.css` with Tailwind + Nuxt UI imports and `@theme` tokens only
- ✅ Monochrome primary (black in light, white in dark), violet secondary, zinc neutrals
- ✅ Font Manrope 300–700 (identified from the design), motion tokens (motion-safe)

### App setup

- ✅ `app.vue` with `UApp`, top loading bar, route announcer, layouts
- ✅ Layouts: `default` (portal), `auth`, `public`, `blank`
- ✅ Rendering: portal client-side, `/f/**` and `/s/**` server-side
- ✅ Security headers (HSTS, nosniff, Referrer-Policy, Permissions-Policy, COOP, frame options; CSP in production)
- ✅ Runtime config: API base, mock switch, root domain, manage subdomain, app version

### Mock API (until FastAPI exists)

- ✅ Real ECDH handshake + encrypted envelopes (expiry, replay, integrity, method/path binding)
- ✅ CSRF tokens bound to the session key
- ✅ Standard response / error helpers with `FRM-*` codes, server-side pagination helper

### Tooling

- ✅ TypeScript strict, ESLint (blocks component/composable imports), Prettier, Vitest
- ✅ `pnpm typecheck:dev` that does not disturb a running dev server

### Languages

- ✅ 20 languages (en, fr, es, pt, de, it, nl, pl, ru, uk, tr, ar, hi, bn, zh-CN, ja, ko, id, vi, sw)
- ✅ Arabic right-to-left, Nuxt UI component strings follow the language
- ✅ Language switchers with country flags and English names (searchable)
- ✅ Test: every language has every key, same placeholders, no empty strings, no broken `@`

---

## F1 — App shell ✅

**Goal:** the portal frame exactly as in the design references.

### Sidebar

- ✅ Rail: more menu, black **+** create menu, workspace avatar(s)
- ✅ Menu column: brand + collapse, MAIN MENU / RESOURCES / SYSTEM
- ✅ Forms status children on a timeline with square colour bullets
- ✅ Active item: grey pill + black edge bar; active child bold
- ✅ Dark mode switch, Settings, Help & support, user card (name, email, menu)
- ✅ Collapse to rail (`[`), remembered; hover / keyboard peek of the full menu; phone drawer

### Header bar (= page header)

- ✅ Page title, subtitle, breadcrumbs (nested pages) on the left
- ✅ Search (`Ctrl/⌘+K`), page buttons (outline + solid), language, notifications, theme on the right
- ✅ Phones: title only, buttons collapse to icons

### Everything else in the frame

- ✅ Command palette: pages, actions, language, theme
- ✅ Keyboard shortcuts + help dialog (`?`, `g` then a letter, `Esc`)
- ✅ Draggable dialogs (`AppModal`: mouse, touch, arrow keys; docked on phones)
- ✅ Notifications panel (empty state until the backend sends notifications)
- ✅ Footer (© · version · help · shortcuts)
- ✅ Error page (404 / generic), workspace not found / suspended
- ✅ Placeholder page for every menu entry (no dead links)

---

## F2 — Core plumbing ✅

**Goal:** the shared building blocks every feature uses.

- ✅ Framework-free API client: envelope, CSRF, re-handshake, token refresh, abort, network errors (8 tests)
- ✅ `useApi()` (get / post / put / patch / delete / list), client-only, memory-only token
- ✅ `useErrorHandler()`: translated toasts for all 48 error codes, copyable support reference, form field errors
- ✅ `useBusy()`: loading state, no double submit, success toast
- ✅ `useFormat()`: dates, relative time, numbers, percent, currency, file sizes in the active language
- ✅ **DataView** — owner-approved, keep unchanged:
  - ✅ Table / Grid switch remembered per page
  - ✅ Search (`/`), Filter popover, filter chips, clear all
  - ✅ Date range with presets + calendar
  - ✅ Sort menu + sortable headers
  - ✅ Row selection + bulk bar, ⋯ row actions
  - ✅ Skeletons, empty, no-results, error + retry
  - ✅ Server pagination with page size; everything in the URL
- ✅ Confirm dialog (`useConfirm()`), copy field, status badge
- ✅ Forms list wired to the mock as the first DataView user

---

## F3 — Workspace detection + sign-in ✅

**Goal:** every way of reaching the app lands in the right workspace, and signing in is secure, simple and beautiful.

### Workspace detection

- ✅ Host → manage entry / workspace / not found (shared resolver, 11 tests)
- ✅ Workspace public profile (name, enabled sign-in methods, status)
- ✅ Unknown / reserved / suspended workspace pages
- ✅ Dev-only `?tenant=` for localhost and phones on Wi-Fi
- ✅ "Continue to <last workspace>" on `manage.`

### Mock backend for auth

- ✅ Test workspaces and people (see README → Test accounts)
- ✅ One-time codes: 5 min, 5 attempts, resend after 60 s (max 3)
- ✅ 15-min access token; single-use rotating refresh cookie; reuse revokes the session
- ✅ Workspace check on every protected call
- ✅ One-time ticket for the new workspace after signup

### Screens

- ✅ Sign in (workspace) — redesigned: dark showcase panel + roomy form
- ✅ Sign in on `manage.` (find workspace / continue / create)
- ✅ One-time code screen (paste, auto-submit, resend countdown, email/SMS switch, attempts left)
- ✅ Social sign-in buttons for the providers the workspace enabled
- ✅ First signup on `manage.` offers Google, Microsoft, Apple and Facebook as well as email (owner request)
- ✅ Signup in 3 steps with password strength and live subdomain check
- ✅ Find my workspace (email → code → list)
- ✅ Forgot / reset password (email → code + new password)
- ✅ Welcome hand-off on the new workspace
- ✅ Visual polish of signup, find workspace and reset screens to the new sign-in standard
- ✅ Arabic RTL pass on every auth screen
- ✅ Keyboard-only pass on every auth screen
- ✅ Phone pass on signup, find workspace and reset

### Session

- ✅ Session restored after reload; logout; "session expired" redirect back to sign-in

### Showcase message (global platform)

- ✅ Headline + platform description (any form, data, systems, access, any organisation, anywhere)
- ✅ Preview: supplier onboarding form with consent, responses visible to compliance, database sync
- ✅ "5+ databases" (MySQL, MariaDB, Oracle, PostgreSQL, SQL Server) or built-in encrypted storage

### Waiting on backend

- ⏸ Real Google / Microsoft / Apple / Facebook sign-in (OAuth)
- ⏸ Social signup callback: skip the code step, go straight to the workspace step
- ⏸ SAML / OIDC single sign-on (later)
- ⏸ Real email / SMS delivery of codes; authenticator-app (TOTP) codes

---

## F4 — Audit trail ⬜

**Goal:** every action in a workspace is recorded — who, what, when, where (IP, location, device) and before / after values — and admins can search, filter and export it. Built now so every later phase records its own actions as it is built (owner request, product overview §11).

### Event model

- ⬜ Event shape in `API-CONTRACT.md`: id, time, actor (user / API key / system), action, resource (type, id, name), organisation, IP, location (city, country), device / browser, outcome (success / failed / blocked), before / after changes, request id
- ⬜ Event catalogue in one place (`shared/utils/audit/events.ts`): action keys grouped by area (sign-in, workspace, forms, responses, settings, users, integrations), each with an icon, severity and a translated label in all 20 languages
- ⬜ Shared types in `shared/types/audit.ts`

### Mock backend

- ⬜ Audit store with realistic international sample history (several people, countries, devices)
- ⬜ Record what already exists: sign-in success / failure, code sent / verified / failed, too many attempts, sign-out, session expired, refresh reuse (session revoked), password reset, signup, workspace created, find workspace
- ⬜ Record form actions in the mock (create, rename, move, archive, delete, restore) — later phases add theirs
- ⬜ `GET /audit-logs` (search, filters, date range, sort, server pagination), `GET /audit-logs/{id}`, `POST /audit-logs/export` (background job with progress)

### Audit trail page (`/audit`)

- ⬜ DataView: table and grid, search, filters (person, action / area, resource type, outcome, organisation, country), date range, sort, server pagination
- ⬜ Event detail slide-over: summary sentence ("Sofia Martins archived the form Supplier onboarding"), who / when / where / device, before → after changes side by side, request id with copy
- ⬜ Export to Excel / CSV with progress; filters carried into the export
- ⬜ Links from an event to the resource (form, user, setting) when it still exists
- ⬜ "Audit trail" in the sidebar (SYSTEM), breadcrumbs, header title / subtitle / export button
- ⬜ Empty, loading and error states; phone layout (cards) and keyboard access

### Reusable activity

- ⬜ `AuditTimeline` component (latest events for one resource) to drop into forms, responses, users and settings pages as they are built
- ⬜ Security view filter preset (failed / blocked sign-ins, revoked sessions) used later by Settings → Security

### Access

- ⬜ Workspace admins only for now; a proper `audit.read` permission arrives with Roles & access (F19)

### Waiting on backend

- ⏸ Real IP geolocation and device detection
- ⏸ Tamper-evident storage (hash chain) and retention period per plan
- ⏸ Audit events for API-key and webhook calls

---

## F5 — Onboarding wizard ⬜

**Goal:** a new workspace is ready to use in a few skippable steps.

- ⬜ Wizard page with stepper and progress (resume where the user left off)
- ⬜ Step: company details (legal name, industry, size, country)
- ⬜ Step: branding (logo upload with progress, brand colour, preview)
- ⬜ Step: localisation (country, timezone, currency, language, date / number format)
- ⬜ Step: invite team (optional; emails + role)
- ⬜ Step: first form (pick a template or start blank)
- ⬜ Skip / back on every step, finish → Forms
- ⬜ Mock endpoints `GET/PATCH /onboarding`
- ⬜ Shown after signup; reachable later from Settings

---

## F6 — Forms list and lifecycle ⬜

**Goal:** everything you do _with_ forms before opening the builder.

- ✅ Forms list with DataView (search, status / folder filters, date range, sort, table / grid)
- ⬜ New form: blank / from template / import JSON
- ⬜ Rename (inline), duplicate, move to folder
- ⬜ Folders: create, rename, delete, filter by folder
- ⬜ Tags: add / remove, filter by tag
- ⬜ Owner filter
- ⬜ Archive / unarchive; close / reopen; unpublish
- ⬜ Delete → Trash; Trash page with restore and permanent delete (confirm)
- ⬜ Bulk actions (archive, move, delete) on selected rows
- ⬜ Live counts next to Drafts / Published / Closed in the sidebar
- ⬜ Optimistic locking (`row_version`) with a clear "changed by someone else" message
- ⬜ Mock endpoints for all of the above

---

## F7 — Form builder ⬜

**Goal:** a robust drag-and-drop builder that works on desktop and stays usable on tablet and phone.

### Fields (one registry entry each: palette item, defaults, inspector, renderer, validation)

- ⬜ Text: short text, long text, rich text, email, phone, URL, number, currency
- ⬜ Dates: date, time, date-time, date range
- ⬜ Choice: dropdown, multi-select, radio, checkbox, toggle, ranking, matrix / grid
- ⬜ Rating: rating, scale / NPS, slider
- ⬜ Files: file upload, image upload, signature
- ⬜ Location: address (with map), country / state
- ⬜ Advanced: hidden field, calculated field, payment (later)
- ⬜ Layout: section header, paragraph / HTML block, divider, image, page break

### Canvas

- ⬜ Palette with search and categories
- ⬜ Drag from palette to canvas; reorder fields, rows, sections, pages (drop indicators, auto-scroll)
- ⬜ Multi-column rows on a 12-column grid (full, ½, ⅓, ⅔, ¼)
- ⬜ Keyboard alternatives for every move (move up / down, move to page)
- ⬜ Select, multi-select (Shift / Ctrl), duplicate (`Ctrl+D`), delete with undo
- ⬜ Undo / redo (`Ctrl+Z` / `Ctrl+Shift+Z`)
- ⬜ Multi-page forms with progress bar; nested sections

### Inspector

- ⬜ Field properties, width, required, help text, placeholder, default value
- ⬜ Validation rules (min / max, length, pattern, file type / size)
- ⬜ Options or reusable option sets
- ⬜ Prefill from URL parameters

### Logic (`/forms/[id]/logic`)

- ⬜ Show / hide, skip / jump to page, required-if
- ⬜ Calculated values
- ⬜ Visual rule editor with a plain-language summary

### Saving and publishing

- ⬜ Autosave to draft with "Saved · 2s ago", conflict detection
- ⬜ Top bar: inline name, status badge, Preview, Publish (with change summary)
- ⬜ Editing a published form creates a draft; published version stays live
- ⬜ Versions page: history, compare, restore

### Devices

- ⬜ Tablet: palette and inspector as slide-overs; phone: bottom drawer
- ⬜ Heavy parts lazy-loaded; long canvases virtualised

---

## F8 — Designer (themes) ⬜

**Goal:** organisations design their form pages as they want.

- ⬜ Live preview with desktop / tablet / phone toggle
- ⬜ Layout (single, two-column, card, full-bleed, split with image)
- ⬜ Background (colour, gradient, image, overlay)
- ⬜ Form container (width, padding, border, radius, shadow)
- ⬜ Typography (font, sizes, weights)
- ⬜ Colours (primary, text, inputs, errors), inputs and buttons style
- ⬜ Header / banner, logo, cover page, thank-you page
- ⬜ Custom CSS (paid plans, sanitised)
- ⬜ Save as theme, apply theme; themes library in Settings
- ⬜ Applied as CSS variables on the renderer only

---

## F9 — Renderer, preview, share, embed, short links, SEO ⬜

### Renderer

- ⬜ One renderer for preview, public page and embed
- ⬜ Public page `/f/[slug]` server-rendered with SEO (title, description, image, canonical, noindex)
- ⬜ Secure server-side fetch for server-rendered pages
- ⬜ Closed / expired / not found / password-protected / response-limit states
- ⬜ Multi-page with progress, save and resume
- ⬜ File uploads to secure upload links with progress
- ⬜ Spam protection (captcha)
- ⬜ Thank-you page or redirect
- ⬜ Preview page with device frames

### Share

- ⬜ Custom link (slug availability), short link, QR code (PNG / SVG), copy buttons
- ⬜ Access: public, password, invite-only, organisation-only; expiry, response limit, schedule
- ⬜ People access: edit / view / responses
- ⬜ Embed: iframe snippet with auto-resize, size options, allowed domains, live preview
- ⬜ SEO settings with link-card preview
- ⬜ Short link redirect `/s/[code]`

---

## F10 — Responses ⬜

- ⬜ Per-form responses (DataView, columns from the form)
- ⬜ Inbox across all forms
- ⬜ Filters per field type, date range, status, tags
- ⬜ Response detail slide-over with next / previous (`J` / `K`)
- ⬜ Status (new, reviewed, approved…), tags, notes, edit history
- ⬜ Bulk actions
- ⬜ Export XLSX / CSV / PDF (all, filtered, selected) with progress and download

---

## F11 — Templates gallery ⬜

- ⬜ System + organisation templates, categories, search
- ⬜ Template preview
- ⬜ Use a template → new form
- ⬜ Save any form as a template

---

## F12 — Settings ⬜

**Goal:** one place where workspace admins control everything about their workspace. Each section is its own page under `/settings/*`, with a section menu (sidebar list on desktop, select on phones), unsaved-changes warning and a save bar.

### Settings shell

- ⬜ `/settings` overview: section cards with a one-line status each (e.g. "2 sign-in methods enabled")
- ⬜ Section navigation (desktop list, phone select), breadcrumbs, unsaved-changes guard
- ⬜ Search inside settings (also from the command palette)

### Company & branding

- ⬜ Company profile: legal name, display name, industry, size, address, country, tax / registration number, support email and phone
- ⬜ Branding: logo (light + dark), favicon, brand colour, sign-in page image and message; live preview of the workspace sign-in page

### Domain & workspace address

- ⬜ Workspace subdomain (change with availability check, redirect from the old one)
- ⬜ Custom domain (DNS records to add, verification status, HTTPS status)
- ⬜ Custom short-link domain (later)

### Organisations

- ⬜ Several organisations per workspace (subsidiaries, branches): create, rename, archive
- ⬜ Organisation switcher in the rail (design: workspace avatars)

### Authentication

- ⬜ Sign-in methods: enable / disable email + password, Google, Microsoft, Apple, Facebook — only enabled ones appear on the workspace sign-in page
- ⬜ Single sign-on: SAML / OIDC set-up (metadata, certificates, test sign-in) — later
- ⬜ One-time code policy: channels (email, SMS, authenticator app), code length / expiry, attempts
- ⬜ Enforce multi-factor authentication for admins / everyone
- ⬜ Allowed email domains for invites and self-signup (optional)

### Security

- ⬜ Password rules (length, character types, reuse, expiry)
- ⬜ Session timeout and maximum session length, sign out everywhere
- ⬜ IP allowlist (CIDR ranges, test my IP)
- ⬜ Security events overview (recent sign-ins, blocked attempts) — links to audit trail

### Localisation

- ⬜ Default language, timezone, date and number format, first day of week, currency
- ⬜ Languages offered on public forms

### Notifications & email templates

- ⬜ Which events notify whom (new response, export ready, form closing, security alerts)
- ⬜ Email templates (sign-in code, invitation, response receipt, notification) with preview and test send, per language
- ⬜ Sender name and reply-to address (custom sending domain later)

### Privacy & data

- ⬜ Data retention per form / default (auto-delete responses after N days)
- ⬜ Consent texts and privacy notice link shown on forms
- ⬜ Data requests: export or delete a respondent's data
- ⬜ Data residency / storage region (if offered by the plan)

### Themes & form defaults

- ⬜ Themes library (created in the designer, F8): list, rename, set default, delete
- ⬜ Embed defaults (allowed domains, size), default form settings (progress bar, save and resume)

### Billing & subscription

- ⬜ Current plan, usage against limits (forms, responses per month, seats, destinations)
- ⬜ Upgrade / change plan, payment method, invoices
- ⬜ Plan-limit messages wherever a limit is hit (FRM-PLAN-1001 / 1002)

---

## F13 — Option sets & integrations ⬜

### Option sets (reusable choice lists)

- ⬜ List (DataView), create, rename, delete (confirm when used by forms)
- ⬜ Items: add, edit, bulk paste, import CSV, reorder (drag + keyboard), values vs labels, translations
- ⬜ "Used in" list of forms

### Destinations (where responses go)

- ⬜ Built-in encrypted storage (default)
- ⬜ Connect MySQL, MariaDB, Oracle, PostgreSQL, SQL Server: connection form, test connection, SSL options
- ⬜ Table and field mapping per form, sync status and error log, retry

### Webhooks

- ⬜ Create (URL, events, secret), signed payloads, test delivery
- ⬜ Delivery log with retries and response details

### API keys

- ⬜ Create (name, scopes, expiry), show once, copy, revoke, last used

### Other integrations (later)

- ⬜ Google Sheets, Slack, email notifications to external addresses

---

## F14 — Profile ⬜

- ⬜ My profile (name, photo, language, timezone)
- ⬜ Change password
- ⬜ Authenticator app (QR, recovery codes), SMS number
- ⬜ Sessions and devices (see and sign out)

---

## F15 — Users ⬜

- ⬜ Users list (DataView), invite by email with role, resend / revoke invites
- ⬜ Enable / disable, reset password or MFA
- ⬜ Team avatars + "Invite member" in the header (design reference)

---

## F16 — Analytics ⬜

- ⬜ Per form: views, starts, completions, completion rate, average time
- ⬜ Drop-off per page and field
- ⬜ Per-question charts, NPS
- ⬜ Date range, export

---

## F17 — Live collaboration (optional) ⬜

- ⬜ Presence, cursors and selections in the builder
- ⬜ Conflict-free editing
- ⬜ Comments on fields (later)

---

## F18 — Dashboard ⬜

**Goal:** the workspace home, built after everything else so it shows what matters (design reference 2). Replaces the Forms redirect on `/` once done.

- ⬜ KPI cards with trend vs previous period (active forms, responses, completion rate, pending reviews, overdue / closing soon)
- ⬜ Date range + Daily / Weekly / Monthly / Yearly switch
- ⬜ Responses over time chart with tooltip
- ⬜ Top forms / form overview card with progress
- ⬜ Recent responses table (DataView) and activity timeline
- ⬜ Filters (organisation, folder, owner)
- ⬜ Empty state for new workspaces (links to onboarding / first form)
- ⬜ Dashboard entry in the sidebar MAIN MENU (first item, as in the design)

---

## F19 — Roles & access ⬜ (last)

- ⬜ Roles and permissions editor (permission catalogue, custom roles)
- ⬜ Role assignment per user and per organisation; form-level access
- ⬜ Access overview ("who can see what")
- ⬜ Permission to view and export the audit trail (`audit.read`, `audit.export`)

---

## Switching to the real backend ⏸

- ⏸ Turn off the mock and point the proxy at FastAPI
- ⏸ Run the encryption tests against backend test vectors
- ⏸ Compare `API-CONTRACT.md` with the backend's generated contract

---

## New requests log

Owner requests added during development, and where they landed.

| Date       | Request                                                                          | Where       | Status |
| ---------- | -------------------------------------------------------------------------------- | ----------- | ------ |
| 2026-10-02 | Support many languages (at least 15) → 20 languages                              | F0          | ✅     |
| 2026-10-02 | Organise files in sub-folders (max two levels)                                   | all         | ✅     |
| 2026-10-02 | Works on every host (manage, workspaces, localhost, IP)                          | F0          | ✅     |
| 2026-10-02 | Match the design references exactly                                              | F1          | ✅     |
| 2026-10-02 | Flags on the language switcher, breadcrumbs in the header, font from the design  | F1          | ✅     |
| 2026-10-02 | Menu detail: timeline children, square bullets, clean dark text                  | F1          | ✅     |
| 2026-10-02 | Title, subtitle, breadcrumbs and buttons in the header; footer                   | F1 / F2     | ✅     |
| 2026-10-02 | Keep the table / grid / filters flow unchanged                                   | F2          | ✅     |
| 2026-10-02 | "Wow" sign-in screen                                                             | F3          | ✅     |
| 2026-10-02 | Test accounts in the README; realistic test people                               | F3          | ✅     |
| 2026-10-02 | Global positioning (not one country); international sample data                  | F3 / all    | ✅     |
| 2026-10-02 | Show 5+ supported databases or built-in encrypted storage                        | F3 / F12    | ✅     |
| 2026-10-02 | Separate progress file with every task per phase                                 | PROGRESS.md | ✅     |
| 2026-10-02 | Social providers on the first signup; more methods enabled later per workspace   | F3 / F12    | 🟡     |
| 2026-10-02 | Provider buttons on one row with a "Sign up with" caption                        | F3          | ✅     |
| 2026-10-02 | Settings as its own detailed phase; Dashboard after everything, just before RBAC | F12 / F18   | ✅     |
| 2026-10-02 | Audit trail early (its own phase after sign-in), not last                        | F4          | ⬜     |
| 2026-10-02 | Use "Email address" (not "Work email") so any email provider is welcome          | F3          | ✅     |

---

## Progress log

| Date       | Phase | What happened                                                                                                                                                                                    |
| ---------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-10-02 | F0    | Foundation: config, 20 languages, mock API with real encryption, tooling. Checked phone / desktop, light / dark, Arabic, keyboard.                                                               |
| 2026-10-02 | F0    | Access matrix verified on every host; shared host resolver with tests.                                                                                                                           |
| 2026-10-02 | F1    | App shell built, then rebuilt to match the design exactly (rail + menu, header, monochrome).                                                                                                     |
| 2026-10-02 | F1    | Flags, breadcrumbs in the header, Manrope font, menu timeline / square bullets / dark text.                                                                                                      |
| 2026-10-02 | F2    | Core plumbing: secure API client, error handling in 20 languages, DataView live on the mock, confirm dialog, formatters.                                                                         |
| 2026-10-02 | F2    | Header carries title / subtitle / crumbs / buttons; footer added; DataView flow approved.                                                                                                        |
| 2026-10-02 | F3    | Auth built end to end; mock flow verified (codes, tokens, refresh rotation, reuse revokes).                                                                                                      |
| 2026-10-02 | F3    | Sign-in redesigned; full flow verified in the browser (sign in → code → portal → log out) on desktop, phone and dark.                                                                            |
| 2026-10-02 | F3    | Global positioning on sign-in; international sample data; 5+ databases or built-in encrypted storage; realistic test people; this progress file.                                                 |
| 2026-10-02 | F3    | Signup offers Google, Microsoft, Apple, Facebook (manage.*) plus email; new workspaces start with email sign-in, more methods enabled in Settings (F12). Provider callback waits on the backend. |
| 2026-10-02 | F3    | Provider buttons on one row with a "Sign up with / Sign in with" caption: logo + name for 2, logo only (tooltip) for 3–4.                                                                        |
| 2026-10-02 | F3    | "Work email" → "Email address" everywhere, neutral placeholder name@example.com, no "work email" wording (any organisation, any email provider).                                                 |
| 2026-10-02 | F3    | Phase done: RTL, keyboard-only and phone passes on every auth screen (logical tab order, nothing hidden focusable, no overflow at 375 px).                                                       |
| 2026-10-02 | F4    | Audit trail moved up to its own phase right after sign-in (owner); phases renumbered, RBAC is now F19 (last).                                                                                    |

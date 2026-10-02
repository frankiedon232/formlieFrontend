# Formalie Portal — Progress

The single place to see **what we are building, what is done and what is next**. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-02 · **Current phase:** F7 — Form builder (review) → next F8 Designer

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ waiting on backend

## Overview

| Phase | Name                                              | Status | Done |
| ----- | ------------------------------------------------- | ------ | ---- |
| F0    | Foundation                                        | ✅     | 100% |
| F1    | App shell                                         | ✅     | 100% |
| F2    | Core plumbing                                     | ✅     | 100% |
| F3    | Workspace detection + sign-in                     | ✅     | 100% |
| F4    | Audit trail                                       | ✅     | 100% |
| F5    | Onboarding wizard                                 | ✅     | 100% |
| F6    | Forms list and lifecycle                          | ✅     | 100% |
| F7    | Form builder                                      | ✅     | 100% |
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

**Every phase is only done when:** phone / tablet / desktop checked · keyboard-only checked · light + dark checked · Arabic RTL checked · every new action recorded in the audit trail (from F4 on) · loading feedback complete (first-load screen, top bar on navigation and API calls, skeletons, busy buttons, busy rows, progress bars — CLAUDE.md rule 5) · empty and error states present · every new string in all 20 languages · matches [docs/design](docs/design/README.md) · typecheck, lint and tests green · this file and the docs updated · committed and pushed.

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
- ✅ Expand chevron and count badges on the right of each row (owner request); counts for All / Drafts / Published / Closed forms and new responses (`GET /navigation/counts`, refreshed on navigation); menu column widened to fit them

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
- ✅ Branded first-load screen (`app/spa-loading-template.html`) — no blank page while the app starts
- ✅ Top progress bar on every API call, not only navigation (`useApi`; polling uses `background: true`)
- ✅ In-app navigation feedback: top bar starts on click and runs until the new page has its data; sweeping in-page bar under every page header (`useActivity`)

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

## F4 — Audit trail ✅

**Goal:** every action in a workspace is recorded — who, what, when, where (IP, location, device) and before / after values — and admins can search, filter and export it. Built now so every later phase records its own actions as it is built (owner request, product overview §11).

### Event model

- ✅ Event shape in `API-CONTRACT.md`: id, time, actor (user / API key / system), action, resource (type, id, name), organisation, IP, location (city, country), device / browser, outcome (success / failed / blocked), before / after changes, request id
- ✅ Event catalogue in one place (`shared/utils/audit/events.ts`): action keys grouped by area (sign-in, workspace, forms, responses, settings, users, integrations), each with an icon, severity and a translated label in all 20 languages
- ✅ Shared types in `shared/types/audit.ts`

### Mock backend

- ✅ Audit store with realistic international sample history (several people, countries, devices)
- ✅ Record what already exists: sign-in success / failure / blocked (disabled account), code sent / failed, too many attempts, sign-out, refresh reuse (session revoked), password reset requested / done, workspace created, sign-in after signup. (Find my workspace runs on manage.* before any workspace is known, so it is not a workspace event.)
- ✅ Sample history already covers form, response, settings, user and integration actions; live recording is added with each endpoint as it is built (form actions → F6)
- ✅ `GET /audit-logs` (search, filters, date range, sort, server pagination), `GET /audit-logs/{id}`, `GET /audit-logs/facets`, `POST /audit-logs/export` → `GET /exports/{id}` (background job with progress) → single-use download link

### Audit trail page (`/audit`)

- ✅ DataView: table and grid, search, filters (area, result, person, country), date range, sort, server pagination; organisation filter arrives with several organisations per workspace (F12)
- ✅ Event detail slide-over: shareable link `/audit?event=<id>`; result + reason, who / when / where / device, item, before → after changes side by side, technical details, request id with copy, related activity
- ✅ Export to Excel / CSV with progress; search, filters and dates carried into the export (mock writes CSV; real .xlsx from the backend)
- ✅ Links from an event to its item (forms, settings, integrations); user pages follow in F15
- ✅ "Audit trail" in the sidebar (SYSTEM), breadcrumbs, header title / subtitle / export button
- ✅ Empty, loading and error states; phone layout (cards) and keyboard access

### Reusable activity

- ✅ `AuditTimeline` component (latest events for one resource) to drop into forms, responses, users and settings pages as they are built
- ✅ Security view filter preset (failed / blocked sign-ins, revoked sessions) used later by Settings → Security

### Access

- ✅ Workspace admins only for now; a proper `audit.read` permission arrives with Roles & access (F19)

### Waiting on backend

- ⏸ Real IP geolocation and device detection
- ⏸ Tamper-evident storage (hash chain) and retention period per plan
- ⏸ Audit events for API-key and webhook calls

---

## F5 — Onboarding wizard ✅

**Goal:** a new workspace is ready to use in a few skippable steps.

- ✅ Full-screen wizard (`/onboarding`, own layout: brand · language · theme · Finish later) with stepper (any step can be opened), phone progress bar and live preview (sign-in page, regional samples, team, form)
- ✅ Resume where the admin left off (progress stored on the server per workspace)
- ✅ Step: company details (name, industry, size, country with flags, website — `https://` added automatically)
- ✅ Step: branding (logo upload with real progress via pre-signed URL, brand colour presets + custom picker, live preview)
- ✅ Step: regional settings (workspace language, timezone with UTC offsets, currency, date / number format with live examples, first day of the week) — defaults from the device and the company's country
- ✅ Step: invite team (email + role rows, paste a list, duplicates / own email caught)
- ✅ Step: first form (blank or one of 6 starter templates) — finishing opens it in `/forms/new`
- ✅ Skip / back on every step, finish → chosen form (or Forms)
- ✅ Mock endpoints `GET / PATCH /onboarding`, `POST /onboarding/finish`, uploads (`POST /uploads` → PUT to storage → `POST /uploads/{id}/complete`)
- ✅ Every saved step recorded in the audit trail (workspace / branding / localisation changes with before → after, invitations, setup finished)
- ✅ Shown after signup (welcome hand-off); reachable later from Settings and the user menu (owners / admins); members are sent to Forms
- ⬜ Workspace logo in the rail and on the sign-in page (the public profile already returns `logo_url` and brand colour) → F12 Branding
- ⏸ Real invitation emails (F15 Users), real object storage

---

## F6 — Forms list and lifecycle ✅

**Goal:** everything you do _with_ forms before opening the builder.

- ✅ Forms list with DataView (search, status / folder / owner / tag filters, date range, sort, table / grid)
- ✅ New form: blank / from a starter template / import JSON (FormSchema v1 validated + previewed, 1 MB max); `?mode=` and `?template=` preselect
- ✅ Rename (inline in the table: Enter / blur saves, Esc cancels), duplicate, move to folder (with "new folder" on the spot)
- ✅ Folders: create, rename, delete (forms stay, without a folder), filter by folder incl. "No folder"
- ✅ Tags: add / remove (suggestions from the workspace), shown in rows and cards, filter by tag
- ✅ Owner filter
- ✅ Archive / unarchive (back to the previous status); close / reopen; unpublish — menu shows only what fits the status
- ✅ Delete → Trash (confirm); Trash page (`/forms/trash`) with restore, permanent delete (confirm), bulk, Empty Trash, days left
- ✅ Bulk actions (move, archive, delete; restore / delete permanently in Trash) on selected rows, with a summary toast
- ✅ Sidebar counts refresh right after every change; Trash entry with its own count
- ✅ Optimistic locking (`row_version`) with "changed by someone else" and a fresh list
- ✅ Busy rows / cards while an action runs (DataView `busy`), toasts for every result
- ✅ Form overview page (`/forms/{id}`): details, status actions, activity timeline; "Edit" arrives with the builder (F7)
- ✅ Mock endpoints for all of the above (per workspace, persisted across reloads)
- ✅ Every form and folder action recorded in the audit trail with before / after values

---

## F7 — Form builder ✅

**Goal:** a robust drag-and-drop builder that works on desktop and stays usable on tablet and phone.

### Fields (one registry entry each: palette item, defaults, inspector, renderer, validation)

- ✅ Text: short text, long text, email, phone, URL, number, currency (amount with the currency symbol)
- ✅ Rich text — Nuxt UI editor (UEditor + toolbar, TipTap ships with Nuxt UI — no new dependency); Basic / Full toolbar (Full, the default: paragraph / heading 1–6, code, code block, left / centre / right / justify); answer stored as sanitised HTML (owner approved the text-align extension); read-only / disabled hide the toolbar; character count with max length
- ✅ Dates: date, time, date-time, date range
- ✅ Choice: dropdown, multi-select, radio, checkbox, toggle, ranking (drag + ↑ / ↓), matrix / grid
- ✅ Rating: star rating, scale / NPS (with end labels), slider
- ✅ Files: file upload, image upload (types, count, size), signature (draw or type the name)
- ✅ Location: international address, country with flags
- ✅ Advanced: hidden field (prefill), calculated field (formula), payment listed as "soon"
- ✅ Layout: section heading (size, description, divider line, alignment, inline edit), paragraph (written on the canvas, rich text), divider (style, spacing), image (upload with progress or link, resize handle + presets, alignment, caption, link, rounded, alt-text prompt); pages instead of a page-break field

### Canvas

- ✅ Palette with search and categories (click / Enter adds below the selected field; drag drops anywhere)
- ✅ Drag from palette to canvas; reorder fields within a row, between rows, out to their own row (SortableJS, auto-scroll); a dashed "Drop here" placeholder shows the landing spot
- ✅ Multi-column rows on a 12-column grid (full, ½, ⅓, ⅔, ¼, ¾); dropping next to a field shares the row evenly
- ✅ Keyboard alternatives for every move (Alt+↑ / ↓ across rows and pages, Move to page, width menu)
- ✅ Select (click / Enter), multi-select (Shift / Ctrl), duplicate (`Ctrl+D`), delete (`Del`) with an Undo toast
- ✅ Undo / redo (`Ctrl+Z` / `Ctrl+Shift+Z`), typing grouped into one step
- ✅ Multi-page forms (page tabs, add / rename / move / delete with confirm) with progress bar
- ✅ Collapsible sections: a section heading can fold the rows below it (optionally folded at start); folded required fields unfold on submit

### Inspector

- ✅ Field properties: label, help, placeholder, required, width, default value, field key (follows the label until first publish)
- ✅ Validation rules: length, number range, pattern + message, choices min / max, file types / count / size
- ✅ Options: add, rename, reorder (drag or ↑ / ↓), remove, paste a list; matrix rows
- ✅ Reusable option lists: palette **Lists** tab, "Fill from a list" / "Save as list" in the options editor (full option-set management page stays in F13)
- ✅ Saved fields: "Save" in field settings → palette **Saved** tab, click or drag to reuse
- ✅ Prefill from URL parameters (example link shown)
- ✅ Nothing selected → form settings (progress bar, save & resume, thank-you screen); several → bulk width / required / move / duplicate / delete

### Logic (`/forms/[id]/logic`)

- ✅ Show / hide, skip / jump to page, required-if — one evaluator (`shared/utils/forms/logic.ts`) for preview, public form and API; Back follows the path actually taken
- ✅ Calculated values — safe arithmetic parser (never `eval`), formula editor with key chips and checks (unknown key, self-reference)
- ✅ Visual rule editor with a plain-language summary ("When Severity is High, require Photos."), All / Any, reorder, duplicate, delete with undo, broken-rule badges

### Saving and publishing

- ✅ Autosave to draft with "Saved · 2 minutes ago", conflict detection (saving pauses, Reload offered), warning before leaving with unsaved changes
- ✅ Top bar: inline name, status badge, "Changes not published", undo / redo, Preview, Publish (with change summary and blocking issues that jump to the field)
- ✅ Editing a published form creates a draft; published version stays live
- ✅ Live preview: fill it in like a respondent (required checks, pages, thank-you screen) on desktop / tablet / phone widths
- ✅ Versions page: timeline of the draft + published versions, view any version in the preview, compare draft vs version (added / changed / removed), restore (confirm), discard draft changes
- ✅ Build / Logic / Versions share one frame (`FormsBuilderFrame` + `useBuilderSession`); switching saves first

### Devices

- ✅ Laptop+: three panes; tablet: palette and settings as slide-overs; phone: bottom drawers, floating "Add field / Field settings" bar, header folds undo / redo / preview into ⋯
- ✅ Heavy parts lazy-loaded (preview, publish dialogs load on first use)
- ✅ Canvas fills the space between the panes (no fixed width); full-screen mode (button or Ctrl+Shift+F) shows only fields · canvas · settings under a slim bar with name, save status, undo / redo, Preview, Publish, Exit (Esc) — browser full screen when allowed (owner request 2026-10-02)
- ➡️ Canvas virtualisation deferred: it conflicts with drag and drop; revisit if forms > 200 fields feel slow (measured, not guessed)

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
- ⬜ Footer (text, links, logo — e.g. privacy note, contact) (owner request 2026-10-02)
- ⬜ Default theme: a form without a chosen theme uses the workspace default (brand colours + logo from onboarding), so every shared form looks finished
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

### Folders workspace (owner request 2026-10-02 — built here because the stats need response data)

- ⬜ Sidebar "Folders" group (design RESOURCES style): coloured folder icons, form count on the end, **+** to create, "Show all" when long
- ⬜ Folder colour chosen when creating / editing a folder
- ⬜ Folder page `/folders/[id]`: name + actions in the header, KPI cards (forms, published, responses, avg. completion, last activity), the folder's forms in DataView
- ⬜ All folders `/folders`: every folder with the same stats, Table / Grid, sort

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
- ⬜ Session timeout (idle, default 60 min — never shorter than the owner's 1-hour minimum without a warning) and maximum session length, sign out everywhere
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

Full plan: [docs/OPTION-LISTS.md](docs/OPTION-LISTS.md) (owner request 2026-10-02). Simple saved lists already exist (F7).

- ⬜ **F13a List manager:** Option sets page (DataView), create, rename, delete (confirm when used by forms)
- ⬜ Items: add, edit, retire, bulk paste, import CSV / XLSX with column mapping, reorder (drag + keyboard), values vs labels, translations
- ⬜ "Used in" list of forms and fields
- ⬜ **F13b Large lists + autocomplete:** items on the server, "search as you type" field mode, paging
- ⬜ **F13c Cascading lists (levels):** tree lists (e.g. State → City → Location, up to 5 levels), "Cascading choice" field group, child opens with the parent's items only, changing the parent clears children
- ⬜ **F13d Details + auto-fill:** extra columns on items; choosing an item fills other fields (optionally read-only); columns usable in formulas and logic
- ⬜ **F13e Dynamic lists:** live sources — another form's responses, a connected database (read-only query), a JSON URL, a refreshed CSV; refresh schedule and sync log
- ⬜ Public option lookups for respondents (rate limited, published lists only); answers store value + label (+ path)

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

| Date       | Request                                                                                                                                                                                                                                                                                                                                                           | Where       | Status |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------ |
| 2026-10-02 | Support many languages (at least 15) → 20 languages                                                                                                                                                                                                                                                                                                               | F0          | ✅     |
| 2026-10-02 | Organise files in sub-folders (max two levels)                                                                                                                                                                                                                                                                                                                    | all         | ✅     |
| 2026-10-02 | Works on every host (manage, workspaces, localhost, IP)                                                                                                                                                                                                                                                                                                           | F0          | ✅     |
| 2026-10-02 | Match the design references exactly                                                                                                                                                                                                                                                                                                                               | F1          | ✅     |
| 2026-10-02 | Flags on the language switcher, breadcrumbs in the header, font from the design                                                                                                                                                                                                                                                                                   | F1          | ✅     |
| 2026-10-02 | Menu detail: timeline children, square bullets, clean dark text                                                                                                                                                                                                                                                                                                   | F1          | ✅     |
| 2026-10-02 | Title, subtitle, breadcrumbs and buttons in the header; footer                                                                                                                                                                                                                                                                                                    | F1 / F2     | ✅     |
| 2026-10-02 | Keep the table / grid / filters flow unchanged                                                                                                                                                                                                                                                                                                                    | F2          | ✅     |
| 2026-10-02 | "Wow" sign-in screen                                                                                                                                                                                                                                                                                                                                              | F3          | ✅     |
| 2026-10-02 | Test accounts in the README; realistic test people                                                                                                                                                                                                                                                                                                                | F3          | ✅     |
| 2026-10-02 | Global positioning (not one country); international sample data                                                                                                                                                                                                                                                                                                   | F3 / all    | ✅     |
| 2026-10-02 | Show 5+ supported databases or built-in encrypted storage                                                                                                                                                                                                                                                                                                         | F3 / F12    | ✅     |
| 2026-10-02 | Separate progress file with every task per phase                                                                                                                                                                                                                                                                                                                  | PROGRESS.md | ✅     |
| 2026-10-02 | Social providers on the first signup; more methods enabled later per workspace                                                                                                                                                                                                                                                                                    | F3 / F12    | 🟡     |
| 2026-10-02 | Provider buttons on one row with a "Sign up with" caption                                                                                                                                                                                                                                                                                                         | F3          | ✅     |
| 2026-10-02 | Settings as its own detailed phase; Dashboard after everything, just before RBAC                                                                                                                                                                                                                                                                                  | F12 / F18   | ✅     |
| 2026-10-02 | Audit trail early (its own phase after sign-in), not last                                                                                                                                                                                                                                                                                                         | F4          | ✅     |
| 2026-10-02 | Use "Email address" (not "Work email") so any email provider is welcome                                                                                                                                                                                                                                                                                           | F3          | ✅     |
| 2026-10-02 | Sidebar: chevron and count badges on the right; counts on items that have them                                                                                                                                                                                                                                                                                    | F1          | ✅     |
| 2026-10-02 | Don't expire sessions so soon — at least 1 hour when idle                                                                                                                                                                                                                                                                                                         | F3 / F12    | ✅     |
| 2026-10-02 | Loading feedback everywhere: page loading, progress, skeletons, top bar, busy buttons                                                                                                                                                                                                                                                                             | F2 / all    | ✅     |
| 2026-10-02 | In-page loading bar (left-to-right sweep) when moving between pages, not only on reload                                                                                                                                                                                                                                                                           | F2 / all    | ✅     |
| 2026-10-02 | Design images are style, not features — follow the look exactly, don’t copy widgets                                                                                                                                                                                                                                                                               | all         | ✅     |
| 2026-10-02 | New form: richer Blank tab (live mini preview + what you get), form details card, Continue button under every tab                                                                                                                                                                                                                                                 | F6          | ✅     |
| 2026-10-02 | Folders in the sidebar with counts, folder pages and an all-folders view with statistics                                                                                                                                                                                                                                                                          | F10         | ⬜     |
| 2026-10-02 | Builder feedback (18 points): inline rename, try fields on the canvas, read-only keys with suffix, help as info icon, smaller radius, tighter spacing, label position, Nuxt UI dates, saved fields + lists, file-type picker, thumbnails, option numbers in formulas, clearer + complete logic, read-only / disabled with required guards, phone preview stacking | F7          | ✅     |
| 2026-10-02 | Form themes: header, footer, body, images and text design carried on shared forms; default theme when none is chosen                                                                                                                                                                                                                                              | F8          | ⬜     |
| 2026-10-02 | Builder canvas uses the full width; full-screen toggle with fields · canvas · settings and visible save status                                                                                                                                                                                                                                                    | F7          | ✅     |
| 2026-10-02 | Lists later: static, large / autocomplete, dynamic sources, cascading levels (State → City → Location) and auto-fill of other fields — plan in docs/OPTION-LISTS.md                                                                                                                                                                                               | F13         | ⬜     |
| 2026-10-02 | Drop indicator while dragging fields (dashed placeholder + label)                                                                                                                                                                                                                                                                                                 | F7          | ✅     |
| 2026-10-02 | Rich text field (real editor)                                                                                                                                                                                                                                                                                                                                     | F7          | ✅     |
| 2026-10-02 | New fields default to ½ width; required messages use the field label                                                                                                                                                                                                                                                                                              | F7          | ✅     |
| 2026-10-02 | Rich text: headings 1–6, paragraph, text alignment, code block                                                                                                                                                                                                                                                                                                    | F7          | ✅     |
| 2026-10-02 | Layout blocks: nicer section, inline paragraph editing, image upload + resize, divider options                                                                                                                                                                                                                                                                    | F7          | ✅     |

---

## Progress log

| Date       | Phase | What happened                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-02 | F0    | Foundation: config, 20 languages, mock API with real encryption, tooling. Checked phone / desktop, light / dark, Arabic, keyboard.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F0    | Access matrix verified on every host; shared host resolver with tests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F1    | App shell built, then rebuilt to match the design exactly (rail + menu, header, monochrome).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-10-02 | F1    | Flags, breadcrumbs in the header, Manrope font, menu timeline / square bullets / dark text.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-10-02 | F2    | Core plumbing: secure API client, error handling in 20 languages, DataView live on the mock, confirm dialog, formatters.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-10-02 | F2    | Header carries title / subtitle / crumbs / buttons; footer added; DataView flow approved.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-10-02 | F3    | Auth built end to end; mock flow verified (codes, tokens, refresh rotation, reuse revokes).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-10-02 | F3    | Sign-in redesigned; full flow verified in the browser (sign in → code → portal → log out) on desktop, phone and dark.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F3    | Global positioning on sign-in; international sample data; 5+ databases or built-in encrypted storage; realistic test people; this progress file.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F3    | Signup offers Google, Microsoft, Apple, Facebook (manage.*) plus email; new workspaces start with email sign-in, more methods enabled in Settings (F12). Provider callback waits on the backend.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F3    | Provider buttons on one row with a "Sign up with / Sign in with" caption: logo + name for 2, logo only (tooltip) for 3–4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-10-02 | F3    | "Work email" → "Email address" everywhere, neutral placeholder name@example.com, no "work email" wording (any organisation, any email provider).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F3    | Phase done: RTL, keyboard-only and phone passes on every auth screen (logical tab order, nothing hidden focusable, no overflow at 375 px).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-10-02 | F4    | Audit trail moved up to its own phase right after sign-in (owner); phases renumbered, RBAC is now F19 (last).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-10-02 | F4    | Audit trail built: event catalogue, mock store with international history, sign-in events recorded live, /audit page (table / grid, filters, shareable detail, export with progress + one-time download), activity timeline, admins only (role on the session user). Checked desktop / phone, light / dark, Arabic RTL, member access.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F1    | Sidebar polish (owner): chevrons moved to the right edge, count badges on the right (forms by status, new responses), menu column 16 → 17.5 rem so labels fit.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-10-02 | F5    | Onboarding wizard: 5 optional steps with live preview, server-side progress, pre-signed logo upload with progress, regional defaults from device and country, invites, starter templates; every saved step in the audit trail. Checked desktop / phone, light / dark, Arabic RTL.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 2026-10-02 | F3    | Sessions: 60-minute sliding idle timeout (owner); mock sessions survive dev reloads (`.data/mock/`); unknown access token → silent refresh instead of sign-out. Verified: signed in → mock reloaded → still signed in.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F2    | Loading feedback (owner): branded first-load screen, top progress bar on every API call (not only navigation), busy rows for menu actions, rule 5 rewritten as a checklist and added to the definition of done.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-10-02 | F6    | Forms lifecycle: new (blank / template / import), inline rename, duplicate, move, tags, folders, unpublish / close / reopen / archive / unarchive, Trash with restore and permanent delete, bulk, row_version conflicts, busy rows, form overview with activity. Checked desktop / phone, Arabic RTL; all actions in the audit trail.                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F2    | In-app navigation progress (owner): one activity counter for navigation + API calls drives the top bar and a new sweeping bar under each page header; starts on click, runs until the new page's data has arrived.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F7    | Builder milestone 1–2: field catalogue (34 types) + registry, renderer for every type, three-pane builder (palette · real form on a page card · inspector), drag and drop (palette → canvas, within / between rows), keyboard moves, multi-select, undo / redo, delete with undo, autosave with conflict pause, publish with checks + change summary, live preview with device sizes, phone / tablet layout; segmented controls now match the design.                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | Milestone 3 — phase done: logic editor (`/forms/[id]/logic`: rules with plain-language summaries, All / Any, show / hide / require / jump, calculations), versions page (timeline, view, compare, restore, discard), shared builder frame with Build / Logic / Versions switch (saves before switching), collapsible sections, lazy dialogs; 20 languages; 87 tests. Stopped for review.                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-10-02 | F6    | New form page polish (owner): Blank tab shows a live mini preview of the empty form and what a blank form offers; name + folder sit in a "Form details" card whose footer has **Continue** (same as Create form, closer to the fields) on Blank, Template and Import.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | Owner feedback round (18 points) done: canvas fields work for trying out, double-click / F2 rename, Label wording, read-only field keys with id suffix (formulas follow), help text as info popover, smaller form radius, tighter spacing, container-query columns (phone preview stacks), form-wide label position (New form + Form settings), all dates Nuxt UI (UInputDate / UInputTime / UCalendar, ranges too), read-only / disabled fields with required guards everywhere, grouped searchable file-type picker + drop checks + thumbnail grid, option numbers + if() / comparisons / functions in formulas, logic: all operators and 12 actions, IF / THEN steps, starters, conflict checks; Saved fields + Lists (library API, palette tabs, list editor). 20 languages. |
| 2026-10-02 | F7    | Phones / tablets: field list easy to find — "Add field" next to the page tabs and a dashed "+ Add field" under the last field (all sizes; laptops focus the palette search); the bottom bar now sticks to the content instead of covering the footer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | "Beside the field" now holds for half-width (and narrower) fields too: decided by the form's width (`@container/form`), not each cell; phone-width forms still stack.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | "Beside the field" sits right next to the input: the label is as wide as its text (up to 45 %, then wraps), the input follows after a small gap and takes the rest — no column gap.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | "Beside the field" is uniform: one label width per form (from its longest label, max 22 characters / 30 % — the input gets most of the row), labels end-aligned against their input, so every input starts on the same line and has the same width.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | Canvas no longer boxed (fills the middle, less padding); full-screen mode for Build / Logic / Versions with save status in a slim bar.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F7    | Preview: Desktop fills the preview panel (no inner box; panel keeps its size); Tablet and Phone keep their device widths.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-10-02 | F7    | Drag and drop shows where a field will land: dashed, tinted placeholder labelled "Drop here — new row" (between rows) or "… beside" (in a row, half width), and a dashed outline around the page while dragging.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F7    | Rich text field done with Nuxt UI's editor: Basic / Full toolbar (marks, lists, quote, link, headings, alignment, code, clear, undo / redo), Markdown answers, locked states, character count.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-10-02 | F7    | New fields start at ½ width (layout blocks full width), width still adjustable; required errors name the field ("First name is required.").                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-10-02 | F7    | "+ Add field" under the canvas is a compact button at the end of the row, so it no longer covers the drop area.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-10-02 | F7    | Yes / No: switch and label on one line (switch first, label right after, centred; click the label to toggle); in "beside" forms it lines up with the other inputs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F7    | Rich text: standard line height (20 px) and a small 2 px gap after Enter, so new paragraphs read like normal lines.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | Rich text Full toolbar (now the default): Text style menu (Paragraph, Heading 1–6), inline code, code block. Text alignment needs the TipTap text-align extension (not bundled with Nuxt UI) and HTML storage — awaiting owner decision.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-10-02 | F7    | Rich text alignment (left / centre / right / justify) with `@tiptap/extension-text-align` (owner-approved); answers now stored as HTML, sanitised server-side; max length counts visible text.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-10-02 | F7    | Layout blocks upgraded: section heading block with placeholders and inline title / description editing; paragraph written on the canvas (bubble toolbar, HTML, shown read-only to respondents); image upload (drop / browse, progress, 5 MB, safe SVG) or link, drag / keyboard resize, presets, alignment, caption, link, rounded, alt-text prompt; divider style and spacing.                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-10-02 | F7    | Image "Fill": spans the whole field; optional height (small / medium / large) crops it like a banner.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

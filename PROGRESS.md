# Formalie Portal — Progress

The single place to see **what we are building, what is done and what is next**. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-04 · **Current phase:** F10 — Renderer, preview, share, embed (F9 reviewed by the owner)

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
| F8    | Designer (themes)                                 | ✅     | 100% |
| F9    | Templates gallery                                 | ✅     | 100% |
| F10   | Renderer, preview, share, embed, short links, SEO | 🟡     | ~45% |
| F11   | Responses                                         | ⬜     | 0%   |
| F12   | Data sources & databases                          | 🟡     | ~3%  |
| F13   | API service & integrations                        | 🟡     | ~2%  |
| F14   | Settings                                          | ⬜     | 0%   |
| F15   | Option sets & payments                            | ⬜     | 0%   |
| F16   | Profile                                           | ⬜     | 0%   |
| F17   | Users                                             | ⬜     | 0%   |
| F18   | Analytics                                         | ⬜     | 0%   |
| F19   | AI assistant                                      | 🟡     | ~2%  |
| F20   | Live collaboration (optional)                     | ⬜     | 0%   |
| F21   | Dashboard                                         | ⬜     | 0%   |
| F22   | Roles & access (last)                             | ⬜     | 0%   |
| F23   | Platform admin (super admin, Formalie team)       | ⬜     | 0%   |

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
- ✅ Rendering: portal client-side, public form pages and `/s/**` server-side (paths now `/{formKey}/fill` · `/embed`, 2026-10-03)
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

- ✅ DataView: table and grid, search, filters (area, result, person, country), date range, sort, server pagination; organisation filter arrives with several organisations per workspace (F14)
- ✅ Event detail slide-over: shareable link `/audit?event=<id>`; result + reason, who / when / where / device, item, before → after changes side by side, technical details, request id with copy, related activity
- ✅ Export to Excel / CSV with progress; search, filters and dates carried into the export (mock writes CSV; real .xlsx from the backend)
- ✅ Links from an event to its item (forms, settings, integrations); user pages follow in F17
- ✅ "Audit trail" in the sidebar (SYSTEM), breadcrumbs, header title / subtitle / export button
- ✅ Empty, loading and error states; phone layout (cards) and keyboard access

### Reusable activity

- ✅ `AuditTimeline` component (latest events for one resource) to drop into forms, responses, users and settings pages as they are built
- ✅ Security view filter preset (failed / blocked sign-ins, revoked sessions) used later by Settings → Security

### Access

- ✅ Workspace admins only for now; a proper `audit.read` permission arrives with Roles & access (F22)

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
- ⬜ Workspace logo in the rail and on the sign-in page (the public profile already returns `logo_url` and brand colour) → F14 Branding
- ⏸ Real invitation emails (F17 Users), real object storage

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
- ✅ Reusable option lists: palette **Lists** tab, "Fill from a list" / "Save as list" in the options editor (full option-set management page stays in F15)
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

## F8 — Designer (themes) ✅

Owner-tested 2026-10-03: all good. Open items below (fonts, custom CSS, workspace default theme) are picked up with Settings / billing and the requests log.

**Goal:** organisations design their form pages as they want.

- ✅ Design view (`/forms/[id]/design`) next to Build / Logic / Versions: controls on the left (collapsible groups), live form page on the right; phones / tablets: preview full width, controls in a drawer / slide-over
- ✅ Live preview with desktop / tablet / phone toggle, and questions / thank-you page
- ✅ Starting points: workspace default, minimal, soft, bold, dark, elegant (replace with confirm, undo); reset to workspace default
- ✅ Layout (card, plain, split with image, full width)
- ✅ Background (colour, gradient with angle, image with darkening overlay)
- ✅ Form container (width, spacing, corners, shadow, border, background)
- ✅ Typography (font: clean sans, device, serif, rounded, mono; text size; heading weight)
- ✅ Colours (accent, text, secondary text, input background / border, errors) with colour picker, hex box and contrast warning; button text colour picked automatically
- ✅ Inputs (outline / soft / underline, size, corners) and buttons (solid / outline / soft, corners, full width)
- ✅ Header / cover (cover image + height, logo — workspace or uploaded, form name, intro text, alignment), thank-you page (tick icon; title / message from form settings)
- ✅ Footer (text, up to 6 https links, logo, alignment) (owner request 2026-10-02)
- ✅ Default theme: a form without a design uses the workspace default (brand colour + logo from onboarding)
- ✅ Applied as CSS variables on the renderer only (Nuxt UI controls follow; portal untouched); theme stored on the form schema (versioned with publishing); builder Preview and Versions preview show the themed page
- ✅ Save as theme (new or update), apply a saved theme in the designer; themes library page (Resources → Themes): Table / Grid, search, rename, duplicate, delete with usage count; audited (`forms.theme_*`) — milestone 2
- ✅ New global and IT field types (owner request): full name (title / middle optional), percentage, duration, consent with terms link, language, time zone, currency (all from `Intl`, in the respondent's language), IP address (any / IPv4 / IPv6), domain, MAC address, colour, IBAN (checksum), SWIFT / BIC — new palette group "Technical & IDs", validated by the shared validator
- ✅ Six more starting points with different structures (owner request): Banner (gradient header band), Ribbon (colour header band), Grounded (footer bar), Side panel (colour panel carrying logo / title), Aurora (gradient side panel), Corporate (header band + footer bar); new tokens `header.band`, `footer.style`, `split.panel`, all editable in the designer
- ✅ Owner follow-ups 2026-10-03: "Folder" on New form explained in place (workspace folders, not template categories); typing masks for IP address (IPv4 dots, IPv6 groups) and MAC address (colon pairs in capitals; dash / dot notation kept); **field access** (Everyone · Departments · Roles · People, all or selected; restricted fields can't be required; lock icon on the field; answers later shown only to the same people — F11)
- ⬜ More fonts (self-hosted web fonts — needs a font package, ask first)
- ⬜ Custom CSS (paid plans, sanitised) — with billing

---

## F9 — Templates gallery ✅

**Goal:** nobody starts from an empty page — a catalogue full of beautiful, ready templates (fields, pages, logic, calculations **and a design**) that people pick, adapt and publish; plus their own workspace templates. Comes before the renderer (owner, 2026-10-02). Stays in the **Forms area** (Resources → Templates) — no own rail icon: templates are a way to start a form.

**Approach (decided 2026-10-03, see 03-DECISIONS → 67):** framework first, proven on two full categories, then the remaining categories in batches — all inside F9, each batch committed and reviewable. F9 closes only when every listed template exists, in all 20 languages.

### Milestone 1 — Framework + Business & Customer + HR & Workplace

- ✅ Template model: key, category, icon, name / description / tags (i18n), schema (pages, fields, logic, calculations, settings), theme, estimated time, field / page counts, "includes calculations / logic" flags, version; system vs workspace templates
- ✅ Authoring kit (`shared/templates/`): one small definition per template (fields by type, options, validation, logic, formulas, theme), validated against the form schema in tests — every template must pass the publish checks
- ✅ **Gallery** (`/templates`) in DataView: Grid of themed cards (mini preview in the template's own design, category, fields, time, "Calculations" / "Logic" badges, uses) and Table (name, category, fields, uses, forms, responses, updated); category chips with counts, search, sort (popular, newest, name, most used), filters (category, has calculations, field count, system / workspace)
- ✅ **Template page** (`/templates/[key]`): live themed preview (desktop / tablet / phone, questions / thank-you), what's included (pages, fields, logic rules, calculations with their formulas in plain words, design), statistics (forms created, responses collected, last used), and **all forms created from it** (DataView filtered by template)
- ✅ **Use template** → name + folder → new form opened in the builder; everything editable (fields, logic, design) before publishing; the form remembers its template
- ✅ New form → "From a template" tab reads the catalogue (search, category, design previews); onboarding starters use the catalogue where built (event registration and incident report follow with their categories in milestone 2)
- ✅ Workspace templates: save any form as a template (forms list row action + form overview menu; builder menu ⬜ with the builder header rework), edit name / description / category, duplicate, delete with confirm; audited (`forms.template_*`)
- ✅ Formula additions for templates: `avg()`, `count()`, `days(from, to)`, text results (e.g. risk level "High")
- ✅ Mock + contract: `/templates` (list with stats, get, create from form, update, duplicate, delete), `/templates/{key}/forms`, `/forms/from-template`; error codes
- ✅ Business & Customer (10): Customer Feedback · Customer Satisfaction (CSAT / NPS — NPS group calculated) · Product Review · Contact / Inquiry · Quote / Estimate Request (line totals, tax, total) · Order Form (line totals, subtotal, tax, total) · Complaint / Dispute · Service Request · Lead Capture / Newsletter Signup · Return / Refund Request (refund amount)
- ✅ HR & Workplace (10): Job Application · Employee Onboarding · Exit Interview · Leave / Time-Off Request (days requested) · Performance Review / Appraisal (average score, rating band) · Employee Engagement Survey (engagement index) · Expense Reimbursement (claim total) · Timesheet (hours, overtime) · Training Feedback (average) · Reference Check

### Milestone 1 follow-ups (owner review 2026-10-03)

- ✅ Template page: "What's included" as tiles; calculations as code snippets (coloured field references, functions, text, numbers; copy button; team-only marked); usage + the latest forms made from the template in a slider with "View all" (forms list → Template filter) — moved from below the preview to the side
- ✅ Table view: small even thumbnails (64 × 40, small radius, shapes only)
- ✅ Sidebar: Templates (new icon) and Themes (palette icon) open submenus with the 6 most recent + "All …"; Responses opens status submenus (All, New, Reviewed, Approved, Rejected, Exports) with counts
- ✅ Form overview redesigned: KPI tiles (responses, completion with views → starts, median time, last response), 30-day response chart with hover / keyboard tooltips, share links (fill + embed), structure tiles linked to Build / Logic / Design, versions timeline, details with the template it came from, activity
- ✅ Field access: Departments and Roles open with the list to pick from ("All …" is a switch, off by default)

### Owner review fixes (2026-10-03)

- ✅ File uploads: chosen files sit inside the drop zone (compact grid), "{n} of {max}" + "Add more"; wrong type, too large and over the file limit are taken out again with a notification and a message under the field; remove buttons always visible (outline, round)
- ✅ Errors clear while typing everywhere: duration hours / minutes now report every keystroke (the stepper only reported on leaving the field)
- ✅ Gallery cards: page-shaped thumbnails with a fixed proportion (no stretching at any card width)
- ✅ Folders: create / rename / delete under Forms → Folders (also created from "Move to folder"); a folder that still holds forms can't be deleted (`FRM-FORM-1013`) — its forms are one click away

### Milestone 2 — Health & Safety · Events & Bookings · Hospitality ✅

- ✅ **Themes catalogue** (owner, 2026-10-03): the themes library shows three kinds — **System** (Formalie's designs: the starting points and every category design), **Saved** (saved from a form's design) and **Created** (made from scratch in a theme editor: the designer controls on a sample form, no form needed); filters and badges per kind; system themes can be duplicated, not changed; Themes submenu keeps the 6 most recent

- ✅ Health & Safety (8): Risk Assessment (likelihood × severity = risk score, risk level, action required when high) · Incident / Accident Report (severity score) · Near-Miss Report (potential severity) · Safety Inspection Checklist (compliance %) · Patient Intake · Medical History · Health Screening / Declaration (flag when any "yes") · Consent Form — controls only, no compliance claims
- ✅ Events & Bookings (7): Event Registration (ticket total) · RSVP (party size) · Appointment Booking · Venue / Room Reservation (hours × rate) · Volunteer Signup · Speaker / Sponsor Application · Post-Event Feedback (average)
- ✅ Hospitality (8): Guest Registration · Hotel Booking Request (nights × rate) · Guest Feedback (average) · Service Evaluation (score) · Special Requirements · Event Catering Request (guests × price per head) · Restaurant Reservation Request · Hospitality Complaint

### Milestone 2 follow-ups (2026-10-03)

- ✅ Form overview KPI cards match the design (dark title, ↗ link, icon · number · trend · caption)
- ✅ QR code for the form link (`uqr`, owner-approved): branded card (organisation name + logo / initials in the centre, form name, Formalie footer; Formalie branding without own subdomain) or plain; colours: form, brand, black, presets, any colour; PNG sizes and SVG
- ✅ Form language: main language of the form in Form settings (20 languages)
- ✅ Themes clickable everywhere: workspace themes open the editor, Formalie themes open read-only with "Duplicate to edit"

### Milestone 3 — Education · Operations & IT · Finance & Legal ✅

- ✅ Education (7): Student Enrolment / Admission · Course Evaluation (average) · Quiz / Assessment (score from answers, pass / fail) · Scholarship Application (eligibility score) · Parent Consent / Permission Slip · Attendance Register (present count) · Academic Survey
- ✅ Operations & IT (9): IT Support Ticket (priority from impact × urgency) · Change Request (risk score) · Asset Check-out / Inventory · Maintenance / Work Order · Purchase Requisition (line totals, total) · Vendor / Supplier Registration · Site / Field Inspection Report (pass rate) · Delivery Confirmation / Proof of Delivery · Quality Control Checklist (pass rate, result)
- ✅ Finance & Legal (5): Loan / Credit Application (debt-to-income ratio, flat-rate monthly payment estimate — labelled as an estimate) · KYC / Identity Verification · Invoice Submission (subtotal, tax, total) · Insurance Claim (claim total) · NDA / Agreement Sign-off

### Milestone 4 — Community & Other · Real Estate · Sales ✅

- ✅ Community & Other (4): Membership Application (fee) · Donation Form (gift + optional fee cover) · Petition · Poll / Voting Ballot
- ✅ Real Estate (8): Property Viewing Request · Tenant Application (income-to-rent ratio) · Rental Application (income-to-rent ratio) · Property Inspection (condition score) · Maintenance Request · Property Information · Landlord Information · Tenant Feedback (average)
- ✅ Sales (8): Lead Capture · Quote Request (total) · Sales Qualification (qualification score, e.g. budget / authority / need / timing) · Product Demo Request · Customer Discovery · Proposal Request · Order Request (total) · Sales Follow-up

### Milestone 5 — Languages, polish, review

- ✅ **Categories first, own templates apart** (owner, 2026-10-03, decision 78): `/templates` lists Formalie's categories (Grid / Table: templates, with calculations / logic, forms made, responses, last used); a category opens its templates (`/templates/category/{key}`); the workspace's own templates under "Your templates" (`/templates/mine`); menu: six most used categories, All categories, Your templates; a template page links back to its category

- ✅ Template content (labels, options, help, page titles, consent / paragraph text, thank-you messages, text results) in all 20 languages — one dictionary per language (`shared/templates/messages/<code>.json`, decision 77); preview and new forms open in the person's language; keys, values, scores, logic and formulas unchanged
- ✅ Phone / desktop, dark, Arabic RTL checked on the categories page, a category, Your templates and a template in Arabic; skeletons from DataView; empty state for Your templates offers next steps; keyboard: cards and rows are links, actions are buttons
- ✅ End-of-phase review with the owner (2026-10-03: "all is good")

Total at launch: **84 templates in 11 categories** (a few names appear in two categories on purpose, framed for each — e.g. Lead Capture, Quote Request, Order, Maintenance). More later (owner: "just the tip of the iceberg"); the AI assistant (F19) can generate more.

---

## F10 — Renderer, preview, share, embed, short links, SEO 🟡

**Plan (2026-10-03, milestones):** **M1** public page core — public key per form, `/{formKey}/fill` + `/embed` server-rendered with SEO, `forms.*` host, secure server-side fetch, not found / not published / closed states, submit with one response per fill-in session (`Idempotency-Key`), thank-you or redirect, respondent language (`?lang`, browser language). **M2** save & resume, file uploads with progress, spam protection, embed auto-resize. **M3** Share card: access (password, invite-only, organisation-only, expiry, response limit, schedule), custom link, short links `/s/{code}`, embed code builder, SEO settings with link-card preview, preview page with device frames. **M4** form translations (questions in several languages + switcher), polish, review.

### Renderer

- ✅ One renderer for preview, public page and embed (submit hook, same rules as the API)
- ✅ Public form links (decided 2026-10-03; built M1 with a 10-character `public_key` per form): `https://{forms | subdomain}.formalie.com/{formKey}/fill` and `…/{formKey}/embed` — `forms.formalie.dev` / `forms.formalie.com` for workspaces without their own subdomain; `{formKey}` is the form's short public key (custom slug optional); helper `shared/utils/urls/public.ts`
- ✅ Public page server-rendered with SEO (title, description, image, canonical, noindex); `forms.*` host served without a workspace (tenant from the form key)
- ✅ Secure server-side fetch for server-rendered pages (internal route + server-only `NUXT_INTERNAL_TOKEN`)
- 🟡 Closed / expired / not found / password-protected / response-limit states — ✅ not found (404), not published, closed, **expired (410) and not-open-yet** (availability dates, owner 2026-10-03), load error; password / limit come with the Share settings (M3)
- ✅ Multi-page with progress, **save and resume** (decision 87): autosave to a server draft, "Save and continue later" emails a 30-day resume link, the link restores answers and page, submitting closes the draft
- ✅ **File uploads** (decision 88): straight to storage through short-lived upload links with progress per file; answers keep references (drafts too); type / size / count / real-picture / no-program checks on both sides; files attached to one response, never public
- ✅ **Help guide** (owner, 2026-10-03, decision 86): Form settings → Help guide (off by default, rich editor in a window); a floating "?" on the form opens it in a chat-style panel
- ✅ **Accent header** (decision 86): quote-like header style; Events & bookings and Operations & IT designs use it instead of the side panel
- ✅ **Recognising respondents** (owner, 2026-10-03, decision 85): the respondent's own email (suggested, never someone else's) — email only (ID option removed, owner); same → refused, near match → "different person?" + flagged possible duplicate; optional email verification with a code; masked hints only
- ✅ **Duplicate protection** (owner, 2026-10-03, decision 84): per session, per browser (with "for someone else" after confirming), exact same answers never twice, optional one response per answer (e.g. email); thank-you page: Fill in another · Close this page
- ✅ **Availability** (decision 84): open from / open until per form, set from the list menu or the overview; badge in table and grid
- ✅ **No duplicate submissions** (owner question 2026-10-03, see 03-DECISIONS → 68): the Submit button is busy and disabled from the first click; every fill-in session has its own submission id sent as an `Idempotency-Key` — the server keeps the first response for that key and answers repeats (double click, retry after a dropped connection, back button) with the same response id instead of a second response; a finished session can't submit again; optional "one response per person" (signed-in respondents by account, others by a signed cookie + email if the form asks for it); rate limits per form / IP
- ✅ **Spam protection** (decision 89): invisible proof-of-work challenge (no third-party captcha), hidden trap field, submission limits per address
- ⬜ F11: show "Possible duplicate" on responses with a link to the earlier one; merge / reject
- ✅ Thank-you page or redirect
- ✅ **In-app browser** (owner, 2026-10-03, decision 83): website, Terms and Data Privacy Policy open in a branded window over the form; answers stay
- ✅ **Page frame** (owner, 2026-10-03, decision 82): Designer → Page with four styles — Branded · Spotlight · Side panel · Minimal — tone, website link, quick facts; shown on the public link, the designer and Preview (not in embeds)
- ⬜ Preview page with device frames
- ✅ **Changing the form language translates its text** in the same step (owner, 2026-10-04, decision 91 — no second button): template text in all 20 languages, the creator’s own text kept (count shown), one undo
- ⬜ **Form languages** (owner, 2026-10-03, see 03-DECISIONS → 73): the form opens in the respondent's browser language when the form offers it, otherwise its main language; `?lang=xx` forces one (shareable per-language links, embeds and QR codes); a language switcher when a form has several; translated questions / options / help / messages per language; the language is saved with each response; buttons, messages, dates, numbers and right-to-left follow it
- ✅ **Embed code** (decision 90): the Share card offers the ready `<iframe>` code — auto height (recommended) or fixed height — instead of a bare embed address; embed pages can be framed by other websites

### Share

- 🟡 Custom link (slug availability), short link, QR code (PNG / SVG), copy buttons — ✅ QR code (form colour or black, PNG 512–2048 px / SVG) and copy buttons on the form overview (2026-10-03)
- ⬜ Access: public, password, invite-only, organisation-only; expiry, response limit, schedule
- ⬜ People access: edit / view / responses
- 🟡 Embed: iframe snippet with auto-resize, size options, allowed domains, live preview — ✅ snippet with auto / fixed height (M2); allowed domains + live preview with the Share settings (M3)
- ⬜ SEO settings with link-card preview
- ⬜ Short link redirect `/s/[code]`

---

## F11 — Responses ⬜

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

## F12 — Data sources & databases ⬜

**Goal:** organisations connect their own databases, send form data to them, and work with that data from the portal — browse it, query it and manage it — safely, with every action audited (owner request 2026-10-02). Comes after Responses (there is data to send) and before Option sets (dynamic lists read from these connections, F15e). Launch engines: MySQL, MariaDB, Oracle, PostgreSQL, SQL Server (`shared/utils/integrations/databases.ts`); built-in encrypted storage stays the default.

### 1. Connections (Integrations → Data sources)

- ⬜ Data sources page in DataView (Table / Grid): engine logo, name, host, database, access mode, status (connected · failing · disabled), last checked, used by N forms; filters, search, sort
- ⬜ Add connection (step by step): engine (default port filled in) → host, port, database / service name → username + password → security (SSL / TLS mode, CA certificate upload, optional SSH tunnel: host, user, key) → access (read only / read + write, allowed schemas) → name and test
- ⬜ Test connection with live progress (reach host → sign in → read schema → write check when read + write) and a clear, actionable error per step (`FRM-DEST-*`)
- ⬜ Credentials are write-only: never shown or returned again, encrypted at rest on the server, sent in the encrypted envelope; "Change password" and "last changed"; Formalie's outgoing IP addresses shown to allow-list
- ⬜ Edit, disable / enable, duplicate, delete (confirm; warns with the forms that send to it); health check every few minutes with status history
- ⬜ Audit: `datasource.created · updated · tested · disabled · deleted · credentials_changed`

### 2. Sending form data (destinations)

- ⬜ Per form (form settings → Destination): built-in storage (default) or one of the connections; several destinations allowed
- ⬜ Table: choose an existing table, or create one from the form — generated table preview (column names from field keys, types from field types), confirm, then create
- ⬜ Field → column mapping: auto-match by key, type-mismatch warnings, required-column check, extra columns (response id, submitted at, form version, language, respondent details), multi-value fields (JSON / joined / child table), files as secure links
- ⬜ Write mode: insert, or update-or-insert on a key column
- ⬜ Delivery runs in the background: queued per response, retries with back-off, status per response (sent · pending · failed), error log with retry / retry all, pause / resume
- ⬜ Backfill: send existing responses (date range) with a progress bar
- ⬜ A form gains a field → offer "Add column" with a preview; a removed field is never dropped from the table automatically

### 3. Database explorer

- ⬜ Explorer page per connection: tree of schemas → tables / views → columns (type, nullable, default, primary / foreign keys, indexes) with row counts; search tables and columns; keyboard navigation of the tree
- ⬜ Table data tab: rows with server-side paging, sort, filters per column type, search, column picker, Table / Grid (record cards), copy cell / row, row detail slide-over
- ⬜ Structure tab: columns, keys, indexes, relations and the table definition (read only)
- ⬜ Export a table or the filtered rows to CSV / XLSX with a progress bar
- ⬜ Skeletons that mirror the tree and the grid; empty / error states with retry and "check connection"

### 4. Query editor

- ⬜ SQL editor with syntax highlighting, table / column completion from the explorer, format query, multiple tabs — **needs a code editor package (e.g. CodeMirror 6) — ask before adding**
- ⬜ Run all or the selection (Ctrl / ⌘ + Enter), cancel a running query, time limit and row limit, results grid with paging, run time, rows affected, errors pointing at the line
- ⬜ Read-only by default: on read-only connections only reading statements run; on read + write connections a changing statement shows what it will do and needs a confirm; structure changes (create / alter / drop) blocked unless the connection allows them
- ⬜ Parameters (`:name` → input boxes), query history, saved queries (personal or shared with the workspace), export results (CSV / XLSX)
- ⬜ Use a saved read query as a dynamic option list source (F15e) and, later, on the dashboard (F21)

### 5. Other database operations

- ⬜ Insert, edit and delete rows from the table view (form generated from the columns, type-checked, confirm on delete; read + write connections only)
- ⬜ Create a table from a form; add columns for new fields (preview + confirm)
- ⬜ Import CSV / XLSX into a table: column mapping, preview, validation, progress, error report
- ⬜ Per-connection activity: delivery queue, failures, throughput, recent queries
- ⬜ Scheduled exports and saved-query snapshots (later)

### 6. Safety (enforced by the backend, visible in the UI)

- ⬜ Queries and data changes run only on the server, through the connection's pool, with statement time-outs and row caps — never from the browser
- ⬜ Every query, row change, import and export is recorded in the audit trail (who, connection, statement, rows affected, duration)
- ⬜ Permissions per role (view explorer · run read queries · run changing queries · manage connections · send form data) — wired up in F22; until then admins only
- ⬜ Rate limits; no credentials or result data in logs; results never stored in the browser
- ⬜ Clear wording: we provide controls (encryption, audit, least privilege), never certifications

### 7. Navigation, API and docs

- ✅ Own rail area (owner, 2026-10-02): Data sources icon under the workspace button, with its own menu — Overview · Connections · Database explorer · Query editor · Saved queries · Destinations · Imports & exports · Activity; placeholder pages in place (`/data-sources/**`), old `/integrations/destinations` redirects; Integrations keeps Webhooks · API keys
- ⬜ Mock first, then API: `/datasources` (CRUD, test, health, change credentials) · `/datasources/{id}/schema` · `/datasources/{id}/tables/{table}/rows` (list, insert, update, delete, import, export) · `/datasources/{id}/query` (+ cancel) · `/saved-queries` · `/forms/{id}/destinations` (+ mapping, create table, backfill, deliveries, retry); error codes `FRM-DEST-*`; contract updated

---

## F13 — API service & integrations 🟡

**Goal:** turn any form into an API so organisations collect data from every side — **links, embeds and API** — all landing in the same storage / destinations (owner request 2026-10-02: "this option is gold"). An entire system of its own: its own rail area and menu, its own analytics, and later its own dashboard (F21). In the backend the API service runs as its own service, separate from form operations.

### Addresses (decided 2026-10-03, see 03-DECISIONS → 61)

- Base URL: development `https://api.formalie.dev/` · production `https://api.formalie.com/`
- Endpoint: `https://api.formalie.dev/{apiKey}/{endpoint}` (+ `/{recordId}` for GET one · PUT · DELETE), e.g. `https://api.formalie.dev/k7Qm2xP9aZ/register-account`
- `apiKey` = a short random public handle per organisation (10 letters / digits) — **not** the tenant or organisation id and **not** encrypted: it only routes the call; the token, headers and access rules decide who may call. Rotatable (old key keeps working for a grace period).
- Endpoint names: lower-case words with hyphens, 3–64 characters, unique per organisation
- Helper: `shared/utils/urls/public.ts` (`apiEndpointUrl`, `API_KEY_PATTERN`, `ENDPOINT_PATTERN`, `API_METHODS`)

### 1. Area and navigation

- ✅ Own rail area under Data sources with its own menu: Overview · Services · Endpoints · Tokens & headers · Access rules · Request logs · Analytics · Docs & testing — placeholder pages (`/api-service/**`), overview shows the three channels (link · embed · API) and an example endpoint

### 2. Services (containers)

- ⬜ Services page in DataView (Table / Grid): name, endpoints, status, calls today, errors, last call; create, rename, duplicate, delete (confirm)
- ⬜ Enable / disable a whole service (every endpoint in it stops answering with a clear error) — one switch, audited

### 3. Endpoints (one form each; as many as needed)

- ⬜ Create an endpoint from a form: pick form (published version) → name → methods → fields → authentication → access rules → review; the full URL shown with a copy button
- ⬜ Methods: **GET, POST, PUT, DELETE only** (for now); each switchable per endpoint
- ⬜ POST / PUT: choose the fields (columns) accepted, which are required, read-only fields refused; validation is the form's own (`shared/utils/forms/validate.ts`) — same rules as the form page
- ⬜ GET: choose the fields (columns) returned, filters allowed, paging, sorting; never more than the chosen fields
- ⬜ DELETE / PUT by record id; soft delete with the response kept in the audit trail
- ⬜ Where data goes: the form's storage / destinations (built-in storage or a Data source, F12) — the same pipeline as form submissions
- ⬜ Enable / disable each endpoint; version pinning to a form version; "Test" button
- ⬜ Example request and response (JSON) generated from the chosen fields

### 4. Authentication and headers

- ⬜ Static bearer token (long-lived, shown once, stored hashed, prefix shows test / live) **or** dynamic tokens: client id + secret → short-lived token from `POST https://api.formalie.dev/{apiKey}/token` (expires in minutes, auto-renew by the client)
- ⬜ Rotate / revoke tokens; expiry dates; scopes per service / endpoint / method; last used
- ⬜ Optional request signing (HMAC header + timestamp) for high-security callers
- ⬜ Headers: `Authorization: Bearer …` (required) · `Content-Type: application/json` · optional `Idempotency-Key` (safe retries of POST) · optional `X-Formalie-Destination` (choose among destinations the endpoint allows) · custom required headers defined per endpoint (name + expected value)
- ⬜ No tenant / organisation id headers needed: the URL key and the token identify the organisation and must match — a mismatch is refused (no spoofing)
- ⬜ Responses always JSON: `{ data, meta }` or `{ error: { code, message, details } }` with `FRM-API-*` codes

### 5. Access rules (allow / block lists)

- ⬜ Allow-list and block-list by IP address / range, domain (Origin / Referer for browser callers), region and country
- ⬜ Per service and per endpoint; block wins over allow; test a caller against the rules
- ⬜ Rate limits per token / IP / endpoint with clear `429` responses

### 6. Logs and analytics

- ⬜ Request logs: time, endpoint, method, status, duration, caller IP / country, token name; filters, search, export; request / response bodies only when switched on (masked)
- ⬜ Analytics (separate from the form analytics): calls, errors, latency (p50 / p95), top endpoints, top callers, by country; date range
- ⬜ Own dashboard in F21 (Forms, Data sources and API service each get one)

### 7. Docs and testing

- ⬜ Generated documentation per service (OpenAPI), code snippets (curl, JavaScript, Python, PHP, C#), copy buttons
- ⬜ Try-it console with a test token; sandbox / test mode that doesn't write live data

### 8. Safety and audit

- ⬜ Every change to services, endpoints, tokens and rules is audited (`api.*`); tokens never shown again after creation
- ⬜ TLS only; CORS per endpoint for browser callers; request size limits; no secrets or bodies in logs by default
- ⬜ Permissions per role in F22; admins only until then

### 9. Integrations (moved here from F15, owner 2026-10-03)

- ✅ Menu entries in the API service area: Webhooks · API keys · App integrations (placeholders; old `/integrations/*` links redirect)
- ⬜ Webhooks: create (URL, events, secret), signed payloads, test delivery; delivery log with retries and response details
- ⬜ API keys (Formalie's own management API): create (name, scopes, expiry), show once, copy, revoke, last used
- ⬜ App integrations: Google Sheets, Slack / team chat, email notifications to external addresses

### 10. API (mock first)

- ⬜ Portal management API: `/api-services` · `/api-services/{id}/endpoints` · `/api-tokens` · `/api-access-rules` · `/api-logs` · `/api-analytics`; error codes `FRM-API-*`; contract updated

---

## F14 — Settings ⬜

**Goal:** one place where workspace admins control everything about their workspace. Each section is its own page under `/settings/*`, with a section menu (sidebar list on desktop, select on phones), unsaved-changes warning and a save bar.

### Settings shell

- ⬜ `/settings` overview: section cards with a one-line status each (e.g. "2 sign-in methods enabled")
- ⬜ Section navigation (desktop list, phone select), breadcrumbs, unsaved-changes guard
- ⬜ Search inside settings (also from the command palette)

### Company & branding

- ⬜ Company profile: legal name, display name, industry, size, address, country, tax / registration number, support email and phone
- ⬜ Branding: logo (light + dark), favicon, brand colour, sign-in page image and message; live preview of the workspace sign-in page

### Organisation data (owner, 2026-10-03 — decision 79)

Every workspace sets up its own reference data here; the builder, field access and logic only ever offer what the workspace has (no built-in samples once Settings exist), with an empty state that links straight to the right settings page.

- ⬜ **Departments:** create, rename, merge, archive (forms keep their history); members per department; import from CSV
- ⬜ **Roles / job titles:** the workspace's own list (separate from the permission roles of F22); people can hold several
- ⬜ **Teams, locations / sites, cost centres** (optional lists, same pattern)
- ⬜ **Lists (option sets):** reachable from Settings as well as Resources → Option sets (F15) — every list and its kinds (simple, large / searchable, cascading, with details, dynamic)
- ⬜ Builder pickers read these live: field access (departments, roles, people), choice fields "from a list", logic conditions; removed / archived entries are flagged on forms that still use them
- ⬜ Mock: replace the fixed sample departments / roles in `server/mock/routes/directory.ts` with per-workspace data managed here

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

- 🟡 Themes library (created in the designer, F8): list, rename, delete done in F8; set workspace default ⬜
- ⬜ Embed defaults (allowed domains, size), default form settings (progress bar, save and resume)

### Billing & subscription

- ⬜ Current plan, usage against limits (forms, responses per month, seats, destinations)
- ⬜ Upgrade / change plan, payment method, invoices
- ⬜ Plan-limit messages wherever a limit is hit (FRM-PLAN-1001 / 1002)

---

## F15 — Option sets & payments ⬜

### Option sets (reusable choice lists)

Full plan: [docs/OPTION-LISTS.md](docs/OPTION-LISTS.md) (owner request 2026-10-02). Simple saved lists already exist (F7).

- ⬜ **F15a List manager:** Option sets page (DataView), create, rename, delete (confirm when used by forms)
- ⬜ Items: add, edit, retire, bulk paste, import CSV / XLSX with column mapping, reorder (drag + keyboard), values vs labels, translations
- ⬜ "Used in" list of forms and fields
- ⬜ **F15b Large lists + autocomplete:** items on the server, "search as you type" field mode, paging
- ⬜ **F15c Cascading lists (levels):** tree lists (e.g. State → City → Location, up to 5 levels), "Cascading choice" field group, child opens with the parent's items only, changing the parent clears children
- ⬜ **F15d Details + auto-fill:** extra columns on items; choosing an item fills other fields (optionally read-only); columns usable in formulas and logic
- ⬜ **F15e Dynamic lists:** live sources — another form's responses, a connected database (read-only query), a JSON URL, a refreshed CSV; refresh schedule and sync log
- ⬜ Public option lookups for respondents (rate limited, published lists only); answers store value + label (+ path)

### Destinations (where responses go)

- Moved to **F12 — Data sources & databases** (connections, sending form data, explorer, query editor, other database operations).

### Payments (Payment field — shown as "soon" in the builder until then)

- ⬜ Payment providers per workspace (connect with the provider's own sign-in; e.g. Stripe, PayPal, Adyen, Mollie, Razorpay, Flutterwave, Paystack — global and regional), test / live mode
- ⬜ Payment field: fixed amount, amount from a choice, or **calculated** (formula — order totals, fees); currency; optional tax and fee lines; one-off payments first (subscriptions later)
- ⬜ Card details never touch Formalie: the provider's secure checkout / hosted fields; we keep only the payment status, reference and amount
- ⬜ Response shows paid / pending / failed / refunded; receipts by email; refunds from the response (audited); webhooks from the provider confirm payment before the response counts as complete

### Webhooks, API keys, other integrations

- Moved to **F13 — API service & integrations** (owner, 2026-10-03: integrations belong to the API service).

---

## F16 — Profile ⬜

- ⬜ My profile (name, photo, language, timezone)
- ⬜ Change password
- ⬜ Authenticator app (QR, recovery codes), SMS number
- ⬜ Sessions and devices (see and sign out)

---

## F17 — Users ⬜

- ⬜ Users list (DataView), invite by email with role, resend / revoke invites
- ⬜ Enable / disable, reset password or MFA
- ⬜ Team avatars + "Invite member" in the header (design reference)

---

## F18 — Analytics ⬜

- ⬜ Per form: views, starts, completions, completion rate, average time
- ⬜ Drop-off per page and field
- ⬜ Per-question charts, NPS
- ⬜ Date range, export

---

## F19 — AI assistant 🟡

**Goal:** an assistant built into Formalie that makes work easier — creating forms and templates, analysing responses, summarising, translating and more (owner idea 2026-10-03). Own rail area and menu; also available in context (builder, templates, responses). People stay in control: the assistant proposes, a person reviews and applies; nothing is published or sent by the assistant on its own.

### 1. Area and navigation

- ✅ Own rail area (sparkles icon) with its own menu: Overview · Create a form · Template ideas · Response analysis · Insights & summaries · Translations · History · Settings & usage — placeholder pages (`/ai/**`)

### 2. Creating

- ⬜ Describe a form in plain words (or paste a document / old form) → a draft with pages, fields, options, validation, logic and calculations, shown as a preview to accept, edit or regenerate; then opened in the builder
- ⬜ In the builder: "Suggest fields", "Write help texts", "Add logic", "Check my form" (accessibility, missing validation, duplicate questions)
- ⬜ Template ideas: generate a template for an industry / use case, with a matching theme; save to the workspace templates (F9)
- ⬜ Design help: suggest a theme from a brand colour / logo / website

### 3. Analysing

- ⬜ Response analysis per form: themes in open text, sentiment, trends, outliers, comparison between periods
- ⬜ Ask questions about the data in plain words ("Which site had most incidents last month?") with the numbers and the filters used shown
- ⬜ Insights and summaries: weekly digest per form, summary of a single response, executive summary for exports

### 4. Translating and writing

- ⬜ Translate a form (labels, options, help, messages) into any of the 20 languages; reviewed side by side before applying
- ⬜ Rewrite for clarity / tone; plain-language check

### 5. Control, privacy and cost

- ⬜ Settings: switch the assistant on / off per workspace, choose which areas it may read (forms, responses, data sources), keep personal data out (masking), retention of prompts
- ⬜ Usage and limits per plan; history of every request (who, what, when) with the result; everything audited (`ai.*`)
- ⬜ Clear labelling of AI-made content; nothing applied without a person's confirmation
- ⬜ Model / provider choice is a backend decision (documented when F19 starts); data processing terms shown — controls, not certifications

---

## F20 — Live collaboration (optional) ⬜

- ⬜ Presence, cursors and selections in the builder
- ⬜ Conflict-free editing
- ⬜ Comments on fields (later)

---

## F21 — Dashboard ⬜

- ⬜ Separate dashboards for **Forms**, **Data sources** and **API service** (owner, 2026-10-02), plus the workspace overview

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

## F22 — Roles & access ⬜ (last)

- ⬜ Roles and permissions editor (permission catalogue, custom roles)
- ⬜ Role assignment per user and per organisation; form-level access
- ⬜ Access overview ("who can see what")
- ⬜ Permission to view and export the audit trail (`audit.read`, `audit.export`)


## F23 — Platform admin (super admin) ⬜

The Formalie team's own console (owner, 2026-10-03: "a place for me to manage everything") — separate from any workspace, on its own host (`admin.formalie.com`), signed in with platform staff accounts and strong second factor; every action audited.

### Platform settings

- ⬜ **Legal links** on every public form: Terms and Data Privacy Policy URLs (already served by the API as platform settings with the app config as fallback — `PublicForm.legal`, mock `server/mock/data/platformStore.ts`); change once, applies to every form without a redeploy
- ⬜ Marketing site, support email / help-centre links, status page link
- ⬜ Platform branding on Formalie-branded surfaces (forms host, QR codes, emails)
- ⬜ Feature switches and announcements (banner in the portal)

### Workspaces and people

- ⬜ Workspaces list (DataView): plan, status, usage, created; suspend / restore (FRM-TEN-1002), change subdomain
- ⬜ Platform staff accounts and their roles; impersonation only with the workspace's consent, time-limited and audited

### Catalogue

- ⬜ System templates and themes (publish, retire), template content languages
- ⬜ Platform audit trail and security events
---

## Switching to the real backend ⏸

- ⏸ Turn off the mock and point the proxy at FastAPI
- ⏸ Run the encryption tests against backend test vectors
- ⏸ Compare `API-CONTRACT.md` with the backend's generated contract

---

## New requests log

Owner requests added during development, and where they landed.

| Date       | Request                                                                                                                                                                                                                                                                                                                                                           | Where                                                                             | Status     |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------- |
| 2026-10-02 | Support many languages (at least 15) → 20 languages                                                                                                                                                                                                                                                                                                               | F0                                                                                | ✅         |
| 2026-10-02 | Organise files in sub-folders (max two levels)                                                                                                                                                                                                                                                                                                                    | all                                                                               | ✅         |
| 2026-10-02 | Works on every host (manage, workspaces, localhost, IP)                                                                                                                                                                                                                                                                                                           | F0                                                                                | ✅         |
| 2026-10-02 | Match the design references exactly                                                                                                                                                                                                                                                                                                                               | F1                                                                                | ✅         |
| 2026-10-02 | Flags on the language switcher, breadcrumbs in the header, font from the design                                                                                                                                                                                                                                                                                   | F1                                                                                | ✅         |
| 2026-10-02 | Menu detail: timeline children, square bullets, clean dark text                                                                                                                                                                                                                                                                                                   | F1                                                                                | ✅         |
| 2026-10-02 | Title, subtitle, breadcrumbs and buttons in the header; footer                                                                                                                                                                                                                                                                                                    | F1 / F2                                                                           | ✅         |
| 2026-10-02 | Keep the table / grid / filters flow unchanged                                                                                                                                                                                                                                                                                                                    | F2                                                                                | ✅         |
| 2026-10-02 | "Wow" sign-in screen                                                                                                                                                                                                                                                                                                                                              | F3                                                                                | ✅         |
| 2026-10-02 | Test accounts in the README; realistic test people                                                                                                                                                                                                                                                                                                                | F3                                                                                | ✅         |
| 2026-10-02 | Global positioning (not one country); international sample data                                                                                                                                                                                                                                                                                                   | F3 / all                                                                          | ✅         |
| 2026-10-02 | Show 5+ supported databases or built-in encrypted storage                                                                                                                                                                                                                                                                                                         | F3 / F14                                                                          | ✅         |
| 2026-10-02 | Separate progress file with every task per phase                                                                                                                                                                                                                                                                                                                  | PROGRESS.md                                                                       | ✅         |
| 2026-10-02 | Social providers on the first signup; more methods enabled later per workspace                                                                                                                                                                                                                                                                                    | F3 / F14                                                                          | 🟡         |
| 2026-10-02 | Provider buttons on one row with a "Sign up with" caption                                                                                                                                                                                                                                                                                                         | F3                                                                                | ✅         |
| 2026-10-02 | Settings as its own detailed phase; Dashboard after everything, just before RBAC                                                                                                                                                                                                                                                                                  | F14 / F21                                                                         | ✅         |
| 2026-10-02 | Audit trail early (its own phase after sign-in), not last                                                                                                                                                                                                                                                                                                         | F4                                                                                | ✅         |
| 2026-10-02 | Use "Email address" (not "Work email") so any email provider is welcome                                                                                                                                                                                                                                                                                           | F3                                                                                | ✅         |
| 2026-10-02 | Sidebar: chevron and count badges on the right; counts on items that have them                                                                                                                                                                                                                                                                                    | F1                                                                                | ✅         |
| 2026-10-02 | Don't expire sessions so soon — at least 1 hour when idle                                                                                                                                                                                                                                                                                                         | F3 / F14                                                                          | ✅         |
| 2026-10-02 | Loading feedback everywhere: page loading, progress, skeletons, top bar, busy buttons                                                                                                                                                                                                                                                                             | F2 / all                                                                          | ✅         |
| 2026-10-02 | In-page loading bar (left-to-right sweep) when moving between pages, not only on reload                                                                                                                                                                                                                                                                           | F2 / all                                                                          | ✅         |
| 2026-10-02 | Design images are style, not features — follow the look exactly, don’t copy widgets                                                                                                                                                                                                                                                                               | all                                                                               | ✅         |
| 2026-10-02 | New form: richer Blank tab (live mini preview + what you get), form details card, Continue button under every tab                                                                                                                                                                                                                                                 | F6                                                                                | ✅         |
| 2026-10-02 | Folders in the sidebar with counts, folder pages and an all-folders view with statistics                                                                                                                                                                                                                                                                          | F11                                                                               | ⬜         |
| 2026-10-02 | Builder feedback (18 points): inline rename, try fields on the canvas, read-only keys with suffix, help as info icon, smaller radius, tighter spacing, label position, Nuxt UI dates, saved fields + lists, file-type picker, thumbnails, option numbers in formulas, clearer + complete logic, read-only / disabled with required guards, phone preview stacking | F7                                                                                | ✅         |
| 2026-10-02 | Form themes: header, footer, body, images and text design carried on shared forms; default theme when none is chosen                                                                                                                                                                                                                                              | F8                                                                                | ⬜         |
| 2026-10-02 | Builder canvas uses the full width; full-screen toggle with fields · canvas · settings and visible save status                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Lists later: static, large / autocomplete, dynamic sources, cascading levels (State → City → Location) and auto-fill of other fields — plan in docs/OPTION-LISTS.md                                                                                                                                                                                               | F15                                                                               | ⬜         |
| 2026-10-02 | Drop indicator while dragging fields (dashed placeholder + label)                                                                                                                                                                                                                                                                                                 | F7                                                                                | ✅         |
| 2026-10-02 | Rich text field (real editor)                                                                                                                                                                                                                                                                                                                                     | F7                                                                                | ✅         |
| 2026-10-02 | New fields default to ½ width; required messages use the field label                                                                                                                                                                                                                                                                                              | F7                                                                                | ✅         |
| 2026-10-02 | Rich text: headings 1–6, paragraph, text alignment, code block                                                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Layout blocks: nicer section, inline paragraph editing, image upload + resize, divider options                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Validate email and all address parts (not only the first line)                                                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | IT / technical field types: IP address, domain, MAC, IBAN, SWIFT / BIC, colour + global types (full name, consent, duration, percentage, language, time zone, currency) — first set built; owner may add more                                                                                                                                                     | F7 (later)                                                                        | ⬜         |
| 2026-10-02 | More theme designs: header-only, footer-only and side designs — at least 5 more now, more later                                                                                                                                                                                                                                                                   | F8                                                                                | ✅         |
| 2026-10-02 | Form workspace header too full: search as an icon, Preview as an icon                                                                                                                                                                                                                                                                                             | F8                                                                                | ✅         |
| 2026-10-02 | Templates before the renderer (both serve form creation) — phases renumbered: F9 Templates, F10 Renderer, F11 Responses                                                                                                                                                                                                                                           | Roadmap                                                                           | ✅         |
| 2026-10-02 | Integrations for data sources: add their databases to send form data, database explorer, query editor, other database operations                                                                                                                                                                                                                                  | F12 (new phase)                                                                   | ⬜         |
| 2026-10-02 | Data sources as its own rail area with its own menu; placeholder pages now (no extra Forms icon — the workspace button is Forms)                                                                                                                                                                                                                                  | F12                                                                               | ✅         |
| 2026-10-03 | API service ("developer option"): build API endpoints from forms (GET / POST / PUT / DELETE), tokens and headers, field choice per method, allow / block lists, analytics, enable / disable; own rail area with placeholders                                                                                                                                      | F13 (new phase)                                                                   | 🟡         |
| 2026-10-03 | API addresses `https://api.formalie.dev/{key}/{endpoint}` (production `api.formalie.com`)                                                                                                                                                                                                                                                                         | F13                                                                               | ✅ decided |
| 2026-10-03 | Form links `https://{forms                                                                                                                                                                                                                                                                                                                                        | sub}.formalie.com/{formId}/fill`and`/embed` (`forms.formalie.dev` in development) | F10        | ✅ decided |
| 2026-10-03 | Separate dashboards for Forms, Data sources and API service                                                                                                                                                                                                                                                                                                       | F21                                                                               | ⬜         |
| 2026-10-03 | Template catalogue: 84 starter templates in 11 categories, each with its own design; calculations where needed (risk score, totals, averages); template statistics and the forms made from each template                                                                                                                                                          | F9                                                                                | ⬜         |
| 2026-10-03 | AI assistant built in (create forms, templates, analysis, more) — own rail area with placeholders                                                                                                                                                                                                                                                                 | F19 (new phase)                                                                   | 🟡         |
| 2026-10-03 | "Folder" on New form — what it means                                                                                                                                                                                                                                                                                                                              | F8                                                                                | ✅         |
| 2026-10-03 | IP address and MAC address typing masks (MAC: other notations allowed)                                                                                                                                                                                                                                                                                            | F8                                                                                | ✅         |
| 2026-10-03 | Field access: Everyone / Departments / Roles / People; restricted fields never required                                                                                                                                                                                                                                                                           | F8 (answers visibility in F11)                                                    | ✅         |
| 2026-10-03 | Payment field — intention                                                                                                                                                                                                                                                                                                                                         | F15 (Payments)                                                                    | ⬜         |
| 2026-10-03 | How duplicate submissions are prevented                                                                                                                                                                                                                                                                                                                           | F10                                                                               | ⬜ planned |
| 2026-10-03 | Field access: Departments / Roles showed no list to pick from                                                                                                                                                                                                                                                                                                     | F8                                                                                | ✅         |
| 2026-10-03 | Templates table: smaller, even thumbnails                                                                                                                                                                                                                                                                                                                         | F9                                                                                | ✅         |
| 2026-10-03 | Form overview page: a much richer, connected design                                                                                                                                                                                                                                                                                                               | F9 (owner request)                                                                | ✅         |
| 2026-10-03 | Templates and Themes menus: new icons, submenus with the 6 most recent + "All"                                                                                                                                                                                                                                                                                    | F9                                                                                | ✅         |
| 2026-10-03 | Integrations belong to the API service (menu + phase)                                                                                                                                                                                                                                                                                                             | F13                                                                               | ✅ moved   |
| 2026-10-03 | Responses menu with submenus (statuses, exports)                                                                                                                                                                                                                                                                                                                  | F11                                                                               | ✅ menu    |
| 2026-10-03 | Template page side panel: better tiles, calculations as code snippets, forms made from it as a slider with "View all"                                                                                                                                                                                                                                             | F9                                                                                | ✅         |
| 2026-10-03 | Uploaded files inside the drop zone                                                                                                                                                                                                                                                                                                                               | F9                                                                                | ✅         |
| 2026-10-03 | Notify when a wrong file type is chosen                                                                                                                                                                                                                                                                                                                           | F9                                                                                | ✅         |
| 2026-10-03 | Errors clear as soon as the answer is fixed (no waiting for Next / Submit)                                                                                                                                                                                                                                                                                        | F9                                                                                | ✅         |
| 2026-10-03 | Remove (×) on attached files not visible in some designs                                                                                                                                                                                                                                                                                                          | F9                                                                                | ✅         |
| 2026-10-03 | Gallery grid thumbnails look stretched                                                                                                                                                                                                                                                                                                                            | F9                                                                                | ✅         |
| 2026-10-03 | Folders: where to add / rename / remove; block removing folders with forms                                                                                                                                                                                                                                                                                        | F6 / F9                                                                           | ✅         |
| 2026-10-03 | Max files / max size not enforced, no notification                                                                                                                                                                                                                                                                                                                | F9                                                                                | ✅         |
| 2026-10-03 | Themes like templates: system, saved and created themes                                                                                                                                                                                                                                                                                                           | F9 milestone 2                                                                    | ⬜         |
| 2026-10-03 | Form overview KPI cards like the design (title colour and position)                                                                                                                                                                                                                                                                                               | F9                                                                                | ✅         |
| 2026-10-03 | Form link vs embed link — same or different? (advice: different; embed as code)                                                                                                                                                                                                                                                                                   | F10                                                                               | ✅ decided |
| 2026-10-03 | QR code for form links                                                                                                                                                                                                                                                                                                                                            | F9 / F10                                                                          | ✅         |
| 2026-10-03 | Languages go with the forms (links, embeds, QR, respondent language)                                                                                                                                                                                                                                                                                              | F9 (picker) / F10 (public pages)                                                  | 🟡         |
| 2026-10-03 | Themes clickable to view or edit                                                                                                                                                                                                                                                                                                                                  | F9                                                                                | ✅         |
| 2026-10-03 | Branded QR codes (organisation, form name, logo in the centre, Formalie mark), several colours, branding on / off | F9 | ✅ |
| 2026-10-03 | Folder explanation behind an info icon (click to read) instead of text under the field — new form page and "Use template" dialog | F9 | ✅ |
| 2026-10-03 | Templates: category chips removed from the top — categories (with counts) only in the Filter menu, like every other list | F9 | ✅ |
| 2026-10-03 | Templates by category: gallery lists categories (counts + analytics) instead of all 84 templates; a category opens its templates; menu shows the top 6 categories then All; Formalie templates and your own (saved) templates kept apart | F9 | ✅ |
| 2026-10-03 | Departments, roles and other organisation data (and lists) are set up per workspace in Settings; the builder only shows what the workspace has | F14 (Organisation data) · F15 | ⬜ planned |
| 2026-10-03 | Preview: Desktop mode fills the whole screen edge to edge (was a box); the design page's preview fills its pane | F10 | ✅ |
| 2026-10-03 | Themes menu like Templates: kinds with counts (All themes · Formalie · Saved · Created) instead of every saved theme | F8 follow-up | ✅ |
| 2026-10-03 | Save as template lives in Form settings → Template (after Save and resume), not the header; a form already saved as a template shows that and offers "Update template" (same template, latest changes) or a separate copy | F9 follow-up | ✅ |
| 2026-10-03 | Sidebar: one menu group open at a time (opening one closes the others) | F1 follow-up | ✅ |
| 2026-10-03 | Preview side panel: Desktop fills the panel edge to edge (panel keeps its width) | F10 | ✅ |
| 2026-10-03 | Text colours sharp and dark everywhere (tables, grids, cards like the navigation) | F1 follow-up | ✅ |
| 2026-10-03 | No real ids anywhere in URLs, parameters or responses — encrypted references only the API can decrypt (globally) | F2 follow-up (security) | ✅ |
| 2026-10-03 | Public form footer: © organisation · Terms · Data Privacy Policy; every link on a public form opens in an in-app browser window over the form (branded, 80%, rounded, clear close) so nothing typed is lost | F10 | ✅ |
| 2026-10-03 | Super admin console for the owner to manage everything — starting with the Terms / Data Privacy Policy URLs (served now as platform settings, config fallback) | F23 (new phase) | ⬜ planned |
| 2026-10-03 | Prevent duplicate submissions (also when someone fills in for a friend on the same computer); thank-you buttons Fill in another (confirm it's for someone else) and Close this page; form availability period (expired page after it); show the period in table and grid | F10 | ✅ |
| 2026-10-03 | Still possible to send twice (one-letter email change): identify the person by their own email (not other emails in the form) or ID; smart matching; optional verification; never mistake another person | F10 | ✅ |
| 2026-10-03 | Events & bookings and Operations & IT designs: side panel squeezed the form — use a smaller quote-like header instead | F9 follow-up | ✅ |
| 2026-10-03 | Help guide per form: written in Form settings (rich editor, opened from a button), shown from a floating "?" in a chat-style panel; on / off, off by default | F10 | ✅ |
| 2026-10-03 | Save and resume: how and where it works — built (autosave + "Save and continue later" link) | F10 M2 | ✅ |
| 2026-10-03 | Portal text still looked faded: dark-mode headline colour fixed, body text darker, list values in the main text colour like the design image | F1 follow-up | ✅ |
| 2026-10-03 | Public form page: branded frame around the form — workspace branding, link to the organisation's website, several page designs to choose from; polished and lively without distracting from the form | F10 (M1b) | ✅ |
| 2026-10-04 | French form: labels, sections, help and thank-you stayed English; "already filled in" showed only after the form flashed for seconds; spam check not visible anywhere | F10 | ✅ |

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
| 2026-10-02 | F3    | Signup offers Google, Microsoft, Apple, Facebook (manage.*) plus email; new workspaces start with email sign-in, more methods enabled in Settings (F14). Provider callback waits on the backend.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F3    | Provider buttons on one row with a "Sign up with / Sign in with" caption: logo + name for 2, logo only (tooltip) for 3–4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-10-02 | F3    | "Work email" → "Email address" everywhere, neutral placeholder name@example.com, no "work email" wording (any organisation, any email provider).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F3    | Phase done: RTL, keyboard-only and phone passes on every auth screen (logical tab order, nothing hidden focusable, no overflow at 375 px).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-10-02 | F4    | Audit trail moved up to its own phase right after sign-in (owner); phases renumbered, RBAC is now F22 (last).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
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
| 2026-10-02 | F7    | Answer validation: email, web address, phone, number range, length, pattern, choice counts, files, date range and every required address part (postal code / region switchable); errors name the field, update live, missing address parts highlighted. One shared validator for renderer and API.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F8    | Milestone 1: Design view with live preview (devices, thank-you page), starting points, layout / background / container / typography / colours / inputs / buttons / header + cover / footer / thank-you; themes stored on the form, applied as CSS variables on the form page only, workspace default from brand colour + logo; builder Preview themed.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F8    | Milestone 2: save / update / apply themes from the designer, themes library page (rename, duplicate, delete with usage count), audit + `FRM-FORM-1010`. 13 new field types (global + technical) with validation (IP v4/v6, domain, MAC, IBAN mod-97, BIC, colour, duration, name parts, consent, catalogue picks); all 20 languages.                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-10-02 | F8    | Six more starting points (Banner, Ribbon, Grounded, Side panel, Aurora, Corporate) with header bands, footer bars and colour / gradient side panels; designer controls for each; swatches show the structure. Form workspace header: search and Preview as icons. Confirm dialogs now always open above drawers (they were hidden behind the designer drawer on phones). Roadmap: Templates moved before the renderer (F9 Templates · F10 Renderer · F11 Responses).                                                                                                                                                                                                                                                                                                             |
| 2026-10-02 | F8    | Fix: “Add link” in the footer reset the footer (a new link starts as an incomplete https:// address, which failed the theme check and switched the footer off). Links are now kept while being typed; only complete https links with a label show on the form; other schemes are emptied.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

| 2026-10-02 | Roadmap | New phase **F12 — Data sources & databases** (connections, sending form data, database explorer, query editor, other database operations, safety); later phases renumbered F14–F22 (Settings → Roles & access). |
| 2026-10-02 | F12 | Placeholder shell: Data sources rail area (icon under the workspace button), own sidebar menu, overview with section cards and supported databases, seven placeholder pages; destinations moved from Integrations (redirect kept). |
| 2026-10-03 | F13 | New phase **F13 — API service** (own rail area + placeholder pages); later phases renumbered F14–F22. Public URL scheme decided: API `https://api.formalie.dev/{apiKey}/{endpoint}`, forms `https://{forms | sub}.formalie.dev/{formKey}/fill · /embed`; `forms` subdomain reserved; copy-link and the form overview use the new links. F8 closed after owner review. |
| 2026-10-03 | F8 | Owner follow-ups: folder hint, IP / MAC typing masks, field access (audience) with directory picker and "never required" rule (editor, form, publish check, logic). |
| 2026-10-03 | F19 | New phase **F19 — AI assistant** (own rail area + placeholder pages); later phases renumbered F20–F22. F9 plan written: framework + 84 templates in 5 milestones. Payments planned in F15. |
| 2026-10-03 | F9 | Milestone 1: template authoring kit (`shared/templates/`), 11 categories with their own designs, 20 templates (Business & Customer, HR & Workplace) with calculations (totals, averages, days, rating bands, loyalty group) and logic — all tested as valid, publishable forms; formula additions `avg` / `count` / `days` / text results, internal calculations; gallery (Grid of themed cards / Table, category chips with counts, filters, sorts), template page (live preview, what’s included, formulas, usage, forms made from it), Use template, Save as template, workspace templates (duplicate, delete), New form catalogue picker; seeded sample forms linked to templates; mock `/templates`; 20 languages. Also: confirm dialog keeps its text while closing. |
| 2026-10-03 | F9 | Owner review round: form overview redesign (KPIs, 30-day chart, share, structure, versions, details, activity; mock `/forms/:id/overview`), template page side panel (tiles, formula snippets, forms slider), mini table thumbnails, sidebar submenus (Templates / Themes recent 6 + All, Responses statuses), integrations moved to the API service (pages + redirects; F13 renamed "API service & integrations", F15 "Option sets & payments"), forms list Template filter, field access list fix. Duplicate-submission protection planned (F10). |
| 2026-10-03 | F9 | Owner review fixes: file uploads (inside the zone, limits enforced with notifications, visible remove), live error clearing for duration, page-shaped gallery thumbnails, folders with forms can't be deleted (`FRM-FORM-1013`); themes catalogue (system / saved / created) planned into milestone 2. |
| 2026-10-03 | F9 | Milestone 2: 23 templates — Health & Safety (risk score / level with action plan, incident priority, near-miss priority, inspection compliance %, BMI, screening result, guardian consent), Events & Bookings (ticket totals, room cost, sponsorship totals, speaker / sponsor page logic), Hospitality (nights from dates, nightly-rate estimate, service score, catering per guest); 43 templates in total, every onboarding starter now from the catalogue. Themes catalogue: system (starting points + category designs, read-only), saved and created themes; theme editor (`/settings/themes/new`, `/settings/themes/:id`) with live preview, Cmd/Ctrl+S and a leave guard. |
| 2026-10-03 | F9 | KPI cards aligned with the design; QR codes for form links (`uqr` added, owner-approved); form language setting; themes open in the editor (workspace) or read-only (Formalie) from list and grid; Settings no longer highlighted on theme pages. Language plan for public forms recorded (decision 73). |
| 2026-10-03 | F9 | Milestone 3: 21 templates — Education (course score, quiz score / percentage / pass, scholarship eligibility for the panel only, attendance count and rate), Operations & IT (ticket priority from impact × urgency, change risk, requisition totals, inspection and QC pass rates), Finance & Legal (debt-to-income and a flat-rate monthly estimate, invoice subtotal / tax / total, claim total, company details when signing for a company); 64 templates in total; new calculation checks; 20 languages. |
| 2026-10-03 | F9 | Milestone 2 + 3 languages complete: template names, theme library and errors in all 20 languages; Spanish wording aligned to "tú" throughout; 188 tests green. |
| 2026-10-03 | F9 | Milestone 4: 20 templates — Community (membership fee, donation with optional 3% cost cover, petition, ranked ballot), Real Estate (income-to-rent ratio with an internal affordability band, room-by-room condition score, emergency note on urgent repairs), Sales (B2B lead capture with hidden source fields, seat-based quote, BANT-style qualification hot / warm / cold, trade order with volume discount); all 84 templates in 11 categories; 20 languages. |
| 2026-10-03 | F9 | Milestone 5: template content (1,411 texts) in all 20 languages — previews and new forms open in the person's language, logic / scores / formulas unchanged (compared values like "yes" kept); templates gallery reorganised by category (overview with counts and use, category pages, Your templates apart, menu: top 6 categories + All + Your templates); 228 tests green. Stopped for the owner's end-of-phase review. |
| 2026-10-03 | F9 | Owner review passed — F9 closed. Preview fix (Desktop full screen, Tablet / Phone device frames that fill the height; design page preview fills its pane); organisation data (departments, roles, lists) planned into Settings (F14). |
| 2026-10-03 | F9 | Follow-ups: Themes menu by kind with counts; "Save as template" in the builder header (Build / Logic / Design, phone menu, full screen) — saves pending edits first, name pre-filled, menu counts refresh. |
| 2026-10-03 | F9 | Follow-ups: "Save as template" moved into Form settings → Template; templates remember their source form (`source_form_id`) — an already-saved form offers "Update template" (`POST /templates/{key}/sync`, audited) or a separate copy; sidebar keeps one group open; preview side panel Desktop fills edge to edge. |
| 2026-10-03 | F10 | Milestone 1: public form pages `/{key}/fill` and `/embed` (server-rendered, SEO tags, canonical, 404 for unknown keys, noindex for embeds / closed forms), `forms.*` host, `public_key` per form, secure server-side fetch (server-only token), states (not found · not published · closed · error), submit through the encrypted API with one response per fill-in session (Idempotency-Key, verified: a retry stores nothing new), server re-checks answers and recomputes calculations (`shared/utils/forms/submission.ts`), thank-you or redirect, page language without touching the portal cookie, embed height messages; audit "Response received". Text colours one step sharper everywhere (owner). |
| 2026-10-04 | F10 | M2: file uploads on public forms — files go straight to storage with progress on each thumbnail, Next / Submit wait for them, answers keep encrypted references (also in Save and resume drafts); server checks type, size, real pictures, no programs, same form / question, one response per file; respondent files never public. Form.vue split (ResumeBar, Upload). |
| 2026-10-04 | F10 | M2 done: spam protection without a captcha (invisible proof-of-work, hidden trap, submission limits) and the Embed code window on the Share card (auto / fixed height, resize script limited to the form address); embed pages can now be shown on other websites (frame headers, SameSite=None device cookie). |
| 2026-10-04 | F10 | Owner test fixes: "Translate the form’s text" when the form language changes (template text, 20 languages, own text kept); "already filled in" rendered by the server from a receipt cookie (no flash); Form settings shows "Spam protection — always on". |
| 2026-10-04 | F10 | Form language: choosing the language now translates the form text in the same step (no second button), toast with Undo. |
| 2026-10-04 | F10 | Blank forms now start in the creator's app language (form language, first page name, thank-you text), like template forms. |
| 2026-10-04 | F10 | Form language change also translates the builder's default question names ("Long text", "Option 1", "Page 1"…), not only template text (owner: a new "Long text" question stayed English). |
| 2026-10-04 | F10 | Form language change covers every field type and text spot (owner: "as long as it has a label"): matching ignores capitals / spaces, new 546-word everyday form vocabulary in all 20 languages, plus image alt / caption, custom error messages, guide title, header subtitle. |

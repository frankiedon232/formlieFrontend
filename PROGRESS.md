# Formalie Portal, Progress

The single place to see **what we are building, what is done and what is next**. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-08 (owner's general test done: lists with levels, builder click-to-add and panes, theme block styles, names outside the form body, API labels / order / connections, Publish only with changes; next: F15 M3 search for large lists)

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
| F10   | Renderer, preview, share, embed, short links, SEO | ✅     | 100% |
| F11   | Responses                                         | ✅     | 100% |
| F12   | Data sources & databases                          | ✅     | 100% |
| F13   | API service & integrations                        | ✅     | 100% (owner-tested 2026-10-06) |
| F14   | Settings                                          | ✅     | 100% (M1 to M7 ✅; billing in F23) |
| F15   | Option sets & payments                            | 🟡     | ~65% (M1 to M4 ✅; M5 dynamic lists next) |
| F16   | Profile                                           | ⬜     | 0%   |
| F17   | Users                                             | ⬜     | 0%   |
| F18   | Analytics                                         | ✅     | 100% |
| F19   | AI assistant                                      | 🟡     | ~2%  |
| F20   | Live collaboration (optional)                     | ⬜     | 0%   |
| F21   | Dashboard                                         | ⬜     | 0%   |
| F22   | Roles & access (last)                             | ⬜     | 0%   |
| F23   | Platform admin (super admin, Formalie team)       | ⬜     | 0%   |

**Every phase is only done when:** phone / tablet / desktop checked · keyboard-only checked · light + dark checked · Arabic RTL checked · every new action recorded in the audit trail (from F4 on) · loading feedback complete (first-load screen, top bar on navigation and API calls, skeletons, busy buttons, busy rows, progress bars, CLAUDE.md rule 5) · empty and error states present · every new string in all 20 languages · matches [docs/design](docs/design/README.md) · typecheck, lint and tests green · this file and the docs updated · committed and pushed.

---

## F0, Foundation ✅

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

## F1, App shell ✅

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

## F2, Core plumbing ✅

**Goal:** the shared building blocks every feature uses.

- ✅ Framework-free API client: envelope, CSRF, re-handshake, token refresh, abort, network errors (8 tests)
- ✅ `useApi()` (get / post / put / patch / delete / list), client-only, memory-only token
- ✅ `useErrorHandler()`: translated toasts for all 48 error codes, copyable support reference, form field errors
- ✅ `useBusy()`: loading state, no double submit, success toast
- ✅ `useFormat()`: dates, relative time, numbers, percent, currency, file sizes in the active language
- ✅ **DataView**, owner-approved, keep unchanged:
  - ✅ Table / Grid switch remembered per page
  - ✅ Search (`/`), Filter popover, filter chips, clear all
  - ✅ Date range with presets + calendar
  - ✅ Sort menu + sortable headers
  - ✅ Row selection + bulk bar, ⋯ row actions
  - ✅ Skeletons, empty, no-results, error + retry
  - ✅ Server pagination with page size; everything in the URL
- ✅ Confirm dialog (`useConfirm()`), copy field, status badge
- ✅ Forms list wired to the mock as the first DataView user
- ✅ Branded first-load screen (`app/spa-loading-template.html`), no blank page while the app starts
- ✅ Top progress bar on every API call, not only navigation (`useApi`; polling uses `background: true`)
- ✅ In-app navigation feedback: top bar starts on click and runs until the new page has its data; sweeping in-page bar under every page header (`useActivity`)

---

## F3, Workspace detection + sign-in ✅

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

- ✅ Sign in (workspace), redesigned: dark showcase panel + roomy form
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

## F4, Audit trail ✅

**Goal:** every action in a workspace is recorded, who, what, when, where (IP, location, device) and before / after values, and admins can search, filter and export it. Built now so every later phase records its own actions as it is built (owner request, product overview §11).

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

## F5, Onboarding wizard ✅

**Goal:** a new workspace is ready to use in a few skippable steps.

- ✅ Full-screen wizard (`/onboarding`, own layout: brand · language · theme · Finish later) with stepper (any step can be opened), phone progress bar and live preview (sign-in page, regional samples, team, form)
- ✅ Resume where the admin left off (progress stored on the server per workspace)
- ✅ Step: company details (name, industry, size, country with flags, website, `https://` added automatically)
- ✅ Step: branding (logo upload with real progress via pre-signed URL, brand colour presets + custom picker, live preview)
- ✅ Step: regional settings (workspace language, timezone with UTC offsets, currency, date / number format with live examples, first day of the week), defaults from the device and the company's country
- ✅ Step: invite team (email + role rows, paste a list, duplicates / own email caught)
- ✅ Step: first form (blank or one of 6 starter templates), finishing opens it in `/forms/new`
- ✅ Skip / back on every step, finish → chosen form (or Forms)
- ✅ Mock endpoints `GET / PATCH /onboarding`, `POST /onboarding/finish`, uploads (`POST /uploads` → PUT to storage → `POST /uploads/{id}/complete`)
- ✅ Every saved step recorded in the audit trail (workspace / branding / localisation changes with before → after, invitations, setup finished)
- ✅ Shown after signup (welcome hand-off); reachable later from Settings and the user menu (owners / admins); members are sent to Forms
- ✅ Workspace logo on the sign-in page and in emails (F14 Branding)
- ⬜ Workspace logo in the rail (the rail still shows the Formalie mark)
- ⏸ Real invitation emails (F17 Users), real object storage

---

## F6, Forms list and lifecycle ✅

**Goal:** everything you do _with_ forms before opening the builder.

- ✅ Forms list with DataView (search, status / folder / owner / tag filters, date range, sort, table / grid)
- ✅ New form: blank / from a starter template / import JSON (FormSchema v1 validated + previewed, 1 MB max); `?mode=` and `?template=` preselect
- ✅ Rename (inline in the table: Enter / blur saves, Esc cancels), duplicate, move to folder (with "new folder" on the spot)
- ✅ Folders: create, rename, delete (forms stay, without a folder), filter by folder incl. "No folder"
- ✅ Tags: add / remove (suggestions from the workspace), shown in rows and cards, filter by tag
- ✅ Owner filter
- ✅ Archive / unarchive (back to the previous status); close / reopen; unpublish, menu shows only what fits the status
- ✅ Delete → Trash (confirm); Trash page (`/forms/trash`) with restore, permanent delete (confirm), bulk, Empty Trash, days left
- ✅ Bulk actions (move, archive, delete; restore / delete permanently in Trash) on selected rows, with a summary toast
- ✅ Sidebar counts refresh right after every change; Trash entry with its own count
- ✅ Optimistic locking (`row_version`) with "changed by someone else" and a fresh list
- ✅ Busy rows / cards while an action runs (DataView `busy`), toasts for every result
- ✅ Form overview page (`/forms/{id}`): details, status actions, activity timeline; "Edit" arrives with the builder (F7)
- ✅ Mock endpoints for all of the above (per workspace, persisted across reloads)
- ✅ Every form and folder action recorded in the audit trail with before / after values

---

## F7, Form builder ✅

**Goal:** a robust drag-and-drop builder that works on desktop and stays usable on tablet and phone.

### Fields (one registry entry each: palette item, defaults, inspector, renderer, validation)

- ✅ Text: short text, long text, email, phone, URL, number, currency (amount with the currency symbol)
- ✅ Rich text, Nuxt UI editor (UEditor + toolbar, TipTap ships with Nuxt UI, no new dependency); Basic / Full toolbar (Full, the default: paragraph / heading 1–6, code, code block, left / centre / right / justify); answer stored as sanitised HTML (owner approved the text-align extension); read-only / disabled hide the toolbar; character count with max length
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

- ✅ Show / hide, skip / jump to page, required-if, one evaluator (`shared/utils/forms/logic.ts`) for preview, public form and API; Back follows the path actually taken
- ✅ Calculated values, safe arithmetic parser (never `eval`), formula editor with key chips and checks (unknown key, self-reference)
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
- ✅ Canvas fills the space between the panes (no fixed width); full-screen mode (button or Ctrl+Shift+F) shows only fields · canvas · settings under a slim bar with name, save status, undo / redo, Preview, Publish, Exit (Esc), browser full screen when allowed (owner request 2026-10-02)
- ➡️ Canvas virtualisation deferred: it conflicts with drag and drop; revisit if forms > 200 fields feel slow (measured, not guessed)
- ✅ Click to add (owner 2026-10-08): a click on an empty spot of the page opens a searchable field list there; the field lands where clicked (new row, or beside the fields of a row with room)
- ✅ No page title block on the canvas; the page name lives on its tab (pencil or double-click to rename); the page fills the screen height and grows with its content
- ✅ Fields and Settings panes collapse / open from the toggles beside the page tabs (open by default, remembered); selecting a field opens Settings
- ✅ Publish only with something new: disabled and dimmed with "No new changes. Make changes first." when the published form has no changes

---

## F8, Designer (themes) ✅

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
- ✅ Header / cover (cover image + height, logo, workspace or uploaded, form name, intro text, alignment), thank-you page (tick icon; title / message from form settings)
- ✅ Footer (text, up to 6 https links, logo, alignment) (owner request 2026-10-02)
- ✅ Default theme: a form without a design uses the workspace default (brand colour + logo from onboarding)
- ✅ Applied as CSS variables on the renderer only (Nuxt UI controls follow; portal untouched); theme stored on the form schema (versioned with publishing); builder Preview and Versions preview show the themed page
- ✅ Save as theme (new or update), apply a saved theme in the designer; themes library page (Resources → Themes): Table / Grid, search, rename, duplicate, delete with usage count; audited (`forms.theme_*`), milestone 2
- ✅ New global and IT field types (owner request): full name (title / middle optional), percentage, duration, consent with terms link, language, time zone, currency (all from `Intl`, in the respondent's language), IP address (any / IPv4 / IPv6), domain, MAC address, colour, IBAN (checksum), SWIFT / BIC, new palette group "Technical & IDs", validated by the shared validator
- ✅ Six more starting points with different structures (owner request): Banner (gradient header band), Ribbon (colour header band), Grounded (footer bar), Side panel (colour panel carrying logo / title), Aurora (gradient side panel), Corporate (header band + footer bar); new tokens `header.band`, `footer.style`, `split.panel`, all editable in the designer
- ✅ Owner follow-ups 2026-10-03: "Folder" on New form explained in place (workspace folders, not template categories); typing masks for IP address (IPv4 dots, IPv6 groups) and MAC address (colon pairs in capitals; dash / dot notation kept); **field access** (Everyone · Departments · Roles · People, all or selected; restricted fields can't be required; lock icon on the field; answers later shown only to the same people, F11)
- ✅ Sections and blocks (owner 2026-10-08): theme styles for sections (plain, underline, edge, band; accent or text colour; small capitals), dividers (line, colour, fade, dots, space; thin / thick), paragraphs (plain, soft, callout) and images (corners, shadow, border); a style per starting point and per template category; default = the earlier look
- ✅ Form name and page name outside the form body (owner 2026-10-08): the form name under the organisation in the page frame (or the hero title), the page name with the step progress
- ⬜ More fonts (self-hosted web fonts, needs a font package, ask first)
- ⬜ Custom CSS (paid plans, sanitised), with billing

---

## F9, Templates gallery ✅

**Goal:** nobody starts from an empty page, a catalogue full of beautiful, ready templates (fields, pages, logic, calculations **and a design**) that people pick, adapt and publish; plus their own workspace templates. Comes before the renderer (owner, 2026-10-02). Stays in the **Forms area** (Resources → Templates), no own rail icon: templates are a way to start a form.

**Approach (decided 2026-10-03, see 03-DECISIONS → 67):** framework first, proven on two full categories, then the remaining categories in batches, all inside F9, each batch committed and reviewable. F9 closes only when every listed template exists, in all 20 languages.

### Milestone 1, Framework + Business & Customer + HR & Workplace

- ✅ Template model: key, category, icon, name / description / tags (i18n), schema (pages, fields, logic, calculations, settings), theme, estimated time, field / page counts, "includes calculations / logic" flags, version; system vs workspace templates
- ✅ Authoring kit (`shared/templates/`): one small definition per template (fields by type, options, validation, logic, formulas, theme), validated against the form schema in tests, every template must pass the publish checks
- ✅ **Gallery** (`/templates`) in DataView: Grid of themed cards (mini preview in the template's own design, category, fields, time, "Calculations" / "Logic" badges, uses) and Table (name, category, fields, uses, forms, responses, updated); category chips with counts, search, sort (popular, newest, name, most used), filters (category, has calculations, field count, system / workspace)
- ✅ **Template page** (`/templates/[key]`): live themed preview (desktop / tablet / phone, questions / thank-you), what's included (pages, fields, logic rules, calculations with their formulas in plain words, design), statistics (forms created, responses collected, last used), and **all forms created from it** (DataView filtered by template)
- ✅ **Use template** → name + folder → new form opened in the builder; everything editable (fields, logic, design) before publishing; the form remembers its template
- ✅ New form → "From a template" tab reads the catalogue (search, category, design previews); onboarding starters use the catalogue where built (event registration and incident report follow with their categories in milestone 2)
- ✅ Workspace templates: save any form as a template (forms list row action + form overview menu; builder menu ⬜ with the builder header rework), edit name / description / category, duplicate, delete with confirm; audited (`forms.template_*`)
- ✅ Formula additions for templates: `avg()`, `count()`, `days(from, to)`, text results (e.g. risk level "High")
- ✅ Mock + contract: `/templates` (list with stats, get, create from form, update, duplicate, delete), `/templates/{key}/forms`, `/forms/from-template`; error codes
- ✅ Business & Customer (10): Customer Feedback · Customer Satisfaction (CSAT / NPS, NPS group calculated) · Product Review · Contact / Inquiry · Quote / Estimate Request (line totals, tax, total) · Order Form (line totals, subtotal, tax, total) · Complaint / Dispute · Service Request · Lead Capture / Newsletter Signup · Return / Refund Request (refund amount)
- ✅ HR & Workplace (10): Job Application · Employee Onboarding · Exit Interview · Leave / Time-Off Request (days requested) · Performance Review / Appraisal (average score, rating band) · Employee Engagement Survey (engagement index) · Expense Reimbursement (claim total) · Timesheet (hours, overtime) · Training Feedback (average) · Reference Check

### Milestone 1 follow-ups (owner review 2026-10-03)

- ✅ Template page: "What's included" as tiles; calculations as code snippets (coloured field references, functions, text, numbers; copy button; team-only marked); usage + the latest forms made from the template in a slider with "View all" (forms list → Template filter), moved from below the preview to the side
- ✅ Table view: small even thumbnails (64 × 40, small radius, shapes only)
- ✅ Sidebar: Templates (new icon) and Themes (palette icon) open submenus with the 6 most recent + "All …"; Responses opens status submenus (All, New, Reviewed, Approved, Rejected, Exports) with counts
- ✅ Form overview redesigned: KPI tiles (responses, completion with views → starts, median time, last response), 30-day response chart with hover / keyboard tooltips, share links (fill + embed), structure tiles linked to Build / Logic / Design, versions timeline, details with the template it came from, activity
- ✅ Field access: Departments and Roles open with the list to pick from ("All …" is a switch, off by default)

### Owner review fixes (2026-10-03)

- ✅ File uploads: chosen files sit inside the drop zone (compact grid), "{n} of {max}" + "Add more"; wrong type, too large and over the file limit are taken out again with a notification and a message under the field; remove buttons always visible (outline, round)
- ✅ Errors clear while typing everywhere: duration hours / minutes now report every keystroke (the stepper only reported on leaving the field)
- ✅ Gallery cards: page-shaped thumbnails with a fixed proportion (no stretching at any card width)
- ✅ Folders: create / rename / delete under Forms → Folders (also created from "Move to folder"); a folder that still holds forms can't be deleted (`FRM-FORM-1013`), its forms are one click away

### Milestone 2, Health & Safety · Events & Bookings · Hospitality ✅

- ✅ **Themes catalogue** (owner, 2026-10-03): the themes library shows three kinds, **System** (Formalie's designs: the starting points and every category design), **Saved** (saved from a form's design) and **Created** (made from scratch in a theme editor: the designer controls on a sample form, no form needed); filters and badges per kind; system themes can be duplicated, not changed; Themes submenu keeps the 6 most recent

- ✅ Health & Safety (8): Risk Assessment (likelihood × severity = risk score, risk level, action required when high) · Incident / Accident Report (severity score) · Near-Miss Report (potential severity) · Safety Inspection Checklist (compliance %) · Patient Intake · Medical History · Health Screening / Declaration (flag when any "yes") · Consent Form, controls only, no compliance claims
- ✅ Events & Bookings (7): Event Registration (ticket total) · RSVP (party size) · Appointment Booking · Venue / Room Reservation (hours × rate) · Volunteer Signup · Speaker / Sponsor Application · Post-Event Feedback (average)
- ✅ Hospitality (8): Guest Registration · Hotel Booking Request (nights × rate) · Guest Feedback (average) · Service Evaluation (score) · Special Requirements · Event Catering Request (guests × price per head) · Restaurant Reservation Request · Hospitality Complaint

### Milestone 2 follow-ups (2026-10-03)

- ✅ Form overview KPI cards match the design (dark title, ↗ link, icon · number · trend · caption)
- ✅ QR code for the form link (`uqr`, owner-approved): branded card (organisation name + logo / initials in the centre, form name, Formalie footer; Formalie branding without own subdomain) or plain; colours: form, brand, black, presets, any colour; PNG sizes and SVG
- ✅ Form language: main language of the form in Form settings (20 languages)
- ✅ Themes clickable everywhere: workspace themes open the editor, Formalie themes open read-only with "Duplicate to edit"

### Milestone 3, Education · Operations & IT · Finance & Legal ✅

- ✅ Education (7): Student Enrolment / Admission · Course Evaluation (average) · Quiz / Assessment (score from answers, pass / fail) · Scholarship Application (eligibility score) · Parent Consent / Permission Slip · Attendance Register (present count) · Academic Survey
- ✅ Operations & IT (9): IT Support Ticket (priority from impact × urgency) · Change Request (risk score) · Asset Check-out / Inventory · Maintenance / Work Order · Purchase Requisition (line totals, total) · Vendor / Supplier Registration · Site / Field Inspection Report (pass rate) · Delivery Confirmation / Proof of Delivery · Quality Control Checklist (pass rate, result)
- ✅ Finance & Legal (5): Loan / Credit Application (debt-to-income ratio, flat-rate monthly payment estimate, labelled as an estimate) · KYC / Identity Verification · Invoice Submission (subtotal, tax, total) · Insurance Claim (claim total) · NDA / Agreement Sign-off

### Milestone 4, Community & Other · Real Estate · Sales ✅

- ✅ Community & Other (4): Membership Application (fee) · Donation Form (gift + optional fee cover) · Petition · Poll / Voting Ballot
- ✅ Real Estate (8): Property Viewing Request · Tenant Application (income-to-rent ratio) · Rental Application (income-to-rent ratio) · Property Inspection (condition score) · Maintenance Request · Property Information · Landlord Information · Tenant Feedback (average)
- ✅ Sales (8): Lead Capture · Quote Request (total) · Sales Qualification (qualification score, e.g. budget / authority / need / timing) · Product Demo Request · Customer Discovery · Proposal Request · Order Request (total) · Sales Follow-up

### Milestone 5, Languages, polish, review

- ✅ **Categories first, own templates apart** (owner, 2026-10-03, decision 78): `/templates` lists Formalie's categories (Grid / Table: templates, with calculations / logic, forms made, responses, last used); a category opens its templates (`/templates/category/{key}`); the workspace's own templates under "Your templates" (`/templates/mine`); menu: six most used categories, All categories, Your templates; a template page links back to its category

- ✅ Template content (labels, options, help, page titles, consent / paragraph text, thank-you messages, text results) in all 20 languages, one dictionary per language (`shared/templates/messages/<code>.json`, decision 77); preview and new forms open in the person's language; keys, values, scores, logic and formulas unchanged
- ✅ Phone / desktop, dark, Arabic RTL checked on the categories page, a category, Your templates and a template in Arabic; skeletons from DataView; empty state for Your templates offers next steps; keyboard: cards and rows are links, actions are buttons
- ✅ End-of-phase review with the owner (2026-10-03: "all is good")

Total at launch: **84 templates in 11 categories** (a few names appear in two categories on purpose, framed for each, e.g. Lead Capture, Quote Request, Order, Maintenance). More later (owner: "just the tip of the iceberg"); the AI assistant (F19) can generate more.

---

## F10, Renderer, preview, share, embed, short links, SEO ✅

**Plan (2026-10-03, milestones):** **M1** public page core, public key per form, `/{formKey}/fill` + `/embed` server-rendered with SEO, `forms.*` host, secure server-side fetch, not found / not published / closed states, submit with one response per fill-in session (`Idempotency-Key`), thank-you or redirect, respondent language (`?lang`, browser language). **M2** save & resume, file uploads with progress, spam protection, embed auto-resize. **M3** Share card: access (password, invite-only, organisation-only, expiry, response limit, schedule), custom link, short links `/s/{code}`, embed code builder, SEO settings with link-card preview, preview page with device frames. **M4** form translations (questions in several languages + switcher), polish, review.

### Renderer

- ✅ One renderer for preview, public page and embed (submit hook, same rules as the API)
- ✅ Public form links (decided 2026-10-03; built M1 with a 10-character `public_key` per form): `https://{forms | subdomain}.formalie.com/{formKey}/fill` and `…/{formKey}/embed`, `forms.formalie.dev` / `forms.formalie.com` for workspaces without their own subdomain; `{formKey}` is the form's short public key (custom slug optional); helper `shared/utils/urls/public.ts`
- ✅ Public page server-rendered with SEO (title, description, image, canonical, noindex); `forms.*` host served without a workspace (tenant from the form key)
- ✅ Secure server-side fetch for server-rendered pages (internal route + server-only `NUXT_INTERNAL_TOKEN`)
- ✅ Closed / expired / not found / password-protected / response-limit states: not found (404), not published, closed, **expired (410) and not-open-yet** (availability dates, owner 2026-10-03), load error; password and response limit with the Share settings (M3)
- ✅ Multi-page with progress, **save and resume** (decision 87): autosave to a server draft, "Save and continue later" emails a 30-day resume link, the link restores answers and page, submitting closes the draft
- ✅ **File uploads** (decision 88): straight to storage through short-lived upload links with progress per file; answers keep references (drafts too); type / size / count / real-picture / no-program checks on both sides; files attached to one response, never public
- ✅ **Help guide** (owner, 2026-10-03, decision 86): Form settings → Help guide (off by default, rich editor in a window); a floating "?" on the form opens it in a chat-style panel
- ✅ **Accent header** (decision 86): quote-like header style; Events & bookings and Operations & IT designs use it instead of the side panel
- ✅ **Recognising respondents** (owner, 2026-10-03, decision 85): the respondent's own email (suggested, never someone else's), email only (ID option removed, owner); same → refused, near match → "different person?" + flagged possible duplicate; optional email verification with a code; masked hints only
- ✅ **Duplicate protection** (owner, 2026-10-03, decision 84): per session, per browser (with "for someone else" after confirming), exact same answers never twice, optional one response per answer (e.g. email); thank-you page: Fill in another · Close this page
- ✅ **Availability** (decision 84): open from / open until per form, set from the list menu or the overview; badge in table and grid
- ✅ **No duplicate submissions** (owner question 2026-10-03, see 03-DECISIONS → 68): the Submit button is busy and disabled from the first click; every fill-in session has its own submission id sent as an `Idempotency-Key`, the server keeps the first response for that key and answers repeats (double click, retry after a dropped connection, back button) with the same response id instead of a second response; a finished session can't submit again; optional "one response per person" (signed-in respondents by account, others by a signed cookie + email if the form asks for it); rate limits per form / IP
- ✅ **Spam protection** (decision 89): invisible proof-of-work challenge (no third-party captcha), hidden trap field, submission limits per address
- ✅ F11: show "Possible duplicate" on responses with a link to the earlier one; Not a duplicate (clears the flag) / Reject as duplicate (Rejected + tag "duplicate"); merging two responses is not offered (both stay as evidence)
- ✅ Thank-you page or redirect
- ✅ **In-app browser** (owner, 2026-10-03, decision 83): website, Terms and Data Privacy Policy open in a branded window over the form; answers stay
- ✅ **Page frame** (owner, 2026-10-03, decision 82): Designer → Page with four styles, Branded · Spotlight · Side panel · Minimal, tone, website link, quick facts; shown on the public link, the designer and Preview (not in embeds)
- ✅ **Preview page** `/forms/[id]/preview` (decision 98, 2026-10-04): the form in a desktop browser window, a tablet or a phone at real screen sizes (turned sideways too), scaled to fit; draft or live version; jump to any page or the thank-you screen; try it out, nothing is sent; phones show it full width; open from the overview, the form menu and the editor's quick preview; open to "Can view"
- ✅ **Changing the form language translates its text** in the same step (owner, 2026-10-04, decision 91, no second button): template text in all 20 languages, the creator’s own text kept (count shown), one undo
- ✅ **Form languages** (owner, 2026-10-03, see 03-DECISIONS → 73 and 99, built 2026-10-04): Form settings → More languages (dictionary fill on add, translation screen with progress, remove, a language the form offers can become the main one with nothing lost), switcher on the form, preview and editor preview; the form opens in its main language (owner 2026-10-04, not the browser's); `?lang=xx` forces one (shareable per-language links, embeds and QR codes); a language switcher when a form has several; translated questions / options / help / messages per language; the language is saved with each response; buttons, messages, dates, numbers and right-to-left follow it
- ✅ **Embed code** (decision 90): the Share card offers the ready `<iframe>` code, auto height (recommended) or fixed height, instead of a bare embed address; embed pages can be framed by other websites

### Share

- ✅ Custom link (slug availability), short link, QR code (PNG / SVG), copy buttons: custom link with live check (2026-10-04) · ✅ short link (2026-10-04) · ✅ QR code (form colour or black, PNG 512–2048 px / SVG) and copy buttons on the form overview (2026-10-03)
- ✅ Access: public, password, invite-only, organisation-only; expiry, response limit, schedule: Share tab (decision 92): anyone with the link / password (hashed, unlock cookie, tries limited), response limit (form full page), availability; ✅ invite-only (personal links, statuses, resend / revoke, one response each) and organisation-only (sign in on the portal, 2-minute pass, works on forms.*), decision 96
- ✅ People access: edit / view / responses (decision 97): workspace default + per-person level on the Share tab (under “Your team”, apart from “Answering the form”), enforced by the API; view only: overview + read-only preview, no editor (owner, 2026-10-04)
- ✅ Embed: iframe snippet with auto-resize, size options (M2), allowed websites + live preview (M3, decision 94)
- ✅ SEO settings with link-card preview (decision 95): title, description, image, hide from search engines; previews as link card and search result
- ✅ Short link redirect `/s/[code]` (decision 93): create / remove on the Share tab, 302 to the current link, visits counted, 404 page for unknown codes

---

### Milestone 4 review (2026-10-04) ✅

- ✅ Out-of-date translations marked: "Changed since translated" + "Still right", "N to check" per language; web addresses and email examples are not offered for translation
- ✅ Empty Trash removes only forms the person can edit (others stay, with a note); folder counts only count forms the person can see
- ✅ Public pages never show draft text: a never-published form's page title and description use only its name
- ✅ Image questions: the server takes the same picture types the form offers (a stray ".pdf" no longer blocks photos)
- ✅ Overview Share card shows all four access modes (invite-only and members-only were shown as public)
- ✅ Save and resume: "Save and continue later" works before anything is typed and saves what is on screen; saves run one at a time (no second draft on a slow network)
- ✅ Invitation emails: space separates emails too (text input with email keyboard), remove buttons have a focus ring and are off while busy
- ✅ "Opening your form…" after the right password until the questions arrive
- ✅ `/forms/open`: "This form isn't yours" only when it really isn't; other errors offer Retry
- ✅ Adding a language changes the form only after the dictionary fill succeeded
- ✅ One spam-check challenge, one submission (reserved while a submission runs)
- ✅ Upload picture previews are freed when a file is removed or fails
- ✅ Watchers on public pages belong to the page (no leftovers after leaving it)
- ✅ Checked clean: every English text exists in all 19 other languages, no left/right utilities or dashes in F10 files, no direct fetch in components, icon buttons named, access checks on every editor / share / template / lifecycle route

## F11, Responses ✅

**Plan (2026-10-04, milestones):** **M1** ✅ one response source for every page (decision 100), per-form Responses page with insights and slim charts, Summary per question, list, response panel, Responses page grouped by form. **M2** ✅ editing answers (with history), filters by answers and tags, bulk tags, possible-duplicate review. **M3** ✅ exports (XLSX / CSV / PDF) with progress and the Exports page. **M4** ✅ Folders workspace, polish and review (then stop for the owner's review).

- ✅ One response source (decision 100): real submissions + stable sample responses for seeded forms; overview, sidebar counts and form lists read from it (owner, 2026-10-04: "connect all the dots")
- ✅ Per-form responses `/forms/[id]/responses` (DataView, Table / Grid, columns from the form picked in "Columns" and remembered, ratings as slim bars)
- ✅ Insights: KPI cards with sparklines and trend, responses over time (daily / weekly), review status stacked bar (filters the list), channels, languages, period 7 d / 30 d / 90 d / 12 m
- ✅ Summary tab: every question summarised (choices as bars, rating average + distribution, numbers, latest text answers, calculated results)
- ✅ Responses page `/responses` grouped by form (decision 103): chart cards for all forms, forms as table / grid, a form opens its own responses; sidebar New / Reviewed / Approved / Rejected list, sort and highlight the forms with that status; old `/responses?form=` links forward
- ✅ Filters: status, channel, possible duplicates, date range, search (names, emails, answers, #number), tags, per question (choices, yes / no, ratings and scales; "Left empty"; decision 105)
- ✅ Response detail slide-over with next / previous (`J` / `K`), facts, answers grouped by likeness in a scroll-free chip row, files side by side in the shared viewer, possible-duplicate notice (Not a duplicate / Reject as duplicate)
- ✅ Status (new, reviewed, approved, rejected), tags, notes, history in the audit trail · editing answers in the panel (decision 104: pencil per answer, same control and rules as the form, Edited mark, audit)
- ✅ Bulk actions: set status, add / remove a tag (type one or pick one in use), delete (editors)
- ✅ M3 Export XLSX / CSV / PDF (all, filtered, selected) with progress and download, and the Exports page (Responses → Exports), decision 108
- ✅ M4 Polish and review: phone / tablet overflow sweep of every F11 page, Arabic (RTL) check with mirrored arrows, light and dark mode, keyboard (focus rings, colour swatches move focus with the arrow keys, Esc closes), empty and error states offer the next step (folder page: Try again)

### Landing pages library ✅ (owner request 2026-10-04: "add more pages, just like Themes on its menu"; decisions 106, 107)

The page people land on from a form's link (the theme's `frame` and page background) is its own library, like Themes, called Landing pages so it is never mixed up with a form's own pages.

- ✅ M1 Library: `PageDesign { id, name, source: system | saved | created, tokens { frame, page } }`; `/page-designs` API (list, insights, get, create, update, duplicate, delete) with audit; Resources → Landing pages (All · Formalie · Saved · Created) in the Themes table / grid format; landing page editor (style, tone, website link, quick facts, background; live preview on desktop / tablet / phone; Formalie's read-only with Duplicate to edit)
- ✅ M2 Ten page styles (branded · spotlight · side · minimal · banner · centred · headline · corporate · compact · floating) and 22 ready-made landing pages, one miniature in the library and the designer
- ✅ M3 In the designer and the theme editor: a "Landing pages" group to pick one (only the page changes, undoable), "Save landing page"; a theme and a landing page combine; Starting points and Your themes collapse like the other groups
- ✅ Renamed from "Pages" to "Landing pages" everywhere people see it (`/settings/landing-pages`)

### Folders workspace ✅ (owner request 2026-10-02, built here because the stats need response data; decision 109)

- ✅ Sidebar "Folders" group (design RESOURCES style): coloured folder icons, form count on the end, **+** to create, "Show all" when long
- ✅ Folder colour chosen when creating / editing a folder
- ✅ Folder page `/folders/[id]`: name + actions in the header, KPI cards (forms, published, responses, avg. completion, last activity), the folder's forms in DataView
- ✅ All folders `/folders`: every folder with the same stats, Table / Grid, sort

---

## F12, Data sources & databases ✅ (waiting for review)

**Goal:** organisations connect their own databases, send form data to them, and work with that data from the portal, browse it, query it and manage it, safely, with every action audited (owner request 2026-10-02). Comes after Responses (there is data to send) and before Option sets (dynamic lists read from these connections, F15e). Launch engines: MySQL, MariaDB, Oracle, PostgreSQL, SQL Server (`shared/utils/integrations/databases.ts`); built-in encrypted storage stays the default.

**Plan (2026-10-05, milestones):** **M1** ✅ Connections (per-engine settings, test, permissions guide, panel). **M2** ✅ Sending form data (response storage, tables, columns, deliveries, backfill). **M3** ✅ Database explorer (browsing, row changes in their own tables, export). **M4** ✅ Query editor (editor, run, results, safety, history, saved queries, export, format). **M5** ✅ Activity, polish and review (stopped for the owner's review).

### 1. Connections (Integrations → Data sources)

**M1 ✅ (2026-10-05; decision 111).** Owner: each engine's own connection properties, every operation covered, and always say which permissions to grant.

- ✅ Connections page (locked list format): two chart cards (activity with daily bars; connections by status, legend filters), DataView table / task card: engine mark, name, version, server, access, status (connected · needs attention · failing · disabled · not tested) with a missing-permission mark, uptime 30 days, operations, last checked; filters (status, engine, access), search, sort; sidebar Connections menu by status with counts
- ✅ Add connection, step by step (`/data-sources/connections/new`): database → server → sign in → security → access → name and test; every engine shows only its own settings from one catalogue (MySQL / MariaDB TLS modes, charset, time zone; PostgreSQL schema, sslmode, target session; SQL Server instance, SQL or Microsoft Entra sign-in incl. service principal, encrypt mandatory / strict, trust certificate, application intent; Oracle service name / SID / descriptor, schema owner, TCPS or native encryption); SSH tunnel, CA / client certificates (paste or load from a file), More options; checks per step on both sides; help beside each step
- ✅ Permissions guide: every operation Formalie performs (Formalie's tables, required · read and change the other tables, optional; decision 112) with the privilege per engine, and the grant statements written for the connection's own database, schemas and account (Copy / Copy all; Oracle 23ai or per-table); in the Access step and on the panel
- ✅ Test with live progress from Formalie's servers (reach, SSH, TLS, sign in, open the database, check every permission), clear error and fix per step (`FRM-DEST-1001…1011`), "Fix" jumps to the step; advice for unencrypted traffic and unchecked certificates; never changes data. Save takes its result; a failed test saves only after a confirm
- ✅ Credentials write-only (encrypted at rest, never returned, "Saved, leave empty to keep", last changed); blocked addresses (Formalie itself, cloud metadata); Formalie's outgoing addresses to allow, with Copy
- ✅ Connection panel: header with Test now / Edit / Enabled, fact tiles, Connection · Security · Permissions (last test per operation + statements) · Health (uptime 30 days, health checks every 5 minutes), Previous / Next (K / J); Edit (`/[id]/edit`, every step one click away), duplicate, disable / enable (confirm), delete (confirm; refused while forms send to it)
- ✅ Audit: `data.connection_created · updated · tested · duplicated · enabled · disabled · deleted`, `data.credentials_changed` (new area Data sources)

### 2. Sending form data (destinations)

**M2 ✅ (2026-10-05; decision 113).**

- ✅ Per form, "Where responses are stored" (form overview card): Formalie's encrypted storage (default) or one connection (one storage per form, decision 113); set up at `/forms/[id]/storage`, admins only
- ✅ Table: a new table from the form (named with the connection's prefix, in its response-table schema; CREATE TABLE shown before saving) or a table of theirs (needs Full access; tables listed per connection)
- ✅ Columns: from the questions' keys (renamable, answers can be left out; reserved words and length limits per engine) with per-engine types; an existing table is matched automatically (names, common aliases) with checks (response id needed, required columns, type warnings, repeats) and "Add a response id column"; extra facts (response number, respondent's email, review status); answers with several values as JSON or text, choices by value or label, files as secure links
- ✅ Write mode: a new row per response, or update-or-insert on a key column (unique key added when needed)
- ✅ Delivery in the background: status per response (sent · pending · failed · held while paused · not sent), retries with growing waits, retry one / retry all, pause / resume (held responses go out on resume)
- ✅ Send earlier responses (date range) with live progress; nothing is sent twice
- ✅ A form gains a question → "N new questions have no column" (card and panel) and "Add columns" with the SQL; nothing is ever dropped
- ✅ Data sources → Destinations (locked list format): chart cards (responses delivered, forms by delivery status), table / card, filters (status, connection, table kind), panel (Delivering switch, Send earlier responses, Retry failed, facts, deliveries, columns, new questions; J / K); connection panels list the forms storing there, and a connection in use can't be deleted
- ✅ Audit: `data.destination_created · updated · paused · resumed · removed`, `data.table_created`, `data.column_added`, `data.backfill_started`, `data.deliveries_retried`

### 3. Database explorer

**M3 part 1 ✅ (2026-10-05; decision 114): browsing.**

- ✅ Explorer per connection (`/data-sources/explorer?ds=&object=`): connection picker in the header; tree of schemas → tables (row counts, response tables marked) → columns (type, key), search tables and columns, keyboard navigation (Nuxt UI tree); on phones the tree opens from "Tables"
- ✅ Rows in DataView: search every column, filters for low-variety columns, sortable headers, Columns (first eight shown), Table / Grid (record cards), server paging, NULL dimmed; a row opens its panel (every column with type and full value, JSON laid out, copy a value or the row, open a referenced table, J / K)
- ✅ Structure tab: columns (type, can be empty, default, keys), indexes, relations (open the other table), the definition with Copy
- ✅ Export the table or the rows matching the search and filters to CSV / Excel with a percentage, one-time private download link; audit `data.table_exported`
- ✅ Skeletons for the tree and the table; empty states; a connection that isn't working shows its error with Try again and Check connection
- ✅ Response tables are read only here (they change through Formalie); what is visible follows the connection's access

**M3 part 2 ✅ (2026-10-05): changing data.**

- ✅ Add, change and delete rows of the organisation's own tables (Full access, primary key): a form built from the columns (the right control per type, empty is NULL, the key set automatically and never changed), checks per column type here and on the server, confirm before deleting; audit records which row, never its values
- ➖ Import CSV / Excel: built, then removed (owner 2026-10-05: not supported for now)
- ✅ Layout (owner 2026-10-05): the connection and tree take the sidebar's menu column on desktop (`useSidebarTakeover`; rail stays; back arrow to the menu and a button back to the tree; same width as the menu, drag to resize); the page keeps the full width; a slim one-line table strip; extra slim rows with column lines (DataView `dense`), table only (DataView `table-only`, no grid); phones, tablets and a folded sidebar open the same panel from "Tables"
- ✅ Export also as JSON (row objects, JSON columns parsed) and SQL INSERT statements for the connection's engine (`shared/utils/datasources/exportFormats.ts`); the tree keeps one table open at a time; the account avatar sits at the foot of the rail while the tree holds the menu column
- ✅ Structure changes on the organisation's own tables (Full access; never response tables or views): New table (columns, key, numbered automatically, defaults), add / change (rename, kind, size, can be empty, default) / delete columns, add / delete indexes, rename, empty (TRUNCATE) and delete (DROP) with the table's name typed to confirm; every dialog shows the exact statements per engine first (`shared/utils/datasources/ddl.ts`); a change that may lose data says so; audit `data.user_table_created` · `table_altered` · `table_truncated` · `table_dropped`

### 4. Query editor

- ✅ SQL editor (CodeMirror 6, owner-approved 2026-10-05) with the connection's SQL dialect, syntax colours from the theme, schema / table / column completion, several tabs (rename, close, kept per connection on the device), Format (Shift + Alt + F, built in, no package)
- ✅ Run the selection or the statement at the cursor (Ctrl / ⌘ + Enter), stop (Esc), results grid built for query output (row numbers, resizable columns, NULL dimmed, right-click copy) with paging, run time, rows affected, the database's problem marking its line with Go to line
- ✅ Read only connections run only reading statements; a changing statement says what it will do (rows, tables) and needs a confirm; never Formalie's response tables; structure changes need Full access
- ✅ Parameters (`:name` → input boxes), query history, saved queries (personal or shared with the workspace; Ctrl / ⌘ + S; side panel tab and the Saved queries page with chart cards, table and cards), export results (this page or up to 5,000 rows; CSV / Excel / JSON)
- ➖ Use a saved read query as a dynamic option list source: moved to F15e (option sets); on the dashboard: F21
- ✅ Run all (Ctrl / ⌘ + Shift + Enter): every statement of the tab in order, stopping at the first problem or a declined confirm; a result tab per statement (status, its own paging and export); the problem's line marked
- ✅ Lazy tree for very large databases: table names first (up to 500, server search beyond that), a table's columns load when it is opened or named in the editor (`GET …/explorer/columns`), cached per connection

### 5. Other database operations

- ✅ Insert, edit and delete rows from the table view (form generated from the columns, type-checked, confirm on delete; read + write connections only)
- ✅ Create a table from a form; add columns for new fields (preview + confirm): done in M2 (response storage: table from the form, Add columns, the exact SQL first)
- ➖ Import CSV / XLSX into a table: not supported for now (owner 2026-10-05)
- ✅ Activity (M5): everything on the connections from the audit trail (queries, row and structure changes, exports, response storage, connection events), two chart cards (30 days with daily bars; by kind with a legend that filters), the list with connection, kind and result filters and a date range, each event opens the audit trail's panel; Exports in the menu opens Activity filtered to exports (imports aren't supported for now)
- ➖ Scheduled exports and saved-query snapshots: later, after F21 (needs the backend's job runner)

### 6. Safety (enforced by the backend, visible in the UI)

- ✅ Queries and data changes run only on the server, through the connection's pool, with statement time-outs and row caps, never from the browser: every call goes through the API; the rules are in API-CONTRACT (paging in the database, count capped at 10,000, 5 s per statement, exports up to 5,000 rows) for the backend to enforce
- ✅ Every query, row change, structure change and export is recorded in the audit trail (who, connection, statement, rows affected, duration; never result values)
- ➖ Permissions per role (view explorer · run read queries · run changing queries · manage connections · send form data): moved to F22; until then admins only
- ✅ No credentials or result data in logs (the audit trail keeps statements and counts, never values); results never stored in the browser (only the tabs' SQL text); rate limits are the backend's (in API-CONTRACT)
- ✅ Clear wording: the Data sources pages promise controls (encryption, audit, least privilege), never certifications

### 7. Navigation, API and docs

- ✅ Own rail area (owner, 2026-10-02): Data sources icon under the workspace button, with its own menu, Overview · Connections · Database explorer · Query editor · Saved queries · Destinations · Exports · Activity; every page live since M5 (`/data-sources/**`), old `/integrations/destinations` redirects; Integrations keeps Webhooks · API keys
- ✅ Mock first, then API: the mock covers `/datasources` (CRUD, test, permissions), `/datasources/{id}/explorer/*` (tables, structure, rows with insert / update / delete, facets, exports, structure changes), `/datasources/{id}/query` (+ export, history), `/saved-queries`, `/datasources/activity/insights` and the destinations routes; error codes `FRM-DEST-1001…1027`; API-CONTRACT is the backend's spec

---

## F13, API service & integrations ✅

**Goal:** turn any form into an API so organisations collect data from every side, **links, embeds and API**, all landing in the same storage / destinations (owner request 2026-10-02: "this option is gold"). An entire system of its own: its own rail area and menu, its own analytics, and later its own dashboard (F21). In the backend the API service runs as its own service, separate from form operations.

**Plan (2026-10-06, milestones):** **M1** ✅ Services and endpoints. **M2** ✅ Tokens and headers, plus the mock public API (Postman) (test and live tokens from the start, owner-confirmed 2026-10-06). **M3** ✅ Access rules and rate limits. **M4** ✅ Request logs, analytics and the API service overview in the dashboard style. **M5** ✅ Docs and testing (try-it console, Test button, files). **M6** ✅ Webhooks and Formalie's own API keys (management API).

### Addresses (decided 2026-10-03, see 03-DECISIONS → 61)

- Base URL: development `https://api.formalie.dev/` · production `https://api.formalie.com/`
- Endpoint: `https://api.formalie.dev/{apiKey}/{endpoint}` (+ `/{recordId}` for GET one · PUT · DELETE), e.g. `https://api.formalie.dev/k7Qm2xP9aZ/register-account`
- `apiKey` = a short random public handle per organisation (10 letters / digits), **not** the tenant or organisation id and **not** encrypted: it only routes the call; the token, headers and access rules decide who may call. Rotatable (old key keeps working for a grace period).
- Endpoint names: lower-case words with hyphens, 3–64 characters, unique per organisation
- Helper: `shared/utils/urls/public.ts` (`apiEndpointUrl`, `API_KEY_PATTERN`, `ENDPOINT_PATTERN`, `API_METHODS`)

### 1. Area and navigation

- ✅ Own rail area under Data sources with its own menu: Overview · Services · Endpoints · Tokens & headers · Access rules · Request logs · Analytics · Docs & testing, placeholder pages (`/api-service/**`), overview shows the three channels (link · embed · API) and an example endpoint

### 2. Services (containers)

- ✅ Services page (rule 21): two chart cards (calls in 30 days with daily bars; services by status, the legend filters), DataView table / cards (name, status, endpoints, methods, calls with sparkline, errors, last call); new / edit (dialog), duplicate (copies its endpoints, switched off), delete (confirm, names how many endpoints go too); panel with fact tiles, calls per day and its endpoints
- ✅ Switch a whole service on / off in one click (row menu, panel switch); its endpoints show "Service switched off"; audited `api.service_enabled / _disabled`

### 3. Endpoints (one form each; as many as needed)

- ✅ Create an endpoint from a form (`/api-service/endpoints/new`): form (published only) → name and service (new service in place) → methods → questions → review; address preview and an example call beside it; edit at `/api-service/endpoints/{id}/edit`. Authentication and access rules are set per organisation in M2 / M3 (the review says so)
- ✅ Methods: **GET, POST, PUT, DELETE only** (for now); each switchable per endpoint
- ✅ POST / PUT: choose the questions accepted and which are required; the form's required questions are always accepted and required; read-only, calculated, signature and payment questions are refused (with the reason shown); file questions are accepted since M5 (upload step); `shared/utils/apiService/endpoints.ts` (wizard and server alike)
- ✅ GET: choose the questions returned and the ones it can filter by (choices, dates, numbers, short text, email), page size up to 100; never more than the chosen questions
- ✅ DELETE / PUT by record id; soft delete with the response kept in the audit trail
- ✅ Where data goes: the form's storage / destinations (built-in storage or a Data source, F12), the same pipeline as form submissions (API responses are stored with the form's other responses)
- ✅ Switch each endpoint on / off (row menu, panel switch); pin a form version or follow the latest published one; "Test" button in the panel opens the try-it console (M5)
- ✅ Example request and answer (JSON) per method, generated from the chosen questions, with Copy (panel and wizard)

### 4. Authentication and headers

- ✅ Bearer tokens (long-lived, shown once, stored as a hash with a 4-character preview, prefixes `formalie_live_` / `formalie_test_`) or client id + secret → short-lived tokens from `POST /{apiKey}/token` (5 to 60 minutes); live and test from the start (test never touches real responses)
- ✅ Rotate (the old secret works for 0 h, 24 h or 7 days), revoke, delete once revoked or expired; expiry (30 / 90 / 365 days, a date, never), "expiring" 14 days before; scopes per service / endpoint / method; last used; tokens unused for 90 days flagged. Tokens & headers page (rule 21) with the token panel
- ✅ Optional request signing per token: `X-Formalie-Timestamp` + `X-Formalie-Signature: sha256=HMAC(secret, "{timestamp}.{METHOD}.{path}.{body}")`, refused after 5 minutes
- ✅ Headers: `Authorization: Bearer …` · `Content-Type: application/json` · optional `Formalie-Key` (a POST with the same key answers the first response again; owner named it, 2026-10-06) · custom required headers per endpoint (name + value, up to 5, in the endpoint wizard; Headers view lists them). `X-Formalie-Destination` dropped: a form has one storage (decision 113)
- ✅ No tenant / organisation id headers: the address key and the token identify the organisation (a token only works under its own organisation's key); the address key rotates with a grace period (Headers view)
- ✅ Answers always JSON: `{ data, meta }` or `{ error: { code, message, details } }`, codes `FRM-API-1006…1014` (+ `FRM-RESP-1001` for the form's rules). Mock public API answers real calls (`server/mock/publicApi.ts`; Postman: see 02-DEV-ENVIRONMENT → API service from Postman)

### 5. Access rules (allow / block lists)

- ✅ Allow and block rules by IP address / range (IPv4 and IPv6), website domain (Origin / Referer, browser callers; `*.example.com`), country and region (continent); several values per rule; on / off; note; Access rules page (rule 21: chart cards, DataView, rule panel); shared rules `shared/utils/apiService/access.ts`
- ✅ For all endpoints, one service or one endpoint; a block always wins; once allow rules apply, a caller must match one; "Test a caller" (endpoint, IP, website, country → gets in or refused, and the rule that decided); rules made for a deleted service or endpoint go with it
- ✅ Rate limits per token, IP and endpoint (calls per minute, or none; Rate limits view): over a limit `429` (`FRM-GEN-1029`) with `Retry-After`; answers carry `X-RateLimit-Limit` / `X-RateLimit-Remaining`. The mock public API applies rules and limits (Postman: `X-Forwarded-For` and `X-Debug-Country` act as the caller's IP and country, mock only)

### 6. Logs and analytics

- ✅ Request logs (rule 21): time, call (method + address), result (2xx / 4xx / 5xx), error code, time taken, endpoint, token (never the token itself), caller IP and country, client, request id; filters (endpoint, result, method, live / test), date range (last 7 days by default), search, sort; panel with headers (secrets masked) and, when "Keep bodies" is on (1, 7 or 30 days), request and answer bodies with personal answers masked; Download (CSV of the calls in view, up to 1,000). Every call to the mock public API is logged
- ✅ Analytics (separate from the form analytics), in the dashboard style: last 7 / 30 days; KPI cards (calls, error share, typical answer time p50, slowest 5 % p95, tokens used) with the change; traffic flow chart (calls vs calls that worked) beside one endpoint at a time; busiest endpoints, busiest tokens, countries, methods. The API service Overview rebuilt the same way (KPI cards, traffic, endpoint overview, recent calls, the three channels, shortcuts)
- ➖ Own dashboard: in F21 (Forms, Data sources and API service each get one)

### 7. Docs and testing

- ✅ Docs & testing page (`/api-service/docs`): pick a service in the header, its endpoints at the side (a sliding row on phones); per method the body table (key, type, required, allowed values), query options, code (curl, JavaScript, Python, PHP, C#, the choice remembered, Copy) and the answer; a shared guide (address, tokens, `Formalie-Key`, files, signed calls, error codes); Download OpenAPI 3.1 per service (`shared/utils/apiService/snippets.ts`)
- ✅ Try-it console (`ApiDocsConsole`, from each method and the endpoint panel's Test button): every real check with a console test token that lives 60 s, nothing stored; status, time taken, rate-limit headers and the JSON (`POST /api-endpoints/{id}/try`)
- ✅ Examples and the console use the form's real answer values (choices, not `option_1`) and fill in a fresh `Formalie-Key` for each new record, with "keep this key" to see a retry (owner, 2026-10-06); every accepted question type's example passes the form's own checks (test)
- ✅ Files through the API (owner-agreed 2026-10-06): upload first to `POST {apiKey}/{endpoint}/files?field={question}` (multipart; same type, size and scan checks as the form page) → a file reference, then send the reference in the JSON; file questions then become acceptable in the wizard

### 8. Safety and audit

- ✅ Every change to services, endpoints, tokens and rules is audited (`api.*`); tokens shown again only after the password (owner 2026-10-06, replaces "never shown again")
- ✅ Request size limits (1 MB), no secrets in logs (tokens masked), bodies only when switched on
- ⬜ Backend: TLS only; CORS for apps that call straight from a web browser (not in the mock; server apps, mobile apps and Postman are not affected)
- ➖ Permissions per role: in F22 (admins only until then)

### 9. Integrations (moved here from F15, owner 2026-10-03)

- ✅ Menu entry in the API service area: Webhooks (API keys folded into tokens, 2026-10-06; old links redirect)
- ✅ Webhooks (`/api-service/webhooks`, rule 21; view switch Webhooks | Deliveries): name, HTTPS address (public hosts only; `http://localhost` while developing), events (new response, response changed, status changed, response deleted), every form or chosen ones; signing secret shown once, new secret; Send a test (the receiver's answer in the panel); every delivery signed (`X-Formalie-Timestamp`, `X-Formalie-Signature: sha256=HMAC(secret, "{timestamp}.{body}")`, `X-Formalie-Event`, `X-Formalie-Delivery`), retried after 1, 5, 15, 60 and 360 minutes, paused by itself after 20 failures in a row; delivery log with tries, request (personal answers masked), answer, Send again / Retry now; signature check code (Node.js, Python, PHP). The mock really calls the address
- ✅ API keys (`/api-service/api-keys`, rule 21): name, permissions (read forms, open / close forms, read / change responses, read webhooks, read the audit trail), expiry; shown once (`formalie_key_…`), edit, revoke, delete once revoked or expired; calls per day, last used and from where. Mock management API at `{base}/v1/…` (forms, a form's responses, one response: read, change status and tags, delete; webhooks; audit trail), permissions checked, changes audited as the key, webhooks fire

### M7. Owner review (2026-10-06)

- ✅ Guided setup: service → endpoint → token → access rules (optional) → test → go live; each dialog explains what it is and what comes next (steps); no endpoint without a service; new endpoints start not live (test tokens can already call them)
- ✅ Secrets visible again: tokens, API keys and webhook secrets masked in their panels, shown after confirming the password, audited
- ✅ Access rules: chips for IPs and domains with checks as you type; anonymous networks rule (VPN, proxy, Tor, hosting); how country detection works with VPNs (docs)
- ✅ Every failure answers with a clear code (matrix checked with curl, listed in README)
- ✅ Docs & testing redesign; Try it in a drawer; method colours everywhere (GET green, POST violet, PUT amber, DELETE red)
- ✅ README: API service test cases

### Owner follow-ups 2026-10-08

- ✅ New tokens named "{Service} Token" (unique with 2, 3 …), for one endpoint or the whole service
- ✅ An endpoint's checklist counts only tokens made for it or its service; tokens for every endpoint are named apart, never shown as assigned
- ✅ Choices by label (owner tested with lists): records return option labels; POST, PUT and filters accept a label or a value (`shared/utils/apiService/choices.ts`)
- ✅ Connections in every detail panel (service, endpoint, token, access rule): service, form, endpoints, tokens (made for it / its service / every endpoint), access rules, each a link (`GET /api-service/connections`)

### 10. API (mock first)

- ✅ Portal management API: `/api-services` · `/api-services/{id}/endpoints` · `/api-tokens` · `/api-access-rules` · `/api-logs` · `/api-analytics`; error codes `FRM-API-*`; contract updated

---

## F14, Settings ✅

**Goal:** one place where workspace admins control everything about their workspace. Each section is its own page under `/settings/*`, with a section menu (sidebar list on desktop, select on phones), unsaved-changes warning and a save bar.

**Plan (2026-10-06, milestones):** **M1** ✅ Settings frame, Company, Branding, Language and region. **M2** ✅ Organisation data (departments, job titles, teams and locations; builder reads them). **M3** ✅ Sign-in and security. **M4** ✅ Notifications and emails (incl. emailing responses to the team and outside addresses). **M5** ✅ Privacy, data and form defaults. **M6** ✅ Appearance. **M7** ✅ Address, domain and organisations. Billing moved to F23.

### Settings shell

- ✅ `/settings` overview: the workspace at a glance (logo, name, address), setup ring with the next step, section cards in groups with a live one-line status ("3 of 8 details filled in") or "Soon"
- ✅ Section navigation: the Settings navigator in the menu column (sidebar takeover) on desktop, a Sections side panel elsewhere; breadcrumbs; Save / Discard in the header with Ctrl / ⌘ + S; unsaved-changes mark and leave warning (also on closing the tab)
- ✅ Search inside settings (the navigator's search box) and from the command palette (admins)

### Company & branding

- ✅ Company profile: legal name, display name, industry, size, website, address, country, tax / registration number, support email and phone, with a live "where it shows" card
- ✅ Branding: logo (light + dark), favicon, brand colour, sign-in page image and message; live preview of the workspace sign-in page (light / dark); the real sign-in page and the browser tab follow

### Appearance: the workspace's own look of the portal (owner request 2026-10-05)

Organisations run on different brand colours, so each workspace can change the look and feel of the whole application (not only its forms). One Appearance page with a live preview of the portal (sidebar, header, a list page, a dialog) on desktop / tablet / phone, ready-made appearance presets plus full control, "Reset to Formalie", and every change in the audit trail.

- ✅ **Colours:** primary (black and white, brand colour with a contrast check, or a palette colour; it drives buttons, links, rings, charts) and the neutral palette (zinc, slate, gray, neutral, stone); status colours never change
- ✅ **Background:** page background (plain, soft tint), corner radius (square → very round); gradients and border styles left out to keep the design calm
- ✅ **Rail:** light or dark (the brand colour shows through the primary accents)
- ✅ **Menu (sidebar):** light or dark, count badges on / off (its width stays adjustable by dragging)
- ✅ **Header (navbar):** show / hide breadcrumbs and the search field (search stays on Ctrl / ⌘ + K)
- ✅ **Footer:** show / hide
- ✅ **Main body:** spacing (compact / comfortable), content width (full / centred), font family and text size from a safe set; presets, live preview on the real portal and Reset to Formalie
- ⬜ **Light and dark:** separate colours per mode and a workspace default mode (later; today one look serves both modes and each person switches light / dark, rule 9)
- ✅ Applied app-wide through Nuxt UI theme tokens (`app.config` / CSS variables at runtime), never per-page styling; the first-load screen (Formalie mark, bar and dots) uses the saved look too (2026-10-07)
- ✅ Files and messages follow it too: the PDF export report (Appearance colour, 2026-10-07), email templates and the sign-in page (Branding)
- ✅ Who may change it: workspace owners / admins (Roles & access, F22, refines this)

### Organisation data (owner, 2026-10-03, decision 79)

Every workspace sets up its own reference data here; the builder, field access and logic only ever offer what the workspace has (no built-in samples once Settings exist), with an empty state that links straight to the right settings page.

- ✅ **Departments:** create, rename, merge (people and field restrictions move), archive / restore (forms keep them, flagged), delete when unused; members per department; import from CSV or pasted names with a preview
- ✅ **Job titles:** the workspace's own list (separate from the permission roles of F22); people can hold several; a Field access choice of their own
- ➖ **Teams, locations / sites, cost centres:** removed (owner, 2026-10-07: not collaborative; access per form in Share settings)
- ✅ **Lists (option sets):** reachable from Settings (navigator link) as well as Resources → Option sets; their kinds stay F15
- ✅ Builder pickers read these live: field access (departments, job titles, roles, people) with an empty state linking to Settings; removed / archived entries are flagged on forms that still use them (choice fields "from a list" and logic conditions on people's departments come with F15 / F22)
- ✅ Mock: `/directory` serves the workspace's own departments and job titles (`orgStore`), no fixed samples

### Domain & workspace address

- ✅ Workspace subdomain (change with availability check and typed confirmation; the old one keeps leading here for 90 days)
- ➖ Custom domain: removed for now (owner, 2026-10-07: the subdomain is enough)
- ➖ Custom short-link domain: not for now

### Organisations

- ➖ Several organisations per workspace: removed (owner, 2026-10-07: one organisation, Company covers it)
- ➖ Organisation switcher: removed with organisations

### Authentication

- ✅ Sign-in methods: enable / disable email + password, Google, Microsoft, Apple, Facebook, only enabled ones appear on the workspace sign-in page (at least one; turning off email and password asks first; live sign-in page preview, also on Branding)
- ⬜ Single sign-on: SAML / OIDC set-up (metadata, certificates, test sign-in), later
- ✅ One-time code policy: email always, text message optional (off for new workspaces), expiry 5 / 10 / 15 min, wrong tries 3 / 5 / 10 (no authenticator app, owner 2026-10-07)
- ✅ Multi-factor authentication: always on for everyone (every sign-in asks for a code), shown as such
- ✅ Allowed email domains (optional; sign-in checks them now, invites in F22); your own domain must stay on the list

### Security

- ✅ Password rules (length, character types, reuse, expiry) with a "try a password" check; the reset page uses the workspace's rules; an expired password leads from sign-in to setting a new one
- ✅ Session timeout (idle, default 60 min, a warning below 1 hour) and maximum session length, checked on every request; who is signed in now, sign out one or everyone else
- ✅ IP allowlist (IPv4 / IPv6, CIDR ranges, your address with one click to add it; refuses to lock you out)
- ✅ Security events overview (sign-ins of the last 14 days, failed, blocked, locked codes, latest attempts), links to audit trail

### Localisation

- ✅ Default language, timezone, date and number format, first day of week, currency, with a live "how things will look" card; applied across the portal (useFormat)
- ✅ Languages offered on public forms (form language pickers only offer these)

### Notifications & email templates

- ✅ Which events notify whom (new response, possible duplicate, form full, form closing, export ready, webhook failing, sign-in blocked): in the app and / or email, admins / everyone / chosen people, optional daily summary; the bell shows a live feed with unread count
- ✅ Email templates (sign-in code, password reset, invitation, new response, respondent copy, notification, daily summary) with placeholders, live preview, test send, per language; a sent log until a mail service is connected
- ✅ Sender name, reply-to address and a footer line (custom sending domain later)
- ✅ Response emails per form (owner request): new responses to team members and outside addresses (personal answers masked unless allowed), a copy for the respondent

### Privacy & data

- ✅ Data retention per form / default (auto-delete responses after N days), with a preview of what a limit removes and a confirmation
- ✅ Consent line above Submit and the organisation's privacy notice link in every public form's footer
- ✅ Data requests: find a person's responses by email, export them (JSON) or delete them all (typed confirmation, audited)
- ⬜ Data residency / storage region (if offered by the plan): with the plans in F23

### Themes & form defaults

- ✅ Themes library (created in the designer, F8): list, rename, delete done in F8; the theme new forms start with is set in Form defaults
- ✅ Form defaults: progress bar, save and resume, field icons, label position, theme, thank-you text, response-email team, allowed embed websites (embed size stays per embed code)

### Billing & subscription (moved to F23 Platform admin, owner 2026-10-06)

- ⬜ Current plan, usage against limits (forms, responses per month, seats, destinations)
- ⬜ Upgrade / change plan, payment method, invoices
- ⬜ Plan-limit messages wherever a limit is hit (FRM-PLAN-1001 / 1002)

---

## F15, Option sets & payments 🟡

### Option sets (reusable choice lists)

**Plan (2026-10-07, milestones):** **M1** ✅ List manager (F15a: Option sets page in the list format, list editor with items, values, retire, reorder, bulk paste, CSV / Excel import with column mapping, translations, used in, update forms). **M2** ✅ Lists with levels (F15c, brought forward by the owner 2026-10-07). **M3** Large lists and search as you type (F15b). **M4** Details and auto-fill (F15d). **M5** Dynamic lists (F15e). **M6** Payments.

Full plan: [docs/OPTION-LISTS.md](docs/OPTION-LISTS.md) (owner request 2026-10-02). Simple saved lists already exist (F7).

- ✅ **F15a List manager:** Option sets page (locked list format), create, rename, duplicate, delete (asks first, says how many forms use it; forms keep their copies)
- ✅ Items: add, edit, retire, bulk paste, import CSV / XLSX with column mapping and preview, reorder (drag + keyboard), values vs labels, scores, translations
- ✅ "Used in" list of forms and fields, up-to-date marks, Update forms (drafts, with translations); the builder flags a changed list
- ✅ **F15c Lists with levels (M2):** up to 4 named levels (owner 2026-10-07: more becomes a mess) (Country → Region → City, Product → Category → Type → Brand); the editor edits one level at a time with the option above (searchable), a filter by it and "N under it" to go down; import by path (one column per level); the builder Lists tab shows plain or levels with the chain and adds one field per level, with One / Several chosen per level; each level's settings show the chain and switch one / several; in the form a level opens only with what is under the choice above and stays closed (not required) when nothing matches; changing a choice clears what no longer fits; the server checks the same
  - ✅ Refined after owner tests (2026-10-07 / 08): at most 4 levels; added by click or drag with nothing to choose, each level set in the right panel (One / Several, Required; plain lists get Show as); the editor canvas behaves as the form (a lower level locked with "Choose … first", only what is under the choice); a chain is one block (delete or duplicate all levels together)
  - ✅ Import and Paste ask what a row is (one option or a path); a file shaped like levels is spotted and creates the levels from its headers; pasted headers detected; List type switch and "How lists work" guide in the editor
  - ✅ API service: levels say what they depend on (`depends_on`, option `parent`), examples follow the levels, POST skips closed levels, PUT checks and clears levels
- ✅ **F15b Large lists + search as you type (M3):** dropdowns and multi-selects search as you type above 50 options (or switched on / off per field); on the public form page lists above 300 options stay on the server and come 50 at a time as people type (`GET /public/forms/{key}/options`, accents and case ignored, starting matches first); long lists drawn as they scroll; the builder shows a summary of a long list's options; a form field may hold up to 20,000 options like a list
- ✅ **F15d Details + auto-fill (M4):** lists get up to 10 detail columns (Details card; per option a Details button; import maps columns to details); fields from a list copy the details; field settings "Fill other fields" maps each detail to a question, locked by default (people can't change it); the logic engine fills in the browser and on the server alike, so a locked value can't be faked; an unlocked field is filled only while empty or still holding a filled-in value
  - ⬜ Details in formulas and logic conditions (later)
- ➖ **F15e Dynamic lists:** dropped (owner 2026-10-08: lists are kept up to date by importing; no live sources)
- ⬜ Public option lookups for respondents (rate limited, published lists only); answers store value + label (+ path)

### Destinations (where responses go)

- Moved to **F12, Data sources & databases** (connections, sending form data, explorer, query editor, other database operations).

### Payments (Payment field, shown as "soon" in the builder until then)

- ⬜ Payment providers per workspace (connect with the provider's own sign-in; e.g. Stripe, PayPal, Adyen, Mollie, Razorpay, Flutterwave, Paystack, global and regional), test / live mode
- ⬜ Payment field: fixed amount, amount from a choice, or **calculated** (formula, order totals, fees); currency; optional tax and fee lines; one-off payments first (subscriptions later)
- ⬜ Card details never touch Formalie: the provider's secure checkout / hosted fields; we keep only the payment status, reference and amount
- ⬜ Response shows paid / pending / failed / refunded; receipts by email; refunds from the response (audited); webhooks from the provider confirm payment before the response counts as complete

### Webhooks, API keys, other integrations

- Moved to **F13, API service & integrations** (owner, 2026-10-03: integrations belong to the API service).

---

## F16, Profile ⬜

- ⬜ My profile (name, photo, language, timezone)
- ⬜ Change password
- ⬜ Authenticator app (QR, recovery codes), SMS number
- ⬜ Sessions and devices (see and sign out)

---

## F17, Users ⬜

- ⬜ Users list (DataView), invite by email with role, resend / revoke invites
- ⬜ Enable / disable, reset password or MFA
- ⬜ Team avatars + "Invite member" in the header (design reference)

---

## F18, Analytics ✅ (brought forward by the owner, 2026-10-05; waiting for review)

- ✅ Analytics page in the design's dashboard style (`/analytics`, Forms menu): five KPI cards (views, started, completed, completion rate, time to fill in) with their change against the period before; conversion overview (started vs completed as the design's flow chart, hatched gap = left without finishing, Daily / Weekly / Monthly, tooltip with the completion rate and its change); form overview card (‹ form ›, completion bar, "Where people stop" timeline with links to the builder)
- ✅ Per form: views, starts, completions, completion rate, median time; DataView table and cards (rule 21) with the biggest stop and a 30-day sparkline; a row opens the panel (fact tiles, funnel, pages and questions: reached, answered, left, time; Previous / Next)
- ✅ Drop-off per page and field (`GET /analytics/forms/{id}/funnel`)
- ✅ Per-question charts: Responses → Insights (linked from Analytics as "Answers per question"); NPS score with detractors / passives / promoters on every 0 to 10 question
- ✅ Date range (in the address, last 30 days by default, up to a year) and Download as CSV (counts only, formula-safe cells)
- ✅ Mock first: `/analytics/overview`, `/analytics/forms`, `/analytics/forms/{id}/funnel`; completions, days, channels and times come from the response data, views / starts / stops are stable estimates until the backend counts the fill-in page's events; contract updated

---

## F19, AI assistant 🟡

**Goal:** an assistant built into Formalie that makes work easier, creating forms and templates, analysing responses, summarising, translating and more (owner idea 2026-10-03). Own rail area and menu; also available in context (builder, templates, responses). People stay in control: the assistant proposes, a person reviews and applies; nothing is published or sent by the assistant on its own.

### 1. Area and navigation

- ✅ Own rail area (sparkles icon) with its own menu: Overview · Create a form · Template ideas · Response analysis · Insights & summaries · Translations · History · Settings & usage, placeholder pages (`/ai/**`)

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
- ⬜ Model / provider choice is a backend decision (documented when F19 starts); data processing terms shown, controls, not certifications

---

## F20, Live collaboration (optional) ⬜

- ⬜ Presence, cursors and selections in the builder
- ⬜ Conflict-free editing
- ⬜ Comments on fields (later)

---

## F21, Dashboard ⬜

- ⬜ Separate dashboards for **Forms**, **Data sources** and **API service** (owner, 2026-10-02), plus the workspace overview

**Goal:** the workspace home, built after everything else so it shows what matters (design reference 2). Replaces the Forms redirect on `/` once done.

**Not replaced by Analytics or the Data sources overview** (owner, 2026-10-05): F18 Analytics is the forms' analysis page and the Data sources overview is that area's landing page; the dashboards here are still built, near the end, as planned. They may reuse `ChartsKpi`, `ChartsFlow` and the analytics endpoints.

- ⬜ KPI cards with trend vs previous period (active forms, responses, completion rate, pending reviews, overdue / closing soon)
- ⬜ Date range + Daily / Weekly / Monthly / Yearly switch
- ⬜ Responses over time chart with tooltip
- ⬜ Top forms / form overview card with progress
- ⬜ Recent responses table (DataView) and activity timeline
- ⬜ Filters (organisation, folder, owner)
- ⬜ Empty state for new workspaces (links to onboarding / first form)
- ⬜ Dashboard entry in the sidebar MAIN MENU (first item, as in the design)

---

## F22, Roles & access ⬜ (last)

- ⬜ Roles and permissions editor (permission catalogue, custom roles)
- ⬜ Role assignment per user and per organisation; form-level access
- ⬜ Access overview ("who can see what")
- ⬜ Permission to view and export the audit trail (`audit.read`, `audit.export`)
- ⬜ Data sources permissions (from F12): view the explorer · change rows and structure · run read queries · run changing queries · manage connections · send form data to a database; until then admins only

## F23, Platform admin (super admin) ⬜

The Formalie team's own console (owner, 2026-10-03: "a place for me to manage everything"), separate from any workspace, on its own host (`admin.formalie.com`), signed in with platform staff accounts and strong second factor; every action audited.

### Platform settings

- ⬜ **Legal links** on every public form: Terms and Data Privacy Policy URLs (already served by the API as platform settings with the app config as fallback, `PublicForm.legal`, mock `server/mock/data/platformStore.ts`); change once, applies to every form without a redeploy
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
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
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
| 2026-10-02 | Social providers on the first signup; more methods enabled later per workspace                                                                                                                                                                                                                                                                                    | F3 / F14                                                                          | ✅ (F3, sign-in methods per workspace in F14 M3) |
| 2026-10-02 | Provider buttons on one row with a "Sign up with" caption                                                                                                                                                                                                                                                                                                         | F3                                                                                | ✅         |
| 2026-10-02 | Settings as its own detailed phase; Dashboard after everything, just before RBAC                                                                                                                                                                                                                                                                                  | F14 / F21                                                                         | ✅         |
| 2026-10-02 | Audit trail early (its own phase after sign-in), not last                                                                                                                                                                                                                                                                                                         | F4                                                                                | ✅         |
| 2026-10-02 | Use "Email address" (not "Work email") so any email provider is welcome                                                                                                                                                                                                                                                                                           | F3                                                                                | ✅         |
| 2026-10-02 | Sidebar: chevron and count badges on the right; counts on items that have them                                                                                                                                                                                                                                                                                    | F1                                                                                | ✅         |
| 2026-10-02 | Don't expire sessions so soon, at least 1 hour when idle                                                                                                                                                                                                                                                                                                         | F3 / F14                                                                          | ✅         |
| 2026-10-02 | Loading feedback everywhere: page loading, progress, skeletons, top bar, busy buttons                                                                                                                                                                                                                                                                             | F2 / all                                                                          | ✅         |
| 2026-10-02 | In-page loading bar (left-to-right sweep) when moving between pages, not only on reload                                                                                                                                                                                                                                                                           | F2 / all                                                                          | ✅         |
| 2026-10-02 | Design images are style, not features, follow the look exactly, don’t copy widgets                                                                                                                                                                                                                                                                               | all                                                                               | ✅         |
| 2026-10-02 | New form: richer Blank tab (live mini preview + what you get), form details card, Continue button under every tab                                                                                                                                                                                                                                                 | F6                                                                                | ✅         |
| 2026-10-02 | Folders in the sidebar with counts, folder pages and an all-folders view with statistics                                                                                                                                                                                                                                                                          | F11                                                                               | ✅         |
| 2026-10-02 | Builder feedback (18 points): inline rename, try fields on the canvas, read-only keys with suffix, help as info icon, smaller radius, tighter spacing, label position, Nuxt UI dates, saved fields + lists, file-type picker, thumbnails, option numbers in formulas, clearer + complete logic, read-only / disabled with required guards, phone preview stacking | F7                                                                                | ✅         |
| 2026-10-02 | Form themes: header, footer, body, images and text design carried on shared forms; default theme when none is chosen                                                                                                                                                                                                                                              | F8                                                                                | ✅         |
| 2026-10-02 | Builder canvas uses the full width; full-screen toggle with fields · canvas · settings and visible save status                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Lists later: static, large / autocomplete, dynamic sources, cascading levels (State → City → Location) and auto-fill of other fields, plan in docs/OPTION-LISTS.md                                                                                                                                                                                               | F15                                                                               | 🟡 (M1 list manager, M2 levels ✅) |
| 2026-10-02 | Drop indicator while dragging fields (dashed placeholder + label)                                                                                                                                                                                                                                                                                                 | F7                                                                                | ✅         |
| 2026-10-02 | Rich text field (real editor)                                                                                                                                                                                                                                                                                                                                     | F7                                                                                | ✅         |
| 2026-10-02 | New fields default to ½ width; required messages use the field label                                                                                                                                                                                                                                                                                              | F7                                                                                | ✅         |
| 2026-10-02 | Rich text: headings 1–6, paragraph, text alignment, code block                                                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Layout blocks: nicer section, inline paragraph editing, image upload + resize, divider options                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | Validate email and all address parts (not only the first line)                                                                                                                                                                                                                                                                                                    | F7                                                                                | ✅         |
| 2026-10-02 | IT / technical field types: IP address, domain, MAC, IBAN, SWIFT / BIC, colour + global types (full name, consent, duration, percentage, language, time zone, currency), first set built; owner may add more                                                                                                                                                     | F7 (later)                                                                        | ✅         |
| 2026-10-02 | More theme designs: header-only, footer-only and side designs, at least 5 more now, more later                                                                                                                                                                                                                                                                   | F8                                                                                | ✅         |
| 2026-10-02 | Form workspace header too full: search as an icon, Preview as an icon                                                                                                                                                                                                                                                                                             | F8                                                                                | ✅         |
| 2026-10-02 | Templates before the renderer (both serve form creation), phases renumbered: F9 Templates, F10 Renderer, F11 Responses                                                                                                                                                                                                                                           | Roadmap                                                                           | ✅         |
| 2026-10-02 | Integrations for data sources: add their databases to send form data, database explorer, query editor, other database operations                                                                                                                                                                                                                                  | F12 (new phase)                                                                   | ✅ |
| 2026-10-02 | Data sources as its own rail area with its own menu; placeholder pages now (no extra Forms icon, the workspace button is Forms)                                                                                                                                                                                                                                  | F12                                                                               | ✅         |
| 2026-10-03 | API service ("developer option"): build API endpoints from forms (GET / POST / PUT / DELETE), tokens and headers, field choice per method, allow / block lists, analytics, enable / disable; own rail area with placeholders                                                                                                                                      | F13 (new phase)                                                                   | ✅ |
| 2026-10-03 | API addresses `https://api.formalie.dev/{key}/{endpoint}` (production `api.formalie.com`)                                                                                                                                                                                                                                                                         | F13                                                                               | ✅ decided |
| 2026-10-03 | Form links `https://{forms                                                                                                                                                                                                                                                                                                                                        | sub}.formalie.com/{formId}/fill`and`/embed` (`forms.formalie.dev` in development) | F10        | ✅ decided |
| 2026-10-03 | Separate dashboards for Forms, Data sources and API service                                                                                                                                                                                                                                                                                                       | F21                                                                               | ⬜         |
| 2026-10-03 | Template catalogue: 84 starter templates in 11 categories, each with its own design; calculations where needed (risk score, totals, averages); template statistics and the forms made from each template                                                                                                                                                          | F9                                                                                | ✅         |
| 2026-10-03 | AI assistant built in (create forms, templates, analysis, more), own rail area with placeholders                                                                                                                                                                                                                                                                 | F19 (new phase)                                                                   | 🟡         |
| 2026-10-03 | "Folder" on New form, what it means                                                                                                                                                                                                                                                                                                                              | F8                                                                                | ✅         |
| 2026-10-03 | IP address and MAC address typing masks (MAC: other notations allowed)                                                                                                                                                                                                                                                                                            | F8                                                                                | ✅         |
| 2026-10-03 | Field access: Everyone / Departments / Roles / People; restricted fields never required                                                                                                                                                                                                                                                                           | F8 (answers visibility in F11)                                                    | ✅         |
| 2026-10-03 | Payment field, intention                                                                                                                                                                                                                                                                                                                                         | F15 (Payments)                                                                    | ⬜         |
| 2026-10-03 | How duplicate submissions are prevented                                                                                                                                                                                                                                                                                                                           | F10                                                                               | ✅ |
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
| 2026-10-03 | Themes like templates: system, saved and created themes                                                                                                                                                                                                                                                                                                           | F9 milestone 2                                                                    | ✅         |
| 2026-10-03 | Form overview KPI cards like the design (title colour and position)                                                                                                                                                                                                                                                                                               | F9                                                                                | ✅         |
| 2026-10-03 | Form link vs embed link, same or different? (advice: different; embed as code)                                                                                                                                                                                                                                                                                   | F10                                                                               | ✅ decided |
| 2026-10-03 | QR code for form links                                                                                                                                                                                                                                                                                                                                            | F9 / F10                                                                          | ✅         |
| 2026-10-03 | Languages go with the forms (links, embeds, QR, respondent language)                                                                                                                                                                                                                                                                                              | F9 (picker) / F10 (public pages)                                                  | ✅         |
| 2026-10-03 | Themes clickable to view or edit                                                                                                                                                                                                                                                                                                                                  | F9                                                                                | ✅         |
| 2026-10-03 | Branded QR codes (organisation, form name, logo in the centre, Formalie mark), several colours, branding on / off | F9 | ✅ |
| 2026-10-03 | Folder explanation behind an info icon (click to read) instead of text under the field, new form page and "Use template" dialog | F9 | ✅ |
| 2026-10-03 | Templates: category chips removed from the top, categories (with counts) only in the Filter menu, like every other list | F9 | ✅ |
| 2026-10-03 | Templates by category: gallery lists categories (counts + analytics) instead of all 84 templates; a category opens its templates; menu shows the top 6 categories then All; Formalie templates and your own (saved) templates kept apart | F9 | ✅ |
| 2026-10-03 | Departments, roles and other organisation data (and lists) are set up per workspace in Settings; the builder only shows what the workspace has | F14 (Organisation data) · F15 | ✅ (F14 M2, F15 M1) |
| 2026-10-03 | Preview: Desktop mode fills the whole screen edge to edge (was a box); the design page's preview fills its pane | F10 | ✅ |
| 2026-10-03 | Themes menu like Templates: kinds with counts (All themes · Formalie · Saved · Created) instead of every saved theme | F8 follow-up | ✅ |
| 2026-10-03 | Save as template lives in Form settings → Template (after Save and resume), not the header; a form already saved as a template shows that and offers "Update template" (same template, latest changes) or a separate copy | F9 follow-up | ✅ |
| 2026-10-03 | Sidebar: one menu group open at a time (opening one closes the others) | F1 follow-up | ✅ |
| 2026-10-03 | Preview side panel: Desktop fills the panel edge to edge (panel keeps its width) | F10 | ✅ |
| 2026-10-03 | Text colours sharp and dark everywhere (tables, grids, cards like the navigation) | F1 follow-up | ✅ |
| 2026-10-03 | No real ids anywhere in URLs, parameters or responses, encrypted references only the API can decrypt (globally) | F2 follow-up (security) | ✅ |
| 2026-10-03 | Public form footer: © organisation · Terms · Data Privacy Policy; every link on a public form opens in an in-app browser window over the form (branded, 80%, rounded, clear close) so nothing typed is lost | F10 | ✅ |
| 2026-10-03 | Super admin console for the owner to manage everything, starting with the Terms / Data Privacy Policy URLs (served now as platform settings, config fallback) | F23 (new phase) | ⬜ planned |
| 2026-10-03 | Prevent duplicate submissions (also when someone fills in for a friend on the same computer); thank-you buttons Fill in another (confirm it's for someone else) and Close this page; form availability period (expired page after it); show the period in table and grid | F10 | ✅ |
| 2026-10-03 | Still possible to send twice (one-letter email change): identify the person by their own email (not other emails in the form) or ID; smart matching; optional verification; never mistake another person | F10 | ✅ |
| 2026-10-03 | Events & bookings and Operations & IT designs: side panel squeezed the form, use a smaller quote-like header instead | F9 follow-up | ✅ |
| 2026-10-03 | Help guide per form: written in Form settings (rich editor, opened from a button), shown from a floating "?" in a chat-style panel; on / off, off by default | F10 | ✅ |
| 2026-10-03 | Save and resume: how and where it works, built (autosave + "Save and continue later" link) | F10 M2 | ✅ |
| 2026-10-03 | Portal text still looked faded: dark-mode headline colour fixed, body text darker, list values in the main text colour like the design image | F1 follow-up | ✅ |
| 2026-10-03 | Public form page: branded frame around the form, workspace branding, link to the organisation's website, several page designs to choose from; polished and lively without distracting from the form | F10 (M1b) | ✅ |
| 2026-10-04 | "Can view" must be view only: no editor, designer, logic, share settings, save as template or availability change | F10 M3 | ✅ |
| 2026-10-04 | Responses page: group by form; only a form's page lists its responses (grouped only) | F11 | ✅ |
| 2026-10-04 | Lock the response card format and use it on the Forms list (table and grid) | F11 / F6 | ✅ |
| 2026-10-04 | Templates and Themes in the same table / grid format (chart cards, Columns, locked card, rows open) | F9 / F11 | ✅ |
| 2026-10-04 | Page designs library (owner chose "Page designs library"): Resources → Pages like Themes, many ready-made designs for the page around the form on its public link, teams save / create their own, pick one per form | F10 / F9 | ✅ |
| 2026-10-04 | About 10 page designs to pick from, addable in the designer; designer: themes collapse like the rest, a little space under each group | F10 / F9 | ✅ |
| 2026-10-04 | Rename "Pages" to "Landing pages" (a form's own pages stay "pages") | F10 / F9 | ✅ |
| 2026-10-05 | Date range ("Any time") on the Responses page and Exports, like every list (filter standard) | F11 | ✅ |
| 2026-10-05 | All-forms Insights not one-sided: more details, balanced rows | F11 | ✅ |
| 2026-10-05 | Appearance in Settings: each workspace customises the portal's look (colours, background, rail, menu, header, footer, main body, light / dark); exports and emails follow it | F14 | ✅ (separate light / dark colours later) |
| 2026-10-05 | PDF export in the application's own colours (not the form's theme) until Appearance exists | F11 | ✅ |
| 2026-10-05 | Folders must not take over the menu as they grow: at most 5 per person (pinned, recent, busiest), pin / unpin, foldable group, All folders with the total, folders in Ctrl / ⌘ K; a line between FOLDERS and SYSTEM | F11 | ✅ |
| 2026-10-05 | Folder colour must show where it applies (page header too); more colours and a picker for any other | F11 | ✅ |
| 2026-10-05 | F12: each engine's own connection properties (MySQL, SQL Server, Oracle, PostgreSQL, MariaDB); cover every operation a database is used for; always tell people which permissions to grant so nothing breaks | F12 M1 (decision 111) | ✅ |
| 2026-10-05 | F12 corrections: any account may be used (all configuration encrypted with Fernet, no admin warning); SSH tunnel only for private networks; a connection is for storing responses: Formalie always creates its own prefixed tables (formalie_ / fmly_ / form_) and reads, writes and alters them; other tables optional, default read and write | F12 M1 (decision 112) | ✅ |
| 2026-10-04 | Responses, following the design image: two top cards with charts; grid cards like the design's task cards; theme status colours (no blue); panel without history, answers grouped by likeness with chips, equal tiles, sliders; a file viewer like the preview (download when not previewable); move and show / hide columns in every table | F11 M1 | ✅ |
| 2026-10-04 | Responses layout: slim top strip and the table right below; Responses | Insights switch on the table's toolbar line; very rich grid cards; a super rich response panel with Previous / Next floating in the footer | F11 M1 | ✅ |
| 2026-10-04 | Responses: a beautiful, clean page with a lot of insight, slim charts, table; and every page must show test responses ("connect all the dots") | F11 M1 | ✅ |
| 2026-10-04 | Forms in several languages open in the form's main language (not the browser's); language switcher beside "Visit website" | F10 M4 | ✅ |
| 2026-10-04 | French form: labels, sections, help and thank-you stayed English; "already filled in" showed only after the form flashed for seconds; spam check not visible anywhere | F10 | ✅ |
| 2026-10-05 | Database explorer: the connection and table tree take the sidebar's whole menu column (rail stays) with a back arrow to the menu, same width as the menu and adjustable; extra slim table rows; no grid for table rows | F12 M3 | ✅ |
| 2026-10-05 | Explorer: export tables as JSON and SQL INSERT statements too; one table open at a time in the tree; account avatar at the foot of the rail (with a line above) while the tree holds the menu column; slimmer tree search and connection picker; one square bullet for every table | F12 M3 | ✅ |
| 2026-10-05 | Explorer: no import for now (removed); adding, changing and deleting rows only in tables created outside Formalie, never in response tables | F12 M3 | ✅ |
| 2026-10-05 | Make sure nothing loads a whole table at once: paging in the database, a capped count ("10,000+"), a time limit on every explorer statement (backend rules in the contract) | F12 M3 | ✅ |
| 2026-10-05 | Table and column management in the explorer (CREATE TABLE, add / change / delete columns, indexes, rename, empty, delete), only on tables that aren't Formalie's, with Full access | F12 M3 | ✅ |
| 2026-10-05 | No data types beside column names in the explorer (tree, row form, row panel); Help & support moves from the menu to the foot of the rail (always in place, short lines between items, level with the account card); in explorer mode Help sits above the account | F12 / shell | ✅ |
| 2026-10-05 | The app's own right-click menu everywhere (never the browser's): rows of every list, the explorer's tree, rows and table area (DDL, export, rows), text fields (cut, copy, paste, select all), links, the app's items (back, search, theme, …) | shell / F12 | ✅ |
| 2026-10-05 | Explorer dialogs that change data or structure don't close on an outside click (Esc, ✕ and Cancel still do) | F12 M3 | ✅ |
| 2026-10-05 | Query editor (M4) uses the same mode as the explorer: its panel in the menu column, full width for the editor; its own results grid | F12 M4 | ✅ |
| 2026-10-05 | Every empty, not-found and error state: a better, evenly centred look with fitting icons | all | ✅ |
| 2026-10-05 | Explorer export: this page by default; "All rows" is a deliberate choice capped at 5,000 rows (server load), with a note when more matched | F12 M3 | ✅ |
| 2026-10-05 | Explorer works like a database editor: double-click a cell to edit it in place (not keys, auto-numbered or UUID columns, not read-only tables), drag the line between headers to resize columns (double-click fits, ← / →), widths remembered per table; explorer only | F12 M3 | ✅ |
| 2026-10-05 | M5: Activity for the connections; "Imports & exports" becomes Exports (Activity filtered to exports); polish sweep of every Data sources page on phone, tablet and desktop | F12 M5 | ✅ |
| 2026-10-05 | SQL reserved words in blue in the Query editor | F12 M4 | ✅ |
| 2026-10-05 | Query editor: Run all (every statement, a result per statement); a lazy tree for very large databases (columns load when a table is opened); open F12 items resolved (done, or moved to F15e / F22 / later) | F12 | ✅ |
| 2026-10-05 | Before F13: Forms → Analytics (still a placeholder) and Data sources → Overview must be finished and look "Wao" in the design's dashboard style | F18 (brought forward) · F12 overview | ✅ |
| 2026-10-06 | F13 tokens: separate test and live tokens from the start | F13 M2 | ✅ decided |
| 2026-10-06 | Files through the API: not in M1 (JSON only); a separate upload step with the form page's checks, once tokens and rate limits exist | F13 M5 | ✅ |
| 2026-10-06 | Test the API service with Postman already against the mock (tell the owner when it works) | F13 M2 (mock public API) | ✅ |
| 2026-10-06 | Token prefixes and headers say Formalie: `formalie_live_…` tokens; `Formalie-Key` instead of `Idempotency-Key` (our own name, on purpose) | F13 M2 | ✅ |
| 2026-10-06 | Examples with the form's real answer values; the console fills in `Formalie-Key` | F13 M5 | ✅ |
| 2026-10-06 | Owner review of F13: guide people from service → endpoint → token → access rules → live, with explanations and steps in every dialog; a service is needed before an endpoint | F13 M7 | ✅ |
| 2026-10-06 | Tokens can be seen again later: masked, click to view after confirming the password (API keys and webhook secrets alike) | F13 M7 | ✅ |
| 2026-10-06 | Access rules: IPs and domains as chips (comma, Enter or space), each checked; country and region honest about VPNs, plus a rule for anonymous networks (VPN, proxy, Tor, hosting) | F13 M7 | ✅ |
| 2026-10-06 | Confirm a proper answer for every failure (headers, access, service, endpoint, address) | F13 M7 | ✅ |
| 2026-10-06 | Docs & testing redesigned (layout, method colours, code beside the text); Try it as a drawer | F13 M7 | ✅ |
| 2026-10-06 | README: test cases for the whole API service | F13 M7 | ✅ |
| 2026-10-06 | Designer: no "Replace the current design?" when picking a theme, starting point or page design; a toast with Undo instead | F8 designer | ✅ |
| 2026-10-06 | Where people can answer: web link, embed, API service per form (API only = no web address at all, its link, embed and short link answer not found); the endpoint wizard offers "Publish for the API only" for drafts | F10 share · F13 | ✅ |
| 2026-10-06 | Clean question keys (`first_name`, not `first_name_w6r3`); keys a published version used stay fixed and are never reused | F7 builder | ✅ |
| 2026-10-06 | Docs & testing: the endpoint's required headers with their values in every code example, Try it and OpenAPI | F13 M7 | ✅ |
| 2026-10-06 | Field icons: every field with a box gets its type's icon; Form settings → Field icons (Show / Hide) for the whole form, like label position | F7 builder · F10 renderer | ✅ |
| 2026-10-06 | Field icons follow the label's meaning (First name → person, Company → building), the type icon only when nothing matches | F10 renderer | ✅ |
| 2026-10-06 | A form changed after its API endpoints exist: endpoints that follow the latest version update on publish; Publish says what changes for apps (new, newly required, removed questions) | F13 · F7 publish | ✅ |
| 2026-10-06 | API payloads and answers use the label names (`first_name`), for every endpoint, old ones too; editable per endpoint; example values fit the label | F13 | ✅ |
| 2026-10-06 | Examples carry every header a call needs: signing headers when a signing token can call the endpoint, the endpoint's own headers with values | F13 | ✅ |
| 2026-10-06 | Headers tab: endpoints with headers of their own grouped by service, values masked with view and copy | F13 | ✅ |
| 2026-10-07 | Sign-in / sign-up pages: new design for the left side, owner to describe later | F2 auth pages (later) | ⏳ waiting for owner |
| 2026-10-07 | Forgot password for the person who signed the workspace up (code, confirm, new password): the flow exists at the workspace sign-in ("Forgot password?"), owner to try it and say what is missing | F2 auth (review) | ⏳ waiting for owner |
| 2026-10-07 | Formalie always present whatever a workspace brands (sign-in page, emails) | F14 feedback | ✅ |
| 2026-10-07 | No own domain for now, the subdomain is enough | F14 M7 | ✅ removed |
| 2026-10-07 | One organisation per workspace (Company covers it): no sub-organisations | F14 M7 | ✅ removed |
| 2026-10-07 | No teams, locations, cost centres (not collaborative; access per form) | F14 M2 | ✅ removed |
| 2026-10-07 | Sign-in codes: no authenticator app; text messages optional, email is the standard | F14 M3 | ✅ |
| 2026-10-07 | Form defaults: show a picture of the selected theme | F14 M5 | ✅ |
| 2026-10-07 | Rename "Option sets" to "List Option" (menu, Settings navigator, page title; the address stays /option-sets) | F15 | ✅ |
| 2026-10-07 | The first-load screen (Formalie mark and three dots) follows the workspace's Appearance | F14 | ✅ |
| 2026-10-07 | Empty states follow the workspace's Appearance (icon and its tile in the primary colour; their buttons too) | F14 | ✅ |
| 2026-10-07 | Lists with levels before search: list multi select; levels single or multi select (Country → State → City, Product → Category → Type → Brand), chosen in the form design; the Lists tab says plain or levels; each level shows only what matches the choice above and does not open when nothing matches | F15 M2 | ✅ |
| 2026-10-07 | Lists have at most 4 levels | F15 M2 | ✅ |
| 2026-10-07 | Lists with levels: one choice or several decided per level when adding (e.g. first several, second one); lower levels stay hidden until something is chosen above and list only what is under it | F15 M2 | ✅ |
| 2026-10-07 | Lists with levels in the editor behave as in the form (no hint texts); levels are removed together, never one alone; required or not decided per level | F15 M2 | ✅ |
| 2026-10-07 | Nothing set while adding a list: click or drag adds it, settings (Show as, one / several, required) in the right panel; lists draggable, not only click | F15 M2 | ✅ |
| 2026-10-08 | List import: a file with several columns went into a simple list as one column; make lists simpler and more flexible, with proper instructions | F15 M2 | ✅ |
| 2026-10-08 | Builder simplicity: click anywhere on the page to add a field there (searchable list at the click); no "Page 1" title on the page, rename on the tab with a pencil; the page fills the screen height and grows; Fields and Settings panes collapse / open (open by default), Settings opens when a field is selected | F7 | ✅ |
| 2026-10-08 | No form name and no page name as headings in the form body; keep them on the page, not taking space in the form | F8 / F10 | ✅ |
| 2026-10-08 | Themes style sections, dividers, paragraphs and images too (various designs; themes, starting points and templates) | F8 | ✅ |
| 2026-10-08 | API: a new endpoint looked assigned a token nobody made for it; wizard tokens named "{service} · /endpoint" instead of "{Service} Token"; visible connections in every API detail panel | F13 | ✅ |
| 2026-10-08 | Publish only clickable when there are new changes; otherwise "No new changes. Make changes first." | F7 | ✅ |
| 2026-10-08 | A general token (no service or endpoint) may call every endpoint, also ones made later: kept as is (owner, after a POST to /vehicles with the sample token "Mobile app") | F13 | ✅ decided |
| 2026-10-08 | API records showed list answers as value codes (running_shoes_air_footwear) instead of what was chosen | F13 / F15 | ✅ |
| 2026-10-08 | API examples (docs, endpoint example, console, code, test tokens) in the form's order; no made-up values for lists with levels | F13 | ✅ |
| 2026-10-06 | Menu "Docs & testing" renamed "API Documentation" (menu, page title, breadcrumbs and the guidance that points to it) | F13 | ✅ |
| 2026-10-06 | Webhooks send a webhook token from Tokens & headers (new type For webhooks; Authorization: Bearer, Content-Type, Formalie-Key = delivery id), no separate secrets or signatures; clean FRM-RESP-1006 details | F13 | ✅ |
| 2026-10-06 | API POST follows the form's duplicate rules (same answers 409 whatever the key; identity email same person 409, typo-close flagged); deleted responses no longer block re-sending | F13 | ✅ |
| 2026-10-06 | New token: "How it signs in" (bearer token or client id and secret) is a required choice with no default, explained under it | F13 | ✅ |
| 2026-10-06 | After creating an endpoint: Open the endpoint also under the Go live box (right), besides the header button | F13 | ✅ |
| 2026-10-06 | New endpoint, step 1: only forms ready for the API are listed; the "Not ready for the API yet" list with Publish for the API only / Open to the API removed (too easy to click by mistake) | F13 | ✅ |
| 2026-10-06 | Sign in: two ways, never both, explained in Docs with per-endpoint detection; examples show the /token step for client id and secret tokens; mix-ups answered with the right way | F13 | ✅ |
| 2026-10-06 | Formalie-Key required on POST only (optional elsewhere, left out of those examples), 16+ characters and no simple patterns, same key with another body refused (409), retries for 24 hours; management API (/v1) and its token rights removed | F13 | ✅ |
| 2026-10-06 | Examples show the workspace's own token (masked) with a link to it; new tokens named after their service or endpoint | F13 | ✅ |
| 2026-10-06 | API keys folded into tokens: a token can hold management rights (Manage forms and responses), the /v1 management API signs in with tokens; API keys page removed | F13 | ✅ |
| 2026-10-06 | Final header rule: three headers on every call (Authorization, Content-Type, Formalie-Key), none optional; no custom headers, no signed calls; token expiry in every answer; Docs show the three | F13 | ✅ |
| 2026-10-06 | Rail "+" menu: Forms group (New form, From a template, New template) and Operations group (Add database, New API service, Query editor, Database explorer) | F1 shell | ✅ |

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
| 2026-10-02 | F7    | Milestone 3, phase done: logic editor (`/forms/[id]/logic`: rules with plain-language summaries, All / Any, show / hide / require / jump, calculations), versions page (timeline, view, compare, restore, discard), shared builder frame with Build / Logic / Versions switch (saves before switching), collapsible sections, lazy dialogs; 20 languages; 87 tests. Stopped for review.                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-10-02 | F6    | New form page polish (owner): Blank tab shows a live mini preview of the empty form and what a blank form offers; name + folder sit in a "Form details" card whose footer has **Continue** (same as Create form, closer to the fields) on Blank, Template and Import.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | Owner feedback round (18 points) done: canvas fields work for trying out, double-click / F2 rename, Label wording, read-only field keys with id suffix (formulas follow), help text as info popover, smaller form radius, tighter spacing, container-query columns (phone preview stacks), form-wide label position (New form + Form settings), all dates Nuxt UI (UInputDate / UInputTime / UCalendar, ranges too), read-only / disabled fields with required guards everywhere, grouped searchable file-type picker + drop checks + thumbnail grid, option numbers + if() / comparisons / functions in formulas, logic: all operators and 12 actions, IF / THEN steps, starters, conflict checks; Saved fields + Lists (library API, palette tabs, list editor). 20 languages. |
| 2026-10-02 | F7    | Phones / tablets: field list easy to find, "Add field" next to the page tabs and a dashed "+ Add field" under the last field (all sizes; laptops focus the palette search); the bottom bar now sticks to the content instead of covering the footer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | "Beside the field" now holds for half-width (and narrower) fields too: decided by the form's width (`@container/form`), not each cell; phone-width forms still stack.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | "Beside the field" sits right next to the input: the label is as wide as its text (up to 45 %, then wraps), the input follows after a small gap and takes the rest, no column gap.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | "Beside the field" is uniform: one label width per form (from its longest label, max 22 characters / 30 %, the input gets most of the row), labels end-aligned against their input, so every input starts on the same line and has the same width.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | Canvas no longer boxed (fills the middle, less padding); full-screen mode for Build / Logic / Versions with save status in a slim bar.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F7    | Preview: Desktop fills the preview panel (no inner box; panel keeps its size); Tablet and Phone keep their device widths.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-10-02 | F7    | Drag and drop shows where a field will land: dashed, tinted placeholder labelled "Drop here, new row" (between rows) or "… beside" (in a row, half width), and a dashed outline around the page while dragging.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-10-02 | F7    | Rich text field done with Nuxt UI's editor: Basic / Full toolbar (marks, lists, quote, link, headings, alignment, code, clear, undo / redo), Markdown answers, locked states, character count.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-10-02 | F7    | New fields start at ½ width (layout blocks full width), width still adjustable; required errors name the field ("First name is required.").                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-10-02 | F7    | "+ Add field" under the canvas is a compact button at the end of the row, so it no longer covers the drop area.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-10-02 | F7    | Yes / No: switch and label on one line (switch first, label right after, centred; click the label to toggle); in "beside" forms it lines up with the other inputs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F7    | Rich text: standard line height (20 px) and a small 2 px gap after Enter, so new paragraphs read like normal lines.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 2026-10-02 | F7    | Rich text Full toolbar (now the default): Text style menu (Paragraph, Heading 1–6), inline code, code block. Text alignment needs the TipTap text-align extension (not bundled with Nuxt UI) and HTML storage, awaiting owner decision.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-10-02 | F7    | Rich text alignment (left / centre / right / justify) with `@tiptap/extension-text-align` (owner-approved); answers now stored as HTML, sanitised server-side; max length counts visible text.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-10-02 | F7    | Layout blocks upgraded: section heading block with placeholders and inline title / description editing; paragraph written on the canvas (bubble toolbar, HTML, shown read-only to respondents); image upload (drop / browse, progress, 5 MB, safe SVG) or link, drag / keyboard resize, presets, alignment, caption, link, rounded, alt-text prompt; divider style and spacing.                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-10-02 | F7    | Image "Fill": spans the whole field; optional height (small / medium / large) crops it like a banner.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-10-02 | F7    | Answer validation: email, web address, phone, number range, length, pattern, choice counts, files, date range and every required address part (postal code / region switchable); errors name the field, update live, missing address parts highlighted. One shared validator for renderer and API.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-10-02 | F8    | Milestone 1: Design view with live preview (devices, thank-you page), starting points, layout / background / container / typography / colours / inputs / buttons / header + cover / footer / thank-you; themes stored on the form, applied as CSS variables on the form page only, workspace default from brand colour + logo; builder Preview themed.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-10-02 | F8    | Milestone 2: save / update / apply themes from the designer, themes library page (rename, duplicate, delete with usage count), audit + `FRM-FORM-1010`. 13 new field types (global + technical) with validation (IP v4/v6, domain, MAC, IBAN mod-97, BIC, colour, duration, name parts, consent, catalogue picks); all 20 languages.                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-10-02 | F8    | Six more starting points (Banner, Ribbon, Grounded, Side panel, Aurora, Corporate) with header bands, footer bars and colour / gradient side panels; designer controls for each; swatches show the structure. Form workspace header: search and Preview as icons. Confirm dialogs now always open above drawers (they were hidden behind the designer drawer on phones). Roadmap: Templates moved before the renderer (F9 Templates · F10 Renderer · F11 Responses).                                                                                                                                                                                                                                                                                                             |
| 2026-10-02 | F8    | Fix: “Add link” in the footer reset the footer (a new link starts as an incomplete https:// address, which failed the theme check and switched the footer off). Links are now kept while being typed; only complete https links with a label show on the form; other schemes are emptied.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

| 2026-10-02 | Roadmap | New phase **F12, Data sources & databases** (connections, sending form data, database explorer, query editor, other database operations, safety); later phases renumbered F14–F22 (Settings → Roles & access). |
| 2026-10-02 | F12 | Placeholder shell: Data sources rail area (icon under the workspace button), own sidebar menu, overview with section cards and supported databases, seven placeholder pages; destinations moved from Integrations (redirect kept). |
| 2026-10-03 | F13 | New phase **F13, API service** (own rail area + placeholder pages); later phases renumbered F14–F22. Public URL scheme decided: API `https://api.formalie.dev/{apiKey}/{endpoint}`, forms `https://{forms | sub}.formalie.dev/{formKey}/fill · /embed`; `forms` subdomain reserved; copy-link and the form overview use the new links. F8 closed after owner review. |
| 2026-10-03 | F8 | Owner follow-ups: folder hint, IP / MAC typing masks, field access (audience) with directory picker and "never required" rule (editor, form, publish check, logic). |
| 2026-10-03 | F19 | New phase **F19, AI assistant** (own rail area + placeholder pages); later phases renumbered F20–F22. F9 plan written: framework + 84 templates in 5 milestones. Payments planned in F15. |
| 2026-10-03 | F9 | Milestone 1: template authoring kit (`shared/templates/`), 11 categories with their own designs, 20 templates (Business & Customer, HR & Workplace) with calculations (totals, averages, days, rating bands, loyalty group) and logic, all tested as valid, publishable forms; formula additions `avg` / `count` / `days` / text results, internal calculations; gallery (Grid of themed cards / Table, category chips with counts, filters, sorts), template page (live preview, what’s included, formulas, usage, forms made from it), Use template, Save as template, workspace templates (duplicate, delete), New form catalogue picker; seeded sample forms linked to templates; mock `/templates`; 20 languages. Also: confirm dialog keeps its text while closing. |
| 2026-10-03 | F9 | Owner review round: form overview redesign (KPIs, 30-day chart, share, structure, versions, details, activity; mock `/forms/:id/overview`), template page side panel (tiles, formula snippets, forms slider), mini table thumbnails, sidebar submenus (Templates / Themes recent 6 + All, Responses statuses), integrations moved to the API service (pages + redirects; F13 renamed "API service & integrations", F15 "Option sets & payments"), forms list Template filter, field access list fix. Duplicate-submission protection planned (F10). |
| 2026-10-03 | F9 | Owner review fixes: file uploads (inside the zone, limits enforced with notifications, visible remove), live error clearing for duration, page-shaped gallery thumbnails, folders with forms can't be deleted (`FRM-FORM-1013`); themes catalogue (system / saved / created) planned into milestone 2. |
| 2026-10-03 | F9 | Milestone 2: 23 templates, Health & Safety (risk score / level with action plan, incident priority, near-miss priority, inspection compliance %, BMI, screening result, guardian consent), Events & Bookings (ticket totals, room cost, sponsorship totals, speaker / sponsor page logic), Hospitality (nights from dates, nightly-rate estimate, service score, catering per guest); 43 templates in total, every onboarding starter now from the catalogue. Themes catalogue: system (starting points + category designs, read-only), saved and created themes; theme editor (`/settings/themes/new`, `/settings/themes/:id`) with live preview, Cmd/Ctrl+S and a leave guard. |
| 2026-10-03 | F9 | KPI cards aligned with the design; QR codes for form links (`uqr` added, owner-approved); form language setting; themes open in the editor (workspace) or read-only (Formalie) from list and grid; Settings no longer highlighted on theme pages. Language plan for public forms recorded (decision 73). |
| 2026-10-03 | F9 | Milestone 3: 21 templates, Education (course score, quiz score / percentage / pass, scholarship eligibility for the panel only, attendance count and rate), Operations & IT (ticket priority from impact × urgency, change risk, requisition totals, inspection and QC pass rates), Finance & Legal (debt-to-income and a flat-rate monthly estimate, invoice subtotal / tax / total, claim total, company details when signing for a company); 64 templates in total; new calculation checks; 20 languages. |
| 2026-10-03 | F9 | Milestone 2 + 3 languages complete: template names, theme library and errors in all 20 languages; Spanish wording aligned to "tú" throughout; 188 tests green. |
| 2026-10-03 | F9 | Milestone 4: 20 templates, Community (membership fee, donation with optional 3% cost cover, petition, ranked ballot), Real Estate (income-to-rent ratio with an internal affordability band, room-by-room condition score, emergency note on urgent repairs), Sales (B2B lead capture with hidden source fields, seat-based quote, BANT-style qualification hot / warm / cold, trade order with volume discount); all 84 templates in 11 categories; 20 languages. |
| 2026-10-03 | F9 | Milestone 5: template content (1,411 texts) in all 20 languages, previews and new forms open in the person's language, logic / scores / formulas unchanged (compared values like "yes" kept); templates gallery reorganised by category (overview with counts and use, category pages, Your templates apart, menu: top 6 categories + All + Your templates); 228 tests green. Stopped for the owner's end-of-phase review. |
| 2026-10-03 | F9 | Owner review passed, F9 closed. Preview fix (Desktop full screen, Tablet / Phone device frames that fill the height; design page preview fills its pane); organisation data (departments, roles, lists) planned into Settings (F14). |
| 2026-10-03 | F9 | Follow-ups: Themes menu by kind with counts; "Save as template" in the builder header (Build / Logic / Design, phone menu, full screen), saves pending edits first, name pre-filled, menu counts refresh. |
| 2026-10-03 | F9 | Follow-ups: "Save as template" moved into Form settings → Template; templates remember their source form (`source_form_id`), an already-saved form offers "Update template" (`POST /templates/{key}/sync`, audited) or a separate copy; sidebar keeps one group open; preview side panel Desktop fills edge to edge. |
| 2026-10-03 | F10 | Milestone 1: public form pages `/{key}/fill` and `/embed` (server-rendered, SEO tags, canonical, 404 for unknown keys, noindex for embeds / closed forms), `forms.*` host, `public_key` per form, secure server-side fetch (server-only token), states (not found · not published · closed · error), submit through the encrypted API with one response per fill-in session (Idempotency-Key, verified: a retry stores nothing new), server re-checks answers and recomputes calculations (`shared/utils/forms/submission.ts`), thank-you or redirect, page language without touching the portal cookie, embed height messages; audit "Response received". Text colours one step sharper everywhere (owner). |
| 2026-10-04 | F10 | M2: file uploads on public forms, files go straight to storage with progress on each thumbnail, Next / Submit wait for them, answers keep encrypted references (also in Save and resume drafts); server checks type, size, real pictures, no programs, same form / question, one response per file; respondent files never public. Form.vue split (ResumeBar, Upload). |
| 2026-10-04 | F10 | M2 done: spam protection without a captcha (invisible proof-of-work, hidden trap, submission limits) and the Embed code window on the Share card (auto / fixed height, resize script limited to the form address); embed pages can now be shown on other websites (frame headers, SameSite=None device cookie). |
| 2026-10-04 | F10 | Owner test fixes: "Translate the form’s text" when the form language changes (template text, 20 languages, own text kept); "already filled in" rendered by the server from a receipt cookie (no flash); Form settings shows "Spam protection, always on". |
| 2026-10-04 | F10 | Form language: choosing the language now translates the form text in the same step (no second button), toast with Undo. |
| 2026-10-04 | F10 | Blank forms now start in the creator's app language (form language, first page name, thank-you text), like template forms. |
| 2026-10-04 | F10 | Form language change also translates the builder's default question names ("Long text", "Option 1", "Page 1"…), not only template text (owner: a new "Long text" question stayed English). |
| 2026-10-04 | F10 | Form language change covers every field type and text spot (owner: "as long as it has a label"): matching ignores capitals / spaces, new 546-word everyday form vocabulary in all 20 languages, plus image alt / caption, custom error messages, guide title, header subtitle. |
| 2026-10-04 | F10 | The form title respondents see (page header, browser tab, link card) follows the form language (`settings.title`); the name in the forms list stays as typed. |
| 2026-10-04 | F10 | M3 started: Share tab in the form editor, access (anyone with the link / password), custom link with live availability check, response limit (form-full page), availability; public password screen; Share settings from the overview card and the forms menu. |
| 2026-10-04 | F10 | Share card rearranged (owner): status badges on one line, link first, three equal action tiles (Open · Embed code · QR code), summary row (access · limit · end date) that opens the Share settings. |
| 2026-10-04 | F10 | Custom link fix (owner): the availability check sent the link the wrong way, so every link read as invalid; taken or reserved links now offer up to three free suggestions (with the organisation name, the year, a number) as one-click chips. |
| 2026-10-04 | F10 | Custom link check really fixed: the server read the link from the address instead of the encrypted request, so every link read as invalid; the Share card summary row opens the Share settings again. |
| 2026-10-04 | F10 | Custom links are unique per address (owner): each workspace subdomain has its own set, workspaces on forms.* share one; a link taken by one of your forms shows which form (name, status, Open) with free suggestions, tested in the browser. |
| 2026-10-04 | F10 | Response limit (owner): starts at 10, goes down to 2, steps of 1 (was steps of 10 from 1). |
| 2026-10-04 | F10 | M3: short links, forms.formalie.dev/s/{code} (5 easy characters) on the Share tab, server-side 302 to the form’s current link, visit count, removable, 404 page; Share card shows it and uses it for the QR code. Tested in the browser. |
| 2026-10-04 | F10 | Form language on non-open pages (owner): full, closed, expired, not-yet-open and password pages now use the form’s language (they fell back to English because no questions are sent then). |
| 2026-10-04 | F10 | M3: embed allowed websites (any / only listed; pasted addresses tidied; frame-ancestors header, Formalie previews always allowed) and a live Preview tab in the Embed code window. Tested in the browser (header with the list, back to any website). |
| 2026-10-04 | F10 | Dialogs (owner): the move grip no longer sits over the close button (close button in the header flow, grip beside it) and the close button is a round soft button. |
| 2026-10-04 | F10 | Short links (owner question "no conflict"): removed codes, and codes of forms deleted for good, are retired and never handed out again, so an old poster can never open another form. Tested. |
| 2026-10-04 | F10 | M3: "How your form’s links work" note on the Share tab (original · custom · short, none cancels another, common situations); Search & link preview card (title, description, image upload, hide from search engines, link-card and search-result previews) feeding the public page tags. Tested in the browser (tags, image, back to defaults). |
| 2026-10-04 | F10 | M3: invite-only (invitations with personal links, Invited / Opened / Responded / Revoked, resend, revoke, one response each) and organisation-only access (portal sign-in → pass → form, “Filling in as …”, respondent kept with the response). Tested end to end in the browser; fixed invitation changes blocking the page’s Save. |
| 2026-10-04 | F10 | Invitations take emails only (owner): chips split on comma / space / semicolon / new line, invalid ones red and blocking, duplicates merged. Embedded organisation-only forms open sign-in in a new tab. Staff test account staff@remedylegal.test (Lena Novak) + organisation-only form test steps in README. |
| 2026-10-04 | F10 | M3: people access per form, workspace default (edit / view / none) and per-person level (edit / view / responses only) on the Share tab; enforced on every form route; read-only editor with "View only" banner, responses-only page, limited menus. Fixed: the staff test user shared an id with another test user (unique ids now tested); the person picker added people by itself. |
| 2026-10-04 | F9/F10 | No side panel beside the form anywhere (owner): Side panel (renamed Slate accent) and Aurora designs and the Real estate template design now use the accent header; the layout is no longer offered; existing split themes open as a card with an accent header. |
| 2026-10-04 | F10 | Share tab split into two titled sections (owner, to avoid confusion): “Answering the form” (who can fill it in, limits, links, embed, link preview, for the people you send it to) and “Your team” (people with access, staff only, doesn’t change who can fill it in); notes on both. |
| 2026-10-04 | F10 | Revoked invitations can be removed from the list (owner); active ones must be revoked first; a response already sent is kept. |
| 2026-10-04 | All | No dashes (owner): every "—" (and spaced " – ") removed from text people read in all 20 languages, the template content and dictionaries, on-screen placeholders, docs, README and code comments (about 2,800). Sentences rewritten naturally per language; a test now fails on any dash. |
| 2026-10-04 | F10 | Image upload questions take pictures only (owner: a PDF on an image question was refused): the builder offers only picture types for image questions, warns when an image question allows other types with one-click "Change to File upload", and the form picker only offers pictures. |
| 2026-10-04 | F10 | Personal invitation links and sign-in passes show "Opening your form…" while the link is checked, instead of flashing "This form is by invitation only" first (owner). |
| 2026-10-04 | F10 | File rules and uploads always agree (owner question): the builder caps a question at 25 MB per file (the upload limit); files a device sends without a type (HEIC photos, some videos) are matched by extension for "All images / audio / video", pictures still checked by their bytes. |
| 2026-10-04 | F10 | Thank-you screen (owner: "Close this page" does nothing in Chrome / Edge, browsers block it): "Close this page" only when the browser allows it (opened by another page); otherwise "All done. You can close this tab." plus "Visit the {org} website" when the organisation has one; in embeds neither. |
| 2026-10-04 | F10 | "Can view" is view only (owner): only editors open the editor, logic, design, share settings and versions, save as template, duplicate or change availability; the API refuses the rest. View people get the overview without editor links and a read-only Preview; an editor address shows "Only people who can edit open the editor" with the way back. |
| 2026-10-04 | F10 | M3 item 6: preview page `/forms/[id]/preview` with device frames (desktop browser window with the form's address, tablet and phone at real sizes, turned sideways, scaled to fit), draft or live version, jump to any page or the thank-you screen, start again, shortcuts 1 / 2 / 3 / R; opened from the overview, the form menu and "Full preview" in the editor (saves first); "Can view" people preview here. Milestone 3 complete. |
| 2026-10-04 | F10 | Editor quick preview (owner: the note took space): "Fill it in like a respondent would. Nothing is sent." moved behind an ⓘ icon next to the title (click to read), the header is one slim line. |
| 2026-10-04 | F10 | M4 part 1: forms in several languages (decision 99). Form settings → More languages with dictionary fill and a translation screen (progress, to do filter, search, rich text), switching the main language to an offered one keeps everything; respondents get their link / browser language and a switcher (address gets `?lang=`), thank-you text and response language follow; switcher in both previews. Renderer `Form.vue` split (407 → 302 lines: sections and error wording composables, Progress, Notices, Nav, Thanks components). |
| 2026-10-04 | F10 | M4 part 2, polish and review: out-of-date translation marker; a full review of F10 fixed 13 issues (empty Trash only for editors, no draft text on unpublished public pages, image upload types agree on both sides, all access modes on the Share card, save and resume edge cases, invitation emails split on space, progress after a password, clearer /forms/open errors, language add only after a successful fill, one challenge per submission, freed upload previews, page-owned watchers, folder counts by access). F10 complete, waiting for the owner's review. |
| 2026-10-04 | F10 | Owner test: a form opens in its main language (Form settings → Form language), only `?lang=` opens another; the browser's language no longer decides. The language switcher moved into the page's top bar beside "Visit website" (side panel: beside the organisation; embeds and Minimal: above the form). Previews also start in the main language (they picked English before the form had loaded). |
| 2026-10-04 | F10 | Language switcher in the page's top bar looked squashed on phone widths (only the flag showed and the button lost its height): it now keeps the website button's height and a fixed width. |
| 2026-10-04 | F11 | M1: one response source for every page (decision 100: real submissions + stable sample responses; overview trend, sidebar counts and form lists follow it, so test submissions now show everywhere). Per-form Responses page and inbox with KPI sparklines, trend chart, review status, channels, languages, busiest forms, Summary per question, DataView table / grid with question columns and slim rating bars, response side panel (J / K, status, tags, notes, history), bulk status / delete. 20 languages. |
| 2026-10-04 | F11 | Owner review of M1: slim top strip (four numbers, sparkline, meters) with the list right below; Responses | Insights switch on the toolbar line (charts and per-question summary moved to Insights); rich grid cards (status edge, facts, answers by kind, tags, quick review); rich response panel (large header, one-click status bar, fact tiles, page cards with answered count, floating Previous / Next pill, copy link, delete); `?response=` opens a response. |
| 2026-10-04 | F11 | Owner review 2 (decision 101): two top cards with charts (Responses with daily bars; Review status as the design's thin-line status overview); theme status colours; grid cards in the design's task-card style with Answered progress; Columns in every DataView (drag or ↑ / ↓ to move, show / hide, reset); response panel without history, answers grouped by likeness with filter chips and two-column equal tiles; file viewer (pictures, PDF, video, audio, text; download otherwise) over 5-minute private links; sample files get stand-ins. |
| 2026-10-04 | F6 / F11 | Locked list-page format (decision 102) applied to the Forms list: two chart cards (responses across forms with daily bars; forms by status as thin lines that filter the list), Columns on the table, grid cards in the locked task-card format (updated pill, status, ⋯, red flag for unpublished changes, two-column facts, Completion bar, owner, key, counts). |
| 2026-10-04 | All lists | Owner: whole grid cards are clickable (anywhere except their own buttons, links and menus) and open the item; cards lift on hover, table rows highlight with a pointer. Built once in DataView (`openRow`), so every list gets it; the Forms list opens the form's overview. |
| 2026-10-04 | F6 / F11 | Form overview in the locked format: Responses and Review status chart cards on top (status opens filtered responses), latest four responses as cards, Highlights of the two most telling questions, then structure; share, details, activity on the side. Fixed: the overview's time to fill in was an estimate (5.2 min vs 3 min 44 s on Responses); it now comes from the responses. |
| 2026-10-04 | F11 | Responses page grouped by form (decision 103): chart cards for all forms, then forms with responses as table / grid (locked card with new count, review progress and 30-day sparkline); a form opens its own responses; sidebar New / Reviewed… list the forms that have them and open them filtered. Sidebar New dot in theme ink (was blue). Closed / archived forms' sample responses end weeks ago. |
| 2026-10-04 | F11 | Response panel answer groups in a rounded chip track (AppChipScroller): no scrollbar, edge fades in the track's own colour, mouse wheel moves sideways, almost hidden arrows, a clicked chip glides to the centre (RTL safe). Sidebar New / Reviewed / Approved / Rejected now visibly change the grouped Responses list: almost every form has every status, so the list looked the same; it now counts, sorts and highlights the chosen status (column, card figure) and opens forms filtered to it. |
| 2026-10-04 | F11 | Response panel files: each file question's tile is as wide as its files and they sit side by side on one row, wrapping only when the row is full (were one full-width row per question); files inside a tile wrap the same way instead of a sideways strip. |
| 2026-10-04 | F9 | Templates (categories, a category, Your templates) and Themes in the locked list format: two chart cards on top (forms from templates + use by category; theme use + themes by kind, a kind filters), table with Columns and a share-of-use bar, the locked card with the design in miniature, whole rows and cards open the item. New `GET /templates/insights` and `GET /themes/insights`; shared `DataShareBar`. |
| 2026-10-04 | F9 | Owner: Templates and Themes without chart cards, only the table / grid (locked card and table stay). Chart components and their texts removed; the insight endpoints stay for the cards' share of use. CLAUDE.md rule 21 notes the exception. |
| 2026-10-04 | F9 | Template, category and theme cards: bigger thumbnail, nothing below the facts (no share bar, no footer); the share of use stays in the table. |
| 2026-10-04 | F9 | Template, category and theme cards: thumbnail left in a fixed 16:9 frame (new clear `tile` miniature, all the same size), name right, then the buttons row, then the details. |
| 2026-10-04 | F9 | Theme cards: "Used in" reads "1 form" / "2 forms" like the table. CLAUDE.md rule 21: one card concept, the arrangement follows each page's purpose. |
| 2026-10-04 | F9 | Theme editor: saving without a name now brings the name field into view (scrolls the design panel back up; phones open the panel first), focuses it and says why in a toast; the red mark clears as soon as a name is typed. |
| 2026-10-04 | F11 | M2: editing answers. Editors get a pencil on every answer that can be changed; the dialog shows the form's own control, checks with the same rules (also on the server), records who / when / before / after in the history and the audit trail (question labels), and the tile shows an Edited mark. Corrected names and emails show as the respondent. Test: `answer-edit`. |
| 2026-10-04 | F11 | M2: filters by answers. Under "Questions" in the Filter menu: one filter per choice, yes / no or rating question and "Left empty"; a Tags filter from the tags in use (`GET /forms/{id}/responses/tags`); chips read "Question: answer". DataView follows its filters live, so options that load later (tags, folders) now show. Test: `answer-filter`. |
| 2026-10-04 | F11 | M2: bulk tags. A Tags button in the selection bar: type a tag or pick one in use, Add to N / Remove; toast confirms, the list and the Tags filter refresh. |
| 2026-10-04 | F11 | M2 done: possible duplicates can be cleared ("Not a duplicate", recorded) or rejected (status Rejected + tag "duplicate") from the panel. M2 complete: edit answers, filters by answers and tags, bulk tags, duplicate review. Next: M3 exports. |
| 2026-10-04 | F10 / F9 | Page designs M1: Resources → Pages (All · Formalie · Saved · Created with counts), the library in the Themes table / grid format with page miniatures, 10 ready-made Formalie designs, the page editor (Page + Background controls, live framed preview, read-only Formalie designs with Duplicate to edit, save-without-name shows the field), `/page-designs` API with audit. Shared `revealField` helper. Test: `page-design`. |
| 2026-10-04 | F10 / F9 | Page designs M2: ten page styles (new: Banner, Centred, Headline, Corporate, Compact, Floating, each its own component on a shared `useFrameParts`), 22 ready-made designs, one miniature (`PageDesignsThumb`) used in the library and in the designer's style picker. Tone is hidden where a style has no bar or panel. |
| 2026-10-04 | F10 / F9 | Page designs M3: the designer (and the theme editor) has a Page designs group with every design as a miniature (yours first); one click puts that page around the form (only the page changes, undoable; asks when it replaces a page you made), "Save page" stores this form's page in Resources → Pages. Picking a theme or a starting point keeps an applied page design. Designer: Starting points and Your themes are collapsible groups like the rest, open groups get more space below. |
| 2026-10-04 | F10 / F9 | Renamed to Landing pages (decision 107): menu, `/settings/landing-pages`, designer groups ("Landing pages", "Landing page style"), editor, toasts and audit labels in all 20 languages. |
| 2026-10-04 | All | PROGRESS brought up to date (owner): F10 marked done after the owner's review, F11 milestones M1 and M2 done with current wording, Landing pages library recorded as done, built requests closed in the New requests log. Next: F11 M3 exports. |
| 2026-10-05 | F11 | M3 exports: Export on the Responses toolbar and selection bar (Excel · CSV · PDF; all / matching filters / selected; table columns or every question; review details), background file with a percentage bar, then Download over a one-time private link; Responses → Exports lists every export (table and locked card, live progress, Download, Delete, kept 7 days). API `POST /forms/{id}/responses/export`, `/responses/exports…`, audit exported / downloaded / deleted. Tests: `responses/export`. |
| 2026-10-05 | F11 | Owner: date range ("Any time") was missing on the Responses page (grouped by form); added there (counts cover only responses received in the period, forms without any drop out) and on Exports (made in the period). The per-form list already had it. |
| 2026-10-05 | F11 | Owner: the all-forms Insights was one-sided (only Responses over time on the left, a long column on the right). Now balanced rows: Responses over time + At a glance (period with change, per day, busiest day, time to fill in, to review, total); Review status · How they came in · Languages as three equal cards; Busiest forms + Busiest days of the week (averages per weekday). The per-form Insights stays as it was. |
| 2026-10-05 | F11 | Fix (owner): on a form's responses page the sidebar opened Forms instead of Responses (the page lives under /forms/{id}/responses). Menu entries can now claim or give up paths by pattern (`alsoMatch` / `exceptMatch`), so a form's responses open the Responses menu; the form's other pages still open Forms. |
| 2026-10-05 | F11 | Owner: "where do I create the export?" Export was only on a form's responses toolbar. Now also: "New export" on Responses → Exports (header and empty state; the dialog first asks which form, with search) and "Export responses" in each form's ⋯ menu on the Responses page (table and cards). |
| 2026-10-05 | F11 | Owner: an outside click closed the export dialog mid-export (looked like a failure). Once Export is pressed (preparing, progress, ready) the dialog only closes with Close or ✕, never by an outside click or Esc; same for the audit trail's export dialog. |
| 2026-10-05 | F11 | Owner: Excel downloaded as CSV. The mock now writes a real .xlsx (small built-in writer, no new library: bold frozen header row, column widths, numbers as numbers, formula-looking text kept as text) for response exports and the audit trail export. |
| 2026-10-05 | F11 | Owner: the PDF export was plain text "with no life". Now a designed report in the form's own colour: cover band with the organisation, form, who exported what and when; status tiles (responses, new, reviewed, approved, rejected); one card per response (number, name, coloured status pill, email, submitted, channel, tags) with questions and answers in two columns; cards never start at a page foot and continue with "(continued)"; brand bar, form and organisation on every page and "Page x of y". Small layout writer `server/mock/core/pdfDoc.ts` (measured Helvetica text, rounded boxes); the plain-text writer is gone. |
| 2026-10-05 | F11 / F14 | Owner: the PDF used the form's theme colour, not the application's look. The report now uses the portal's monochrome ink and status colours. New request recorded in F14: Settings → Appearance, each workspace customises the whole portal (colours, background, rail, menu, header, footer, main body, light / dark), and exports follow it. |
| 2026-10-05 | F11 | M4 Folders (decision 109): folder colours (create / edit dialog with a swatch palette, keyboard friendly), sidebar FOLDERS group (coloured icons, counts, up to six, All folders, + creates and opens), `/folders` (table / locked card with numbers and sparklines; edit, new form, delete when empty), folder page (colour, Edit / Delete / New form, two chart cards, the folder's forms in the same list as the Forms page). The Forms page list became `FormsListBrowser` (shared). New form accepts `?folder=`. Archived forms are left out of folder counts everywhere. API `/folders/overview`, `/folders/{id}`, colour on create / PATCH. |
| 2026-10-05 | F11 | Folders as they grow (owner): the sidebar shows at most five per person (pinned first, then recently opened, then the busiest; `pickSidebarFolders`), pin / unpin from the folder menus (up to five, pin mark in the sidebar), the FOLDERS group folds away (remembered), "All folders" shows the total, and every folder is in the command palette (Ctrl / ⌘ K) in its colour with its count. Pickers were already searchable. A line now separates FOLDERS from SYSTEM. Test: `forms/folders`. |
| 2026-10-05 | F11 | Folder colours (owner): 18 named colours plus Custom (Nuxt UI colour picker and a hex box, saved as #rrggbb); the folder's colour now also shows on its page header (desktop), and custom colours work everywhere (sidebar, command palette, cards, table, header) through a class-or-style helper. A folder created a moment before the server picked up colours had lost its colour; creating with a colour works. |
| 2026-10-05 | F11 | Fix (owner): in the response panel the Notes "Add note" button sat under the floating Previous / Next bar. More room at the bottom of the panel, so the button now ends well above the bar and its fade. |
| 2026-10-05 | F11 | M4 polish and review: no overflow at 375 / 768 px on Responses, Exports, Folders, Landing pages, Themes, Templates and Forms; Arabic (RTL) checked, forward arrows now mirror; light mode checked; folder colour swatches now move keyboard focus with the arrow keys; the folder page error state offers Try again. F11 complete, waiting for the owner's review. |
| 2026-10-05 | F11 | Fix (owner): still more room at the bottom of the response panel (10 → 14 rem), so the Notes section and its Add note button sit well clear of the Previous / Next bar. |
| 2026-10-05 | F11 | Fix (owner): most folder colour swatches looked empty in the New / Edit folder dialog (and those colours were missing on folder icons) because Tailwind did not scan `shared/`, where the colour classes live. `main.css` now adds `@source` for `shared/` (decision 110); all 18 colours show. |
| 2026-10-05 | F12 | M1 Connections (decision 111): engine catalogue with each database's own settings (MySQL / MariaDB, PostgreSQL, SQL Server, Oracle) and checks on both sides; permission catalogue with every operation by level and grant statements per engine for the connection's own names; Add / Edit connection in six steps with help, live test (steps, errors with fixes, permissions, advice), write-only secrets, blocked addresses, outgoing addresses; Connections page (two chart cards, table / card, filters, sidebar by status) and connection panel (Test now, Enabled, settings, permissions, health, J / K); audit area Data sources. Mock API `/datasources/**` with dev triggers (02-DEV-ENVIRONMENT). Tests: `datasources/engines`, `datasources/simulation`. |
| 2026-10-05 | F12 | Owner corrections (decision 112): no administrator-account or extra-rights warnings (any account; configuration encrypted at rest); SSH tunnel copy says it is only for private networks; Access step rebuilt: Formalie's tables are required (prefix formalie_ / fmly_ / form_, own schema on PostgreSQL / SQL Server / Oracle) and the other tables optional (not shared · read · read and write, default read and write); permission levels own · read · write with new grant statements per engine; a test that can't create Formalie's tables fails (`FRM-DEST-1012`); stored connections upgraded. |
| 2026-10-05 | F12 | Owner: schema was asked twice. The server step no longer has a schema field (PostgreSQL, SQL Server, Oracle); the Access step has two separate parts, "Your responses" (required, prefix and response-table schema) and "Your other tables" (optional, not used for responses, with their schemas). Stored connections moved over. |
| 2026-10-05 | F12 | Owner: schemas for your other tables can be separated with space, comma or semicolon as well as Enter (also from phone keyboards and pasted lists). |
| 2026-10-05 | F12 | Owner wording: no "not used for responses" or "optional" (a form may store responses in a table of theirs). Access step: "Your responses" (Formalie's tables or a table of yours) and "Other database operations" (Full access · Read only · None, default Full access); Full access now also creates and changes tables in their schemas (new operation and grants per engine). |
| 2026-10-05 | F12 | Owner: ports are the usual defaults, not a rule. Engine cards say "Default port …"; the Port field explains it is prefilled with the engine's usual port and to enter their own if the database uses another (Oracle: TCPS often 2484). |
| 2026-10-05 | F12 | Owner: optional connection fields (e.g. SQL Server instance name, SSH key passphrase, certificates) now say "Optional" beside their label; instance placeholder PROD01 instead of SQLEXPRESS (a development edition). |
| 2026-10-05 | F12 | M2 Response storage (decision 113): per-form "Where responses are stored" (overview card, setup at /forms/[id]/storage: connection → table (create from the form or a table of yours) → columns (per-engine types, auto-matching, checks) → options (new row or update-or-insert, JSON or text, value or label, extra facts) → review with the exact SQL); background delivery with statuses, retries, pause / resume, send earlier responses with progress, add columns for new questions; Destinations page (chart cards, table / card, panel). Mock: synthetic tables per connection, delivery status derived per response. Tests: `datasources/tables`. |
| 2026-10-05 | F12 | Owner: forms and responses lists (table and grid) show where each form's responses are kept, after its folder with a thin divider: a database icon (tooltip names the connection) or the Formalie mark. List rows carry `storage { mode, datasource, engine }`. |
| 2026-10-05 | F12 | Owner: the storage icon was too dark. Connections now show their engine's own logo (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server) and Formalie's storage a plain database icon, both in the text colour, no dark tile. |
| 2026-10-05 | F12 | Owner: no icon for Formalie's own storage (the default); only forms stored in a database show the divider and their engine's logo. |
| 2026-10-05 | F12 | Owner: our standard for tables Formalie creates, one row per response found by its response id (no writing choice; retries never duplicate); "Create a table from the form" marked Recommended, a table of theirs comes with a caution; a Formalie table's panel offers a ready view named after the questions for their systems. |
| 2026-10-05 | F12 | Owner: the table name's prefix is a fixed label attached to the field; people type only the rest (at least 6 characters, letters, numbers and underscores, within the engine's limit), checked in the form and on the server. Short form names get "_responses" in the suggestion. |
| 2026-10-05 | F12 | Owner: column names of tables Formalie creates are fixed (from the question keys); readable names come from the view. Answers can still be left out. |
| 2026-10-05 | F12 | Owner: how several values and choices are written is chosen at setup and locked afterwards (UI and API), so every row stays alike. |
| 2026-10-05 | F12 | New response tables store the response number and review status by default; the respondent's email stays opt-in (personal data). |
| 2026-10-05 | F12 | Response tables: `language` VARCHAR(35) and `review_status` VARCHAR(16) (were email-sized); an index on `submitted_at` is created with the table. |
| 2026-10-05 | F12 | M3 part 1, Database explorer (decision 114): tree, rows (DataView with search, filters, sort, Columns, Table / Grid), row panel, structure, export with progress; failing connections show their error. Fix found while testing: a response table on a PostgreSQL connection had been saved with MySQL types (a slower answer for an earlier-picked connection replaced the chosen one); the setup now ignores stale answers, the server sets the types of tables Formalie creates itself, and stored tables were repaired. |
| 2026-10-05 | F12 | M3 part 2, changing data: add / change / delete rows of the organisation's tables (Full access) with a form built from the columns and one set of value rules on both sides; import CSV / Excel with column matching, preview, progress and a report of skipped rows (CSV and .xlsx read without a library). Tests: `datasources/values`, `datasources/tabular`, `datasources/import`. M3 complete. |
| 2026-10-05 | F12 | Explorer layout (owner): connection and table tree in the sidebar's menu column with a back arrow to the menu (`useSidebarTakeover`, `AppSidebarTakeover`, page content teleported); same, resizable width as the menu; one-line table strip; DataView `dense` (28px rows, column lines) and `table-only` (no grid). |
| 2026-10-05 | F12 | Explorer: JSON and SQL (INSERT per engine) exports; one open table in the tree; account at the rail's foot in explorer mode. Test: `datasources/exportFormats`. |
| 2026-10-05 | F12 | Import into tables removed (owner: not supported for now): dialog, routes, file readers, errors FRM-DEST-1020 / 1021, audit `data.rows_imported`. Row changes stay limited to the organisation's own tables. |
| 2026-10-05 | F12 | Explorer backend rules in API-CONTRACT (paging in the database, count capped at 10,000 with `meta.total_capped` shown as "10,000+", 5 s statement limit → FRM-DEST-1011, capped facets, catalogue-only tree, streamed and capped exports, workspace check). Fixed duplicate auto-import warnings (`DbEngine` imported from its one home, connection `FieldType` renamed `ConnectionFieldType`, one `quoteName`). |
| 2026-10-05 | F12 | Explorer structure changes (owner): New table, columns, indexes, rename, empty, delete for their own tables with Full access, never Formalie's; statements per engine shown first and run as shown; mock keeps the changes (`server/mock/data/tableEdits.ts`). Tests: `datasources/ddl`. |
| 2026-10-05 | shell / F12 | Right-click menus everywhere (`AppContextMenu`, `useContextMenu`, DataView `rowMenu`, explorer `useExplorerMenus`); Help & support at the rail's foot; no types beside column names; explorer dialogs keep their input on outside clicks (`AppModal keep-open`). |
| 2026-10-05 | all | One empty / not-found / error state everywhere (`AppEmpty`, replacing UEmpty in 35 files and 15 hand-made ones): evenly centred, a layered icon tile, title, short description, next step; sizes md / sm / xs; error icons tint red. |
| 2026-10-05 | F12 | Explorer export scope: this page (default) or all matching rows up to 5,000 (`EXPORT_MAX_ROWS`, `TableExport.scope / total / capped`), in the button and the right-click menus. |
| 2026-10-05 | F12 | Explorer as an editor: in-place cell editing (`ExplorerEditCell`, one value per PATCH, same checks as the row form, a click opens the panel after a short pause so a double-click can edit) and resizable columns (DataView `resizable`, `useColumnWidths`, start widths by type, fixed table layout). |
| 2026-10-05 | F12 | M4 part 1, Query editor: CodeMirror 6 (owner-approved) with the connection's dialect and schema completion, tabs, run selection / statement at cursor, stop, `:name` parameters, results grid (row numbers, resizable, paging, copy), changing statements confirmed with what they touch, Read only and response-table protection, the database's problem on its line, history in the side panel, audit `data.query_run`. Mock runner for common SELECT / INSERT / UPDATE / DELETE. Tests: `datasources/sql`. |
| 2026-10-05 | F12 | M4 part 2: saved queries (personal / shared, owner-only changes, run counts; Save with Ctrl / ⌘ + S, an unsaved-changes dot on the tab, a Saved tab in the side panel, `?saved=` links) and the Saved queries page (two chart cards, DataView table and cards, edit / share / delete), export of results (CSV / Excel / JSON, this page or up to 5,000 rows, through the explorer's export flow), Format (built-in SQL formatter). M4 complete. Tests: `datasources/sql` (format). |
| 2026-10-05 | F12 | M5: Activity page (audit trail area `data`, kinds in `shared/utils/datasources/activity.ts`, insights `GET /datasources/activity/insights`, the audit panel per event), Exports opens Activity filtered to exports, overview marks every section live, seeded data events in the mock's history; phone (375) and tablet (768) sweep of all eight Data sources pages: no overflow. F12 complete; stopped for the owner's review. |
| 2026-10-05 | F12 | Run all in the Query editor (`useQueryRunner.runAll`, a result tab per statement in `QueryOutput`, Ctrl / ⌘ + Shift + Enter) and a lazy tree (`useDatabaseTables`: names first with `columns=none`, up to 500 and server search beyond, columns per table from `GET /explorer/columns` when opened or named in the editor). PROGRESS tidy: every open F12 item resolved (done, or moved to F15e option sets, F22 permissions, later for scheduled exports). F12 still waiting for the owner's review. |
| 2026-10-05 | F18 / F12 | Analytics (F18, brought forward): dashboard page with KPI cards (`ChartsKpi`), the conversion flow chart (`ChartsFlow`, the design's hatched two-line chart), form overview with where people stop, DataView of every form with cards and a funnel panel, CSV download, NPS on 0 to 10 questions in Responses → Insights; mock `/analytics/*`. Data sources overview rebuilt the same way: KPI cards, database traffic (operations vs responses delivered, kinds that open Activity), connection overview with uptime and latest activity, recent activity table, supported databases and shortcuts. Phone (375) checked: no overflow. Tests: `analytics/csv`. |
| 2026-10-06 | F13 | M1 Services and endpoints: Services and Endpoints pages (rule 21, chart cards, DataView table / cards, panels), service dialog, endpoint wizard (form → name and service → methods → questions → review, address preview and example call), shared rules `shared/utils/apiService/endpoints.ts`, mock `/api-service/settings`, `/api-services`, `/api-endpoints` (+ insights, duplicate, form-fields), audit area `api` (10 events), errors `FRM-API-1001…1003`. Fixed in the mock: list filters sent as `filter[key]` were ignored by Connections, Destinations, Saved queries, explorer rows (`filtersOf`). Tests: `apiService/endpoints`. |
| 2026-10-06 | F13 | M2 Tokens and headers: Tokens & headers page (rule 21; view switch Tokens | Headers), new token (live / test, bearer or client id + secret, scopes, expiry, signing; secrets shown once), rotate with a grace period, revoke, delete; address key rotation; required headers per endpoint (wizard, panel, example call); shared rules `shared/utils/apiService/tokens.ts`. Mock public API `server/mock/publicApi.ts` (`/public-api/**` and the `api.formalie.dev` host): token, list, one, create (Idempotency-Key replay), change, delete, the form's rules, scopes, required headers, signatures, test mode; file ids returned as references. Tests: `apiService/tokens`. |
| 2026-10-06 | F13 | M3 Access rules: Access rules page (rule 21; view switch Rules | Rate limits), rule dialog (allow / block; IPs and ranges, domains, countries, regions; all, a service or an endpoint), rule panel, Test a caller, rate limits per token / IP / endpoint; shared rules `shared/utils/apiService/access.ts` (IPv4 / IPv6 ranges, continents); mock `/api-access-rules` (+ insights, test), `/api-service/limits`; the mock public API applies rules (`FRM-API-1015`) and limits (`429` + `Retry-After`). Also: token prefixes `formalie_…`, header `Formalie-Key` (owner). Tests: `apiService/access`. |
| 2026-10-06 | F13 | M4 Request logs and analytics: Request logs page (rule 21, panel with headers and kept bodies, log settings, CSV download), API Analytics page and the API service Overview in the dashboard style (`ChartsKpi`, `ChartsFlow`, endpoint overview, breakdowns, recent calls); mock `/api-logs` (+ insights, settings, one), `/api-analytics`; the mock public API logs every call (bodies only when kept, personal answers masked); sample history of 7 days from the endpoints' daily numbers, respecting token scopes. |
| 2026-10-06 | F13 | M5 Docs and testing: Docs & testing page (per service: endpoints, per-method body tables with real allowed values, query options, code in five languages, answers, a shared guide with tokens, `Formalie-Key`, files, signing and error codes), Download OpenAPI 3.1, try-it console (endpoint panel Test button too; console test token, nothing stored; mock `POST /api-endpoints/{id}/try`). Files through the API: `POST {apiKey}/{endpoint}/files?field=` (multipart `file`, the form page's type and size checks) → an id for the JSON. Fixed: the public API now uses the same worked-out question choices as the portal (a form-required question is always accepted); currency, duration and IBAN examples match the form's checks. Tests: `apiService/snippets`, `apiService/samples`. |
| 2026-10-06 | F13 | M6 Webhooks and API keys: Webhooks page (chart cards, DataView, panel with Send a test, recent deliveries, events and forms, signature check code; Deliveries view with its panel, Send again / Retry now), signed deliveries really sent by the mock with retries and auto-pause, fired from the form page, the API service, the portal and the management API (`server/mock/data/integrationStore.ts`, `routes/webhooks.ts`); API keys page and panel, mock management API `/v1/…` (`server/mock/managementApi.ts`, `routes/apiKeys.ts`); shared `shared/types/integrations.ts`, `shared/utils/integrations/webhooks.ts`; masking moved to `server/mock/core/mask.ts`. Checked with a local receiver (signature verified, status events with the previous status) and with a key (permissions, 401, 404). F13 complete; stopped for the owner's review. Tests: `integrations/webhooks`. |
| 2026-10-06 | F13 | M7 owner review: guided setup (shared five-step journey on the Overview and in every dialog; service, token and access rule dialogs in steps with what each is and what comes next; New endpoint asks for a service first, starts not live and ends with a *Before it goes live* checklist that also sits in the endpoint panel; test tokens may call not-live endpoints); tokens, API keys and webhook secrets viewable again after the password (`FRM-AUTH-1013`, five tries per 15 minutes, audited); access rules with chips (comma, space, Enter, paste; wrong values stay with the reason) and an Anonymous networks kind (VPN, proxy, Tor, hosting; mock `X-Debug-Network`); `415 FRM-API-1017` and `413 FRM-API-1018`; not-found details name the wrong part; failure matrix of 44 calls all answered as documented; Docs & testing redesigned (sticky navigation with scroll spy, hero, getting started, method sections beside a dark code panel with answer tabs), Try it as a drawer, method colours everywhere; rail + menu grouped (Forms: New form, From a template, New template; Operations: Add database, New API service, Query editor, Database explorer); README test cases. Fixed: the dialog setup never ran when a page opened it on load; the sample signing token had no signing secret. |
| 2026-10-06 | F13 / F10 / F7 / F8 | Owner fixes: designer applies themes, starting points and page designs at once with an Undo toast (no confirm); form channels (`channels`: link, embed, api; Share → Where people can answer; API only hides every web card and answers not found on the link, key address, embed, short link and the shared forms host, checked with curl), the endpoint wizard lists ready forms and offers Publish for the API only / Open to the API, endpoints refuse forms without the API (`FRM-API-1019`, public API `FRM-API-1007 not_for_api`, endpoint checklist says so); clean question keys from labels with `_2` on a clash, keys of published versions fixed and reserved (`published_keys` from the builder route); required header values in the docs' code, Try it and OpenAPI. |
| 2026-10-06 | F7 / F10 / F13 | Field icons: one helper (`app/utils/forms/field-icons.ts`, `useFieldIcon`) gives every boxed field its type's icon (text, numbers, dropdowns, dates and times, full name, duration, address parts with their own); `settings.field_icons` (default on) with Show / Hide in Form settings beside label position, the canvas and every form follow it. API and form changes: endpoints that follow the latest version use each newly published version; Publish lists the endpoints and what changes for their callers (`apiChanges`: added, now required, removed; labels alone change nothing) and suggests pinning a version first. Builder route adds `live_fields`; endpoints list filter `form`. Tests: `apiService/endpoints` (apiChanges). |
| 2026-10-06 | F10 | Field icons from the label: built-in multilingual word list (`label-icons.ts`) for general fields, type icon as fallback; checked on the Account form (person, mail, phone, cake, map pin, buildings, mailbox). Tests: `forms/label-icons`. |
| 2026-10-06 | F13 | API names: every endpoint question has a `name` (clean, from the label, unique, not reserved; editable in the wizard's Questions step with checks), existing endpoints given theirs once; the public API translates names ↔ question keys (bodies, answers, filters, file uploads, error details; unknown names reported as sent); examples, docs and OpenAPI use names; example values follow the label (First name → Alex, Phone → a phone number…). Signing headers in examples when a signing token can call the endpoint (`setup.signing_tokens`). Headers tab lists endpoints with own headers by service, values masked, view and copy. Tokens whose scope points at a deleted service or endpoint show it (never "All") with a warning. Checked with Try it on /account: names in and out, old key refused as sent. Tests: API names, label samples. |
| 2026-10-06 | F13 | Three headers, nothing else: the public API requires `Formalie-Key` (new unique id per call, 400 FRM-API-1011 when missing or invalid) on every method, reads bodies as JSON, ignores any other header; custom endpoint headers and signed calls removed in the UI (wizard, endpoint panel, token dialog, secrets, Headers tab) and cleared from saved data; every answer carries the token's expiry (`Formalie-Token-Expires`, `meta.token_expires_at`, `meta.token_expires_in_days`). Examples, Docs (new Headers and Token expiry topics), Try it and OpenAPI show the three headers on every method; code samples generate the key per language. Checked with curl: no key 400, short key 400, with the three 200 plus expiry. Tests: snippets. |
| 2026-10-06 | F13 | API keys folded into tokens (owner): `ApiTokenScopes.manage` (six rights, none by default) set in the token dialog's new _Manage forms and responses_ field and shown in the token panel; the management API (`/v1`) signs in with tokens across workspaces (static and short-lived), checks the right (`403 FRM-API-1009`, `manage: <right>`), requires the Formalie-Key, counts in Request logs and carries the expiry tracker; API keys page, components, routes, types and saved keys removed (old keys 401). Docs: new _Manage forms and responses_ topic with the /v1 calls; the file upload sample sends the Formalie-Key. Headers tab expiry card redesigned in the Docs style. Checked with curl: no token 401, old key 401, token without rights 403. |
| 2026-10-06 | F13 | Examples with the real token: the endpoint panel's Request and the Docs code samples show a token that may call the endpoint (preferring one limited to it, then its service, live before test), masked as its prefix and last four, with its name linking to it in Tokens & headers, or a Make a token link when none may (`useCallerToken`). New tokens are named after what they may call ("Account Service · /account", or "Account Service token"), unique among the workspace's tokens, until the person types a name. |
| 2026-10-06 | F13 | Formalie-Key rules (owner): required on POST, optional on GET / PUT / DELETE (checked when sent); `checkCallKey` (16 to 100 characters, no simple patterns: `short`, `weak`, `invalid`, `missing`); POST retries stored 24 hours per endpoint and key with the body's hash (`canonicalJson`): same body → first record (`meta.replayed`), other body → `409 FRM-API-1020`; examples, Docs chips, Try it, OpenAPI (required on POST only) and the Headers tab say so. Management API (`/v1`), token management rights and the Docs topic removed. Checked with calls: GET without key 200, short 400, POST without key 400, `1234567890123456` / `aaaabbbbaaaabbbb` weak 400, new POST 201, retry 200 replayed, other body 409, PUT / DELETE without key 200; in the browser: panel example (masked token, key on POST only), Docs samples and chips, token dialog auto-name. Tests: key check, canonical JSON, snippets. |
| 2026-10-06 | F13 | Sign-in ways: Docs Getting started section `ApiDocsAuth` (bearer token vs client id and secret, never both, warning, how each endpoint signs in from `useCallerToken().kindsFor`), header chips follow it; `ApiCallToken` under every example names the token and its way; client tokens get a step 1 (`/token` with the real client id, never the secret) and `Bearer <short-lived token from /token>` in the panel and Docs code. Server: client id or secret as Bearer → 1010 `client_credentials`, bearer token to /token → 1010 `bearer_token`. Checked with calls (four mix-ups and a right /token) and in the browser (Customer onboarding: bearer; Partner bookings: both, Partner sandbox example with the /token step). |
| 2026-10-06 | F13 | Endpoint wizard step 1 lists only published forms open to the API; nothing in it changes a form any more (the not-ready list with one-click Publish for the API only / Open to the API is removed); when none is ready the empty state says to turn on API under Share and publish, with a link to Forms. Checked in the browser. |
| 2026-10-06 | F13 | New endpoint, created page: Open the endpoint also below the checklist, right-aligned under Go live (the header button stays). Checked in the browser with a throwaway endpoint (made through the wizard, opened with the new button, deleted). |
| 2026-10-06 | F13 | Token dialog step 1: the type is now "How it signs in" with a line on the two ways (never both), nothing pre-chosen, Continue asks to choose (owner: a Bearer default went unnoticed). Checked in the browser: Continue without a choice stays with the message, choosing Client id and secret goes on. |
| 2026-10-06 | F13 | Local webhook receiver for testing: `pnpm webhook:listen` (`scripts/webhook-receiver.mjs`, no dependencies) prints each delivery, checks the signature with `WEBHOOK_SECRET`, answers `FAIL=500` to try retries and auto-pause; README test steps updated. Checked: a signed call shows valid, a wrong signature shows WRONG. |
| 2026-10-06 | F13 | Duplicates through the API (owner: a new key sent the same record again): POST now applies the form's own rules like the web page (`fingerprintOf` moved to the response store and shared): same answers → 409 FRM-RESP-1005, identity email same → 409 FRM-RESP-1006, typo-close → flagged possible duplicate; responses deleted (API or portal) no longer count, web page included. Checked with calls: new 201, retry replayed, new key same data 409 (also with keys in another order), same email 409, another person 201, after a delete the same data 201; test records removed. |
| 2026-10-06 | F13 | Webhook tokens (owner): token type `webhook` (no scope, live, `formalie_hook_live_`, refused by the API with `webhook_token`); webhook dialog picks one or makes "{name} · webhook" (shown once with the headers); panel shows the token with Open the token and a warning when it is gone; deliveries send Authorization / Content-Type / Formalie-Key (delivery id, same on retries), logged masked; no usable token → the try fails with `token`; webhook rotate / reveal routes and signing removed; existing webhooks migrated to tokens; Checking the token code (Node, Python, PHP); `pnpm webhook:listen` checks `WEBHOOK_TOKEN` and flags repeats. FRM-RESP-1006 details are plain fields. Checked: migration (CRM sync · webhook), a new webhook to the local receiver (token valid, Formalie-Key dlv_…), the webhook token refused by the API, masked log. |
| 2026-10-06 | F13 | "Docs & testing" is now "API Documentation" (owner): `nav.apiDocs` (menu, page title, breadcrumb, command palette) and the four guidance sentences that name it, in every language; README and dev guide follow. |
| 2026-10-06 | F13 | Webhooks, owner review: the local receiver now requires `WEBHOOK_TOKEN` (will not start without it), refuses a missing or wrong token with 401 before reading the body, answers a repeated Formalie-Key without handling it again; webhook answers use the clean API names (the form's endpoint names, else from the labels; masking follows), never internal keys. Checked: no token 401, wrong 401, right 200, retry not handled twice; a real response.created arrived with token valid and clean names. |
| 2026-10-06 | F13 | Owner tested the whole API service end to end (services, endpoints, tokens of all three kinds, access rules, API Documentation, Postman, duplicates and Formalie-Key, webhooks with the local receiver): phase closed. Stale open items ticked; left for the backend: TLS only and CORS for browser callers; dashboard and roles stay in F21 / F22. |
| 2026-10-06 | F14 | M1 Settings frame and basics: one saved settings record per workspace (`settingsStore`, onboarding reads and writes it), `/settings` routes with shared validation (`shared/utils/settings/schemas.ts`) and field-by-field audit; Settings navigator in the menu column (takeover) or a Sections panel, overview with setup ring, next step and section statuses, search (navigator and Ctrl+K); Company (with a receipt-style preview), Branding (pictures upload at once; live sign-in preview; the sign-in page, its showcase and the browser tab icon use the branding), Language and region (live preview; useFormat applies time zone, short date format, number signs and currency everywhere; form language pickers follow form languages). Checked in the browser: overview statuses, Company save with a field error refused then saved, Branding uploads and preview, tab icon after reload, number format applied on another page (13.735), leave warning, phone layout; test edits undone. Tests: settings rules. |
| 2026-10-07 | F14 | M2 Organisation data: `orgStore` (per workspace, demo workspaces keep their sample departments' ids, new ones start empty), `/org/{kind}` routes (list, insights, CRUD, archive / restore, merge with field restrictions moved, import, usage, delete only when unused; FRM-ORG-1001 / 1002; audit `settings.org_*`), `/directory` reads it; Settings pages Departments, Job titles, Teams and locations (switch: teams, locations, cost centres) in the locked list format with Import (paste or CSV, preview) and Merge (also for selected rows); builder Field access gains Job titles (dropdown), an empty state linking to Settings and stale-entry marks. Checked in the browser: departments overview and cards, import preview (header, duplicates, too long) and import, merge into Finance with the panel opening, the builder listing the job titles; test entries removed and the form field put back. |
| 2026-10-07 | F14 | M3 Sign-in and security: sections `signin` and `security` in the settings store (backfilled for existing workspaces), the sign-in methods now come from Settings; mock auth applies everything: code expiry and tries per workspace, SMS on / off, allowed domains (FRM-AUTH-1014), expired passwords (1015, sign-in opens the reset), IP allowlist at sign-in and on every request (1016), password rules and no reuse on reset (1007 / 1018), idle and maximum session length; lock-out guard (1017); sessions list and sign out (one or everyone else); sign-in activity from the audit trail. Pages Sign-in (method cards, code rules, domains, live preview) and Security (activity card, password rules with a try field, sessions, allowlist). Checked in the browser: domain list refused without our own domain then saved, SMS off, IP allowlist refused without our address then saved with it (portal kept working), try-a-password with Symbol required, overview statuses, phone layout; test changes reverted. |
| 2026-10-07 | F14 | M4 Notifications and emails: sections `notifications` and `emails`; mock notification store (`notify()` follows the rules: in-app feed per person, emails or the daily summary) hooked into responses (form page and API: new, possible duplicate, form full), blocked sign-ins and locked codes, paused webhooks, and (when the feed is read) forms closing within a day and finished exports; `/notifications` feed routes; bell with unread count and a real panel (Today / Earlier, open goes to the item). Emails: renderer with the workspace's look, default texts per language (`server/mock/data/emailDefaults/`), sent log (codes never stored), template editor with placeholders, live preview, test send; sign-in and reset code emails go to the log. Per-form response emails in the builder (team, outside addresses with masked personal answers, respondent copy). Checked in the browser: settings pages, a real response showing in the bell and opening the exact response, a test email and its preview, a form published with team + outside + copy (three correct emails: link only for the team, email masked for the outside address, copy to the respondent), then switched off and republished. |
| 2026-10-07 | F14 | M5 Privacy, data and form defaults: sections `privacy` and `form_defaults`; retention (`retentionStore`: per-form or workspace limit, preview, removal on save and daily, audited), Keep responses in the builder's form settings; privacy notice link and consent line on public forms; data requests (find, export JSON, delete with typed confirmation, audited with masked address); form defaults applied to new blank and template forms and preselected in the new-form dialog. Checked in the browser: retention preview (30 days → 47,717 sample responses) and the confirmation on Ctrl+S, not saved; data request search for a test respondent; notice and consent on a live form, then turned off; defaults set, a new form starting with them (then moved to Trash), defaults put back. |
| 2026-10-07 | F14 | M6 Appearance: section `appearance` (presets, primary incl. brand with contrast check, greys, background, corners, font, text size, dark rail / menu, menu counts, breadcrumbs, search, footer, width, spacing); `useAppearance` applies it for everyone (Nuxt UI colours + CSS variables, the primary also takes the design's inverted accent), the shell reads the rest; the Appearance page makes the real portal the live preview while editing. Checked in the browser: Midnight (dark rail and menu in light mode), Ocean saved with centred and compact, the Forms page in light and dark wearing it, then Reset to Formalie saved. |
| 2026-10-07 | F14 | M7 Address, domain and organisations: `addressStore` (subdomain change with 90-day redirect via the host resolver, own domain with CNAME / TXT and a real DNS check, verified domains resolve to the workspace), Settings → Address and domain; organisations (`organisationStore`, `/organisations` routes, archive / restore, form move), request scope (`core/scope.ts`, header `x-formalie-organisation`) narrowing every list, new forms in the chosen organisation, public pages with the form's organisation; Settings → Organisations in the list format, the rail switcher, the builder's Organisation setting. Checked in the browser: availability (taken / free), a real change to remedylegal-uk and back (still signed in, old address listed), a test domain with a DNS check (not found) then removed, a second organisation created, the switcher narrowing Forms to it (empty), Visitor sign-in moved there (public page shows its name) and back, the test organisation archived. F14 complete; stopped for review. |
| 2026-10-07 | F14 | Owner feedback: "Powered by Formalie" on the workspace sign-in page, Branding preview and every email; own domain and short-link domain removed (Workspace address keeps the subdomain change); organisations, the rail switcher and the form setting removed; teams, locations and cost centres removed; sign-in codes without an authenticator app, text messages off by default; Form defaults show the chosen theme. Checked in the browser: sign-in page (Samath Tax, Remedy Legal) with the mark in the showcase and under the form, the settings menu, the theme picture changing with the choice, the email preview HTML with the Formalie mark. |
| 2026-10-07 | F15 | M1 List manager: `/option-lists` paged rows, insights, detail, usage, sync (copies into drafts with translations), duplicate; FRM-FORM-1020 repeated values; Option sets page (chart cards, table / cards), list editor (Options with values, scores, retire, reorder by drag or keyboard, Paste / Import with column mapping and preview, Translations, Used in with Update); CSV / XLSX reader in the browser (`app/utils/files/table.ts`); builder takes active options only and flags a changed list. Checked in the browser: the page, Departments: paste (2 new, 1 updated), retire, values, save, Used in reporting the older form, Update (the form got the new options without the retired one), then put back (Sales offered, the two test options retired, form updated back to its original six); the Excel reader with a compressed workbook and the CSV parser; the Translations tab. |
| 2026-10-07 | F15 | M2 Lists with levels: `OptionList.levels`, `OptionItem.level / parent` (FRM-FORM-1021 when an option has nothing above it), sample list Places (Country → Region → City); `shared/utils/forms/cascade.ts` (options under the choice above, closed levels, answers that no longer fit) used by the renderer and the submission check; fields `option_level` / `option_parent`; builder Lists tab (plain or levels, one choice / several), level settings (`InspectorLevel`); editor Levels card, per-level options with the option above, "N under it", import by path (`importPaths`); cards and rows show the chain. Checked in the browser: the Places editor (levels, Canada → Ontario, Quebec; Japan → Tokyo, Osaka), import dialog by path, a test form "Places test" with Country (one), Region (several), City: only Country shows at first, Canada opens Ontario and Quebec, both chosen give the cities of both, Japan clears Region and closes City. |
| 2026-10-07 | F14 / F15 | PROGRESS tidy (owner): F14 header ticked, open request rows brought up to date (sign-in methods, data sources, API service, organisation data, Appearance), F15 in progress. The first-load screen follows the workspace's Appearance (`formalie-loading-look` kept by useAppearance, read by an inline script in the template: background, accent for the mark, bar and dots, font), checked in the browser with a green workspace in dark mode. The PDF report uses the Appearance colour (`appearanceInk`) instead of fixed black. |
| 2026-10-07 | F14 | Empty states (`AppEmpty`) follow Appearance (owner): the icon in the primary colour and the tile softly tinted with it; black and white workspaces keep the monochrome look. Checked in the browser on List Option (no results) with a green workspace. |
| 2026-10-07 | F14 | Empty state buttons follow Appearance (owner): neutral actions in `AppEmpty` take the primary colour, solid or outline as given; red / amber ones keep theirs. Checked in the browser (Clear all in green on a green workspace). |
| 2026-10-07 | F15 | Owner tested lists with levels (fine) and limited them to 4 levels: `MAX_LIST_LEVELS` in `shared/utils/forms/options.ts` used by the editor, the server (levels, option level), the form schema and the cascade rules. |
| 2026-10-07 | F15 | Owner: single or several per level, not all the same. The Lists tab shows each level with its own One choice / Several choices switch and "Add N fields" (`createListFields` takes a type per level); the canvas notes under lower levels that they stay hidden until something is chosen above. Checked in the browser: Country several, Region one, City several; in the preview only Country shows, Canada + Japan give Ontario, Quebec, Tokyo, Osaka, Tokyo gives Shinjuku and Shibuya. |
| 2026-10-07 | F15 | Owner: no hint text under levels (removed); the builder canvas behaves as the form: what you try in a level narrows the next, a lower level is locked with "Choose Country first" until something is chosen above, a changed choice clears what no longer fits (canvas try-out answers shared via `RENDERER_ANSWERS`, nothing stored). Deleting any level removes the whole chain (one Undo brings it back); duplicating a level copies the chain, linked. Adding a list with levels sets Required and One / Several per level. Checked in the browser: canvas Canada gives Ontario and Quebec only, City locked until a region; Delete on one level took 6 fields to 3, Undo restored all; the picker shows Required per level. |
| 2026-10-07 | F15 | Owner: settings in the right panel, not while adding; lists draggable. The Lists tab adds on click or drag with no choices (plain list = dropdown, list with levels = one linked field per level in one row, even widths, one choice, not required); a dragged list with levels lands as its top level and the others join it in its own row (`attachChain`, `usePaletteDrag.track(field, others)`). New right-panel section Show as (dropdown, multi-select, single choice, checkboxes) for choice fields; levels keep One / Several and Required in their settings. Checked in the browser: click on Products added its 4 levels; Show as turned Priority into checkboxes; options section still shown. The drag itself could not be run by the test browser (its drag does not start this drag library, not even for Short text); please try dragging a list. |
| 2026-10-07 | F13 / F15 | API service and lists with levels (owner asked to confirm): POST already ran the form's own check (`checkSubmission`, levels fitted, closed levels skipped), but the endpoint's own Required check ran first and now skips a level with nothing under the choice above; PUT now checks a sent level against the record's choice above (`422 FRM-RESP-1001`, `choice`) and clears levels below a changed one that no longer fit, as the form does. Endpoint fields carry `depends_on` and each option's `parent`; the docs say what a level depends on; example bodies and records pick level values under the example above (`withLevelSamples`). Unit tests added. |
| 2026-10-08 | F0 | Dev server warnings (owner): duplicated auto-import `isTimeZone` (one copy kept in `shared/utils/forms/catalogues.ts`, Settings schemas use it); BigInt literals in `shared/utils/apiService/access.ts` replaced by `BigInt()` constants (the build targets ES2019, esbuild warned 4 times, now 0). The remaining two warnings come from Nuxt itself: the HTTPS dev server hint about NODE_TLS_REJECT_UNAUTHORIZED (not to be set, it switches off certificate checks) and Nuxt DevTools with the current Vite (fixed upstream; harmless). |
| 2026-10-08 | F15 | Owner: a 3-column import into a simple list kept only the first column. Import and Paste now ask what each row is (one option, or a path with one column per level) with an example; a file shaped like levels is spotted (`looksLikeLevels`) and read as paths; for a simple list Apply creates the levels, named from the column headers (up to 4); pasted text gets its header row detected (`looksLikeHeader`); a warning says when the list's existing options would stay on the top level (Replace keeps only the file's). Paste works for lists with levels too. The editor has a List type switch (Simple list / List with levels; back to simple asks first) and a "How lists work" guide (3 steps, remembered when closed). Checked in the browser on Days of the week (not saved): pasted Country / Region / City rows were spotted as levels, header detected, Apply made Country → Region → City (9 / 3 / 4), then Discard. |
| 2026-10-08 | F7 | Owner's builder ideas: click-to-add (`QuickAdd`: searchable list at the click, Enter picks; the canvas works out the row from the click: new row after / before rows, beside fields of a row with room, `builder.addToRow`); page title block removed from the canvas, page tabs in their own component (`PageTabs`) with a pencil / double-click rename and Rename in the page menu; the page fills the screen height and grows (empty page message centred); Fields / Settings panes toggled from both ends of the tabs row (`useBuilderPanes`, open by default, remembered), Settings reopens on selecting a field. Checked in the browser on Places test: a click below the fields added Email at the end; with the field list hidden a click to the right of Email added Phone beside it; hiding Settings then selecting Email brought it back; rename to "Contact details" and back; test fields removed again. Page names in the form: see the next line. |
| 2026-10-08 | F8 / F10 | Owner: the form name and page name made the form body heavy. The form card no longer shows the form name; frames without a hero title (branded, centred, corporate, floating) show it as a small line under the organisation in the top bar (theme switch now "Show the form name under the organisation"), hero frames (spotlight, side, banner, headline, compact) keep their title; the page name rides with the step progress ("Step 1 of 3 · About you") on forms with several pages and is no longer a heading. Themes, templates and stored data unchanged. Checked in the preview: Places test (branded, no headings in the card) and Job application 2 (floating, Step 1 of 3 · About you). |
| 2026-10-08 | F8 | Theme block styles (owner): new theme group `blocks` (section plain / underline / edge / band, heading in text or accent colour, small capitals, the theme's heading weight; divider line / accent / fade / dots / space, thin or thick; paragraph plain / soft / callout; image corners, shadow, border). Default = today's look, so older themes and forms do not change. Every starting point and every template category has its own block style; designer group "Sections and blocks". Renderer `Layout` reads it (`provideBlockStyle` / `useBlockStyle`); the builder canvas keeps the default look. Checked in the designer on Places test with a section, divider and paragraph: default, Soft (band, fade, callout), Bold (edge, thick accent line), Elegant (small capitals, dots, soft text); then reset to the workspace default and the test blocks removed. |
| 2026-10-08 | F13 | API service tidy (owner). What happened: tokens without a chosen service or endpoint can call every endpoint, and a new endpoint's checklist counted them, so a token nobody made for it looked assigned; the token dialog named endpoint tokens "{service} · /{endpoint}". Now: the checklist counts only tokens made for the endpoint or its service (`tokens_live / _test`), tokens for every endpoint apart (`tokens_all_live / _test`, said in the text); new tokens are named "{Service} Token" (unique with 2, 3 …); `GET /api-service/connections` and a Connections block in the service, endpoint, token and access rule panels (service, form, endpoints, tokens with how they reach it, access rules; each a link). Checked in the browser: the /account panel lists its service, form, 2 tokens (one for every endpoint) and 2 rules; a new token from the endpoint is named "Service Account Data Token" (cancelled, nothing created). |
| 2026-10-08 | F7 | Publish (builder header on Build, Logic, Design and Versions, normal and full screen) is disabled and dimmed when the form is published and has no saved or pending changes (`nothingToPublish` in `useBuilderSession`: published version known, no `has_unpublished_changes`, autosave not pending); hovering or focusing it says "No new changes. Make changes first." A form never published can always be published. Checked in the browser: Account (published, no changes) disabled with the message; Places test (never published) clickable. |
| 2026-10-08 | Docs | PROGRESS brought up to date (owner): "Last updated", F15 lists with levels refinements (right panel settings, canvas behaviour, chain delete, smarter import, API support), the F7 builder items (click to add, page tabs, full-height page, panes, Publish), the F8 designer items (block styles, names outside the form body) and the F13 API follow-ups (token names, own tokens, Connections) ticked in their phases, F15 overview ~35%. |
| 2026-10-08 | F13 / F15 | Owner tested the API with plain lists and lists with levels: records gave value codes ("running_shoes_air_footwear"). Now records give option labels (one choice: the label; several: a list of labels; every level of a list with levels); POST, PUT and GET filters take a label (any case) or a value, labels become values before the form's checks, a label shared by two options of a level is settled by the choice above (`choiceOut`, `choicesIn`, `choiceFilter`). Docs list labels (value on hover), examples and the OpenAPI enum use labels. Tests updated and added (538). |
| 2026-10-08 | F13 | Owner: example bodies were not in the form's order (required questions were put first) and a list with levels showed "option_1" under a top option with nothing under it. Examples (`exampleRequestBody`, `exampleRecord`, used by the Docs page, an endpoint's Example call, the test console, the code snippets and test-token answers) now follow the form's order; each level picks an option with something under it all the way down, and a level with nothing to offer is null, never made up. Checked in the browser on /account (GET and POST examples in form order); tests added (540). |
| 2026-10-08 | F13 / F15 | Owner asked that the API fixes hold for every endpoint and list, not just the tested form: confirmed (examples, labels and level paths are worked out from each form's questions every time; any endpoint, any list, up to 4 levels, any question with options). One gap closed: an answer whose option was later removed from the form now still reads as its label, looked up in the form's List Option list (retired options keep their labels). |
| 2026-10-08 | All | Owner's general test done. Decision: general tokens stay general (they may call every endpoint, also ones made later; shown with a globe in Connections). Docs tidied: OPTION-LISTS marks its draft model as superseded where built differently and its phasing shows M1, M2 done and M3 search next. |
| 2026-10-08 | F15 | M3 large lists and search as you type: `searchesAsYouType` (dropdown / multi-select above 50 options, or `props.search`), `servedRemotely` (no level above, above 300 options: left out of the public form, `options_remote.total`), `matchOptions` (accents and case ignored, starting matches first, 50 at a time) and `GET /public/forms/{key}/options?field=&q=&values=&language=` (open forms with the page's access; `values` for a resumed draft's labels); renderer search box with server matches and "Showing 50 of N", long lists virtualised; builder: Search as you type switch (field settings and level settings), long list summary instead of rows; field options limit 5,000 → 20,000. Checked in the browser on Places test: switch on, the canvas Country searched ("ja" → Japan), then undone. The server lookup is unit-tested; it has not been tried in the browser yet (needs a published form with a list above 300 options). |
| 2026-10-08 | F15 | M4 details and auto-fill: `OptionList.columns`, `OptionItem.attrs` (server keeps details only for the list's columns), `offeredOptions` copies details into fields and `matchesList` notices changed details; list editor Details card (`option-sets/Columns.vue`), a Details popover per option, import role "Detail: …"; `shared/utils/forms/fills.ts` (`props.fills = [{ column, target, lock }]`) applied inside `evaluateLogic`, so the form page and `checkSubmission` fill alike (locked = disabled and always the detail); builder "Fill other fields" (`InspectorFill.vue`). Checked in the browser: a Dial code detail on Places (Brazil +55), Update from the list on Places test, Dial code → a short text field (locked); in the preview choosing Brazil filled "+55" and kept it locked; then fill, field, detail removed and the form updated back. Found and fixed: a select item with an empty value breaks the select ("Don't fill" now uses "none"). Tests added (`test/forms/fills.test.ts`). |

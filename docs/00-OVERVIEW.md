# 00, Formalie Product Overview

## Positioning (owner, 2026-10-02)

**A secure, flexible platform for creating forms, collecting and managing data, connecting systems and controlling access, built for organisations of any size, anywhere in the world.** Companies and organisations can build any form, design it as they want, share it, connect their own database, stay privacy-compliant and keep data secure.

Formalie is a **global** product: copy, examples, sample data and visuals are international and neutral, never tied to one country.

## One-liner

A drag-and-drop form builder with ready templates, full visual design control, versioned draft → publish workflow, sharing/embedding, short links, responses stored in Formalie or sent to the customer's own database, Excel export and analytics, multi-tenant, secure enough for a large enterprise, yet simple to use.

## Core modules

### 1. Form builder (the heart of the product)

- Drag-and-drop canvas with field palette, inspector panel and reordering (fields, sections, pages). Robust, not "child's play": nested sections, multi-column rows, copy/duplicate, multi-select, undo/redo, autosave, keyboard alternatives for every drag action.
- Field types: short text, long text, rich text, number, currency, email, phone, URL, date, time, date-time, date range, dropdown, multi-select, radio, checkbox, toggle, rating, scale/NPS, slider, file upload, image upload, signature, address (with map), country/state (from platform lists), matrix/grid, ranking, payment (later), hidden field, calculated field, section header, paragraph/HTML block, divider, image, page break.
- Logic: show/hide, skip/jump to page, required-if, calculated values, validation rules (min/max, regex, length, file type/size), prefill from URL params.
- Multi-page forms with progress bar, save-and-resume.
- Predefined select lists (option sets) from Settings reusable in any form.
- Conditional forms fields (show/hide/navigate etc) based on actions etc.

### 2. Form designer (page design)

Users can design the whole form page: layout (single column, two-column, card, full-bleed, split with image), page and form background (colour, gradient, image, overlay), borders (width, style, colour, radius), shadows, spacing, typography (font family, sizes, weights), colours (primary, text, input), button style, header/banner image, logo, cover page, thank-you page, per-field width on a 12-column grid. Saved as a theme; themes reusable across forms.

### 3. Lifecycle and versioning

- States: **Draft → Published → Closed / Archived**. Soft-deleted forms go to Trash.
- A form is **never publicly accessible until published** (public URL returns 404).
- Re-editing a published form opens a **new draft version**; the currently published version stays live until the new draft is published (see Decisions).
- Every publish creates an immutable version; responses record the version they were submitted against; rollback to any version.

### 4. Templates

System templates (platform-wide) + organisation templates. Categories: questionnaires/surveys, customer feedback/NPS, compliance & audit checklists, customer onboarding/KYC, employee data/HR onboarding, event registration, job applications, incident reports, patient intake, school admission, order forms, contact/lead forms. "Save as template" from any form.

### 5. Sharing, embedding, URLs, SEO

- Share with people inside the organisation with **edit** or **view** access; share responses view separately.
- Public link options: open, password-protected, invite-only, expiry date, response limit, one response per person, schedule open/close.
- Form link `https://{forms | sub}.formalie.com/{formKey}/fill` and embed `…/{formKey}/embed` (`forms.formalie.com` for workspaces without their own subdomain) + **short URL** (`/s/{code}`) + QR code.
- **API service** (F13): any form can also become API endpoints (`https://api.formalie.com/{apiKey}/{endpoint}`, GET / POST / PUT / DELETE) so applications send and read its data, links, embeds and API all land in the same storage.
- Embed via **iframe** (primary, with auto-resize script) and popup/slide-in later. Per-form allowed embed domains.
- **SEO on every shared form link**: title, description, Open Graph/Twitter image, canonical URL, favicon, `noindex` toggle (default noindex for private forms).

### 6. Responses

- Data sources (F12): organisations connect their own databases, then browse them (database explorer), query them (query editor, read-only by default) and manage rows, imports and exports, all server-side and audited.
- Destinations: Formalie database (default), customer's own database, launch set: **MySQL, MariaDB, Oracle, PostgreSQL, SQL Server** (via Celery writer; list in `shared/utils/integrations/databases.ts`), or Formalie's own encrypted storage, webhook (sent with a webhook token, retried), email notification.
- Response views: table and grid (switchable), filters, search, date ranges, single response view, edit history, notes/tags/status (e.g. new, reviewed, approved), bulk actions.
- Export: Excel (.xlsx), CSV, PDF (single and bulk) via background jobs.

### 6b. API service (developer option)

Build API endpoints from forms (one form per endpoint, as many as needed), grouped into services that can be switched on / off as a whole. Per endpoint: methods (GET, POST, PUT, DELETE), the fields accepted (POST / PUT) and returned (GET), static or dynamic bearer tokens, required headers, allow / block lists (IP, domain, region, country), rate limits, request logs and its own analytics; generated docs and a try-it console. Runs as its own backend service. Forms, Data sources and API service each get their own dashboard.

### 7. Analytics

Per form: views, starts, completions, completion rate, drop-off per page/field, average completion time, per-question charts, NPS. Date-range filters. Organisation-wide numbers on the Dashboard (F21: Workspace, Forms, Data sources and API service views).

### 8. Collaboration

Live co-editing was removed by the owner (2026-10-08). People work together through sharing (edit / view / responses access) and roles.

### 9. Settings (handles everything)

Company profile, branding, subdomain, authentication providers (Google, Microsoft, Apple, Facebook, email/password), OTP policy, predefined select lists (option sets), themes, data destinations/connections, webhooks, API keys, notification and email templates, data retention, localisation (language, timezone, date/number formats, currency), embed defaults, security policies (password rules, session timeout, IP allowlist), billing/subscription.

### 10. Users, roles, access (RBAC)

Brought forward into F16 (owner, 2026-10-09). Org admin (all access by default) profiles people in their organisation (department, job titles, roles), defines roles whose permissions carry a scope per action (None, Own, Shared, Own & shared, All), resets passwords/accounts, enables/disables users, forces MFA, enables auth providers shown on their subdomain login page.

### 11. Audit trail and logs

Built right after sign-in (F4); every later feature records its actions there. Every action recorded with who, what, when, where (IP, geo), before/after values.

### 12. Dashboard

Built in F21 (2026-10-10): Workspace, Forms, Data sources and API service views with period, folder and owner filters and first steps for new workspaces.

### 13. Subscription

Plans and pricing live on the product website; upgrade/renewal also available inside the portal for free-tier users. Plans Starter (free), Professional, Business and Enterprise (contact us), billed Monthly, Quarterly or Annually through **Payoneer** (F24). Plan limits enforced in the backend (forms, responses/month, seats, own-database destination, custom branding, data residency, etc.). No custom CSS in any plan (owner, 2026-10-10).

## Non-negotiables (summary)

Clean, mobile-first Nuxt UI interface · keyboard navigable · theme switch · 20+ languages incl. RTL · loading states everywhere · table/grid switch with filters and pagination · strict tenant isolation (Postgres RLS) · app-layer encryption of all API traffic on top of TLS · Fernet bearer tokens with expiry and rotation · OTP on every login · CSRF tokens · rate limiting · full request/audit/error logging with geo data · soft delete everywhere · UUIDs everywhere externally.

# Front-end Spec (`formaliePlatformFront`, Nuxt 4)

Same shell, same components and the same look as the Formalie portal. Start by **copying Formalie's foundation** from `formalieFrontend` (same owner, same stack): the app shell (`components/app/**`: Panel, Footer, Modal, Breadcrumbs, Search, Sidebar rail and menu, Navbar, UserMenu, LocaleSwitch), `components/data/**` (DataView, Toolbar, DateRangePicker, Pagination, StatusBadge, ShareBar), `components/charts/**`, the composables for API, session, activity, busy, confirm, error handler, format, context menu, draggable modals, the envelope client (`utils/api/client.ts`, with the platform's HKDF info string), the i18n setup with the 20 locales, the loading template and the navigation progress plugin. Then rename the product to "Formalie Platform" and remove everything tenant-specific (no subdomain detection, no workspace switcher, no public form routes).

## Rendering and routes

Client-rendered only (`routeRules: { '/**': { ssr: false } }`), `noindex`. Auth pages use the `auth` layout; everything else the dashboard layout.

## Navigation (rail areas, each with its own menu, like Formalie)

| Rail area | Menu |
| --- | --- |
| **Overview** | Home (KPI cards, alerts) |
| **Analytics** | Overview · Realtime · Acquisition · Engagement · Activation · Retention · Usage · Revenue · Geography & technology · Access history · Explorer · Saved reports |
| **Workspaces** | All · Trials · Paying · Past due · Suspended · Closing · Tags |
| **Accounts** | People · Sessions · Locked · Disabled |
| **Billing** | Subscriptions · Payments · Invoices · Refunds · Plans · Billing actions |
| **Content** | Help articles · Categories · FAQs · Glossary · Tours · Media · Feedback · Missed searches |
| **Defaults** | Lists · Folders · Email templates · Templates · Themes · Landing pages · Publish history |
| **Operations** | Health · Queues & jobs · Errors · Requests · Security events · Rate limits |
| **Communications** | Messages · Announcements |
| **SYSTEM group** | Platform settings · Feature switches · Staff · Roles & access · Approvals · Audit trail · My profile · Dark mode |

Every item has a `permission`; areas and items the role can't open don't show, and their addresses go to No access.

## Page map

| Route | Page |
| --- | --- |
| `/auth/login`, `/auth/two-step`, `/auth/activate/[token]`, `/auth/recovery` | Staff sign-in (email + password → authenticator code), activation (set password + set up authenticator, recovery codes), recovery code sign-in |
| `/` | Overview |
| `/analytics/**` | Reports (ANALYTICS.md), `/analytics/explorer`, `/analytics/reports/[id]` |
| `/workspaces`, `/workspaces/[id]` | List (two chart cards: sign-ups, status overview; DataView) and detail (header with status bar and actions; tabs Summary · People · Usage · Billing · Activity · Notes · Support) |
| `/accounts`, `/accounts/[id]` | People across Formalie (masked), detail with workspaces, sessions, sign-ins, actions |
| `/billing/**` | Subscriptions, payments, invoices, refunds, plans editor (`/billing/plans/[id]`), billing actions |
| `/content/**` | Help CMS: article editor (Nuxt UI `UEditor`, media, translations side by side with "changed since translated", preview as the portal shows it, publish), categories, FAQs, glossary, tours editor, media library, feedback, missed searches |
| `/defaults/**` | List editor (same as Formalie's List Option editor: levels, details, translations, import, Large), folders, email templates editor, catalogue (templates / themes / landing pages publish and retire), publish history |
| `/operations/**` | Health board, queues, error log (trace ids), request log, security events, rate limits |
| `/communications/**` | Message composer (audience builder, 20 languages, preview, schedule, approval), announcements |
| `/settings/**` | Platform settings (legal links, support links, status page, branding on Formalie surfaces, reserved subdomains), feature switches |
| `/staff`, `/staff/[id]`, `/staff/roles`, `/staff/roles/[id]` | Staff (Add staff, activation, status), roles with the granular editor (copy Formalie's Roles & access editor) |
| `/approvals` | Pending (to me / by me), decided, expired; approve / reject with reason and step-up |
| `/audit` | Platform audit trail (DataView, filters by staff, action, target, outcome; detail with before / after; chain status) |
| `/profile` | My profile: photo, name, language, region, password, authenticator, recovery codes, sessions |
| `/no-access` | No access page |

## List pages (same discipline as Formalie's rule 21)

Two equal chart cards on top (a count with change, small stats and daily bars; a status overview with thin lines and a legend that filters), then DataView: one-line toolbar (search, Filter, chips, Columns, date range, Sort, Table / Grid), sortable headers, status badges, row ⋯ menu, right-click menu, a row opens its detail panel (rich header, one-click status bar, fact tiles, grouped content, Previous / Next pill), server-side paging.

## Approvals in the UI

A button for an action that needs approval says "Request …"; it opens a dialog with the reason (required) and the exact effect; on success a toast "Sent for approval" links to the approval. Pending approvals show a badge in the SYSTEM group and on the target's detail page ("Suspension pending approval by another staff member"). Approving shows the full request, asks for the reason and the step-up code.

## Masking and reveal

Emails, phone numbers and names in lists show masked; a "Reveal" control (eye icon) asks for step-up, shows the value for this view only, and is audited. Exports with personal data need approval.

## Translations and copy

All strings in the 20 languages (English first, then translated, same workflow as Formalie). Names Formalie provides follow the language; names people typed stay as typed.

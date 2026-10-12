# 00, Formalie Platform Admin, Product Overview

## Positioning (owner, 2026-10-10)

**The Formalie team's command centre.** One place to see everything that happens on Formalie (like Google Analytics, for the whole platform) and to manage everything: workspaces, accounts, plans, payments, help content, Formalie's default data and platform settings. Very powerful, so it is also the most protected system Formalie has.

It is a separate project from the Formalie portal, with its own front end, its own backend and its own database, and it can read and act on Formalie's system (see 01-ARCHITECTURE and FORMALIE-INTEGRATION).

## Who uses it

Only Formalie staff (the owner and the team). Each person has a profile and one role; roles are built in the platform's own Roles & access, granular like Formalie's (see module 9). Examples of roles the owner may create: Platform owner, Operations, Support, Finance, Content editor, Analyst, Engineer (read-only diagnostics).

## Modules

### 1. Overview (the home page)

KPI cards with trends and date ranges: active workspaces, new sign-ups, paying workspaces, MRR, responses collected, API calls, error rate; a live strip (people signed in now, responses in the last hour); alerts (failed payments, queue backlogs, security events, workspaces near their limits). Every card opens its full report.

### 2. Analytics (Google Analytics style, see ANALYTICS.md)

- **Realtime:** people active now, by country, device and page; live events stream (sign-ins, publishes, responses, API calls) without personal data by default.
- **Acquisition:** sign-ups over time, by source (UTM, referrer, campaign), country, plan chosen; sign-up funnel from the website.
- **Engagement:** DAU / WAU / MAU (people and workspaces), sessions, session length, pages and features used, top features by plan.
- **Activation funnel:** sign-up → workspace set up → first form → first publish → first response → invited a colleague → paid.
- **Retention:** cohorts by sign-up week / month, stickiness (DAU/MAU), churn and reasons.
- **Usage:** forms, published forms, responses, files, storage, API calls, data source operations, exports, per workspace and in total, against plan limits.
- **Revenue:** MRR, ARR, new / expansion / contraction / churned MRR, ARPU, LTV, payments, failed payments, refunds, by plan, country and currency.
- **Geography and technology:** countries, cities, languages, devices, browsers, operating systems.
- **Access history:** every sign-in across the platform (who, workspace, when, where, device, method, result), failed sign-ins, two-step use, sessions; per account and per workspace.
- **Explorer:** pick a metric, dimensions, filters and a date range; -table and chart; save as a report; export; schedule by email.
- Comparisons with the previous period everywhere; every chart has a table view.

### 3. Workspaces

Every workspace (tenant): name, subdomain, owner, plan, status (active, trial, past due, suspended, closed), country, created, last activity, usage against limits, health. Detail panel with tabs: summary, people, usage, subscription and payments, activity (from Formalie's audit trail, read-only), notes from staff, support access log.

Actions (all audited, some need approval): suspend / restore (with reason, the workspace sees the suspended page), change subdomain, change plan or limits, extend a trial, move to read-only, request data export, close and schedule deletion (approval), add a staff note.

### 4. Accounts (people across Formalie)

Search anyone on Formalie by name or email; see their workspaces, roles, status, two-step setup, last sign-ins, sessions, devices. Actions: sign out everywhere, reset two-step (approval), send password reset, disable on the platform (approval), unlock after too many attempts. Personal data masked by default, revealed on purpose.

### 5. Support access (impersonation, strictly controlled)

A staff member can view a workspace as its owner sees it **only with the workspace's consent** (the workspace owner grants time-limited support access from their Formalie Settings, or approves a request), read-only by default, time-limited (max 60 minutes), shown to the workspace as a banner and recorded in both audit trails. Write access during support needs a second staff approval and the workspace's explicit consent for writing.

### 6. Subscriptions and payments

- **Plans:** the plan catalogue (names, limits, features, prices per currency, monthly / yearly), trial length, grandfathered plans. Published to Formalie (plans are a global table there).
- **Subscriptions:** every subscription with status (trialing, active, past due, cancelled, expired), period, next billing date, seats, add-ons; filters by plan, status, country, currency.
- **Payments:** every payment, invoice and receipt from the processor (amount, currency, status, method type, processor reference), failed payments and retries, refunds, disputes.
- **Manual actions (owner, 2026-10-10):** activate a subscription manually (for example paid by bank transfer or invoice), extend a period, give a discount or credit, change plan, cancel; each with reason, approval for amounts above a threshold, and an entry in both audit trails.
- Card details never reach Formalie or the platform; the processor holds them.

### 7. Help centre content (feeds Formalie's F25 Help centre)

Write, translate and publish the help centre the Formalie portal shows: categories by area, articles (rich text, screenshots, GIFs, videos with captions), FAQs, glossary, guided tours ("show me where" links to real portal pages), keyboard shortcut pages. Every article in all 20 languages, with translation status and "changed since translated" like Formalie forms. Drafts and review here; **Publish** sends it to Formalie. Feedback: "Was this helpful?", comments, and what people searched without finding.

### 8. Formalie default data

What every workspace receives and can use but not change (owner, 2026-10-08): system lists (simple and with levels, translated, Large lists), default folders, default roles' texts, email templates, statuses, system templates, themes and landing pages. Edited here with the same editors as in the portal (List Option editor, designer), then published to every workspace; see where each default is used.

### 9. Staff, roles and access

The platform's own people and access, built like Formalie's F16 + F22: staff profiles (invited by the owner, activated by email, mandatory two-step), roles with granular permissions and reach, approval rules for dangerous actions, sessions and devices, IP allowlist per role, the platform audit trail (who did what, before / after, never editable).

### 10. Platform settings

Legal links shown on every public form (Terms, Privacy), support email and links, status page link, marketing site link, Formalie branding on shared surfaces (forms host, QR codes, emails), feature switches (per plan, per workspace, gradual rollout), announcements and maintenance banners in the portal (who sees them, when), reserved subdomains list.

### 11. Operations

Health of Formalie's services and the platform's own: API latency and errors, queues and workers (backlogs, failed jobs, retry), exports and destinations in trouble, webhooks failing, email delivery, storage, rate-limit hits, error log (with trace ids), security events (blocked envelopes, replays, token reuse, cross-tenant attempts).

### 12. Communications

Messages to workspace owners or admins (product news, incident notices, billing notices), with audience filters (plan, country, language, status), in all 20 languages, sent through Formalie's email service; in-app notifications in the portal. Opt-out respected for non-essential messages.

## Non-negotiables

Staff only · mandatory two-step · approvals for dangerous actions · immutable audit trail · least data, masked by default · Formalie's rules applied through its internal admin API · same stack, same look and same quality bar as Formalie (mobile first, keyboard, light / dark, RTL, 20 languages, loading feedback everywhere, Table and Grid lists with filters and server paging).

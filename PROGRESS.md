# Formalie Platform Admin, Front end Progress (formaliePlatformFront)

The single place to see **what we are building, what is done and what is next** in the front end. The backend has its own PROGRESS.md in formaliePlatformBack with the same phases. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-10 (plan written; nothing built yet; starts after Formalie's real backend switch, owner 2026-10-10)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ waiting on Formalie · ➖ dropped or merged

The front end may run ahead of the backend on its mock layer (the shapes in API-CONTRACT.md). A phase is finished when this project's tasks are done and the phase has been checked together with the backend.

## Overview

| Phase | Name | Status | Done |
| --- | --- | --- | --- |
| P0 | Foundation (both projects) | ⬜ | 0% |
| P1 | Staff sign-in and security | ⬜ | 0% |
| P2 | Platform audit trail | ⬜ | 0% |
| P3 | Staff, roles & access, approvals | ⬜ | 0% |
| P4 | Formalie bridge (front end: "Formalie unavailable" states) | ⏸ | 0% |
| P5 | Workspaces and accounts | ⬜ | 0% |
| P6 | Support access | ⬜ | 0% |
| P7 | Analytics (Google Analytics style) | ⬜ | 0% |
| P8 | Subscriptions and payments | ⬜ | 0% |
| P9 | Help centre content | ⬜ | 0% |
| P10 | Formalie default data | ⬜ | 0% |
| P11 | Platform settings, feature switches, announcements | ⬜ | 0% |
| P12 | Operations | ⬜ | 0% |
| P13 | Communications | ⬜ | 0% |
| P14 | Overview home and hardening | ⬜ | 0% |

**Every phase is only done when:** phone / tablet / desktop checked · keyboard only · light and dark · Arabic RTL · permissions followed everywhere (menus, pages, buttons, shortcuts) · approvals and step-up handled · loading feedback complete · empty and error states · every new string in all 20 languages · matches `docs/design` · typecheck, lint, tests green · this file and the docs updated · committed and pushed.

---

## P0, Foundation

- ⬜ `formaliePlatformFront` project, copy Formalie's foundation (FRONTEND-SPEC first paragraph), rename product, remove tenant parts
- ⬜ Dev server on `https://platformadm.formalie.dev:2203` (mkcert, hosts lines), proxy to the API, mock layer on
- ⬜ Formalie brand kit applied (`docs/brand/`, BRAND.md): favicon, web icons, manifest ("Formalie Platform"), `i-formalie-mark` in the menu header and loading screen
- ⬜ 20 locales, light / dark, RTL, loading template, navigation progress, breadcrumbs, shell with the rail areas from FRONTEND-SPEC (placeholders)
- ⬜ README run steps verified on a clean machine; `.env.example` files complete (with the backend)

## P1, Staff sign-in and security

- ⬜ Sign-in, two-step, recovery, activation pages (auth layout), step-up dialog wired into `useErrorHandler`, session expiry handling
- ⬜ My profile (name, photo, language, region, password, authenticator, recovery codes, sessions)

## P2, Platform audit trail

- ⬜ Audit trail page (DataView, filters, detail with before / after, chain status badge), "Activity" link from any record

## P3, Staff, roles & access, approvals

- ⬜ Staff list and detail (add staff, resend invite, disable / enable, sign out, unlock, role), Roles & access (copy Formalie's granular editor), Approvals page and dialogs, "Request …" buttons pattern
- ⬜ Menus, pages, buttons, shortcuts follow grants (`useCan`), No access page

## P4, Formalie bridge ⏸ (needs Formalie's backend: FORMALIE-INTEGRATION §5)

- ⬜ "Formalie unavailable" states (actions queued, clear status), health of the bridge on the Operations page (with the backend)

## P5, Workspaces and accounts

- ⬜ Workspaces list (two chart cards, DataView, task-style cards) and detail panel / page with tabs; Accounts list and detail; reveal control; action dialogs with reason

## P6, Support access

- ⬜ Request access, active grants on the workspace page, start session (opens Formalie's support view), end session; banner state shown

## P7, Analytics (Google Analytics style, ANALYTICS.md)

- ⬜ Analytics area with every report: date range + compare, segment filters, chart cards in Formalie's style, tables, exports; Explorer (metrics, up to 3 dimensions, filters, chart type), saved and scheduled reports
- ⬜ Performance check with a year of synthetic events (reports under 1 s on rollups) (with the backend)

## P8, Subscriptions and payments (after Formalie's F24 and the processor choice)

- ⬜ Billing area (plans editor, subscriptions, payments, invoices, refunds, billing actions log), manual action dialogs with reason and approval

## P9, Help centre content (feeds Formalie's F25)

- ⬜ Article editor (`UEditor`, media, side-by-side translations, preview as the portal shows it), categories, FAQs, glossary, tours editor (pick portal route and control), media library, feedback and missed searches reports

## P10, Formalie default data

- ⬜ List editor (same as Formalie's List Option editor), folders, email template editor, catalogue, publish history

## P11, Platform settings, feature switches, announcements

- ⬜ Settings pages, feature switch editor, announcement composer with preview

## P12, Operations

- ⬜ Operations area (health board, queues, errors with trace ids, requests, security events, rate limits)

## P13, Communications

- ⬜ Message composer, audience count preview, history

## P14, Overview home and hardening

- ⬜ Overview home (KPI cards, live strip, alerts, links into reports)
- ⬜ Security review (permissions matrix test, approvals, step-up, masking, headers, CSP), load test, backup and restore drill, key rotation drill, production deployment on AWS or dedicated servers (04-HOSTING.md: systemd units, Nginx, valid certificate, chosen domain or IP, backups) (with the backend)

---

## New requests log

| Date | Request | Where | Status |
| --- | --- | --- | --- |
| 2026-10-10 | The platform admin is a separate project with its own front end, backend and database, reaching Formalie's database; Google Analytics-like analytics; full management; help content; payments with manual subscription activation; its own staff roles and access; dev `platformadm.formalie.dev:2203` and `platformapi.formalie.dev:5601` | All | ⬜ planned |

## Progress log

| Date | Phase | Note |
| --- | --- | --- |
| 2026-10-10 | Plan | Folder created with README, CLAUDE.md (both projects), overview, architecture, dev environment, decisions, backend architecture, front-end spec, data model, API contract v0, security protocol, analytics, Formalie integration, error codes, design references, Nginx sketch |
| 2026-10-10 | Plan | Owner: no Docker. Development uses the installed services shared with Formalie; production on AWS or dedicated servers (new 04-HOSTING.md, systemd unit sketches); the compose file removed |

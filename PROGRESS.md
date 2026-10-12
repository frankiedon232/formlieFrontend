# Formalie Platform Admin, Backend Progress (formaliePlatformBack)

The single place to see **what we are building, what is done and what is next** in the backend. The front end has its own PROGRESS.md in formaliePlatformFront with the same phases. Every phase lists every task. New work is added to the right phase (and to [New requests](#new-requests-log)) the moment it comes up.

**Last updated:** 2026-10-10 (plan written; nothing built yet; starts after Formalie's real backend switch, owner 2026-10-10)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ waiting on Formalie · ➖ dropped or merged

The front end may run ahead on its mock layer (the shapes in API-CONTRACT.md); the backend implements the contract exactly. A phase is finished when this project's tasks are done and the phase has been checked together with the front end.

## Overview

| Phase | Name | Status | Done |
| --- | --- | --- | --- |
| P0 | Foundation (both projects) | ⬜ | 0% |
| P1 | Staff sign-in and security | ⬜ | 0% |
| P2 | Platform audit trail | ⬜ | 0% |
| P3 | Staff, roles & access, approvals | ⬜ | 0% |
| P4 | Formalie bridge (replica, admin API, publisher, events) | ⏸ | 0% |
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

**Every phase is only done when:** every route checks its permission · approvals and step-up where required · every action audited (hash chained) · least data (masking, no answers, no secrets) · database paging · tests for services, routes, permissions, approvals and the bridge · ruff, mypy, pytest green · this file and the docs updated · committed and pushed.

---

## P0, Foundation

- ⬜ `formaliePlatformBack` project (Python 3.11.9, venv `padm`), FastAPI app factory, settings, health, error shape with `PLT-*` codes, structured logging
- ⬜ Local services ready (database `formalie_platform`, RabbitMQ vhost `platform`, Redis index, MinIO bucket, Mailpit; installed services, no Docker); Alembic set up; first migration
- ⬜ Envelope (handshake, AES-GCM, expiry, replay), CSRF, rate limits, host check, encrypted id references; tests
- ⬜ Celery app, queues, Beat; one sample task
- ⬜ README run steps verified on a clean machine; `.env.example` files complete (with the front end)

## P1, Staff sign-in and security

- ⬜ Staff table, Argon2id, breached-password list, invitation + activation (password, mandatory authenticator, recovery codes)
- ⬜ Sign-in (password → TOTP or recovery code), lockout, tokens (10 min / 12 h, rotation, family revoke), idle 30 min, sessions list, sign out one / all, step-up endpoint
- ⬜ IP allowlist (edge + API), security events table
- ⬜ `app.cli seed-owner` (first Platform owner, activation link on the console)

## P2, Platform audit trail

- ⬜ Append-only `audit_log` (insert-only role, monthly partitions), hash chain, daily verification job, export (approval)
- ⬜ Audit write in every service (helper), including refused and failed attempts, reveals and reads of personal data

## P3, Staff, roles & access, approvals

- ⬜ Permission catalogue (API-CONTRACT → Roles & access), needs, `permission_for`, per-item checks, built-in Platform owner (locked), roles CRUD, grants changes need approval
- ⬜ Approvals (request, approve, reject, expire, execute with both names, never self-approval), pending badge counts

## P4, Formalie bridge ⏸ (needs Formalie's backend: FORMALIE-INTEGRATION §5)

- ⬜ `formalie_bridge.reader` (replica, read-only role, time-outs, row caps, paging), fixtures for tests
- ⬜ `formalie_bridge.admin_client` (mTLS, HMAC, idempotency, staff headers, retries via `pending_actions`), fake Formalie for tests
- ⬜ `formalie_bridge.publisher` (global tables, `platform.published`, publish jobs and history)
- ⬜ `formalie_bridge.consumer` (formalie.events, dedup, cursor, replay)
- ⬜ "Formalie unavailable" states (actions queued, clear status), health of the bridge on the Operations page (with the front end)

## P5, Workspaces and accounts

- ⬜ Workspaces list / insights / detail / tabs from the replica; actions through the admin API (suspend, restore, read-only, close, subdomain, export, plan) with approvals; notes and tags
- ⬜ Accounts across Formalie (masked), detail, reveal, actions (sign out, two-step reset, password reset, disable, enable, unlock)

## P6, Support access

- ⬜ Support requests and consented sessions (read-only by default, write with approval and consent), time limits, both audit trails

## P7, Analytics (Google Analytics style, ANALYTICS.md)

- ⬜ Ingestion (validation, enrichment, dedup, batches, realtime counters), rollups (minute / hour / day), sessions, daily snapshots, retention jobs, backfill from Formalie logs
- ⬜ Report endpoints (overview, realtime, acquisition, engagement, activation, retention, usage, revenue, geography, technology, access history), explorer, saved reports, schedules, exports
- ⬜ Performance check with a year of synthetic events (reports under 1 s on rollups) (with the front end)

## P8, Subscriptions and payments (after Formalie's F24 and the processor choice)

- ⬜ Plans drafts and publish (approval), subscriptions / payments / invoices / refunds from Formalie and the processor, manual actions (activate, extend, credit, change plan, cancel, refund) with thresholds and approvals

## P9, Help centre content (feeds Formalie's F25)

- ⬜ Categories, articles with versions and translations ("changed since translated"), FAQs, glossary, tours, media (S3), publish to Formalie, feedback and missed searches from events

## P10, Formalie default data

- ⬜ Default lists (simple and levels, details, translations, import, Large), folders, email templates, catalogue changes (templates, themes, landing pages); publish (approval) and usage across workspaces

## P11, Platform settings, feature switches, announcements

- ⬜ Settings drafts and publish (legal links, support links, status page, branding on Formalie surfaces, reserved subdomains), feature switches (plans, workspaces, percentage), announcements and maintenance banners (audience, period, 20 languages)

## P12, Operations

- ⬜ Health of Formalie and the platform, queues and failed jobs (retry), error and request logs, security events, rate-limit hits

## P13, Communications

- ⬜ Messages (audience builder, 20 languages, schedule, approval, send via Formalie, opt-out for non-essential)

## P14, Overview home and hardening

- ⬜ Security review (permissions matrix test, approvals, step-up, masking, headers, CSP), load test, backup and restore drill, key rotation drill, production deployment on AWS or dedicated servers (04-HOSTING.md: systemd units, Nginx, valid certificate, chosen domain or IP, backups) (with the front end)

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

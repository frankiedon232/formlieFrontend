# 03, Decisions and Notes

## Decisions

1. **Separate project** (owner, 2026-10-10). The platform admin is not part of the Formalie portal: own front end, own backend, own database, own deployment, own secrets. It was phase F23 of the Formalie portal; the portal no longer builds any platform-admin screen.
2. **Same stack, no deviation** (owner, 2026-10-10). Nuxt 4.5 + Nuxt UI 4 + Tailwind 4 + TypeScript 6 + pnpm; FastAPI + Python 3.11 + PostgreSQL 16 + Redis 7 + RabbitMQ / Celery + S3-compatible storage + Nginx. Same allowed front-end extras as Formalie; anything else needs the owner's approval.
3. **Addresses** (owner, 2026-10-10). Dev `https://platformadm.formalie.dev:2203` and API `https://platformapi.formalie.dev:5601/`, mkcert certificates. Production `https://platformadm.formalie.com/` and `https://platformapi.formalie.com/`, or a separate domain, or a separate IP: to decide. Always a valid certificate in production.
4. **Reaching Formalie.** Reads from Formalie's read replica (read-only role). Changes to workspaces, accounts, subscriptions and forms through Formalie's internal admin API, so Formalie's rules, caches, events and its own audit trail stay right. Direct writes only to platform-owned global tables (plans, default data, help articles, platform settings, announcements, feature switches) through a role limited to those tables. Analytics from Formalie's event bus. (Proposed by Claude on 2026-10-10 to satisfy "access Formalie database for all other actions" safely; see open question 2.)
5. **Google Analytics-style analytics** (owner, 2026-10-10): accounts, access, history, usage, revenue, built on Formalie's events plus a one-time backfill, stored in the platform's own PostgreSQL (partitioned raw events and rollups), never respondents' answers.
6. **Help content is written here and published to Formalie** (owner, 2026-10-10). Formalie's F25 Help centre shows what the platform publishes.
7. **Payments are viewed and managed here, including manual activation of subscriptions** (owner, 2026-10-10). Card data never reaches Formalie or the platform; the payment processor (chosen by the owner during Formalie's F24) holds it.
8. **Its own staff, roles and access** (owner, 2026-10-10): profiles, granular roles like Formalie's F22, plus approval steps (maker-checker) for dangerous actions and an immutable audit trail.
9. **Formalie default data** is created and kept here and published to every workspace, where it is usable and locked (owner, 2026-10-08).
10. **Names Formalie provides are translated, names people type are shown as typed** (owner, 2026-10-10, from Formalie): the same rule applies to everything the platform publishes (default lists, help, roles' default names).
11. **No Docker; AWS or dedicated servers** (owner, 2026-10-10). Services are installed directly (development: the same installed services as Formalie, kept apart by database, vhost, index and bucket). Production runs on AWS or on dedicated servers, with systemd and Nginx; Docker only if a real need comes up, with the owner's approval. See 04-HOSTING.md.

## Open questions (for the owner)

1. **Production address:** subdomains of `formalie.com`, a separate domain, or a separate IP only reachable through a VPN?
2. **Write path:** is the internal admin API (decision 4) fine, or should some actions write straight into Formalie's tables? Recommendation: keep the API for everything that touches a workspace.
3. **Staff sign-in:** password + authenticator app (TOTP) mandatory is the baseline. Add hardware security keys / passkeys later (needs one extra library on both sides, owner approval)?
4. **Approval thresholds:** which actions always need a second person (suggested list in SECURITY-PROTOCOL §6) and the money threshold for manual payments / credits.
5. **Support access:** read-only by default with the workspace's consent; is write access during support ever allowed?
6. **Analytics retention:** raw events 13 months, rollups forever (suggested)?
7. **Payment processor:** chosen during Formalie's F24; the platform's payments module follows it.
8. **Hosting for production:** AWS or dedicated servers for the first deployment (04-HOSTING.md describes both)? Same choice as Formalie's, or separate?

## Notes

- The platform admin ships after Formalie's own roadmap (F19, F24, F21, F25, then the real backend), owner 2026-10-10. Formalie's backend must expose what FORMALIE-INTEGRATION.md lists before the platform's bridge phases.
- Formalie items that need the platform (legal links, default data, plans, help articles, announcements) are already served by Formalie's API as platform settings / global tables, so the platform only has to write them.

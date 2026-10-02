# Formalie — portal frontend

Multi-tenant form builder portal. Nuxt 4 · Nuxt UI 4 · Tailwind 4 · TypeScript · pnpm.

- **Rules:** [CLAUDE.md](CLAUDE.md)
- **Roadmap (full checklist + dated progress log):** [docs/FRONTEND-ROADMAP.md](docs/FRONTEND-ROADMAP.md)
- **Design references:** [docs/design/README.md](docs/design/README.md)

## Progress

Last updated **2026-10-02**. ✅ done · 🟡 in progress · ⬜ not started

| Phase | What                                                                                         | Status |
| ----- | -------------------------------------------------------------------------------------------- | ------ |
| F0    | Foundation — config, 20 languages, encrypted mock API, tooling                               | ✅     |
| F1    | App shell — rail + menu sidebar, header, search, shortcuts, draggable dialogs, error pages   | ✅     |
| F2    | Core plumbing — secure API client, error handling, DataView (table/grid/filters), formatters | ✅     |
| F3    | Workspace detection + sign-in — login, one-time code, signup, find workspace, reset password | 🟡     |
| F4    | Onboarding wizard                                                                            | ⬜     |
| F5    | Forms list and lifecycle (create, duplicate, archive, trash)                                 | ⬜     |
| F6    | Form builder (drag and drop, all field types, logic, publish, versions)                      | ⬜     |
| F7    | Designer (themes)                                                                            | ⬜     |
| F8    | Public renderer, preview, share, embed, short links, SEO                                     | ⬜     |
| F9    | Responses (views, filters, exports)                                                          | ⬜     |
| F10   | Templates gallery                                                                            | ⬜     |
| F11   | Settings, option sets, integrations                                                          | ⬜     |
| F12   | Profile (password, MFA, sessions)                                                            | ⬜     |
| F13   | Users                                                                                        | ⬜     |
| F14   | Analytics                                                                                    | ⬜     |
| F15   | Live collaboration (optional)                                                                | ⬜     |
| F16   | Roles & access, audit trail, dashboard                                                       | ⬜     |

**F3 now:** sign-in redesigned (showcase panel + new form), full flow verified in the browser (login → code → portal → logout), desktop / phone / dark. **Next in F3:** polish pass on signup, find workspace and reset password screens; Arabic RTL and keyboard check; then F4.

## Run

```bash
cp .env.example .env
pnpm install
pnpm dev --host 0.0.0.0 --port 2202 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formalie-key.pem
```

Open `https://manage.formalie.dev:2202/` (default entry) or `https://{workspace}.formalie.dev:2202/`.
Hosts file, wildcard certificate and backend setup: [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md).
After `pnpm add` / `pnpm install`, **restart `pnpm dev`** (postinstall regenerates `.nuxt`).

## Test accounts (mock API)

The mock API (`NUXT_PUBLIC_API_MOCK=true`) is seeded in [server/mock/data/tenants.ts](server/mock/data/tenants.ts). These are **test values for local development only** — they exist only in the dev server's memory and never reach a real backend.

**Password for every account:** `Formalie!2026`

| Workspace              | Open                                               | Email                       | Notes                                                      |
| ---------------------- | -------------------------------------------------- | --------------------------- | ---------------------------------------------------------- |
| Remedy Legal           | `https://remedylegal.formalie.dev:2202/auth/login` | `admin@remedylegal.test`    | Admin. Code by email or SMS.                               |
| Samath Tax             | `https://samathtax.formalie.dev:2202/auth/login`   | `admin@samathtax.test`      | Admin. Google, Apple, Facebook buttons shown.              |
| Samath Tax             | `https://samathtax.formalie.dev:2202/auth/login`   | `admin@remedylegal.test`    | Same person in two workspaces (find-workspace lists both). |
| Remedy Legal           | `https://remedylegal.formalie.dev:2202/auth/login` | `disabled@remedylegal.test` | Disabled account → "Account disabled" error.               |
| Old Co (suspended)     | `https://oldco.formalie.dev:2202/`                 | —                           | Shows "Workspace suspended". Needs a hosts entry.          |
| Manage (default entry) | `https://manage.formalie.dev:2202/`                | any of the above            | Find my workspace, or **Create a workspace** (signup).     |

**One-time code:** after the password, the code screen shows the mock's code in dev ("Development code: 123456"). It is also printed in the dev-server console as `[mock-otp]`. Wrong code 5× locks the challenge.

**Without a hosts entry** (e.g. `localhost` or a phone on Wi-Fi): add `?tenant=remedylegal` once, e.g. `https://localhost:2202/auth/login?tenant=remedylegal` (dev only, remembered for the tab).

New workspaces created through signup live until the dev server restarts.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test
```

While `pnpm dev` runs, use `pnpm typecheck:dev` (does not regenerate `.nuxt`).

# Formalie — portal frontend

A secure, flexible platform for creating forms, collecting and managing data, connecting systems and controlling access — built for organisations of any size, anywhere in the world.

Nuxt 4 · Nuxt UI 4 · Tailwind 4 · TypeScript · pnpm.

- **Progress and roadmap (every task, per phase):** [PROGRESS.md](PROGRESS.md)
- **Rules for development:** [CLAUDE.md](CLAUDE.md)
- **Design references:** [docs/design/README.md](docs/design/README.md)

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

| Workspace    | Person                                  | Email                              | Use it to test                                                                     |
| ------------ | --------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- |
| Remedy Legal | Frankie Don — workspace owner           | `admin@remedylegal.test`           | Normal sign-in; code by email or SMS; sees the **Audit trail**                     |
| Remedy Legal | Marcus Reid — account disabled by admin | `marcus.reid@remedylegal.test`     | Correct password, but "Account disabled. Contact your administrator."              |
| Samath Tax   | Elena Rossi — workspace owner           | `admin@samathtax.test`             | Sign-in with Google, Apple and Facebook buttons shown                              |
| Both         | James Carter — external consultant      | `james.carter@carterpartners.test` | Member of both workspaces; **Find my workspace** lists both; no audit trail access |
| Old Co       | —                                       | —                                  | Suspended workspace page (`https://oldco.formalie.dev:2202/`, needs a hosts entry) |

**Where to sign in**

| Address                                  | What you get                                    |
| ---------------------------------------- | ----------------------------------------------- |
| `https://remedylegal.formalie.dev:2202/` | Remedy Legal sign-in                            |
| `https://samathtax.formalie.dev:2202/`   | Samath Tax sign-in                              |
| `https://manage.formalie.dev:2202/`      | Find my workspace · Create a workspace (signup) |

**One-time code:** after the password, the code screen shows the mock's code in dev ("Development code: 123456"). It is also printed in the dev-server console as `[mock-otp]`. Five wrong codes lock the attempt.

**Without a hosts entry** (e.g. `localhost` or a phone on Wi-Fi): add `?tenant=remedylegal` once, e.g. `https://localhost:2202/auth/login?tenant=remedylegal` (dev only, remembered for the tab).

Workspaces created through signup live until the dev server restarts.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test
```

While `pnpm dev` runs, use `pnpm typecheck:dev` (does not regenerate `.nuxt`).

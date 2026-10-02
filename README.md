# Formalie — portal frontend

Multi-tenant form builder portal. Nuxt 4 · Nuxt UI 4 · Tailwind 4 · TypeScript · pnpm.

Start with [CLAUDE.md](CLAUDE.md) (rules) and [docs/FRONTEND-ROADMAP.md](docs/FRONTEND-ROADMAP.md) (progress).

## Run

```bash
cp .env.example .env
pnpm install
pnpm dev --host 0.0.0.0 --port 2202 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formaliekey.pem
```

Open `https://manage.formalie.dev:2202/` (default entry) or `https://{tenant}.formalie.dev:2202/`.
Hosts file, wildcard certificate and backend setup: [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md).

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test
```

`NUXT_PUBLIC_API_MOCK=true` serves the mock API from `server/mock` (same encrypted protocol as the real backend).

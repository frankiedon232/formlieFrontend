# 02 — Local Development Environment

## Current setup (as done by Frankie)

| Item             | Value                                                                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Frontend project | `formalieFrontend` (Nuxt 4.5.2, @nuxt/ui 4.11.1, tailwindcss 4.3.3, vue 3.5.43, vue-router 5.3.1), pnpm                            |
| Frontend URL     | `https://formalie.dev:2202/`                                                                                                       |
| Frontend run     | `pnpm dev --host 0.0.0.0 --port 2202 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formaliekey.pem`        |
| Backend project  | `formalieBackend`, Python 3.11.9, venv, `pip install fastapi[all]`                                                                 |
| Backend run      | `uvicorn app.run:app --host 0.0.0.0 --port 5004 --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formaliekey.pem` |
| API docs         | `https://formalie.dev:5004/docs`, `https://formalie.dev:5004/redoc`                                                                |
| Certificate      | mkcert for `localhost 127.0.0.1 formalie.dev`                                                                                      |

## ⚠ Fixes needed before subdomain work

1. **Domain mismatch.** The hosts entries use `manage.medique.dev`, `remedylegal.medique.dev`, `samathtax.medique.dev`, but the portal runs on `formalie.dev`. Use `formalie.dev` subdomains so cookies, CORS and tenant detection all line up.
2. **Certificate does not cover subdomains.** The current cert is only for `formalie.dev`. Regenerate it with a wildcard:
   ```powershell
   mkcert -cert-file C:\devcerts\formalie.pem -key-file C:\devcerts\formaliekey.pem formalie.dev "*.formalie.dev" localhost 127.0.0.1
   ```
3. **Venv name.** It was created as `fmly` but activated as `fmly\scripts\activate.ps1`. Pick one name (suggest `fmly`) and use it consistently.

## Hosts file (`C:\Windows\System32\drivers\etc\hosts`)

Windows hosts does not support wildcards, so add one line per test subdomain:

```
127.0.0.1   formalie.dev
127.0.0.1   manage.formalie.dev
127.0.0.1   remedylegal.formalie.dev
127.0.0.1   samathtax.formalie.dev
127.0.0.1   forms.formalie.dev
127.0.0.1   api.formalie.dev
```

Add more lines as new test tenants are created.

## Dev URLs

- Default entry: `https://manage.formalie.dev:2202/`
- Tenant workspaces: `https://remedylegal.formalie.dev:2202/`, `https://samathtax.formalie.dev:2202/`
- API (direct): `https://formalie.dev:5004/` — the browser should call `/api/...` on its own origin; Nuxt proxies it (below).

## Nuxt dev settings to add

- Allow the subdomains in Vite: `vite.server.allowedHosts: ['.formalie.dev']`.
- Proxy `/api` to the backend, preserving the original host so the backend can read the subdomain:
  `nitro.devProxy` / `routeRules: { '/api/**': { proxy: 'https://formalie.dev:5004/api/**' } }` with `X-Forwarded-Host` forwarded (implemented in Phase F0).
- Node must trust the mkcert root when proxying: set `NODE_EXTRA_CA_CERTS` to the mkcert `rootCA.pem` (find it with `mkcert -CAROOT`).

## Backend dev services (Phase B0)

Docker Desktop with compose services: PostgreSQL 16 (primary + 1 replica), PgBouncer, Redis 7, RabbitMQ 3 (management UI), MinIO (S3), MailHog/Mailpit (catch OTP emails). Ports to be fixed in `docker-compose.dev.yml`.

## Production equivalent

Cloudflare wildcard DNS `*.formalie.com` → Nginx → Nuxt + FastAPI. Same subdomain logic as dev.

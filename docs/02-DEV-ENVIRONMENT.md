# 02, Development environment

- **Node 22+, pnpm.**
- **Address:** `https://formalie.dev:3033/`.
- **Hosts file:** `formalie.dev` already points to `127.0.0.1` for the app, so nothing new is needed. The app keeps port 2202, and the website uses 3033.
- **HTTPS:** use the same development certificate as the app (`C:\devcerts\formalie.pem`, `C:\devcerts\formalie-key.pem`):

```bash
pnpm dev --host 0.0.0.0 --port 3033 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formalie-key.pem
```

- **Environment (`.env`):**

```
NUXT_PUBLIC_SITE_URL=https://formalie.dev:3033
NUXT_PUBLIC_PORTAL_URL=https://manage.formalie.dev:2202
NUXT_PUBLIC_FORMS_URL=https://forms.formalie.dev:2202
NUXT_PUBLIC_API_URL=https://formalie.dev:5004/api/v1
```

- **Production values:** `https://formalie.com`, `https://manage.formalie.com`, `https://forms.formalie.com` and `https://services.formalie.com/api/v1` (never `api.formalie.com`, which is customers' own API service).
- **The backend:** the public endpoints the site reads (`API-HOOKS.md`) are live on formlyBackend in development (`https://formalie.dev:5004/api/v1`). When it doesn't answer, the site uses its fallback data. Run one dev server per project, never two of the same project.
- **Certificate in `.env`:** `DEV_HTTPS_CERT` and `DEV_HTTPS_KEY` point at the certificate files, so `pnpm dev` alone serves `https://formalie.dev:3033` (see `.env.example`).

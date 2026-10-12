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
NUXT_PUBLIC_API_URL=https://api.formalie.dev
```

- **Production values:** `https://formalie.com`, `https://manage.formalie.com`, `https://forms.formalie.com` and `https://api.formalie.com`.
- **Running beside the app:** while the app's mock API is used, the plans and legal endpoints the site needs (`API-HOOKS.md`) come from the app's dev server on 2202. Run both dev servers, one each, never two of the same project.

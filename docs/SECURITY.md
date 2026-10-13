# Security and what the site may show

## Screenshots (owner: "only the part required, not all, for security")

- **Only the shots in `docs/screenshots/`**, or new ones made **the same way**:
  - desktop size (1440 wide, 2x);
  - cropped to the one part a section talks about, never the whole app with its menus;
  - the Formalie watermark baked into the pixels;
  - sample data only.
- **Every name, key and address in a shot is neutral sample data.** The capture tool replaced:
  - the workspace's real API address key;
  - test names;
  - the owner's name and email;
  - the workspace name (shown as "Northwind Group");
  - uploaded logos and photos (shown as an "N" monogram).
- **Don't add new shots** that show:
  - real customer data, tokens or keys;
  - internal hostnames;
  - the audit trail with real people;
  - billing details;
  - the platform admin.
- **Don't remove or crop out the watermark.**
- Light and dark versions exist for the main screens (`-dark`). Use the one that fits the section.

## The site itself

**Built in S7 (2026-10-13):** `deploy/headers.ts` holds the headers (unit-tested). The dev server sends them through `routeRules` (no CSP there: Vite needs eval); `pnpm generate` writes Cloudflare's `_headers` (with the CSP, built from `NUXT_PUBLIC_API_URL` and `NUXT_PUBLIC_FORMS_URL`) and `_redirects`. CSP: `default-src 'self'`; scripts and styles from the site only (`'unsafe-inline'` for Nuxt's payload and the JSON-LD); images and fonts from the site; `connect-src` the site and the backend API; `frame-src` only the Formalie forms host; `frame-ancestors 'none'`; `object-src 'none'`.


- No secrets in the code or `.env` that reach the browser. Only `NUXT_PUBLIC_*` addresses.
- **Security headers:**
  - HSTS, CSP (self; frames only from the Formalie forms origin; connect only to the Formalie API), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`;
  - `frame-ancestors 'none'`, so nobody embeds the website.
- No cookies except the language and theme choice. No third-party trackers or fonts from other sites: fonts are self-hosted, as in the app (`@nuxt/fonts`).
- Forms are Formalie's own embedded forms (`API-HOOKS.md`), protected by the portal's own checks (rate limits, bot checks, encrypted submission).
- **Legal and compliance wording** promises *controls* ("privacy and compliance controls", "encrypted in transit and at rest"), never certifications Formalie doesn't hold.
- A `/.well-known/security.txt` file names the security contact: a copy of formlyBackend's `docs/legal/security.txt` (`public/.well-known/security.txt`), renewed before its `Expires` date.

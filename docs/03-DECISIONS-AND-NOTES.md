# 03 — Decisions, Interpretations and Items to Confirm

Edit this file whenever a decision changes.

## Interpretations made from the brief

1. **"CEO on shared links"** is read as **SEO** (meta title, description, Open Graph image, canonical, noindex toggle).
2. **"Role level security"** in the backend brief is read as **PostgreSQL Row-Level Security (RLS)**. Role-based access (RBAC) is a separate, later feature.
3. **Tenant vs organisation:** tenant = subscribing account + subdomain; organisation = unit inside the tenant. Both IDs on every tenant table.
4. **Re-editing a published form:** creates a new draft version; the published version **stays live** until the draft is published. Option to "unpublish while editing" if the owner wants the form offline.
5. **"Same token should not be sent twice":** every issued token is unique (Fernet random IV + timestamp); refresh tokens are single-use and rotated; per-request replay is blocked by the envelope nonce. The access token itself is reused across requests until its 15-min expiry — making every access token single-use would force a round trip per request.
6. **"Microservice architecture":** modular monolith API + independent Celery worker services over RabbitMQ events, designed so modules can be split out later.
7. **"No reinventing CSS":** use Nuxt UI components, their `ui`/`class` props and Tailwind utilities only. The one exception is user-designed form themes, applied through CSS variables on the rendered form.
8. **Drag and drop:** Nuxt UI has no DnD primitive, so we use `vue-draggable-plus` (SortableJS) — the only extra UI dependency — with keyboard alternatives.
9. **Live collaboration:** planned as an optional later phase (Yjs CRDT over WebSockets) once the single-user builder is stable.

10. **Product name:** "Formalie" everywhere (some early docs said "Formly").
11. **Backend dev port:** `https://formalie.dev:5004` (configurable via `NUXT_API_PROXY_TARGET`).
12. **Mock API speaks the real protocol:** the Nitro mock performs the ECDH handshake and checks/produces real envelopes (expiry, nonce replay, AAD, method/path binding, CSRF). Envelope code lives in `shared/utils/crypto/` and is shared by browser and mock, so switching to FastAPI only needs both sides to match SECURITY-PROTOCOL.md.
13. **Mock vs proxy:** `NUXT_PUBLIC_API_MOCK=true` mounts `server/mock` at `/api/**`; otherwise `server/proxy/api.ts` forwards `/api/**` to the backend with `X-Forwarded-Host`. Read at startup — restart dev after changing it.
14. **SSR public forms and the envelope:** for server-rendered `/f/**`, Nitro performs its own handshake with the API (acting as a client, same protocol, scoped to the tenant host) to fetch the published schema; the browser then does its own handshake for submit. Finalised in F8.
15. **Draggable modals:** Nuxt UI modals have no drag; we use `@vueuse/core` `useDraggable` on the modal header plus arrow-key moves (F1). On phones modals stay docked.
16. **Languages:** `@nuxtjs/i18n` with 20 languages (see FRONTEND-SPEC §10). Strategy `no_prefix`; cookie `formalie_locale`. Yoruba, Hausa, Igbo, Amharic etc. can be added by one entry in `shared/utils/i18n/locales.ts` + one JSON file.
17. **TypeScript 6.0** pinned: typescript-eslint does not support TS 7 yet.
18. **`custom.css` removed:** `main.css` holds only the Tailwind/Nuxt UI imports and `@theme` tokens (CLAUDE.md rule 1).

19. **Host classification** is one pure, shared, unit-tested function (`resolveHostContext`): manage/root/www → manage entry; `{sub}.{rootDomain}` and `{sub}.localhost` → tenant; localhost/IP → manage, or a tenant via a **dev-only** `?tenant=` override (for phones on the LAN, which have no hosts file); reserved/nested/malformed → "workspace not found"; any other domain → custom domain (resolved by the API, later). The subdomain is never trusted alone (token must match, FRM-TEN-1003).

20. **Modal drag offset uses margins**, not `translate`/`transform`: Tailwind 4 centres Nuxt UI modals with the `translate` property and animates them with `transform`; margins move the dialog without fighting either.
21. **Nuxt UI 4.11 missing locale strings:** `dashboardSearch.title/description` and `dashboardSidebar.description` are absent from Nuxt UI's messages, so we pass our own translated `title`/`description` props. Re-check when upgrading Nuxt UI.
22. **User menu lives at the bottom of the sidebar** (as in the design reference); the navbar keeps search, notifications, language and theme.

23. **Design images are the exact target** (owner, 2026-10-02) — supersedes "don't copy colours": monochrome primary (`--ui-primary` = neutral-900 light / neutral-100 dark in `main.css`), rail + menu sidebar, search left in the top bar.
24. **Theme toggle placement** follows the design (sidebar SYSTEM → Dark mode); navbar theme button only below `lg` where the sidebar is hidden.
25. **Breadcrumbs** live in the top bar right after the search field (owner, 2026-10-02: avoid extra vertical space).
26. **Nuxt Icon endpoint moved to `/_nuxt_icon`** and icons are client-bundled: `/api/**` belongs to the backend (mock, dev proxy, Nginx in production).

27. **Font: Manrope** (Google, via `@nuxt/fonts`), weights 300–700; titles 600, body 400/500. Identified by comparing the design's glyphs (straight-tailed y, descending J, single-storey g, flagged 1, round geometric o) against candidates; Onest was the runner-up. Swap = one line in `main.css`.
28. **Language flags** come from the `circle-flags` icon set (`@iconify-json/circle-flags`), one flag per language variant (en → US, pt → BR, ar → SA, sw → KE …), shown on every language switcher.

29. **API client is framework-free** (`app/utils/api/client.ts`, transport injected) so the protocol is unit-tested against a fake server; `useApi()` only adds Nuxt bits. Session key, CSRF token and access token live in closures / module refs (memory only).
30. **Recovery policy** (once each per request): FRM-SEC-1004 → re-handshake, FRM-SEC-1006 → new CSRF, FRM-SEC-1002 → resend, FRM-AUTH-1001 → refresh; FRM-AUTH-1010/1011/1012 or failed refresh → session cleared (F3 redirects to login).
31. **Confirm dialogs** use one `<AppConfirmDialog>` in the layout driven by `useConfirm()` state — no component imports (CLAUDE.md rule 2).
32. **DataView: the URL is the source of truth**; table/grid preference is the only thing in localStorage (`formalie:view:<id>`, non-sensitive).
33. **`secondary` colour = violet** (closed status, as the design's purple badges); status → colour: draft warning/amber, published success/green, closed secondary/violet, archived neutral.
34. **`@internationalized/date`** added as a direct dependency: Nuxt UI's `UCalendar` needs its date objects and pnpm's strict layout requires the direct install.

## Corrections to the dev setup

- Hosts use `*.medique.dev` but the app runs on `formalie.dev` → switch to `*.formalie.dev` (see 02-DEV-ENVIRONMENT.md).
- mkcert cert must include `*.formalie.dev`.
- Venv named `mdq` but activated as `fmly` → standardise.

## To confirm

- Production domains: `formalie.com` (website), `manage.formalie.com`, `*.formalie.com`, short-link domain? Check domain and trademark availability for "formalie" — several products use that name.
- Email provider for OTP/notifications (Amazon SES, Postmark, Resend, Mailgun) and SMS provider.
- Hosting target (VPS/Kubernetes/cloud) and object storage provider.
- GeoIP: MaxMind GeoLite2 needs a free account and licence key.
- Payment providers for subscriptions (Paystack for NGN, Stripe for international).
- Data residency requirements for early customers.

# Production checklist (going live)

Everything that is set for development and must change before Formalie goes live, for every project. The owner asked on 2026-10-12 for one place that lists all of it, with step-by-step instructions and a reminder before going live.

**Keep it current.** Whenever a project adds a setting, a key, an address or a service that differs between development and production, add a line here, in every project's copy (this file is shared and identical in formalieFrontend, formlyBackend, formalieSite, formaliePlatformFront and formaliePlatformBack).

**Reminder.** Before any production deployment, walk the owner through this file from top to bottom. Each line gets ✅ once it's done on the production servers, never before.

Marks: ⬜ to do · ✅ done in production · ⏸ waiting on a decision or an account.

**Build-time reminder (owner, 2026-10-12).** Every production build points at production only. Before building the portal, the website or the platform admin for production, set every value in sections 2, 3, 7 and 8 to its production value; no development address may be left in a build or its environment: `formalie.dev`, `:2202`, `:3033`, `:5004`, `:5005`, `localhost`, `127.0.0.1`, mkcert paths. After each build, search the built files (`.output/public`) for those strings; the release script stops when one is found (B17).

---

## 1. Decisions and accounts first

- ⬜ **Hosting model (owner, 2026-10-12):**
  - The three front ends are **static SPA files on Cloudflare**, with no Node server: formalieFrontend (portal and public forms), formalieSite (website) and formaliePlatformFront (platform admin). Each is built with `nuxt generate` and deployed to Cloudflare (Workers static assets or Pages).
  - **Formalie's backend API is `https://services.formalie.com`** (`/api/v1/…`). Every front end calls it there, never `formalie.dev:5004`.
  - The API service for customers stays `https://api.formalie.com/{apiKey}/{endpoint}` (the gateway).
  - A small **Cloudflare Worker** on the form pages adds each form's title and preview image to `/{formKey}/fill` and `/{formKey}/embed` (link previews), and answers short links `/s/{code}` with a redirect. Everything else is the static app.
- ⬜ **Hosting for the back ends:** AWS or dedicated servers (decided per deployment, 02-DEV-ENVIRONMENT). Servers for: the API (`services.formalie.com`), the API service gateway (`api.formalie.com`), Celery workers and Beat, PostgreSQL (primary and replica), PgBouncer, Redis, RabbitMQ.
- ⬜ **Domain and DNS:** `formalie.com` on Cloudflare. Static front ends on Cloudflare: wildcard `*.formalie.com`, `manage.formalie.com` and `forms.formalie.com` (the portal build), `formalie.com` and `www` (the website build), the platform admin's own host (its build). To the servers through Nginx: `services.formalie.com` (the API) and `api.formalie.com` (the API service gateway).
- ⬜ **TLS certificates:** real certificates (Cloudflare origin certificates or Let's Encrypt), wildcard included. The mkcert certificates (`C:\devcerts\…`) and `NODE_EXTRA_CA_CERTS` are development only.
- ⬜ **Email sending provider:** Amazon SES or another SMTP service, with SPF, DKIM and DMARC on `formalie.com`. Development uses Mailpit.
- ⬜ **Object storage:** the cloud provider's S3 for uploads and exports. Development keeps them in the `data/storage` folder.
- ⏸ **Payments:** the owner's Payoneer account (F24): live keys and the webhook secret.
- ⏸ **SMS provider** for text-message codes (for example Twilio or Vonage), when workspaces should be able to use them.
- ⬜ **AI provider: Anthropic Claude** (owner 2026-10-12) for the assistant (B13): a production API key at console.anthropic.com (`ANTHROPIC_API_KEY`, backend only, separate from any development key), the model (`ANTHROPIC_MODEL`), spending limits on the Anthropic account, and Anthropic's commercial terms / data processing agreement accepted.
- ⬜ **MaxMind GeoLite2:** account ID and licence key for request locations.

## 2. Backend (formlyBackend `.env` on the production servers)

Generate fresh keys with `fmly\Scripts\python.exe scripts\gen_keys.py --write` on the production machine. Never copy development keys.

| Setting | Development | Production |
| --- | --- | --- |
| `APP_ENV` | `development` | ⬜ `production` |
| `APP_RELEASE` | `0.0.0-dev` | ⬜ the release version |
| `DOCS_ENABLED` | `true` | ⬜ `false` (no `/docs`, `/redoc`) |
| `SSL_CERTFILE` / `SSL_KEYFILE` | mkcert files | ⬜ empty when Nginx ends TLS; otherwise the real certificate |
| `ROOT_DOMAIN` | `formalie.dev` | ⬜ `formalie.com` |
| `TRUSTED_PROXIES` | `127.0.0.1/32,::1/128` | ⬜ the Nginx servers' addresses (and Cloudflare's ranges if Nginx doesn't rewrite them) |
| Server start | `--no-proxy-headers` | ⬜ keep `--no-proxy-headers` (required: the app reads the forwarded headers itself) |
| `DB_*_URL` | local, `CHANGE_ME` passwords | ⬜ production database, long random passwords per role; `DB_REPLICA_URLS` for the replica |
| `DB_PGBOUNCER` | `false` | ⬜ `true` when the API goes through PgBouncer |
| `REDIS_URL`, `CELERY_RESULT_BACKEND`, `RABBITMQ_URL` | WSL on this machine | ⬜ production services, with passwords and TLS |
| `ID_REF_ENC_KEY`, `ID_REF_MAC_KEY`, `FERNET_KEYS` | development keys | ⬜ new keys made on the server; keep a secure copy (losing them breaks every link and session) |
| `EMAIL_FROM` | `no-reply@formalie.dev` | ⬜ `Formalie <no-reply@formalie.com>` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Mailpit `127.0.0.1:1025`, `none` | ⬜ the email provider, `starttls` or `tls`, its user and password |
| `EMAIL_ASSETS_URL` | `https://manage.formalie.dev:2202` | ⬜ `https://manage.formalie.com` |
| `OAUTH_*_CLIENT_ID` / `_SECRET` | development apps | ⬜ the same apps with production addresses added (section 5), or production apps |
| `OAUTH_REDIRECT_BASE` | empty | ⬜ empty (it becomes `https://manage.formalie.com`) |
| `EMAIL_SPF_INCLUDE`, `EMAIL_DKIM_DOMAIN`, `EMAIL_BOUNCES_HOST` (B11) | `spf.formalie.com`, `dkim.formalie.com`, `bounces.formalie.com` | ⬜ the same names, really published (section 6): what workspaces' own sending domains point their SPF, DKIM CNAMEs and bounce CNAME at |
| `EMAIL_SMTP_ALLOW_LOCAL`, `SSO_ALLOW_LOCAL` (B11) | `false` (`true` only while trying a mail server or identity provider on this machine) | ⬜ `false` (never true in production; ignored there anyway) |
| `SAML_SP_CERT`, `SAML_SP_KEY` (B11) | empty (SAML requests unsigned) | ⬜ a certificate and private key (PEM) made for Formalie's SAML service provider, e.g. `openssl req -x509 -newkey rsa:2048 -nodes -days 1095 -subj "/CN=formalie.com"`; renew before it expires (workspaces' identity providers then import the new metadata) |
| `DNS_TIMEOUT_SECONDS` (B11) | `4` | ⬜ keep; the servers need a working DNS resolver (own domain and sending domain checks) |
| `INTERNAL_TOKEN` | development value | ⬜ a new random value, the same as the frontend's `NUXT_INTERNAL_TOKEN` |
| `LEGAL_TERMS_URL`, `LEGAL_PRIVACY_URL` | formalie.com pages | ⬜ check the pages exist on the website |
| `SUPPORT_EMAIL`, `SUPPORT_URL` (B14) | `support@formalie.com`, empty | ⬜ the real support mailbox (it must receive mail) and, if there is one, the support page; shown on the help centre's home until the platform settings take over |
| `STORAGE_DIR` | `data/storage` | ⬜ replaced by the object storage settings (to be added when storage is chosen) |
| `DATASOURCES_ALLOW_LOCAL` | `false` | ⬜ `false` (never true in production) |
| `WEBHOOKS_ALLOW_LOCAL` | `false` (`true` while trying a receiver on this machine) | ⬜ `false` (never true in production; ignored there anyway) |
| `EGRESS_IPS` | empty | ⬜ Formalie's fixed outgoing addresses, shown to customers for their database firewall |
| `GATEWAY_PORT` | `5005` (`python -m app.gateway`; the main app on 5004 also answers `api.formalie.dev`) | ⬜ the port Nginx sends `api.formalie.com` to (its own process, `uvicorn app.gateway:app --no-proxy-headers`) |
| `GATEWAY_IP_PER_MINUTE` | `6000` | ⬜ the ceiling per caller IP across all workspaces (keep 6000 or set from real traffic) |
| `API_NETWORKS_DIR` | empty (`data/geoip/networks`, usually no lists) | ⬜ a folder with `vpn.txt`, `proxy.txt`, `tor.txt`, `hosting.txt` (an IP or range per line) kept up to date, so access rules on anonymous networks match; without them only hosting providers are known (by network number) |
| `ANTHROPIC_API_KEY` (B13) | empty (the built-in assistant answers) or a development key | ⬜ the production key from console.anthropic.com (backend only, never in the frontend or logs), with a monthly spending limit set on the Anthropic account |
| `ANTHROPIC_MODEL`, `ANTHROPIC_FAST_MODEL` (B13) | `claude-opus-5-5`, `claude-haiku-5-5` | ⬜ keep, or the models the owner chooses (the fast one answers designs, reading answers, questions and summaries) |
| `ANTHROPIC_TIMEOUT_SECONDS`, `ANTHROPIC_MAX_RETRIES`, `ANTHROPIC_FALLBACKS` (B13) | `90`, `2`, `true` | ⬜ keep; the API servers must reach `api.anthropic.com` (outgoing HTTPS) |
| `RATE_LIMIT_ENABLED`, `RATE_LIMIT_FAIL_OPEN` | `true`, `true` | ⬜ `true`; decide fail open or closed when Redis is down |
| `ALERT_EMAILS` | empty | ⬜ the team's address for CRITICAL errors |
| `LOG_CONSOLE_FORMAT` | pretty | ⬜ `json` |
| `REQUEST_LOG_SINK` | `database` | ⬜ `celery` (the `logs` queue) at volume |
| `MAXMIND_ACCOUNT_ID`, `MAXMIND_LICENSE_KEY` | maybe empty | ⬜ set; Beat refreshes the databases weekly |
| `TEST_MYSQL_URL`, `DB_TEST_DATABASE` | test only | ⬜ not set in production |
| `DB_PLATFORM_READER_URL`, `DB_PLATFORM_WRITER_URL` (B16) | empty (roles without LOGIN) | ⬜ long random passwords; reader on the read replica's address, writer on the primary. `scripts/db_bootstrap.py` gives the roles LOGIN with them; the same URLs go into the platform admin's backend (formaliePlatformBack) |
| `PLATFORM_ADMIN_KEYS` (B16) | a development pair, also in the platform admin's settings (or empty: internal admin API refused) | ⬜ a new `key_id:secret` pair (secret 32+ random characters), the same in formaliePlatformBack; rotate by adding the new pair first, then removing the old |
| `PLATFORM_ADMIN_REQUIRE_MTLS`, `PLATFORM_ADMIN_CERT_FINGERPRINTS` (B16) | `false`, empty | ⬜ `true` (the API refuses every internal admin call in production without it) and the platform's client certificate fingerprint as Nginx passes it (`$ssl_client_fingerprint`) |
| `PLATFORM_ADMIN_NETWORKS` (B16) | local and private ranges | ⬜ only the platform admin's private addresses |
| `PLATFORM_ADMIN_WINDOW_SECONDS`, `SUPPORT_TICKET_SECONDS`, `SUPPORT_SESSION_MINUTES`, `SUPPORT_REQUEST_DAYS`, `PLATFORM_EVENTS_API_SAMPLE`, `PLATFORM_PUBLISHED_QUEUE` (B16) | `300`, `120`, `60`, `7`, `1.0`, `formalie.platform_published` | ⬜ keep (lower the API sample rate if `api.called` volume is too high) |

Also on the backend side:
- ⬜ **The API answers on `https://services.formalie.com`** (owner, 2026-10-12), not on each workspace's address. Backend work before go-live (B17): recognise the workspace from the `Origin` header (set by the browser, scripts can't change it) instead of the request host; CORS with credentials for `https://*.formalie.com`, `forms.` and verified workspace domains only; the refresh cookie on `services.` kept apart per workspace (still HttpOnly, Secure, SameSite=Strict, which holds because every host is on `formalie.com`); the sign-in providers' return addresses move to `services.` (section 5).
- ⬜ Database roles and schema: run `scripts/db_bootstrap.py` and `alembic upgrade head` against production; never seed development data (`scripts/seed_dev.py`) there.
- ⬜ Services: the API (several instances), the API service gateway (`app.gateway:app`, its own instances on `GATEWAY_PORT`), Celery workers per queue, Celery Beat, the outbox relay; restart on failure (systemd).
- ⬜ The development-only headers `X-Debug-Country` and `X-Debug-Network` are ignored when `APP_ENV=production` (nothing to set; check once with a call).
- ⬜ Backups: continuous WAL archiving plus a daily full backup, encrypted, off-site, 30 days; a restore drill before launch and monthly after.
- ⬜ Flower and the RabbitMQ management page: not public (VPN or SSH tunnel only).
- ⬜ Celery Beat runs `privacy.apply_retention` once a day (response retention; nothing to set).
- ⬜ B16: the `platform.published` consumer runs as its own service (`python -m app.modules.platform_bridge.consumer`, restart on failure); Beat runs `platform.expire_support_access` every minute (nothing to set).
- ⬜ The servers' Python has `xmlsec` working (python3-saml): `python -c "import xmlsec"`; on Linux the wheel needs `libxmlsec1` (`apt install libxmlsec1-openssl`) and `lxml` built against the same libxml2.

## 3. Frontend (formalieFrontend, the production build and its environment)

| Setting | Development | Production |
| --- | --- | --- |
| `NUXT_PUBLIC_API_MOCK` | `false` (mock off since 2026-10-12) | ⬜ `false`; the mock is never deployed |
| `NUXT_PUBLIC_API_BASE` | `/api/v1` (the dev server passes it on to `https://formalie.dev:5004`) | ⬜ `https://services.formalie.com/api/v1`, set at build time (a static build bakes it in) |
| `NUXT_API_PROXY_TARGET` | `https://formalie.dev:5004` | ⬜ not used (static build, no server) |
| `NUXT_INTERNAL_TOKEN` | the backend's development value | ⬜ the same new value as the backend's `INTERNAL_TOKEN` |
| `NUXT_PUBLIC_ROOT_DOMAIN` | `formalie.dev` | ⬜ `formalie.com` |
| `NUXT_PUBLIC_FORMS_HOST` | `forms.formalie.dev` | ⬜ `forms.formalie.com` |
| `NUXT_PUBLIC_API_SERVICE_URL` | `https://api.formalie.dev` | ⬜ `https://api.formalie.com` |
| `NUXT_PUBLIC_LEGAL_*` | formalie.com pages | ⬜ check they exist |
| `NUXT_PAYONEER_WEBHOOK_SECRET` | empty | ⏸ Payoneer's webhook secret |
| `NODE_EXTRA_CA_CERTS`, `DEV_HTTPS_*` | mkcert | ⬜ not used |
| Dev port `:2202` | in every development address | ⬜ gone (443 through Nginx) |

Also:
- ⬜ **Build as static SPA files** (owner, 2026-10-12): `pnpm generate` with the production values above, then deploy `.output/public` to Cloudflare; every unknown path falls back to `index.html`. One build serves `manage.`, `forms.` and every workspace subdomain. To do before this works (switch-over, B17 and phase SB): public form pages become client-rendered (the `ssr: true` route rules go); `server/` (mock, dev proxy, `api-host` middleware, `_ssr` routes) stays development only; the Cloudflare Worker (section 1) takes over form link previews and `/s/` short links.
- ⬜ No development address in the build: search `.output/public` for `formalie.dev`, `:2202`, `:5004`, `localhost` (build-time reminder at the top).
- ⬜ The capture tools (`scripts/site-screenshots/`, `scripts/brand/`) are development only.
- ⬜ The brand images in `public/brand/` are served (emails load the Formalie mark from `https://manage.formalie.com/brand/…`).

## 4. Nginx and Cloudflare

- ⬜ Hosts on Nginx: `services.formalie.com` → the API; `api.formalie.com` → the API service gateway (`GATEWAY_PORT`, every path, no `/api/` prefix; it sets its own CORS headers, so Nginx adds none); the front-end hosts (`*.formalie.com`, `manage.`, `forms.`, `formalie.com`, `www`, the platform admin) are static on Cloudflare and never reach Nginx.
- ⬜ Forward `X-Forwarded-Host`, `X-Forwarded-Proto` and the visitor's IP (`X-Forwarded-For`, or Cloudflare's `CF-Connecting-IP`).
- ⬜ HSTS, gzip / brotli, request size limits, the Content-Security-Policy from SECURITY-PROTOCOL (per-form `frame-ancestors` for embeds; Payoneer's frame hosts when connected).
- ⬜ Cloudflare: proxy on, SSL "Full (strict)", WAF and rate limiting rules, cache static assets only (never `/api`).

- ⬜ **Workspaces' own web domains (B11):** `custom.formalie.com` → Nginx (the CNAME target workspaces point their domain at), Nginx answers any host on it, and HTTPS certificates are issued per verified domain (Cloudflare for SaaS custom hostnames, or Caddy / certbot on demand, allowing only domains in `platform.custom_domains_directory` that are not released). The app maps the host to the workspace itself.

## 5. Sign-in providers (their consoles)

The production return addresses (backend README, "The addresses to register"). With the API on `services.formalie.com` they become `https://services.formalie.com/api/v1/auth/oauth/{google | facebook}/callback`; B17 confirms the final form before they are registered:
- `https://manage.formalie.com/api/v1/auth/oauth/google/callback`
- `https://manage.formalie.com/api/v1/auth/oauth/facebook/callback`

- ⬜ **Google:** add the production address under Authorised redirect URIs; publish the app (out of Testing) and complete Google's verification of the consent screen.
- ⬜ **Facebook:** add the production address under Valid OAuth Redirect URIs and `formalie.com` under App domains; switch the app to Live; complete Business verification if asked.
- ⬜ Remove development-only addresses you no longer need (the `:2202` ones can stay on a separate development app).
- No Microsoft app (owner, 2026-10-12): Microsoft accounts come in through each workspace's own single sign-on with Entra ID, set up by the customer in Settings → Sign-in. If a Microsoft social sign-in app was registered earlier, it can be deleted in Entra (and `OAUTH_MICROSOFT_*` removed from the server's environment; the API ignores them).

## 6. Email deliverability

- ⬜ SPF, DKIM and DMARC records for `formalie.com` (and for each workspace's own sending domain, B11).
- ⬜ **Workspaces' own sending domains (B11):** publish `spf.formalie.com` (an SPF record with the relay's senders, which workspaces include), and for each verified workspace the DKIM keys at `fm1.{key}.dkim.formalie.com` and `fm2.{key}.dkim.formalie.com` (the `key` is in `email_sending.domain`); the relay (SES or the chosen provider) must sign mail from that domain with the selector `fm1` (rotate to `fm2`). `bounces.formalie.com` must receive bounces for `fm-bounces.{their domain}` (the envelope sender `bounces@fm-bounces.{domain}`) and the relay must allow those From and MAIL FROM addresses (for SES: verify each domain as an identity with custom MAIL FROM, or use the provider's own DKIM CNAMEs instead and change the records the portal lists).
- ⬜ Unsubscribe headers (`List-Unsubscribe`, `List-Unsubscribe-Post`) on optional emails, required by Gmail and Yahoo for bulk senders (being built).
- ⬜ Send a test of every template to Gmail, Outlook and Apple Mail and check the layout.

## 7. Website (formalieSite)

- ⬜ Production address `https://formalie.com` (the site's CLAUDE.md lists development as `https://formalie.dev:3033`).
- ⬜ Built as static files (`nuxt generate`) and deployed to Cloudflare; anything it calls points at `https://services.formalie.com`; no `:3033` or `formalie.dev` left in the build.
- ⬜ Legal pages content from the platform admin; the links used by the portal and emails resolve.
- ⬜ Sign-up links go to `https://manage.formalie.com/auth/signup`.
- ⬜ SEO settings (sitemap, robots, canonical addresses on `.com`).

## 8. Platform admin (formaliePlatformFront / formaliePlatformBack)

- ⬜ Their own production settings: `docs/04-HOSTING.md` in each project.
- ⬜ formaliePlatformFront built as static SPA files (`nuxt generate`) on Cloudflare, calling formaliePlatformBack's production address; no development address left in the build.
- ⬜ Database roles `platform_reader` / `platform_writer` in Formalie's production database (PLATFORM-ADMIN-INTEGRATION §5): LOGIN through `DB_PLATFORM_READER_URL` / `DB_PLATFORM_WRITER_URL` and `scripts/db_bootstrap.py`; `platform_reader` connects to the read replica only.
- ⬜ The internal admin API between the two systems: a private Nginx listener for `/internal/admin/v1/` only (never on the public hosts) with `ssl_verify_client on`, the platform's CA, and `X-Client-Verify` / `X-Client-Cert-Fingerprint` passed to the API; HMAC keys made for production (`PLATFORM_ADMIN_KEYS`, the same pair in formaliePlatformBack).
- ⬜ RabbitMQ: the platform's own user with permission to bind its queue `platform.analytics` to `formalie.events` and to publish `platform.published` there; Formalie's consumer reads `formalie.platform_published`.

## 9. Last checks on launch day

- ⬜ No development value left: search the production environment files and every built front end (`.output/public`) for `formalie.dev`, `:2202`, `:3033`, `:5004`, `:5005`, `CHANGE_ME`, `localhost`, `127.0.0.1`, `mailpit`.
- ⬜ Sign up, sign in with each provider, publish a form, submit a response, receive its email, export, on production.
- ⬜ Monitoring and alerts reach the team; backups ran once and a restore was tested.

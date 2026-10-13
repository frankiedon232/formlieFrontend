# Production checklist (going live)

Everything that is set for development and must change before Formalie goes live, for every project. The owner asked on 2026-10-12 for one place that lists all of it, with step-by-step instructions and a reminder before going live.

**Keep it current.** Whenever a project adds a setting, a key, an address or a service that differs between development and production, add a line here, in every project's copy (this file is shared and identical in formalieFrontend, formlyBackend, formalieSite, formaliePlatformFront and formaliePlatformBack).

**Reminder.** Before any production deployment, walk the owner through this file from top to bottom. The step-by-step instructions (servers, Nginx, Cloudflare, building and deploying each project, first checks, later releases) are in [`DEPLOYMENT-GUIDE.md`](DEPLOYMENT-GUIDE.md). Each line gets ✅ once it's done on the production servers, never before.

Marks: ⬜ to do · ✅ done in production · ⏸ waiting on a decision or an account.

**Build-time reminder (owner, 2026-10-12).** Every production build points at production only. Before building the portal, the website or the platform admin for production, set every value in sections 2, 3, 7 and 8 to its production value; no development address may be left in a build or its environment: `formalie.dev`, `:2202`, `:3033`, `:5004`, `:5005`, `localhost`, `127.0.0.1`, mkcert paths. After each build, search the built files (`.output/public`) for those strings; the release script stops when one is found (B17).

---

## 1. Decisions and accounts first

- ⬜ **Hosting model (owner, 2026-10-12):**
  - The three front ends are **static SPA files on Cloudflare**, with no Node server: formalieFrontend (portal and public forms), formalieSite (website) and formaliePlatformFront (platform admin). Each is built with `nuxt generate` and deployed to Cloudflare (Workers static assets or Pages).
  - **Formalie's backend API is `https://services.formalie.com`** (`/api/v1/…`), never `formalie.dev:5004`. The portal reaches it through its Worker: every portal host (`*.formalie.com`, `manage.`, `forms.`, workspaces' verified own domains) answers `/api/*` itself and the Worker forwards it to `services.formalie.com` with the edge secret (`EDGE_SECRET`, section 2). So the browser stays on one origin: no CORS, the cookies stay host-only per workspace as today, and the backend still recognises the workspace from the (forwarded) host.
  - The API service for customers stays `https://api.formalie.com/{apiKey}/{endpoint}` (the gateway).
  - One **Cloudflare Worker** per front end serves the static app. The portal's Worker also proxies `/api/*` to `services.formalie.com` (adding `X-Formalie-Edge` and `X-Forwarded-Host / -Proto / -For`), adds each form's title and preview image to `/{formKey}/fill` and `/{formKey}/embed` (link previews, from `GET /api/v1/edge/forms/{formKey}/preview`), and answers short links `/s/{code}` with a redirect (from `GET /api/v1/edge/links/{code}`).
- ⬜ **Hosting for the back ends:** AWS or dedicated servers (decided per deployment, 02-DEV-ENVIRONMENT). Servers for: the API (`services.formalie.com`), the API service gateway (`api.formalie.com`), Celery workers and Beat, PostgreSQL (primary and replica), PgBouncer, Redis, RabbitMQ.
- ⬜ **PostgreSQL extension `pg_trgm`** (owner 2026-10-13; migration 0040 creates it in the `platform` schema for the audit trail and API call log search): it ships with PostgreSQL (contrib) and is a trusted extension, so the migration role needs CREATE on the database; on a managed database (AWS RDS and similar) check it is on the allowed list.
- ⬜ **Domain and DNS:** `formalie.com` on Cloudflare. Static front ends on Cloudflare: wildcard `*.formalie.com`, `manage.formalie.com` and `forms.formalie.com` (the portal build), `formalie.com` and `www` (the website build), the platform admin's own host (its build). To the servers through Nginx: `services.formalie.com` (the API) and `api.formalie.com` (the API service gateway).
- ⬜ **TLS certificates:** real certificates (Cloudflare origin certificates or Let's Encrypt), wildcard included. The mkcert certificates (`C:\devcerts\…`) and `NODE_EXTRA_CA_CERTS` are development only.
- ⬜ **Email sending provider:** Amazon SES or another SMTP service, with SPF, DKIM and DMARC on `formalie.com`. Development uses Mailpit.
- ⬜ **Object storage:** the cloud provider's S3 for uploads and exports. Development keeps them in the `data/storage` folder.
- ⬜ **Payments: Paddle** (primary, merchant of record; owner 2026-10-13; formlyBackend docs/PADDLE-SETUP-GUIDE.md): the live account approved, `PADDLE_ENVIRONMENT=production`, a live `PADDLE_API_KEY` (permissions as in the guide), a live `PADDLE_CLIENT_TOKEN`, the notification destination at `https://services.formalie.com/api/v1/billing/webhooks/paddle` and its `PADDLE_WEBHOOK_SECRET`, `scripts/paddle_catalog.py --apply` run with the live key, the default payment link `https://manage.formalie.com/settings/billing`, then one real small purchase and refund.
- ⏸ **Payments: Payoneer** (second option, later): live keys and the webhook secret when it is connected.
- ⏸ **SMS provider** for text-message codes: Twilio or Vonage (the owner sets up the account; step by step in formlyBackend `docs/SMS-SETUP-GUIDE.md`). Production: billing on, the countries served allowed, sender registration where a country requires it (US A2P 10DLC).
- ⬜ **AI provider: Anthropic Claude** (owner 2026-10-12) for the assistant (B13): a production API key at console.anthropic.com (`ANTHROPIC_API_KEY`, backend only, separate from any development key), the model (`ANTHROPIC_MODEL`), spending limits on the Anthropic account, and Anthropic's commercial terms / data processing agreement accepted.
- ⬜ **MaxMind GeoLite2:** account ID and licence key for request locations.

## 2. Backend (formlyBackend `.env` on the production servers)

Generate fresh keys with `fmly\Scripts\python.exe scripts\gen_keys.py --write` on the production machine. Never copy development keys.

| Setting | Development | Production |
| --- | --- | --- |
| `APP_ENV` | `development` | ⬜ `production`, always set explicitly (B17: unset means production; staging and production refuse to start without `FERNET_KEYS`, `SECRET_KEYS`, `ID_REF_*`, `DB_APP_URL`, broker and Redis credentials, or with any `*_ALLOW_LOCAL` on; `dev_*` helpers only with exactly `development`) |
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
| `SECRET_KEYS` (security review L17) | a development key | ⬜ a new key made on the server, never one of the `FERNET_KEYS`; keep a secure copy (losing it makes every stored credential and two-step secret unreadable). After setting it on a database that already holds secrets, run `scripts/reencrypt_secrets.py --apply` once |
| `EMAIL_FROM` | `no-reply@formalie.dev` | ⬜ `Formalie <no-reply@formalie.com>` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Mailpit `127.0.0.1:1025`, `none` | ⬜ the email provider, `starttls` or `tls`, its user and password |
| Bounces and complaints (security review L19) | none | ⬜ once the email provider is chosen: its bounce and complaint notifications feed a do-not-email list, so a hard-bounced or complaining address gets no more mail (to build with the provider) |
| `EMAIL_ASSETS_URL` | `https://manage.formalie.dev:2202` | ⬜ `https://manage.formalie.com` |
| `OAUTH_*_CLIENT_ID` / `_SECRET` | development apps | ⬜ the same apps with production addresses added (section 5), or production apps |
| `OAUTH_REDIRECT_BASE` | empty | ⬜ empty (it becomes `https://manage.formalie.com`) |
| `EMAIL_SPF_INCLUDE`, `EMAIL_DKIM_DOMAIN`, `EMAIL_BOUNCES_HOST` (B11) | `spf.formalie.com`, `dkim.formalie.com`, `bounces.formalie.com` | ⬜ the same names, really published (section 6): what workspaces' own sending domains point their SPF, DKIM CNAMEs and bounce CNAME at |
| `EMAIL_SMTP_ALLOW_LOCAL`, `SSO_ALLOW_LOCAL` (B11) | `false` (`true` only while trying a mail server or identity provider on this machine) | ⬜ `false` (never true in production; ignored there anyway) |
| `SAML_SP_CERT`, `SAML_SP_KEY` (B11) | empty (SAML requests unsigned) | ⬜ a certificate and private key (PEM) made for Formalie's SAML service provider, e.g. `openssl req -x509 -newkey rsa:2048 -nodes -days 1095 -subj "/CN=formalie.com"`; renew before it expires (workspaces' identity providers then import the new metadata) |
| `DNS_TIMEOUT_SECONDS` (B11) | `4` | ⬜ keep; the servers need a working DNS resolver (own domain and sending domain checks) |
| `INTERNAL_TOKEN` | development value | ⬜ **retired:** leave it empty. The frontend no longer uses it (static build, no Nuxt server, no `NUXT_INTERNAL_TOKEN`); its only remaining use is the two unused routes `GET /api/v1/internal/public-forms/{key}` and `GET /api/v1/internal/short/{code}` (the old server-rendered form and short-link reads, `app/modules/public/router.py`), which refuse everything while it is empty, and Nginx blocks `/api/v1/internal/` anyway (section 4) |
| Website's API address (formalieSite `NUXT_PUBLIC_API_URL`) | `https://formalie.dev:5004/api/v1` | ⬜ `https://services.formalie.com/api/v1` (the `/public/plans`, `/public/legal`, `/public/platform` routes), never `api.formalie.com`, which is customers' own API |
| `LEGAL_TERMS_URL`, `LEGAL_PRIVACY_URL` | development `https://formalie.dev:3033/legal/terms`, `/legal/privacy` (the website's dev server) | ⬜ the website's legal pages (documentation style, `docs/legal/` drafts reviewed by a lawyer and filled in); check they open |
| `SUPPORT_EMAIL`, `SUPPORT_URL` (B14) | `support@formalie.com`, empty | ⬜ the real support mailbox (it must receive mail) and, if there is one, the support page; shown on the help centre's home until the platform settings take over |
| `STORAGE_DIR` | `data/storage` | ⬜ replaced by the object storage settings (to be added when storage is chosen) |
| `DATASOURCES_ALLOW_LOCAL` | `false` | ⬜ `false` (never true in production) |
| `WEBHOOKS_ALLOW_LOCAL` | `false` (`true` while trying a receiver on this machine) | ⬜ `false` (never true in production; ignored there anyway) |
| `EGRESS_IPS` | empty | ⬜ Formalie's fixed outgoing addresses, shown to customers for their database firewall |
| `GATEWAY_PORT` | `5005` (`python -m app.gateway`; the main app on 5004 also answers `api.formalie.dev`) | ⬜ the port Nginx sends `api.formalie.com` to (its own process, `uvicorn app.gateway:app --no-proxy-headers`) |
| `GATEWAY_IP_PER_MINUTE` | `6000` | ⬜ the ceiling per caller IP across all workspaces (keep 6000 or set from real traffic) |
| `API_NETWORKS_DIR` | empty (`data/geoip/networks`, usually no lists) | ⬜ a folder with `vpn.txt`, `proxy.txt`, `tor.txt`, `hosting.txt` (an IP or range per line) kept up to date, so access rules on anonymous networks match; without them only hosting providers are known (by network number) |
| `SMS_PROVIDER`, `TWILIO_*` or `VONAGE_*` | `none`, or a trial account's keys | ⏸ `twilio` or `vonage` with the production account's keys and sender (backend only; docs/SMS-SETUP-GUIDE.md) |
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
| `DB_ADMIN_API_URL` (B17) | `formalie_admin_api` on the local database | ⬜ a long random password, on the primary; run `scripts/db_bootstrap.py` before `alembic upgrade head` (it creates the role, member of `formalie_app`, and gives it the platform admin functions, which the portal's role no longer has) |
| `REQUEST_LOG_RETENTION_DAYS` (B17) | `30` | ⬜ keep `30`, the period the privacy policy states. The platform admin can change it (`log_retention` in platform settings: 0 keeps forever); Beat `logs.apply_retention` archives each older month (encrypted with `BACKUP_ENCRYPTION_KEY`, which must be set or nothing is removed) and then removes it; the archives live in the file store under `platform/log-archives/` and are downloaded from the platform admin |
| `REQUEST_BODY_MAX_BYTES` (B17) | `2097152` (2 MB) | ⬜ keep; Nginx's `client_max_body_size` per location matches it (DEPLOYMENT-GUIDE Part 6), uploads have their own |
| `PLATFORM_ADMIN_KEYS` (B16) | a development pair, also in the platform admin's settings (or empty: internal admin API refused) | ⬜ a new `key_id:secret` pair (secret 32+ random characters), the same in formaliePlatformBack; rotate by adding the new pair first, then removing the old |
| `PLATFORM_ADMIN_REQUIRE_MTLS`, `PLATFORM_ADMIN_CERT_FINGERPRINTS` (B16) | `false`, empty | ⬜ `true` (the API refuses every internal admin call in production without it) and the platform's client certificate fingerprint as Nginx passes it (`$ssl_client_fingerprint`) |
| `PLATFORM_ADMIN_NETWORKS` (B16) | local and private ranges | ⬜ only the platform admin's private addresses |
| `PLATFORM_ADMIN_WINDOW_SECONDS`, `SUPPORT_TICKET_SECONDS`, `SUPPORT_SESSION_MINUTES`, `SUPPORT_REQUEST_DAYS`, `PLATFORM_EVENTS_API_SAMPLE`, `PLATFORM_PUBLISHED_QUEUE` (B16) | `300`, `120`, `60`, `7`, `1.0`, `formalie.platform_published` | ⬜ keep (lower the API sample rate if `api.called` volume is too high) |
| `EDGE_SECRET` (2026-10-12) | empty (off) | ⬜ a long random value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), the same in each Worker's secret `EDGE_SECRET` (`wrangler secret put EDGE_SECRET`); rotate both together |
| `SERVICES_HOST` (2026-10-12) | `services.formalie.dev` | ⬜ `services.formalie.com` |

Also on the backend side:
- ⬜ **The API runs on `https://services.formalie.com`** (owner, 2026-10-12) and is reached through the portal's Worker (built 2026-10-12, nothing else to build): the Worker proxies `/api/*` from every portal host with `X-Formalie-Edge: <EDGE_SECRET>`, and only with that secret does the API trust `X-Forwarded-Host`, `X-Forwarded-Proto` and `X-Forwarded-For` (SECURITY-PROTOCOL, Edge trust). No CORS, no Origin-based lookup, the cookies stay as they are, workspaces' own domains work the same way, and the sign-in providers' return addresses stay on `manage.` (section 5). Direct calls to `services.formalie.com` (health, the platform admin) answer as a host with no workspace.
- ⬜ Check once after deploying: a call through a portal host shows the workspace; the same call straight to `services.formalie.com` with a made-up `X-Forwarded-Host` and no secret does not.
- ⬜ Database roles and schema: run `scripts/db_bootstrap.py` and `alembic upgrade head` against production; never seed development data (`scripts/seed_dev.py`) there.
- ⬜ Services: the API (several instances), the API service gateway (`app.gateway:app`, its own instances on `GATEWAY_PORT`), Celery workers per queue, Celery Beat, the outbox relay; restart on failure (systemd).
- ⬜ The development-only headers `X-Debug-Country` and `X-Debug-Network` are ignored when `APP_ENV=production` (nothing to set; check once with a call).
- ⬜ Backups: continuous WAL archiving plus a daily full backup, encrypted, off-site, 30 days; a restore drill before launch and monthly after.
- ⬜ `BACKUP_ENCRYPTION_KEY` (32 bytes, base64; `scripts/gen_keys.py`): a new one for production, never the development key, with a copy kept apart from the backups (a password manager or the secret store). The drill is `scripts/backups.py restore` into a scratch database (formlyBackend README, "Backups and the restore drill"); it must say "Restore drill passed".
- ⬜ Flower and the RabbitMQ management page: not public (VPN or SSH tunnel only).
- ⬜ The platform admin's Operations page shows every health entry `ok` after deploying (Beat's heartbeat, the last backup, next month's partitions); monitoring and alerts are run there.
- ⬜ Celery Beat runs `privacy.apply_retention` once a day (response retention; nothing to set).
- ⬜ B17: Beat also runs `forms.sweep_trash` (every 5 minutes), `notifications.announce_due` (every minute), `events.prune_processed` and `db.drop_expired_partitions` (daily). Nothing to set.
- ⬜ B17: the workers that connect to customers' databases (queue `destinations`, and the API for the explorer and the Query editor) run as a system user without `~/.pgpass`, `~/.postgresql/`, `~/.my.cnf` or `freetds.conf` aliases, and without `PG*`, `TDSDUMP` or `TNS_ADMIN` in their environment; ideally a separate worker user that can't read `.env` (review C1, point 3).
- ⬜ B16: the `platform.published` consumer runs as its own service (`python -m app.modules.platform_bridge.consumer`, restart on failure); Beat runs `platform.expire_support_access` every minute (nothing to set).
- ⬜ Beat runs `platform.close_due_workspaces` every 10 minutes: a closing workspace past its date becomes `closed` (refuses sign-in, the API and answers; nothing is deleted). Nothing to set.
- ⬜ The servers' Python has `xmlsec` working (python3-saml): `python -c "import xmlsec"`; on Linux the wheel needs `libxmlsec1` (`apt install libxmlsec1-openssl`) and `lxml` built against the same libxml2.

## 3. Frontend (formalieFrontend, the production build and its environment)

| Setting | Development | Production |
| --- | --- | --- |
| `NUXT_PUBLIC_API_MOCK` | `false` (mock off since 2026-10-12) | ⬜ `false`; the mock is never deployed |
| `NUXT_PUBLIC_API_BASE` | `/api/v1` (the dev server passes it on to `https://formalie.dev:5004`) | ⬜ stays `/api/v1`: the Worker forwards it to `https://services.formalie.com` |
| Worker secret `EDGE_SECRET` | not used | ⬜ `npx wrangler@4 secret put EDGE_SECRET`, the backend's `EDGE_SECRET` value (never in the build or in `wrangler.jsonc`) |
| `NUXT_API_PROXY_TARGET` | `https://formalie.dev:5004` | ⬜ not used (static build, no server) |
| `NUXT_PUBLIC_ROOT_DOMAIN` | `formalie.dev` | ⬜ `formalie.com` |
| `NUXT_PUBLIC_FORMS_HOST` | `forms.formalie.dev` | ⬜ `forms.formalie.com` |
| `NUXT_PUBLIC_API_SERVICE_URL` | `https://api.formalie.dev` | ⬜ `https://api.formalie.com` |
| `NUXT_PUBLIC_SITE_URL` (the website: legal pages `/legal/{slug}` on public forms and sign-up, the Enterprise enquiry) | `https://formalie.dev:3033` | ⬜ `https://formalie.com` |
| `NUXT_PAYONEER_WEBHOOK_SECRET` | empty | ⏸ Payoneer's webhook secret |
| `NODE_EXTRA_CA_CERTS`, `DEV_HTTPS_*` | mkcert | ⬜ not used |
| Dev port `:2202` | in every development address | ⬜ gone (443 on Cloudflare) |

Also:
- ⬜ **Build as static SPA files** (owner, 2026-10-12; built 2026-10-12): `pnpm generate --dotenv .env.production` with the production values above, then `npx wrangler@4 deploy` (DEPLOYMENT-GUIDE Part 8a); every unknown path falls back to `index.html`. One build serves `manage.`, `forms.` and every workspace subdomain. Every page is client-rendered (also the public form pages and `/s/`); `server/` (mock, dev proxy, `api-host`, `embed-frame`) is development only; the Cloudflare Worker (`edge/worker.ts`, section 1) proxies `/api/*` and adds form link previews and `/s/` short-link redirects.
- ⬜ No development address in the build: `pnpm release:check` must say clean (it searches `.output/public`, and `.output/edge` when the Worker bundle was made, for `formalie.dev`, `:2202`, `:3033`, `:5004`, `:5005`, `localhost`, `127.0.0.1`, `mkcert`, `devcerts`).
- ⬜ The Worker routes in `wrangler.jsonc` (`manage.formalie.com/*`, `forms.formalie.com/*`, `*.formalie.com/*`) are commented out until go-live; uncomment them then, with `api.formalie.com/*` and `services.formalie.com/*` set to Worker "None" in Cloudflare (DEPLOYMENT-GUIDE Part 7).
- ⬜ The capture tools (`scripts/site-screenshots/`, `scripts/brand/`) are development only.
- ⬜ The brand images in `public/brand/` are served (emails load the Formalie mark from `https://manage.formalie.com/brand/…`).

## 4. Nginx and Cloudflare

- ⬜ Hosts on Nginx: `services.formalie.com` → the API; `api.formalie.com` → the API service gateway (`GATEWAY_PORT`, every path, no `/api/` prefix; it sets its own CORS headers, so Nginx adds none); the front-end hosts (`*.formalie.com`, `manage.`, `forms.`, `formalie.com`, `www`, the platform admin) are static on Cloudflare and never reach Nginx.
- ⬜ On `services.formalie.com`, pass the Worker's `X-Formalie-Edge`, `X-Forwarded-Host`, `X-Forwarded-Proto` and `X-Forwarded-For` through unchanged (never overwrite `X-Forwarded-Host` with `$host`; the API checks the secret itself) and keep `Host $host` (DEPLOYMENT-GUIDE Part 6). Nginx on app-1 accepts Cloudflare's addresses only.
- ⬜ Visitor address and location headers (security review M14; DEPLOYMENT-GUIDE Part 6): `real_ip` from Cloudflare's ranges, then `CF-Connecting-IP` overwritten with `$remote_addr` and Cloudflare's location headers (`CF-IPCountry` and the other `CF-IP*` / `CF-Region*` / `CF-Postal-Code` / `CF-Timezone`) cleared unless the peer is Cloudflare; `X-Client-Verify` and `X-Client-Cert-Fingerprint` cleared on the public listeners; Cloudflare Authenticated Origin Pulls on.
- ⬜ `location /api/v1/internal/ { return 404; }` and `location /internal/ { return 404; }` on the public server blocks (review L15).
- ⬜ `client_max_body_size` per location, sized to what each route needs (review M12 and I6; the `api.` block needs its own for gateway uploads).
- ⬜ HSTS, gzip / brotli, request size limits, the Content-Security-Policy from SECURITY-PROTOCOL (per-form `frame-ancestors` for embeds; Payoneer's frame hosts when connected).
- ⬜ Cloudflare: proxy on, SSL "Full (strict)", WAF and rate limiting rules, cache static assets only (never `/api`).

- ⬜ **Workspaces' own web domains (B11):** Cloudflare for SaaS on the zone with the fallback origin `custom.formalie.com` (the CNAME target workspaces point their domain at); each verified domain (only domains in `platform.custom_domains_directory` that are not released) is a custom hostname with its own certificate from Cloudflare, and the portal's Worker answers it like a workspace subdomain: the static app, and `/api/*` forwarded to `services.formalie.com` with `X-Forwarded-Host` = that domain, which the API maps to the workspace (DEPLOYMENT-GUIDE 8d). Nginx is not involved.

## 5. Sign-in providers (their consoles)

The production return addresses (backend README, "The addresses to register"). They stay on `manage.formalie.com`: the browser comes back to the portal host and its Worker forwards the call to the API (2026-10-12):
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
- ⬜ **Build environment** (formalieSite, set before `NODE_ENV=production pnpm generate`; S7, 2026-10-13): `NUXT_PUBLIC_SITE_URL=https://formalie.com` (canonical addresses, hreflang, sitemap, Open Graph), `NUXT_PUBLIC_PORTAL_URL=https://manage.formalie.com`, `NUXT_PUBLIC_FORMS_URL=https://forms.formalie.com`, `NUXT_PUBLIC_API_URL=https://services.formalie.com/api/v1` (never `api.formalie.com`). The build writes them into the pages and into `_headers` (the CSP allows only that API and that forms host).
- ⬜ Built as static files (`nuxt generate`, output `.output/public`) and deployed to Cloudflare; anything it calls points at `https://services.formalie.com`; no `:3033`, `:5004`, `:2202` or `formalie.dev` left in the build (search `.output/public`, `_headers` included).
- ⬜ Cloudflare serves the build's `_headers` (HSTS, CSP with `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff`, Referrer and Permissions policies, long caching for `/_nuxt/*` and `/_fonts/*`) and `_redirects` (`/terms`, `/privacy`, `/refunds`, `/legal` answered with 301). Brotli or gzip on.
- ⬜ The backend answers `/public/plans`, `/public/legal`, `/public/legal/{slug}` and `/public/platform` on `services.formalie.com` with `Access-Control-Allow-Origin: *` (the website refreshes prices and legal text in the browser).
- ⬜ Formalie's own forms `FormalieEn` and `FormalieHp`: make them once in Formalie's own workspace with `scripts/platform_forms.py --workspace <its subdomain>` (formlyBackend; published, with these fixed keys, owned by the workspace's Owner), and allowed to be embedded on `https://formalie.com` (if their "allowed websites" list is set, add it); then formalieSite `NUXT_PUBLIC_FORMS_LIVE=true`.
- ⬜ Legal pages content from the platform admin (each published version replaces the Draft note); `pnpm legal:sync` run once more so the site's offline copy matches; the links used by the portal and emails (`/legal/terms`, `/legal/privacy`, `/terms`, `/privacy`, `/refunds`) resolve.
- ⬜ `public/.well-known/security.txt` (a copy of formlyBackend `docs/legal/security.txt`) renewed before its `Expires` date (2027-10-13); the mailboxes it and the trust page name exist (security@, privacy@, abuse@, support@, sales@).
- ⬜ Sign-up links go to `https://manage.formalie.com/auth/signup` (with `plan` and `period` once the portal reads them, F24); Sign in to `/auth/find-workspace`.
- ⬜ SEO settings (sitemap, robots, canonical addresses on `.com`): submit `https://formalie.com/sitemap.xml` to Google Search Console and Bing Webmaster Tools, and check a few pages with the Rich Results Test.
- ⬜ Run Lighthouse (mobile) on the live site: home, pricing, a feature page, a legal page; note the scores in formalieSite PROGRESS.md.

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

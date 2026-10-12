# Production checklist (going live)

Everything that is set for development and must change before Formalie goes live, for every project. The owner asked on 2026-10-12 for one place that lists all of it, with step-by-step instructions and a reminder before going live.

**Keep it current.** Whenever a project adds a setting, a key, an address or a service that differs between development and production, add a line here, in every project's copy (this file is shared and identical in formalieFrontend, formlyBackend, formalieSite, formaliePlatformFront and formaliePlatformBack).

**Reminder.** Before any production deployment, walk the owner through this file from top to bottom. Each line gets ✅ once it's done on the production servers, never before.

Marks: ⬜ to do · ✅ done in production · ⏸ waiting on a decision or an account.

---

## 1. Decisions and accounts first

- ⬜ **Hosting:** AWS or dedicated servers (decided per deployment, 02-DEV-ENVIRONMENT). Servers for: Nuxt (portal and public forms), the API, the API service gateway (`api.formalie.com`), Celery workers and Beat, PostgreSQL (primary and replica), PgBouncer, Redis, RabbitMQ.
- ⬜ **Domain and DNS:** `formalie.com` on Cloudflare: wildcard `*.formalie.com` and the root to Nginx; `forms.formalie.com`, `api.formalie.com`, `manage.formalie.com`. The website (formalieSite) answers on `formalie.com` and `www`.
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
| `INTERNAL_TOKEN` | development value | ⬜ a new random value, the same as the frontend's `NUXT_INTERNAL_TOKEN` |
| `LEGAL_TERMS_URL`, `LEGAL_PRIVACY_URL` | formalie.com pages | ⬜ check the pages exist on the website |
| `STORAGE_DIR` | `data/storage` | ⬜ replaced by the object storage settings (to be added when storage is chosen) |
| `DATASOURCES_ALLOW_LOCAL` | `false` | ⬜ `false` (never true in production) |
| `WEBHOOKS_ALLOW_LOCAL` | `false` (`true` while trying a receiver on this machine) | ⬜ `false` (never true in production; ignored there anyway) |
| `EGRESS_IPS` | empty | ⬜ Formalie's fixed outgoing addresses, shown to customers for their database firewall |
| `RATE_LIMIT_ENABLED`, `RATE_LIMIT_FAIL_OPEN` | `true`, `true` | ⬜ `true`; decide fail open or closed when Redis is down |
| `ALERT_EMAILS` | empty | ⬜ the team's address for CRITICAL errors |
| `LOG_CONSOLE_FORMAT` | pretty | ⬜ `json` |
| `REQUEST_LOG_SINK` | `database` | ⬜ `celery` (the `logs` queue) at volume |
| `MAXMIND_ACCOUNT_ID`, `MAXMIND_LICENSE_KEY` | maybe empty | ⬜ set; Beat refreshes the databases weekly |
| `TEST_MYSQL_URL`, `DB_TEST_DATABASE` | test only | ⬜ not set in production |

Also on the backend side:
- ⬜ Database roles and schema: run `scripts/db_bootstrap.py` and `alembic upgrade head` against production; never seed development data (`scripts/seed_dev.py`) there.
- ⬜ Services: the API (several instances), the API service gateway, Celery workers per queue, Celery Beat, the outbox relay; restart on failure (systemd).
- ⬜ Backups: continuous WAL archiving plus a daily full backup, encrypted, off-site, 30 days; a restore drill before launch and monthly after.
- ⬜ Flower and the RabbitMQ management page: not public (VPN or SSH tunnel only).

## 3. Frontend (formalieFrontend, the production build and its environment)

| Setting | Development | Production |
| --- | --- | --- |
| `NUXT_PUBLIC_API_MOCK` | `false` (mock off since 2026-10-12) | ⬜ `false`; the mock is never deployed |
| `NUXT_API_PROXY_TARGET` | `https://formalie.dev:5004` | ⬜ not used (Nginx sends `/api` to the API) |
| `NUXT_INTERNAL_TOKEN` | the backend's development value | ⬜ the same new value as the backend's `INTERNAL_TOKEN` |
| `NUXT_PUBLIC_ROOT_DOMAIN` | `formalie.dev` | ⬜ `formalie.com` |
| `NUXT_PUBLIC_FORMS_HOST` | `forms.formalie.dev` | ⬜ `forms.formalie.com` |
| `NUXT_PUBLIC_API_SERVICE_URL` | `https://api.formalie.dev` | ⬜ `https://api.formalie.com` |
| `NUXT_PUBLIC_LEGAL_*` | formalie.com pages | ⬜ check they exist |
| `NUXT_PAYONEER_WEBHOOK_SECRET` | empty | ⏸ Payoneer's webhook secret |
| `NODE_EXTRA_CA_CERTS`, `DEV_HTTPS_*` | mkcert | ⬜ not used |
| Dev port `:2202` | in every development address | ⬜ gone (443 through Nginx) |

Also:
- ⬜ Build with `pnpm build` and run the Nuxt server behind Nginx; public form pages are server-rendered.
- ⬜ The capture tools (`scripts/site-screenshots/`, `scripts/brand/`) are development only.
- ⬜ The brand images in `public/brand/` are served (emails load the Formalie mark from `https://manage.formalie.com/brand/…`).

## 4. Nginx and Cloudflare

- ⬜ Hosts: `*.formalie.com` and `manage.formalie.com` → Nuxt, with `/api/` → the API; `forms.formalie.com` → Nuxt; `api.formalie.com` → the API service gateway; `formalie.com`, `www` → the website.
- ⬜ Forward `X-Forwarded-Host`, `X-Forwarded-Proto` and the visitor's IP (`X-Forwarded-For`, or Cloudflare's `CF-Connecting-IP`).
- ⬜ HSTS, gzip / brotli, request size limits, the Content-Security-Policy from SECURITY-PROTOCOL (per-form `frame-ancestors` for embeds; Payoneer's frame hosts when connected).
- ⬜ Cloudflare: proxy on, SSL "Full (strict)", WAF and rate limiting rules, cache static assets only (never `/api`).

## 5. Sign-in providers (their consoles)

The production return addresses (backend README, "The addresses to register"):
- `https://manage.formalie.com/api/v1/auth/oauth/google/callback`
- `https://manage.formalie.com/api/v1/auth/oauth/microsoft/callback`
- `https://manage.formalie.com/api/v1/auth/oauth/facebook/callback`

- ⬜ **Google:** add the production address under Authorised redirect URIs; publish the app (out of Testing) and complete Google's verification of the consent screen.
- ⬜ **Microsoft:** add the production address under Authentication; publisher verification (Branding & properties → Add MPN ID, and the `.well-known/microsoft-identity-association.json` file on formalie.com); the `xms_edov` optional claim; renew the client secret before it expires (calendar reminder).
- ⬜ **Facebook:** add the production address under Valid OAuth Redirect URIs and `formalie.com` under App domains; switch the app to Live; complete Business verification if asked.
- ⬜ Remove development-only addresses you no longer need (the `:2202` ones can stay on a separate development app).

## 6. Email deliverability

- ⬜ SPF, DKIM and DMARC records for `formalie.com` (and for each workspace's own sending domain, B11).
- ⬜ Unsubscribe headers (`List-Unsubscribe`, `List-Unsubscribe-Post`) on optional emails, required by Gmail and Yahoo for bulk senders (being built).
- ⬜ Send a test of every template to Gmail, Outlook and Apple Mail and check the layout.

## 7. Website (formalieSite)

- ⬜ Production address `https://formalie.com` (the site's CLAUDE.md lists development as `https://formalie.dev:3033`).
- ⬜ Legal pages content from the platform admin; the links used by the portal and emails resolve.
- ⬜ Sign-up links go to `https://manage.formalie.com/auth/signup`.
- ⬜ The Microsoft `.well-known` file (section 5) and SEO settings (sitemap, robots, canonical addresses on `.com`).

## 8. Platform admin (formaliePlatformFront / formaliePlatformBack)

- ⬜ Their own production settings: `docs/04-HOSTING.md` in each project.
- ⬜ Database roles `platform_reader` / `platform_writer` in Formalie's production database (PLATFORM-ADMIN-INTEGRATION §5).
- ⬜ The internal admin API between the two systems with mTLS and HMAC keys made for production.

## 9. Last checks on launch day

- ⬜ No development value left: search the production environment files for `formalie.dev`, `:2202`, `:5004`, `CHANGE_ME`, `localhost`, `mailpit`.
- ⬜ Sign up, sign in with each provider, publish a form, submit a response, receive its email, export, on production.
- ⬜ Monitoring and alerts reach the team; backups ran once and a restore was tested.

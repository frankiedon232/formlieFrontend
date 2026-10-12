# Formalie API (formlyBackend)

The backend of Formalie. It replaces the mock API the finished frontend (`C:\UNETPROJECTS\formalieFrontend`) runs against today. Python 3.11, FastAPI, PostgreSQL 18, Redis, RabbitMQ, Celery.

- **Where the work stands:** [docs/PROGRESS.md](docs/PROGRESS.md) (phase by phase), [docs/BACKEND-ROADMAP.md](docs/BACKEND-ROADMAP.md), [docs/ENDPOINTS.md](docs/ENDPOINTS.md) (every endpoint, ticked when done).
- **Rules and design:** [CLAUDE.md](CLAUDE.md) and everything in [docs/](docs/).

---

## Every day: start, watch, stop

Everything runs **quietly in the background, no windows open**. From `C:\UNETPROJECTS\formlyBackend`, in PowerShell:

### Start: `scripts\dev-up.ps1`

| Command | Starts |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1` | **Everything:** the services, the API (https://formalie.dev:5004), the Celery worker, Celery Beat and Flower |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApi` | Everything **except the API**, when you prefer to run the API yourself in your terminal (see below) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-up.ps1 -NoApp` | **Services only** (Ubuntu with Redis, RabbitMQ, PgBouncer and Mailpit; PostgreSQL), no API and no workers |

What it does:
1. **Wakes Ubuntu (WSL)** and keeps it running in the background. Redis, RabbitMQ, PgBouncer and Mailpit start with Ubuntu; PostgreSQL starts with Windows.
2. **Checks every service answers.** If one doesn't, it says which and how to fix it.
3. **Starts the API, worker, Beat and Flower hidden**, writing their output to `logs\dev\{api,worker,beat,flower}.log`.

It's **safe to run again**: anything already running is left as it is. If port 5004 is already taken (an API you started yourself), it leaves it alone and says so.

### Watch the logs live: `scripts\dev-logs.ps1`

It runs in the terminal you start it from, with no other windows. Each line starts with where it came from (`api`, `worker`, `beat`, `flower`). It shows the last 20 lines first, then new lines as they happen. **Ctrl+C** stops watching; the services keep running.

| Command | Shows |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1` | **All:** API, worker, Beat and Flower together |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api` | Only the API (every request, one line each) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 worker` | Only the Celery worker (emails, request-log writes, events) |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api worker` | Any mix of `api`, `worker`, `beat`, `flower` |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 -Errors` | Only problems (ERROR, CRITICAL, tracebacks) from all of them |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1 api -Errors` | Only the API's problems |

### Stop: `scripts\dev-down.ps1`

| Command | Stops |
| --- | --- |
| `powershell -ExecutionPolicy Bypass -File scripts\dev-down.ps1` | The API (if dev-up started it), the worker, Beat, Flower, and the keep-alive. Ubuntu then stops on its own. **Data is never touched.** An API you started yourself is left alone (Ctrl+C it). |

### Running the API yourself instead

Use `dev-up.ps1 -NoApi`, then in your own terminal:

```powershell
uvicorn app.run:app --host 0.0.0.0 --port 5004 --no-proxy-headers --ssl-certfile C:\devcerts\formalie.pem --ssl-keyfile C:\devcerts\formalie-key.pem
```

or `fmly\Scripts\python.exe -m app.run`, which does the same with the host, port and certificates from `.env`. **`--no-proxy-headers` is required.** The API reads the forwarded headers itself, and only from trusted proxies; without the flag, workspaces are not found from their subdomain behind the Nuxt dev proxy.

### Every log there is

| Where | What |
| --- | --- |
| `scripts\dev-logs.ps1`, or `logs\dev\*.log` | The live output of the API, worker, Beat and Flower: one readable line per entry, with details after the message (`{name}.err.log` holds Python warnings and crashes) |
| `logs\{level}\{date}.log`, for example `logs\error\2026-10-11.log` | Everything, as JSON lines, per level and day, kept 90 days; also when you run the API yourself |
| The `formaly.request_logs` table | Every request in full: headers, body, response, real IP, location, device |
| The `formaly.audit_logs` table | Who did what: sign-ins (failed ones too), changes; in the app under Audit trail |
| The `formaly.error_logs` table | Every warning, error and critical line of every process, loaded from the files above every 30 seconds by Beat (search by `trace_id`). Critical ones are also emailed to `ALERT_EMAILS` |
| Flower, http://127.0.0.1:5555 | Every background task: what ran, how long it took, what failed |
| Mailpit, http://127.0.0.1:8025 | Every email the backend sent (sign-in codes and others) |

The console format is set with `LOG_CONSOLE_FORMAT` in `.env`: empty or `pretty` for readable lines, `json` for raw JSON.

If a service is down, `dev-up` says which one. To fix it:
- Redis, RabbitMQ, PgBouncer or Mailpit: in an Ubuntu window, `sudo systemctl restart redis-server rabbitmq-server pgbouncer mailpit`.
- PostgreSQL: in PowerShell as administrator, `Restart-Service postgresql-x64-18`.

The setup script `scripts/wsl/setup-services.sh` was a one-time install. Don't run it again unless you set up a new machine.

## Addresses

| What | Address | Sign in |
| --- | --- | --- |
| API | https://formalie.dev:5004 | |
| API docs (development only) | https://formalie.dev:5004/docs and /redoc | |
| Celery dashboard: Flower | http://127.0.0.1:5555 | none |
| RabbitMQ | http://127.0.0.1:15672 | user `formalie`, the password inside `RABBITMQ_URL` in `.env` (between `formalie:` and `@`) |
| Emails caught in development: Mailpit | http://127.0.0.1:8025 | none |
| Redis | the Redis Insight desktop app (redis.io/insight), connect to `127.0.0.1:6379` | none |
| Frontend | https://formalie.dev:2202 (run from the frontend project) | |

## Settings: `.env`

- `.env` holds the real values and passwords. The app reads only this file, and git never stores it.
- `.env.example` is the committed template with `CHANGE_ME` placeholders. Never put real passwords in it.
- A new setting goes into both: the real value in `.env`, a placeholder in `.env.example`.
- Secret keys (references, tokens): `fmly\Scripts\python.exe scripts\gen_keys.py --write` adds any missing ones to `.env` and keeps existing ones.
- Public form pages: `INTERNAL_TOKEN` (made by `gen_keys.py`) must have the same value as `NUXT_INTERNAL_TOKEN` in the frontend, so its server can read published forms through `/api/v1/internal/*`.

## Common commands

All from the project folder:

| What | Command |
| --- | --- |
| Run all tests | `fmly\Scripts\python.exe -m pytest` |
| Tests without the database | `fmly\Scripts\python.exe -m pytest -m "not db"` |
| Apply database migrations (development, then test) | `fmly\Scripts\alembic.exe upgrade head`, then `fmly\Scripts\alembic.exe -x db=test upgrade head` |
| Create roles and databases (new machine, or to change their passwords) | `fmly\Scripts\python.exe scripts\db_bootstrap.py` |
| Add the test workspaces and accounts (same as the frontend's mock; safe to repeat) | `fmly\Scripts\python.exe scripts\seed_dev.py` |
| Refresh the location databases (MaxMind; Beat also does it weekly) | `fmly\Scripts\python.exe scripts\geoip_update.py` |
| Load request logs that went to the fallback files | `fmly\Scripts\python.exe scripts\replay_request_logs.py` |
| Check the encryption against the frontend's own code | `fmly\Scripts\python.exe scripts\check_envelope_vectors.py` |
| Record the frontend's rules again after its `shared/` changed, then rebuild the catalogues | `fmly\Scripts\python.exe scripts\dump_frontend_rules.py`, `fmly\Scripts\python.exe scripts\dump_settings_rules.py`, `fmly\Scripts\python.exe scripts\dump_forms_rules.py`, `fmly\Scripts\python.exe scripts\dump_design_rules.py`, `fmly\Scripts\python.exe scripts\dump_templates_rules.py`, `fmly\Scripts\python.exe scripts\dump_links_rules.py`, `fmly\Scripts\python.exe scripts\dump_submission_rules.py`, `fmly\Scripts\python.exe scripts\dump_public_rules.py`, `fmly\Scripts\python.exe scripts\dump_responses_rules.py`, `fmly\Scripts\python.exe scripts\dump_report_rules.py`, `fmly\Scripts\python.exe scripts\dump_datasource_rules.py`, `fmly\Scripts\python.exe scripts\dump_table_rules.py`, then `fmly\Scripts\python.exe scripts\gen_frontend_catalogues.py` |
| Copy the frontend's data files again (email templates, template text in 20 languages, sample list translations) | `fmly\Scripts\python.exe scripts\sync_frontend_data.py` |
| Tidy an autogenerated migration (keep only the new tables, add RLS) | `fmly\Scripts\python.exe scripts\tidy_migration.py alembic\versions\00NN_name.py table_a table_b` |
| Make the "customer" PostgreSQL databases that data source tests connect to (role `formalie_customer`, databases `customer_dev` and `customer_test`; writes `TEST_POSTGRES_URL` and `DATASOURCES_ALLOW_LOCAL=true` into `.env`, prints no password) | `fmly\Scripts\python.exe scripts\setup_customer_pg.py` |
| Install MariaDB in Ubuntu for the MySQL / MariaDB data source tests (asks for the Ubuntu password; prints the `TEST_MYSQL_URL` line to paste into `.env`) | In Ubuntu: `bash /mnt/c/UNETPROJECTS/formlyBackend/scripts/wsl/setup-mariadb.sh` |
| Rebuild error codes after the frontend added some | `fmly\Scripts\python.exe scripts\gen_error_codes.py` |
| Install packages (new machine) | `fmly\Scripts\python.exe -m pip install -r requirements-dev.txt` |

## Test workspaces and accounts (development)

`scripts/seed_dev.py` creates the same ones as the frontend's mock, with the mock's sample departments and job titles in Remedy Legal and Samath Tax, and Formalie's sample lists (Priority, Departments, Days of the week, Satisfaction, Places, Sample products) in every seeded workspace:
- **Workspaces:** `remedylegal` (Business plan), `samathtax` (Starter), `oldco` (suspended) and `formalie-team` (Formalie's own).
- **Accounts:** `admin@remedylegal.test` (owner), `admin@samathtax.test` (owner) and `james.carter@carterpartners.test` (a member of both, for "find my workspace").
- **Password:** the mock's test password, `MOCK_PASSWORD` in the frontend's `server/mock/data/tenants.ts`.
- **Sign-in codes:** they arrive in Mailpit (http://127.0.0.1:8025).

## Social sign-in (Google, Microsoft, Facebook)

People can sign up and sign in with Google, Microsoft or Facebook. Each provider needs an "app" registered on its developer site, which gives a **client ID** and a **client secret**. Those two values go in `.env`. This section is the full setup, step by step, for development and for going live.

### How it works (read once)

- Every provider sends people back to **one address on `manage.`**: `…/api/v1/auth/oauth/{provider}/callback`. Providers don't accept wildcard subdomains, so workspaces (`remedylegal.formalie.com` and so on) never need registering: the API sends people on to the page they started from.
- **Sign-up** with a provider skips the email code (the provider checked the address) and goes straight to naming the workspace.
- **Sign-in** on a workspace works only for someone who already has an account there with the same email, and it still asks for the 6-digit code.
- **Starter plan** has no social sign-in for new people, but anyone who came in with a provider (for example the Owner who signed up with it) keeps using it, with no password.
- A provider whose keys are empty in `.env` shows "not available yet" on its button. Nothing breaks.

### The addresses to register (copy exactly)

| Provider | Development | Production |
| --- | --- | --- |
| Google | `https://manage.formalie.dev:2202/api/v1/auth/oauth/google/callback` | `https://manage.formalie.com/api/v1/auth/oauth/google/callback` |
| Microsoft | `https://manage.formalie.dev:2202/api/v1/auth/oauth/microsoft/callback` | `https://manage.formalie.com/api/v1/auth/oauth/microsoft/callback` |
| Facebook | `https://manage.formalie.dev:2202/api/v1/auth/oauth/facebook/callback` | `https://manage.formalie.com/api/v1/auth/oauth/facebook/callback` |

Register **both** lines with each provider (one app can hold several addresses), so the same app works on your machine and live. The address must match character for character: `https`, no slash at the end, the port `:2202` only in development.

**Register only these addresses.** Never register the API's own address (`https://formalie.dev:5004/…`): people's browsers always come back through `manage.` (the portal on `:2202` in development), never to the API directly, so a `:5004` address is never used. An unused address at a provider is only a risk, so remove it if one was added (owner, 2026-10-12: removed from the Microsoft app).

The API builds this address from `ROOT_DOMAIN` (`formalie.dev` in development, `formalie.com` in production) and the port the browser used. If it ever has to be different, set `OAUTH_REDIRECT_BASE` in `.env` (for example `OAUTH_REDIRECT_BASE=https://manage.formalie.com`) and register the matching address.

### Google

Site: https://console.cloud.google.com (sign in with the Google account that will own Formalie's apps).

1. **Project.** Top bar → project picker → **New project** → name `Formalie` → **Create**, then select it.
2. **Consent screen.** Menu → **APIs & Services** → **OAuth consent screen** (newer screens call it **Google Auth Platform** → **Branding**).
   - User type: **External** → **Create**.
   - App name `Formalie`, user support email: yours, app logo (optional; a logo means Google reviews the app before it can go live).
   - **App domain**: home page `https://formalie.com`, privacy policy `https://formalie.com/privacy`, terms `https://formalie.com/terms`.
   - **Authorised domains**: add `formalie.com` (Google asks you to prove you own it: see step 6).
   - Developer contact email: yours → **Save and continue**.
3. **Scopes** (Data access): **Add or remove scopes** → tick `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile` → **Update** → **Save and continue**. These three are "non-sensitive": no review needed for them.
4. **Test users** (Audience): while the app is in **Testing**, only the addresses listed here can sign in. Add your own Gmail address (and anyone helping you test).
5. **Client ID.** **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
   - Application type: **Web application**, name `Formalie web`.
   - **Authorised JavaScript origins**: leave empty (not needed).
   - **Authorised redirect URIs** → **Add URI**: the two Google addresses from the table above.
   - **Create**. Copy the **Client ID** (ends in `.apps.googleusercontent.com`) and the **Client secret** (starts with `GOCSPX-`).
6. **Prove you own formalie.com** (needed to publish): open https://search.google.com/search-console → **Add property** → **Domain** → `formalie.com` → Google shows a `TXT` record. In Cloudflare: **formalie.com** → **DNS** → **Records** → **Add record** → Type `TXT`, Name `@`, Content: the value Google gave → **Save**. Back in Search Console → **Verify** (can take a few minutes).
7. **Going live**: OAuth consent screen (Audience) → **Publish app** → **In production**. With only the three basic scopes Google publishes at once (unless you added a logo, then it reviews branding, usually a few days). Until then only the test users from step 4 can sign in.

### Microsoft

Site: https://entra.microsoft.com (or https://portal.azure.com → **Microsoft Entra ID**). Use a work account of the organisation that owns Formalie.

1. **Register the app.** **Applications** → **App registrations** → **New registration**.
   - Name `Formalie`.
   - **Supported account types**: **Accounts in any organizational directory and personal Microsoft accounts** (the third option). This must be the one: Formalie signs people in through the `common` address, which serves both work and personal accounts. Any other choice fails at sign-in.
   - **Redirect URI**: platform **Web**, then the development Microsoft address from the table → **Register**.
2. **Copy the client ID**: on the app's **Overview**, **Application (client) ID** (36 characters, like `1a2b3c4d-…`). This is `OAUTH_MICROSOFT_CLIENT_ID`. (The "Directory (tenant) ID" is not needed.) **Careful:** the **Secret ID** on the Certificates & secrets page looks the same (also 36 characters) but is **not** the client ID. Putting it here gives `AADSTS700016` (found 2026-10-12).
3. **Add the production address**: **Authentication** → under **Web**, **Redirect URIs** → **Add URI** → the production Microsoft address → **Save**. Leave "Access tokens" and "ID tokens" (implicit grant) **unticked**: Formalie uses the safer code flow.
4. **Client secret**: **Certificates & secrets** → **Client secrets** → **New client secret** → description `Formalie API`, expires **24 months** → **Add**. Copy the **Value** column at once (it's shown only this one time; the "Secret ID" next to it is not the secret). This is `OAUTH_MICROSOFT_CLIENT_SECRET`.
   - **Put a reminder in your calendar** one month before it expires: make a new secret, put it in `.env`, restart the API, then delete the old one. When a secret expires, Microsoft sign-in stops working.
5. **Permissions**: **API permissions**. `Microsoft Graph` → `User.Read` is there by default. **Add a permission** → **Microsoft Graph** → **Delegated permissions** → tick `openid`, `email`, `profile` → **Add permissions**. No admin consent is needed for these.
6. **Work accounts' email (important)**: a company directory can type in any email for its people without checking it, so Formalie only trusts a work account's email when Microsoft says the domain was checked. Turn that on: **Token configuration** → **Add optional claim** → token type **ID** → tick `xms_edov` → **Add**. Personal accounts (outlook.com, hotmail.com, live.com) work without it. Without this step, people with work accounts get `FRM-AUTH-1021`.
7. **Publisher verification (recommended before going live)**: **Branding & properties**.
   - **Home page URL** `https://formalie.com`, **Terms of service** `https://formalie.com/terms`, **Privacy statement** `https://formalie.com/privacy`.
   - **Publisher domain** → **Verify a new domain** → `formalie.com`. Microsoft gives a small JSON file; it must be served at `https://formalie.com/.well-known/microsoft-identity-association.json`. Put that file in the coming-soon site on Cloudflare (Pages: add the folder `.well-known` with the file, deploy), open the address in a browser to check it shows, then **Verify and save**.
   - Optionally verify the publisher (a Microsoft Partner Network account), which shows a blue badge on the consent screen instead of "unverified".

### Facebook

Site: https://developers.facebook.com (log in with the Facebook account that will own the app; it becomes a developer account the first time).

1. **Create the app.** **My Apps** → **Create app**.
   - Use case: **Authenticate and request data from users with Facebook Login** → **Next**.
   - Business portfolio: choose one, or "I don't want to connect a business portfolio yet" → **Next**.
   - App name `Formalie`, contact email: yours → **Create app**.
2. **Copy the keys**: **App settings** → **Basic**. **App ID** (digits) is `OAUTH_FACEBOOK_CLIENT_ID`; **App secret** → **Show** (asks your Facebook password) is `OAUTH_FACEBOOK_CLIENT_SECRET`.
3. **Basic settings, same page**:
   - **App domains**: `formalie.com` (and `formalie.dev` for development).
   - **Privacy policy URL** `https://formalie.com/privacy`, **Terms of service URL** `https://formalie.com/terms`.
   - **User data deletion**: choose "Data deletion instructions URL" → `https://formalie.com/privacy` (a page that says how people ask for their data to be deleted).
   - **App icon** (1024 × 1024) and **Category** (Business and pages) → **Save changes**.
4. **Facebook Login settings**: **Use cases** → **Authenticate and request data…** → **Customise** → **Settings** (or **Facebook Login** → **Settings** on older screens).
   - **Client OAuth login**: Yes. **Web OAuth login**: Yes. **Enforce HTTPS**: Yes. **Use strict mode for redirect URIs**: Yes.
   - **Valid OAuth Redirect URIs**: the two Facebook addresses from the table → **Save changes**.
5. **Permissions**: in the same use case → **Permissions**: `public_profile` is there; **Add** `email`. Formalie needs both (no email, no sign-in: `FRM-AUTH-1021`).
6. **Testing**: while the app is in **Development** mode only people with a role on the app can log in. **App roles** → **Roles** → **Add people** → Testers or Developers.
7. **Going live**: top of the dashboard, switch **App mode** from **Development** to **Live** (it asks for the privacy URL and category from step 3). For `email` to work for everyone, Meta may ask for **Business verification** (your company documents) and for `email` to have **Advanced access** (**App review** → **Permissions and features** → `email` → **Request advanced access**). Do this a few weeks before launch: reviews take days.

### Put the keys in `.env`

Open `C:\UNETPROJECTS\formlyBackend\.env` in an editor (never paste keys into a chat, a ticket or git) and fill in, with no quotes and no spaces around `=`:

```
OAUTH_GOOGLE_CLIENT_ID=<Client ID from Google step 5>
OAUTH_GOOGLE_CLIENT_SECRET=<Client secret from Google step 5>
OAUTH_MICROSOFT_CLIENT_ID=<Application (client) ID from Microsoft step 2>
OAUTH_MICROSOFT_CLIENT_SECRET=<secret Value from Microsoft step 4>
OAUTH_FACEBOOK_CLIENT_ID=<App ID from Facebook step 2>
OAUTH_FACEBOOK_CLIENT_SECRET=<App secret from Facebook step 2>
```

Then **restart the API** (stop it with Ctrl+C and start it again): keys are read only when it starts. On the live server, put the same lines in its environment (or secret manager) and set `ROOT_DOMAIN=formalie.com`.

Check what is filled in without showing any secret (prints only the length):

```bash
for k in OAUTH_GOOGLE_CLIENT_ID OAUTH_GOOGLE_CLIENT_SECRET OAUTH_MICROSOFT_CLIENT_ID OAUTH_MICROSOFT_CLIENT_SECRET OAUTH_FACEBOOK_CLIENT_ID OAUTH_FACEBOOK_CLIENT_SECRET; do v=$(grep -E "^$k=" .env | cut -d= -f2-); echo "$k: ${#v} characters"; done
```

Usual lengths: Google ID about 72, Google secret 35, Microsoft ID 36, Microsoft secret about 40, Facebook ID 15 or 16, Facebook secret 32. Zero means it's missing.

### Try it

1. Start the API, the frontend and the Celery worker as usual.
2. **Sign-up**: open https://manage.formalie.dev:2202/auth/signup → **Continue with Google** (or Microsoft, Facebook) → choose your account → you come back and name a new workspace.
3. **Sign-in on an existing workspace**: the test accounts use `.test` addresses, so first add your own address to Remedy Legal as an Admin, with all three buttons switched on:
   ```
   fmly\Scripts\python.exe scripts\seed_dev.py --person you@gmail.com
   ```
   Then open https://remedylegal.formalie.dev:2202/auth/login → the provider's button → the 6-digit code arrives in Mailpit (http://127.0.0.1:8025).

### When it doesn't work

| What you see | Why | Fix |
| --- | --- | --- |
| Button says "not available yet" | Keys empty, or the API wasn't restarted | Fill in `.env`, restart the API |
| Google: `Error 400: redirect_uri_mismatch` | The address registered differs | Copy the address from the table exactly (port, `https`, no end slash) into **Authorised redirect URIs** |
| Google: "Access blocked: this app's request is invalid" or "has not completed the Google verification process" | You aren't a test user while the app is in Testing | Add the address under **Test users**, or publish the app |
| Microsoft: `AADSTS50011` | Redirect address not registered | Add it under **Authentication** → **Web** |
| Microsoft: `AADSTS50194` or "not configured as a multi-tenant application" | Wrong supported account type | **Authentication** (or **Manifest**): set to "any organizational directory and personal Microsoft accounts" |
| Microsoft: `AADSTS700016` "Application with identifier '…' was not found in the directory" | `OAUTH_MICROSOFT_CLIENT_ID` isn't the app's ID: often the **Secret ID** from Certificates & secrets was copied | Copy **Overview** → **Application (client) ID** into `.env`, restart the API |
| Microsoft: `unauthorized_client` "The client does not exist or is not enabled for consumers" | A wrong client ID (as above), or supported account types without personal accounts | Check the client ID first, then **Authentication** → **Supported accounts**: "Any Entra ID Tenant + Personal Microsoft accounts" |
| Microsoft: a work account from another company can't approve the app ("needs admin approval" / unverified publisher) | Multi-tenant apps without a verified publisher can't be approved by other companies' people | Testing: use your own organisation's or a personal account. Before launch: step 7 (publisher verification) |
| Microsoft: `AADSTS7000215` / `AADSTS7000222` | Wrong or expired secret (the Secret ID was copied instead of the Value?) | Make a new secret, copy its **Value**, restart |
| Facebook: "URL blocked" / "Can't load URL" | Redirect address or app domain missing | Facebook step 3 and 4 |
| Facebook: "App not active" / "feature unavailable" | App in Development and you have no role | Add yourself under **App roles**, or switch the app to Live |
| `FRM-AUTH-1021` "didn't share a verified email address" | Facebook without `email`, Microsoft work account without `xms_edov`, or an unverified Google address | Facebook step 5, Microsoft step 6 |
| `FRM-AUTH-1022` "no account with this email" | Sign-in on a workspace where this email has no account | Use sign-up, or invite the person first (or `seed_dev.py --person` in development) |
| `FRM-AUTH-1008` "method not enabled" | The workspace switched this button off, or its plan has no social sign-in for new people | Settings → Security → sign-in methods, or the plan |
| `FRM-AUTH-1023` "didn't finish" | The provider refused the code (secret wrong, clock far off, took too long) | Check the secret, try again; the API's log has the provider's reply |

### Keep in mind

- **Secrets expire or leak**: Microsoft secrets expire (step 4 reminder). If any secret was ever shown somewhere it shouldn't be, make a new one at the provider, put it in `.env`, restart, and delete the old one.
- **One set of apps** serves development and production (both addresses registered). If you prefer separate apps for development, make a second app at each provider and use its keys only on your machine.
- **The legal pages** `https://formalie.com/privacy` and `https://formalie.com/terms` must exist (not the coming-soon page) before Google, Microsoft and Facebook let the apps go live for everyone.

## How the pieces fit

- **PostgreSQL 18** (Windows, port 5432): databases `formalie` (development) and `formalie_test` (tests). Workspace tables live in the `formaly` schema, global tables in `platform`. Every workspace table has row-level security forced. Nothing is ever hard deleted.
- **Redis** (Ubuntu, 6379): cache, rate limits and secure-channel keys. If it goes down, the API keeps working: it falls back and logs the outage once.
- **RabbitMQ** (Ubuntu, 5672): Celery jobs and the `formalie.events` exchange, fed by the event outbox.
- **Celery** (Windows, `--pool=solo`): worker queues `scheduled` (outbox relay, partitions, GeoIP refresh, error log loading), `logs` (request log), `notifications` (emails), `exports` (export files) and `destinations` (connection tests, health checks every 5 minutes, writing responses to customers' databases, retries and backfills every 30 seconds), plus Beat for the timers.
- **Customers' databases** (data sources): reached with asyncpg (PostgreSQL), aiomysql (MySQL, MariaDB), pymssql (SQL Server) and oracledb (Oracle), through an SSH tunnel (asyncssh) when a connection has one. Private and local addresses are refused unless `DATASOURCES_ALLOW_LOCAL=true` (development only; never in production).
- **Stored files** (uploads such as logos, and exports): `data/storage/tenants/{workspace}/orgs/{organisation}/{module}/{id}` (not in git). Object storage replaces the folder before going live (to choose: see PROGRESS, open questions).
- **Request log** (`formaly.request_logs`): every request in full (headers, body, response, real IP, location, device), with secrets masked.
- **Mailpit** (Ubuntu, 8025): catches every email in development, such as sign-in codes, so nothing is really sent.
- **MaxMind GeoLite2** (`data/geoip/`, not in git): locations for the request log.

## Setting up a new machine

The full steps are in [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md):
1. Install the packages into the `fmly` venv.
2. Copy `.env.example` to `.env`, fill in the passwords, and run `gen_keys.py --write`.
3. Run `db_bootstrap.py` and the migrations.
4. Install Ubuntu in WSL with mirrored networking, and run `scripts/wsl/setup-services.sh` once.
5. Run `geoip_update.py`.
6. Run `dev-up.ps1`.

## Resuming work with Claude Code

Start a new session in this folder with:

```
Read CLAUDE.md and docs/BACKEND-ROADMAP.md. Tell me which phase we are on
and what is left in it, then continue from there.
```

`docs/PROGRESS.md` holds the details: what's done, what's next, and any open questions.

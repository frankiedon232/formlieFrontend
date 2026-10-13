# Deployment guide (step by step)

How to put Formalie live, and how to ship every later release. Written for the owner on 2026-10-12; it is the "how", and [`PRODUCTION-CHECKLIST.md`](PRODUCTION-CHECKLIST.md) is the "what" (every setting and its production value). Do both together: this guide tells you when to fill in each part of the checklist.

This file is shared and identical in all five projects: formalieFrontend, formlyBackend, formalieSite, formaliePlatformFront and formaliePlatformBack. Change it in one, copy it to the others.

Marks: ⬜ to do · ✅ done · ⏸ waiting. Tick a step only once it is done on the real servers.

**Before you start, ask Claude to walk you through it.** The steps marked **(after B17)** depend on switch-over work that is still open in B17 (object storage, how workspaces' own domains are added). Built on 2026-10-12: the portal's static build with every page client-rendered, its Cloudflare Worker (`/api/*` proxied from every portal host to `services.formalie.com` with the edge secret, form link previews, `/s/` short links) and the release check (`pnpm release:check`); the API trusts the Worker's forwarded headers only with that secret. Claude goes through this guide with you, line by line.

---

## The picture

```
                         Cloudflare (DNS, TLS, WAF, cache)
                                       |
     +---------------------------------+------------------------------------+
     | static files, no server (Workers with static assets)                 |  proxied to our servers
     |                                                                      |
  *.formalie.com, manage., forms.   formalie.com, www     platform admin    services.formalie.com  api.formalie.com
  portal + form pages               website                host              Formalie API (/api/v1) API service gateway
  (+ Worker: /api/* proxied to                                                         |                |
   services. with the edge secret,                                                     +---- Nginx -----+
   form previews, /s/ short links)
                                                                                              |
                                          API (uvicorn) · gateway (uvicorn) · Celery workers + Beat · platform consumer
                                                                                              |
                                          PostgreSQL 18 (primary + replica) · PgBouncer · Redis 7 · RabbitMQ 3 · file storage
```

- **Static on Cloudflare:** the portal (formalieFrontend), the website (formalieSite), the platform admin (formaliePlatformFront). No Node server anywhere.
- **One origin for the browser:** on every portal host (`*.formalie.com`, `manage.`, `forms.`, workspaces' own domains) the portal's Worker answers `/api/*` itself and forwards it to `services.formalie.com` with `X-Formalie-Edge` (the shared secret `EDGE_SECRET`) and `X-Forwarded-Host / -Proto / -For`. No CORS, the cookies stay per workspace host, sign-in return addresses stay on `manage.formalie.com`.
- **On our servers (no Docker):** the Formalie API on `services.formalie.com`, the API service gateway on `api.formalie.com`, the background workers, the databases. The platform admin's own backend (formaliePlatformBack) on its own servers ([its 04-HOSTING](../../formaliePlatformBack/docs/04-HOSTING.md)).
- **Order of the first launch:** accounts (Part 1) → servers (Part 2) → databases (Part 3) → backend (Part 4, 5) → Nginx (Part 6) → Cloudflare (Part 7) → front ends (Part 8) → outside services (Part 9) → platform admin (Part 10) → checks (Part 11). Later releases: Part 12.

---

## Part 1. Accounts and decisions (once)

- ⬜ **Cloudflare:** an account with `formalie.com` added as a zone (the registrar's name servers changed to Cloudflare's). Plan: Free works to start; Pro adds better WAF rules. Workers: the free plan allows 100,000 requests a day, Workers Paid ($5 a month) removes that limit; take Paid before launch.
- ⬜ **Hosting for the back ends:** AWS or dedicated servers (Part 2 lists both). Pick one region close to most customers.
- ⬜ **Email:** Amazon SES (or another SMTP relay), production access requested (SES starts in a sandbox that only sends to verified addresses; asking to leave it takes about a day).
- ⬜ **Google** and **Facebook** developer apps for sign-in (already made for development; Part 9).
- ⬜ **Anthropic:** a production API key and spending limits (console.anthropic.com).
- ⬜ **MaxMind GeoLite2:** account ID and licence key.
- ⏸ **Payoneer** (payments, F24/B15) and an **SMS provider** when ready.
- ⬜ **A password manager** for the team (every key below goes there, never into chat, email or the repository).
- ⬜ **The edge secret:** make one long random value now (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) and keep it in the password manager. It goes into the backend's `.env` as `EDGE_SECRET` (Part 4) and into the portal's Worker as its secret `EDGE_SECRET` (Part 8a). Both must always hold the same value.
- ⬜ **GitHub:** the production servers pull releases with a read-only deploy key (one per server), never your own account.

## Part 2. Servers (once)

Suggested start; grow by adding API and worker machines.

| Machine | Runs | Size to start |
| --- | --- | --- |
| **app-1** | Nginx, the API, the gateway, PgBouncer | 4 vCPU, 8 GB |
| **worker-1** | Celery workers, Celery Beat (exactly one in total), the platform consumer | 4 vCPU, 8 GB |
| **db-1** | PostgreSQL 18 primary, Redis 7, RabbitMQ 3 | 4 vCPU, 16 GB, fast SSD |
| **db-2** | PostgreSQL 18 replica (streaming replication) | same as db-1 |

On AWS: EC2 for app and worker, Amazon RDS for PostgreSQL (Multi-AZ, one read replica), ElastiCache for Redis, Amazon MQ for RabbitMQ, all in one VPC with private subnets; only Nginx (or a load balancer) is reachable from the internet.

On each server:

1. ⬜ Install **Ubuntu 24.04 LTS**. SSH keys only (`PasswordAuthentication no`, `PermitRootLogin no`), `unattended-upgrades` on, `fail2ban` on.
2. ⬜ Firewall (`ufw`): app-1 opens 443 to **Cloudflare's IP ranges only** (cloudflare.com/ips) plus SSH from your own address; every other port only between your own servers (private network).
3. ⬜ Set the time zone to UTC and turn on time sync (`timedatectl set-timezone UTC`).
4. ⬜ Create a service user: `sudo adduser --system --group --home /srv/formalie formalie`.
5. ⬜ Packages:
   - app-1 and worker-1: `python3.11 python3.11-venv` (from the deadsnakes PPA on 24.04), `git`, `nginx` (app-1), `pgbouncer` (app-1), `libxmlsec1-dev libxmlsec1-openssl pkg-config` (single sign-on with SAML needs it).
   - db-1 / db-2: PostgreSQL 18 from the PGDG apt repository (apt.postgresql.org), `redis-server` 7, `rabbitmq-server` 3 (from the RabbitMQ apt repository).

## Part 3. Databases and services on db-1 / db-2 (once)

1. ⬜ **PostgreSQL:** listen on the private address only (`listen_addresses`), `pg_hba.conf` allows app-1 and worker-1 with `scram-sha-256`, TLS on. Set a strong password for `postgres`.
2. ⬜ **Replica on db-2:** streaming replication from db-1 (`pg_basebackup -R`), read only. The platform admin reads from here only.
3. ⬜ **Redis:** bind to the private address, `requirepass` set, `maxmemory` and `maxmemory-policy allkeys-lru`.
4. ⬜ **RabbitMQ:** remove the `guest` user; add the user `formalie` with a strong password and its own vhost; a separate user for the platform admin (PRODUCTION-CHECKLIST section 8). The management page stays private (SSH tunnel only).
5. ⬜ **PgBouncer** on app-1: transaction pooling in front of db-1; set `DB_PGBOUNCER=true` in the backend's `.env`.
6. ⬜ **Backups:** pgBackRest (or WAL archiving plus a nightly base backup), encrypted, to off-site storage, kept 30 days. Do one **restore drill** before launch.

## Part 4. Backend first install (app-1 and worker-1)

1. ⬜ Get the code (as the `formalie` user):
   ```bash
   cd /srv/formalie && mkdir -p releases shared/data shared/logs
   git clone --branch formalieBackend --depth 1 git@github.com:frankiedon232/formlieFrontend.git releases/2026-xx-xx
   ln -sfn /srv/formalie/releases/2026-xx-xx /srv/formalie/current
   ```
2. ⬜ Python environment: `cd /srv/formalie/current && python3.11 -m venv fmly && fmly/bin/pip install -r requirements.txt` (never `requirements-dev.txt` in production). Check SAML: `fmly/bin/python -c "import xmlsec"`.
3. ⬜ **Settings:** create `/srv/formalie/shared/.env` (owner `formalie`, `chmod 600`) and link it: `ln -s /srv/formalie/shared/.env .env`. Fill in **every row of PRODUCTION-CHECKLIST section 2**. At least:
   - `APP_ENV=production`, `DOCS_ENABLED=false`, `ROOT_DOMAIN=formalie.com`, `TRUSTED_PROXIES` = app-1's Nginx address (`127.0.0.1/32`, Nginx on the same machine).
   - `EDGE_SECRET` = the edge secret from Part 1, `SERVICES_HOST=services.formalie.com`.
   - The database, Redis and RabbitMQ addresses with their real passwords.
   - `INTERNAL_TOKEN` stays **empty** (retired: the frontend no longer has a server; it only guards the old server-rendered reads `/api/v1/internal/public-forms/{key}` and `/api/v1/internal/short/{code}`, which then refuse everything).
   - Fresh keys: `fmly/bin/python scripts/gen_keys.py --write` **on the server** (never copy development keys).
   - Email (SES), Google, Facebook, Anthropic, MaxMind, the platform admin keys, `SUPPORT_EMAIL`, `SUPPORT_URL`, `EMAIL_ASSETS_URL=https://manage.formalie.com`.
   - `STORAGE_DIR=/srv/formalie/shared/data/storage` on a disk both app-1 and worker-1 reach (a shared volume), until object storage (S3) is added in B17.
   - `LOG_DIR=/srv/formalie/shared/logs`, `ALERT_EMAILS` = your address.
4. ⬜ Create roles and the database: `fmly/bin/python scripts/db_bootstrap.py` (uses `DB_SUPERUSER_URL` once; afterwards remove that line from `.env`).
   - (B17) Set `DB_ADMIN_API_URL` first: the bootstrap creates `formalie_admin_api`, the only role allowed to run the platform admin functions, and must run before `alembic upgrade head` reaches migration 0036 (if it runs after, it applies the same grants itself).
5. ⬜ Build the schema: `fmly/bin/alembic upgrade head`. The migrations also fill the global tables (plans, email templates, templates, themes, help centre). **Never run `scripts/seed_dev.py` in production.**
6. ⬜ Request locations: `fmly/bin/python scripts/geoip_update.py` once (Beat refreshes it weekly).

## Part 5. Backend services (systemd)

One unit per process, all `User=formalie`, `WorkingDirectory=/srv/formalie/current`, `EnvironmentFile=/srv/formalie/shared/.env`, `Restart=always`. Example, `/etc/systemd/system/formalie-api.service`:

```ini
[Unit]
Description=Formalie API
After=network-online.target

[Service]
User=formalie
WorkingDirectory=/srv/formalie/current
EnvironmentFile=/srv/formalie/shared/.env
ExecStart=/srv/formalie/current/fmly/bin/uvicorn app.run:app --host 127.0.0.1 --port 5004 --workers 4 --no-proxy-headers
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

| Unit | Machine | `ExecStart` (after `/srv/formalie/current/fmly/bin/`) |
| --- | --- | --- |
| ⬜ `formalie-api` | app-1 | `uvicorn app.run:app --host 127.0.0.1 --port 5004 --workers 4 --no-proxy-headers` |
| ⬜ `formalie-gateway` | app-1 | `uvicorn app.gateway:app --host 127.0.0.1 --port 5005 --workers 2 --no-proxy-headers` |
| ⬜ `formalie-worker-fast` | worker-1 | `celery -A app.workers.celery_app worker -Q scheduled,logs,notifications -n fast@%h -c 4 -l info` |
| ⬜ `formalie-worker-jobs` | worker-1 | `celery -A app.workers.celery_app worker -Q exports,destinations,webhooks -n jobs@%h -c 4 -l info` |
| ⬜ `formalie-beat` | worker-1, **one in total** | `celery -A app.workers.celery_app beat -l info --schedule /srv/formalie/shared/data/celerybeat-schedule` |
| ⬜ `formalie-platform-consumer` | worker-1 | `python -m app.modules.platform_bridge.consumer` |

`--no-proxy-headers` is required: the app reads `X-Forwarded-*` itself, only from `TRUSTED_PROXIES` and, for the forwarded host, only with the Worker's edge secret. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now formalie-api formalie-gateway
sudo systemctl enable --now formalie-worker-fast formalie-worker-jobs formalie-beat formalie-platform-consumer
```

Check: `systemctl status formalie-*` all "active (running)"; `journalctl -u formalie-api -n 50` without errors; `curl -s http://127.0.0.1:5004/api/v1/health` answers.

## Part 6. Nginx on app-1

1. ⬜ **Certificate:** in Cloudflare, SSL/TLS → Origin Server → Create certificate for `formalie.com, *.formalie.com` (15 years). Save it as `/etc/ssl/formalie/origin.pem` and `origin-key.pem` (`chmod 600` on the key).
2. ⬜ **Real visitor addresses (security review M14).** How the app takes the visitor's address (`app/core/middleware/request_context.py`):
   - With the right `X-Formalie-Edge` (a call the Worker forwarded): the first address in `X-Forwarded-For`, which the Worker sets to the visitor's `CF-Connecting-IP`.
   - Otherwise, only when the TCP peer is in `TRUSTED_PROXIES` (Nginx on `127.0.0.1`): `CF-Connecting-IP` first, else `X-Forwarded-For` read right to left (the first address that is not a trusted proxy).
   - Otherwise the TCP peer itself. The forwarded host (`X-Forwarded-Host`) counts only with the edge secret while `EDGE_SECRET` is set; `X-Forwarded-Proto` with the secret or from a trusted proxy.
   - Cloudflare's location headers (`CF-IPCountry` and the other `CF-IP*`, `CF-Region*`, `CF-Postal-Code`, `CF-Timezone`) fill the request log's location when MaxMind has no answer, again only from a trusted proxy (`app/core/logging/geo.py`).

   Nginx is always the trusted peer, so the app believes `CF-Connecting-IP` and the `CF-*` location headers exactly as Nginx hands them over. Nginx must therefore never pass on what a caller wrote itself: anything that reaches app-1 without going through Cloudflare (a firewall gap, another route to the origin) could otherwise claim any address or country and get round rate limits, access rules and the audit trail. Put this in `/etc/nginx/conf.d/cloudflare.conf` (http level), with Cloudflare's current ranges from cloudflare.com/ips (IPv4 and IPv6) in both lists:
   ```nginx
   # Visitor address: believe CF-Connecting-IP only from Cloudflare's own addresses.
   set_real_ip_from 173.245.48.0/20;     # ... one line per Cloudflare range
   real_ip_header CF-Connecting-IP;

   # 1 when the TCP peer (before real_ip) is Cloudflare. The same ranges again.
   geo $realip_remote_addr $from_cloudflare {
     default 0;
     173.245.48.0/20 1;                  # ... one line per Cloudflare range
   }
   # Cloudflare's location headers pass only when the peer is Cloudflare; "" removes the header.
   map $from_cloudflare $cf_ipcountry   { 1 $http_cf_ipcountry;   default ""; }
   map $from_cloudflare $cf_ipcontinent { 1 $http_cf_ipcontinent; default ""; }
   map $from_cloudflare $cf_ipcity      { 1 $http_cf_ipcity;      default ""; }
   map $from_cloudflare $cf_region      { 1 $http_cf_region;      default ""; }
   map $from_cloudflare $cf_region_code { 1 $http_cf_region_code; default ""; }
   map $from_cloudflare $cf_postal_code { 1 $http_cf_postal_code; default ""; }
   map $from_cloudflare $cf_timezone    { 1 $http_cf_timezone;    default ""; }
   map $from_cloudflare $cf_iplatitude  { 1 $http_cf_iplatitude;  default ""; }
   map $from_cloudflare $cf_iplongitude { 1 $http_cf_iplongitude; default ""; }
   ```
   And a snippet `/etc/nginx/snippets/formalie-public.conf` that every proxied `location` of the public server blocks includes (through the two snippets in step 3; a `location` that sets any `proxy_set_header` of its own inherits none from its `server`, so it goes inside each `location`):
   ```nginx
   # After real_ip, $remote_addr is the visitor when the peer is Cloudflare, else the real peer.
   # Overwrite whatever the caller sent.
   proxy_set_header CF-Connecting-IP $remote_addr;
   proxy_set_header CF-IPCountry     $cf_ipcountry;
   proxy_set_header CF-IPContinent   $cf_ipcontinent;
   proxy_set_header CF-IPCity        $cf_ipcity;
   proxy_set_header CF-Region        $cf_region;
   proxy_set_header CF-Region-Code   $cf_region_code;
   proxy_set_header CF-Postal-Code   $cf_postal_code;
   proxy_set_header CF-Timezone      $cf_timezone;
   proxy_set_header CF-IPLatitude    $cf_iplatitude;
   proxy_set_header CF-IPLongitude   $cf_iplongitude;
   # The platform admin's client-certificate headers belong to the private listener only (step 4).
   proxy_set_header X-Client-Verify           "";
   proxy_set_header X-Client-Cert-Fingerprint "";
   ```
3. ⬜ **Sites.** Body size limits per location, sized to what each route takes (security review M12 and I6): enveloped JSON is at most 2 MB (`MAX_ENVELOPE_BYTES`), upload bytes at most 25 MB (`PUT /api/v1/storage/{token}`), the gateway's JSON at most 1 MB and its file uploads (`POST /{apiKey}/{endpoint}/files`) at most 25 MB plus the multipart around it. Nginx answers anything larger with 413 before the app reads it.
   ```nginx
   server {
     listen 443 ssl http2;
     server_name services.formalie.com;
     ssl_certificate     /etc/ssl/formalie/origin.pem;
     ssl_certificate_key /etc/ssl/formalie/origin-key.pem;
     client_max_body_size 3m;                       # enveloped JSON (2 MB) and the small plain routes
     location /internal/ { return 404; }            # the internal admin API is never public
     location /api/v1/internal/ { return 404; }     # the retired server-rendered reads (review L15)
     location ~ ^/api/v1/storage/[^/]+$ {           # upload bytes (pre-signed, single use)
       client_max_body_size 26m;
       include snippets/formalie-services.conf;
     }
     location / {
       include snippets/formalie-services.conf;
     }
   }
   server {
     listen 443 ssl http2;
     server_name api.formalie.com;                  # the API service gateway; it sets its own CORS headers
     ssl_certificate     /etc/ssl/formalie/origin.pem;
     ssl_certificate_key /etc/ssl/formalie/origin-key.pem;
     client_max_body_size 1m;                       # the gateway's JSON bodies (1 MB)
     location /internal/ { return 404; }
     location /api/v1/internal/ { return 404; }
     location ~ ^/[^/]+/[^/]+/files$ {              # file uploads through the API service (25 MB a file)
       client_max_body_size 27m;
       include snippets/formalie-gateway.conf;
     }
     location / {
       include snippets/formalie-gateway.conf;
     }
   }
   ```
   With the two proxy snippets:
   ```nginx
   # /etc/nginx/snippets/formalie-services.conf
   include snippets/formalie-public.conf;
   proxy_pass http://127.0.0.1:5004;
   proxy_set_header Host $host;                     # services.formalie.com: a host with no workspace
   # The Worker's headers go through unchanged (never $host here): the API trusts them only when
   # X-Formalie-Edge carries EDGE_SECRET, and ignores them otherwise.
   proxy_set_header X-Forwarded-Host  $http_x_forwarded_host;
   proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
   proxy_set_header X-Forwarded-For   $http_x_forwarded_for;
   proxy_set_header X-Formalie-Edge   $http_x_formalie_edge;
   proxy_read_timeout 120s;

   # /etc/nginx/snippets/formalie-gateway.conf
   include snippets/formalie-public.conf;
   proxy_pass http://127.0.0.1:5005;
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-Host  $host;
   proxy_set_header X-Forwarded-Proto https;
   proxy_set_header X-Forwarded-For   $remote_addr;
   ```
4. ⬜ **Private listener for the platform admin** (PRODUCTION-CHECKLIST section 8): a separate `server` on the private address only, `/internal/admin/v1/` only, `ssl_verify_client on` with the platform's CA, passing `X-Client-Verify $ssl_client_verify` and `X-Client-Cert-Fingerprint $ssl_client_fingerprint`. This is the only place those two headers are set.
5. ⬜ **Cloudflare Authenticated Origin Pulls (recommended):** Cloudflare → SSL/TLS → Origin Server → Authenticated Origin Pulls on, and in both public server blocks `ssl_client_certificate /etc/ssl/cloudflare/authenticated_origin_pull_ca.pem; ssl_verify_client on;` (Cloudflare's origin-pull CA). Then only Cloudflare can open a TLS connection to the public listeners, even if the firewall has a gap. On these listeners `$ssl_client_verify` says SUCCESS for Cloudflare's own certificate, one more reason the snippet clears `X-Client-Verify`.
6. ⬜ `sudo nginx -t && sudo systemctl reload nginx`.
7. ⬜ **Cloudflare only:** app-1's firewall accepts ports 80 and 443 from Cloudflare's ranges only (cloudflare.com/ips), so nobody reaches Nginx around Cloudflare. Check once from a machine outside Cloudflare: `curl -sk --resolve services.formalie.com:443:<app-1 address> -H "CF-Connecting-IP: 203.0.113.9" https://services.formalie.com/api/v1/health` must not connect (firewall) or must fail the TLS handshake (Authenticated Origin Pulls); if it does answer, the request log must show your own address, never `203.0.113.9`.

## Part 7. Cloudflare (once)

1. ⬜ **DNS** (all proxied, orange cloud, except mail records):

   | Name | Type | Points to |
   | --- | --- | --- |
   | `services` | A | app-1's public address |
   | `api` | A | app-1's public address |
   | `*` | AAAA | `100::` (placeholder: the Workers answer, nothing reaches it) |
   | `@` (formalie.com), `www` | AAAA | `100::` (the website's Worker) |
   | mail records | TXT / CNAME / MX | SPF, DKIM, DMARC and SES's records (Part 9), DNS only |

2. ⬜ **SSL/TLS:** mode **Full (strict)**; Edge Certificates: Always Use HTTPS on, HSTS on (after the first checks pass), minimum TLS 1.2.
3. ⬜ **Security:** WAF managed rules on; a rate limiting rule on `/api/v1/auth/*` of the portal hosts (`*.formalie.com/api/v1/auth/*`, where browsers call it); Bot Fight Mode on.
4. ⬜ **Caching:** a Cache Rule "bypass cache" for `services.formalie.com`, `api.formalie.com` and `/api/*` on the portal hosts (never cache the API). The static sites are cached by the Workers themselves.
5. ⬜ **Worker routes:** more specific routes win, so `services.formalie.com/*` and `api.formalie.com/*` must **not** match the portal's wildcard route: add both as routes with "Worker: None" in Workers Routes, so they go to Nginx.

## Part 8. Front ends: build and deploy (after B17)

All three are built on your own machine (or a CI job), never on a server. Each project has a `wrangler.jsonc` (the portal's is built, 2026-10-12); the deploy tool is Cloudflare's `wrangler`.

### 8a. The portal (formalieFrontend)

1. ⬜ Fresh copy of the branch: `git pull`. Checks: `pnpm typecheck`, `pnpm lint`, `pnpm test` (the Worker's tests are in `test/edge/`), all green.
2. ⬜ Production values (PRODUCTION-CHECKLIST section 3) in `.env.production` (git-ignored, never committed):
   ```
   NUXT_PUBLIC_API_MOCK=false
   NUXT_PUBLIC_API_BASE=/api/v1
   NUXT_PUBLIC_ROOT_DOMAIN=formalie.com
   NUXT_PUBLIC_FORMS_HOST=forms.formalie.com
   NUXT_PUBLIC_API_SERVICE_URL=https://api.formalie.com
   NUXT_PUBLIC_SITE_URL=https://formalie.com
   ```
   `NUXT_PUBLIC_API_BASE` stays `/api/v1`: the browser calls its own host and the Worker forwards it to `https://services.formalie.com`.
3. ⬜ Build, check and deploy, in this order:
   ```
   pnpm install
   pnpm generate --dotenv .env.production
   pnpm release:check   # must say clean
   npx wrangler@4 deploy --dry-run --outdir .output/edge && pnpm release:check   # optional, checks the Worker bundle
   npx wrangler@4 login          # once
   npx wrangler@4 secret put EDGE_SECRET   # once, the backend's EDGE_SECRET
   npx wrangler@4 deploy         # every release
   npx wrangler@4 rollback       # roll back
   npx wrangler@4 tail formalie-portal   # live logs
   ```
   - `pnpm generate --dotenv .env.production` builds `.output/public` (without `--dotenv`, Nuxt reads `.env`, the development values).
   - `pnpm release:check` searches `.output/public` (and `.output/edge`, the Worker bundle, when the dry run made it) for `formalie.dev`, `:2202`, `:3033`, `:5004`, `:5005`, `localhost`, `127.0.0.1`, `mkcert`, `devcerts`. Any hit lists the file and stops; never deploy then, fix the source.
   - The Worker's secret is set once, and again whenever it is rotated (together with the backend's). Never in `wrangler.jsonc` or the build.
4. ⬜ **Routes, at go-live:** the routes in `wrangler.jsonc` (`manage.formalie.com/*`, `forms.formalie.com/*`, `*.formalie.com/*`) stay commented out until then; uncomment them for the go-live deploy. In Cloudflare → Workers Routes, `api.formalie.com/*` and `services.formalie.com/*` are set to Worker **"None"** (Part 7 step 5), so the wildcard route never catches them and they go to Nginx.
5. ⬜ What the deploy serves: `.output/public` as a single-page app (unknown paths fall back to `index.html`); the Worker runs first for `/api/*` (proxied to `https://services.formalie.com` with `X-Formalie-Edge` and `X-Forwarded-Host / -Proto / -For`), `/s/*` (short-link redirects from `/api/v1/edge/links/{code}`), `/*/fill` and `/*/embed` (form titles, preview images and the embed's `frame-ancestors` from `/api/v1/edge/forms/{formKey}/preview`).
6. ⬜ Check `https://manage.formalie.com` loads and signing in works (that is the Worker's `/api/*` proxy and the edge secret together), then Part 11.

### 8b. The website (formalieSite)

1. ⬜ `pnpm install --frozen-lockfile`, checks green, production values (PRODUCTION-CHECKLIST section 7).
2. ⬜ `pnpm generate`, the same "no development address" search, then `pnpm dlx wrangler deploy` with routes `formalie.com/*` and `www.formalie.com/*`.
3. ⬜ Sign-up links reach `https://manage.formalie.com/auth/signup`; sitemap and robots answer.

### 8c. The platform admin (formaliePlatformFront)

1. ⬜ The same steps with its own values (its 04-HOSTING), deployed to its own host. Protect it with **Cloudflare Access** (staff email addresses only) in front of its own sign-in.

### 8d. Workspaces' own web addresses (B11)

1. ⬜ Cloudflare for SaaS on the zone: fallback origin `custom.formalie.com`; each verified workspace domain is added as a custom hostname, and the portal's Worker answers them exactly like a workspace subdomain: the static app, and `/api/*` proxied to `services.formalie.com` with the edge secret and `X-Forwarded-Host` = the workspace's domain, which the API maps to the workspace. Confirm who adds the custom hostnames (by hand or from the backend) with Claude in B17.

## Part 9. Outside services (once)

1. ⬜ **Email (SES):** verify `formalie.com` as an identity, publish its DKIM CNAMEs, SPF (`v=spf1 include:amazonses.com ~all`), DMARC (`v=DMARC1; p=quarantine; rua=mailto:dmarc@formalie.com`), and a custom MAIL FROM. Leave the sandbox. Workspaces' own sending domains: PRODUCTION-CHECKLIST section 6.
2. ⬜ **Google:** in Google Cloud → Credentials → the OAuth client, add the production return address (PRODUCTION-CHECKLIST section 5), then publish the app and finish the consent screen check.
3. ⬜ **Facebook:** add the production return address and `formalie.com` under App domains, switch the app to Live.
4. ⬜ **Anthropic:** production key in `.env`, monthly limit set in the console.
5. ⬜ **MaxMind:** account ID and licence key in `.env`.
6. ⏸ **Payoneer** and **SMS** when they are ready.

## Part 10. Platform admin backend (formaliePlatformBack)

1. ⬜ Install it on its own servers as its [04-HOSTING](../../formaliePlatformBack/docs/04-HOSTING.md) describes (its own database, Redis, RabbitMQ vhost).
2. ⬜ Connect it to Formalie over the private network only: the read replica (`platform_reader`), the global tables (`platform_writer`), the private Nginx listener with its client certificate, the same `PLATFORM_ADMIN_KEYS` pair on both sides, its RabbitMQ user (PRODUCTION-CHECKLIST section 8).

## Part 11. First launch checks

Do these in a private browser window; tick each.

1. ⬜ `https://formalie.com` shows the website; Sign up goes to `https://manage.formalie.com/auth/signup`.
2. ⬜ Sign up with email and password: the code email arrives (check spam), the workspace opens on `https://{sub}.formalie.com`.
3. ⬜ Sign out and in again with Google, then with Facebook.
4. ⬜ Build a form, publish it, open its link on a phone, submit an answer; the response appears, the notification email arrives with the Formalie layout and an Unsubscribe link.
5. ⬜ Share the form link in a chat app: the preview shows the form's title. A short link `/s/…` opens the form.
6. ⬜ Embed the form on a test page: it shows and submits.
7. ⬜ Export responses: the file downloads.
8. ⬜ API service: create a token, call `https://api.formalie.com/{apiKey}/{endpoint}` from Postman.
9. ⬜ AI: one request of each kind in the builder.
10. ⬜ Help centre opens, search works.
11. ⬜ Platform admin: sign in, see the new workspace, request support access, approve it in the workspace, the banner shows.
12. ⬜ Look at `journalctl -u formalie-*` and the error logs: nothing red. Cloudflare → Security → Events: nothing blocked that should pass.
13. ⬜ Edge trust: `curl -i -H "X-Forwarded-Host: {sub}.formalie.com" https://services.formalie.com/api/v1/edge/links/abcde` (no secret) answers 404 `FRM-GEN-1004`, like a route that does not exist; the same short link through `https://forms.formalie.com/s/{code}` redirects to the form.
14. ⬜ Run the "no development value left" search from PRODUCTION-CHECKLIST once more, then turn on HSTS.

## Part 12. Every later release

**Backend:**
1. ⬜ Tests green on your machine (`fmly\Scripts\python.exe -m pytest`).
2. ⬜ On app-1 and worker-1: clone the new version into `releases/<date>`, make its `fmly` venv, `pip install -r requirements.txt`, link `.env`.
3. ⬜ Once, on one machine: `fmly/bin/alembic upgrade head` (migrations add first and remove later, so the old version keeps working meanwhile).
4. ⬜ Switch: `ln -sfn /srv/formalie/releases/<date> /srv/formalie/current`, then `sudo systemctl restart formalie-api formalie-gateway` (app-1) and `formalie-worker-fast formalie-worker-jobs formalie-beat formalie-platform-consumer` (worker-1).
5. ⬜ `curl https://services.formalie.com/api/v1/health` answers; Part 11 steps 2 and 4 quickly.
6. **Roll back:** link `current` to the previous release folder and restart the same units. No database restore is needed.

**Front ends:** Part 8 for the project that changed (the portal: 8a steps 1 to 3 and 6). **Roll back:** `npx wrangler@4 rollback` in the project, or Cloudflare → Workers → the Worker → Deployments → "Rollback" to the previous version (instant).

**After each release:** keep the last 5 release folders, delete older ones (`releases/` only; never the database or `shared/`).

## Part 13. Running it day to day

- ⬜ **Monitoring:** an uptime check on `https://services.formalie.com/api/v1/health` and `https://manage.formalie.com` (for example Cloudflare Health Checks or UptimeRobot), alerts by email.
- ⬜ **Alerts:** `ALERT_EMAILS` receives the backend's CRITICAL errors. Monitoring and alerts are the platform admin's Operations page, fed by `/internal/admin/v1/health/services` (services, queues and dead letters, Beat's heartbeat, the last backup, partitions, connections, replica lag, disk, certificate).
- ⬜ **Backups:** a monthly restore drill.
- ⬜ **Updates:** Ubuntu security updates are automatic; once a month, `pip list --outdated` and `pnpm outdated` reviewed with Claude.
- ⬜ **Keys:** rotate the platform admin keys and the SAML certificate before they expire (PRODUCTION-CHECKLIST section 2).

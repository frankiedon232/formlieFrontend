# 04, Hosting and Deployment

**No Docker** (owner, 2026-10-10): services are installed directly on the machines, the way Formalie is run. Production is either **AWS** or **dedicated servers**, chosen per deployment; both are described here and the application is the same on either. Docker may be added later only if a real need comes up (owner approval).

## What runs where

| Part | Runs as | Notes |
| --- | --- | --- |
| Front end (`formaliePlatformFront`) | static files from `nuxt generate` (client-rendered SPA), hosted on Cloudflare (owner, 2026-10-12; DEPLOYMENT-GUIDE Part 8c), behind Cloudflare Access | no Node process in production |
| API (`formaliePlatformBack`) | `uvicorn --workers N` under **systemd**, behind Nginx | listens on `127.0.0.1:5601` (or a private address); stateless, add servers to scale |
| Workers | `celery worker` per queue group under **systemd** | `ingest`, `rollups`, `publish`, `actions`, `reports`, `mail`, `maintenance` |
| Scheduler | `celery beat` under **systemd**, exactly **one** running | |
| Analytics consumer | Celery worker on `platform.analytics` (Formalie's event bus) | idempotent, replays from its cursor |
| PostgreSQL 16 | the platform's own database (`formalie_platform`), primary + replica | never on the same database server as Formalie in production |
| PgBouncer | next to the API (or on the database server) | transaction pooling |
| Redis 7 | the platform's own instance | sessions, nonces, rate limits, realtime counters |
| RabbitMQ 3 | the platform's own vhost `platform`; a read-only user on Formalie's broker for its events | |
| File storage | S3 (AWS) or S3-compatible storage (MinIO on a dedicated server) | help media, exports |
| Email | Amazon SES (AWS) or the company SMTP relay | staff invitations, two-step codes, scheduled reports |

Unit file sketches: [`infra/systemd/`](../infra/systemd). Nginx sketch: [`infra/nginx.platform.conf`](../infra/nginx.platform.conf).

## Option A: AWS

| Part | AWS service |
| --- | --- |
| Network | one VPC, private subnets for everything except the load balancer; security groups allow only the paths below |
| Entry | Application Load Balancer with an ACM certificate (or Nginx on the instances with its own certificate); AWS WAF with an IP allowlist if the owner wants staff-only networks |
| Front end | S3 bucket + CloudFront (private bucket, origin access control), or Nginx on the API instances |
| API and workers | EC2 instances (Ubuntu LTS) with systemd units; an Auto Scaling group for the API; workers on their own instance(s) |
| Database | Amazon RDS for PostgreSQL 16, Multi-AZ, one read replica, automated backups and point-in-time recovery, encryption at rest |
| Redis | Amazon ElastiCache for Redis 7 (TLS, AUTH) |
| RabbitMQ | Amazon MQ for RabbitMQ (platform vhost); Formalie's broker reached over the private link |
| Storage | S3 (bucket `formalie-platform-…`, encryption, versioning, no public access) |
| Email | Amazon SES |
| Secrets | AWS Secrets Manager (or SSM Parameter Store), read at start; never in files on the instance |
| Logs and alerts | CloudWatch Logs and alarms (API errors, queue depth, replica lag, failed jobs) |
| Reaching Formalie | VPC peering or PrivateLink to Formalie's VPC: its read replica, its internal admin API, its broker. Never over the public internet |

## Option B: dedicated servers

| Part | Set-up |
| --- | --- |
| Servers (suggested start) | **web / API** (Nginx, API, PgBouncer), **workers** (Celery, Beat, consumer), **database** (PostgreSQL primary, Redis, RabbitMQ), **database replica** (streaming replication); grow by adding API and worker servers |
| OS | Ubuntu LTS, unattended security updates, SSH keys only (no passwords), no root login, fail2ban |
| Firewall | only 443 open to the world (or only to staff networks / VPN); every other port only between the platform's servers |
| Certificates | Let's Encrypt (certbot, auto renewal) or a commercial certificate; always valid, never mkcert |
| Storage | MinIO (S3-compatible) on the database or a storage server, or a provider's S3-compatible object storage |
| Backups | pgBackRest (or WAL archiving + nightly base backups) to off-site storage, encrypted; restore tested every quarter |
| Reaching Formalie | a private network between the providers' servers or a WireGuard tunnel to Formalie's servers: read replica, internal admin API, broker. Never over the public internet |
| Monitoring | the provider's monitoring plus the platform's own Operations page; alerts by email |

## Deploying a release (same on both)

1. Front end: `pnpm install --frozen-lockfile`, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm generate`; upload `.output/public` to the web root (or the S3 bucket) as a new release folder, then switch the link (instant roll back by switching it back).
2. Backend: copy the release into `/srv/platformapi/releases/<version>`, create its venv (`python3.11 -m venv padm`, `pip install -r requirements.txt`), run `alembic upgrade head` once, switch the `current` link, `systemctl restart platformapi` (one server at a time behind the load balancer, so no requests are lost) and restart the workers. Beat restarts last.
3. Migrations are backwards compatible for one release (add first, remove later), so a roll back never needs a database restore.
4. Health check `GET /api/health` after every step; the release stops if it fails.

## Production addresses

To decide (open question 1): `platformadm.formalie.com` / `platformapi.formalie.com`, a separate domain, or a separate IP reachable only through a VPN. The hosting above works for all three.

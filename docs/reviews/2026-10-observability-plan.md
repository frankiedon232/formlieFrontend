# Observability plan (B17, 2026-10-12)

What to watch in production, built first on what Formalie already has, and the options for dashboards. **This is a proposal only.** Every new dependency or service below needs the owner's approval before it is added, and any setting that differs between development and production goes into `docs/PRODUCTION-CHECKLIST.md` in all five projects.

## 1. What exists today

| Source | What it gives | Where |
| --- | --- | --- |
| Level and day log files | JSON lines per process (`api`, `gateway`, `worker`, `beat`), one file per level per UTC day, 90 days kept; every request line has `trace_id`, tenant, route, status, duration, error code, IP and host | `logs/{level}/YYYY-MM-DD.log`, `app/core/logging/sinks.py`; request summary in `app/core/middleware/request_log.py` |
| `error_logs` table | Warning, error and critical lines ingested from the files (`logs.ingest_error_files`), with level, code, trace id, tenant | `app/modules/logs/tasks.py`, `logs/models.py` |
| `request_logs` table | Every portal request (route, status, duration, geo), monthly partitions | `app/modules/logs/models.py` |
| `api_request_logs` | Every API service call per workspace (status, duration, endpoint, token, rate limited) | `app/modules/api_service/models.py` |
| `ALERT_EMAILS` | CRITICAL log lines are emailed when the error files are ingested | `config.py:198`, `logs/tasks.py:38` |
| `GET /api/v1/health` | Liveness, plaintext, any host | `app/modules/platform/router.py:38` |
| `GET /internal/admin/v1/health/services` | Primary and replica DB ping times, Redis, RabbitMQ with per-queue depth and consumers, the outbox's oldest unpublished event (degraded when late); signed platform admin call | `app/modules/platform_bridge/health.py` |
| Flower | Celery tasks, workers, failures, runtimes (dev dependency today: `flower==2.2.0` in requirements-dev.txt) | `logs/dev/flower.log` |
| RabbitMQ management | Queue depth, publish and deliver rates, unacked messages, connections | port 15672 |
| Cloudflare analytics | Requests, cache ratio, status codes, countries, WAF events, per host (`services.`, `api.`, `manage.`, `forms.`, the Worker) | Cloudflare dashboard |
| DEPLOYMENT-GUIDE monitoring line | An uptime check on `/api/v1/health` and `manage.` with email alerts, not done yet | `docs/DEPLOYMENT-GUIDE.md:291` |

Gaps: no numbers over time (latency percentiles, error rate, queue depth trend), no host metrics (CPU, memory, disk), no PostgreSQL internals (connections, locks, slow queries, replication lag, partition creation), no alert other than CRITICAL lines and the uptime check, and Flower and the RabbitMQ page are not safe to expose as they are.

## 2. What to watch (signals and first thresholds)

Thresholds are starting points; tune after two weeks of real traffic.

**API (portal, `services.`)**
- Request rate, error rate (5xx share; alert above 1 % for 5 minutes), p95 latency per route group (alert p95 above 1.5 s for 10 minutes on lists, above 800 ms on public form and submit).
- 429 share per route (a jump means an attack or a client bug), FRM-SEC-1002 / 1003 / 1004 counts (clock skew, replays, key loss after a Redis restart).
- Sign-in: `auth.otp.failed`, `auth.otp.locked`, login failures per minute (spikes = credential stuffing); these are already audit rows.

**Public forms**
- Submits per minute, FRM-RESP-1009 (challenge refused) and 1004 / 1005 / 1006 (duplicates) shares, p95 submit time (the query review's Q2 and Q4 show up here first).

**API service gateway (`api.`)**
- Calls, 4xx / 5xx, p95 per endpoint, rate-limited share; from `api_request_logs` or the gateway's request lines.

**Background work**
- RabbitMQ: depth per queue (`exports`, `destinations`, `webhooks`, `notifications`, `logs`, `scheduled`); alert when a queue grows for 10 minutes or has no consumer.
- Outbox: oldest unpublished event (already in health; alert above 60 s).
- Celery: task failure rate per task name, task runtime p95, Beat alive (a heartbeat task that writes a timestamp; alert when older than 5 minutes).
- Webhook and destination deliveries: failed share, auto-paused webhooks.
- Emails: send failures (the sent log), bounces when the relay reports them.

**PostgreSQL**
- Connections used vs `max_connections` and PgBouncer pool waits, longest running query and transaction, lock waits, deadlocks, replication lag per replica, cache hit ratio, table and index bloat on `responses`, `audit_logs`, `request_logs`.
- Monthly partitions exist for the next 2 months (`platform.ensure_monthly_partitions`); alert if not (a missing partition makes inserts fail).
- `pg_stat_statements` top 20 by total time (a PostgreSQL contrib extension; enabling it is a server setting, owner to approve).

**Redis**: memory used vs max, evictions (must stay 0: nonces, sessions and rate limits live there), connected clients, command latency.

**Hosts**: CPU, memory, disk (logs and the file store), open files; TLS certificate expiry (Cloudflare origin certs and the mTLS client cert for the platform admin).

**Security signals** (from logs and audit rows): FRM-TEN-1003 (token and host disagree), support sessions started, internal admin API refusals (bad HMAC or nonce), spikes of 401 on `/auth/refresh`, data source tests to new hosts.

**Backups**: last successful base backup and WAL archive age; alert if older than 26 h; a restore drill each quarter (B17 lists it).

## 3. Quick wins with no new dependency

1. Turn on the uptime check from DEPLOYMENT-GUIDE (Cloudflare Health Checks or the free tier of an uptime service) for `/api/v1/health`, `api.formalie.com` (an unknown key answers FRM-API-1006 quickly), `manage.` and `forms.`.
2. A Beat task every minute that calls `platform_bridge.health.services()` in process and logs one `formalie.health` JSON line (status and latency per service, queue depths, outbox age); log a CRITICAL line when something is down or degraded for 3 runs, so `ALERT_EMAILS` fires. (Code change; for the backend's next phase.)
3. Make `ALERT_EMAILS` go through a channel that does not depend on the API being healthy: the Celery `notifications` queue fails with RabbitMQ. A last-resort direct SMTP send from the ingest task when the broker is down.
4. Keep Flower and the RabbitMQ management page off the public internet: bind to `127.0.0.1`, reach them through an SSH tunnel, set credentials (Flower `--basic-auth` or `--auth`, RabbitMQ: delete `guest`). Flower shows task arguments, and email tasks carry codes and links (security review I9).
5. Cloudflare: notifications for origin error rate (5xx) and for WAF or DDoS events on each zone; these exist on every plan.

## 4. Dashboard options

### Option A. Self-hosted Prometheus and Grafana

- **App side:** expose `/metrics` on a private port per process.
  - FastAPI: `prometheus-client` plus either a small ASGI middleware of our own (route template, status, duration histogram) or `prometheus-fastapi-instrumentator`.
  - Celery: `celery-exporter` (a separate process reading events from RabbitMQ) or Flower's own `/metrics`.
- **Exporters (no code):** `node_exporter` (hosts), `postgres_exporter`, `pgbouncer_exporter`, `redis_exporter`, RabbitMQ's built-in `rabbitmq_prometheus` plugin.
- **Logs:** Grafana Loki with Promtail (or Grafana Alloy) shipping the existing JSON files; queries by `trace_id`, tenant, error code.
- **Alerting:** Alertmanager (email, later Slack or SMS).
- **New dependencies:** Python: `prometheus-client` (and optionally `prometheus-fastapi-instrumentator`). Services on a small monitoring VM (2 vCPU, 4 GB, 50 GB disk): Prometheus, Grafana, Alertmanager, Loki, plus the exporters on each host. All open source, no Docker needed (systemd binaries).
- **Pros:** no per-host or per-GB fees; data stays on Formalie's servers (good for the data residency story); Grafana has ready dashboards for PostgreSQL, Redis, RabbitMQ, node.
- **Cons:** one more server to patch, back up and secure; someone has to own it; retention and disk need care.

### Option B. Hosted (Grafana Cloud, Datadog, New Relic, Better Stack, Sentry)

- **Grafana Cloud:** the same agents as option A (Grafana Alloy collects metrics, logs and traces and sends them out); free tier covers a start (10k series, 50 GB logs, 14 days); paid by usage.
- **Datadog / New Relic:** one agent per host plus `ddtrace` / `newrelic` Python packages for traces; strongest out of the box, priced per host and per GB, gets expensive quickly.
- **Sentry:** `sentry-sdk` for errors and traces with request context; complements, does not replace, metrics.
- **New dependencies:** one agent per host, and a Python package per tool (`sentry-sdk`, `ddtrace` or `newrelic`; Grafana Cloud needs only `prometheus-client` as in A).
- **Pros:** nothing to run; alerting, on-call and retention included; fastest to useful dashboards.
- **Cons:** monthly cost that grows with traffic; logs and traces leave Formalie's servers, so log content must be clean first (security review M8, M9, L18: answers, tokens and SQL parameters are in today's logs); a data processing agreement and the sub-processor list need updating.

### Option C. Cloudflare plus log shipping

- **Edge:** Cloudflare analytics, Health Checks, notifications, and Logpush (Enterprise only for HTTP request logs; Workers Trace Events and Workers Logs on paid Workers plans) to an R2 bucket.
- **Origin logs:** ship the JSON files with Vector or Fluent Bit to object storage or a log service; query with ad hoc tools; alerts from a small scheduled job.
- **New dependencies:** Vector or Fluent Bit on each host (single binaries); a Cloudflare plan that includes what is needed.
- **Pros:** cheapest; edge view is good for traffic, attacks and the forms host.
- **Cons:** no metrics over time for the database, Redis, queues or latency percentiles at the origin; dashboards are thin; alerting is hand-made.

## 5. Recommendation

Go with **Option A, Prometheus and Grafana, on Grafana Cloud's free tier first** (so nothing new to run), with the same agents and exporters as a self-hosted setup. Move to a self-hosted monitoring VM when the free tier is outgrown or when the owner prefers data to stay on Formalie's servers. Keep Cloudflare analytics and Health Checks for the edge (option C's free parts) alongside.

Why: the problems this review found (in-memory lists, per-form lock on submit, unbounded queries, queue build-up) show up as latency percentiles, pool waits, lock waits and queue depth, which only a metrics system gives. Grafana Cloud's agents are the same open source pieces, so there is no lock-in.

Before any logs leave the servers, fix what the logs contain (security review M8, M9, L18), and do not send `request_logs` bodies anywhere.

### Dependencies to approve (proposal)

| Item | Kind | Needed for |
| --- | --- | --- |
| `prometheus-client` | Python package (runtime) | `/metrics` for API, gateway and workers |
| `prometheus-fastapi-instrumentator` (optional) | Python package | Route metrics without our own middleware |
| `celery-exporter` or Flower `/metrics` | Process | Task metrics |
| `node_exporter`, `postgres_exporter`, `pgbouncer_exporter`, `redis_exporter` | Binaries on hosts | Host and service metrics |
| `rabbitmq_prometheus` | RabbitMQ plugin (ships with RabbitMQ) | Queue metrics |
| Grafana Alloy (or Promtail) | Agent on each host | Shipping metrics and the JSON log files |
| Grafana Cloud account (or a monitoring VM with Prometheus, Grafana, Alertmanager, Loki) | Service | Storage, dashboards, alerts |
| `pg_stat_statements` | PostgreSQL extension | Slow query view |

### First dashboards

1. **Overview:** requests per second, 5xx share, p50 / p95 / p99 by route group, 429 share, active sessions; per host (`services.`, `api.`).
2. **Public forms:** form loads, submits, refusals by code, submit p95.
3. **Background:** queue depth per queue, consumers, outbox age, task failures, Beat heartbeat, webhook and destination failures.
4. **Database:** connections and pool waits, slow queries, locks, replication lag, partitions ahead, disk.
5. **Redis and hosts:** memory, evictions, CPU, memory, disk.
6. **Security:** sign-in failures and lockouts, FRM-TEN-1003, FRM-SEC-1003 replays, support sessions, internal API refusals.

### First alerts (email to `ALERT_EMAILS`)

API down (uptime), 5xx above 1 % for 5 min, p95 above threshold for 10 min, any queue without a consumer, a queue growing for 10 min, outbox older than 60 s, Beat heartbeat older than 5 min, DB connections above 80 %, replication lag above 30 s, next month's partition missing, Redis evictions above 0, disk above 80 %, last backup older than 26 h, certificate expiring within 14 days.

## 6. To add to PRODUCTION-CHECKLIST (when approved)

The metrics port and its firewall rule, the Grafana Cloud (or monitoring VM) credentials, the alert addresses, Flower and RabbitMQ management bound to localhost with credentials, the uptime checks, `pg_stat_statements` enabled.

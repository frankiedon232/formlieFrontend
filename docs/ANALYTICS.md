# Analytics (Google Analytics style, owner 2026-10-10)

What happens on Formalie, as numbers, charts and history: accounts, access, usage, growth and revenue. Built from Formalie's events (FORMALIE-INTEGRATION §4) plus a one-time backfill from Formalie's audit and request logs.

## Principles

- **Never content.** No respondents' answers, files, form questions' text, passwords, tokens or secrets. People appear as encrypted references; names and emails only where a report needs them, masked until revealed (permission + step-up, audited).
- **Country and city, never the IP.** IPs are turned into country / region / city on arrival (local GeoIP file) and dropped.
- **Everything has a date range and a comparison** with the previous period (or the same period last year).
- **Every chart has a table** and an export (CSV / XLSX); every number links to the list behind it.
- **Time zone:** each staff member's own; rollups stored in UTC with hourly grain so any time zone can be shown.

## Data model (platform database, DATA-MODEL.md in formaliePlatformBack)

| Table | Grain | Kept |
| --- | --- | --- |
| `analytics_events` | one row per event, partitioned by day | 13 months (configurable) |
| `analytics_rollup_minute` | metric × key dimensions per minute | 7 days |
| `analytics_rollup_hour` | metric × dimensions per hour | 25 months |
| `analytics_rollup_day` | metric × dimensions per day | forever |
| `analytics_sessions` | one row per portal session (start, end, pages, device, country, workspace) | 13 months |
| `analytics_daily_tenant` | one row per workspace per day (active people, forms, responses, API calls, storage, plan, MRR) | forever |
| `analytics_daily_user` | one row per person per day they were active | 25 months |
| `analytics_reports` | saved explorer reports, schedules | forever |

Rollups are recomputable from raw events (Celery task per partition), so a fix to a metric can be re-run over history.

## Metrics

| Group | Metrics |
| --- | --- |
| People | active people (1, 7, 28 days), new people, returning people, DAU / WAU / MAU, stickiness (DAU/MAU) |
| Workspaces | active workspaces, new sign-ups, set-up completed, trials, paying, suspended, closed |
| Sessions | sessions, average session length, pages per session, bounce (one page) |
| Access | sign-ins, failed sign-ins, lockouts, two-step use by method, sign-ins by provider, sessions ended by idle / sign-out / admin |
| Product | forms created, published, closed; responses; responses per form; completion rate; files uploaded; exports; data source operations; API calls and errors; webhooks sent / failed; AI requests (F19) |
| Activation | sign-up → set-up completed → first form → first publish → first response → second member → paid (step conversion and median time) |
| Retention | weekly / monthly cohorts by sign-up date (people and workspaces), churn rate, reasons (from cancellation) |
| Revenue | MRR, ARR, new / expansion / contraction / churned MRR, net revenue retention, ARPU, LTV, payments, failed payments, refunds, by plan / country / currency |
| Limits | workspaces near or over plan limits (forms, responses, seats, storage, connections) |
| Health | API latency (p50 / p95), error rate, queue backlog, failed jobs (operations, mirrored here for trends) |

## Dimensions

Date (hour, day, week, month), workspace, plan, plan interval, country, region, city, language, device type, browser, operating system, sign-in method, source / medium / campaign (sign-ups), channel (link, embed, API), feature, form template, role (built-in or custom), status.

## Reports (pages)

1. **Overview:** KPI cards (active people, active workspaces, new sign-ups, responses, MRR, error rate) with sparklines and change; sign-ups and active people over time; top countries; activation funnel summary; alerts.
2. **Realtime:** active now (last 5 min) by country, device, page template; events per minute; latest events (no personal data).
3. **Acquisition:** sign-ups by source / medium / campaign / referrer / country / plan; sign-up conversion from the website (when the website sends its events).
4. **Engagement:** DAU / WAU / MAU, sessions, pages, features used (by plan), time in product.
5. **Activation:** the funnel above with drop-off, median time between steps, by cohort, plan and country.
6. **Retention:** cohort grid (sign-up week × weeks after), people and workspaces; churn reasons.
7. **Usage:** forms, responses, API calls, storage per workspace and in total; top workspaces; near limits.
8. **Revenue:** MRR movements chart, plan mix, payments and failures, refunds, by country and currency (from F24's billing events).
9. **Geography and technology:** map (countries), tables by country, language, device, browser, OS.
10. **Access history:** every sign-in with workspace, person (masked), method, result, country, device, time; filters; per-person and per-workspace timelines; failed sign-in spikes highlighted.
11. **Explorer:** choose metric(s), dimensions (up to 3), filters, date range, chart type (line, bars, table); save; share with staff; schedule by email (daily / weekly / monthly, to staff only); export.

Each report: date range picker with presets (today, yesterday, 7 / 28 / 90 days, this / last month, year, custom), compare toggle, segment filters (plan, country, status), chart cards in Formalie's style (`ChartsMiniBars`, `ChartsLines`, SVG with theme tokens), DataView table below with Table / Grid, columns, sort, export.

## Ingestion

1. Celery consumer reads `platform.analytics` (prefetch tuned), validates the event against its schema (Pydantic), drops unknown or personal fields, enriches (GeoIP if Formalie sent an IP by mistake, then drops it; user agent → device / browser / OS), writes `analytics_events` in batches, increments Redis realtime counters, acknowledges.
2. Dedup by event id (unique index on `(occurred_on, id)`).
3. Celery Beat: minute rollups every minute, hour rollups every 5 minutes for the current hour, day rollups every hour for today and once after midnight UTC for yesterday; sessions closed after 30 minutes without events.
4. Backfill job (once, and on demand for a date range): reads Formalie's audit logs, request logs and billing tables from the replica and writes events with `source = backfill`.

## Performance

Partitioned tables, BRIN indexes on time, composite indexes on rollup keys, queries only on rollups for ranges longer than a day, cached report responses (Redis, 60 s for today, 1 h for closed days), paged tables in the database, never the whole set in the browser.

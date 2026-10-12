# Query and index review (B17, 2026-10-12)

Scope: the hot paths named in BACKEND-ROADMAP B17 (response lists and filters, forms list, audit list, the request logs, dashboard and analytics, public submit, the API service gateway, the outbox relay). For each, the SQLAlchemy query was read and the indexes checked in the models and migrations (0001 to 0034). This is a review only: no code, migration or index was changed.

## How it was checked

- Code read at commit `ff378a2b` plus the working tree of 2026-10-12 (another helper was editing edge and gateway code at the same time; nothing here depends on those edits).
- `EXPLAIN` (plans only; no `ANALYZE` on anything that writes) against the **development database**, connected with `DB_APP_URL` as `formalie_app`, in a `READ ONLY` transaction, with `app.tenant_id` / `app.organisation_id` set through `set_config(..., true)` exactly as `app/core/db/session.py` does, so RLS applied. The tenant was found with `platform.resolve_tenant()`. Nothing was written. The helper script stayed in the session's scratch folder.
- **Limit of the evidence:** the development database is almost empty (1 form, 2 responses, 69 audit rows, 0 API calls in the reachable workspaces). The plans below show the *shape* PostgreSQL picks (which index, how many partitions are visited); they cannot show timings at 1M responses. Where a problem is in the Python code (whole tables loaded into memory), the code is the evidence and no plan is needed.

## Summary

| # | Severity | Path | Problem |
| --- | --- | --- | --- |
| Q1 | Critical | Response lists, inbox, tags, insights, exports (`responses/router.py`, `responses/service.py`) | Every response of the form(s) is loaded (full rows with `data`) and filtered, searched, sorted and paged in Python |
| Q2 | Critical | Public submit with an identity email (`public/router.py`) and the gateway's create (`api_service/gateway_records.py`) | Every response's `data` of the form is read on **each** submit to look for a near-duplicate email |
| Q3 | High | API gateway `GET /{apiKey}/{endpoint}` (`api_service/gateway_records.py:92-161`) | Every response of the form loaded per call, filtered and paged in Python |
| Q4 | High | Submit (portal and gateway) | Form row locked `FOR UPDATE` for the rest of the transaction (destinations, webhooks, audit, outbox): one popular form = one submit at a time |
| Q5 | High | Every query on partitioned tables | No partition pruning: queries filter by `form_id` / `tenant_id`, not by the partition key, so every monthly partition is probed; grows by one partition a month forever |
| Q6 | Medium | Forms list, inbox, dashboard, analytics (`forms/service.py:104`) | `forms_of()` loads every form row (with `draft_schema` jsonb) of the workspace; permission filtering and paging in Python |
| Q7 | Medium | Inbox and multi-form insights (`responses/router.py:77-83`) | N+1: one or two queries per form to read its schema (`published_schema`, then `lists_by_id`) |
| Q8 | Medium | Audit list (`audit/queries.py:86-90, 129-135`) | `q` search is `lower(col) LIKE '%x%'` on seven columns: sequential scan of every partition; `count(*)` on every page |
| Q9 | Medium | API services / tokens / rules lists (`api_service/traffic.py:241-246`) | `max(at)` per endpoint, token and rule with no time bound: reads every `api_request_logs` partition |
| Q10 | Medium | Missing indexes for exact lookups on `responses` | `respondent_kind, respondent_ref_id`; `status = 'new'` counts; device and fingerprint lookups ignore `deleted_at` |
| Q11 | Medium | Forms list and notifications poll | Reads on the primary inside write transactions (`sweep_trash` UPDATE on every forms list; `announce_due` on every notifications poll, the most called route) |
| Q12 | Low | Outbox | `processed_events` never pruned; relay updates rows one by one |
| Q13 | Low | API log list | `strpos(lower(path \|\| ip \|\| ...))` search and `count(*)` per page over up to 30 days |
| Q14 | Info | Indexes the code cannot use | `ix_api_tokens_secret_hash`, `ix_api_tokens_previous_hash` (tokens are matched in Python) |

## Findings

### Q1. Response lists are built in memory (Critical)

**Where.**
- `app/modules/responses/service.py:186-193`, `responses_of()`: `SELECT * FROM responses WHERE tenant_id = :t AND form_id IN (...) AND deleted_at IS NULL ORDER BY submitted_at DESC, id DESC`, with no `LIMIT`.
- `app/modules/responses/router.py:77-83`, `_entries()`. It is used by:
  - `GET /forms/{id}/responses` (line 174)
  - `/responses` (the inbox, line 211)
  - `/responses/forms`
  - `/forms/{id}/responses/insights`
  - `/responses/insights`
- `responses/router.py:188`: `/forms/{id}/responses/tags` reads every row to count tags.
- `filter_entries()` (`router.py:86-145`):
  - status, tag, channel, date, answer filters and `q`;
  - `q` runs `json.dumps(data)` for each row;
  - then two Python sorts, and `_page()` slices the list.
- For every row, `Entry.__init__` runs `respondent_from()` and `title_of()`, and `row_of()` walks the schema again.

**At 1M responses.**
- Each list call transfers about 1M rows with their `data` (typically 1 to 5 KB), in other words 1 to 5 GB.
- It builds 1M ORM objects plus 1M `Entry` objects, holds them all in one worker's memory, and runs on the 15 s `statement_timeout` only for the SQL part.
- The page shows 25 rows. A single form with 50k responses already makes the list take seconds and hundreds of MB.
- Insights and the inbox do this across every visible form.

**Fix.** Move filtering, sorting and paging into SQL:

- **Filters:**
  - status / channel / form: `IN`
  - tag: `tags ?| :tags` (jsonb) with a GIN index
  - flag: `possible_duplicate IS NOT NULL AND NOT duplicate_cleared`
  - dates: `submitted_at BETWEEN`, which also gives partition pruning
  - answer filters: `data -> :key ? :value` or `data @> :json`
- **Search:** `number = :n` for `#123`. Otherwise, a stored lower-cased `search_text` column, filled at submit and on edit with the title, email and form name, behind a `pg_trgm` GIN index. Answer search uses the same column with the answers appended.
- **Sort and page:** `ORDER BY` the chosen column, then keyset pagination (`(submitted_at, id) < (:at, :id)`), or `OFFSET` / `LIMIT` with a `LIMIT` cap on page size.
- **Total:**
  - exact `count(*)` only while it stays below about 10k rows;
  - above that, an estimate, or the per-form counter `forms.responses_count` that already exists when there is no filter.
- **Tags:** `SELECT tag, count(*) FROM responses, jsonb_array_elements_text(tags) tag WHERE ... GROUP BY tag`.
- **Insights:**
  - `count(*) FILTER (...)` and `date_trunc` grouping in SQL (the dashboard code in `dashboard/common.py` already does this, so the pattern exists);
  - per-question summaries over `data -> key` in SQL, or from a nightly rollup table for big forms.
- **Exports** (`responses/exports.py`): already Celery jobs, so stream with `yield_per(1000)` / server-side cursors instead of one list.

### Q2. Every submit reads every earlier response (Critical)

**Where.**
- `app/modules/public/router.py`, `submit_public_form`, in the `elif identity["email"]` branch: `select(StoredResponse.id, StoredResponse.submitted_at, StoredResponse.data).where(*live).order_by(...)` with no limit, then `rules.match_identity()` in Python (typo-distance matching).
- The same pattern sits in `app/modules/api_service/gateway_records.py:292` (`_create`).

**Effect.** This runs on every submit to a form that names a respondent email (decision 85), which is the common case for registrations. The cost of submit number N is O(N) in rows and bytes, inside the write transaction. The transaction holds a pooled primary connection while it reads.

- At 100k responses, each submit reads about 100k jsonb documents: seconds per submit.
- At 1M responses, a submit hits the 15 s statement timeout, and the form stops taking responses.

**Fix.**
1. **Exact duplicates:** look up `identity_email` with the index that already exists (`ix_responses_identity (tenant_id, form_id, identity_email)`), with `LIMIT 1`.
2. **Near duplicates** (one typo away): compare against a bounded candidate set instead of the whole form. Pick one:
   - Same local part or same domain: index the domain (`split_part(identity_email,'@',2)`) and the local part, and only compare rows that share one of them.
   - `pg_trgm` similarity on `identity_email`: `identity_email % :email`, with a GIN trigram index, `LIMIT 20`.
3. Read only `identity_email` (already stored, normalised), never `data`.

### Q3. Gateway GET loads the whole form (High)

**Where.**
- `api_service/gateway_records.py:92-96`: `responses_of(work)` with no limit.
- `read()` (lines 122-161): filters in Python, sorts, then slices `entries[start:end]`.

**Effect.** This is the third-party API path, so it is called by machines in loops. Every page of every call costs a full read of the form's responses. A customer paging through 1M records costs O(N²) overall. It also holds a write session (`db_session("write", ...)`, `gateway.py:314`) on the primary for a read.

**Fix:**
- Use SQL `WHERE` on the chosen filter fields (`data ->> :key = :value`, or `data -> :key ? :value` for arrays).
- Use `ORDER BY submitted_at`, `LIMIT :per_page OFFSET :offset`. A keyset cursor would be better, to add to the contract later.
- Get the total with `count(*)` only on the first page, or switch to `has_more`.
- Use a read session for GET.

### Q4. One submit at a time per form (High)

**Where.**
- `public/router.py`, `locked = (await db.execute(select(Form).where(Form.id == form.id).with_for_update()))`. After this lock, the same transaction:
  - inserts the response and the submission;
  - updates the uploads, the invite and the draft;
  - updates `forms.responses_count`;
  - writes the outbox (`emit`);
  - runs `response_stored()` (destinations), `response_event()` (webhooks) and `record()` (audit).
- The same lock is taken in `gateway_records.py:362`.

**Effect.** The lock is held until commit, so all submits to one form are serialised by the slowest of those steps. In the load test, the steps before the lock already took 25 to 90 ms. A form shared in a newsletter, or a class enrolment at 09:00, queues behind one lock. Waiters hold pool connections (pool 10 + 10), so the whole API can stall on one hot form.

**Fix:**
- Take the number without a long lock: `UPDATE forms SET next_response_number = next_response_number + 1, responses_count = responses_count + 1 WHERE id = :id RETURNING next_response_number - 1` as the **last** statement before commit, or a per-form `SEQUENCE`-like counter table updated at the end.
- Move destinations and webhooks fully to the outbox consumers. They already run from events.
- Keep the transaction to: insert response, insert submission, counter update, outbox insert, audit.

### Q5. Partitions are never pruned (High, grows with time)

**Evidence (EXPLAIN, dev DB).**
- A response list for one form produced an `Append` over `responses_p202610`, `p202611`, `p202612` and `p202701`, with an `Index Scan Backward using ..._tenant_id_form_id_submitted_at_idx` on **each** partition.
- The same holds for `audit_logs` (4 partitions) and `api_request_logs` (7 partitions, `p202607` to `p202701`).
- The planner cannot skip partitions because no query filters on `submitted_at` / `occurred_at` / `at` unless the user picked dates.

**Effect.** After 3 years a response list or a duplicate check probes about 40 partition indexes: each probe is cheap, but planning time and buffer reads grow linearly. The duplicate checks in Q2 and Q10 (`fingerprint`, `device_hash`, `respondent_ref_id`) are the worst, because they run on every submit.

**Fix:**
- For per-form lookups, bound the search where the product allows it, for example `submitted_at >= forms.published_at` or the form's first response date, kept on `forms` as `first_response_at`.
- Put a date bound on the defaults: the response list default view (newest first) can use keyset pagination that stops early. The audit default `from` can be 90 days.
- Consider a non-partitioned **lookup table** for duplicate checks: `response_keys(tenant_id, form_id, kind, value, response_id)` with a unique index, written at submit. That gives one index probe instead of one per partition.
- Keep partitions for retention and archiving, which is what they buy.

### Q6. `forms_of()` loads every form, with its draft (Medium)

**Where.**
- `forms/service.py:104-107`. Called by the forms list (`forms/router.py:119`), the inbox (`responses/router.py:164`), the dashboard (`dashboard/common.py:86`, `router.py:49,89`), analytics (`analytics/router.py` through `C.visible_forms`) and the navigation counts.
- It selects whole `Form` rows, including `draft_schema` (often 20 to 200 KB of jsonb), then:
  - filters by permission (`access.can_see`) in Python;
  - applies status, folder, owner, tag and date filters in Python;
  - sorts in Python and slices.

**Effect.** A workspace with 2,000 forms moves tens of MB on every list call and every dashboard load. Today it is fine (dev: 1 form), but it scales with the customer's size, not with the page.

**Fix:**
1. Select only summary columns: `load_only(...)`, or `defer(Form.draft_schema)`.
2. Push the plain filters to SQL: status, folder_id, owner_id, `tags ?| :tags`, template_key, `updated_at` range, `deleted_at IS NULL` or not.
3. Keep permission scope in Python only where it needs the role. Most of it, "own", "shared" and "all", maps to `owner_id = :me OR id IN (SELECT form_id FROM form_grants WHERE user_id = :me) OR folder_id IN (...)`.
4. Sort and page in SQL. Natural sort on name: `ORDER BY lower(name) COLLATE "und-x-icu"` with numeric collation, or keep the Python sort only for the name column.

### Q7. N+1 schema reads in the inbox (Medium)

**Where.**
- `responses/router.py:79`: `schemas = {f.id: await service.response_schema(db, f) for f in forms}`.
- `response_schema()` makes up to two queries per form: `db.get(FormVersion, ...)`, then `lists_by_id` when the form has large lists.
- `analytics/router.py:150-152` does the same for the visible page only, which is acceptable.

**Fix:**
- Load the published versions of all forms in one query: `select(FormVersion).where(FormVersion.id.in_(published_ids))`.
- Collect every `option_set_id` across them for one `lists_by_id` call.
- Once Q1 is fixed, only the forms present on the page need a schema.

### Q8. Audit search and counts (Medium)

**Where.**
- `audit/queries.py:86-90`: `q` becomes `lower(cast(col AS text)) LIKE '%q%'` over `actor_name`, `actor_email`, `resource_name`, `host(ip)`, `city`, `request_id`, `action`.
- `page()` runs `count(*)` with the same conditions on every page (lines 129-135).

**Evidence.** EXPLAIN with `lower(actor_name) LIKE '%frank%'` used a **Seq Scan** on `audit_logs_p202610`, and an index scan on `tenant_id` with a filter on the others: every row of the workspace in every partition is read.

**Effect.** The audit trail grows fastest of all tables: every request that changes something, plus sign-in events. A workspace with 5M audit rows makes each search keystroke a full scan.

**Fix:**
- Default the period to the last 90 days when no `from` is given. The UI already shows a date range, and this gives pruning.
- Add a trigram index on a generated search column (below).
- Cap the count: `SELECT count(*) FROM (SELECT 1 ... LIMIT 10001) s`, showing "10,000+".
- `facets()` (lines 144-154) aggregates over the whole trail on each call. Cache it per workspace (Redis, 5 minutes), or bound it to the period.

### Q9. API usage `max(at)` without a time bound (Medium)

**Where.** `api_service/traffic.py:241-246`, in `load_usage()`: `SELECT ..., max(at) FROM api_request_logs WHERE tenant_id = :t GROUP BY GROUPING SETS ((endpoint_id), (token_id), (rule_id))`.

The other two queries in the function are bounded to 60 and 30 days. This one is not. EXPLAIN showed a `Merge Append` over all seven partitions, aggregating every API call the workspace ever made. It runs on every API services, tokens and access-rules page load (`service.py:210`).

**Fix:**
- Keep `last_used_at` on `api_tokens`, `api_endpoints` and `api_access_rules`. `api_tokens.last_used_at` is already written for client tokens.
- Update it at most once a minute per item, for example with a Redis flag or a `WHERE last_used_at < now() - interval '1 minute'` guard.
- Drop the unbounded query.

### Q10. Missing indexes for submit-time lookups (Medium)

**Where.**
- `public/router.py`: a known respondent (`respondent_kind`, `respondent_ref_id`), a device (`device_hash`), the same answers (`fingerprint`), all with `deleted_at IS NULL`.
- `dashboard/common.py:113-121`, `to_review`: `status = 'new'` per form, with no date bound.

**Evidence.**
- The respondent lookup used `ix_responses_identity (tenant_id, form_id, identity_email)` and **filtered** `respondent_kind` / `respondent_ref_id` row by row, so it reads every response of the form.
- `to_review` did the same with `status = 'new'`.

**Fix:** the index proposals below (I2 and I3). The existing device and fingerprint indexes are fine, but they would be smaller and exact as partial indexes `WHERE deleted_at IS NULL`.

### Q11. Reads on the primary inside write transactions (Medium)

**Where.**
- `GET /forms` (`forms/router.py:114`) opens `db_session("write")` and runs `sweep_trash()`, an `UPDATE ... RETURNING` on `forms`, on **every** list call.
- `GET /notifications` (`notifications/router.py:39-41`) opens a write session and runs `announce_due()` on every poll: a forms query on `closes_at`, plus `announce_once` inserts and `flush_digest`.
  - In the dev logs, `/notifications` is the most called route (198 of the last day's calls on one workspace), so this runs every few seconds per open tab.
- The gateway handles GETs in a write session (`api_service/gateway.py:314`).

**Effect:**
- Read traffic cannot move to replicas (CLAUDE.md rule 9).
- Every list takes row locks and WAL.
- The notifications poll multiplies by the number of open tabs.

**Fix:**
- Move `sweep_trash` and `announce_due` to Celery Beat jobs (per workspace, every 5 minutes and every minute).
- Make the two GETs read-only sessions.
- Add `ix_forms_closing (tenant_id, closes_at) WHERE status = 'published' AND deleted_at IS NULL` if the job stays per workspace.

### Q12. Outbox (Low)

**Where.** `app/core/events/tasks.py:20-42` and `outbox.py`.

The relay is sound:
- partial index `ix_event_outbox_unpublished (created_at) WHERE published_at IS NULL`;
- `FOR UPDATE SKIP LOCKED`, batch `LIMIT`, oldest first.

Two small points:
- It publishes and updates one row at a time: one `UPDATE` round trip per event. With a batch of 100 this is 100 statements every 2 seconds. Collect the published ids and run one `UPDATE ... WHERE (id, created_at) IN (...)`. Use publisher confirms on the channel so "published" is true.
- `processed_events` (one row per consumer per event) has no pruning anywhere in the code. It grows by (events × consumers) forever. Add a daily job that deletes, or marks and archives, rows older than the outbox replay window (7 days). The no-hard-delete rule is about tenant data; this is a technical dedup table, but the owner should confirm. Alternatively, partition it by month like the outbox and drop old partitions.

The EXPLAIN of the relay query could not be run: `formalie_app` has no `SELECT` on `event_outbox` (correct, per the grants).

### Q13. API log list (Low)

**Where.** `api_service/traffic.py:331-370`.

The query is bounded to 7 days by default (good) and uses `ix_api_request_logs_at (tenant_id, at)`. Two issues:
- The `q` search is `strpos(lower(path || ' ' || ip || ...), :q) > 0`, a filter over every row in the window.
- `count(*)` runs per page.

For a busy API (1M calls a week) each search is a scan of that week. Fixes:
- Cap the count as in Q8.
- If search on path matters, add a trigram index on `lower(path)` per partition (I6).

### Q14. Indexes the code does not use (Info)

- `api_tokens.ix_api_tokens_secret_hash` and `ix_api_tokens_previous_hash`: `gateway_auth.caller_token()` loads all the workspace's tokens and matches them in Python (`gateway_auth.py:86-89, 132-156`). That is fine for tens of tokens. Either query by hash (`WHERE tenant_id = :t AND (secret_hash = :h OR previous_hash = :h)`), which also removes the per-call load of every token, or drop the indexes.
- `pg_stat_user_indexes` on the dev DB shows `idx_scan = 0` for many indexes (`forms.uq_forms_public_key`, `ix_forms_tenant_owner`, `ix_api_endpoints_form`, ...). With an almost empty dev database this means nothing. Re-run the query below on production after a month, before dropping anything:

```sql
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes WHERE schemaname = 'formaly' AND idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;
```

## What is already good

- **Dashboard and analytics** (`dashboard/common.py:95-157`, `analytics/router.py`) aggregate in SQL:
  - `count(*)` grouped by form and day, bounded by the period;
  - `percentile_cont` for medians;
  - they use `ix_responses_form (tenant_id, form_id, submitted_at)`.
- **Audit list:**
  - filters, sort and paging are in SQL with `OFFSET` / `LIMIT`;
  - the export has a `limit`;
  - indexes cover the area, actor and resource filters.
- **API log list:** a default 7-day window, SQL paging, and indexes per endpoint, token and rule.
- **Notifications feed:** `LIMIT 100` on `(tenant_id, user_id, created_at)`.
- **Outbox:** a partial index with `SKIP LOCKED`.
- **Webhook retries:** a partial index on `next_retry_at WHERE status = 'retrying'`.
- **Response detail:** history is limited to 200 entries.
- **Tables and keys:** every tenant table leads its indexes with `tenant_id`, which matches the RLS predicate. Partitioning is in place for the four big insert-only tables.

## Index proposals (for a later migration; not created)

All on the partitioned parent, so PostgreSQL creates them per partition. On production, build each one with `CREATE INDEX CONCURRENTLY` on each partition first, then attach with `ALTER INDEX ... ATTACH PARTITION`, so nothing is locked during business hours. `pg_trgm` is a contrib extension shipped with PostgreSQL. Installing it is a database change the owner should approve.

```sql
-- I1. Response list default view and keyset paging, live rows only (replaces the ORDER BY in Q1)
CREATE INDEX ix_responses_form_live ON formaly.responses (tenant_id, form_id, submitted_at DESC, id DESC)
    WHERE deleted_at IS NULL;

-- I2. Known respondent check on submit (Q10)
CREATE INDEX ix_responses_respondent ON formaly.responses (tenant_id, form_id, respondent_kind, respondent_ref_id)
    WHERE deleted_at IS NULL AND respondent_ref_id IS NOT NULL;

-- I3. "To review" counts per form (dashboard, navigation, inbox chips) (Q10)
CREATE INDEX ix_responses_new ON formaly.responses (tenant_id, form_id)
    WHERE deleted_at IS NULL AND status = 'new';

-- I4. Exact identity / device / fingerprint lookups, live rows only (replace the three existing ones)
CREATE INDEX ix_responses_identity_live ON formaly.responses (tenant_id, form_id, identity_email)
    WHERE deleted_at IS NULL AND identity_email IS NOT NULL;
CREATE INDEX ix_responses_device_live ON formaly.responses (tenant_id, form_id, device_hash)
    WHERE deleted_at IS NULL AND device_hash IS NOT NULL;
CREATE INDEX ix_responses_fingerprint_live ON formaly.responses (tenant_id, form_id, fingerprint)
    WHERE deleted_at IS NULL;
-- then DROP INDEX ix_responses_identity, ix_responses_device, ix_responses_fingerprint

-- I5. Tag filter and tag counts (Q1)
CREATE INDEX ix_responses_tags ON formaly.responses USING gin (tags jsonb_path_ops) WHERE deleted_at IS NULL;

-- I6. Near-duplicate email on submit and response search (Q1, Q2); needs pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_responses_identity_trgm ON formaly.responses USING gin (identity_email gin_trgm_ops)
    WHERE deleted_at IS NULL AND identity_email IS NOT NULL;
-- with a new column responses.search_text (lower case: title, email, answers as text), kept by the app:
-- CREATE INDEX ix_responses_search_trgm ON formaly.responses USING gin (search_text gin_trgm_ops)
--     WHERE deleted_at IS NULL;

-- I7. Audit search (Q8): a generated column so one index serves the seven fields
-- ALTER TABLE formaly.audit_logs ADD COLUMN search text GENERATED ALWAYS AS (lower(
--     coalesce(actor_name,'') || ' ' || coalesce(actor_email,'') || ' ' || coalesce(resource_name,'') || ' ' ||
--     coalesce(host(ip),'') || ' ' || coalesce(city,'') || ' ' || coalesce(request_id,'') || ' ' || action)) STORED;
CREATE INDEX ix_audit_logs_search_trgm ON formaly.audit_logs USING gin (search gin_trgm_ops);

-- I8. Forms list filters pushed to SQL (Q6)
CREATE INDEX ix_forms_live ON formaly.forms (tenant_id, status, updated_at DESC) WHERE deleted_at IS NULL AND purged_at IS NULL;
CREATE INDEX ix_forms_trash ON formaly.forms (tenant_id, deleted_at) WHERE deleted_at IS NOT NULL AND purged_at IS NULL;
CREATE INDEX ix_forms_tags ON formaly.forms USING gin (tags jsonb_path_ops) WHERE purged_at IS NULL;  -- if tags is jsonb
CREATE INDEX ix_forms_closing ON formaly.forms (tenant_id, closes_at) WHERE status = 'published' AND deleted_at IS NULL;

-- I9. API gateway token lookup by hash (Q14), only if the code moves to querying by hash; otherwise drop the two
-- existing hash indexes. The existing ones already fit: (tenant_id, secret_hash), (tenant_id, previous_hash).

-- I10. API log path search (Q13), optional
CREATE INDEX ix_api_request_logs_path_trgm ON formaly.api_request_logs USING gin (lower(path) gin_trgm_ops);
```

Check `forms.tags`'s column type before I8 (the model is `JSONB` in `forms/models.py`; if it is `text[]`, use a plain `gin (tags)`). Each index costs write time on submit. I1 to I4 replace or narrow existing ones, so the net cost on `responses` is about two extra indexes (I5, I6).

## Order of work suggested

1. Q2 and Q4: they affect every respondent and get worse with every response.
2. Q1 and Q3: lists in SQL, with I1, I3 and I5.
3. Q11: move `sweep_trash` and `announce_due` to Beat, which takes reads off the primary.
4. Q6 to Q9: forms in SQL, batch schema reads, bounded audit and usage queries.
5. Re-run this review with production-like data: seed one workspace with 1M responses (a script that inserts through the app's model in batches, in the test database, never production) and run `EXPLAIN (ANALYZE, BUFFERS)` on the list, submit and gateway queries.

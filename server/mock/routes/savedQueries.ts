/**
 * Mock saved queries (F12 M4 part 2, docs/API-CONTRACT.md → Query editor). Admins only until F22.
 *
 *   GET    /saved-queries              list (q, sort, filter[datasource], filter[scope]=mine|shared, filter[kind]=read|change)
 *   GET    /saved-queries/insights     counts, runs in the last 30 days, read vs change
 *   GET    /saved-queries/:id          one
 *   POST   /saved-queries              { name, description?, sql (one statement or a script), datasource_id, shared }
 *   PATCH  /saved-queries/:id          { name?, description?, sql?, shared? } (its owner only, FRM-DEST-1027)
 *   DELETE /saved-queries/:id          (its owner only)
 *
 * Everyone sees their own and the shared ones; only the person who saved one changes it.
 */
import { z } from 'zod'
import type { SavedQueryInsights } from '#shared/types/query'
import { scriptKind, splitStatements } from '#shared/utils/datasources/sql'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok, paginate, filtersOf } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { dataSourcesOf } from '../data/dataSourceStore'
import { saveSavedQueries, savedQueriesOf, toSavedQuery, visibleTo } from '../data/savedQueryStore'

const DAY = 86_400_000
const input = z.object({
  name: z.string().trim().min(1).max(120),
  description: z.string().trim().max(500).nullish(),
  sql: z.string().min(1).max(100_000),
  datasource_id: z.string(),
  shared: z.boolean().default(false),
})

export const listSavedQueries = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAdmin(event)
  const filter = filtersOf(query)
  let rows = visibleTo(tenant, user).map(item => toSavedQuery(tenant, user, item))
  if (filter.datasource) rows = rows.filter(row => filter.datasource!.split(',').includes(row.datasource.id))
  if (filter.scope) rows = rows.filter(row => filter.scope!.split(',').some(scope => (scope === 'mine' ? row.mine : scope === 'shared' ? row.shared : true)))
  if (filter.kind) rows = rows.filter(row => filter.kind!.split(',').includes(row.kind === 'read' ? 'read' : 'change'))
  const sort = typeof query.sort === 'string' && query.sort ? query.sort : '-updated_at'
  const desc = sort.startsWith('-')
  const key = (desc ? sort.slice(1) : sort) as 'name' | 'updated_at' | 'run_count' | 'last_run_at'
  rows.sort((a, b) => {
    const x = a[key] ?? ''
    const y = b[key] ?? ''
    const order = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })
    return desc ? -order : order
  })
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.name} ${row.description ?? ''} ${row.sql} ${row.datasource.name}`.toLowerCase().includes(q.toLowerCase()))
  return ok(data, meta)
})

export const savedQueryInsights = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const items = visibleTo(tenant, user).map(item => toSavedQuery(tenant, user, item))
  const daily = Array.from({ length: 30 }, (_, index) => {
    const date = new Date(Date.now() - (29 - index) * DAY).toISOString().slice(0, 10)
    return { date, count: items.reduce((sum, item) => sum + (item.daily.find(entry => entry.date === date)?.count ?? 0), 0) }
  })
  const runs = daily.reduce((sum, entry) => sum + entry.count, 0)
  const insights: SavedQueryInsights = {
    total: items.length,
    mine: items.filter(item => item.mine).length,
    shared: items.filter(item => item.shared).length,
    runs_30d: runs,
    previous_30d: Math.round(runs * 0.82),
    daily,
    by_kind: { read: items.filter(item => item.kind === 'read').length, change: items.filter(item => item.kind !== 'read').length },
  }
  return ok(insights)
})

function find(tenant: Parameters<typeof savedQueriesOf>[0], user: Parameters<typeof visibleTo>[1], id: string | undefined) {
  const item = visibleTo(tenant, user).find(entry => entry.id === id)
  if (!item) throw new MockError('FRM-GEN-1004')
  return item
}

export const getSavedQuery = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  return ok(toSavedQuery(tenant, user, find(tenant, user, getRouterParam(event, 'id'))))
})

export const createSavedQuery = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const values = parseBody(input, body)
  const source = dataSourcesOf(tenant).find(item => item.id === values.datasource_id)
  if (!source) throw new MockError('FRM-GEN-1002', [{ field: 'datasource_id', message: 'required' }])
  // A saved query may hold a script (several statements); the editor runs one at a time
  if (!splitStatements(values.sql).length) throw new MockError('FRM-GEN-1002', [{ field: 'sql', message: 'required' }])
  const now = new Date().toISOString()
  const item = { id: crypto.randomUUID(), name: values.name, description: values.description || null, sql: values.sql.trim(), datasource_id: source.id, shared: values.shared, owner_id: user.id, runs: {}, last_run_at: null, created_at: now, updated_at: now }
  savedQueriesOf(tenant).unshift(item)
  saveSavedQueries()
  recordAudit(event, tenant, { action: 'data.saved_query_saved', actor: actorOf(user), resource: { type: 'data_source', id: source.id, name: source.name }, metadata: { name: item.name, kind: scriptKind(item.sql), shared: String(item.shared) } })
  return ok(toSavedQuery(tenant, user, item), {}, 201)
})

export const updateSavedQuery = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const item = find(tenant, user, getRouterParam(event, 'id'))
  if (item.owner_id !== user.id) throw new MockError('FRM-DEST-1027')
  const values = parseBody(input.partial().omit({ datasource_id: true }), body)
  if (values.sql !== undefined && !splitStatements(values.sql).length) throw new MockError('FRM-GEN-1002', [{ field: 'sql', message: 'required' }])
  Object.assign(item, {
    ...(values.name !== undefined ? { name: values.name } : {}),
    ...(values.description !== undefined ? { description: values.description || null } : {}),
    ...(values.sql !== undefined ? { sql: values.sql.trim() } : {}),
    ...(values.shared !== undefined ? { shared: values.shared } : {}),
    updated_at: new Date().toISOString(),
  })
  saveSavedQueries()
  const source = dataSourcesOf(tenant).find(entry => entry.id === item.datasource_id)
  recordAudit(event, tenant, { action: 'data.saved_query_saved', actor: actorOf(user), resource: { type: 'data_source', id: item.datasource_id, name: source?.name ?? '' }, metadata: { name: item.name, kind: scriptKind(item.sql), shared: String(item.shared) } })
  return ok(toSavedQuery(tenant, user, item))
})

export const deleteSavedQuery = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const item = find(tenant, user, getRouterParam(event, 'id'))
  if (item.owner_id !== user.id) throw new MockError('FRM-DEST-1027')
  const list = savedQueriesOf(tenant)
  list.splice(list.indexOf(item), 1)
  saveSavedQueries()
  const source = dataSourcesOf(tenant).find(entry => entry.id === item.datasource_id)
  recordAudit(event, tenant, { action: 'data.saved_query_deleted', actor: actorOf(user), resource: { type: 'data_source', id: item.datasource_id, name: source?.name ?? '' }, metadata: { name: item.name } })
  return ok({ deleted: true })
})

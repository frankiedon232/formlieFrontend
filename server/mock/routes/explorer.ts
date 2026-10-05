/**
 * Mock database explorer API (F12 M3, docs/API-CONTRACT.md → Database explorer). Admins only until
 * F22. Everything runs on Formalie's servers through the connection (never from the browser);
 * a connection that isn't working answers with its error, a disabled one with FRM-DEST-1009.
 *
 *   GET  /datasources/:id/explorer/tables                     the tree: schemas, tables, columns
 *   GET  /datasources/:id/explorer/structure?schema&table     columns, keys, indexes, definition
 *   GET  /datasources/:id/explorer/rows?schema&table&…        rows (paged, sorted, searched, filtered)
 *   GET  /datasources/:id/explorer/facets?schema&table        values of low-variety columns (filters)
 *   POST /datasources/:id/explorer/exports                    a table or the filtered rows as CSV / XLSX
 *   GET  /explorer-exports/:id                                its progress
 *   POST /explorer-exports/:id/link                           a one-time private download link (5 min)
 *   GET  /datasource-exports/:token                           the file (plain download)
 */
import { z } from 'zod'
import type { DatabaseTable } from '#shared/types/destinations'
import type { ColumnFacet, TableExport, TableRow, TableStructure } from '#shared/types/explorer'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, tenantOf } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { xlsx } from '../core/xlsx'
import { rowsOf, structureOf } from '../data/databaseRows'
import { tablesOf } from '../data/databaseTables'
import { dataSourcesOf, statusOf, type StoredDataSource } from '../data/dataSourceStore'
import { createdTablesOn } from '../data/destinationStore'
import type { MockTenant } from '../data/tenants'
import { csvCell } from './responseExports'

/** The connection, if it can be used right now (the real backend would just fail to connect). */
function usable(tenant: MockTenant, id: string | undefined): StoredDataSource {
  const source = dataSourcesOf(tenant).find(item => item.id === id)
  if (!source) throw new MockError('FRM-GEN-1004')
  const status = statusOf(source)
  if (status === 'disabled') throw new MockError('FRM-DEST-1009')
  if (status === 'failing') throw new MockError((source.last_test?.steps.find(step => step.error_code)?.error_code as 'FRM-DEST-1001' | undefined) ?? 'FRM-DEST-1001')
  return source
}

function tableOf(tenant: MockTenant, source: StoredDataSource, query: Record<string, unknown>): { tables: DatabaseTable[]; structure: TableStructure } {
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  const table = tables.find(item => item.schema === String(query.schema ?? '') && item.name === String(query.table ?? ''))
  if (!table) throw new MockError('FRM-GEN-1004')
  return { tables, structure: structureOf(tenant, source, tables, table) }
}

const text = (value: unknown) => (value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value))

/** Rows after the search (any column) and the filters (`filter[column]=a,b`), sorted. */
function select(rows: TableRow[], query: Record<string, unknown>): TableRow[] {
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''
  const filter = (query.filter ?? {}) as Record<string, unknown>
  let list = rows.filter(row => (!q || Object.entries(row).some(([key, value]) => key !== '__key' && text(value).toLowerCase().includes(q))) && Object.entries(filter).every(([column, wanted]) => typeof wanted !== 'string' || !wanted || wanted.split(',').includes(text(row[column]))))
  const sort = typeof query.sort === 'string' ? query.sort : ''
  if (sort) {
    const desc = sort.startsWith('-')
    const key = desc ? sort.slice(1) : sort
    list = [...list].sort((a, b) => {
      const x = a[key]
      const y = b[key]
      if (x == null && y == null) return 0
      if (x == null) return 1
      if (y == null) return -1
      const order = typeof x === 'number' && typeof y === 'number' ? x - y : text(x).localeCompare(text(y), undefined, { numeric: true })
      return desc ? -order : order
    })
  }
  return list
}

/** GET /datasources/:id/explorer/tables, the tree (fails like the connection does). */
export const explorerTables = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  return ok(tablesOf(source, createdTablesOn(tenant, source)))
})

export const tableStructure = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  return ok(tableOf(tenant, usable(tenant, getRouterParam(event, 'id')), query).structure)
})

export const tableRows = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  const { tables, structure } = tableOf(tenant, source, query)
  const rows = select(rowsOf(tenant, source, tables, structure), query)
  // The order is already applied; paginate only pages.
  const { data, meta } = paginate(rows, { ...query, q: undefined, sort: undefined })
  return ok(data, meta)
})

export const tableFacets = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  const { tables, structure } = tableOf(tenant, source, query)
  const rows = rowsOf(tenant, source, tables, structure)
  const facets: ColumnFacet[] = []
  for (const column of structure.columns) {
    if (column.primary || /JSON|CLOB|TEXT|MAX/i.test(column.type)) continue
    const counts = new Map<string, number>()
    for (const row of rows) {
      const value = row[column.name]
      if (value == null || value === '') continue
      counts.set(text(value), (counts.get(text(value)) ?? 0) + 1)
      if (counts.size > 12) break
    }
    if (counts.size >= 2 && counts.size <= 12) facets.push({ column: column.name, values: [...counts].sort((a, b) => b[1] - a[1]).map(([value, count]) => ({ value, count })) })
  }
  return ok(facets)
})

// ── Exports ──────────────────────────────────────────────────────────────────────────────

interface StoredTableExport extends TableExport {
  tenantId: string
  started: number
  speed: number
  bytes: Uint8Array | string
  file_name: string
}
const exports = new Map<string, StoredTableExport>()
const links = new Map<string, { exportId: string; expires: number }>()
const LINK_MS = 5 * 60 * 1000

const view = (item: StoredTableExport): TableExport => {
  const done = Math.min(item.rows, Math.floor(((Date.now() - item.started) / 1000) * item.speed))
  const ready = done >= item.rows
  return { id: item.id, table: item.table, format: item.format, status: ready ? 'ready' : 'running', progress: item.rows ? Math.round((done / item.rows) * 100) : 100, rows: item.rows, size: ready ? (typeof item.bytes === 'string' ? item.bytes.length : item.bytes.byteLength) : null }
}

export const startTableExport = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  const input = parseBody(z.object({ schema: z.string(), table: z.string(), format: z.enum(['csv', 'xlsx']), q: z.string().optional(), sort: z.string().optional(), filter: z.record(z.string(), z.string()).optional() }), body)
  const { tables, structure } = tableOf(tenant, source, input)
  const rows = select(rowsOf(tenant, source, tables, structure), input)
  const head = structure.columns.map(column => column.name)
  const lines = rows.map(row => head.map(name => text(row[name])))
  const name = `${structure.name}.${input.format}`
  const bytes = input.format === 'xlsx' ? xlsx(structure.name.slice(0, 31), [head, ...lines]) : String.fromCharCode(0xfeff) + [head, ...lines].map(line => line.map(csvCell).join(',')).join('\r\n')
  const item: StoredTableExport = { id: crypto.randomUUID(), table: `${structure.schema}.${structure.name}`, format: input.format, status: 'running', progress: 0, rows: rows.length, size: null, tenantId: tenant.id, started: Date.now(), speed: Math.max(400, rows.length / 3), bytes, file_name: name }
  exports.set(item.id, item)
  recordAudit(event, tenant, { action: 'data.table_exported', actor: actorOf(user), resource: { type: 'data_source', id: source.id, name: source.name }, metadata: { table: item.table, format: input.format, rows: String(rows.length), filtered: input.q || Object.keys(input.filter ?? {}).length ? 'yes' : 'no' } })
  return ok(view(item), {}, 201)
})

function findExport(tenant: MockTenant, id: string | undefined) {
  const item = id ? exports.get(id) : undefined
  if (!item || item.tenantId !== tenant.id) throw new MockError('FRM-EXP-1001')
  return item
}

export const getTableExport = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  return ok(view(findExport(tenant, getRouterParam(event, 'id'))))
})

export const tableExportLink = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const item = findExport(tenant, getRouterParam(event, 'id'))
  if (view(item).status !== 'ready') throw new MockError('FRM-GEN-1002', [{ field: 'status', message: 'The file is still being made.' }])
  const token = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '')
  links.set(token, { exportId: item.id, expires: Date.now() + LINK_MS })
  return ok({ url: `/api/v1/datasource-exports/${token}`, expires_at: new Date(Date.now() + LINK_MS).toISOString() })
})

export const downloadTableExport = defineEventHandler(event => {
  const token = getRouterParam(event, 'token') ?? ''
  const link = links.get(token)
  const item = link ? exports.get(link.exportId) : undefined
  const host = tenantOf(event)
  const isLocal = host.context.kind === 'manage' && host.context.reason === 'local'
  if (!link || !item || link.expires < Date.now() || (!isLocal && host.tenant?.id !== item.tenantId)) {
    setResponseStatus(event, 410)
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    return 'This download link has expired. Export the table again from the database explorer.'
  }
  links.delete(token)
  setHeader(event, 'content-type', item.format === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv; charset=utf-8')
  setHeader(event, 'content-disposition', `attachment; filename="${item.file_name}"`)
  setHeader(event, 'cache-control', 'no-store')
  return item.bytes
})

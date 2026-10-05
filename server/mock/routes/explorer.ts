/**
 * Mock database explorer API (F12 M3, docs/API-CONTRACT.md → Database explorer). Admins only until
 * F22. Everything runs on Formalie's servers through the connection (never from the browser);
 * a connection that isn't working answers with its error, a disabled one with FRM-DEST-1009.
 *
 *   GET  /datasources/:id/explorer/tables                     the tree: schemas, tables, columns
 *   GET  /datasources/:id/explorer/structure?schema&table     columns, keys, indexes, definition
 *   GET  /datasources/:id/explorer/rows?schema&table&…        rows (paged, sorted, searched, filtered)
 *   GET  /datasources/:id/explorer/facets?schema&table        values of low-variety columns (filters)
 *   POST /datasources/:id/explorer/exports                    a table or the filtered rows as CSV / XLSX / JSON / SQL
 *   GET  /explorer-exports/:id                                its progress
 *   POST /explorer-exports/:id/link                           a one-time private download link (5 min)
 *   GET  /datasource-exports/:token                           the file (plain download)
 *   POST · PATCH · DELETE /datasources/:id/explorer/rows      add, change, delete a row (Full access, their tables)
 */
import { z } from 'zod'
import type { H3Event } from 'h3'
import { parseValue } from '#shared/utils/datasources/values'
import { jsonExport, sqlInsertScript } from '#shared/utils/datasources/exportFormats'
import type { DatabaseTable } from '#shared/types/destinations'
import type { ColumnFacet, TableExport, TableRow, TableStructure } from '#shared/types/explorer'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin, tenantOf } from '../core/auth'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { xlsx } from '../core/xlsx'
import { changesOf, rowsOf, structureOf } from '../data/databaseRows'
import { tablesOf } from '../data/databaseTables'
import { dataSourcesOf, statusOf, type StoredDataSource } from '../data/dataSourceStore'
import { createdTablesOn } from '../data/destinationStore'
import type { MockTenant, MockUser } from '../data/tenants'
import { csvCell } from './responseExports'

/** The connection, if it can be used right now (the real backend would just fail to connect). */
function usable(tenant: MockTenant, id: string | undefined): StoredDataSource {
  const source = dataSourcesOf(tenant).find(item => item.id === id)
  if (!source) throw new MockError('FRM-GEN-1004')
  const status = statusOf(source)
  if (status === 'disabled') throw new MockError('FRM-DEST-1009')
  if (status === 'failing')
    throw new MockError(
      (source.last_test?.steps.find(step => step.error_code)?.error_code as 'FRM-DEST-1001' | undefined) ??
        'FRM-DEST-1001',
    )
  return source
}

function tableOf(
  tenant: MockTenant,
  source: StoredDataSource,
  query: Record<string, unknown>,
): { tables: DatabaseTable[]; structure: TableStructure } {
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  const table = tables.find(
    item => item.schema === String(query.schema ?? '') && item.name === String(query.table ?? ''),
  )
  if (!table) throw new MockError('FRM-GEN-1004')
  return { tables, structure: structureOf(tenant, source, tables, table) }
}

const text = (value: unknown) =>
  value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)

/** Rows after the search (any column) and the filters (`filter[column]=a,b`), sorted. */
function select(rows: TableRow[], query: Record<string, unknown>): TableRow[] {
  const q = typeof query.q === 'string' ? query.q.trim().toLowerCase() : ''
  const filter = (query.filter ?? {}) as Record<string, unknown>
  let list = rows.filter(
    row =>
      (!q ||
        Object.entries(row).some(
          ([key, value]) => key !== '__key' && text(value).toLowerCase().includes(q),
        )) &&
      Object.entries(filter).every(
        ([column, wanted]) =>
          typeof wanted !== 'string' || !wanted || wanted.split(',').includes(text(row[column])),
      ),
  )
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
      const order =
        typeof x === 'number' && typeof y === 'number'
          ? x - y
          : text(x).localeCompare(text(y), undefined, { numeric: true })
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
    if (counts.size >= 2 && counts.size <= 12)
      facets.push({
        column: column.name,
        values: [...counts].sort((a, b) => b[1] - a[1]).map(([value, count]) => ({ value, count })),
      })
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
  return {
    id: item.id,
    table: item.table,
    format: item.format,
    status: ready ? 'ready' : 'running',
    progress: item.rows ? Math.round((done / item.rows) * 100) : 100,
    rows: item.rows,
    size: ready ? (typeof item.bytes === 'string' ? item.bytes.length : item.bytes.byteLength) : null,
  }
}

export const startTableExport = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  const input = parseBody(
    z.object({
      schema: z.string(),
      table: z.string(),
      format: z.enum(['csv', 'xlsx', 'json', 'sql']),
      q: z.string().optional(),
      sort: z.string().optional(),
      filter: z.record(z.string(), z.string()).optional(),
    }),
    body,
  )
  const { tables, structure } = tableOf(tenant, source, input)
  const rows = select(rowsOf(tenant, source, tables, structure), input)
  const head = structure.columns.map(column => column.name)
  const lines = rows.map(row => head.map(name => text(row[name])))
  const name = `${structure.name}.${input.format}`
  const bytes =
    input.format === 'xlsx'
      ? xlsx(structure.name.slice(0, 31), [head, ...lines])
      : input.format === 'json'
        ? jsonExport(structure.columns, rows)
        : input.format === 'sql'
          ? sqlInsertScript(source.engine, { schema: structure.schema, table: structure.name }, structure.columns, rows)
          : String.fromCharCode(0xfeff) + [head, ...lines].map(line => line.map(csvCell).join(',')).join('\r\n')
  const item: StoredTableExport = {
    id: crypto.randomUUID(),
    table: `${structure.schema}.${structure.name}`,
    format: input.format,
    status: 'running',
    progress: 0,
    rows: rows.length,
    size: null,
    tenantId: tenant.id,
    started: Date.now(),
    speed: Math.max(400, rows.length / 3),
    bytes,
    file_name: name,
  }
  exports.set(item.id, item)
  recordAudit(event, tenant, {
    action: 'data.table_exported',
    actor: actorOf(user),
    resource: { type: 'data_source', id: source.id, name: source.name },
    metadata: {
      table: item.table,
      format: input.format,
      rows: String(rows.length),
      filtered: input.q || Object.keys(input.filter ?? {}).length ? 'yes' : 'no',
    },
  })
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
  if (view(item).status !== 'ready')
    throw new MockError('FRM-GEN-1002', [{ field: 'status', message: 'The file is still being made.' }])
  const token = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '')
  links.set(token, { exportId: item.id, expires: Date.now() + LINK_MS })
  return ok({
    url: `/api/v1/datasource-exports/${token}`,
    expires_at: new Date(Date.now() + LINK_MS).toISOString(),
  })
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
  setHeader(
    event,
    'content-type',
    {
      xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      csv: 'text/csv; charset=utf-8',
      json: 'application/json; charset=utf-8',
      sql: 'application/sql; charset=utf-8',
    }[item.format],
  )
  setHeader(event, 'content-disposition', `attachment; filename="${item.file_name}"`)
  setHeader(event, 'cache-control', 'no-store')
  return item.bytes
})

// ── Changing rows (Full access, the organisation's own tables only) ─────────────────────

/** The table, if its rows may be changed here (FRM-DEST-1019 otherwise). */
function writable(tenant: MockTenant, source: StoredDataSource, query: Record<string, unknown>) {
  const found = tableOf(tenant, source, query)
  if (found.structure.read_only)
    throw new MockError('FRM-DEST-1019', [{ field: 'table', message: found.structure.read_only }])
  return found
}

/** Typed values for a row, or FRM-GEN-1002 with a problem per column. */
function typedRow(
  structure: TableStructure,
  input: Record<string, unknown>,
  partial: boolean,
): Record<string, unknown> {
  const values: Record<string, unknown> = {}
  const problems: { field: string; message: string }[] = []
  for (const column of structure.columns) {
    if (partial && (!(column.name in input) || column.primary)) continue
    const parsed = parseValue(column, input[column.name])
    if ('problem' in parsed) problems.push({ field: column.name, message: parsed.problem })
    else values[column.name] = parsed.value
  }
  if (problems.length) throw new MockError('FRM-GEN-1002', problems)
  return values
}

/** The next value of an auto-numbered key. */
const nextKey = (rows: TableRow[], column: string) =>
  rows.reduce((max, row) => Math.max(max, Number(row[column]) || 0), 0) + 1
const keyFor = (structure: TableStructure, row: Record<string, unknown>) =>
  structure.primary_key.map(name => String(row[name] ?? '')).join('|')
/** Which row changed, never its values (no result data in logs). */
const rowAudit = (
  event: H3Event,
  tenant: MockTenant,
  user: MockUser,
  action: 'data.row_inserted' | 'data.row_updated' | 'data.row_deleted',
  source: StoredDataSource,
  structure: TableStructure,
  key: string,
) =>
  recordAudit(event, tenant, {
    action,
    actor: actorOf(user),
    resource: { type: 'data_source', id: source.id, name: source.name },
    metadata: { table: `${structure.schema}.${structure.name}`, key },
  })

export const insertRow = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(
    z.object({ schema: z.string(), table: z.string(), values: z.record(z.string(), z.unknown()) }),
    body,
  )
  const source = usable(tenant, getRouterParam(event, 'id'))
  const { tables, structure } = writable(tenant, source, input)
  const rows = rowsOf(tenant, source, tables, structure)
  const values = typedRow(structure, input.values, false)
  for (const name of structure.primary_key) {
    const column = structure.columns.find(item => item.name === name)!
    if (values[name] == null && column.has_default) values[name] = nextKey(rows, name)
  }
  const key = keyFor(structure, values)
  if (rows.some(row => row.__key === key))
    throw new MockError('FRM-DEST-1018', [{ field: structure.primary_key[0] ?? 'key', message: 'taken' }])
  const row = { ...values, __key: key } as TableRow
  changesOf(source, structure).inserted.push(row)
  rowAudit(event, tenant, user, 'data.row_inserted', source, structure, key)
  return ok(row, {}, 201)
})

export const updateRow = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(
    z.object({
      schema: z.string(),
      table: z.string(),
      key: z.string(),
      values: z.record(z.string(), z.unknown()),
    }),
    body,
  )
  const source = usable(tenant, getRouterParam(event, 'id'))
  const { tables, structure } = writable(tenant, source, input)
  const current = rowsOf(tenant, source, tables, structure).find(row => row.__key === input.key)
  if (!current) throw new MockError('FRM-GEN-1004')
  const values = typedRow(structure, input.values, true)
  const changes = changesOf(source, structure)
  const inserted = changes.inserted.find(row => row.__key === input.key)
  if (inserted) Object.assign(inserted, values)
  else changes.updated[input.key] = { ...changes.updated[input.key], ...values }
  rowAudit(event, tenant, user, 'data.row_updated', source, structure, input.key)
  return ok({ ...current, ...values })
})

export const deleteRow = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usable(tenant, getRouterParam(event, 'id'))
  const { tables, structure } = writable(tenant, source, query)
  const key = String(query.key ?? '')
  if (!rowsOf(tenant, source, tables, structure).some(row => row.__key === key))
    throw new MockError('FRM-GEN-1004')
  const changes = changesOf(source, structure)
  changes.inserted = changes.inserted.filter(row => row.__key !== key)
  changes.deleted.push(key)
  rowAudit(event, tenant, user, 'data.row_deleted', source, structure, key)
  return ok({ deleted: true })
})

/**
 * Mock Query editor API (F12 M4, docs/API-CONTRACT.md → Query editor). Admins only until F22.
 *
 *   POST   /datasources/:id/query            { sql, params?, page?, page_size?, confirm? } → QueryResult
 *   GET    /datasources/:id/query-history    this person's recent statements on the connection (50)
 *   DELETE /datasources/:id/query-history    ?id= one, or all of them
 *
 * One statement per run (FRM-DEST-1026). Reading: paged, counted up to 10,000. Changing rows or
 * structure: Full access only (FRM-DEST-1024), never Formalie's response tables (FRM-DEST-1019),
 * and only after a confirm (FRM-DEST-1023 says what it will do). Database problems: FRM-DEST-1025
 * with the database's message and the position. Every run is recorded in the audit trail (the
 * statement, never its result rows).
 */
import { z } from 'zod'
import type { QueryHistoryItem, QueryResult } from '#shared/types/query'
import { splitStatements, statementKind, tablesIn } from '#shared/utils/datasources/sql'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { tablesOf } from '../data/databaseTables'
import { createdTablesOn } from '../data/destinationStore'
import { planChange, resolveTable, runSelect } from '../data/queryEngine'
import { usableSource } from './explorer'

const COUNT_CAP = 10_000
const history = new Map<string, QueryHistoryItem[]>()
const historyKey = (tenantId: string, userId: string, sourceId: string) => `${tenantId}:${userId}:${sourceId}`

export const runQuery = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usableSource(tenant, getRouterParam(event, 'id'))
  const input = parseBody(
    z.object({
      sql: z.string().max(100_000),
      params: z.record(z.string(), z.string()).optional(),
      page: z.coerce.number().int().min(1).default(1),
      page_size: z.coerce.number().int().min(1).max(100).default(50),
      confirm: z.boolean().optional(),
    }),
    body,
  )
  const statements = splitStatements(input.sql)
  if (!statements.length) throw new MockError('FRM-GEN-1002', [{ field: 'sql', message: 'required' }])
  if (statements.length > 1) throw new MockError('FRM-DEST-1026', [{ field: 'sql', message: String(statements.length) }])
  const sql = statements[0]!.text
  const kind = statementKind(sql)
  const params = input.params ?? {}
  const started = Date.now()
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  const record = (item: Omit<QueryHistoryItem, 'id' | 'sql' | 'kind' | 'ran_at'>) => {
    const key = historyKey(tenant.id, user.id, source.id)
    history.set(key, [{ id: crypto.randomUUID(), sql, kind, ran_at: new Date().toISOString(), ...item }, ...(history.get(key) ?? [])].slice(0, 50))
  }
  const confirmNeeded = (tablesNamed: string[], estimate: number | null) =>
    new MockError('FRM-DEST-1023', [
      { field: 'kind', message: kind },
      { field: 'tables', message: tablesNamed.join(',') },
      { field: 'estimate', message: estimate == null ? '' : String(estimate) },
    ])

  try {
    let result: QueryResult
    const duration = () => Math.max(3, Date.now() - started) + (sql.length % 37)
    if (kind === 'read') {
      const read = runSelect(tenant, source, tables, sql, params)
      const total = read.rows.length
      const page = read.rows.slice((input.page - 1) * input.page_size, input.page * input.page_size)
      result = { run_id: crypto.randomUUID(), kind, columns: read.columns, rows: page, page: input.page, page_size: input.page_size, total: Math.min(total, COUNT_CAP), capped: total > COUNT_CAP, rows_affected: null, duration_ms: duration(), notice: null }
    } else {
      if (source.access.other !== 'read_write') throw new MockError('FRM-DEST-1024', [{ field: 'access', message: source.access.other }])
      if (kind === 'insert' || kind === 'update' || kind === 'delete') {
        const plan = planChange(tenant, source, tables, sql, params)
        if (plan.resolved.table.formalie) throw new MockError('FRM-DEST-1019', [{ field: 'table', message: 'response_table' }])
        if (!input.confirm) throw confirmNeeded([`${plan.resolved.table.schema}.${plan.resolved.table.name}`], plan.estimate)
        const affected = plan.apply()
        result = { run_id: crypto.randomUUID(), kind, columns: [], rows: [], page: 1, page_size: input.page_size, total: null, capped: false, rows_affected: affected, duration_ms: duration(), notice: null }
      } else {
        // Structure and other statements: checked, confirmed, not applied in the preview.
        const named = tablesIn(sql)
        for (const name of named) {
          const resolved = (() => {
            try {
              return resolveTable(tenant, source, tables, name, 0)
            } catch {
              return null
            }
          })()
          if (resolved?.table.formalie) throw new MockError('FRM-DEST-1019', [{ field: 'table', message: 'response_table' }])
        }
        if (!input.confirm) throw confirmNeeded(named, null)
        result = { run_id: crypto.randomUUID(), kind, columns: [], rows: [], page: 1, page_size: input.page_size, total: null, capped: false, rows_affected: 0, duration_ms: duration(), notice: 'structure_preview' }
      }
    }
    record({ duration_ms: result.duration_ms, rows: result.total ?? result.rows_affected, ok: true, error_code: null })
    recordAudit(event, tenant, {
      action: 'data.query_run',
      actor: actorOf(user),
      resource: { type: 'data_source', id: source.id, name: source.name },
      metadata: { kind, statement: sql.slice(0, 300), rows: String(result.total ?? result.rows_affected ?? 0), duration_ms: String(result.duration_ms) },
    })
    return ok(result)
  } catch (error) {
    // A confirm request isn't a run; everything else is kept in the history with its problem.
    if (error instanceof MockError && error.code !== 'FRM-DEST-1023') record({ duration_ms: null, rows: null, ok: false, error_code: error.code })
    throw error
  }
})

export const queryHistory = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usableSource(tenant, getRouterParam(event, 'id'))
  return ok(history.get(historyKey(tenant.id, user.id, source.id)) ?? [])
})

export const clearQueryHistory = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usableSource(tenant, getRouterParam(event, 'id'))
  const key = historyKey(tenant.id, user.id, source.id)
  const id = typeof query.id === 'string' ? query.id : null
  history.set(key, id ? (history.get(key) ?? []).filter(item => item.id !== id) : [])
  return ok({ cleared: true })
})

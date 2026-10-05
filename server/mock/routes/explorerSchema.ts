/**
 * Mock structure changes in the explorer (F12 M3, owner 2026-10-05): the organisation's own
 * tables with Full access only, never Formalie's response tables (FRM-DEST-1019) and never views.
 *
 *   POST /datasources/:id/explorer/tables     create a table { schema, name, columns }
 *   POST /datasources/:id/explorer/changes    { schema, table, change } (add / change / delete a
 *        column, add / delete an index, rename, empty or delete the table)
 *
 * Both answer with the statements that ran (the same ones the browser showed, from
 * shared/utils/datasources/ddl.ts) and record the change in the audit trail.
 */
import { z } from 'zod'
import type { H3Event } from 'h3'
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'
import type { ExplorerColumn } from '#shared/types/explorer'
import { COLUMN_KINDS, changeStatements, checkName, createTableStatements, typeFor, type ColumnSpec, type TableChange } from '#shared/utils/datasources/ddl'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'
import { parseValue } from '#shared/utils/datasources/values'
import { actorOf, recordAudit } from '../core/audit'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { changesOf, structureOf } from '../data/databaseRows'
import { tablesOf } from '../data/databaseTables'
import type { StoredDataSource } from '../data/dataSourceStore'
import { createdTablesOn } from '../data/destinationStore'
import { editsOf, ensureStructureEdit, omit, renameColumnInRows, renameEdits } from '../data/tableEdits'
import type { MockTenant, MockUser } from '../data/tenants'
import { usableSource } from './explorer'

const columnSpec = z.object({
  name: z.string().trim().max(128),
  kind: z.enum(COLUMN_KINDS),
  length: z.number().int().min(1).max(8000).nullish(),
  scale: z.number().int().min(0).max(30).nullish(),
  nullable: z.boolean(),
  default: z.string().max(500).nullish(),
  primary: z.boolean().optional(),
  auto: z.boolean().optional(),
})
const change = z.discriminatedUnion('op', [
  z.object({ op: z.literal('add_column'), column: columnSpec }),
  z.object({ op: z.literal('alter_column'), column: z.string(), to: columnSpec }),
  z.object({ op: z.literal('drop_column'), column: z.string() }),
  z.object({ op: z.literal('rename_table'), name: z.string().trim().max(128) }),
  z.object({ op: z.literal('add_index'), name: z.string().trim().max(128), columns: z.array(z.string()).min(1).max(16), unique: z.boolean() }),
  z.object({ op: z.literal('drop_index'), name: z.string() }),
  z.object({ op: z.literal('truncate') }),
  z.object({ op: z.literal('drop_table') }),
])

const problem = (field: string, message: string) => new MockError('FRM-GEN-1002', [{ field, message }])

/** Problems with one column (name, default) → FRM-GEN-1002 on `${field}.…`. */
function checkColumn(source: StoredDataSource, spec: ColumnSpec, field: string) {
  const name = checkName(source.engine, spec.name, 'column')
  if (name) throw problem(`${field}.name`, name)
  if (spec.auto && !(spec.primary && (spec.kind === 'integer' || spec.kind === 'big_integer'))) throw problem(`${field}.auto`, 'auto')
  if (spec.default) {
    const parsed = parseValue({ type: typeFor(source.engine, spec), nullable: true, has_default: false }, spec.default)
    if ('problem' in parsed) throw problem(`${field}.default`, parsed.problem)
  }
}

const asColumn = (source: StoredDataSource, spec: ColumnSpec): TableColumn => ({
  name: spec.name,
  type: typeFor(source.engine, spec),
  nullable: !spec.primary && spec.nullable,
  has_default: !!spec.auto || !!spec.default,
  primary: !!spec.primary,
  unique: !!spec.primary,
})

/** The schemas their tables may go in: those in the tree, the connection's list, the default. */
function schemasOf(source: StoredDataSource, tables: DatabaseTable[]): string[] {
  return [...new Set([...tables.filter(table => !table.formalie).map(table => table.schema), ...source.access.schemas, tablesSchemaOf(source.engine, source.settings, source.access)])]
}

function audit(event: H3Event, tenant: MockTenant, user: MockUser, action: 'data.user_table_created' | 'data.table_altered' | 'data.table_truncated' | 'data.table_dropped', source: StoredDataSource, table: string, extra: Record<string, string> = {}) {
  recordAudit(event, tenant, { action, actor: actorOf(user), resource: { type: 'data_source', id: source.id, name: source.name }, metadata: { table, ...extra } })
}

export const createTable = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usableSource(tenant, getRouterParam(event, 'id'))
  if (source.access.other !== 'read_write') throw new MockError('FRM-DEST-1019', [{ field: 'table', message: 'read_access' }])
  const input = parseBody(z.object({ schema: z.string(), name: z.string().trim().max(128), columns: z.array(columnSpec).min(1).max(200) }), body)
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  if (!schemasOf(source, tables).includes(input.schema)) throw problem('schema', 'schema')
  const name = checkName(source.engine, input.name, 'table')
  if (name) throw problem('name', name)
  if (tables.some(table => table.schema === input.schema && table.name.toLowerCase() === input.name.toLowerCase())) throw new MockError('FRM-DEST-1022', [{ field: 'name', message: 'taken' }])
  const seen = new Set<string>()
  input.columns.forEach((spec, index) => {
    checkColumn(source, spec, `columns.${index}`)
    if (seen.has(spec.name.toLowerCase())) throw problem(`columns.${index}.name`, 'taken')
    seen.add(spec.name.toLowerCase())
  })
  const statements = createTableStatements(source.engine, input.schema, input.name, input.columns)
  const edits = editsOf(source.id)
  const key = `${input.schema}.${input.name}`
  edits.dropped.delete(key)
  edits.structure.delete(key)
  edits.rows.delete(key)
  const table: DatabaseTable = { schema: input.schema, name: input.name, columns: input.columns.map(spec => asColumn(source, spec)), rows_estimate: 0, formalie: false }
  edits.created.push(table)
  const edit = ensureStructureEdit(source, table)
  edit.created = true
  edit.columnOrigin = Object.fromEntries(table.columns.map(column => [column.name, null]))
  edit.defaults = Object.fromEntries(input.columns.filter(spec => spec.default && !spec.auto).map(spec => [spec.name, spec.default!]))
  audit(event, tenant, user, 'data.user_table_created', source, key, { columns: String(input.columns.length) })
  return ok({ statements, table: { schema: input.schema, name: input.name } }, {}, 201)
})

export const changeTable = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const source = usableSource(tenant, getRouterParam(event, 'id'))
  const input = parseBody(z.object({ schema: z.string(), table: z.string(), change }), body)
  const tables = tablesOf(source, createdTablesOn(tenant, source))
  const table = tables.find(item => item.schema === input.schema && item.name === input.table)
  if (!table) throw new MockError('FRM-GEN-1004')
  const structure = structureOf(tenant, source, tables, table)
  if (!structure.alterable) throw new MockError('FRM-DEST-1019', [{ field: 'table', message: structure.formalie ? 'response_table' : 'read_access' }])
  const step: TableChange = input.change
  const columnNamed = (name: string) => structure.columns.find(column => column.name === name)
  const taken = (name: string, except?: string) => structure.columns.some(column => column.name.toLowerCase() === name.toLowerCase() && column.name !== except)
  const current = (column: ExplorerColumn) => ({ name: column.name, type: column.type, nullable: column.nullable, default: column.primary ? null : column.default, primary: column.primary })
  let statements: string[] = []
  const key = `${structure.schema}.${structure.name}`
  const rows = changesOf(source, table)
  let result: { schema: string; name: string } | null = { schema: structure.schema, name: structure.name }

  switch (step.op) {
    case 'add_column': {
      checkColumn(source, step.column, 'column')
      if (taken(step.column.name)) throw new MockError('FRM-DEST-1022', [{ field: 'column.name', message: 'taken' }])
      if (!step.column.nullable && !step.column.default && (table.rows_estimate ?? 0) > 0) throw problem('column.default', 'needs_default')
      statements = changeStatements(source.engine, structure.schema, structure.name, { ...step, column: { ...step.column, primary: false, auto: false } })
      const edit = ensureStructureEdit(source, table)
      edit.columns!.push(asColumn(source, { ...step.column, primary: false, auto: false }))
      edit.columnOrigin[step.column.name] = null
      if (step.column.default) edit.defaults[step.column.name] = step.column.default
      break
    }
    case 'alter_column': {
      const column = columnNamed(step.column)
      if (!column) throw new MockError('FRM-GEN-1004')
      checkColumn(source, { ...step.to, primary: column.primary, auto: false }, 'to')
      if (taken(step.to.name, column.name)) throw new MockError('FRM-DEST-1022', [{ field: 'to.name', message: 'taken' }])
      const type = typeFor(source.engine, step.to)
      // Key columns: only the name changes here (their type and default stay as they are).
      if (column.primary && (type.toUpperCase() !== column.type.toUpperCase() || step.to.default)) throw problem('to.kind', 'key_column')
      statements = changeStatements(source.engine, structure.schema, structure.name, step, current(column))
      const edit = ensureStructureEdit(source, table)
      const index = edit.columns!.findIndex(item => item.name === column.name)
      edit.columns![index] = { ...edit.columns![index]!, name: step.to.name, type: column.primary ? column.type : type, nullable: column.primary ? false : step.to.nullable, has_default: column.primary ? column.has_default : !!step.to.default }
      if (step.to.name !== column.name) {
        edit.columnOrigin = { ...omit(edit.columnOrigin, column.name), [step.to.name]: edit.columnOrigin[column.name] ?? null }
        edit.defaults = omit(edit.defaults, column.name)
        renameColumnInRows(rows, column.name, step.to.name)
        edit.indexes = edit.indexes.map(item => ({ ...item, columns: item.columns.map(name => (name === column.name ? step.to.name : name)) }))
      }
      if (!column.primary) {
        edit.defaults = step.to.default ? { ...edit.defaults, [step.to.name]: step.to.default } : omit(edit.defaults, step.to.name)
      }
      break
    }
    case 'drop_column': {
      const column = columnNamed(step.column)
      if (!column) throw new MockError('FRM-GEN-1004')
      if (column.primary) throw problem('column', 'key_column')
      if (structure.columns.length === 1) throw problem('column', 'last_column')
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      const edit = ensureStructureEdit(source, table)
      edit.columns = edit.columns!.filter(item => item.name !== column.name)
      edit.columnOrigin = omit(edit.columnOrigin, column.name)
      edit.defaults = omit(edit.defaults, column.name)
      edit.indexes = edit.indexes.filter(item => !item.columns.includes(column.name))
      break
    }
    case 'rename_table': {
      const name = checkName(source.engine, step.name, 'table')
      if (name) throw problem('name', name)
      if (tables.some(item => item.schema === structure.schema && item.name.toLowerCase() === step.name.toLowerCase())) throw new MockError('FRM-DEST-1022', [{ field: 'name', message: 'taken' }])
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      ensureStructureEdit(source, table)
      renameEdits(source, table, step.name)
      result = { schema: structure.schema, name: step.name }
      break
    }
    case 'add_index': {
      const name = checkName(source.engine, step.name, 'index')
      if (name) throw problem('name', name)
      if (structure.indexes.some(item => item.name.toLowerCase() === step.name.toLowerCase())) throw new MockError('FRM-DEST-1022', [{ field: 'name', message: 'taken' }])
      if (step.columns.some(name => !columnNamed(name))) throw problem('columns', 'columns')
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      ensureStructureEdit(source, table).indexes.push({ name: step.name, columns: step.columns, unique: step.unique, primary: false })
      break
    }
    case 'drop_index': {
      const index = structure.indexes.find(item => item.name === step.name)
      if (!index) throw new MockError('FRM-GEN-1004')
      if (index.primary) throw problem('name', 'key_index')
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      const edit = ensureStructureEdit(source, table)
      edit.indexes = edit.indexes.filter(item => item.name !== step.name)
      if (!edit.droppedIndexes.includes(step.name)) edit.droppedIndexes.push(step.name)
      break
    }
    case 'truncate': {
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      ensureStructureEdit(source, table).truncated = true
      Object.assign(rows, { inserted: [], updated: {}, deleted: [] })
      break
    }
    case 'drop_table': {
      statements = changeStatements(source.engine, structure.schema, structure.name, step)
      const edits = editsOf(source.id)
      edits.dropped.add(key)
      edits.created = edits.created.filter(item => `${item.schema}.${item.name}` !== key)
      edits.rows.delete(key)
      result = null
      break
    }
  }

  const action = step.op === 'truncate' ? 'data.table_truncated' : step.op === 'drop_table' ? 'data.table_dropped' : 'data.table_altered'
  audit(event, tenant, user, action, source, key, action === 'data.table_altered' ? { change: step.op, ...('column' in step && typeof step.column === 'string' ? { column: step.column } : {}), ...(step.op === 'rename_table' ? { name: step.name } : {}) } : {})
  return ok({ statements, table: result })
})

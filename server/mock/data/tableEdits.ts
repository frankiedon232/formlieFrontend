/**
 * Changes made in the mock explorer (F12 M3), on top of the generated tables and rows: rows
 * added, changed and deleted, and structure changes to the organisation's own tables (never
 * Formalie's response tables): tables created, renamed, emptied or deleted, columns added,
 * changed or deleted, indexes added or deleted. Kept in memory (a real database keeps them).
 */
import type { DatabaseTable, TableColumn } from '#shared/types/destinations'
import type { TableIndex, TableRow } from '#shared/types/explorer'

export interface TableChanges {
  inserted: TableRow[]
  updated: Record<string, Record<string, unknown>>
  deleted: string[]
}

export interface StructureEdit {
  /** The generated table this one came from (rows keep their values after a rename). */
  origin: string
  /** The columns now; null = as generated. */
  columns: TableColumn[] | null
  /** Current column name → the generated column it came from (null = added here). */
  columnOrigin: Record<string, string | null>
  /** Defaults set here, as typed. */
  defaults: Record<string, string>
  indexes: TableIndex[]
  droppedIndexes: string[]
  /** Emptied: the generated rows are gone. */
  truncated: boolean
  /** Created here (no generated rows). */
  created: boolean
}

interface SourceEdits {
  rows: Map<string, TableChanges>
  structure: Map<string, StructureEdit>
  created: DatabaseTable[]
  dropped: Set<string>
}

const bySource = new Map<string, SourceEdits>()
const keyOf = (table: { schema: string; name: string }) => `${table.schema}.${table.name}`

export function editsOf(sourceId: string): SourceEdits {
  let found = bySource.get(sourceId)
  if (!found) {
    found = { rows: new Map(), structure: new Map(), created: [], dropped: new Set() }
    bySource.set(sourceId, found)
  }
  return found
}

export function changesOf(source: { id: string }, table: { schema: string; name: string }): TableChanges {
  const edits = editsOf(source.id)
  let found = edits.rows.get(keyOf(table))
  if (!found) {
    found = { inserted: [], updated: {}, deleted: [] }
    edits.rows.set(keyOf(table), found)
  }
  return found
}

export function structureEditOf(source: { id: string }, table: { schema: string; name: string }): StructureEdit | undefined {
  return editsOf(source.id).structure.get(keyOf(table))
}

/** The edit record of a table, made on first change. */
export function ensureStructureEdit(source: { id: string }, table: DatabaseTable): StructureEdit {
  const edits = editsOf(source.id)
  let found = edits.structure.get(keyOf(table))
  if (!found) {
    found = { origin: keyOf(table), columns: null, columnOrigin: Object.fromEntries(table.columns.map(column => [column.name, column.name])), defaults: {}, indexes: [], droppedIndexes: [], truncated: false, created: false }
    edits.structure.set(keyOf(table), found)
  }
  if (!found.columns) found.columns = table.columns.map(column => ({ ...column }))
  return found
}

/** Moves everything kept for a table to its new name. */
export function renameEdits(source: { id: string }, from: { schema: string; name: string }, to: string) {
  const edits = editsOf(source.id)
  const next = { schema: from.schema, name: to }
  for (const map of [edits.rows, edits.structure] as Map<string, unknown>[]) {
    const value = map.get(keyOf(from))
    if (value !== undefined) {
      map.delete(keyOf(from))
      map.set(keyOf(next), value)
    }
  }
  const created = edits.created.find(table => keyOf(table) === keyOf(from))
  if (created) created.name = to
}

/** A copy without one key. */
export const omit = <T>(record: Record<string, T>, key: string): Record<string, T> => Object.fromEntries(Object.entries(record).filter(([name]) => name !== key))

/** Renames a column in rows added or changed here. */
export function renameColumnInRows(changes: TableChanges, from: string, to: string) {
  const move = <T extends Record<string, unknown>>(row: T): T => (from in row ? ({ ...omit(row, from), [to]: row[from] } as T) : row)
  changes.inserted = changes.inserted.map(move)
  changes.updated = Object.fromEntries(Object.entries(changes.updated).map(([key, row]) => [key, move(row)]))
}

/** The generated tables with the changes made here applied (organisation's tables only). */
export function applyStructureEdits(sourceId: string, tables: DatabaseTable[]): DatabaseTable[] {
  const edits = editsOf(sourceId)
  const generated = new Map(tables.map(table => [keyOf(table), table]))
  const out: DatabaseTable[] = tables.filter(table => table.formalie)
  for (const table of tables) {
    if (table.formalie) continue
    const key = keyOf(table)
    // A renamed table shows under its new name (below); a table nobody renamed shows as is.
    if (edits.dropped.has(key) || ([...edits.structure.entries()].some(([current, edit]) => edit.origin === key && current !== key))) continue
    const edit = edits.structure.get(key)
    out.push(edit?.columns ? { ...table, columns: edit.columns, rows_estimate: edit.truncated ? changesOf({ id: sourceId }, table).inserted.length : table.rows_estimate } : table)
  }
  for (const [current, edit] of edits.structure) {
    if (edit.created || current === edit.origin || edits.dropped.has(current)) continue
    const base = generated.get(edit.origin)
    if (!base) continue
    const dot = current.indexOf('.')
    const name = { schema: current.slice(0, dot), name: current.slice(dot + 1) }
    out.push({ ...base, ...name, columns: edit.columns ?? base.columns, rows_estimate: edit.truncated ? changesOf({ id: sourceId }, name).inserted.length : base.rows_estimate })
  }
  for (const table of edits.created) {
    if (edits.dropped.has(keyOf(table))) continue
    const edit = edits.structure.get(keyOf(table))
    out.push({ ...table, columns: edit?.columns ?? table.columns, rows_estimate: changesOf({ id: sourceId }, table).inserted.length - changesOf({ id: sourceId }, table).deleted.length })
  }
  return out
}

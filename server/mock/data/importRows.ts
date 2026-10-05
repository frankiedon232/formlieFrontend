/**
 * One row of an import file → the values to store (F12 M3), or the first problem (which column,
 * what is wrong). Columns are filled from the file column chosen for them, typed by the column's
 * own type; Excel day numbers in date columns become dates.
 */
import type { TableStructure } from '#shared/types/explorer'
import { kindOfType, parseValue } from '#shared/utils/datasources/values'
import { excelDate } from '../core/tabularRead'

/** One file row → typed values, or the first problem (column and what is wrong). */
export function importRow(
  structure: TableStructure,
  headers: string[],
  line: string[],
  mapping: Record<string, string | null>,
): { values: Record<string, unknown> } | { problem: { column: string; problem: string } } {
  const values: Record<string, unknown> = {}
  for (const column of structure.columns) {
    const header = mapping[column.name]
    let raw: unknown = header ? (line[headers.indexOf(header)] ?? '') : ''
    // Excel day numbers in date columns become dates.
    const kind = kindOfType(column.type)
    if ((kind === 'date' || kind === 'datetime') && /^\d+(\.\d+)?$/.test(String(raw).trim()))
      raw = kind === 'date' ? excelDate(Number(raw)).slice(0, 10) : excelDate(Number(raw))
    const parsed = parseValue(column, raw)
    if ('problem' in parsed) return { problem: { column: column.name, problem: parsed.problem } }
    values[column.name] = parsed.value
  }
  return { values }
}

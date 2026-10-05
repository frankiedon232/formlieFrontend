/**
 * Turning typed text into a column's value, the same way for the row form, imports and the
 * server (F12 M3): numbers, whole numbers, yes / no, dates, date-times, times, JSON and text (with
 * its length limit). Empty means NULL where the column allows it.
 */
import type { TableColumn } from '#shared/types/destinations'

export type ValueKind = 'integer' | 'decimal' | 'boolean' | 'date' | 'datetime' | 'time' | 'json' | 'text'
export type ValueProblem =
  'required' | 'integer' | 'number' | 'boolean' | 'date' | 'datetime' | 'time' | 'json' | 'length'

/** What kind of value a database type holds (by its name, any engine). */
export function kindOfType(type: string): ValueKind {
  const t = type.toUpperCase()
  if (/^BOOL|^BIT$|TINYINT\(1\)|NUMBER\(1\)$/.test(t)) return 'boolean'
  if (/JSON/.test(t)) return 'json'
  if (/^(BIG|SMALL|TINY|MEDIUM)?INT|^INTEGER|^SERIAL|NUMBER\(\d+\)$|^NUMBER\(19\)/.test(t)) return 'integer'
  if (/DEC|NUMERIC|NUMBER|FLOAT|DOUBLE|REAL|MONEY/.test(t)) return 'decimal'
  if (/TIMESTAMP|DATETIME/.test(t)) return 'datetime'
  if (/^DATE$/.test(t)) return 'date'
  if (/^TIME/.test(t)) return 'time'
  return 'text'
}

/** The longest text a column takes (VARCHAR(200) → 200), or null when unlimited. */
export function lengthOf(type: string): number | null {
  const match = /CHAR2?\((\d+)/i.exec(type)
  return match ? Number(match[1]) : null
}

const YES = new Set(['true', 'yes', '1', 'y', 'on'])
const NO = new Set(['false', 'no', '0', 'n', 'off'])

/** Text (as typed or as read from a file) → the value to store, or what is wrong with it. */
export function parseValue(
  column: Pick<TableColumn, 'type' | 'nullable' | 'has_default'>,
  raw: unknown,
): { value: unknown } | { problem: ValueProblem } {
  const text = raw == null ? '' : typeof raw === 'string' ? raw.trim() : raw
  if (text === '' || text === null)
    return column.nullable || column.has_default ? { value: null } : { problem: 'required' }
  switch (kindOfType(column.type)) {
    case 'integer': {
      const number = Number(text)
      return Number.isInteger(number) ? { value: number } : { problem: 'integer' }
    }
    case 'decimal': {
      const number = Number(typeof text === 'string' ? text.replace(/\s/g, '') : text)
      return Number.isFinite(number) ? { value: number } : { problem: 'number' }
    }
    case 'boolean': {
      if (typeof text === 'boolean') return { value: text }
      const word = String(text).toLowerCase()
      return YES.has(word) ? { value: true } : NO.has(word) ? { value: false } : { problem: 'boolean' }
    }
    case 'date':
      return /^\d{4}-\d{2}-\d{2}$/.test(String(text)) && !Number.isNaN(Date.parse(String(text)))
        ? { value: String(text) }
        : { problem: 'date' }
    case 'datetime': {
      const time = Date.parse(String(text))
      return Number.isNaN(time) ? { problem: 'datetime' } : { value: new Date(time).toISOString() }
    }
    case 'time':
      return /^\d{2}:\d{2}(:\d{2})?$/.test(String(text)) ? { value: String(text) } : { problem: 'time' }
    case 'json':
      if (typeof text === 'object') return { value: JSON.stringify(text) }
      try {
        JSON.parse(String(text))
        return { value: String(text) }
      } catch {
        return { problem: 'json' }
      }
    default: {
      const value = String(text)
      const max = lengthOf(column.type)
      return max !== null && value.length > max ? { problem: 'length' } : { value }
    }
  }
}

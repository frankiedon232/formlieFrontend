/**
 * Importing options into a list (F15), the two ways a row can be read:
 * - one option per row (`importRows`): columns hold the label, value, score or a translation;
 * - a path per row (`importPaths`, lists with levels, F15 M2): one column per level (Country, Region,
 *   City). Options already there (same label under the same option above) are kept; new ones are added
 *   under their parent with a value made from the parent's and their own.
 * "Replace" retires what the file no longer has (never deleted, old answers keep reading).
 * `looksLikeLevels` spots a path file (owner 2026-10-08: a 3-column file went into a simple list as one column).
 */
import type { OptionItem } from '#shared/types/forms'
import { MAX_LIST_LEVELS, valueFromLabel } from '#shared/utils/forms/options'

/** A value not taken yet, against a set of taken values (lower case) kept up to date by the caller: one look-up, not a copy of the set per row. */
function freeValue(wanted: string, taken: Set<string>): string {
  if (!taken.has(wanted.toLowerCase())) return wanted
  for (let n = 2; ; n++) if (!taken.has(`${wanted}_${n}`.toLowerCase())) return `${wanted}_${n}`
}

export interface PathImport {
  list: OptionItem[]
  added: number
  kept: number
  skipped: number
  retired: number
}
export interface RowImport {
  list: OptionItem[]
  added: number
  updated: number
  skipped: number
  retired: number
}

/** Retired count after "Replace", and the list tidied (no `active: undefined`). */
function finish(list: OptionItem[], before: OptionItem[], replace: boolean): number {
  // Indexed, not searched: big files (150,000 rows) stay quick (owner 2026-10-08: a 5 MB file hung)
  const wasActive = new Set(before.filter(item => item.active !== false).map(item => item.value))
  const retired = replace ? list.filter(option => option.active === false && wasActive.has(option.value)).length : 0
  for (const option of list) if (option.active !== false) delete option.active
  return retired
}

/** `columns[level]` = the column holding that level (−1 = none, which ends the path there). */
export function importPaths(options: OptionItem[], rows: string[][], columns: number[], replace: boolean): PathImport {
  const list: OptionItem[] = options.map(option => (replace ? { ...option, active: false } : { ...option }))
  const taken = new Set(list.map(option => option.value.toLowerCase()))
  const seen = new Set<OptionItem>()
  // One look-up per row: level, the option above and the label (without case)
  const keyOf = (at: number, parent: string | undefined, label: string) => `${at}\u001f${at === 0 ? '' : (parent ?? '')}\u001f${label.toLowerCase()}`
  const index = new Map(list.map(option => [keyOf(option.level ?? 0, option.parent, option.label), option]))
  let added = 0
  let kept = 0
  let skipped = 0
  for (const row of rows) {
    let parent: string | undefined
    let used = false
    for (let at = 0; at < columns.length; at++) {
      const column = columns[at] ?? -1
      const label = column >= 0 ? (row[column] ?? '').trim() : ''
      if (!label) break
      let match = index.get(keyOf(at, parent, label))
      if (!match) {
        const own = valueFromLabel(label) || 'option'
        const value = freeValue(parent ? `${parent}_${own}` : own, taken)
        taken.add(value.toLowerCase())
        match = { value, label, ...(at > 0 ? { level: at, parent } : {}) }
        list.push(match)
        index.set(keyOf(at, parent, label), match)
        added++
      } else if (!seen.has(match)) {
        kept++
      }
      seen.add(match)
      delete match.active
      parent = match.value
      used = true
    }
    if (!used) skipped++
  }
  return { list, added, kept, skipped, retired: finish(list, options, replace) }
}

/** One option per row: `at` = the columns holding label, value, score and translations (−1 = none). */
export function importRows(options: OptionItem[], rows: string[][], at: { label: number; value: number; score: number; languages: [string, number][]; details?: [string, number][] }, replace: boolean): RowImport {
  const list: OptionItem[] = options.map(option => (replace ? { ...option, active: false } : { ...option }))
  let added = 0
  let updated = 0
  let skipped = 0
  const seen = new Set<OptionItem>()
  const cell = (row: string[], index: number) => (index >= 0 ? (row[index] ?? '').trim() : '')
  const byValue = new Map(list.map(option => [option.value.toLowerCase(), option]))
  const byLabel = new Map<string, OptionItem>()
  for (const option of list) if (!byLabel.has(option.label.toLowerCase())) byLabel.set(option.label.toLowerCase(), option)
  const taken = new Set(list.map(option => option.value.toLowerCase()))
  for (const row of rows) {
    const label = cell(row, at.label)
    if (!label) {
      skipped++
      continue
    }
    const wanted = cell(row, at.value)
    const match = wanted ? byValue.get(wanted.toLowerCase()) : byLabel.get(label.toLowerCase())
    const scoreText = cell(row, at.score)
    const score = scoreText && !Number.isNaN(Number(scoreText)) ? Number(scoreText) : undefined
    const translations = Object.fromEntries(at.languages.map(([code, index]) => [code, cell(row, index)]).filter(([, value]) => value))
    // Details (F15 M4): a column per list detail
    const details = Object.fromEntries((at.details ?? []).map(([key, index]) => [key, cell(row, index)]).filter(([, value]) => value))
    const withDetails = (option: OptionItem) => (Object.keys(details).length ? { attrs: { ...option.attrs, ...details } } : {})
    if (match) {
      if (seen.has(match)) {
        skipped++
        continue
      }
      seen.add(match)
      Object.assign(match, { label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations: { ...match.translations, ...translations } } : {}), ...withDetails(match) })
      delete match.active
      updated++
    } else {
      const option: OptionItem = { value: freeValue(wanted || valueFromLabel(label), taken), label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations } : {}) }
      Object.assign(option, withDetails(option))
      list.push(option)
      taken.add(option.value.toLowerCase())
      byValue.set(option.value.toLowerCase(), option)
      if (!byLabel.has(label.toLowerCase())) byLabel.set(label.toLowerCase(), option)
      seen.add(option)
      added++
    }
  }
  return { list, added, updated, skipped, retired: finish(list, options, replace) }
}

/**
 * A file shaped like levels: two to four filled text columns where the first column repeats
 * (Canada, Canada, Japan …) because several rows sit under the same option.
 */
export function looksLikeLevels(rows: string[][]): boolean {
  if (rows.length < 2) return false
  // A loop, not Math.max(...rows): spreading 150,000 rows overflows the call stack
  const width = rows.reduce((most, row) => Math.max(most, row.length), 0)
  if (width < 2 || width > MAX_LIST_LEVELS) return false
  const filled = (column: number) => rows.filter(row => (row[column] ?? '').trim()).length >= rows.length * 0.8
  if (!filled(0) || !filled(1)) return false
  const numeric = (column: number) => rows.every(row => !(row[column] ?? '').trim() || !Number.isNaN(Number(row[column])))
  if (numeric(1)) return false
  const first = new Set(rows.map(row => (row[0] ?? '').trim().toLowerCase()))
  return first.size < rows.length
}

const HEADER_WORDS = ['label', 'name', 'option', 'options', 'value', 'code', 'id', 'key', 'score', 'points', 'weight']
/**
 * Pasted text whose first row names the columns: known words (Label, Value, Score …), or a path file
 * whose first cell never comes back while the rest of that column repeats (Country, then Canada, Canada …).
 */
export function looksLikeHeader(rows: string[][]): boolean {
  const first = rows[0]?.map(cell => cell.trim().toLowerCase()) ?? []
  if (rows.length < 3 || !first.length || first.some(cell => !cell || !Number.isNaN(Number(cell)))) return false
  if (first.some(cell => HEADER_WORDS.includes(cell))) return true
  const rest = rows.slice(1)
  return looksLikeLevels(rest) && first.every((cell, column) => !rest.some(row => (row[column] ?? '').trim().toLowerCase() === cell))
}

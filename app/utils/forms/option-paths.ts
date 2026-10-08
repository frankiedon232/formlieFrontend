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
import { MAX_LIST_LEVELS, uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

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
  const retired = replace ? list.filter(option => option.active === false && before.find(item => item.value === option.value)?.active !== false).length : 0
  for (const option of list) if (option.active !== false) delete option.active
  return retired
}

/** `columns[level]` = the column holding that level (−1 = none, which ends the path there). */
export function importPaths(options: OptionItem[], rows: string[][], columns: number[], replace: boolean): PathImport {
  const list: OptionItem[] = options.map(option => (replace ? { ...option, active: false } : { ...option }))
  const taken = new Set(list.map(option => option.value.toLowerCase()))
  const seen = new Set<OptionItem>()
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
      let match = list.find(option => (option.level ?? 0) === at && (at === 0 || option.parent === parent) && option.label.toLowerCase() === label.toLowerCase())
      if (!match) {
        const own = valueFromLabel(label) || 'option'
        const value = uniqueValue(parent ? `${parent}_${own}` : own, taken)
        taken.add(value.toLowerCase())
        match = { value, label, ...(at > 0 ? { level: at, parent } : {}) }
        list.push(match)
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
export function importRows(options: OptionItem[], rows: string[][], at: { label: number; value: number; score: number; languages: [string, number][] }, replace: boolean): RowImport {
  const list: OptionItem[] = options.map(option => (replace ? { ...option, active: false } : { ...option }))
  let added = 0
  let updated = 0
  let skipped = 0
  const seen = new Set<OptionItem>()
  const cell = (row: string[], index: number) => (index >= 0 ? (row[index] ?? '').trim() : '')
  for (const row of rows) {
    const label = cell(row, at.label)
    if (!label) {
      skipped++
      continue
    }
    const wanted = cell(row, at.value)
    const match = list.find(option => (wanted ? option.value.toLowerCase() === wanted.toLowerCase() : option.label.toLowerCase() === label.toLowerCase()))
    const scoreText = cell(row, at.score)
    const score = scoreText && !Number.isNaN(Number(scoreText)) ? Number(scoreText) : undefined
    const translations = Object.fromEntries(at.languages.map(([code, index]) => [code, cell(row, index)]).filter(([, value]) => value))
    if (match) {
      if (seen.has(match)) {
        skipped++
        continue
      }
      seen.add(match)
      Object.assign(match, { label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations: { ...match.translations, ...translations } } : {}) })
      delete match.active
      updated++
    } else {
      const option: OptionItem = { value: uniqueValue(wanted || valueFromLabel(label), list.map(item => item.value)), label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations } : {}) }
      list.push(option)
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
  const width = Math.max(...rows.map(row => row.length))
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

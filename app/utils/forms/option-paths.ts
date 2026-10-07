/**
 * Import into a list with levels (F15 M2): each row is a path (Country, Region, City), one column per
 * level. Options already there (same label under the same option above) are kept; new ones are added
 * under their parent with a value made from the parent's and their own. "Replace" retires what the
 * file no longer has (never deleted, old answers keep reading).
 */
import type { OptionItem } from '#shared/types/forms'
import { uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

export interface PathImport {
  list: OptionItem[]
  added: number
  kept: number
  skipped: number
  retired: number
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
  const retired = replace ? list.filter(option => option.active === false && options.find(item => item.value === option.value)?.active !== false).length : 0
  for (const option of list) if (option.active !== false) delete option.active
  return { list, added, kept, skipped, retired }
}

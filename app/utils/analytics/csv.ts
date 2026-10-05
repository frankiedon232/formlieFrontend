/**
 * A small CSV for the analytics download (F18): numbers as they are, text quoted, cells that a
 * spreadsheet would run as a formula (= + - @) prefixed with an apostrophe, a BOM so Excel reads
 * UTF-8. Only counts and form names go in it, never answers.
 */
const BOM = String.fromCharCode(0xfeff)

export function analyticsCsv(rows: (string | number | null)[][]): string {
  const cell = (value: string | number | null) => {
    if (value == null) return ''
    if (typeof value === 'number') return String(value)
    const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
    return /[",\n\r;]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
  }
  return `${BOM}${rows.map(row => row.map(cell).join(',')).join('\r\n')}\r\n`
}

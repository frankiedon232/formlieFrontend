/**
 * Reading spreadsheet files for imports (F12 M3), without a library: CSV (quoted fields, comma,
 * semicolon or tab, a byte-order mark) and .xlsx (a zip of XML: the first sheet and its shared
 * strings, unpacked with Node's zlib). Returns the header row and the data rows as text.
 */
import { inflateRawSync } from 'node:zlib'

export interface Tabular {
  headers: string[]
  rows: string[][]
}

export function parseCsv(text: string): Tabular {
  const body = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text
  const firstLine = body.split(/\r?\n/, 1)[0] ?? ''
  const separator = [',', ';', '\t'].sort((a, b) => firstLine.split(b).length - firstLine.split(a).length)[0]!
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < body.length; i++) {
    const char = body[i]!
    if (quoted) {
      if (char === '"' && body[i + 1] === '"') {
        cell += '"'
        i++
      } else if (char === '"') quoted = false
      else cell += char
    } else if (char === '"') quoted = true
    else if (char === separator) {
      row.push(cell)
      cell = ''
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && body[i + 1] === '\n') i++
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
    } else cell += char
  }
  if (cell || row.length) rows.push([...row, cell])
  const filled = rows.filter(line => line.some(value => value.trim() !== ''))
  return { headers: (filled[0] ?? []).map(header => header.trim()), rows: filled.slice(1) }
}

// ── .xlsx ────────────────────────────────────────────────────────────────────────────────

/** The files inside a zip (only the ones asked for), unpacked. */
function unzip(buffer: Buffer, wanted: (name: string) => boolean): Map<string, string> {
  const files = new Map<string, string>()
  let end = buffer.length - 22
  while (end >= 0 && buffer.readUInt32LE(end) !== 0x06054b50) end--
  if (end < 0) throw new Error('not a zip')
  const count = buffer.readUInt16LE(end + 10)
  let at = buffer.readUInt32LE(end + 16)
  for (let i = 0; i < count; i++) {
    if (buffer.readUInt32LE(at) !== 0x02014b50) break
    const method = buffer.readUInt16LE(at + 10)
    const size = buffer.readUInt32LE(at + 20)
    const nameLength = buffer.readUInt16LE(at + 28)
    const extraLength = buffer.readUInt16LE(at + 30)
    const commentLength = buffer.readUInt16LE(at + 32)
    const local = buffer.readUInt32LE(at + 42)
    const name = buffer.toString('utf8', at + 46, at + 46 + nameLength)
    if (wanted(name)) {
      const start = local + 30 + buffer.readUInt16LE(local + 26) + buffer.readUInt16LE(local + 28)
      const data = buffer.subarray(start, start + size)
      files.set(name, (method === 8 ? inflateRawSync(data) : data).toString('utf8'))
    }
    at += 46 + nameLength + extraLength + commentLength
  }
  return files
}

const decode = (text: string) =>
  text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&amp;/g, '&')

const columnIndex = (ref: string) => {
  const letters = /^[A-Z]+/.exec(ref)?.[0] ?? 'A'
  return [...letters].reduce((sum, letter) => sum * 26 + letter.charCodeAt(0) - 64, 0) - 1
}

export function parseXlsx(buffer: Buffer): Tabular {
  const files = unzip(
    buffer,
    name => name === 'xl/sharedStrings.xml' || /^xl\/worksheets\/sheet\d+\.xml$/.test(name),
  )
  const shared = [...(files.get('xl/sharedStrings.xml') ?? '').matchAll(/<si>([\s\S]*?)<\/si>/g)].map(match =>
    decode([...match[1]!.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(part => part[1]).join('')),
  )
  const sheetName = [...files.keys()].filter(name => name.startsWith('xl/worksheets/')).sort()[0]
  if (!sheetName) throw new Error('no sheet')
  const rows: string[][] = []
  for (const rowMatch of files.get(sheetName)!.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)) {
    const row: string[] = []
    for (const cell of rowMatch[1]!.matchAll(/<c\s([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
      const attrs = cell[1]!
      const inner = cell[2] ?? ''
      const ref = /r="([A-Z]+\d+)"/.exec(attrs)?.[1] ?? ''
      const type = /t="(\w+)"/.exec(attrs)?.[1]
      const raw = /<v>([\s\S]*?)<\/v>/.exec(inner)?.[1]
      let value: string
      if (type === 's') value = shared[Number(raw)] ?? ''
      else if (type === 'inlineStr')
        value = decode([...inner.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(part => part[1]).join(''))
      else if (type === 'b') value = raw === '1' ? 'true' : 'false'
      else value = decode(raw ?? '')
      row[ref ? columnIndex(ref) : row.length] = value
    }
    rows.push(Array.from(row, value => value ?? ''))
  }
  const filled = rows.filter(line => line.some(value => value.trim() !== ''))
  return { headers: (filled[0] ?? []).map(header => header.trim()), rows: filled.slice(1) }
}

/** Excel stores dates as day numbers since 1899-12-30. */
export const excelDate = (serial: number) => new Date(Math.round((serial - 25569) * 86_400_000)).toISOString()

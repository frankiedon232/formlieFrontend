/**
 * Reads a table from a file people drop in (F15, list import): CSV / TXT (comma, semicolon or tab,
 * quotes respected) and Excel .xlsx (its first sheet). .xlsx is a zip of XML files: read with the
 * browser's own DecompressionStream, no extra library. Values come back as trimmed strings.
 */

/** CSV text → rows. The delimiter is guessed from the first line when not given. */
export function parseCsv(text: string, delimiter?: string): string[][] {
  const clean = text.replace(/^﻿/, '')
  const first = clean.split(/\r?\n/, 1)[0] ?? ''
  const sep = delimiter ?? (['\t', ';', ','].map(char => [char, first.split(char).length] as const).sort((a, b) => b[1] - a[1])[0]![0])
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < clean.length; i++) {
    const char = clean[i]!
    if (quoted) {
      if (char === '"' && clean[i + 1] === '"') {
        cell += '"'
        i++
      } else if (char === '"') quoted = false
      else cell += char
    } else if (char === '"' && cell === '') quoted = true
    else if (char === sep) {
      row.push(cell.trim())
      cell = ''
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && clean[i + 1] === '\n') i++
      row.push(cell.trim())
      rows.push(row)
      row = []
      cell = ''
    } else cell += char
  }
  if (cell || row.length) {
    row.push(cell.trim())
    rows.push(row)
  }
  return rows.filter(item => item.some(value => value !== ''))
}

// ── .xlsx ────────────────────────────────────────────────────────────────────────────

async function inflate(data: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([data as BlobPart]).stream().pipeThrough(new DecompressionStream('deflate-raw'))
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

/** The files inside a zip, by name (only those asked for). */
async function unzip(buffer: ArrayBuffer, wanted: (name: string) => boolean): Promise<Map<string, string>> {
  const view = new DataView(buffer)
  const bytes = new Uint8Array(buffer)
  let end = -1
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65_557); i--)
    if (view.getUint32(i, true) === 0x06054b50) {
      end = i
      break
    }
  if (end < 0) throw new Error('not_zip')
  const count = view.getUint16(end + 10, true)
  let at = view.getUint32(end + 16, true)
  const files = new Map<string, string>()
  const decoder = new TextDecoder()
  for (let n = 0; n < count; n++) {
    if (view.getUint32(at, true) !== 0x02014b50) break
    const method = view.getUint16(at + 10, true)
    const size = view.getUint32(at + 20, true)
    const nameLength = view.getUint16(at + 28, true)
    const extraLength = view.getUint16(at + 30, true)
    const commentLength = view.getUint16(at + 32, true)
    const local = view.getUint32(at + 42, true)
    const name = decoder.decode(bytes.subarray(at + 46, at + 46 + nameLength))
    at += 46 + nameLength + extraLength + commentLength
    if (!wanted(name)) continue
    const start = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true)
    const raw = bytes.subarray(start, start + size)
    files.set(name, decoder.decode(method === 8 ? await inflate(raw) : raw))
  }
  return files
}

const columnIndex = (ref: string) => [...(ref.match(/^[A-Z]+/)?.[0] ?? 'A')].reduce((sum, char) => sum * 26 + char.charCodeAt(0) - 64, 0) - 1

async function readXlsx(buffer: ArrayBuffer): Promise<string[][]> {
  const files = await unzip(buffer, name => name === 'xl/sharedStrings.xml' || /^xl\/worksheets\/sheet\d+\.xml$/.test(name))
  const parser = new DOMParser()
  const shared = files.has('xl/sharedStrings.xml')
    ? [...parser.parseFromString(files.get('xl/sharedStrings.xml')!, 'application/xml').getElementsByTagName('si')].map(si => [...si.getElementsByTagName('t')].map(t => t.textContent ?? '').join(''))
    : []
  const sheetName = [...files.keys()].filter(name => name.startsWith('xl/worksheets/')).sort((a, b) => Number(a.match(/\d+/)![0]) - Number(b.match(/\d+/)![0]))[0]
  if (!sheetName) return []
  const sheet = parser.parseFromString(files.get(sheetName)!, 'application/xml')
  const rows: string[][] = []
  for (const rowElement of sheet.getElementsByTagName('row')) {
    const row: string[] = []
    for (const cell of rowElement.getElementsByTagName('c')) {
      const type = cell.getAttribute('t')
      const value = cell.getElementsByTagName('v')[0]?.textContent ?? ''
      const text = type === 's' ? (shared[Number(value)] ?? '') : type === 'inlineStr' ? [...cell.getElementsByTagName('t')].map(t => t.textContent ?? '').join('') : type === 'b' ? (value === '1' ? 'TRUE' : 'FALSE') : value
      row[columnIndex(cell.getAttribute('r') ?? '')] = text.trim()
    }
    rows.push(Array.from(row, value => value ?? ''))
  }
  return rows.filter(item => item.some(value => value !== ''))
}

/** Rows from a CSV, TXT or XLSX file (first sheet). Throws `unsupported` for anything else. */
export async function readTable(file: File): Promise<string[][]> {
  const name = file.name.toLowerCase()
  if (name.endsWith('.xlsx')) return readXlsx(await file.arrayBuffer())
  if (name.endsWith('.csv') || name.endsWith('.txt') || file.type.startsWith('text/')) return parseCsv(await file.text())
  throw new Error('unsupported')
}

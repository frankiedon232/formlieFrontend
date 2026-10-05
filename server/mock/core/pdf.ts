/**
 * A small text-only PDF writer for the mock (response exports, sample files): pages of A4 with a
 * title and lines in Helvetica, wrapped and paged. Characters outside Latin-1 become "?" (the
 * real backend renders every script with embedded fonts).
 */
const A4 = { width: 595, height: 842, margin: 56 }

const clean = (text: string) =>
  text
    .normalize('NFC')
    .replace(/[^ -ÿ]/g, '?')
    .replace(/[()\\]/g, match => `\\${match}`)

function wrap(text: string, size: number): string[] {
  const max = Math.floor((A4.width - A4.margin * 2) / (size * 0.5))
  const out: string[] = []
  for (const paragraph of text.split('\n')) {
    let line = ''
    for (const word of paragraph.split(' ')) {
      if ((line + ' ' + word).trim().length > max && line) {
        out.push(line)
        line = word
      } else line = (line + ' ' + word).trim()
    }
    out.push(line)
  }
  return out
}

/** `lines`: plain text; a line starting with "# " is a heading. */
export function textPdf(title: string, lines: string[]): Uint8Array {
  type Row = { text: string; size: number; bold: boolean; gap: number }
  const rows: Row[] = [{ text: title, size: 16, bold: true, gap: 26 }]
  for (const line of lines) {
    const heading = line.startsWith('# ')
    const size = heading ? 12 : 10
    for (const part of wrap(heading ? line.slice(2) : line, size)) rows.push({ text: part, size, bold: heading, gap: heading ? 20 : 14 })
  }
  const pages: Row[][] = [[]]
  let y = A4.height - A4.margin
  for (const row of rows) {
    if (y - row.gap < A4.margin) {
      pages.push([])
      y = A4.height - A4.margin
    }
    y -= row.gap
    pages.at(-1)!.push(row)
  }
  const objects: string[] = ['<< /Type /Catalog /Pages 2 0 R >>', '']
  const kids: number[] = []
  const fontRegular = 3
  const fontBold = 4
  objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
  objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
  pages.forEach((page, index) => {
    let cursor = A4.height - A4.margin
    const body = page
      .map(row => {
        cursor -= row.gap
        return `BT /F${row.bold ? 2 : 1} ${row.size} Tf ${A4.margin} ${cursor} Td (${clean(row.text)}) Tj ET`
      })
      .join('\n')
    const footer = `BT /F1 8 Tf ${A4.margin} 28 Td (${clean(`${title} - ${index + 1} / ${pages.length}`)}) Tj ET`
    const stream = `${body}\n${footer}`
    objects.push(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`)
    const contents = objects.length
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${A4.width} ${A4.height}] /Contents ${contents} 0 R /Resources << /Font << /F1 ${fontRegular} 0 R /F2 ${fontBold} 0 R >> >> >>`)
    kids.push(objects.length)
  })
  objects[1] = `<< /Type /Pages /Kids [${kids.map(k => `${k} 0 R`).join(' ')}] /Count ${kids.length} >>`
  let pdf = '%PDF-1.4\n'
  const offsets = objects.map((object, i) => {
    const at = pdf.length
    pdf += `${i + 1} 0 obj\n${object}\nendobj\n`
    return at
  })
  const xref = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map(at => `${String(at).padStart(10, '0')} 00000 n \n`).join('')}`
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  return Uint8Array.from(pdf, char => char.charCodeAt(0) & 0xff)
}

/**
 * A small PDF layout writer for the mock (owner 2026-10-05: the export PDF must look designed, not
 * plain text). A4 pages with filled and rounded boxes, lines, Helvetica regular / bold in any
 * colour, text measured with Helvetica's real character widths (so wrapping and right alignment
 * are exact), and a footer on every page with "Page x of y". Text outside Latin-1 shows as "?"
 * (the real backend embeds fonts for every script).
 */
export const PAGE = { width: 595.28, height: 841.89 }

// Helvetica advance widths (1/1000 em) for ASCII 32–126, from the standard font metrics.
const WIDTHS = [
  278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667,
  722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278,
  556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
const charWidth = (char: string) => {
  const code = char.charCodeAt(0)
  return code >= 32 && code <= 126 ? WIDTHS[code - 32]! : 556
}
export function textWidth(text: string, size: number, bold = false): number {
  let units = 0
  for (const char of text) units += charWidth(char)
  return (units / 1000) * size * (bold ? 1.06 : 1)
}

/** Lines that fit `width` (words kept whole unless a single word is too long). */
export function wrapText(text: string, size: number, width: number, bold = false): string[] {
  const lines: string[] = []
  for (const paragraph of text.split('\n')) {
    let line = ''
    for (const word of paragraph.split(/\s+/).filter(Boolean)) {
      const next = line ? `${line} ${word}` : word
      if (textWidth(next, size, bold) <= width) line = next
      else {
        if (line) lines.push(line)
        let rest = word
        while (textWidth(rest, size, bold) > width && rest.length > 1) {
          let cut = rest.length - 1
          while (cut > 1 && textWidth(rest.slice(0, cut), size, bold) > width) cut--
          lines.push(rest.slice(0, cut))
          rest = rest.slice(cut)
        }
        line = rest
      }
    }
    lines.push(line)
  }
  return lines
}

// Characters the PDF's WinAnsi encoding has outside Latin-1 (dashes, curly quotes, bullet, euro…).
const WIN_ANSI: Record<string, number> = { '€': 0x80, '‚': 0x82, '„': 0x84, '…': 0x85, '‘': 0x91, '’': 0x92, '“': 0x93, '”': 0x94, '•': 0x95, '–': 0x96, '—': 0x97, '™': 0x99 }
const clean = (text: string) =>
  text
    .normalize('NFC')
    .replace(/[€‚„…‘’“”•–—™]/g, char => String.fromCharCode(WIN_ANSI[char]!))
    .replace(/[^ -ÿ]/g, '?')
    .replace(/[()\\]/g, match => `\\${match}`)
const rgb = (hex: string) => {
  const value = /^#?([0-9a-f]{6})$/i.exec(hex)?.[1] ?? '18181b'
  return [0, 2, 4].map(i => (parseInt(value.slice(i, i + 2), 16) / 255).toFixed(3)).join(' ')
}
const n = (value: number) => value.toFixed(2)

export interface TextOptions {
  size?: number
  bold?: boolean
  color?: string
  /** x is the right edge (right-aligned text). */
  right?: boolean
}

/** Drawing commands per page; coordinates from the top-left corner, in points. */
export class PdfDoc {
  private pages: string[][] = []
  private current: string[] = []

  constructor() {
    this.addPage()
  }

  addPage() {
    this.current = []
    this.pages.push(this.current)
  }

  get pageCount() {
    return this.pages.length
  }

  rect(x: number, y: number, width: number, height: number, fill: string, radius = 0) {
    const top = PAGE.height - y
    if (!radius) {
      this.current.push(`${rgb(fill)} rg ${n(x)} ${n(top - height)} ${n(width)} ${n(height)} re f`)
      return
    }
    const r = Math.min(radius, width / 2, height / 2)
    const k = r * 0.5523
    const left = x
    const right = x + width
    const bottom = top - height
    this.current.push(
      `${rgb(fill)} rg ${n(left + r)} ${n(top)} m ${n(right - r)} ${n(top)} l ${n(right - r + k)} ${n(top)} ${n(right)} ${n(top - r + k)} ${n(right)} ${n(top - r)} c ` +
        `${n(right)} ${n(bottom + r)} l ${n(right)} ${n(bottom + r - k)} ${n(right - r + k)} ${n(bottom)} ${n(right - r)} ${n(bottom)} c ` +
        `${n(left + r)} ${n(bottom)} l ${n(left + r - k)} ${n(bottom)} ${n(left)} ${n(bottom + r - k)} ${n(left)} ${n(bottom + r)} c ` +
        `${n(left)} ${n(top - r)} l ${n(left)} ${n(top - r + k)} ${n(left + r - k)} ${n(top)} ${n(left + r)} ${n(top)} c f`,
    )
  }

  line(x1: number, y1: number, x2: number, y2: number, color: string, width = 0.6) {
    this.current.push(`${rgb(color)} RG ${n(width)} w ${n(x1)} ${n(PAGE.height - y1)} m ${n(x2)} ${n(PAGE.height - y2)} l S`)
  }

  /** `y` is the text's baseline. */
  text(x: number, y: number, value: string, options: TextOptions = {}) {
    const size = options.size ?? 10
    const left = options.right ? x - textWidth(value, size, options.bold) : x
    this.current.push(`BT ${rgb(options.color ?? '#18181b')} rg /F${options.bold ? 2 : 1} ${n(size)} Tf ${n(left)} ${n(PAGE.height - y)} Td (${clean(value)}) Tj ET`)
  }

  /** The finished file; `footer` draws on every page once the page count is known. */
  render(footer?: (doc: PdfDoc, page: number, pages: number) => void): Uint8Array {
    if (footer)
      this.pages.forEach((commands, index) => {
        this.current = commands
        footer(this, index + 1, this.pages.length)
      })
    const objects: string[] = ['<< /Type /Catalog /Pages 2 0 R >>', '']
    objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
    const kids: number[] = []
    for (const commands of this.pages) {
      const stream = commands.join('\n')
      objects.push(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`)
      const contents = objects.length
      objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${n(PAGE.width)} ${n(PAGE.height)}] /Contents ${contents} 0 R /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>`)
      kids.push(objects.length)
    }
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
}

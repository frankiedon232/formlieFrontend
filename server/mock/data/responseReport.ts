/**
 * The PDF of a response export (owner 2026-10-05: "no arrangement, no branding, no theme, no life").
 * A designed report in the form's own colour: a cover band with the organisation, the form and who
 * exported what and when; a row of status tiles; then one card per response (number, name, status
 * pill, email, submitted, channel, tags) with its questions and answers in two columns. Cards never
 * start at the foot of a page and continue cleanly onto the next; every page has a slim brand bar,
 * the form and organisation, and "Page x of y".
 */
import type { ResponseStatus } from '#shared/types/responses'
import { readableOn } from '#shared/utils/forms/theme'
import { PAGE, PdfDoc, textWidth, wrapText } from '../core/pdfDoc'

export interface ReportResponse {
  number: number
  name: string
  email: string
  submitted: string
  status: ResponseStatus
  channel: string
  tags: string[]
  answers: { question: string; answer: string }[]
}

export interface ReportInput {
  org: string
  form: string
  brand: string
  exportedBy: string
  exportedAt: Date
  scope: string
  counts: Record<ResponseStatus, number>
  responses: ReportResponse[]
}

const INK = '#18181b'
const MUTED = '#71717a'
const LINE = '#e4e4e7'
const SOFT = '#f4f4f5'
const STATUS: Record<ResponseStatus, { label: string; color: string; fill: string }> = {
  new: { label: 'New', color: '#18181b', fill: '#e4e4e7' },
  reviewed: { label: 'Reviewed', color: '#b45309', fill: '#fef3c7' },
  approved: { label: 'Approved', color: '#15803d', fill: '#dcfce7' },
  rejected: { label: 'Rejected', color: '#b91c1c', fill: '#fee2e2' },
}
const CHANNEL: Record<string, string> = { link: 'Form link', embed: 'Embedded', api: 'API' }
const M = 40
const RIGHT = PAGE.width - M
const BOTTOM = PAGE.height - 56
const Q_X = M + 12
const Q_W = 168
const A_X = Q_X + Q_W + 14
const A_W = RIGHT - 12 - A_X

const when = (date: Date) =>
  `${date.getUTCDate()} ${date.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })} ${date.getUTCFullYear()}, ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')} UTC`
const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join('') || 'F'

export function responseReport(input: ReportInput): Uint8Array {
  const doc = new PdfDoc()
  const onBrand = readableOn(input.brand)
  let y = 0

  // ── Cover ───────────────────────────────────────────────────────────────────────
  doc.rect(0, 0, PAGE.width, 132, input.brand)
  doc.rect(M, 28, 30, 30, onBrand, 6)
  doc.text(M + 15 - textWidth(initials(input.org), 11, true) / 2, 47, initials(input.org), { size: 11, bold: true, color: input.brand })
  doc.text(M + 40, 47, input.org, { size: 12, bold: true, color: onBrand })
  doc.text(RIGHT, 47, 'Responses export', { size: 9, color: onBrand, right: true })
  const title = wrapText(input.form, 22, RIGHT - M, true)[0] ?? input.form
  doc.text(M, 92, title, { size: 22, bold: true, color: onBrand })
  doc.text(M, 113, `Exported ${when(input.exportedAt)} by ${input.exportedBy}  ·  ${input.responses.length} responses  ·  ${input.scope}`, { size: 9.5, color: onBrand })

  // ── Status tiles ────────────────────────────────────────────────────────────────
  const tiles: { label: string; value: number; color: string }[] = [
    { label: 'Responses', value: input.responses.length, color: input.brand },
    ...(Object.keys(STATUS) as ResponseStatus[]).map(key => ({ label: STATUS[key].label, value: input.counts[key], color: STATUS[key].color })),
  ]
  const tileW = (RIGHT - M - 8 * (tiles.length - 1)) / tiles.length
  tiles.forEach((tile, i) => {
    const x = M + i * (tileW + 8)
    doc.rect(x, 150, tileW, 54, SOFT, 6)
    doc.rect(x + 10, 162, 7, 7, tile.color, 1.5)
    doc.text(x + 22, 169, tile.label, { size: 8.5, color: MUTED })
    doc.text(x + 10, 193, tile.value.toLocaleString('en-GB'), { size: 16, bold: true, color: INK })
  })
  y = 226

  // ── Following pages: a slim brand bar and the form ─────────────────────────────
  const newPage = () => {
    doc.addPage()
    doc.rect(0, 0, PAGE.width, 6, input.brand)
    doc.text(M, 30, input.form, { size: 9, bold: true, color: INK })
    doc.text(RIGHT, 30, input.org, { size: 9, color: MUTED, right: true })
    doc.line(M, 40, RIGHT, 40, LINE)
    y = 58
  }

  // ── One card per response ───────────────────────────────────────────────────────
  for (const response of input.responses) {
    const rows = response.answers.map(item => {
      const q = wrapText(item.question, 8.5, Q_W)
      const a = item.answer ? wrapText(item.answer, 10, A_W) : ['–']
      return { q, a, empty: !item.answer, height: Math.max(q.length * 11, a.length * 13) + 10 }
    })
    const header = 46
    // Never start a card at the foot of a page: its header and first answer stay together.
    if (y + header + (rows[0]?.height ?? 0) > BOTTOM) newPage()

    const drawHeader = (continued: boolean) => {
      doc.rect(M, y, RIGHT - M, header, SOFT, 6)
      doc.rect(M, y, 4, header, input.brand, 2)
      doc.text(Q_X, y + 19, `#${response.number}`, { size: 11, bold: true, color: input.brand })
      const nameX = Q_X + textWidth(`#${response.number}`, 11, true) + 8
      doc.text(nameX, y + 19, `${response.name || response.email || 'Anonymous'}${continued ? '  (continued)' : ''}`, { size: 11, bold: true, color: INK })
      const status = STATUS[response.status]
      const pillW = textWidth(status.label, 8, true) + 16
      doc.rect(RIGHT - 12 - pillW, y + 9, pillW, 15, status.fill, 7.5)
      doc.text(RIGHT - 12 - pillW / 2 - textWidth(status.label, 8, true) / 2, y + 19.5, status.label, { size: 8, bold: true, color: status.color })
      const meta = [response.email, response.submitted, CHANNEL[response.channel] ?? response.channel, response.tags.length ? `Tags: ${response.tags.join(', ')}` : ''].filter(Boolean).join('   ·   ')
      doc.text(Q_X, y + 35, wrapText(meta, 8.5, RIGHT - 24 - Q_X)[0] ?? '', { size: 8.5, color: MUTED })
      y += header + 6
    }
    drawHeader(false)
    for (const row of rows) {
      if (y + row.height > BOTTOM) {
        newPage()
        drawHeader(true)
      }
      row.q.forEach((line, i) => doc.text(Q_X, y + 12 + i * 11, line, { size: 8.5, color: MUTED }))
      row.a.forEach((line, i) => doc.text(A_X, y + 12 + i * 13, line, { size: 10, color: row.empty ? '#a1a1aa' : INK }))
      y += row.height
      doc.line(Q_X, y - 3, RIGHT - 12, y - 3, LINE, 0.5)
    }
    y += 18
  }

  // ── Footer on every page ────────────────────────────────────────────────────────
  return doc.render((page, number, pages) => {
    page.line(M, PAGE.height - 40, RIGHT, PAGE.height - 40, LINE)
    page.text(M, PAGE.height - 26, `${input.org}  ·  ${input.form}  ·  ${when(input.exportedAt)}`, { size: 8, color: MUTED })
    page.text(RIGHT, PAGE.height - 26, `Page ${number} of ${pages}`, { size: 8, bold: true, color: INK, right: true })
  })
}

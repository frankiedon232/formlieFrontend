/**
 * Files in responses (F11 file viewer). Respondents' files are personal data and never public:
 *   POST /responses/:id/files { field, index } (enveloped, "Responses only" or more on the form) →
 *     a private link for that one file, valid 5 minutes, bound to the workspace;
 *   GET /response-files/:token (plain, so an <img>, <video> or PDF frame can load it) serves it
 *     inline, or as a download with ?download=1.
 * Sample responses' files get a generated stand-in (a picture, a one-page PDF, or a short text),
 * so the viewer can be tried on seeded forms.
 */
import { randomBytes } from 'node:crypto'
import { z } from 'zod'
import { fileAnswers } from '#shared/utils/forms/file-answers'
import { requireAuth, tenantOf } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { answersOf } from '../data/responseData'
import { responseFor } from './responses'
import { respondentFileBytes } from './uploads'

const TTL_MS = 5 * 60 * 1000
/** What a browser shows by itself. */
const PREVIEWABLE = /^(image\/(png|jpe?g|gif|webp|avif|svg\+xml|bmp)|application\/pdf|video\/(mp4|webm|ogg)|audio\/(mpeg|mp3|ogg|wav|webm|mp4|aac|x-m4a)|text\/(plain|csv))$/i

interface FileLink {
  tenantId: string
  expires: number
  name: string
  type: string
  source: { kind: 'upload'; id: string } | { kind: 'sample'; size: number }
}
const links = new Map<string, FileLink>()

const body = z.object({ field: z.string().max(64), index: z.number().int().min(0).max(50) })

/** POST /responses/:id/files, a 5-minute private link to one file of the response. */
export const fileLink = defineMockRoute(({ event, body: raw }) => {
  const { tenant, user } = requireAuth(event)
  const input = parseBody(body, raw)
  const { form, entry } = responseFor(tenant, user, getRouterParam(event, 'id'), 'view')
  const files = fileAnswers(answersOf(form, entry)[input.field]) as (ReturnType<typeof fileAnswers>[number] & { sample?: boolean })[]
  const file = files[input.index]
  if (!file) throw new MockError('FRM-GEN-1004')
  for (const [token, link] of links) if (link.expires < Date.now()) links.delete(token)
  const token = randomBytes(24).toString('base64url')
  const sample = !!file.sample || !file.id
  links.set(token, {
    tenantId: tenant.id,
    expires: Date.now() + TTL_MS,
    name: file.name,
    type: file.type || 'application/octet-stream',
    source: sample ? { kind: 'sample', size: file.size } : { kind: 'upload', id: file.id },
  })
  const url = `/api/v1/response-files/${token}`
  return ok({
    url,
    download_url: `${url}?download=1`,
    name: file.name,
    type: file.type,
    size: file.size,
    previewable: PREVIEWABLE.test(file.type),
    sample,
    expires_at: new Date(Date.now() + TTL_MS).toISOString(),
  })
})

// ── Sample stand-ins ──────────────────────────────────────────────────────────────────
const escapeXml = (text: string) => text.replace(/[<>&"']/g, char => `&#${char.charCodeAt(0)};`)
function samplePicture(name: string): string {
  const hue = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 360
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl(${hue},45%,82%)"/><stop offset="1" stop-color="hsl(${(hue + 40) % 360},40%,62%)"/></linearGradient></defs>
<rect width="1200" height="800" fill="url(#g)"/><circle cx="880" cy="250" r="90" fill="#fff" opacity=".55"/>
<path d="M0 640 L300 420 L520 600 L760 380 L1200 700 L1200 800 L0 800 Z" fill="#fff" opacity=".45"/>
<text x="60" y="740" font-family="Arial, sans-serif" font-size="40" fill="#1a1a1a" opacity=".75">${escapeXml(name)} · sample picture</text></svg>`
}
function samplePdf(name: string): Uint8Array {
  const text = `Sample document: ${name}`.replace(/[()\\]/g, '')
  const stream = `BT /F1 24 Tf 72 720 Td (${text}) Tj 0 -36 Td /F1 14 Tf (A stand-in for a file in a sample response.) Tj ET`
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  let pdf = '%PDF-1.4\n'
  const offsets = objects.map((object, i) => {
    const at = pdf.length
    pdf += `${i + 1} 0 obj\n${object}\nendobj\n`
    return at
  })
  const xref = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map(at => `${String(at).padStart(10, '0')} 00000 n \n`).join('')}`
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  return new TextEncoder().encode(pdf)
}

/** GET /response-files/:token, the file itself (inline, or ?download=1 to save it). */
export const serveResponseFile = defineEventHandler(event => {
  const link = links.get(getRouterParam(event, 'token') ?? '')
  const host = tenantOf(event)
  // Browser loads can't send the dev tenant header, so localhost / LAN addresses skip the host check.
  const isLocal = host.context.kind === 'manage' && host.context.reason === 'local'
  if (!link || link.expires < Date.now() || (!isLocal && host.tenant?.id !== link.tenantId)) {
    setResponseStatus(event, 410)
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    return 'This file link has expired. Open the file again from the response.'
  }
  const download = getQuery(event).download === '1'
  let type = link.type
  let name = link.name
  let data: Uint8Array | string
  if (link.source.kind === 'upload') {
    const file = respondentFileBytes(link.source.id, link.tenantId)
    if (!file) {
      setResponseStatus(event, 404)
      return 'Not found'
    }
    data = file.data
  } else if (type.startsWith('image/')) {
    type = 'image/svg+xml'
    data = samplePicture(name)
    if (download) name = name.replace(/\.[^.]+$/, '') + '.svg'
  } else if (type === 'application/pdf') {
    data = samplePdf(name)
  } else {
    type = 'text/plain; charset=utf-8'
    data = `This is a stand-in for "${name}", a file in a sample response.\n`
    name = `${name}.txt`
  }
  setHeader(event, 'content-type', type)
  setHeader(event, 'x-content-type-options', 'nosniff')
  setHeader(event, 'cache-control', 'private, no-store')
  // Never run anything a file carries: SVG as an image only.
  if (type.startsWith('image/svg')) setHeader(event, 'content-security-policy', "default-src 'none'; style-src 'unsafe-inline'; sandbox")
  setHeader(event, 'content-disposition', `${download ? 'attachment' : 'inline'}; filename="${encodeURIComponent(name)}"`)
  return data
})

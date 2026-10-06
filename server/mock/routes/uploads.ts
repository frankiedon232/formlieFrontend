/**
 * Mock uploads (SECURITY-PROTOCOL.md: files go straight to object storage through a pre-signed,
 * expiring URL; only the request that obtains the URL is enveloped).
 *   POST /uploads → ticket · PUT /storage/:token (plain, the "object storage") · POST /uploads/:id/complete
 *   GET /files/:id serves the stored file (a CDN URL in production).
 */
import { z } from 'zod'
import { decodeId } from '../core/ids'
import { MAX_RESPONDENT_FILE_BYTES } from '#shared/utils/forms/file-answers'
import type { UploadedFile, UploadTicket } from '#shared/types/onboarding'
import type { FileAnswer } from '#shared/types/public'
import { requireAdmin, requireAuth } from '../core/auth'
import { loadPersisted, savePersisted } from '../core/persist'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'

/** What each purpose may upload: logos (admins, 2 MB) and images inside forms (members, 5 MB). */
const PURPOSES = {
  logo: { types: ['image/png', 'image/jpeg', 'image/webp'], maxBytes: 2 * 1024 * 1024, admin: true },
  /** Link preview image (F10 M3): what WhatsApp, LinkedIn… show, no SVG (social sites don't show it). */
  share_image: { types: ['image/png', 'image/jpeg', 'image/webp'], maxBytes: 5 * 1024 * 1024, admin: false },
  form_image: {
    types: ['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml'],
    maxBytes: 5 * 1024 * 1024,
    admin: false,
  },
} as const
type Purpose = keyof typeof PURPOSES
const MAX_BYTES = Math.max(MAX_RESPONDENT_FILE_BYTES, ...Object.values(PURPOSES).map(p => p.maxBytes))
const TICKET_TTL_MS = 5 * 60 * 1000

interface StoredUpload {
  id: string
  tenantId: string
  token: string
  contentType: string
  size: number
  maxBytes: number
  expiresAt: number
  data: Uint8Array | null
  completed: boolean
  /** Respondent files (public forms, F10 M2): never served publicly, only to the workspace (F11). */
  respondent?: {
    formId: string
    field: string
    name: string
    /** image, must really be a picture · file, anything the question allows, never a program. */
    kind: 'image' | 'file'
    /** Extensions the question lists explicitly (a program is accepted only when its type is listed). */
    listed: string[]
    /** The response that uses it (a file is never attached to two responses). */
    responseId?: string
  }
}

// Completed files are kept across dev reloads (base64 in .data/mock/uploads.json) so images in
// forms don't disappear; pending tickets are memory-only.
type SavedUpload = Omit<StoredUpload, 'data'> & { data: string }
const uploads = new Map<string, StoredUpload>(
  loadPersisted<SavedUpload[]>('uploads', []).map(u => [u.id, { ...u, data: Uint8Array.from(Buffer.from(u.data, 'base64')) }]),
)
const saveUploads = () =>
  savePersisted('uploads', () =>
    [...uploads.values()]
      .filter(u => u.completed && u.data)
      .map(u => ({ ...u, data: Buffer.from(u.data!).toString('base64') })),
  )

/** The bytes must really be the declared image type (SVG and anything script-like are refused). */
function looksLike(contentType: string, bytes: Uint8Array): boolean {
  const starts = (...sig: number[]) => sig.every((value, i) => bytes[i] === value)
  if (contentType === 'image/png') return starts(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)
  if (contentType === 'image/jpeg') return starts(0xff, 0xd8, 0xff)
  if (contentType === 'image/webp')
    return starts(0x52, 0x49, 0x46, 0x46) && String.fromCharCode(...bytes.slice(8, 12)) === 'WEBP'
  if (contentType === 'image/gif') return starts(0x47, 0x49, 0x46, 0x38)
  if (contentType === 'image/svg+xml') {
    // SVG is text: accept only a plain drawing, no scripts, event handlers, links to code or embeds.
    const text = new TextDecoder().decode(bytes).slice(0, 2_000_000)
    return /<svg[\s>]/i.test(text) && !/<script|\son\w+\s*=|javascript:|<foreignObject|<iframe|<embed|<object/i.test(text)
  }
  return false
}

/** Respondent pictures: common photo formats by their bytes (SVG is never accepted from respondents). */
function isPicture(bytes: Uint8Array): boolean {
  const starts = (...sig: number[]) => sig.every((value, i) => bytes[i] === value)
  const at = (offset: number, text: string) => String.fromCharCode(...bytes.slice(offset, offset + text.length)) === text
  return (
    ['image/png', 'image/jpeg', 'image/webp', 'image/gif'].some(type => looksLike(type, bytes)) ||
    starts(0x42, 0x4d) || // BMP
    starts(0x49, 0x49, 0x2a, 0x00) || starts(0x4d, 0x4d, 0x00, 0x2a) || // TIFF
    (at(4, 'ftyp') && ['avif', 'avis', 'heic', 'heix', 'hevc', 'mif1', 'msf1'].some(brand => at(8, brand))) // AVIF / HEIC
  )
}

/** Programs (Windows, Linux, macOS) and scripts with a `#!` line. */
function isProgram(bytes: Uint8Array): boolean {
  const starts = (...sig: number[]) => sig.every((value, i) => bytes[i] === value)
  return (
    starts(0x4d, 0x5a) ||
    starts(0x7f, 0x45, 0x4c, 0x46) ||
    starts(0xcf, 0xfa, 0xed, 0xfe) || starts(0xce, 0xfa, 0xed, 0xfe) || starts(0xfe, 0xed, 0xfa, 0xcf) || starts(0xca, 0xfe, 0xba, 0xbe) ||
    starts(0x23, 0x21)
  )
}

/** Does the stored file pass its checks? (Respondent files: picture / not a program; others: the declared image.) */
function bytesAllowed(upload: StoredUpload, bytes: Uint8Array): boolean {
  const respondent = upload.respondent
  if (!respondent) return looksLike(upload.contentType, bytes)
  if (respondent.kind === 'image') return isPicture(bytes)
  const extension = respondent.name.toLowerCase().match(/\.[a-z0-9]+$/)?.[0] ?? ''
  return !isProgram(bytes) || respondent.listed.includes(extension)
}

const ticketSchema = z.object({
  purpose: z.enum(Object.keys(PURPOSES) as [Purpose, ...Purpose[]]),
  file_name: z.string().min(1).max(200),
  content_type: z.string().max(100),
  size: z.number().int().positive(),
})

export const createUpload = defineMockRoute(({ event, body }) => {
  const input = parseBody(ticketSchema, body)
  const rules = PURPOSES[input.purpose]
  const { tenant } = rules.admin ? requireAdmin(event) : requireAuth(event)
  if (!(rules.types as readonly string[]).includes(input.content_type))
    throw new MockError('FRM-GEN-1002', [{ field: 'content_type', message: 'This file type is not allowed.' }])
  if (input.size > rules.maxBytes)
    throw new MockError('FRM-GEN-1002', [
      { field: 'size', message: `The file is larger than ${rules.maxBytes / 1024 / 1024} MB.` },
    ])
  const upload: StoredUpload = {
    id: crypto.randomUUID(),
    tenantId: tenant.id,
    token: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
    contentType: input.content_type,
    size: input.size,
    maxBytes: rules.maxBytes,
    expiresAt: Date.now() + TICKET_TTL_MS,
    data: null,
    completed: false,
  }
  uploads.set(upload.id, upload)
  return ok<UploadTicket>({
    upload_id: upload.id,
    upload_url: `/api/v1/storage/${upload.token}`,
    method: 'PUT',
    headers: { 'content-type': input.content_type },
    max_bytes: rules.maxBytes,
    expires_at: new Date(upload.expiresAt).toISOString(),
  })
})

/** PUT /storage/:token, plain body, like an object-storage pre-signed URL. */
export const storeUpload = defineEventHandler(async event => {
  const token = getRouterParam(event, 'token') ?? ''
  const upload = [...uploads.values()].find(item => item.token === token)
  const refuse = (status: number, message: string) => {
    setResponseStatus(event, status)
    return { error: message }
  }
  if (!upload || upload.expiresAt < Date.now() || upload.data) return refuse(403, 'Upload link expired.')
  if (getHeader(event, 'content-type') !== upload.contentType) return refuse(400, 'Unexpected file type.')
  const raw = await readRawBody(event, false)
  const bytes = raw ? new Uint8Array(raw) : new Uint8Array()
  if (bytes.length === 0 || bytes.length > Math.min(upload.maxBytes, MAX_BYTES) || bytes.length !== upload.size)
    return refuse(400, 'Unexpected file size.')
  if (!bytesAllowed(upload, bytes)) return refuse(400, upload.respondent?.kind === 'file' ? 'This kind of file is not allowed.' : 'The file is not a valid image.')
  upload.data = bytes
  upload.token = ''
  setResponseStatus(event, 204)
  return null
})

export const completeUpload = defineMockRoute(({ event }) => {
  const { tenant } = requireAuth(event)
  const upload = uploads.get(getRouterParam(event, 'id') ?? '')
  if (!upload || upload.tenantId !== tenant.id || !upload.data) throw new MockError('FRM-GEN-1004')
  upload.completed = true
  saveUploads()
  return ok<UploadedFile>({
    id: upload.id,
    url: `/api/v1/files/${upload.id}`,
    content_type: upload.contentType,
    size: upload.size,
  })
})

/** The public URL of a completed upload (logos are shown on the public sign-in page anyway). */
export const serveFile = defineEventHandler(event => {
  // Image addresses carry an encrypted reference (core/ids.ts), never the file's id.
  const upload = uploads.get(decodeId(getRouterParam(event, 'id') ?? '') ?? '')
  // Respondents' files are personal data: only the workspace sees them (responses, F11).
  if (!upload?.completed || !upload.data || upload.respondent) {
    setResponseStatus(event, 404)
    return 'Not found'
  }
  setHeader(event, 'content-type', upload.contentType)
  setHeader(event, 'x-content-type-options', 'nosniff')
  // SVGs open as images only, never as a page that could run anything.
  if (upload.contentType === 'image/svg+xml') setHeader(event, 'content-security-policy', "default-src 'none'; style-src 'unsafe-inline'; sandbox")
  setHeader(event, 'cache-control', 'private, max-age=3600')
  return upload.data
})

/** For the onboarding route: the URL of a completed upload of this workspace, else null. */
export function completedUploadUrl(id: string, tenantId: string): string | null {
  const upload = uploads.get(id)
  return upload?.completed && !upload.respondent && upload.tenantId === tenantId ? `/api/v1/files/${upload.id}` : null
}

// ── Respondent files (public forms, F10 M2, routes in publicForms.ts) ─────────────────────
export interface RespondentTicketInput {
  tenantId: string
  formId: string
  field: string
  name: string
  contentType: string
  size: number
  maxBytes: number
  kind: 'image' | 'file'
  listed: string[]
}

/** A pre-signed upload link for one respondent file. */
export function createRespondentTicket(input: RespondentTicketInput): UploadTicket {
  const upload: StoredUpload = {
    id: crypto.randomUUID(),
    tenantId: input.tenantId,
    token: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
    contentType: input.contentType,
    size: input.size,
    maxBytes: input.maxBytes,
    expiresAt: Date.now() + TICKET_TTL_MS,
    data: null,
    completed: false,
    respondent: { formId: input.formId, field: input.field, name: input.name, kind: input.kind, listed: input.listed },
  }
  uploads.set(upload.id, upload)
  return {
    upload_id: upload.id,
    upload_url: `/api/v1/storage/${upload.token}`,
    method: 'PUT',
    headers: { 'content-type': input.contentType },
    max_bytes: input.maxBytes,
    expires_at: new Date(upload.expiresAt).toISOString(),
  }
}

const answerOf = (upload: StoredUpload): FileAnswer => ({ id: upload.id, name: upload.respondent!.name, size: upload.size, type: upload.contentType })

/** Confirms a respondent file once its bytes are stored → the answer the form keeps. */
export function completeRespondentUpload(id: string, formId: string): FileAnswer | null {
  const upload = uploads.get(id)
  if (!upload?.respondent || upload.respondent.formId !== formId || !upload.data) return null
  upload.completed = true
  saveUploads()
  return answerOf(upload)
}

/** A finished respondent file of this form and question that no other response uses → its answer. */
export function respondentFile(id: string, formId: string, field: string): FileAnswer | null {
  const upload = uploads.get(id)
  const owner = upload?.respondent
  if (!upload?.completed || !owner || owner.formId !== formId || owner.field !== field || owner.responseId) return null
  return answerOf(upload)
}

/** Attaches files to the response that was just stored. */
export function attachRespondentFiles(ids: string[], responseId: string) {
  for (const id of ids) {
    const owner = uploads.get(id)?.respondent
    if (owner) owner.responseId = responseId
  }
  saveUploads()
}

/** A respondent file's bytes for its own workspace (F11 file viewer, behind a short-lived link). */
export function respondentFileBytes(id: string, tenantId: string): { data: Uint8Array; contentType: string; name: string } | null {
  const upload = uploads.get(id)
  if (!upload?.completed || !upload.data || !upload.respondent || upload.tenantId !== tenantId) return null
  return { data: upload.data, contentType: upload.contentType, name: upload.respondent.name }
}

/**
 * A file sent to the API service (F13 M5, `POST /{apiKey}/{endpoint}/files`): the same checks as the
 * form page (bytes must be a real picture for image questions, never a program unless the question
 * lists its type), stored at once as a finished respondent file → its answer. `check` only checks.
 */
export function storeApiFile(input: RespondentTicketInput & { bytes: Uint8Array; check?: boolean }): FileAnswer | 'size' | 'type' {
  if (input.bytes.length === 0 || input.bytes.length > Math.min(input.maxBytes, MAX_BYTES)) return 'size'
  const upload: StoredUpload = {
    id: crypto.randomUUID(),
    tenantId: input.tenantId,
    token: '',
    contentType: input.contentType,
    size: input.bytes.length,
    maxBytes: input.maxBytes,
    expiresAt: Date.now(),
    data: input.bytes,
    completed: true,
    respondent: { formId: input.formId, field: input.field, name: input.name, kind: input.kind, listed: input.listed },
  }
  if (!bytesAllowed(upload, input.bytes)) return 'type'
  if (input.check) return answerOf(upload)
  uploads.set(upload.id, upload)
  saveUploads()
  return answerOf(upload)
}

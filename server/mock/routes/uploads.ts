/**
 * Mock uploads (SECURITY-PROTOCOL.md: files go straight to object storage through a pre-signed,
 * expiring URL; only the request that obtains the URL is enveloped).
 *   POST /uploads → ticket · PUT /storage/:token (plain, the "object storage") · POST /uploads/:id/complete
 *   GET /files/:id serves the stored file (a CDN URL in production).
 */
import { z } from 'zod'
import type { UploadedFile, UploadTicket } from '#shared/types/onboarding'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'

const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp'] as const
const MAX_LOGO_BYTES = 2 * 1024 * 1024
const TICKET_TTL_MS = 5 * 60 * 1000

interface StoredUpload {
  id: string
  tenantId: string
  token: string
  contentType: string
  size: number
  expiresAt: number
  data: Uint8Array | null
  completed: boolean
}

const uploads = new Map<string, StoredUpload>()

/** The bytes must really be the declared image type (SVG and anything script-like are refused). */
function looksLike(contentType: string, bytes: Uint8Array): boolean {
  const starts = (...sig: number[]) => sig.every((value, i) => bytes[i] === value)
  if (contentType === 'image/png') return starts(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)
  if (contentType === 'image/jpeg') return starts(0xff, 0xd8, 0xff)
  if (contentType === 'image/webp')
    return starts(0x52, 0x49, 0x46, 0x46) && String.fromCharCode(...bytes.slice(8, 12)) === 'WEBP'
  return false
}

const ticketSchema = z.object({
  purpose: z.literal('logo'),
  file_name: z.string().min(1).max(200),
  content_type: z.enum(LOGO_TYPES),
  size: z.number().int().positive(),
})

export const createUpload = defineMockRoute(({ event, body }) => {
  const { tenant } = requireAdmin(event)
  const input = parseBody(ticketSchema, body)
  if (input.size > MAX_LOGO_BYTES)
    throw new MockError('FRM-GEN-1002', [{ field: 'size', message: 'The file is larger than 2 MB.' }])
  const upload: StoredUpload = {
    id: crypto.randomUUID(),
    tenantId: tenant.id,
    token: crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, ''),
    contentType: input.content_type,
    size: input.size,
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
    max_bytes: MAX_LOGO_BYTES,
    expires_at: new Date(upload.expiresAt).toISOString(),
  })
})

/** PUT /storage/:token — plain body, like an object-storage pre-signed URL. */
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
  if (bytes.length === 0 || bytes.length > MAX_LOGO_BYTES || bytes.length !== upload.size)
    return refuse(400, 'Unexpected file size.')
  if (!looksLike(upload.contentType, bytes)) return refuse(400, 'The file is not a valid image.')
  upload.data = bytes
  upload.token = ''
  setResponseStatus(event, 204)
  return null
})

export const completeUpload = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const upload = uploads.get(getRouterParam(event, 'id') ?? '')
  if (!upload || upload.tenantId !== tenant.id || !upload.data) throw new MockError('FRM-GEN-1004')
  upload.completed = true
  return ok<UploadedFile>({
    id: upload.id,
    url: `/api/v1/files/${upload.id}`,
    content_type: upload.contentType,
    size: upload.size,
  })
})

/** The public URL of a completed upload (logos are shown on the public sign-in page anyway). */
export const serveFile = defineEventHandler(event => {
  const upload = uploads.get(getRouterParam(event, 'id') ?? '')
  if (!upload?.completed || !upload.data) {
    setResponseStatus(event, 404)
    return 'Not found'
  }
  setHeader(event, 'content-type', upload.contentType)
  setHeader(event, 'x-content-type-options', 'nosniff')
  setHeader(event, 'cache-control', 'private, max-age=3600')
  return upload.data
})

/** For the onboarding route: the URL of a completed upload of this workspace, else null. */
export function completedUploadUrl(id: string, tenantId: string): string | null {
  const upload = uploads.get(id)
  return upload?.completed && upload.tenantId === tenantId ? `/api/v1/files/${upload.id}` : null
}

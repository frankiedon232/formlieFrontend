/**
 * The Worker's logic as pure functions (no Cloudflare APIs), so vitest runs them in Node
 * (test/edge/edge.test.ts). edge/worker.ts wires them to the request.
 */
import { RESERVED_LINKS, SHORT_CODE_PATTERN, isFormAddress } from '../shared/utils/urls/public'
import { contentSecurityPolicy, securityHeaders } from './security-headers'

// ── Paths ───────────────────────────────────────────────────────────────────────────

export type EdgeRoute =
  | { kind: 'api' }
  | { kind: 'short'; code: string }
  | { kind: 'form'; formKey: string; mode: 'fill' | 'embed' }
  | { kind: 'asset' }

/**
 * What a path is. Form pages are exactly `/{formKey}/fill` or `/{formKey}/embed`, where the first
 * segment is a form key or a custom link and never one of the portal's own first segments
 * (RESERVED_LINKS: every top-level page folder in app/pages plus system words).
 */
export function matchRoute(pathname: string): EdgeRoute {
  if (pathname === '/api' || pathname.startsWith('/api/')) return { kind: 'api' }
  const segments = pathname.split('/').slice(1)
  if (segments.length === 2 && segments[0] === 's' && SHORT_CODE_PATTERN.test(segments[1]!))
    return { kind: 'short', code: segments[1]! }
  if (segments.length === 2 && (segments[1] === 'fill' || segments[1] === 'embed')) {
    const formKey = segments[0]!
    if (!RESERVED_LINKS.has(formKey) && isFormAddress(formKey))
      return { kind: 'form', formKey, mode: segments[1] }
  }
  return { kind: 'asset' }
}

// ── Headers to the API ──────────────────────────────────────────────────────────────

/** Headers a visitor may not set themselves: the Worker sets its own (or Cloudflare does). */
const SPOOFABLE = new Set([
  'x-formalie-edge',
  'forwarded',
  'x-real-ip',
  'true-client-ip',
  'x-client-ip',
  'x-original-forwarded-for',
  'host',
])

export function isSpoofable(name: string): boolean {
  const lower = name.toLowerCase()
  return SPOOFABLE.has(lower) || lower.startsWith('x-forwarded-') || lower.startsWith('cf-')
}

/**
 * The headers the Worker sends to the API: the visitor's own (cookies, content type, CSRF and
 * envelope headers…) without anything they could use to pose as the edge, a different host or
 * a different address, then the edge's own.
 */
export function edgeHeaders(
  incoming: Headers,
  edge: { host: string; ip: string | null; secret: string },
): Headers {
  const headers = new Headers()
  incoming.forEach((value, name) => {
    if (!isSpoofable(name)) headers.append(name, value)
  })
  headers.set('X-Formalie-Edge', edge.secret)
  headers.set('X-Forwarded-Host', edge.host)
  headers.set('X-Forwarded-Proto', 'https')
  if (edge.ip) headers.set('X-Forwarded-For', edge.ip)
  return headers
}

// ── Form previews ───────────────────────────────────────────────────────────────────

/** `GET /api/v1/edge/forms/{formKey}/preview` (formlyBackend). */
export interface FormPreview {
  title: string
  description: string | null
  image_url: string | null
  language: string
  indexable: boolean
  site_name: string
  /** Optional: websites allowed to frame the embed (CSP source list); without it any website may. */
  embed_ancestors?: string | null
}

/** Safe in HTML text and in double- or single-quoted attributes. */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** Only absolute https addresses become a preview image (never http, data: or javascript:). */
export function safeImageUrl(value: unknown): string | null {
  if (typeof value !== 'string' || !value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}

const LANGUAGE_TAG = /^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/

/** The preview answer checked field by field (anything odd → null, and the page is served plain). */
export function parsePreview(body: unknown): FormPreview | null {
  if (!body || typeof body !== 'object') return null
  const value = body as Record<string, unknown>
  if (typeof value.title !== 'string' || !value.title.trim()) return null
  return {
    title: value.title.slice(0, 300),
    description:
      typeof value.description === 'string' && value.description.trim()
        ? value.description.slice(0, 1000)
        : null,
    image_url: safeImageUrl(value.image_url),
    language: typeof value.language === 'string' && LANGUAGE_TAG.test(value.language) ? value.language : 'en',
    indexable: value.indexable === true,
    site_name: typeof value.site_name === 'string' ? value.site_name.slice(0, 200) : '',
    embed_ancestors: typeof value.embed_ancestors === 'string' ? value.embed_ancestors : null,
  }
}

/**
 * index.html with the form's title and link-preview tags (chat apps and search engines read
 * them; the app itself still renders in the browser). Every value is escaped.
 */
export function injectMeta(
  html: string,
  preview: FormPreview,
  page: { url: string; embed: boolean },
): string {
  const title = preview.site_name ? `${preview.title} · ${preview.site_name}` : preview.title
  const tags: string[] = [
    `<meta property="og:title" content="${escapeHtml(preview.title)}">`,
    `<meta property="og:type" content="website">`,
    `<meta property="og:url" content="${escapeHtml(page.url)}">`,
  ]
  if (preview.site_name)
    tags.push(`<meta property="og:site_name" content="${escapeHtml(preview.site_name)}">`)
  if (preview.description) {
    tags.push(`<meta name="description" content="${escapeHtml(preview.description)}">`)
    tags.push(`<meta property="og:description" content="${escapeHtml(preview.description)}">`)
  }
  const image = safeImageUrl(preview.image_url)
  if (image) tags.push(`<meta property="og:image" content="${escapeHtml(image)}">`)
  tags.push(`<meta name="twitter:card" content="${image ? 'summary_large_image' : 'summary'}">`)
  // Embeds are never listed; other pages follow the form's own setting.
  if (page.embed || !preview.indexable) tags.push(`<meta name="robots" content="noindex">`)

  let out = /<title>[\s\S]*?<\/title>/i.test(html)
    ? html.replace(/<title>[\s\S]*?<\/title>/i, () => `<title>${escapeHtml(title)}</title>`)
    : html.replace(/<\/head>/i, () => `<title>${escapeHtml(title)}</title></head>`)
  out = out.replace(/<\/head>/i, () => `${tags.join('')}</head>`)
  const lang = LANGUAGE_TAG.test(preview.language) ? preview.language : 'en'
  out = out.replace(
    /<html\b([^>]*)>/i,
    (_match, attributes: string) =>
      `<html${attributes.replace(/\s+lang=("[^"]*"|'[^']*'|[^\s>]*)/i, '')} lang="${escapeHtml(lang)}">`,
  )
  return out
}

// ── Page headers ────────────────────────────────────────────────────────────────────

/** A CSP source: `*`, `'self'`, `'none'` or an https origin (wildcard subdomain allowed). */
const FRAME_SOURCE = /^(?:\*|'self'|'none'|https:\/\/(?:\*\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*(?::\d{1,5})?)$/i

/** The embed's frame-ancestors from the form's allowed websites; anything unexpected → only Formalie itself. */
export function frameAncestors(value: string | null | undefined): string {
  if (value == null || !value.trim()) return '*'
  const sources = value.trim().split(/\s+/)
  return sources.every(source => FRAME_SOURCE.test(source)) ? sources.join(' ') : "'self'"
}

/** The security headers for a page the Worker answers; an embed may be framed by its allowed websites. */
export function pageHeaders(page: { embed: boolean; ancestors?: string | null }): Headers {
  const headers = new Headers(securityHeaders(true))
  headers.set('Content-Type', 'text/html; charset=utf-8')
  headers.set('Cache-Control', 'no-store')
  if (page.embed) {
    headers.delete('X-Frame-Options')
    headers.set('Content-Security-Policy', contentSecurityPolicy(frameAncestors(page.ancestors)))
  }
  return headers
}

/** A short link's destination: only absolute https addresses are followed. */
export function safeRedirect(value: unknown): string | null {
  if (typeof value !== 'string') return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}

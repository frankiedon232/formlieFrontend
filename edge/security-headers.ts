/**
 * Security headers for the portal's pages, one list for every place that serves them:
 *   - development: Nuxt's route rules (nuxt.config.ts, the dev server);
 *   - production: the static build's `_headers` file (Cloudflare static assets) and the Worker
 *     (edge/worker.ts) for the pages it answers itself (form pages).
 * Plain TypeScript without imports, so nuxt.config.ts, the Worker and the tests can all read it.
 */

const CSP_DIRECTIVES = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  // The in-app browser on public forms shows https pages (website, terms, privacy) in a frame (F10).
  "frame-src 'self' https:",
  "frame-ancestors 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
]

/** The Content-Security-Policy; `frameAncestors` replaces `'self'` (embeds: the form's allowed websites). */
export function contentSecurityPolicy(frameAncestors = "'self'"): string {
  return CSP_DIRECTIVES.map(directive =>
    directive.startsWith('frame-ancestors ') ? `frame-ancestors ${frameAncestors}` : directive,
  ).join('; ')
}

/** Headers on every page. `production` adds the CSP (Vite's dev server needs eval and websockets). */
export function securityHeaders(production: boolean): Record<string, string> {
  const headers: Record<string, string> = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'X-Frame-Options': 'SAMEORIGIN',
  }
  if (production) headers['Content-Security-Policy'] = contentSecurityPolicy()
  return headers
}

/** Cloudflare's `_headers` file for the static build: the same headers on every path. */
export function headersFile(): string {
  const lines = Object.entries(securityHeaders(true)).map(([name, value]) => `  ${name}: ${value}`)
  return ['/*', ...lines, ''].join('\n')
}

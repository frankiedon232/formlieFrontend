/**
 * Security headers and redirects for the website (docs/SECURITY.md), one list for every place that serves it:
 *   - development: Nuxt's route rules (nuxt.config.ts) add the same headers, without the CSP (Vite needs eval);
 *   - production: the static build's `_headers` and `_redirects` files for Cloudflare (written by nuxt.config.ts).
 * Plain TypeScript without imports, so nuxt.config.ts and the tests can both read it.
 */

export interface Origins {
  /** Formalie's backend API (the public plans, legal and platform routes). */
  api: string
  /** Formalie's public forms, embedded on /enterprise and /contact. */
  forms: string
}

const origin = (url: string) => new URL(url).origin

/** The Content-Security-Policy: only this site, the backend API and Formalie's own form frames. */
export function contentSecurityPolicy(origins: Origins): string {
  return [
    "default-src 'self'",
    // Nuxt's payload and the JSON-LD blocks are inline scripts; nothing is loaded from another site.
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${origin(origins.api)}`,
    `frame-src ${origin(origins.forms)}`,
    // Nobody embeds the website (docs/SECURITY.md).
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    'upgrade-insecure-requests',
  ].join('; ')
}

/** Headers on every page; `production` adds the CSP. */
export function securityHeaders(origins: Origins, production: boolean): Record<string, string> {
  const headers: Record<string, string> = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'X-Frame-Options': 'DENY',
  }
  if (production) headers['Content-Security-Policy'] = contentSecurityPolicy(origins)
  return headers
}

/** Cloudflare's `_headers` file: the security headers everywhere, long caching for hashed assets. */
export function headersFile(origins: Origins): string {
  const lines = Object.entries(securityHeaders(origins, true)).map(([name, value]) => `  ${name}: ${value}`)
  return [
    '/*',
    ...lines,
    '',
    '/_nuxt/*',
    '  Cache-Control: public, max-age=31536000, immutable',
    '',
    '/_fonts/*',
    '  Cache-Control: public, max-age=31536000, immutable',
    '',
  ].join('\n')
}

/** Short addresses used in emails and older links (owner, 2026-10-13), answered by Cloudflare with a 301. */
export const REDIRECTS: [from: string, to: string][] = [
  ['/terms', '/legal/terms'],
  ['/privacy', '/legal/privacy'],
  ['/refunds', '/legal/refunds'],
  ['/legal', '/legal/privacy'],
]

export function redirectsFile(): string {
  return `${REDIRECTS.map(([from, to]) => `${from} ${to} 301`).join('\n')}\n`
}

/**
 * Security headers for the portal's pages, one list for every place that serves them:
 *   - development: Nuxt's route rules (nuxt.config.ts, the dev server);
 *   - production: the static build's `_headers` file (Cloudflare static assets) and the Worker
 *     (edge/worker.ts) for the pages it answers itself (form pages).
 * Plain TypeScript without imports, so nuxt.config.ts, the Worker and the tests can all read it.
 */

/** Paddle's checkout frames (production and sandbox). */
export const PADDLE_FRAMES = ['https://buy.paddle.com', 'https://sandbox-buy.paddle.com'] as const

const CSP_DIRECTIVES = [
  "default-src 'self'",
  // Paddle.js for the checkout (Paddle, our payment provider, owner 2026-10-13), loaded only when a checkout opens
  "script-src 'self' 'unsafe-inline' https://cdn.paddle.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  // The in-app browser on public forms shows https pages (website, terms, privacy) in a frame (F10); this also lets
  // Paddle's checkout window in (https://buy.paddle.com, https://sandbox-buy.paddle.com).
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
    // Card wallets (Apple Pay, Google Pay) work only inside Paddle's checkout frames
    'Permissions-Policy': `camera=(), microphone=(), geolocation=(), payment=(self ${PADDLE_FRAMES.map(origin => `"${origin}"`).join(' ')}), usb=()`,
    // same-origin-allow-popups, not same-origin: Paddle's checkout (inside its frame) opens PayPal in a pop-up that has
    // to report back, and same-origin cuts that link. The portal is one single-page app whose headers come from the
    // first page loaded, so this can't be set for the billing pages alone; other sites still can't reach this window.
    'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
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

/**
 * Allowed websites of an API service (F13, leftovers L6, owner 2026-10-10): the sites whose pages may call its
 * endpoints straight from a visitor's browser (CORS). A website is an origin: `https://` + host (+ port), no
 * path. Plain `http://` only for localhost, for trying things out. Server apps, mobile apps and Postman send
 * no Origin and are not affected. The same rules in the portal and in the API.
 */

export const MAX_ALLOWED_ORIGINS = 20

/** The origin in its one form (`https://shop.example.com`), or null when it isn't a website address. */
export function normaliseOrigin(value: string): string | null {
  const text = value.trim().toLowerCase().replace(/\/+$/, '')
  if (!text || /\s/.test(text)) return null
  let url: URL
  try {
    url = new URL(text.includes('://') ? text : `https://${text}`)
  } catch {
    return null
  }
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname.endsWith('.localhost')
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && local)) return null
  // A website, not a page: nothing after the host
  if ((url.pathname && url.pathname !== '/') || url.search || url.hash || url.username || url.password) return null
  if (!local && !/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(url.hostname)) return null
  return url.origin
}

/** May a page on `origin` call this service from a browser? */
export const originAllowed = (origin: string | null | undefined, allowed: readonly string[] | undefined): boolean => {
  if (!origin || !allowed?.length) return false
  const normal = normaliseOrigin(origin)
  return !!normal && allowed.includes(normal)
}

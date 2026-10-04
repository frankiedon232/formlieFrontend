/**
 * Websites allowed to show a form's embed (F10 M3, decision 94). People type or paste anything —
 * `https://www.example.com/contact`, `Example.com`, `*.example.com`, `localhost:3000` — and get the
 * host they meant. An empty list = any website. The embed page turns the list into the browser's
 * `frame-ancestors` rule; Formalie's own pages (previews) are always allowed.
 */

const HOST = /^(\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/
const LOCAL = /^(localhost|127\.0\.0\.1)$/

export const MAX_EMBED_DOMAINS = 20

/** A typed website → `host` / `*.host` / `host:port`, or null when it isn't one. */
export function normaliseEmbedDomain(input: string): string | null {
  let value = input.trim().toLowerCase()
  if (!value) return null
  value = value.replace(/^[a-z][a-z0-9+.-]*:\/\//, '') // scheme
  value = value.split(/[/?#]/)[0] ?? '' // path, query
  value = value.replace(/^[^@]*@/, '').replace(/\.$/, '') // user info, trailing dot
  const [host = '', port, ...rest] = value.split(':')
  if (rest.length || (port !== undefined && !/^\d{1,5}$/.test(port))) return null
  const bare = host.startsWith('www.') ? host.slice(4) : host
  if (!HOST.test(bare) && !LOCAL.test(bare)) return null
  return port ? `${bare}:${port}` : bare
}

/** The `frame-ancestors` value: Formalie's own hosts always, then each allowed site (with and without www). */
export function frameAncestors(domains: string[], rootDomain: string): string {
  if (!domains.length) return '*'
  const sources = new Set(["'self'", `https://${rootDomain}`, `https://*.${rootDomain}`])
  for (const domain of domains) {
    const local = LOCAL.test(domain.split(':')[0] ?? '')
    const scheme = local ? 'http' : 'https'
    sources.add(`${scheme}://${domain}`)
    if (local) sources.add(`https://${domain}`)
    if (!domain.startsWith('*.') && !local) sources.add(`https://www.${domain}`)
  }
  return [...sources].join(' ')
}

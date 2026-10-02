/**
 * Classifies the host the app is opened on (docs/01-ARCHITECTURE.md → Subdomain flow).
 * Pure function, shared by the tenant middleware (browser), SSR public forms and the mock API,
 * so every way of reaching the app resolves the same way:
 *
 *   manage.formalie.dev, formalie.dev, www.formalie.dev → manage (default entry)
 *   acme.formalie.dev                                   → tenant "acme"
 *   localhost, 127.0.0.1, [::1], 192.168.x.x            → manage (local dev), or tenant via override
 *   acme.localhost                                       → tenant "acme" (no hosts-file entry needed)
 *   api.formalie.dev, a.b.formalie.dev, "-x-"            → invalid (workspace not found)
 *   forms.customer.com                                   → custom (resolved by the API, later)
 */

export const RESERVED_SUBDOMAINS: readonly string[] = [
  'www',
  'manage',
  'api',
  'app',
  'admin',
  'mail',
  'static',
  'cdn',
  'docs',
  'status',
  'help',
  'support',
  'blog',
  's',
  'auth',
  'login',
  'billing',
  'dev',
  'staging',
  'test',
]

const SUBDOMAIN_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/

export type HostContext =
  | { kind: 'manage'; host: string; reason: 'manage' | 'root' | 'local' }
  | { kind: 'tenant'; host: string; subdomain: string }
  | { kind: 'custom'; host: string }
  | { kind: 'invalid'; host: string; reason: 'reserved' | 'nested' | 'malformed' }

export interface HostResolveOptions {
  rootDomain: string
  manageSubdomain: string
  /** Dev only: force a tenant when the host can't carry one (localhost / IP / phone on LAN). */
  tenantOverride?: string | null
}

/** Lower-cases, strips port, IPv6 brackets and a trailing dot. */
export function normaliseHost(rawHost: string): string {
  let host = rawHost.trim().toLowerCase()
  if (host.startsWith('[')) host = host.slice(1, host.indexOf(']'))
  else if (host.split(':').length === 2) host = host.split(':')[0]!
  return host.replace(/\.$/, '')
}

function isIpAddress(host: string): boolean {
  return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host) || host.includes(':')
}

export function isValidSubdomain(value: string): boolean {
  return SUBDOMAIN_PATTERN.test(value) && !RESERVED_SUBDOMAINS.includes(value)
}

function classifySubdomain(host: string, sub: string, manageSubdomain: string): HostContext {
  if (sub.includes('.')) return { kind: 'invalid', host, reason: 'nested' }
  if (sub === manageSubdomain) return { kind: 'manage', host, reason: 'manage' }
  if (sub === 'www') return { kind: 'manage', host, reason: 'root' }
  if (RESERVED_SUBDOMAINS.includes(sub)) return { kind: 'invalid', host, reason: 'reserved' }
  if (!SUBDOMAIN_PATTERN.test(sub)) return { kind: 'invalid', host, reason: 'malformed' }
  return { kind: 'tenant', host, subdomain: sub }
}

export function resolveHostContext(rawHost: string, options: HostResolveOptions): HostContext {
  const host = normaliseHost(rawHost)
  const rootDomain = options.rootDomain.toLowerCase()
  const isLocal = host === 'localhost' || isIpAddress(host)

  if (isLocal) {
    const override = options.tenantOverride?.trim().toLowerCase()
    if (override) return classifySubdomain(host, override, options.manageSubdomain)
    return { kind: 'manage', host, reason: 'local' }
  }

  if (host === rootDomain) return { kind: 'manage', host, reason: 'root' }

  for (const suffix of [`.${rootDomain}`, '.localhost']) {
    if (host.endsWith(suffix)) {
      return classifySubdomain(host, host.slice(0, -suffix.length), options.manageSubdomain)
    }
  }

  return { kind: 'custom', host }
}

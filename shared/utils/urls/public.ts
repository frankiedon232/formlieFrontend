/**
 * Public URLs — one place for every link Formalie hands out (docs/01-ARCHITECTURE.md → Public URLs).
 *
 *   Forms (fill / embed)
 *     workspace without its own subdomain → https://forms.formalie.com/{formKey}/fill · /embed
 *     workspace with a subdomain          → https://{sub}.formalie.com/{formKey}/fill · /embed
 *     (development: forms.formalie.dev / {sub}.formalie.dev, plus the dev port)
 *
 *   API service (F13)
 *     https://api.formalie.com/{apiKey}/{endpoint}[/{recordId}]   (development: api.formalie.dev)
 *     `apiKey` is a short random public handle for the organisation — not its id, not encrypted;
 *     it only says where a call goes. Who may call is decided by the token, headers and access rules.
 */

export interface PublicHosts {
  /** Shared forms host, e.g. `forms.formalie.dev`. */
  formsHost: string
  /** Root domain for workspace subdomains, e.g. `formalie.dev`. */
  rootDomain: string
  /** Port suffix in development (`:2202`), empty in production. */
  port?: string
}

export type FormLinkKind = 'fill' | 'embed'

/** Host that serves a workspace's public forms. */
export const formsHostFor = (hosts: PublicHosts, subdomain?: string | null) =>
  subdomain ? `${subdomain}.${hosts.rootDomain}` : hosts.formsHost

/** `https://{forms | sub}.formalie.com/{formKey}/fill` (or `/embed`). */
export function formLink(hosts: PublicHosts, formKey: string, kind: FormLinkKind = 'fill', subdomain?: string | null) {
  return `https://${formsHostFor(hosts, subdomain)}${hosts.port ?? ''}/${encodeURIComponent(formKey)}/${kind}`
}

/** A form's public key: 10 random letters / digits (never a database id; 01-ARCHITECTURE → Public URLs). */
export const FORM_KEY_PATTERN = /^[A-Za-z0-9]{10}$/
const KEY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
/** A new random public key (unambiguous letters and digits; ≈ 58 bits). */
export function newPublicKey(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(10))
  return Array.from(bytes, byte => KEY_ALPHABET[byte % KEY_ALPHABET.length]).join('')
}

// ── API service ─────────────────────────────────────────────────────────────────────

/** Organisation API key in the URL: 10 characters, letters and digits (≈ 59 bits, random). */
export const API_KEY_PATTERN = /^[A-Za-z0-9]{10}$/
/** Endpoint names: lower-case words joined by hyphens, 3–64 characters (`register-account`). */
export const ENDPOINT_PATTERN = /^[a-z0-9](?:[a-z0-9-]{1,62}[a-z0-9])$/
/** Methods an endpoint may enable (owner, 2026-10-02: these four only for now). */
export const API_METHODS = ['GET', 'POST', 'PUT', 'DELETE'] as const
export type ApiMethod = (typeof API_METHODS)[number]

/** `https://api.formalie.com/{apiKey}/{endpoint}` — `recordId` for GET one / PUT / DELETE. */
export function apiEndpointUrl(apiServiceUrl: string, apiKey: string, endpoint: string, recordId?: string) {
  const base = apiServiceUrl.replace(/\/+$/, '')
  return `${base}/${apiKey}/${endpoint}${recordId ? `/${encodeURIComponent(recordId)}` : ''}`
}

/** Hosts from the public runtime config; the dev port is taken from the page the user is on. */
export function publicHosts(config: { formsHost: string; rootDomain: string }, currentPort = ''): PublicHosts {
  return { formsHost: config.formsHost, rootDomain: config.rootDomain, port: currentPort ? `:${currentPort}` : '' }
}

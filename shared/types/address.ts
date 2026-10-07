/**
 * Workspace address and own domain (F14 M7, docs/API-CONTRACT.md → Settings). The subdomain can be
 * changed (the old one keeps working for 90 days); an own domain is verified with two DNS records.
 */

export interface DnsRecord {
  type: 'CNAME' | 'TXT'
  name: string
  value: string
  /** Found in DNS at the last check. */
  found: boolean
}

export interface CustomDomain {
  domain: string
  /** pending: waiting for the records · verified: in use, HTTPS issued · failed: records point elsewhere */
  status: 'pending' | 'verified' | 'failed'
  records: DnsRecord[]
  added_at: string
  checked_at: string | null
  /** Why the last check didn't verify, in words for the client to translate. */
  problem: 'not_found' | 'wrong_target' | 'dns_error' | null
}

/** GET /settings/address */
export interface WorkspaceAddress {
  subdomain: string
  /** The portal's address, e.g. https://remedylegal.formalie.com */
  url: string
  /** Old subdomains that still lead here, and until when. */
  previous: { subdomain: string; until: string }[]
  domain: CustomDomain | null
}

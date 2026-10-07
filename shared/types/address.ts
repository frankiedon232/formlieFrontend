/**
 * Workspace address (F14 M7, docs/API-CONTRACT.md → Settings): the subdomain can be changed and the
 * old one keeps working for 90 days. Own domains are not offered (owner, 2026-10-07).
 */

/** GET /settings/address */
export interface WorkspaceAddress {
  subdomain: string
  /** The portal's address, e.g. https://remedylegal.formalie.com */
  url: string
  /** Old subdomains that still lead here, and until when. */
  previous: { subdomain: string; until: string }[]
}

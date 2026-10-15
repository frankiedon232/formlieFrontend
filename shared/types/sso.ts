/**
 * Single sign-on (Settings → Sign-in, owner 2026-10-10; docs/API-CONTRACT.md → Settings). One connection per
 * workspace to the company's identity provider. Three choices (owner 2026-10-15): Microsoft Entra ID (OpenID
 * Connect), Google Workspace (SAML 2.0) and SAML 2.0 for every other provider (Okta, OneLogin, JumpCloud, ADFS, Ping,
 * Auth0, Keycloak and others all support it). Secrets are write-only: the API says whether one is set, never what it is.
 */

export const SSO_PROVIDERS = ['entra', 'google_workspace', 'saml'] as const
export type SsoProvider = (typeof SSO_PROVIDERS)[number]
export type SsoProtocol = 'saml' | 'oidc'
/** draft = saved, not tested · tested = the test passed · active = shown on the sign-in page. */
export type SsoStatus = 'draft' | 'tested' | 'active'
export type SsoProblem = 'unreachable' | 'not_metadata' | 'not_discovery' | 'issuer_mismatch' | 'incomplete'

export interface SsoSamlConfig {
  /** The provider's metadata address (preferred: keeps certificates up to date). */
  metadata_url: string | null
  /** Or the values by hand. */
  entity_id: string | null
  sso_url: string | null
  certificate: string | null
}

export interface SsoOidcConfig {
  /** Microsoft Entra ID: https://login.microsoftonline.com/{tenant}/v2.0 */
  issuer: string | null
  client_id: string | null
  /** True when a client secret is stored (never returned). */
  has_secret: boolean
}

export interface SsoConnection {
  provider: SsoProvider
  protocol: SsoProtocol
  /** The button text on the sign-in page, e.g. "Acme" → "Continue with Acme". */
  label: string
  saml: SsoSamlConfig
  oidc: SsoOidcConfig
  /** Email domains that sign in through the provider (typing such an address goes straight there). */
  domains: string[]
  /** People with these domains must use single sign-on (their password and social sign-in stop working). */
  enforce: boolean
  /** Create an account the first time someone from these domains signs in, with this role. */
  auto_create: boolean
  default_role: string
  status: SsoStatus
  tested_at: string | null
  problem: SsoProblem | null
  updated_at: string
}

/** What the identity provider needs from Formalie (copied into Entra ID, Google Workspace or the SAML provider). */
export interface SsoServiceProvider {
  entity_id: string
  acs_url: string
  metadata_url: string
  redirect_uri: string
  signout_url: string
}

/** GET /settings/sso */
export interface SsoSettings {
  connection: SsoConnection | null
  service_provider: SsoServiceProvider
}

/** PUT /settings/sso (client_secret: a new one replaces, left out keeps it). */
export interface SsoSaveRequest {
  provider: SsoProvider
  label: string
  saml?: Partial<Omit<SsoSamlConfig, never>>
  oidc?: { issuer: string | null; client_id: string | null; client_secret?: string | null }
  domains: string[]
  enforce: boolean
  auto_create: boolean
  default_role: string
}

/** On the public sign-in profile when single sign-on is active. */
export interface SsoPublic {
  provider: SsoProvider
  label: string
  domains: string[]
  enforce: boolean
}

/** The protocol each choice uses: Entra ID with OpenID Connect, the other two with SAML 2.0. */
export const SSO_PROTOCOL: Record<SsoProvider, SsoProtocol> = { entra: 'oidc', google_workspace: 'saml', saml: 'saml' }
/** Names in full: "Google Workspace" is the company's single sign-on, not the sign-in page's personal Google button. */
export const SSO_NAMES: Record<SsoProvider, string> = { entra: 'Microsoft Entra ID', google_workspace: 'Google Workspace', saml: 'SAML 2.0' }
export const SSO_ICONS: Record<SsoProvider, string> = { entra: 'i-simple-icons-microsoft', google_workspace: 'i-simple-icons-google', saml: 'i-lucide-file-badge' }
/** Common identity providers set up as SAML 2.0 (named under that choice so an Okta customer knows to pick it). */
export const SAML_PROVIDERS_EXAMPLES = ['Okta', 'OneLogin', 'JumpCloud', 'ADFS', 'Ping', 'Auth0', 'Keycloak'] as const

/**
 * Which SAML tab the form opens on (owner 2026-10-15): a saved connection on the way it was saved (an entity ID without
 * a metadata address = by hand); a new one on its choice's default. Google Workspace gives no metadata address (only
 * values and a download), so by hand; any other SAML 2.0 provider, the metadata address.
 */
export function ssoSamlByHand(provider: SsoProvider, saved: Pick<SsoConnection, 'provider' | 'saml'> | null): boolean {
  if (saved && saved.provider === provider) return !saved.saml.metadata_url && !!saved.saml.entity_id
  return provider === 'google_workspace'
}

/** The form's fields, as typed (empty = not given). */
export interface SsoFormValues {
  label: string
  metadata_url: string
  entity_id: string
  sso_url: string
  certificate: string
  issuer: string
  client_id: string
  /** Typed only to replace the stored one; empty keeps it. */
  client_secret: string
  domains: string[]
  enforce: boolean
  auto_create: boolean
  default_role: string
}

/**
 * PUT /settings/sso from the form: only the chosen protocol's part, and for SAML only the active tab's values (the
 * metadata address alone, or entity ID, sign-on address and certificate). Values on the other tab are never sent.
 */
export function ssoSaveRequest(provider: SsoProvider, samlByHand: boolean, values: SsoFormValues): SsoSaveRequest {
  const protocol = SSO_PROTOCOL[provider]
  return {
    provider,
    label: values.label.trim(),
    saml:
      protocol === 'saml'
        ? samlByHand
          ? { metadata_url: null, entity_id: values.entity_id, sso_url: values.sso_url, certificate: values.certificate }
          : { metadata_url: values.metadata_url, entity_id: null, sso_url: null, certificate: null }
        : undefined,
    oidc: protocol === 'oidc' ? { issuer: values.issuer, client_id: values.client_id, ...(values.client_secret ? { client_secret: values.client_secret } : {}) } : undefined,
    domains: values.domains,
    enforce: values.enforce,
    auto_create: values.auto_create,
    default_role: values.default_role,
  }
}

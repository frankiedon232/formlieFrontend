/**
 * Single sign-on (Settings → Sign-in, owner 2026-10-10; docs/API-CONTRACT.md → Settings). One connection per
 * workspace to the company's identity provider (Okta, Microsoft Entra ID, Google Workspace, OneLogin or any
 * SAML 2.0 / OpenID Connect provider). Secrets are write-only: the API says whether one is set, never what it is.
 */

export const SSO_PROVIDERS = ['okta', 'entra', 'google_workspace', 'onelogin', 'saml', 'oidc'] as const
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
  /** e.g. https://example.okta.com or https://login.microsoftonline.com/{tenant}/v2.0 */
  issuer: string | null
  client_id: string | null
  /** True when a client secret is stored (never returned). */
  has_secret: boolean
}

export interface SsoConnection {
  provider: SsoProvider
  protocol: SsoProtocol
  /** The button text on the sign-in page, e.g. "Okta" → "Continue with Okta". */
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

/** What the identity provider needs from Formalie (copied into Okta etc.). */
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

/** Which protocol each provider uses by default (Okta and Entra could do both; OIDC is the simpler set-up). */
export const SSO_PROTOCOL: Record<SsoProvider, SsoProtocol> = { okta: 'oidc', entra: 'oidc', google_workspace: 'saml', onelogin: 'saml', saml: 'saml', oidc: 'oidc' }
export const SSO_NAMES: Record<SsoProvider, string> = { okta: 'Okta', entra: 'Microsoft Entra ID', google_workspace: 'Google Workspace', onelogin: 'OneLogin', saml: 'SAML 2.0', oidc: 'OpenID Connect' }
export const SSO_ICONS: Record<SsoProvider, string> = { okta: 'i-simple-icons-okta', entra: 'i-simple-icons-microsoft', google_workspace: 'i-simple-icons-google', onelogin: 'i-lucide-key-square', saml: 'i-lucide-file-badge', oidc: 'i-simple-icons-openid' }

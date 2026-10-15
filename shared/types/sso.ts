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

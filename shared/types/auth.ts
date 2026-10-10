import type { DateFormat } from './onboarding'
/** Auth + tenant shapes (docs/API-CONTRACT.md → Tenants, Auth). */

export type AuthProvider = 'password' | 'google' | 'microsoft' | 'apple' | 'facebook'
export type OtpChannel = 'email' | 'sms' | 'totp'
export type TenantStatus = 'active' | 'suspended'
/** Simple workspace role until Roles & access (F22): owner and admin manage the workspace. */
/** A role id: the built-in owner · admin · member, or one the workspace made (Roles & access, F22). */
export type WorkspaceRole = 'owner' | 'admin' | 'member' | (string & {})

/** GET /tenants/public, what the login page of a host may show (no secrets). */
export interface TenantPublicProfile {
  /** `manage` = default entry (signup / find workspace); `tenant` = a workspace. */
  mode: 'manage' | 'tenant'
  name: string
  subdomain: string
  logo_url: string | null
  /** Settings → Branding (F14): logo for dark backgrounds, browser tab icon, sign-in picture and welcome. */
  logo_dark_url?: string | null
  favicon_url?: string | null
  signin_image_url?: string | null
  signin_message?: string | null
  colors: { primary: string | null }
  /** The organisation's own website (public form pages link to it); null on manage.*. */
  website?: string | null
  auth_providers: AuthProvider[]
  /** The workspace's password rules, for new passwords (reset); absent = the default. */
  password_policy?: PasswordPolicy
  status: TenantStatus
}

/** A workspace's password rules (Settings → Security; manage.* uses the default). */
export interface PasswordPolicy {
  min_length: number
  lower: boolean
  upper: boolean
  number: boolean
  symbol: boolean
}

export interface LoginChallenge {
  challenge_id: string
  channels: OtpChannel[]
  channel: OtpChannel
  masked_destination: string
  /** Seconds until a new code may be requested. */
  resend_after: number
  expires_at: string
}

export interface SessionUser {
  id: string
  first_name: string
  last_name: string
  email: string
  avatar_url: string | null
  role: WorkspaceRole
  /** The role's name and what it allows (Roles & access, F22): the app shows only what the role can use. */
  role_name?: string
  permissions?: string[]
  /** The same with each action's scope (own · shared · all), F22 R2. */
  grants?: Record<string, 'own' | 'shared' | 'all'>
  /** My profile (F16 M5): null = the workspace's. */
  language?: string | null
  time_zone?: string | null
  date_format?: DateFormat | null
}

export interface SessionTenant {
  id: string
  name: string
  subdomain: string
}

export interface SessionOrganisation {
  id: string
  name: string
}

export interface AuthTokens {
  access_token: string
  expires_in: number
  user: SessionUser
  tenant: SessionTenant
  organisation: SessionOrganisation
}

export interface WorkspaceLink {
  name: string
  subdomain: string
  url: string
}

export interface SubdomainAvailability {
  available: boolean
  reason: 'taken' | 'reserved' | 'invalid' | null
}

export interface SignupComplete {
  /** Open this URL to land signed-in on the new workspace (one-time ticket inside). */
  redirect_url: string
}

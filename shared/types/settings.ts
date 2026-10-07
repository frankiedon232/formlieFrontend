/**
 * Workspace settings (F14, docs/API-CONTRACT.md → Settings): one shape per section, read and saved with
 * GET / PATCH /settings/{section}. Onboarding writes the same company, branding and localisation data.
 */
import type { AppearanceSettings } from './appearance'
import type { AuditDevice } from './audit'
import type { AuthProvider, PasswordPolicy } from './auth'
import type { EmailSettings } from './emails'
import type { NotificationSettings } from './notifications'
import type { FormDefaults, PrivacySettings } from './privacy'
import type { CompanySize, DateFormat, Industry, NumberFormat, WeekStart } from './onboarding'

/** Sections that exist (the rest of F14 arrives milestone by milestone). */
export const SETTINGS_SECTIONS = ['company', 'branding', 'localisation', 'signin', 'security', 'notifications', 'emails', 'privacy', 'form_defaults', 'appearance'] as const
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number]

export interface CompanyAddress {
  line1: string | null
  line2: string | null
  city: string | null
  region: string | null
  postal_code: string | null
  /** ISO 3166-1 alpha-2. */
  country: string | null
}

export interface CompanySettings {
  /** The registered name, used on invoices and legal texts. */
  legal_name: string
  /** What people see in the portal, emails and public pages. */
  display_name: string
  industry: Industry | null
  size: CompanySize | null
  website: string | null
  registration_number: string | null
  tax_number: string | null
  support_email: string | null
  support_phone: string | null
  address: CompanyAddress
}

export interface BrandingSettings {
  logo_url: string | null
  /** For dark backgrounds (dark mode, the sign-in showcase); falls back to the logo. */
  logo_dark_url: string | null
  /** The browser tab icon; falls back to the logo. */
  favicon_url: string | null
  brand_color: string | null
  /** The picture on the workspace sign-in page (desktop). */
  signin_image_url: string | null
  /** A short welcome on the workspace sign-in page. */
  signin_message: string | null
}

/** PATCH /settings/branding: an upload id replaces a picture, null removes it, leaving it out keeps it. */
export interface BrandingSaveRequest {
  logo_upload_id?: string | null
  logo_dark_upload_id?: string | null
  favicon_upload_id?: string | null
  signin_image_upload_id?: string | null
  brand_color: string | null
  signin_message: string | null
}

export interface LocalisationSettings {
  language: string
  timezone: string
  currency: string
  date_format: DateFormat
  number_format: NumberFormat
  week_start: WeekStart
  /** Languages people can answer public forms in (each form picks from these). */
  form_languages: string[]
}

/** Settings → Sign-in (F14 M3): how people sign in to the workspace. */
export interface SigninSettings {
  /** Shown on the workspace sign-in page; at least one. */
  methods: AuthProvider[]
  /** The one-time code every sign-in asks for (always on; email always offered). */
  code: {
    /** Also offer a text message to people with a phone number. */
    sms: boolean
    expiry_minutes: 5 | 10 | 15
    max_attempts: 3 | 5 | 10
  }
  /** Only these email domains may sign in (and be invited); empty = any. */
  allowed_domains: string[]
}

export interface IpAllowEntry {
  /** An address or a CIDR range (IPv4 or IPv6). */
  value: string
  label: string | null
}

/** Settings → Security (F14 M3). */
export interface SecuritySettings {
  password: PasswordPolicy & {
    /** Refuse the last N passwords again (0 = off). */
    reuse_last: 0 | 3 | 5 | 10
    /** Ask for a new password after N days (0 = never). */
    expiry_days: 0 | 90 | 180 | 365
  }
  sessions: {
    /** Signed out after this long without activity. */
    idle_minutes: number
    /** Signed out after this long whatever happens. */
    max_hours: number
  }
  ip_allowlist: { enabled: boolean; entries: IpAllowEntry[] }
}

export interface SettingsChange {
  at: string
  by: string
}

/** GET /settings: every section, with who changed it last. */
export interface WorkspaceSettings {
  company: CompanySettings
  branding: BrandingSettings
  localisation: LocalisationSettings
  signin: SigninSettings
  security: SecuritySettings
  notifications: NotificationSettings
  emails: EmailSettings
  privacy: PrivacySettings
  form_defaults: FormDefaults
  appearance: AppearanceSettings
  updated: Record<SettingsSection, SettingsChange | null>
}

export type SettingsOf<S extends SettingsSection> = WorkspaceSettings[S]

/** A signed-in session (Settings → Security). */
export interface ActiveSession {
  id: string
  user: { name: string; email: string }
  current: boolean
  started_at: string
  last_active_at: string
  ip: string
  device: AuditDevice
}

/** GET /settings/security/activity: sign-in activity of the last 14 days, and the caller's address. */
export interface SecurityActivity {
  my_ip: string
  days: { date: string; succeeded: number; failed: number }[]
  totals: { succeeded: number; failed: number; blocked: number; locked: number }
  recent: { id: string; at: string; action: string; outcome: 'success' | 'failure' | 'blocked'; name: string; email: string | null; ip: string; reason: string | null }[]
}

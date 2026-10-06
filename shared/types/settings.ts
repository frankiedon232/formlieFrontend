/**
 * Workspace settings (F14, docs/API-CONTRACT.md → Settings): one shape per section, read and saved with
 * GET / PATCH /settings/{section}. Onboarding writes the same company, branding and localisation data.
 */
import type { CompanySize, DateFormat, Industry, NumberFormat, WeekStart } from './onboarding'

/** Sections that exist (the rest of F14 arrives milestone by milestone). */
export const SETTINGS_SECTIONS = ['company', 'branding', 'localisation'] as const
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

export interface SettingsChange {
  at: string
  by: string
}

/** GET /settings: every section, with who changed it last. */
export interface WorkspaceSettings {
  company: CompanySettings
  branding: BrandingSettings
  localisation: LocalisationSettings
  updated: Record<SettingsSection, SettingsChange | null>
}

export type SettingsOf<S extends SettingsSection> = WorkspaceSettings[S]

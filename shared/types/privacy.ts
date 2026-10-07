/**
 * Privacy and data, and form defaults (F14 M5, docs/API-CONTRACT.md → Settings). Retention removes
 * responses older than its limit for good; data requests find, export or delete one person's responses.
 */

/** Keep responses for N days; 0 = keep them until someone deletes them. */
export const RETENTION_DAYS = [0, 30, 90, 180, 365, 730, 1825] as const
export type RetentionDays = (typeof RETENTION_DAYS)[number]

export interface PrivacySettings {
  retention_days: RetentionDays
  /** The organisation's own privacy notice, linked on every public form. */
  notice_url: string | null
  /** Show a consent line above Submit on every public form. */
  consent: boolean
  /** The workspace's own consent line; empty = Formalie's text in the respondent's language. */
  consent_text: string | null
}

export interface FormDefaults {
  settings: { progress_bar: boolean; save_resume: boolean; field_icons: boolean; label_position: 'top' | 'left' }
  /** A theme new forms start with (a saved or a built-in one); null = the workspace look. */
  theme_id: string | null
  thank_you: { title: string | null; message: string | null }
  /** Team members who get new responses by email (shared/utils/forms/emails.ts). */
  team_emails: string[]
  /** Websites allowed to embed new forms; empty = any. */
  embed_domains: string[]
}

/** GET /settings/privacy/retention-preview?days= → what a retention limit would remove now. */
export interface RetentionPreview {
  days: RetentionDays
  responses: number
  forms: number
  oldest_kept: string | null
}

/** POST /privacy/requests/search { email } → one person's responses. */
export interface DataRequestMatch {
  email: string
  total: number
  forms: { id: string; name: string; count: number; latest: string }[]
}

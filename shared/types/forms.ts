import type { FormField } from '../utils/forms/build'
import type { FormTheme } from '../utils/forms/theme'
/** Form list shapes (docs/API-CONTRACT.md → Forms). */
export type FormStatus = 'draft' | 'published' | 'closed' | 'archived'

export interface FormOwner {
  id: string
  name: string
}

export interface FormFolder {
  id: string
  name: string
  /** Forms in the folder (not counting trash). */
  forms_count?: number
}

export interface FormSummary {
  id: string
  name: string
  slug: string
  /** Public address of the form: `/{public_key}/fill` (01-ARCHITECTURE → Public URLs). */
  public_key: string
  status: FormStatus
  has_unpublished_changes: boolean
  folder: FormFolder | null
  owner: FormOwner
  tags: string[]
  responses_count: number
  /** 0–100: share of started sessions that were submitted. */
  completion_rate: number
  created_at: string
  updated_at: string
  /** Optimistic locking: send it back on every change; a mismatch → FRM-GEN-1009. */
  row_version: number
  /** Set while the form is in Trash (kept 30 days, then removed for good). */
  deleted_at: string | null
  /** Availability (F10): responses only from / until these times (null = no limit). */
  opens_at: string | null
  closes_at: string | null
  /** Share settings (F10 M3): readable address instead of the key (null = the key only). */
  custom_link: string | null
  /** Who can open the form: anyone with the link, or people who know the password. */
  access: FormAccess
  /** Stop taking responses after this many (null = no limit). */
  response_limit: number | null
  /** Short link code (forms.formalie.com/s/{code}), or null. */
  short_code: string | null
}

export type FormAccess = 'public' | 'password'

/** GET /forms/{id}/share — everything about how a form is shared (the password itself is never returned). */
export interface FormShareSettings {
  access: FormAccess
  /** A password is set (required for access "password"). */
  has_password: boolean
  password_changed_at: string | null
  response_limit: number | null
  responses_count: number
  custom_link: string | null
  opens_at: string | null
  closes_at: string | null
  row_version: number
  /** Short link: its code and how many times it was opened. */
  short_link: { code: string; clicks: number; created_at: string } | null
  /** Websites allowed to show the embed (empty = any website). */
  embed_domains: string[]
}

/** The Share tab's unsaved changes (portal only). */
export interface ShareDraft {
  access: FormAccess
  /** A new password (empty = keep the current one). */
  password: string
  limitOn: boolean
  limit: number
  link: string
  /** Embed: only the websites listed (false = any website). */
  embedLimited: boolean
  domains: string[]
}

/** GET /forms/{id}/share/link-check?value= — can this custom link be used? */
export interface CustomLinkCheck {
  value: string
  available: boolean
  /** invalid · reserved (a Formalie page) · taken (another form) */
  reason: 'invalid' | 'reserved' | 'taken' | null
  /** Up to three free links close to it (taken or reserved). */
  suggestions: string[]
  /**
   * Taken by one of your own forms: which one (`link`: its custom link, or else its key).
   * Null when another organisation sharing forms.formalie.com uses it — never named.
   */
  taken_by: { id: string; name: string; status: FormStatus; link: boolean } | null
}

/** GET /forms/facets — options for the owner and tag filters. */
export interface FormFacets {
  owners: FormOwner[]
  tags: string[]
  /** Templates the forms were made from (for the Template filter). */
  templates: { key: string; name: string }[]
}

export type FormLifecycleAction = 'unpublish' | 'close' | 'reopen' | 'archive' | 'unarchive' | 'restore'

export type FormBulkAction = 'archive' | 'move' | 'delete' | 'restore' | 'purge'

/** POST /forms/bulk → what happened to each selected form. */
export interface FormBulkResult {
  updated: number
  failed: { id: string; code: string }[]
}

export const TRASH_RETENTION_DAYS = 30

/** GET /forms/:id/versions item — a published snapshot (the schema comes from GET …/versions/:vid). */
export interface FormVersion {
  id: string
  number: number
  published_at: string
  published_by: { id: string; name: string }
  change_summary: string | null
  fields_count: number
}

/** A field kept for reuse (GET /field-library). `field` has no id; inserting gives it a new one. */
export interface SavedField {
  id: string
  name: string
  field: Omit<FormField, 'id'>
  created_by: { id: string; name: string }
  created_at: string
}

/** A reusable list of options — countries, regions, products … (GET /option-lists). */
export interface OptionList {
  id: string
  name: string
  options: { value: string; label: string; score?: number }[]
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

/** A saved design (GET /themes) — reusable on any form; forms keep a copy of the tokens. */
/** system = Formalie's designs (read-only) · saved = from a form's design · created = in the theme editor. */
export type ThemeSource = 'system' | 'saved' | 'created'

export interface SavedTheme {
  id: string
  name: string
  tokens: FormTheme
  source: ThemeSource
  /** System themes: i18n key of the name, so it shows in the person's language. */
  name_key?: string
  forms_count: number
  created_by: { id: string; name: string }
  created_at: string
  updated_at: string
}

/** GET /forms/:id/overview — everything the form overview page shows (F9 redesign). */
export interface FormOverview {
  stats: {
    views: number
    starts: number
    responses: number
    /** 0–100 */
    completion_rate: number
    /** Median time to complete, in seconds (null until there are responses). */
    avg_seconds: number | null
    last_response_at: string | null
  }
  /** Responses per day for the last 30 days, oldest first (ISO date). */
  daily: { date: string; count: number }[]
  structure: { pages: number; fields: number; logic: number; calculations: number }
  /** Latest published versions, newest first (up to 3). */
  versions: Omit<FormVersion, 'change_summary'>[]
  template: { key: string; name: string } | null
  /** Design tokens and first questions, for the themed mini preview. */
  theme: Record<string, unknown>
  preview: string[]
}

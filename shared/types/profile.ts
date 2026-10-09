/**
 * My profile (F16 M5, docs/API-CONTRACT.md → My profile): what every person sees and changes about
 * themselves. Department, job titles, role and manager are shown but set by admins (People).
 */
import type { WorkspaceRole } from './auth'
import type { PersonRef } from './people'

import { DATE_FORMATS, type DateFormat } from './onboarding'

/** The same short date formats as the workspace's (Settings → Language and region). */
export const PROFILE_DATE_FORMATS = DATE_FORMATS
/** Personal emails (security emails always go out). */
export const PROFILE_NOTIFICATIONS = ['responses', 'digest', 'mentions', 'product'] as const
export type ProfileNotification = (typeof PROFILE_NOTIFICATIONS)[number]

export interface MyProfile {
  id: string
  first_name: string
  last_name: string
  email: string
  /** A small image (data URL, up to 200 KB) or null. */
  photo: string | null
  /** null = the workspace's (Settings → Language and region). */
  language: string | null
  time_zone: string | null
  date_format: DateFormat | null
  role: WorkspaceRole
  departments: PersonRef[]
  job_titles: PersonRef[]
  manager: PersonRef | null
  password_changed_at: string | null
  two_step: {
    app: boolean
    recovery_left: number
    /** The SMS number, masked (+44 •••• ••0123). */
    phone: string | null
    /** The workspace allows codes by text message (Settings → Sign-in). */
    sms_allowed: boolean
  }
  notifications: Record<ProfileNotification, boolean>
}

/** GET /me/sessions */
export interface MySession {
  id: string
  current: boolean
  started_at: string
  last_active_at: string
  ip: string
  device: { type: string; browser: string | null; os: string | null }
}

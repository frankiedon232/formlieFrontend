/**
 * Formalie support access, platform announcements and switches (B16, docs/API-CONTRACT.md → Formalie
 * support access, announcements and switches). The workspace allows Formalie's support team in for a
 * while (Settings → Security); a support session is a one-time ticket redeemed on `/support`.
 */
import type { AuthTokens } from './auth'

export const SUPPORT_HOURS = [1, 24, 168] as const
export type SupportHours = (typeof SUPPORT_HOURS)[number]
export const SUPPORT_MODES = ['read', 'write'] as const
export type SupportMode = (typeof SUPPORT_MODES)[number]

/** The workspace's consent: open until `expires_at`, unless someone turns it off. */
export interface SupportGrant {
  id: string
  mode: SupportMode
  hours: SupportHours
  starts_at: string
  expires_at: string
  granted_by: { id: string | null; name: string }
  request_id: string | null
}

/** Formalie asked first; the workspace's admins approve or decline. */
export interface SupportRequest {
  id: string
  staff_name: string
  reason: string
  mode: SupportMode
  hours: SupportHours
  status: 'pending' | 'approved' | 'declined' | 'expired'
  created_at: string
  expires_at: string
  decided_at: string | null
  decided_by_name: string | null
}

export type SupportEndedReason = 'signed_out' | 'expired' | 'access_ended' | 'not_used'

export interface SupportSessionRow {
  id: string
  staff_name: string
  mode: SupportMode
  started_at: string | null
  ends_at: string
  ended_at: string | null
  ended_reason: SupportEndedReason | null
  active: boolean
}

/** GET · POST · DELETE /settings/security/support-access */
export interface SupportAccessState {
  grant: SupportGrant | null
  requests: SupportRequest[]
  sessions: SupportSessionRow[]
  hours: SupportHours[]
  modes: SupportMode[]
}

/** POST /settings/security/support-access */
export interface SupportAllowRequest {
  hours: SupportHours
  mode: SupportMode
  request_id?: string
}

/** GET /support-access/status (also `support_session` in GET /me): everyone sees the banner. */
export interface SupportBanner {
  active: true
  staff_name: string
  mode: SupportMode
  started_at: string
  ends_at: string
}

/** POST /auth/support/redeem */
export interface SupportRedeemResult extends AuthTokens {
  support: { session_id: string; mode: SupportMode; staff_name: string; ends_at: string }
}

/** GET /platform/announcements */
export interface PlatformAnnouncement {
  id: string
  kind: 'banner' | 'maintenance' | 'news'
  tone: 'info' | 'warning' | 'critical'
  title: string
  body: string | null
  link_url: string | null
  dismissible: boolean
  starts_at: string
  ends_at: string | null
}

/** GET /platform/feature-flags */
export type FeatureFlags = Record<string, boolean>

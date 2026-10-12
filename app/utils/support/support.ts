/**
 * Pure helpers for Formalie support access and platform announcements (B16). No Vue, no Nuxt, so they
 * are unit tested (test/support/support.test.ts).
 */
import type { PlatformAnnouncement } from '#shared/types/support'

/** The one-time ticket in `/support#ticket=…` (the fragment never reaches a server log). */
export function supportTicketFromHash(hash: string | null | undefined): string | null {
  const raw = (hash ?? '').replace(/^#/, '')
  if (!raw) return null
  const ticket = new URLSearchParams(raw).get('ticket')?.trim() ?? ''
  // The backend takes 20 to 100 characters; anything else can't be a ticket
  return ticket.length >= 20 && ticket.length <= 100 ? ticket : null
}

/** Milliseconds left until `endsAt` (never below 0); null when there is no end. */
export function msLeft(endsAt: string | null | undefined, now = Date.now()): number | null {
  if (!endsAt) return null
  const end = Date.parse(endsAt)
  return Number.isNaN(end) ? null : Math.max(0, end - now)
}

/** Live countdown text: "1:05:09" over an hour, "05:09" under it, then "00:00". Days as "2d 03:04:05". */
export function countdownText(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const days = Math.floor(total / 86_400)
  const hours = Math.floor((total % 86_400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const two = (n: number) => String(n).padStart(2, '0')
  if (days) return `${days}d ${two(hours)}:${two(minutes)}:${two(seconds)}`
  if (hours) return `${hours}:${two(minutes)}:${two(seconds)}`
  return `${two(minutes)}:${two(seconds)}`
}

const TONE_ORDER: Record<PlatformAnnouncement['tone'], number> = { critical: 0, warning: 1, info: 2 }

/** What shows now: started, not ended, not dismissed (only dismissible ones can be); critical first. */
export function visibleAnnouncements(list: PlatformAnnouncement[], dismissed: readonly string[], now = Date.now()): PlatformAnnouncement[] {
  return list
    .filter(item => Date.parse(item.starts_at) <= now && (!item.ends_at || Date.parse(item.ends_at) > now))
    .filter(item => !item.dismissible || !dismissed.includes(item.id))
    .sort((a, b) => TONE_ORDER[a.tone] - TONE_ORDER[b.tone] || Date.parse(b.starts_at) - Date.parse(a.starts_at))
}

/** Link of an announcement, only when it is https (never javascript: or anything else). */
export const safeAnnouncementLink = (url: string | null | undefined) => (url && /^https:\/\//i.test(url) ? url : null)

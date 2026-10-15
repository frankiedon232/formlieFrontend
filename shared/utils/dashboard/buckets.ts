/**
 * Buckets for the dashboard's and analytics' charts (F21): days, weeks, months or years, covering a period from its
 * first to its last day. Each bucket is named by its first day (YYYY-MM-DD). Formalie is a global platform (owner
 * 2026-10-15): days are the workspace's own (Settings → Localisation time zone) and weeks start on its `week_start`
 * (Monday unless it chose Sunday or Saturday). The backend ports these rules (parity).
 */
import type { DashboardGroup } from '#shared/types/dashboard'
import type { WeekStart } from '#shared/types/onboarding'

const DAY = 86_400_000
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

/** The workspace's calendar: where its weeks start and which time zone its days are in. */
export interface BucketCalendar {
  weekStart?: WeekStart
  /** An IANA time zone, e.g. Africa/Lagos; UTC when missing or unknown. */
  timeZone?: string
}

/** getUTCDay() of the first day of a week. */
const FIRST_DAY: Record<WeekStart, number> = { sunday: 0, monday: 1, saturday: 6 }

/** The calendar day (as UTC midnight) a moment falls on in the time zone. */
export function dayOf(time: number, timeZone = 'UTC'): number {
  let parts: Intl.DateTimeFormatPart[]
  try {
    parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(time))
  } catch {
    // An unknown time zone counts as UTC
    parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(time))
  }
  const part = (type: string) => Number(parts.find(item => item.type === type)?.value)
  return Date.UTC(part('year'), part('month') - 1, part('day'))
}

/** The first day of the group a calendar day (UTC midnight) belongs to. */
function groupStart(day: number, group: DashboardGroup, weekStart: WeekStart): number {
  const d = new Date(day)
  if (group === 'day') return day
  if (group === 'week') return day - ((d.getUTCDay() - FIRST_DAY[weekStart] + 7) % 7) * DAY
  if (group === 'month') return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)
  return Date.UTC(d.getUTCFullYear(), 0, 1)
}

/** The first day of the bucket a moment falls in, on the workspace's calendar. */
export function bucketStart(time: number, group: DashboardGroup, calendar: BucketCalendar = {}): number {
  return groupStart(dayOf(time, calendar.timeZone), group, calendar.weekStart ?? 'monday')
}

/**
 * Every bucket from `from` to `to` (both calendar days as UTC midnight, inclusive), in order. The period's days are
 * already the workspace's days, so only the week start applies here.
 */
export function bucketsOf(from: number, to: number, group: DashboardGroup, calendar: BucketCalendar = {}): string[] {
  const weekStart = calendar.weekStart ?? 'monday'
  const out: string[] = []
  // Plain dates: their UTC day, never shifted by a time zone
  let at = groupStart(dayOf(from), group, weekStart)
  const end = groupStart(dayOf(to), group, weekStart)
  while (at <= end && out.length < 400) {
    out.push(iso(at))
    const d = new Date(at)
    at = group === 'day' ? at + DAY : group === 'week' ? at + 7 * DAY : group === 'month' ? Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1) : Date.UTC(d.getUTCFullYear() + 1, 0, 1)
  }
  return out
}

/** The group that fits a period best when none is chosen (about 7 to 60 points). */
export function groupFor(days: number): DashboardGroup {
  return days <= 62 ? 'day' : days <= 400 ? 'week' : days <= 1500 ? 'month' : 'year'
}

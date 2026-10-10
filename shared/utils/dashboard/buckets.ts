/**
 * Buckets for the dashboard's charts (F21): days, weeks (starting Monday), months or years, in UTC, covering a
 * period from its first to its last day. Each bucket is named by its first day (YYYY-MM-DD).
 */
import type { DashboardGroup } from '#shared/types/dashboard'

const DAY = 86_400_000
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

/** The first day of the bucket a moment falls in. */
export function bucketStart(time: number, group: DashboardGroup): number {
  const d = new Date(time)
  const day = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
  if (group === 'day') return day
  if (group === 'week') return day - ((d.getUTCDay() + 6) % 7) * DAY
  if (group === 'month') return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)
  return Date.UTC(d.getUTCFullYear(), 0, 1)
}

/** Every bucket from `from` to `to` (both days, inclusive), in order. */
export function bucketsOf(from: number, to: number, group: DashboardGroup): string[] {
  const out: string[] = []
  let at = bucketStart(from, group)
  const end = bucketStart(to, group)
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

/**
 * The audit trail's period when no start date is picked (owner 2026-10-13; backend query review Q8): the last
 * 90 days, today included, counted from midnight UTC 89 days ago, exactly as the backend counts it. The list and
 * its export use it; a picked start date shows that period instead, so older entries are one pick away.
 */
export const AUDIT_DEFAULT_DAYS = 90

/** The first day (YYYY-MM-DD, UTC) of the default period. */
export function auditDefaultFrom(now: Date = new Date()): string {
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - (AUDIT_DEFAULT_DAYS - 1)))
  return start.toISOString().slice(0, 10)
}

/** The start the list really uses: the picked one, else the default period's. */
export const auditPeriodFrom = (from: string | null | undefined, now?: Date) => from || auditDefaultFrom(now)

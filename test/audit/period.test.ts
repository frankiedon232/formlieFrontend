import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AuditEvent } from '../../shared/types/audit'
import { AUDIT_DEFAULT_DAYS, auditDefaultFrom, auditPeriodFrom } from '../../shared/utils/audit/period'
import { filterEvents } from '../../server/mock/data/auditFilter'

describe('the audit trail default period (owner 2026-10-13, backend query review Q8)', () => {
  it('is the last 90 days, today included, counted in UTC as the backend does', () => {
    expect(AUDIT_DEFAULT_DAYS).toBe(90)
    expect(auditDefaultFrom(new Date('2026-10-13T12:00:00Z'))).toBe('2026-07-16')
    // Late in the evening west of UTC it is already the next day in UTC
    expect(auditDefaultFrom(new Date('2026-10-13T23:30:00-05:00'))).toBe('2026-07-17')
    // Across a year end and February
    expect(auditDefaultFrom(new Date('2026-03-01T00:00:00Z'))).toBe('2025-12-02')
  })
  it('gives way to a picked start date', () => {
    expect(auditPeriodFrom('2025-01-01', new Date('2026-10-13T12:00:00Z'))).toBe('2025-01-01')
    expect(auditPeriodFrom('', new Date('2026-10-13T12:00:00Z'))).toBe('2026-07-16')
    expect(auditPeriodFrom(null, new Date('2026-10-13T12:00:00Z'))).toBe('2026-07-16')
  })
})

describe('the mock audit list and export use the same period', () => {
  beforeEach(() => vi.useFakeTimers({ now: new Date('2026-10-13T12:00:00Z') }))
  afterEach(() => vi.useRealTimers())
  const at = (occurred_at: string) => ({ id: occurred_at, occurred_at, area: 'auth', action: 'auth.logout', outcome: 'success', actor: { id: null }, location: { country: null }, resource: null }) as unknown as AuditEvent
  const events = [at('2026-10-13T08:00:00Z'), at('2026-07-16T00:00:00Z'), at('2026-07-15T23:59:59Z'), at('2025-03-01T10:00:00Z')]
  const ids = (list: AuditEvent[]) => list.map(event => event.id)

  it('shows only the last 90 days when no start is sent', () => {
    expect(ids(filterEvents(events, {}))).toEqual(['2026-10-13T08:00:00Z', '2026-07-16T00:00:00Z'])
    expect(ids(filterEvents(events, { from: '' }))).toEqual(['2026-10-13T08:00:00Z', '2026-07-16T00:00:00Z'])
  })
  it('shows older entries once a start date is picked', () => {
    expect(ids(filterEvents(events, { from: '2025-01-01' }))).toHaveLength(4)
    expect(ids(filterEvents(events, { from: '2025-01-01', to: '2025-12-31' }))).toEqual(['2025-03-01T10:00:00Z'])
  })
})

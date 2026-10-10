import { describe, expect, it } from 'vitest'
import { bucketStart, bucketsOf, groupFor } from '../shared/utils/dashboard/buckets'
import { scopeFrom } from '../shared/utils/dashboard/scope'

const at = (day: string) => Date.parse(`${day}T12:00:00Z`)
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)

describe('dashboard buckets', () => {
  it('starts weeks on Monday, months and years on their first day', () => {
    expect(iso(bucketStart(at('2026-10-10'), 'week'))).toBe('2026-10-05')
    expect(iso(bucketStart(at('2026-10-05'), 'week'))).toBe('2026-10-05')
    expect(iso(bucketStart(at('2026-10-11'), 'week'))).toBe('2026-10-05')
    expect(iso(bucketStart(at('2026-10-10'), 'month'))).toBe('2026-10-01')
    expect(iso(bucketStart(at('2026-10-10'), 'year'))).toBe('2026-01-01')
  })

  it('covers a period with every bucket once', () => {
    expect(bucketsOf(at('2026-10-01'), at('2026-10-07'), 'day')).toHaveLength(7)
    expect(bucketsOf(at('2026-09-28'), at('2026-10-11'), 'week')).toEqual(['2026-09-28', '2026-10-05'])
    expect(bucketsOf(at('2025-11-15'), at('2026-02-01'), 'month')).toEqual(['2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01'])
    expect(bucketsOf(at('2024-06-01'), at('2026-01-01'), 'year')).toEqual(['2024-01-01', '2025-01-01', '2026-01-01'])
  })

  it('picks a sensible group for a period', () => {
    expect(groupFor(30)).toBe('day')
    expect(groupFor(90)).toBe('week')
    expect(groupFor(730)).toBe('month')
    expect(groupFor(3000)).toBe('year')
  })
})

describe('dashboard forms filter', () => {
  const hr = { folder: { id: 'hr' }, owner: { id: 'u1' } }
  const loose = { folder: null, owner: { id: 'u2' } }

  it('keeps every form without a filter', () => {
    const scope = scopeFrom({})
    expect(scope.filtered).toBe(false)
    expect([hr, loose].filter(scope.matches)).toHaveLength(2)
  })

  it('narrows to a folder, forms in no folder, or an owner', () => {
    expect([hr, loose].filter(scopeFrom({ folder: 'hr' }).matches)).toEqual([hr])
    expect([hr, loose].filter(scopeFrom({ folder: 'none' }).matches)).toEqual([loose])
    expect([hr, loose].filter(scopeFrom({ owner: 'u2' }).matches)).toEqual([loose])
    expect([hr, loose].filter(scopeFrom({ folder: 'hr', owner: 'u2' }).matches)).toEqual([])
    expect(scopeFrom({ owner: 'u2' }).filtered).toBe(true)
  })
})

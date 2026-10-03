import { describe, expect, it } from 'vitest'
import { availabilityOf } from '../../shared/utils/forms/availability'

const NOW = Date.parse('2026-10-03T12:00:00Z')
const at = (offsetDays: number) => new Date(NOW + offsetDays * 86_400_000).toISOString()

describe('form availability', () => {
  it('is always open without dates', () => expect(availabilityOf({ opens_at: null, closes_at: null }, NOW)).toBe('always'))
  it('is open within the dates', () => expect(availabilityOf({ opens_at: at(-1), closes_at: at(2) }, NOW)).toBe('open'))
  it('waits for the start', () => expect(availabilityOf({ opens_at: at(1), closes_at: null }, NOW)).toBe('scheduled'))
  it('expires at the end', () => {
    expect(availabilityOf({ opens_at: null, closes_at: at(-0.01) }, NOW)).toBe('expired')
    expect(availabilityOf({ opens_at: null, closes_at: new Date(NOW).toISOString() }, NOW)).toBe('expired')
  })
})

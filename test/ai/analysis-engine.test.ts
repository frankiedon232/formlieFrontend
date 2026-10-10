import { describe, expect, it } from 'vitest'
import { periodIn, sentimentOf, themesOf } from '../../server/mock/ai/textAnalysis'

const NOW = Date.parse('2026-10-10T12:00:00Z')
const day = (ms: number) => new Date(ms).toISOString().slice(0, 10)

describe('AI analysis (mock)', () => {
  it('understands periods in plain words', () => {
    const lastMonth = periodIn('Which site had most incidents last month?', NOW)!
    expect([day(lastMonth.from), day(lastMonth.to)]).toEqual(['2026-09-01', '2026-09-30'])
    const days = periodIn('how many in the last 7 days', NOW)!
    expect([day(days.from), day(days.to)]).toEqual(['2026-10-04', '2026-10-10'])
    expect(day(periodIn('responses this year', NOW)!.from)).toBe('2026-01-01')
    expect(periodIn('average rating', NOW)).toBeNull()
  })

  it('finds themes and tone in written answers', () => {
    expect(themesOf('Friendly team and fast answers.')).toEqual(expect.arrayContaining(['staff', 'speed']))
    expect(themesOf('Nothing to add')).toEqual(['other'])
    expect(sentimentOf('Friendly team and fast answers. I would recommend it.')).toBe('positive')
    expect(sentimentOf('Delivery was slow and the price too expensive.')).toBe('negative')
    expect(sentimentOf('Next week works')).toBe('neutral')
  })
})

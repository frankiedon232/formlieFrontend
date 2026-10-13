import { describe, expect, it } from 'vitest'
import { fallbackPlans } from '../app/utils/plans'
import { bestSaving, comparison, pricePerMonth, savingPercent } from '../app/utils/pricing'

const [starter, professional, business, enterprise] = fallbackPlans()

describe('periods (docs/PRICING.md)', () => {
  it('shows the price per month for each period, rounded to cents', () => {
    expect(pricePerMonth(professional!, 'monthly')).toBe(19)
    expect(pricePerMonth(professional!, 'quarterly')).toBe(17.1)
    expect(pricePerMonth(professional!, 'annually')).toBe(15.2)
    expect(pricePerMonth(business!, 'annually')).toBe(39.2)
    expect(pricePerMonth(enterprise!, 'annually')).toBeNull()
  })

  it('works out the saving against monthly', () => {
    expect(savingPercent(professional!, 'quarterly')).toBe(10)
    expect(savingPercent(business!, 'annually')).toBe(20)
    expect(savingPercent(starter!, 'annually')).toBe(0)
    expect(bestSaving(fallbackPlans(), 'annually')).toBe(20)
  })
})

describe('the comparison table', () => {
  const groups = comparison(fallbackPlans())
  const cells = (group: string, key: string, engine?: string) =>
    groups.find(g => g.key === group)!.rows.find(r => r.key === key && (!engine || r.engine === engine))!
      .cells

  it('is grouped like the app', () => {
    expect(groups.map(group => group.key)).toEqual([
      'forms',
      'insight',
      'data',
      'api',
      'brand',
      'signin',
      'support',
    ])
  })

  it('reads limits and features', () => {
    expect(cells('forms', 'forms')).toEqual({
      starter: 5,
      professional: 20,
      business: 'unlimited',
      enterprise: 'unlimited',
    })
    expect(cells('data', 'database', 'oracle')).toEqual({
      starter: false,
      professional: false,
      business: true,
      enterprise: true,
    })
    expect(cells('brand', 'customDomain')).toEqual({
      starter: false,
      professional: 1,
      business: 'unlimited',
      enterprise: 'unlimited',
    })
    expect(cells('insight', 'aiCredits').enterprise).toBe('custom')
    expect(cells('support', 'dedicated')).toEqual({
      starter: false,
      professional: false,
      business: false,
      enterprise: true,
    })
  })
})

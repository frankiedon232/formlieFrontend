import { describe, expect, it } from 'vitest'
import { allFields, publishIssues } from '../../shared/utils/forms/build'
import { calculateResult, formulaKeys, isValidFormula } from '../../shared/utils/forms/formula'
import { END_OF_FORM, type LogicRule } from '../../shared/utils/forms/logic'
import { formSchemaV1 } from '../../shared/utils/forms/schema'
import { themeSchema } from '../../shared/utils/forms/theme'
import { STARTER_TEMPLATE_KEYS } from '../../shared/utils/templates/starters'
import { SYSTEM_TEMPLATES, TEMPLATE_CATEGORY_KEYS, schemaStats, systemTemplate, templateSchema } from '../../shared/templates'

describe('template catalogue', () => {
  it('has unique keys in known categories', () => {
    const keys = SYSTEM_TEMPLATES.map(t => t.key)
    expect(new Set(keys).size).toBe(keys.length)
    for (const t of SYSTEM_TEMPLATES) expect(TEMPLATE_CATEGORY_KEYS, t.key).toContain(t.category)
  })

  for (const def of SYSTEM_TEMPLATES) {
    it(`${def.key} builds a valid, publishable form with a valid design`, () => {
      const schema = templateSchema(def)
      expect(formSchemaV1.safeParse(schema).success, def.key).toBe(true)
      expect(publishIssues(schema), def.key).toEqual([])
      expect(themeSchema.safeParse(schema.theme).success, def.key).toBe(true)
      expect(schemaStats(schema).fields, def.key).toBeGreaterThan(2)

      const fields = allFields(schema)
      const keys = new Set(fields.map(f => f.key))
      const ids = new Set(fields.map(f => f.id))
      for (const field of fields.filter(f => f.type === 'calculated')) {
        const formula = String(field.props?.formula ?? '')
        expect(isValidFormula(formula), `${def.key}.${field.key}: ${formula}`).toBe(true)
        for (const key of formulaKeys(formula)) expect(keys.has(key), `${def.key}.${field.key} uses {${key}}`).toBe(true)
      }
      const pages = new Set(schema.pages.map(p => p.id))
      for (const rule of (schema.logic ?? []) as LogicRule[]) {
        for (const c of [...(rule.when.all ?? []), ...(rule.when.any ?? [])]) expect(ids.has(c.field), `${def.key} ${rule.id} condition`).toBe(true)
        for (const e of rule.then)
          if (e.target) expect(ids.has(e.target) || pages.has(e.target) || e.target === END_OF_FORM, `${def.key} ${rule.id} → ${e.target}`).toBe(true)
      }
    })
  }

  it('calculates realistic results', () => {
    const answers = (key: string, values: Record<string, unknown>) => {
      const schema = templateSchema(systemTemplate(key)!)
      const fields = new Map(allFields(schema).map(f => [f.key, f]))
      return (field: string) => calculateResult(String(fields.get(field)!.props!.formula), values, fields)
    }
    const order = answers('order_form', { product_1: 'standard_pack_45_00', qty_1: 2, delivery: 'express_15_00', line_1: 90, subtotal: 90 })
    expect(order('line_1')).toBe(90)
    expect(order('total')).toBe(105)
    const leave = answers('leave_request', { first_day: '2026-10-05', last_day: '2026-10-09' })
    expect(leave('days_requested')).toBe(5)
    const review = answers('performance_review', { c1: 'strong', c2: 'outstanding', c3: 'strong', c4: 'strong', c5: 'meets_expectations', c6: 'strong', average: 4 })
    expect(review('average')).toBe(4)
    expect(review('band')).toBe('Strong')
    const csat = answers('csat_nps', { nps: 6 })
    expect(csat('nps_group')).toBe('Detractor')
    const risk = answers('risk_assessment', { likelihood: 'likely', severity: 'major', risk_score: 16 })
    expect(risk('risk_score')).toBe(16)
    expect(risk('risk_level')).toBe('High')
    const inspection = answers('safety_inspection', Object.fromEntries([1, 2, 3, 4, 5, 6, 7, 8].map(n => [`check_${n}`, n === 3 ? 'fail' : 'pass'])))
    expect(inspection('compliance')).toBe(88)
    const hotel = answers('hotel_booking_request', { check_in: '2026-11-02', check_out: '2026-11-05', room_type: 'deluxe_180_00_night', rooms: 2, nights: 3 })
    expect(hotel('nights')).toBe(3)
    expect(hotel('estimate')).toBe(1080)
    const catering = answers('event_catering_request', { menu: 'buffet_25_00', extras: ['drinks_package_15_00', 'coffee_and_tea_3_00'], guests: 40, per_guest: 43 })
    expect(catering('per_guest')).toBe(43)
    expect(catering('estimate')).toBe(1720)
    const register = answers('attendance_register', { status_1: 'present', status_2: 'late', status_3: 'absent', status_4: 'present', present: 3 })
    expect(register('present')).toBe(3)
    expect(register('attendance_rate')).toBe(75)
    const quiz = answers('quiz_assessment', { q1: 'wind', q2: 'mercury', q3: 'mercury', q4: '6', q5: '100_c', score: 4, percentage: 80 })
    expect(quiz('percentage')).toBe(80)
    expect(quiz('result')).toBe('Pass')
    const loan = answers('loan_application', { amount: 12000, months: 24, rate: 9, income: 4000, debts: 400, monthly_payment: 590 })
    expect(loan('monthly_payment')).toBe(590)
    expect(loan('dti')).toBe(25)
    const invoice = answers('invoice_submission', { qty_1: 2, price_1: 100, qty_2: 1, price_2: 50, tax_rate: 20, subtotal: 250, tax: 50 })
    expect(invoice('subtotal')).toBe(250)
    expect(invoice('tax')).toBe(50)
    expect(invoice('total')).toBe(300)
    const claim = answers('insurance_claim', { amount_1: 120.5, amount_2: 79.5 })
    expect(claim('claim_total')).toBe(200)
    const membership = answers('membership_application', { level: 'standard_60_00_a_year', extras: ['printed_newsletter_10_00'] })
    expect(membership('fee')).toBe(70)
    const donation = answers('donation_form', { preset: 'other_amount', other_amount: 40, cover_fees: true, gift: 40 })
    expect(donation('gift')).toBe(40)
    expect(donation('total')).toBe(41.2)
    expect(answers('donation_form', { preset: '50_00', cover_fees: false, gift: 50 })('total')).toBe(50)
    const tenant = answers('tenant_application', { rent: 1000, income: 2700, income_ratio: 2.7 })
    expect(tenant('income_ratio')).toBe(2.7)
    expect(tenant('affordability')).toBe('Borderline')
    const property = answers('property_inspection', { room_1: 'good', room_2: 'good', room_3: 'fair', room_4: 'poor', room_5: 'good' })
    expect(property('condition_score')).toBe(80)
    const quote = answers('sales_quote_request', { plan: 'business_15_00_per_seat_month', seats: 10, services: ['onboarding_500_00'], subscription: 1800 })
    expect(quote('subscription')).toBe(1800)
    expect(quote('quote_total')).toBe(2300)
    const lead = answers('sales_qualification', { budget: 'approved', authority: 'decision_maker', need: 'clear_need', timing: 'this_quarter', qual_score: 10 })
    expect(lead('qual_score')).toBe(10)
    expect(lead('temperature')).toBe('Hot')
    const trade = answers('order_request', { qty_1: 100, price_1: 60, subtotal: 6000, discount: 300 })
    expect(trade('discount')).toBe(300)
    expect(trade('order_total')).toBe(5700)
  })

  it('covers every onboarding starter', () => {
    const built = STARTER_TEMPLATE_KEYS.filter(key => systemTemplate(key))
    expect(built).toEqual([...STARTER_TEMPLATE_KEYS])
  })
})

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
  })

  it('covers the onboarding starters that are built so far', () => {
    const built = STARTER_TEMPLATE_KEYS.filter(key => systemTemplate(key))
    expect(built).toEqual(expect.arrayContaining(['customer_feedback', 'job_application', 'employee_onboarding', 'contact_lead']))
  })
})

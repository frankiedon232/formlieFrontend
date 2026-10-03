import { describe, expect, it } from 'vitest'
import { allFields, starterSchema } from '../../shared/utils/forms/build'
import { END_OF_FORM, evaluateLogic, operatorsFor, type LogicRule } from '../../shared/utils/forms/logic'
import { calculate, calculateResult, formulaKeys, isValidFormula } from '../../shared/utils/forms/formula'
import type { FormField } from '../../shared/utils/forms/build'

describe('form logic', () => {
  const schema = starterSchema('incident_report')
  const fields = allFields(schema)
  const severity = fields.find(f => f.key === 'severity')!
  const injured = fields.find(f => f.key === 'was_anyone_injured')!
  const names = fields.find(f => f.key === 'names_of_people_involved_or_witnesses')!
  const photos = fields.find(f => f.key === 'photos')!
  const secondPage = schema.pages[1]!.id

  const rules: LogicRule[] = [
    { id: 'r1', when: { all: [{ field: injured.id, op: 'true' }] }, then: [{ action: 'show', target: names.id }] },
    { id: 'r2', when: { any: [{ field: severity.id, op: 'eq', value: 'critical' }, { field: severity.id, op: 'eq', value: 'high' }] }, then: [{ action: 'require', target: photos.id }] },
    { id: 'r3', when: { all: [{ field: severity.id, op: 'eq', value: 'low' }] }, then: [{ action: 'jump', target: secondPage }] },
  ]
  const withRules = { ...schema, logic: rules }

  it('show rules hide their target until they match', () => {
    expect(evaluateLogic(withRules, {}).hidden.has(names.id)).toBe(true)
    expect(evaluateLogic(withRules, { was_anyone_injured: true }).hidden.has(names.id)).toBe(false)
  })

  it('required-if and "any" conditions', () => {
    expect(evaluateLogic(withRules, { severity: 'medium' }).required.has(photos.id)).toBe(false)
    expect(evaluateLogic(withRules, { severity: 'high' }).required.has(photos.id)).toBe(true)
  })

  it('jump rules attach to the page of their condition', () => {
    const state = evaluateLogic(withRules, { severity: 'low' })
    expect(state.jumps.get(schema.pages[0]!.id)).toBe(secondPage)
  })

  it('offers operators per field type', () => {
    expect(operatorsFor('number')).toContain('gt')
    expect(operatorsFor('toggle')).toEqual(['true', 'false'])
    expect(operatorsFor('checkbox')).toContain('contains')
    expect(operatorsFor('dropdown')).toContain('in')
    expect(operatorsFor('file_upload')).toEqual(['not_empty', 'empty'])
  })

  it('covers lists, ranges and text operators', () => {
    const one = (when: LogicRule['when']) => ({
      ...schema,
      logic: [{ id: 'x', when, then: [{ action: 'hide' as const, target: names.id }] }],
    })
    const hiddenWith = (when: LogicRule['when'], answers: Record<string, unknown>) =>
      evaluateLogic(one(when), answers).hidden.has(names.id)
    expect(hiddenWith({ all: [{ field: severity.id, op: 'in', value: ['high', 'critical'] }] }, { severity: 'high' })).toBe(true)
    expect(hiddenWith({ all: [{ field: severity.id, op: 'not_in', value: ['high'] }] }, { severity: 'high' })).toBe(false)
    expect(hiddenWith({ all: [{ field: photos.id, op: 'not_empty' }] }, { photos: [new Blob(['x'])] })).toBe(true)
    const multi = fields.find(f => f.type === 'checkbox' || f.type === 'multi_select')
    if (multi) {
      expect(hiddenWith({ all: [{ field: multi.id, op: 'contains_all', value: ['a', 'b'] }] }, { [multi.key]: ['a', 'b', 'c'] })).toBe(true)
      expect(hiddenWith({ all: [{ field: multi.id, op: 'count_gte', value: 3 }] }, { [multi.key]: ['a', 'b'] })).toBe(false)
    }
  })

  it('runs every action', () => {
    const page2 = schema.pages[1]!.id
    const state = evaluateLogic(
      {
        ...schema,
        logic: [
          {
            id: 'a',
            when: { all: [{ field: severity.id, op: 'eq', value: 'low' }] },
            then: [
              { action: 'disable', target: photos.id },
              { action: 'unrequire', target: names.id },
              { action: 'set_value', target: names.id, value: 'n/a' },
              { action: 'hide_page', target: page2 },
              { action: 'skip_to_end' },
            ],
          },
        ],
      },
      { severity: 'low' },
    )
    expect(state.disabled.has(photos.id)).toBe(true)
    expect(state.optional.has(names.id)).toBe(true)
    expect(state.values.get(names.id)).toBe('n/a')
    expect(state.hiddenPages.has(page2)).toBe(true)
    expect(state.jumps.get(schema.pages[0]!.id)).toBe(END_OF_FORM)
  })
})

describe('calculated fields', () => {
  it('evaluates arithmetic with field keys, safely', () => {
    expect(calculate('{quantity} * {price}', { quantity: 3, price: '2.5' })).toBe(7.5)
    expect(calculate('({a} + {b}) / 2', { a: 4, b: 6 })).toBe(5)
    expect(calculate('-{a} + 10', { a: 4 })).toBe(6)
    expect(calculate('{a} * ', { a: 4 })).toBeNull()
    expect(calculate('{missing} + 1', {})).toBeNull()
    expect(calculate('alert(1)', {})).toBeNull()
    expect(calculate('1 / 0', {})).toBeNull()
    expect(formulaKeys('{qty} * {unit_price}')).toEqual(['qty', 'unit_price'])
  })

  it('supports if, comparisons, functions and option numbers', () => {
    const plan = {
      id: 'f1', key: 'plan', type: 'radio', label: 'Plan',
      options: [{ value: 'basic', label: 'Basic', score: 10 }, { value: 'premium', label: 'Premium', score: 50 }],
    } as FormField
    const extras = {
      id: 'f2', key: 'extras', type: 'checkbox', label: 'Extras',
      options: [{ value: 'a', label: 'A', score: 5 }, { value: 'b', label: 'B', score: 7 }],
    } as FormField
    const fields = new Map([['plan', plan], ['extras', extras]])
    expect(calculate('{plan} + {extras}', { plan: 'premium', extras: ['a', 'b'] }, fields)).toBe(62)
    expect(calculate('if({plan} = "premium", 1, 0)', { plan: 'premium' }, fields)).toBe(1)
    expect(calculate('if({plan} = "Basic", 1, 0)', { plan: 'basic' }, fields)).toBe(1)
    expect(calculate('if({age} >= 18, 100, 50)', { age: 21 })).toBe(100)
    expect(calculate('round(max({a}, {b}) * 1.155, 2)', { a: 2, b: 3 })).toBe(3.47)
    expect(calculate('if({x} > 0, {y} / {x}, 0)', { x: 0 })).toBe(0)
    expect(calculate('and({a} > 1, {b} < 5)', { a: 2, b: 3 })).toBe(1)
    expect(isValidFormula('if({a}, 1)')).toBe(true)
    expect(isValidFormula('{a} +* 2')).toBe(false)
  })
})

describe('formula additions for templates', () => {
  it('averages and counts answered fields only', () => {
    expect(calculate('avg({a}, {b}, {c})', { a: 4, b: 2 })).toBe(3)
    expect(calculate('count({a}, {b}, {c})', { a: 4 })).toBe(1)
    expect(calculate('sum({a}, {b})', { a: 5 })).toBe(5)
    expect(calculate('sum({a}, {b})', {})).toBeNull()
  })

  it('counts days between dates', () => {
    expect(calculate('days({in}, {out})', { in: '2026-10-01', out: '2026-10-04' })).toBe(3)
    expect(calculate('days({in}, {out}) * 120', { in: '2026-10-01T14:00', out: '2026-10-03T10:00' })).toBe(240)
    expect(calculate('days({in}, {out})', { in: 'soon', out: '2026-10-04' })).toBeNull()
  })

  it('can give a text result', () => {
    const level = 'if({l} * {s} >= 15, "High", if({l} * {s} >= 8, "Medium", "Low"))'
    expect(calculateResult(level, { l: 5, s: 4 })).toBe('High')
    expect(calculateResult(level, { l: 2, s: 4 })).toBe('Medium')
    expect(calculateResult(level, { l: 1, s: 2 })).toBe('Low')
    expect(calculate(level, { l: 5, s: 4 })).toBeNull()
    expect(calculateResult('{l} * {s}', { l: 5, s: 4 })).toBe(20)
  })
})

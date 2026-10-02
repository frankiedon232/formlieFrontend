import { describe, expect, it } from 'vitest'
import { allFields, starterSchema } from '../../shared/utils/forms/build'
import { calculate, evaluateLogic, formulaKeys, operatorsFor, type LogicRule } from '../../shared/utils/forms/logic'

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
})

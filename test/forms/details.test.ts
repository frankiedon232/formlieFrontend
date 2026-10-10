import { describe, expect, it } from 'vitest'
import { blankSchema, type FormField } from '../../shared/utils/forms/build'
import { detailAnswer, detailKeysOf, isNumericDetail } from '../../shared/utils/forms/details'
import { calculateResult, formulaDetails, formulaKeys, isValidFormula } from '../../shared/utils/forms/formula'
import { evaluateLogic, operatorsForDetail, type LogicRule } from '../../shared/utils/forms/logic'
import { checkSubmission } from '../../shared/utils/forms/submission'

const product: FormField = {
  id: 'f1', key: 'product', type: 'dropdown', label: 'Product',
  options: [
    { value: 'desk', label: 'Desk', attrs: { price: 250, region: 'North' } },
    { value: 'chair', label: 'Chair', attrs: { price: '79,50', region: 'South' } },
    { value: 'lamp', label: 'Lamp', attrs: { region: 'North' } },
  ],
}
const extras: FormField = { ...product, id: 'f2', key: 'extras', type: 'checkbox', label: 'Extras' }
const quantity: FormField = { id: 'f3', key: 'quantity', type: 'number', label: 'Quantity' }
const total: FormField = { id: 'f4', key: 'total', type: 'calculated', label: 'Total', props: { formula: '{product.price} * {quantity}' } }
const note: FormField = { id: 'f5', key: 'note', type: 'short_text', label: 'Note' }
const fields = new Map([product, extras, quantity, total, note].map(field => [field.key, field]))

describe('list details in formulas and logic (leftovers L1)', () => {
  it('read a detail of the chosen option, and add up several', () => {
    expect(detailAnswer(product, 'desk', 'price')).toBe(250)
    expect(detailAnswer(product, 'chair', 'price')).toBe(79.5)
    expect(detailAnswer(product, 'desk', 'region')).toBe('North')
    expect(detailAnswer(extras, ['desk', 'chair'], 'price')).toBe(329.5)
    expect(detailAnswer(extras, ['desk', 'chair'], 'region')).toEqual(['North', 'South'])
    expect(detailAnswer(product, 'lamp', 'price')).toBeNull()
    expect(detailAnswer(product, '', 'price')).toBeNull()
  })

  it('know which details a field has and whether they are numbers', () => {
    expect(detailKeysOf(product)).toEqual(['price', 'region'])
    expect(isNumericDetail(product, 'price')).toBe(true)
    expect(isNumericDetail(product, 'region')).toBe(false)
    expect(operatorsForDetail(true, false)).toContain('gt')
    expect(operatorsForDetail(false, true)).toEqual(['contains', 'not_contains', 'empty', 'not_empty'])
  })

  it('use {field.detail} in formulas', () => {
    expect(isValidFormula('{product.price} * {quantity}')).toBe(true)
    expect(formulaKeys('{product.price} * {quantity}')).toEqual(['product', 'quantity'])
    expect(formulaDetails('{product.price} * {quantity}')).toEqual([{ key: 'product', detail: 'price' }])
    expect(calculateResult('{product.price} * {quantity}', { product: 'desk', quantity: 2 }, fields)).toBe(500)
    expect(calculateResult('{extras.price}', { extras: ['desk', 'chair'] }, fields)).toBe(329.5)
    expect(calculateResult('if({product.region} = "North", 10, 0)', { product: 'lamp' }, fields)).toBe(10)
    // No price on the chosen option: the calculation waits like an unanswered question
    expect(calculateResult('{product.price} * 2', { product: 'lamp' }, fields)).toBeNull()
  })

  it('large lists use the options the page learned', () => {
    const large: FormField = { id: 'f9', key: 'branch', type: 'dropdown', label: 'Branch', options: [] }
    const picked = { f9: [{ value: 'b1', label: 'Branch 1', attrs: { fee: 12 } }] }
    expect(calculateResult('{branch.fee} + 1', { branch: 'b1' }, new Map([['branch', large]]), picked)).toBe(13)
  })

  it('test a detail in logic, on the page and on the server alike', () => {
    const schema = blankSchema()
    schema.pages[0]!.rows = [{ id: 'r1', fields: [product, quantity, total, note] }]
    const rules: LogicRule[] = [
      { id: 'r1', when: { all: [{ field: 'f1', detail: 'price', op: 'gt', value: 100 }] }, then: [{ action: 'require', target: 'f5' }] },
      { id: 'r2', when: { all: [{ field: 'f1', detail: 'region', op: 'eq', value: 'north' }] }, then: [{ action: 'show', target: 'f5' }] },
    ]
    schema.logic = rules
    expect(evaluateLogic(schema, { product: 'desk' }).required.has('f5')).toBe(true)
    expect(evaluateLogic(schema, { product: 'chair' }).required.has('f5')).toBe(false)
    expect(evaluateLogic(schema, { product: 'chair' }).hidden.has('f5')).toBe(true)
    expect(evaluateLogic(schema, { product: 'lamp' }).hidden.has('f5')).toBe(false)
    expect(checkSubmission(schema, { product: 'desk', quantity: 3 }).answers.total).toBe(750)
    expect(checkSubmission(schema, { product: 'desk', quantity: 3 }).issues.some(issue => issue.key === 'note')).toBe(true)
  })
})

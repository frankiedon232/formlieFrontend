import { describe, expect, it } from 'vitest'
import { blankSchema, type FormField } from '../../shared/utils/forms/build'
import { evaluateLogic } from '../../shared/utils/forms/logic'
import { checkSubmission } from '../../shared/utils/forms/submission'
import { offeredOptions, matchesList } from '../../shared/utils/forms/options'

const site: FormField = {
  id: 'f1', key: 'site', type: 'dropdown', label: 'Site',
  options: [
    { value: 'north', label: 'North office', attrs: { postcode: 'N1 1AA', capacity: '40' } },
    { value: 'south', label: 'South office', attrs: { postcode: 'S2 2BB', capacity: '25' } },
  ],
  props: { fills: [{ column: 'postcode', target: 'f2', lock: true }, { column: 'capacity', target: 'f3', lock: false }] },
}
const postcode: FormField = { id: 'f2', key: 'postcode', type: 'short_text', label: 'Postcode' }
const capacity: FormField = { id: 'f3', key: 'capacity', type: 'number', label: 'Capacity' }
const schema = blankSchema()
schema.pages[0]!.rows = [{ id: 'r1', fields: [site, postcode, capacity] }]

describe('details and auto-fill (F15 M4)', () => {
  it('fill and lock from the chosen option', () => {
    const logic = evaluateLogic(schema, { site: 'north' })
    expect(logic.values.get('f2')).toBe('N1 1AA')
    expect(logic.values.get('f3')).toBe(40)
    expect(logic.disabled.has('f2')).toBe(true)
    expect(logic.disabled.has('f3')).toBe(false)
  })

  it('never overwrite what a person typed in an unlocked field, but follow a changed choice', () => {
    expect(evaluateLogic(schema, { site: 'south', capacity: 99 }).values.has('f3')).toBe(false)
    expect(evaluateLogic(schema, { site: 'south', capacity: 40 }).values.get('f3')).toBe(25)
  })

  it('keep a locked value on submit whatever is sent', () => {
    const { answers } = checkSubmission(schema, { site: 'north', postcode: 'FAKE', capacity: 12 })
    expect(answers.postcode).toBe('N1 1AA')
    expect(answers.capacity).toBe(12)
  })

  it('come from the list with its columns, and changes are noticed', () => {
    const list = { columns: [{ key: 'postcode', label: 'Postcode' }], options: [{ value: 'a', label: 'A', attrs: { postcode: 'X', stray: 'Y' } }] }
    expect(offeredOptions(list)).toEqual([{ value: 'a', label: 'A', attrs: { postcode: 'X' } }])
    expect(matchesList([{ value: 'a', label: 'A' }], list)).toBe(false)
  })
})

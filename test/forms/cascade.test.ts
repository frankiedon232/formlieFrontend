import { describe, expect, it } from 'vitest'
import { blankSchema, type FormField } from '../../shared/utils/forms/build'
import { cascadeChain, cascadeClosed, cascadeOptions, fitAnswer } from '../../shared/utils/forms/cascade'
import { checkSubmission } from '../../shared/utils/forms/submission'
import { levelsOf, matchesList, offeredOptions } from '../../shared/utils/forms/options'
import { importPaths } from '../../app/utils/forms/option-paths'

const country: FormField = { id: 'f1', key: 'country', type: 'dropdown', label: 'Country', option_set_id: 'l', option_level: 0, options: [{ value: 'ca', label: 'Canada' }, { value: 'jp', label: 'Japan' }, { value: 'is', label: 'Island' }] }
const region: FormField = { id: 'f2', key: 'region', type: 'multi_select', label: 'Region', option_set_id: 'l', option_level: 1, option_parent: 'f1', options: [{ value: 'on', label: 'Ontario', parent: 'ca' }, { value: 'qc', label: 'Quebec', parent: 'ca' }, { value: 'tk', label: 'Tokyo', parent: 'jp' }] }
const city: FormField = { id: 'f3', key: 'city', type: 'dropdown', label: 'City', option_set_id: 'l', option_level: 2, option_parent: 'f2', required: true, options: [{ value: 'to', label: 'Toronto', parent: 'on' }, { value: 'mt', label: 'Montréal', parent: 'qc' }, { value: 'sj', label: 'Shinjuku', parent: 'tk' }] }
const byId = new Map([country, region, city].map(field => [field.id, field]))
const values = (field: FormField, answers: Record<string, unknown>) => cascadeOptions(field, byId, answers).map(option => option.value)

describe('lists with levels in forms', () => {
  it('offer only what is under the choice above', () => {
    expect(values(region, { country: 'ca' })).toEqual(['on', 'qc'])
    expect(values(city, { country: 'ca', region: ['on', 'qc'] })).toEqual(['to', 'mt'])
    expect(values(country, {})).toHaveLength(3)
  })

  it('stay closed when nothing matches', () => {
    expect(cascadeClosed(region, byId, {})).toBe(true)
    expect(cascadeClosed(region, byId, { country: 'is' })).toBe(true)
    expect(cascadeClosed(city, byId, { country: 'is', region: ['on'] })).toBe(true)
    expect(cascadeClosed(region, byId, { country: 'jp' })).toBe(false)
  })

  it('clear what no longer fits when a choice above changes', () => {
    expect(fitAnswer(region, byId, { country: 'jp', region: ['on', 'tk'] })).toEqual(['tk'])
    expect(fitAnswer(region, byId, { country: 'jp', region: ['on'] })).toBeUndefined()
    expect(fitAnswer(city, byId, { country: 'ca', region: ['on'], city: 'to' })).toBe('to')
  })

  it('find the whole chain from any level', () => {
    expect(cascadeChain(region, [country, region, city]).map(field => field.id)).toEqual(['f1', 'f2', 'f3'])
  })

  it('are checked the same way on submit', () => {
    const schema = blankSchema()
    schema.pages[0]!.rows = [{ id: 'r1', fields: [country, region, city] }]
    // A country without regions: the closed levels are not required
    expect(checkSubmission(schema, { country: 'is' }).issues).toEqual([])
    // An open level stays required; a city that isn't under the region is dropped
    const wrong = checkSubmission(schema, { country: 'jp', region: ['tk'], city: 'to' })
    expect(wrong.issues.map(issue => issue.key)).toEqual(['city'])
    expect('city' in wrong.answers).toBe(false)
  })
})

describe('option lists with levels', () => {
  const list = {
    levels: [{ key: 'country', label: 'Country' }, { key: 'region', label: 'Region' }],
    options: [{ value: 'ca', label: 'Canada' }, { value: 'jp', label: 'Japan', active: false }, { value: 'on', label: 'Ontario', level: 1, parent: 'ca' }, { value: 'tk', label: 'Tokyo', level: 1, parent: 'jp' }],
  }

  it('offer each level with its parents, skipping retired paths', () => {
    expect(levelsOf(list)).toHaveLength(2)
    expect(offeredOptions(list, 1)).toEqual([{ value: 'on', label: 'Ontario', parent: 'ca' }])
    expect(matchesList(offeredOptions(list, 1), list, 1)).toBe(true)
    expect(matchesList([{ value: 'on', label: 'Ontario', parent: 'jp' }], list, 1)).toBe(false)
  })

  it('import rows as paths', () => {
    const rows = [['Canada', 'Ontario'], ['Canada', 'Quebec'], ['Kenya', 'Nairobi'], ['', 'Lost']]
    const result = importPaths(list.options, rows, [0, 1], false)
    expect(result).toMatchObject({ added: 3, kept: 2, skipped: 1, retired: 0 })
    expect(result.list.find(option => option.label === 'Quebec')).toMatchObject({ level: 1, parent: 'ca', value: 'ca_quebec' })
    expect(result.list.find(option => option.label === 'Nairobi')?.parent).toBe('kenya')
    const replaced = importPaths(list.options, [['Canada', 'Ontario']], [0, 1], true)
    expect(replaced.retired).toBe(1)
    expect(replaced.list.find(option => option.value === 'tk')?.active).toBe(false)
  })
})

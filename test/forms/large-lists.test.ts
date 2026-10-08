import { describe, expect, it } from 'vitest'
import type { OptionList } from '../../shared/types/forms'
import { blankSchema, allFields, type FormField } from '../../shared/utils/forms/build'
import { cascadeClosed, fitAnswer } from '../../shared/utils/forms/cascade'
import { keptOnServer, levelCounts, lookupOptions, maxOptionsOf, searchesAsYouType, servedRemotely } from '../../shared/utils/forms/options'
import { applyFills } from '../../shared/utils/forms/fills'
import { fillLargeLists, keepAnswered, trimLargeLists } from '../../server/mock/data/largeLists'

const list: OptionList = {
  id: 'l1', name: 'Places', large: true,
  levels: [{ key: 'country', label: 'Country' }, { key: 'city', label: 'City' }],
  options: [
    { value: 'fr', label: 'France' }, { value: 'jp', label: 'Japan' }, { value: 'xx', label: 'Nowhere' },
    { value: 'paris', label: 'Paris', level: 1, parent: 'fr' }, { value: 'lyon', label: 'Lyon', level: 1, parent: 'fr' },
    { value: 'osaka', label: 'Osaka', level: 1, parent: 'jp' },
  ],
  created_by: { id: 'u', name: 'U' }, created_at: '', updated_at: '',
}
const country: FormField = { id: 'f1', key: 'country', type: 'radio', label: 'Country', option_set_id: 'l1', option_level: 0, options: [] }
const city: FormField = { id: 'f2', key: 'city', type: 'dropdown', label: 'City', option_set_id: 'l1', option_level: 1, option_parent: 'f1', options: [] }
const schemaOf = () => {
  const schema = blankSchema()
  schema.pages[0]!.rows = [{ id: 'r1', fields: [structuredClone(country), structuredClone(city)] }]
  return schema
}

describe('large dynamic lists (F15 M5)', () => {
  it('hold up to 200,000 options and count active ones per level', () => {
    expect(maxOptionsOf({})).toBe(20000)
    expect(maxOptionsOf({ large: true })).toBe(200000)
    expect(levelCounts(list)).toEqual([3, 3])
  })

  it('fill forms on the server (as a dropdown) and never send the options out', () => {
    const schema = schemaOf()
    expect(fillLargeLists(schema, [list])).toBe(2)
    const [top, low] = allFields(schema)
    expect(top!.type).toBe('dropdown')
    expect(low!.options).toHaveLength(3)
    const sent = trimLargeLists({ schema })
    const [sentTop, sentLow] = allFields(sent.schema)
    expect(sentTop!.options).toEqual([])
    expect(sentLow!.options_large).toEqual({ total: 3, parents: ['fr', 'jp'] })
    // the stored schema is untouched
    expect(allFields(schema)[1]!.options).toHaveLength(3)
  })

  it('open a lower level only under a choice that has options, in the browser too', () => {
    const schema = schemaOf()
    fillLargeLists(schema, [list])
    const fields = allFields(trimLargeLists(schema))
    const byId = new Map(fields.map(field => [field.id, field]))
    const low = byId.get('f2')!
    expect(cascadeClosed(low, byId, {})).toBe(true)
    expect(cascadeClosed(low, byId, { country: 'xx' })).toBe(true)
    expect(cascadeClosed(low, byId, { country: 'fr' })).toBe(false)
    // the page fits the answer as the choice above changes; the server checks it
    expect(fitAnswer(low, byId, { country: 'jp', city: 'paris' })).toBe('paris')
    expect(searchesAsYouType(low) && servedRemotely(low)).toBe(true)
  })

  it('a field just added in the builder opens as soon as something is chosen above', () => {
    const fresh = { ...city, options_large: { total: 3 } }
    const byId = new Map([[country.id, country], [fresh.id, fresh]])
    expect(cascadeClosed(fresh, byId, {})).toBe(true)
    expect(cascadeClosed(fresh, byId, { country: 'xx' })).toBe(false)
  })

  it('look up what is under the choices above, as people type', () => {
    const options = list.options.filter(option => option.level === 1)
    expect(lookupOptions(options, { q: 'ly', parents: ['fr'] }).items.map(item => item.value)).toEqual(['lyon'])
    expect(lookupOptions(options, { q: '', parents: ['jp'] })).toEqual({ items: [{ value: 'osaka', label: 'Osaka' }], total: 1 })
    expect(lookupOptions(options, { values: ['paris'], parents: ['jp'] }).items).toEqual([])
  })

  it('keep answered options for responses, and go back to copies when no longer large', () => {
    const schema = schemaOf()
    fillLargeLists(schema, [list])
    const kept = keepAnswered(schema, [{ city: 'lyon' }])
    expect(allFields(kept)[1]!.options).toEqual([{ value: 'lyon', label: 'Lyon', parent: 'fr' }])
    expect(allFields(trimLargeLists(kept))[1]!.options).toHaveLength(1)
    fillLargeLists(schema, [{ ...list, large: false }])
    expect(allFields(schema)[1]!.options_large).toBeUndefined()
    expect(allFields(schema)[1]!.options).toHaveLength(3)
  })

  it('keep every list above 20 options in the database, shorter ones are copied (owner 2026-10-08)', () => {
    const options = (n: number) => Array.from({ length: n }, (_, i) => ({ value: `o${i}`, label: `O ${i}` }))
    expect(keptOnServer({ options: options(20) })).toBe(false)
    expect(keptOnServer({ options: options(21) })).toBe(true)
    expect(keptOnServer({ options: [...options(20), { value: 'x', label: 'X', active: false }] })).toBe(false)
    const radio: FormField = { id: 'r', key: 'r', type: 'radio', label: 'R', options: options(21) }
    expect(servedRemotely(radio)).toBe(true)
    expect(servedRemotely({ ...radio, options: options(20) })).toBe(false)
  })

  it('auto-fill from options the page picked from the server', () => {
    const source: FormField = { id: 's', key: 's', type: 'dropdown', label: 'S', options: [], options_large: { total: 40 }, props: { fills: [{ column: 'zip', target: 't', lock: true }] } }
    const target: FormField = { id: 't', key: 't', type: 'short_text', label: 'T' }
    const state = { values: new Map(), disabled: new Set<string>(), enabled: new Set<string>() }
    applyFills(state, [source, target], { s: 'a' }, { s: [{ value: 'a', label: 'A', attrs: { zip: '12345' } }] })
    expect(state.values.get('t')).toBe('12345')
  })
})

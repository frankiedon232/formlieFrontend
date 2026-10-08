import { describe, expect, it } from 'vitest'
import { matchesList, matchOptions, offeredOptions, repeatedValues, searchesAsYouType, servedRemotely, uniqueValue, valueFromLabel } from '../../shared/utils/forms/options'
import { parseCsv } from '../../app/utils/files/table'

describe('option values', () => {
  it('come from labels in the field-key style', () => {
    expect(valueFromLabel('Très urgent!')).toBe('tres_urgent')
    expect(valueFromLabel('東京')).toBe('option')
  })

  it('stay unique and say which repeat', () => {
    expect(uniqueValue('north', ['north', 'North_2'])).toBe('north_3')
    expect([...repeatedValues(['a', 'B', 'b'])]).toEqual(['b'])
  })
})

describe('fields from lists', () => {
  const list = { options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B', active: false }, { value: 'c', label: 'C', score: 2 }] }

  it('get the active options only', () => {
    expect(offeredOptions(list)).toEqual([{ value: 'a', label: 'A' }, { value: 'c', label: 'C', score: 2 }])
  })

  it('know when they no longer match', () => {
    expect(matchesList([{ value: 'a', label: 'A' }, { value: 'c', label: 'C', score: 2 }], list)).toBe(true)
    expect(matchesList([{ value: 'a', label: 'A' }], list)).toBe(false)
    expect(matchesList(null, list)).toBe(false)
  })
})

describe('pasted and CSV tables', () => {
  it('guess the delimiter and respect quotes', () => {
    expect(parseCsv('Label;Value\n"North, upper";n\r\nSouth;s\n')).toEqual([['Label', 'Value'], ['North, upper', 'n'], ['South', 's']])
    expect(parseCsv('One\nTwo\n\nThree')).toEqual([['One'], ['Two'], ['Three']])
    expect(parseCsv('a\tb\n"say ""hi"""\tc')).toEqual([['a', 'b'], ['say "hi"', 'c']])
  })
})

describe('long lists (F15 M3)', () => {
  const many = (n: number) => Array.from({ length: n }, (_, i) => ({ value: `v${i}`, label: `Option ${i}` }))

  it('search as you type above 50 options, or as set on the field', () => {
    expect(searchesAsYouType({ type: 'dropdown', options: many(51) })).toBe(true)
    expect(searchesAsYouType({ type: 'dropdown', options: many(10) })).toBe(false)
    expect(searchesAsYouType({ type: 'dropdown', options: many(10), props: { search: true } })).toBe(true)
    expect(searchesAsYouType({ type: 'multi_select', options: many(500), props: { search: false } })).toBe(false)
    expect(searchesAsYouType({ type: 'radio', options: many(500) })).toBe(false)
  })

  it('keep very long lists on the server, but not lower levels', () => {
    expect(servedRemotely({ type: 'dropdown', options: many(301) })).toBe(true)
    expect(servedRemotely({ type: 'dropdown', options: many(300) })).toBe(false)
    expect(servedRemotely({ type: 'dropdown', options: many(400), option_parent: 'f1' })).toBe(false)
  })

  it('match without minding case or accents, starting matches first, 50 at a time', () => {
    const places = [{ value: 'a', label: 'Lisbon São Paulo' }, { value: 'b', label: 'São Paulo' }, { value: 'c', label: 'Osaka' }]
    expect(matchOptions(places, 'sao').items.map(item => item.value)).toEqual(['b', 'a'])
    expect(matchOptions(places, 'SÃO').total).toBe(2)
    expect(matchOptions(many(120), '').items).toHaveLength(50)
    expect(matchOptions(many(120), 'option 1').total).toBe(31)
  })
})

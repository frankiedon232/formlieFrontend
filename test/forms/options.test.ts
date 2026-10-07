import { describe, expect, it } from 'vitest'
import { matchesList, offeredOptions, repeatedValues, uniqueValue, valueFromLabel } from '../../shared/utils/forms/options'
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

import { describe, expect, it } from 'vitest'
import { answerMatches, filterValues, isEmptyAnswer } from '../../shared/utils/forms/answer-filter'

describe('filtering responses by answers', () => {
  it('offers the options of choice questions', () => {
    expect(filterValues({ type: 'radio', options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }] } as never)).toEqual(['a', 'b'])
    expect(filterValues({ type: 'toggle' } as never)).toEqual(['true', 'false'])
  })

  it('offers each score of short ratings and scales only', () => {
    expect(filterValues({ type: 'rating', props: { max: 5 } } as never)).toEqual(['1', '2', '3', '4', '5'])
    expect(filterValues({ type: 'scale', props: { min: 0, max: 10 } } as never)).toHaveLength(11)
    expect(filterValues({ type: 'scale', props: { min: 0, max: 100 } } as never)).toBeNull()
    expect(filterValues({ type: 'short_text' } as never)).toBeNull()
  })

  it('matches any picked value', () => {
    expect(answerMatches('remote', ['remote', 'hybrid'])).toBe(true)
    expect(answerMatches(['a', 'c'], ['c'])).toBe(true)
    expect(answerMatches(4, ['4', '5'])).toBe(true)
    expect(answerMatches(true, ['false'])).toBe(false)
    expect(answerMatches(null, ['a'])).toBe(false)
  })

  it('knows an empty answer', () => {
    expect(isEmptyAnswer('')).toBe(true)
    expect(isEmptyAnswer([])).toBe(true)
    expect(isEmptyAnswer({ line1: '', city: '' })).toBe(true)
    expect(isEmptyAnswer({ line1: 'Main St' })).toBe(false)
    expect(isEmptyAnswer(0)).toBe(false)
  })
})

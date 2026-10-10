import { describe, expect, it } from 'vitest'
import { readingAge, rewrite } from '../../server/mock/ai/writing'

describe('AI writing help (mock)', () => {
  it('uses plain words and keeps the capital', () => {
    const out = rewrite('Please provide details of the individual you wish to utilise.', 'plain')
    expect(out.text).toBe('Please tell us about the person you wish to use.')
    expect(out.reasons).toContain('plain_words')
  })

  it('follows the tone asked for, in English only', () => {
    expect(rewrite('Enter your name', 'friendly').text).toBe('Please enter your name')
    expect(rewrite("We'll reply if you don't hear from us", 'formal').text).toBe('We will reply if you do not hear from us')
    expect(rewrite('Enter your name', 'friendly', false).reasons).toEqual([])
  })

  it('calms all-capitals and leaves good text alone', () => {
    expect(rewrite('EMERGENCY CONTACT', 'plain').text).toBe('Emergency contact')
    expect(rewrite('Your email address', 'plain').reasons).toEqual([])
  })

  it('estimates a lower reading age for plainer text', () => {
    const hard = readingAge(['In accordance with organisational requirements, individuals are required to demonstrate sufficient documentation prior to commencement.'])
    const easy = readingAge(['Show us your papers before you start.'])
    expect(easy).toBeLessThan(hard)
  })
})

describe('AI reading age (mock)', () => {
  it('counts short labels as short sentences', () => {
    expect(readingAge(['Full name', 'Email address', 'Phone number', 'Company', 'Start date', 'Upload your CV'])).toBeLessThanOrEqual(10)
  })
})

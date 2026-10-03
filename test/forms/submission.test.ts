import { describe, expect, it } from 'vitest'
import { allFields } from '../../shared/utils/forms/build'
import { checkSubmission, pathPages } from '../../shared/utils/forms/submission'
import { evaluateLogic } from '../../shared/utils/forms/logic'
import { systemTemplate, templateSchema } from '../../shared/templates'
import { newPublicKey, FORM_KEY_PATTERN } from '../../shared/utils/urls/public'

const schemaOf = (key: string) => templateSchema(systemTemplate(key)!)

describe('public submission check', () => {
  it('asks for required answers on the respondent’s path only', () => {
    const rsvp = schemaOf('rsvp')
    const empty = checkSubmission(rsvp, {})
    expect(empty.issues.map(issue => issue.code)).toContain('required')
    // Fields shown only for "yes / maybe" aren't required when the guest declines.
    const fields = allFields(rsvp)
    const attending = fields.find(field => field.key === 'attending')!
    const declined = Object.fromEntries(
      fields.filter(field => field.required && field.key !== 'attending').map(field => [field.key, field.type === 'email' ? 'guest@example.org' : 'Ada']),
    )
    const result = checkSubmission(rsvp, { ...declined, attending: attending.options!.find(o => o.value === 'no')?.value ?? 'no' })
    expect(result.issues.filter(issue => issue.key === 'party_size')).toEqual([])
  })

  it('works out calculated fields itself and drops unknown answers', () => {
    const quiz = schemaOf('quiz_assessment')
    const { answers } = checkSubmission(quiz, { q1: 'wind', q2: '30', q3: 'mercury', q4: '6', q5: '100_c', score: 0, percentage: 999, hacked: 'x' })
    expect(answers.score).toBe(5)
    expect(answers.percentage).toBe(100)
    expect(answers.result).toBe('Pass')
    expect('hacked' in answers).toBe(false)
  })

  it('follows jumps and hidden pages', () => {
    const schema = schemaOf('job_application')
    const logic = evaluateLogic(schema, {})
    expect(pathPages(schema, logic)[0]).toBe(0)
    expect(new Set(pathPages(schema, logic)).size).toBe(pathPages(schema, logic).length)
  })

  it('makes public keys of 10 unambiguous letters and digits', () => {
    const keys = Array.from({ length: 200 }, newPublicKey)
    for (const key of keys) expect(key).toMatch(FORM_KEY_PATTERN)
    expect(keys.some(key => /[0OIl1]/.test(key))).toBe(false)
    expect(new Set(keys).size).toBe(keys.length)
  })
})

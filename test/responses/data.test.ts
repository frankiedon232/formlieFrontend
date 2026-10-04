import { describe, expect, it } from 'vitest'
import { parseSampleId, rngOf, sampleAnswers, sampleId, samplePerson } from '../../server/mock/data/sampleAnswers'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'

// Sample responses (decision 100): stable ids, people and answers that fit each question.
const schema: FormSchemaV1 = {
  schema_version: 1,
  pages: [
    {
      id: 'p1',
      rows: [
        {
          id: 'r1',
          fields: [
            { id: 'f1', key: 'email', type: 'email', label: 'Email', width: 12, required: true } as never,
            { id: 'f2', key: 'score', type: 'rating', label: 'Score', width: 12, required: true, props: { max: 5 } } as never,
            { id: 'f3', key: 'pick', type: 'radio', label: 'Pick', width: 12, required: true, options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }] } as never,
          ],
        },
      ],
    },
  ],
}

describe('sample responses', () => {
  it('round-trips sample ids back to the form and index', () => {
    const id = sampleId('a1b2c3d4-0006-4000-8000-1234567890ab', 1815)
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/)
    expect(parseSampleId(id)).toEqual({ index: 1815, tail: '1234567890ab' })
    expect(parseSampleId('a1b2c3d4-0006-4000-8000-1234567890ab')).toBeNull()
  })

  it('gives the same answers every time, fitting each question', () => {
    const person = samplePerson(rngOf('form:person:7'))
    const first = sampleAnswers(schema, 'form', 7, person, Date.parse('2026-10-01'))
    expect(sampleAnswers(schema, 'form', 7, person, Date.parse('2026-10-01'))).toEqual(first)
    expect(first.email).toBe(person.email)
    expect(person.email).toMatch(/@example\.(com|org|net)$/)
    expect(person.phone).toMatch(/^\+44 7700 900\d{3}$/)
    expect(Number(first.score)).toBeGreaterThanOrEqual(1)
    expect(Number(first.score)).toBeLessThanOrEqual(5)
    expect(['a', 'b']).toContain(first.pick)
  })
})

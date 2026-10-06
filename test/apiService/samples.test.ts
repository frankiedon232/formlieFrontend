import { describe, expect, it } from 'vitest'
import { NOT_ACCEPTED_TYPES, sampleValue } from '../../shared/utils/apiService/endpoints'
import { FIELD_TYPES } from '../../shared/utils/forms/fields'
import { validateAnswer } from '../../shared/utils/forms/validate'

describe('example values', () => {
  it('pass the form\'s own checks for every question type the API accepts', () => {
    const refused = Object.keys(FIELD_TYPES)
      .filter(type => !NOT_ACCEPTED_TYPES.includes(type))
      .map(type => {
        const field = { id: 'x', key: 'k', label: 'k', type, options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }] } as never
        return { type, issue: validateAnswer(field, sampleValue(field), true) }
      })
      .filter(item => item.issue)
    expect(refused).toEqual([])
  })
})

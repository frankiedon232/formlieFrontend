import { describe, expect, it } from 'vitest'
import type { ApiEndpointField } from '../../shared/types/apiService'
import { blankSchema, type FormField } from '../../shared/utils/forms/build'
import { endpointFieldsOf, exampleRequestBody, withLevelSamples } from '../../shared/utils/apiService/endpoints'
import { choiceOut, choicesIn } from '../../shared/utils/apiService/choices'

const country: FormField = { id: 'f1', key: 'country', type: 'dropdown', label: 'Country', option_set_id: 'l', option_level: 0, options: [{ value: 'ca', label: 'Canada' }, { value: 'jp', label: 'Japan' }] }
const region: FormField = { id: 'f2', key: 'region', type: 'dropdown', label: 'Region', option_set_id: 'l', option_level: 1, option_parent: 'f1', options: [{ value: 'tk', label: 'Tokyo', parent: 'jp' }, { value: 'on', label: 'Ontario', parent: 'ca' }] }

describe('API endpoints and lists with levels', () => {
  const schema = blankSchema()
  schema.pages[0]!.rows = [{ id: 'r1', fields: [country, region] }]
  const fields = endpointFieldsOf(schema)

  it('say which question a level depends on, with each value’s parent', () => {
    const level = fields.find(field => field.key === 'region')!
    expect(level.depends_on).toBe('country')
    expect(level.options?.[0]).toEqual({ value: 'tk', label: 'Tokyo', parent: 'jp' })
    expect(fields.find(field => field.key === 'country')!.depends_on).toBeUndefined()
  })

  it('give examples the API accepts: a level’s value sits under the example above', () => {
    const narrowed = withLevelSamples(fields as ApiEndpointField[])
    expect(narrowed.find(field => field.key === 'region')!.options!.map(option => option.value)).toEqual(['on'])
    const body = exampleRequestBody(fields.map(field => ({ ...field, accept: true })))
    expect(body).toMatchObject({ country: 'Canada', region: 'Ontario' })
  })
})

describe('choices in the public API, by label (owner 2026-10-08)', () => {
  const country = { id: 'f1', key: 'country', options: [{ value: 'ca', label: 'Canada' }, { value: 'us', label: 'United States' }] }
  const city = { id: 'f2', key: 'city', option_parent: 'f1', options: [{ value: 'ca_springfield', label: 'Springfield', parent: 'ca' }, { value: 'us_springfield', label: 'Springfield', parent: 'us' }] }

  it('return the label people saw, for one or several choices', () => {
    expect(choiceOut(country, 'ca')).toBe('Canada')
    expect(choiceOut(country, ['ca', 'us'])).toEqual(['Canada', 'United States'])
    expect(choiceOut({ key: 'note' }, 'free text')).toBe('free text')
  })

  it('take a label or a value, a shared label settled by the choice above', () => {
    expect(choicesIn([country, city], { country: 'united states', city: 'Springfield' })).toEqual({ country: 'us', city: 'us_springfield' })
    expect(choicesIn([country, city], { country: 'ca', city: ['Springfield'] })).toEqual({ country: 'ca', city: ['ca_springfield'] })
    expect(choicesIn([country], { country: 'Mars' })).toEqual({ country: 'Mars' })
  })
})

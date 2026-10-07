import { describe, expect, it } from 'vitest'
import type { ApiEndpointField } from '../../shared/types/apiService'
import { blankSchema, type FormField } from '../../shared/utils/forms/build'
import { endpointFieldsOf, exampleRequestBody, withLevelSamples } from '../../shared/utils/apiService/endpoints'

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
    expect(body).toMatchObject({ country: 'ca', region: 'on' })
  })
})

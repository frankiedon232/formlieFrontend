import { describe, expect, it } from 'vitest'
import { apiChanges, checkApiName, checkEndpointName, endpointFieldsOf, endpointNameFrom, exampleRecord, exampleRequestBody, notAcceptedReason } from '../../shared/utils/apiService/endpoints'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'

const field = (key: string, type: string, extra: Record<string, unknown> = {}) => ({ id: `f_${key}`, key, type, label: key.replace(/_/g, ' '), ...extra })
const schema = {
  schema_version: 1,
  pages: [
    { id: 'p1', rows: [{ id: 'r1', fields: [field('full_name', 'short_text', { required: true }), field('email', 'email'), field('intro', 'paragraph')] }] },
    { id: 'p2', rows: [{ id: 'r2', fields: [field('cv', 'file_upload'), field('total', 'calculated'), field('reference', 'short_text', { readonly: true }), field('topic', 'dropdown')] }] },
  ],
} as unknown as FormSchemaV1

describe('endpoint fields', () => {
  it('turns questions into fields with safe defaults (layout blocks left out)', () => {
    const fields = endpointFieldsOf(schema)
    expect(fields.map(item => item.key)).toEqual(['full_name', 'email', 'cv', 'total', 'reference', 'topic'])
    const byKey = Object.fromEntries(fields.map(item => [item.key, item]))
    expect(byKey.full_name).toMatchObject({ page: 0, form_required: true, accept: true, required: true, returned: true })
    expect(byKey.email).toMatchObject({ accept: true, required: false, filterable: true, filter: false })
    expect(byKey.cv).toMatchObject({ page: 1, acceptable: true, accept: true, returned: true })
    expect(byKey.total!.accept).toBe(false)
    expect(byKey.reference!.accept).toBe(false)
  })

  it('keeps saved choices but never lets a form-required question go unaccepted', () => {
    const fields = endpointFieldsOf(schema, [
      { key: 'full_name', accept: false, required: false, returned: false, filter: false },
      { key: 'email', accept: true, required: true, returned: true, filter: true },
      { key: 'cv', accept: true, required: true, returned: false, filter: true },
      { key: 'total', accept: true, required: true, returned: true, filter: false },
    ])
    const byKey = Object.fromEntries(fields.map(item => [item.key, item]))
    expect(byKey.full_name).toMatchObject({ accept: true, required: true, returned: false })
    expect(byKey.email).toMatchObject({ accept: true, required: true, filter: true })
    expect(byKey.cv).toMatchObject({ accept: true, required: true, returned: false, filter: false })
    expect(byKey.total).toMatchObject({ accept: false, required: false })
  })

  it('says why a question cannot be sent', () => {
    const fields = Object.fromEntries(endpointFieldsOf(schema).map(item => [item.key, item]))
    expect(notAcceptedReason(fields.cv!)).toBeNull()
    expect(notAcceptedReason(fields.total!)).toBe('calculated')
    expect(notAcceptedReason(fields.reference!)).toBe('locked')
    expect(notAcceptedReason(fields.email!)).toBeNull()
  })
})

describe('endpoint names', () => {
  it('accepts lower-case words joined by single hyphens, 3 to 64 characters', () => {
    expect(checkEndpointName('register-account')).toBeNull()
    expect(checkEndpointName('')).toBe('required')
    expect(checkEndpointName('ab')).toBe('pattern')
    expect(checkEndpointName('Register')).toBe('pattern')
    expect(checkEndpointName('-start')).toBe('pattern')
    expect(checkEndpointName('double--hyphen')).toBe('pattern')
    expect(checkEndpointName('token')).toBe('reserved')
  })

  it('suggests a name from a form name', () => {
    expect(endpointNameFrom('Register account')).toBe('register-account')
    expect(endpointNameFrom('  Café & Résumé 2026! ')).toBe('cafe-resume-2026')
    expect(endpointNameFrom('Quote - Estimate Request')).toBe('quote-estimate-request')
  })
})

describe('examples', () => {
  it('use the form\'s own answer values for choices', () => {
    const withChoices = { ...schema, pages: [{ id: 'p', rows: [{ id: 'r', fields: [field('position', 'dropdown', { options: [{ value: 'designer', label: 'Designer' }, { value: 'engineer', label: 'Engineer' }] }), field('skills', 'checkbox', { options: [{ value: 'vue', label: 'Vue' }, { value: 'ts', label: 'TypeScript' }, { value: 'sql', label: 'SQL' }] })] }] }] } as unknown as FormSchemaV1
    expect(exampleRequestBody(endpointFieldsOf(withChoices))).toEqual({ position: 'designer', skills: ['vue', 'ts'] })
  })

  it('sends accepted fields (required first) and returns the returned ones', () => {
    const fields = endpointFieldsOf(schema, [{ key: 'email', accept: true, required: false, returned: false, filter: false }])
    expect(Object.keys(exampleRequestBody(fields))).toEqual(['full_name', 'email', 'cv', 'topic'])
    const record = exampleRecord(fields)
    expect(Object.keys(record.data)).toEqual(['full_name', 'cv', 'total', 'reference', 'topic'])
    expect(record).toMatchObject({ status: 'new' })
  })
})

describe('what a new version changes for apps', () => {
  it('lists added, removed and newly required questions; labels alone change nothing', () => {
    const live = [
      { key: 'first_name', label: 'First name', required: true, type: 'short_text' },
      { key: 'email', label: 'Email', required: false, type: 'email' },
      { key: 'notes', label: 'Notes', required: false, type: 'long_text' },
      { key: 'intro', label: 'Intro', required: false, type: 'paragraph' },
    ]
    const draft = [
      { key: 'first_name', label: 'Given name', required: true, type: 'short_text' },
      { key: 'email', label: 'Email', required: true, type: 'email' },
      { key: 'phone', label: 'Phone', required: true, type: 'phone' },
      { key: 'total', label: 'Total', required: false, type: 'calculated' },
    ]
    expect(apiChanges(live, draft)).toEqual({
      added: [{ key: 'phone', label: 'Phone', required: true }],
      removed: [{ key: 'notes', label: 'Notes' }],
      nowRequired: [{ key: 'email', label: 'Email' }],
    })
    expect(apiChanges(live.slice(0, 2), live.slice(0, 2).map(field => ({ ...field, label: `${field.label}!` })))).toEqual({ added: [], removed: [], nowRequired: [] })
  })
})

describe('API names', () => {
  const suffixed = { schema_version: 1, pages: [{ id: 'p', rows: [{ id: 'r', fields: [field('first_name_w6r3', 'short_text', { label: 'First Name' }), field('status_x1', 'short_text', { label: 'Status' }), field('first_name_a9', 'short_text', { label: 'First name' }), field('phone_number_4cde', 'short_text', { label: 'Phone Number' })] }] }] } as unknown as FormSchemaV1

  it('come from the label, never reserved, unique', () => {
    expect(endpointFieldsOf(suffixed).map(item => item.name)).toEqual(['first_name', 'status_2', 'first_name_2', 'phone_number'])
  })

  it('keep a saved name, fix an invalid one', () => {
    const fields = endpointFieldsOf(suffixed, [
      { key: 'first_name_w6r3', name: 'given', accept: true, required: false, returned: true, filter: false },
      { key: 'status_x1', name: 'Bad Name', accept: true, required: false, returned: true, filter: false },
    ])
    expect(fields.map(item => item.name)).toEqual(['given', 'status_2', 'first_name', 'phone_number'])
    expect(checkApiName('first_name')).toBeNull()
    expect(checkApiName('id')).toBe('reserved')
    expect(checkApiName('First')).toBe('pattern')
  })

  it('shape the examples, with values that fit the label', () => {
    const body = exampleRequestBody(endpointFieldsOf(suffixed))
    expect(body).toMatchObject({ first_name: 'Alex', phone_number: '+44 7700 900123' })
    expect(Object.keys(exampleRecord(endpointFieldsOf(suffixed)).data)).toContain('first_name')
  })
})

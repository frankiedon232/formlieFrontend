import { describe, expect, it } from 'vitest'
import { checkEndpointName, endpointFieldsOf, endpointNameFrom, exampleRecord, exampleRequestBody, notAcceptedReason } from '../../shared/utils/apiService/endpoints'
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
    expect(byKey.cv).toMatchObject({ page: 1, acceptable: false, accept: false, returned: true })
    expect(byKey.total!.accept).toBe(false)
    expect(byKey.reference!.accept).toBe(false)
  })

  it('keeps saved choices but never lets a form-required question go unaccepted', () => {
    const fields = endpointFieldsOf(schema, [
      { key: 'full_name', accept: false, required: false, returned: false, filter: false },
      { key: 'email', accept: true, required: true, returned: true, filter: true },
      { key: 'cv', accept: true, required: true, returned: false, filter: true },
    ])
    const byKey = Object.fromEntries(fields.map(item => [item.key, item]))
    expect(byKey.full_name).toMatchObject({ accept: true, required: true, returned: false })
    expect(byKey.email).toMatchObject({ accept: true, required: true, filter: true })
    expect(byKey.cv).toMatchObject({ accept: false, required: false, returned: false, filter: false })
  })

  it('says why a question cannot be sent', () => {
    const fields = Object.fromEntries(endpointFieldsOf(schema).map(item => [item.key, item]))
    expect(notAcceptedReason(fields.cv!)).toBe('file')
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
  it('sends accepted fields (required first) and returns the returned ones', () => {
    const fields = endpointFieldsOf(schema, [{ key: 'email', accept: true, required: false, returned: false, filter: false }])
    expect(Object.keys(exampleRequestBody(fields))).toEqual(['full_name', 'email', 'topic'])
    const record = exampleRecord(fields)
    expect(Object.keys(record.data)).toEqual(['full_name', 'cv', 'total', 'reference', 'topic'])
    expect(record).toMatchObject({ status: 'new' })
  })
})

import { describe, expect, it } from 'vitest'
import { buildSchema } from '../../shared/templates/kit'
import { formSchemaV1 } from '../../shared/utils/forms/schema'
import { allFields } from '../../shared/utils/forms/build'
import { draftForm, titleFrom } from '../../server/mock/ai/formEngine'

const fieldsOf = (prompt: string, extra: Partial<Parameters<typeof draftForm>[0]> = {}) => {
  const result = draftForm({ prompt, ...extra })
  const schema = buildSchema(result.def)
  expect(formSchemaV1.safeParse(schema).success).toBe(true)
  return { result, schema, fields: allFields(schema) }
}

describe('AI form engine (mock)', () => {
  it('names the form from the description', () => {
    expect(titleFrom('A sign-in form for visitors at reception', 'x')).toBe('Visitor sign-in form')
    expect(titleFrom('Customer satisfaction survey for our shops', 'x')).toBe('Shop customer satisfaction survey')
    expect(titleFrom('hello there', 'Fallback')).toBe('Fallback')
  })

  it('turns a listed description into the right fields', () => {
    const { result, fields } = fieldsOf('A sign-in form for visitors at reception: name, company, who they are visiting, arrival time, a photo and agreement to the site rules.')
    expect(result.source).toBe('list')
    const types = fields.map(field => field.type)
    expect(types).toContain('full_name')
    expect(types).toContain('image_upload')
    expect(types).toContain('datetime')
    expect(types).toContain('consent')
    expect(types.at(-1)).toBe('consent')
    expect(fields.find(field => field.type === 'short_text' && /company/i.test(field.label))).toBeTruthy()
  })

  it('adds a follow-up after a yes and a total for quantity × price', () => {
    const { schema, fields } = fieldsOf('An order request with: item, quantity, unit price, any special requirements, details of the requirements')
    expect(fields.some(field => field.type === 'calculated')).toBe(true)
    expect((schema.logic ?? []).length).toBeGreaterThan(0)
  })

  it('reads questions from a pasted document, sections as pages', () => {
    const doc = 'SECTION A\nFull name:\nDate of incident:\nWas anyone hurt? ( ) Yes ( ) No\n\nSECTION B\nDescribe what happened?\nShift: Morning / Afternoon / Night\nSignature: ________'
    const { result, schema, fields } = fieldsOf('Incident report', { document: doc })
    expect(result.source).toBe('document')
    expect(schema.pages.length).toBe(2)
    expect(fields.find(field => field.label.startsWith('Shift'))?.type).toBe('radio')
    expect(fields.find(field => /hurt/i.test(field.label))?.type).toBe('toggle')
    expect(fields.at(-1)?.type).toBe('signature')
  })

  it('falls back to the closest template, another one on try again', () => {
    const first = draftForm({ prompt: 'job application for our warehouse roles' })
    expect(first.source).toBe('template')
    expect(first.based_on).not.toBeNull()
    const second = draftForm({ prompt: 'job application for our warehouse roles', variant: 1 })
    expect(second.based_on?.key).not.toBe(first.based_on?.key)
  })

  it('makes a basic form when there is little to go on', () => {
    const { result, fields } = fieldsOf('zzz')
    expect(result.source).toBe('basic')
    expect(fields.length).toBeGreaterThanOrEqual(3)
  })
})

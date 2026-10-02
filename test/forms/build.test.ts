import { describe, expect, it } from 'vitest'
import {
  allFields,
  blankSchema,
  keyFromLabel,
  publishIssues,
  starterSchema,
} from '../../shared/utils/forms/build'
import { FIELD_TYPE_KEYS } from '../../shared/utils/forms/fields'
import { formImportFile, formSchemaV1 } from '../../shared/utils/forms/schema'
import { STARTER_TEMPLATE_KEYS } from '../../shared/utils/templates/starters'

describe('form schema helpers', () => {
  it('every starter template is a valid, publishable FormSchema v1 with unique keys', () => {
    for (const key of STARTER_TEMPLATE_KEYS) {
      const schema = starterSchema(key)
      expect(formSchemaV1.safeParse(schema).success, key).toBe(true)
      expect(publishIssues(schema), key).toEqual([])
      const keys = allFields(schema).map(f => f.key)
      expect(new Set(keys).size, key).toBe(keys.length)
      for (const field of allFields(schema)) expect(FIELD_TYPE_KEYS, key).toContain(field.type)
    }
  })

  it('makes readable, unique field keys', () => {
    expect(keyFromLabel('Full name', [])).toBe('full_name')
    expect(keyFromLabel('Café — préféré ?', [])).toBe('cafe_prefere')
    expect(keyFromLabel('2nd address', [])).toBe('f_2nd_address')
    expect(keyFromLabel('Email', ['email', 'email_2'])).toBe('email_3')
    expect(keyFromLabel('???', [])).toBe('field')
  })

  it('reports what blocks publishing', () => {
    const empty = blankSchema()
    expect(publishIssues(empty).map(i => i.code)).toEqual(['no_inputs'])

    const schema = starterSchema('contact_lead')
    const [first, second] = allFields(schema)
    first!.label = ''
    second!.key = first!.key
    const dropdown = allFields(schema).find(f => f.type === 'dropdown')!
    dropdown.options = []
    const codes = publishIssues(schema).map(i => i.code)
    expect(codes).toContain('empty_label')
    expect(codes).toContain('duplicate_key')
    expect(codes).toContain('no_options')
  })

  it('imports a bare schema or a { name, schema } export, and refuses junk', () => {
    const schema = starterSchema('incident_report')
    expect(formImportFile.safeParse(schema).success).toBe(true)
    expect(formImportFile.safeParse({ name: 'Incident', schema }).success).toBe(true)
    expect(formImportFile.safeParse({ schema_version: 2, pages: [] }).success).toBe(false)
    const bad = structuredClone(schema)
    bad.pages[0]!.rows[0]!.fields[0]!.width = 20
    expect(formSchemaV1.safeParse(bad).success).toBe(false)
  })
})

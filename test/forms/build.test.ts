import { describe, expect, it } from 'vitest'
import {
  allFields,
  blankSchema,
  diffSchemas,
  fieldKey,
  sectionOwners,
  type FormField,
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

describe('diffSchemas', () => {
  it('lists added, removed and changed fields', () => {
    const before = starterSchema('incident_report')
    const after = structuredClone(before)
    const first = allFields(after)[0]
    const second = allFields(after).at(-1)
    first!.label = 'Renamed'
    for (const page of after.pages) page.rows = page.rows.filter(row => !row.fields.some(f => f.id === second!.id))
    after.pages[0]!.rows.push({ id: 'row_x', fields: [{ ...structuredClone(first!), id: 'fld_new', key: 'extra' }] })
    const diff = diffSchemas(before, after)
    expect(diff.changed.map(f => f.id)).toEqual([first!.id])
    expect(diff.removed.map(f => f.id)).toContain(second!.id)
    expect(diff.added.map(f => f.id)).toEqual(['fld_new'])
    expect(diffSchemas(before, before)).toMatchObject({ added: [], removed: [], changed: [], pages: 0, rules: 0 })
  })
})

describe('sectionOwners', () => {
  const f = (id: string, type: string, props?: Record<string, unknown>) => ({ id, key: id, type, label: id, props }) as FormField
  it('assigns rows to the collapsible section above them', () => {
    const owners = sectionOwners([
      { id: 'r0', fields: [f('a', 'short_text')] },
      { id: 'r1', fields: [f('s1', 'section', { collapsible: true })] },
      { id: 'r2', fields: [f('b', 'email')] },
      { id: 'r3', fields: [f('s2', 'section')] },
      { id: 'r4', fields: [f('c', 'phone')] },
    ])
    expect([...owners.values()]).toEqual([null, null, 's1', null, null])
  })
})

describe('field keys and locked fields', () => {
  it('adds a stable suffix from the field id', () => {
    expect(fieldKey('Full name', 'fld_k3x9abcdef', [])).toBe('full_name_k3x9')
    expect(fieldKey('Full name', 'fld_k3x9abcdef', ['full_name_k3x9'])).toBe('full_name_k3x9_2')
  })

  it('flags required fields nobody can fill in', () => {
    const schema = starterSchema('contact_lead')
    const field = allFields(schema).find(f => f.required)!
    field.readonly = true
    expect(publishIssues(schema).some(i => i.code === 'locked_required' && i.field_id === field.id)).toBe(true)
  })
})

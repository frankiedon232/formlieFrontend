import { describe, expect, it } from 'vitest'
import { withUrlPrefill } from '../../shared/utils/forms/prefill'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'

const schema = {
  schema_version: 1,
  pages: [
    {
      id: 'p1',
      title: 'Page',
      rows: [
        {
          id: 'r1',
          fields: [
            { id: 'a', key: 'source', type: 'hidden', label: 'Source' },
            { id: 'b', key: 'email', type: 'email', label: 'Email', props: { url_prefill: true } },
            { id: 'c', key: 'notes', type: 'long_text', label: 'Notes' },
            { id: 'd', key: 'topic', type: 'dropdown', label: 'Topic', options: [{ value: 'question', label: 'A question' }], props: { url_prefill: true } },
            { id: 'e', key: 'name', type: 'full_name', label: 'Name', props: { url_prefill: true } },
          ],
        },
      ],
    },
  ],
  logic: [],
  calculations: [],
} as unknown as FormSchemaV1
const field = (result: FormSchemaV1, key: string) => result.pages[0]!.rows[0]!.fields.find(item => item.key === key)!

describe('starting values from the address', () => {
  it('fills hidden fields and fields that allow it, nothing else', () => {
    const result = withUrlPrefill(schema, { source: 'help', email: 'ada@example.com', notes: 'sneaky', topic: 'question' })
    expect(field(result, 'source').default).toBe('help')
    expect(field(result, 'email').default).toBe('ada@example.com')
    expect(field(result, 'notes').default).toBeUndefined()
    expect(field(result, 'topic').default).toBe('question')
  })

  it('refuses a choice that is not an option, and splits a full name', () => {
    const result = withUrlPrefill(schema, { topic: 'hack', name: 'Ada Love Lace' })
    expect(field(result, 'topic').default).toBeUndefined()
    expect(field(result, 'name').default).toEqual({ first: 'Ada Love', last: 'Lace' })
  })

  it('leaves the schema alone without values', () => {
    expect(withUrlPrefill(schema, {})).toBe(schema)
  })
})

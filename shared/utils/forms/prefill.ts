/**
 * Starting values from the form's address (owner 2026-10-10): `?{field key}=value` fills a **hidden** field, or a
 * field the form allows it for (`props.url_prefill`), e.g. where a link was shared from, a reference, or the
 * person's email when the app opens a form for them. Nothing else can be set from outside. Values are text,
 * trimmed and cut to 500 characters; a choice must be one of its options; a full name is split into first and
 * last name (the last word is the last name).
 */
import type { FormSchemaV1 } from './schema'
import type { FormField } from './build'

const CHOICES = new Set(['dropdown', 'single_choice', 'radio', 'yes_no'])

export function prefillable(field: FormField) {
  return field.type === 'hidden' || field.props?.url_prefill === true
}

export function withUrlPrefill(schema: FormSchemaV1, query: Record<string, unknown>): FormSchemaV1 {
  const values = new Map(Object.entries(query).flatMap(([key, value]) => (typeof value === 'string' && value.trim() ? [[key, value.trim().slice(0, 500)] as const] : [])))
  if (!values.size) return schema
  let changed = false
  const pages = schema.pages.map(page => ({
    ...page,
    rows: page.rows.map(row => ({
      ...row,
      fields: (row.fields as FormField[]).map(field => {
        const value = values.get(field.key)
        if (value === undefined || !prefillable(field)) return field
        if (CHOICES.has(field.type) && field.options && !field.options.some(option => option.value === value)) return field
        changed = true
        if (field.type === 'full_name') {
          const words = value.split(/\s+/)
          return { ...field, default: words.length > 1 ? { first: words.slice(0, -1).join(' '), last: words.at(-1) } : { first: value, last: '' } }
        }
        return { ...field, default: value }
      }),
    })),
  }))
  return changed ? ({ ...schema, pages } as FormSchemaV1) : schema
}

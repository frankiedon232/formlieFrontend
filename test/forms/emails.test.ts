import { describe, expect, it } from 'vitest'
import { formEmailsOf, formEmailsOn, suggestReceiptField } from '../../shared/utils/forms/emails'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'

const schema = (settings: Record<string, unknown> = {}): FormSchemaV1 => ({
  schema_version: 1,
  settings,
  pages: [{ id: 'p1', rows: [{ id: 'r1', fields: [{ id: 'f1', key: 'contact', type: 'email', label: 'Contact' }, { id: 'f2', key: 'own_email', type: 'email', label: 'Your email' }] }] }],
}) as FormSchemaV1

describe('form response emails', () => {
  it('are off until set', () => {
    const emails = formEmailsOf(schema())
    expect(emails).toEqual({ team: [], others: [], others_personal: false, receipt_field: null })
    expect(formEmailsOn(emails)).toBe(false)
  })

  it('send the copy to the respondent’s own email first, else the first email question', () => {
    expect(suggestReceiptField(schema({ identity: { email: 'own_email', verify: false } }))).toBe('own_email')
    expect(suggestReceiptField(schema())).toBe('contact')
  })

  it('count as on with any recipient', () => {
    expect(formEmailsOn(formEmailsOf(schema({ emails: { team: [], others: ['partner@example.com'], others_personal: false, receipt_field: null } })))).toBe(true)
  })
})

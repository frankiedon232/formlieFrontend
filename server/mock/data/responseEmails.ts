/**
 * A form's response emails in the mock (F14 M4, shared/utils/forms/emails.ts): after a response is
 * stored (form page or API), the chosen team members get it with a link to it, outside addresses get
 * it without a link and with personal answers masked (unless the form says otherwise), and the
 * respondent gets a copy in the language they filled in. Never throws.
 */
import type { H3Event } from 'h3'
import { allFields } from '#shared/utils/forms/build'
import { answerText } from '#shared/utils/forms/answer-text'
import { formEmailsOf } from '#shared/utils/forms/emails'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { emailDate, emailLanguage, templateText, type EmailAnswer } from '../core/email'
import { encodeId } from '../core/ids'
import { PERSONAL_TYPES } from '../core/mask'
import { workspaceUrl } from './notificationStore'
import { peopleOf } from './orgStore'
import { sendEmail } from './outboxStore'
import type { MockTenant } from './tenants'

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const mask = (text: string) => (text.length <= 2 ? '••' : `${text[0]}•••${text.slice(-1)}`)

export function emailResponse(event: H3Event | null, tenant: MockTenant, form: { id: string; name: string; responses_count: number }, schema: FormSchemaV1 | null, response: { id: string; data: Record<string, unknown>; submitted_at: string; language?: string | null }) {
  try {
    if (!schema) return
    const settings = formEmailsOf(schema)
    if (!settings.team.length && !settings.others.length && !settings.receipt_field) return
    const fields = allFields(schema).filter(field => field.key in response.data)
    const answers = (hidePersonal: boolean): EmailAnswer[] =>
      fields
        .map(field => {
          const value = answerText(field, response.data[field.key])
          return { label: field.label?.trim() || field.key, value: value && hidePersonal && PERSONAL_TYPES.has(field.type) ? mask(value) : value }
        })
        .filter(item => item.value !== '')
    const vars = (language: string) => ({ form: form.name, number: form.responses_count, date: emailDate(tenant, language, response.submitted_at) })

    // The team: everything, and where to find it
    const language = emailLanguage(tenant)
    const link = workspaceUrl(event, tenant, `/forms/${encodeId(form.id)}/responses?response=${encodeId(response.id)}`)
    for (const person of peopleOf(tenant).filter(item => settings.team.includes(item.id)))
      sendEmail(tenant, { to: person.email, key: 'response_notification', language, vars: { ...vars(language), link }, answers: answers(false), reason: 'response' })

    // Outside addresses: no link into the portal, personal answers masked unless allowed
    if (settings.others.length) {
      const text = templateText(tenant, 'response_notification', language).text
      const withoutLink = { subject: text.subject, body: text.body.split('\n').filter(line => !line.includes('{{link}}')).join('\n') }
      for (const to of settings.others) sendEmail(tenant, { to, key: 'response_notification', language, vars: vars(language), answers: answers(!settings.others_personal), text: withoutLink, reason: 'response_outside', footer: 'form' })
    }

    // The respondent: their own answers, in their language
    const to = settings.receipt_field ? String(response.data[settings.receipt_field] ?? '').trim() : ''
    if (EMAIL.test(to)) {
      const theirs = emailLanguage(tenant, response.language)
      sendEmail(tenant, { to, key: 'response_receipt', language: theirs, vars: vars(theirs), answers: answers(false), reason: 'receipt', footer: 'form' })
    }
  } catch (error) {
    console.error('[response-emails]', error)
  }
}

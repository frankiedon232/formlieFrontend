/**
 * Email templates and the sent log (F14 M4, docs/API-CONTRACT.md → Emails). Admins only.
 *
 *   GET  /settings/emails/templates/:key?language=   default and own text, the placeholders
 *   POST /settings/emails/preview                    { key, language, subject, body } → rendered with sample values
 *   POST /settings/emails/test                       the same, sent to the admin (lands in the sent log)
 *   GET  /settings/emails/sent?q=&page=&per_page=    the sent log, newest first (no bodies)
 *   GET  /settings/emails/sent/:id                   one email with its HTML
 */
import { z } from 'zod'
import { EMAIL_TEMPLATES, EMAIL_VARIABLES, type EmailTemplateKey, type EmailTemplateView, type SentEmail } from '#shared/types/emails'
import { emailTextSchema } from '#shared/utils/settings/schemas'
import { requireAdmin } from '../core/auth'
import { emailDate, emailDefaults, emailLanguage, renderEmail, templateText, type EmailAnswer } from '../core/email'
import { MockError, ok, paginate } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { workspaceUrl } from '../data/notificationStore'
import { outboxOf, sendEmail } from '../data/outboxStore'
import type { MockTenant, MockUser } from '../data/tenants'
import type { H3Event } from 'h3'

const keyOf = (value: string | undefined): EmailTemplateKey => {
  if (!value || !(EMAIL_TEMPLATES as readonly string[]).includes(value)) throw new MockError('FRM-GEN-1004')
  return value as EmailTemplateKey
}

export const getTemplate = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const key = keyOf(getRouterParam(event, 'key'))
  const language = emailLanguage(tenant, typeof query.language === 'string' ? query.language : null)
  const { custom, fallback } = templateText(tenant, key, language)
  return ok<EmailTemplateView>({ key, language, default: fallback, custom, variables: EMAIL_VARIABLES[key] })
})

/** Believable values for a preview or test, in the email's language. */
function sampleValues(event: H3Event, tenant: MockTenant, user: MockUser, key: EmailTemplateKey, language: string) {
  const texts = emailDefaults(language)
  const form = 'Customer feedback'
  const vars: Record<string, string | number> = {
    name: user.first_name,
    code: '483921',
    minutes: 5,
    inviter: `${user.first_name} ${user.last_name}`,
    form,
    number: 128,
    date: emailDate(tenant, language),
    link: workspaceUrl(event, tenant, key === 'invitation' ? '/auth/login' : '/'),
    title: texts.events.response_new!.title.replace('{{form}}', form),
    message: texts.events.response_new!.message.replace('{{form}}', form),
    summary: [texts.events.response_new!.title.replace('{{form}}', form), texts.events.export_ready!.title].join('\n'),
  }
  const answers: EmailAnswer[] = key === 'response_notification' || key === 'response_receipt'
    ? [
        { label: 'Full name', value: 'Ada Visitor' },
        { label: 'Email', value: 'ada@example.com' },
        { label: 'How likely are you to recommend us?', value: '9' },
        { label: 'Anything else?', value: 'Quick and friendly service.' },
      ]
    : []
  return { vars, answers }
}

const previewSchema = emailTextSchema.extend({ key: z.enum(EMAIL_TEMPLATES), language: z.string().max(10) })

export const previewEmail = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(previewSchema, body)
  const language = emailLanguage(tenant, input.language)
  const { vars, answers } = sampleValues(event, tenant, user, input.key, language)
  const rendered = renderEmail(tenant, input.key, language, vars, { answers, text: { subject: input.subject, body: input.body }, footer: input.key === 'response_receipt' ? 'form' : 'account' })
  return ok({ subject: rendered.subject, html: rendered.html, from: rendered.from, reply_to: rendered.reply_to })
})

export const testEmail = defineMockRoute(({ event, body }) => {
  const { tenant, user } = requireAdmin(event)
  const input = parseBody(previewSchema, body)
  const language = emailLanguage(tenant, input.language)
  const { vars, answers } = sampleValues(event, tenant, user, input.key, language)
  const sent = sendEmail(tenant, { to: user.email, key: input.key, language, vars, answers, reason: 'test', text: { subject: input.subject, body: input.body }, footer: input.key === 'response_receipt' ? 'form' : 'account' })
  if (!sent) throw new MockError('FRM-GEN-5000')
  const { html: _h, text: _t, ...item } = sent
  return ok(item)
})

export const listSent = defineMockRoute(({ event, query }) => {
  const { tenant } = requireAdmin(event)
  const rows = outboxOf(tenant).map(({ html: _h, text: _t, ...item }) => item)
  const { data, meta } = paginate(rows, { ...query, sort: undefined }, (row, q) => `${row.to} ${row.subject}`.toLowerCase().includes(q))
  return ok(data, meta)
})

export const getSent = defineMockRoute(({ event }) => {
  const { tenant } = requireAdmin(event)
  const found = outboxOf(tenant).find(item => item.id === getRouterParam(event, 'id'))
  if (!found) throw new MockError('FRM-GEN-1004')
  return ok<SentEmail>(found)
})

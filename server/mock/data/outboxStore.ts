/**
 * The sent log in the mock (F14 M4), kept in `.data/mock/outbox.json`: every email Formalie would have
 * sent for a workspace (codes, notifications, responses, tests), newest first, the last 200. Settings →
 * Email templates shows it, so emails can be checked before a real mail service exists.
 */
import type { EmailAnswer } from '../core/email'
import type { EmailTemplateKey, SentEmail } from '#shared/types/emails'
import { loadPersisted, savePersisted } from '../core/persist'
import { emailLanguage, renderEmail } from '../core/email'
import type { MockTenant } from './tenants'

const KEEP = 200
const stores = new Map<string, SentEmail[]>(Object.entries(loadPersisted<Record<string, SentEmail[]>>('outbox', {})))
const save = () => savePersisted('outbox', () => Object.fromEntries(stores))

export const outboxOf = (tenant: MockTenant) => stores.get(tenant.id) ?? []

export interface SendInput {
  to: string
  key: EmailTemplateKey
  /** The language asked for (a respondent's form language); the workspace's when it isn't offered. */
  language?: string | null
  vars: Record<string, string | number>
  reason: string
  answers?: EmailAnswer[]
  text?: { subject: string; body: string }
}

/** "Sends" an email: rendered in the workspace's look and put in its sent log. Never throws. */
export function sendEmail(tenant: MockTenant, input: SendInput): SentEmail | null {
  try {
    const language = emailLanguage(tenant, input.language)
    const rendered = renderEmail(tenant, input.key, language, input.vars, { answers: input.answers, text: input.text })
    const email: SentEmail = { id: crypto.randomUUID(), at: new Date().toISOString(), to: input.to, subject: rendered.subject, template: input.key, language, reason: input.reason, html: rendered.html, text: rendered.text }
    stores.set(tenant.id, [email, ...outboxOf(tenant)].slice(0, KEEP))
    save()
    console.info(`[mock-email] ${input.key} → ${input.to}: ${rendered.subject}`)
    return email
  } catch (error) {
    console.error('[mock-email]', error)
    return null
  }
}

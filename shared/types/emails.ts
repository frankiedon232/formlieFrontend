/**
 * Emails Formalie sends for a workspace (F14 M4, docs/API-CONTRACT.md → Emails): the sender, the
 * templates (Formalie's default text in every language, or the workspace's own), and the sent log.
 * Template text uses `{{variable}}` placeholders; `{{answers}}` becomes the answers table.
 */

export const EMAIL_TEMPLATES = ['signin_code', 'password_reset', 'invitation', 'response_notification', 'response_receipt', 'notification', 'daily_digest'] as const
export type EmailTemplateKey = (typeof EMAIL_TEMPLATES)[number]

/** The placeholders each template can use. */
export const EMAIL_VARIABLES: Record<EmailTemplateKey, string[]> = {
  signin_code: ['name', 'code', 'minutes', 'workspace'],
  password_reset: ['name', 'code', 'minutes', 'workspace'],
  invitation: ['name', 'inviter', 'workspace', 'link'],
  response_notification: ['form', 'number', 'date', 'answers', 'link', 'workspace'],
  response_receipt: ['form', 'number', 'date', 'answers', 'workspace'],
  notification: ['title', 'message', 'link', 'workspace'],
  daily_digest: ['name', 'summary', 'link', 'workspace'],
}

export interface EmailText {
  subject: string
  body: string
}

export interface EmailSettings {
  /** The "From" name; empty = the workspace's name. The address is Formalie's own sending address. */
  sender_name: string | null
  /** Where replies go; empty = replies are not delivered. */
  reply_to: string | null
  /** A line under every email (e.g. the company's address). */
  footer: string | null
  /** The workspace's own text by template and language; missing = Formalie's default. */
  custom: Partial<Record<EmailTemplateKey, Record<string, EmailText>>>
}

/** GET /settings/emails/templates/{key}?language= */
export interface EmailTemplateView {
  key: EmailTemplateKey
  language: string
  default: EmailText
  custom: EmailText | null
  variables: string[]
}

/** The sent log (the mock never sends; this is where emails land). */
export interface SentEmail {
  id: string
  at: string
  to: string
  subject: string
  template: EmailTemplateKey
  language: string
  /** Why it was sent: an event, a form, a test… */
  reason: string
  /** Sent only for this preview / log; real emails carry the same. */
  html: string
  text: string
}

/** POST /settings/emails/preview · /test */
export interface EmailPreviewRequest extends EmailText {
  key: EmailTemplateKey
  language: string
}

/**
 * A form's response emails (F14 M4, owner 2026-10-07: "emailing responses to the team and outside
 * addresses"): each new response to chosen team members and / or outside addresses, and a copy for the
 * respondent at the email they gave. Outside addresses get personal answers masked unless the form
 * owner says otherwise. Stored in the form's settings, so it applies to the published form.
 */
import type { FormSchemaV1 } from './schema'
import { allFields } from './build'
import { identityOf } from './identity'

export interface FormEmails {
  /** Team members (people ids) who get every new response. */
  team: string[]
  /** Addresses outside the workspace that get every new response. */
  others: string[]
  /** Outside addresses also see personal answers (names, emails, phone numbers…). */
  others_personal: boolean
  /** Send the respondent a copy, to the answer of this email question (null = off). */
  receipt_field: string | null
}

export const NO_FORM_EMAILS: FormEmails = { team: [], others: [], others_personal: false, receipt_field: null }

export function formEmailsOf(schema: FormSchemaV1 | null | undefined): FormEmails {
  const stored = (schema?.settings as { emails?: Partial<FormEmails> } | undefined)?.emails
  return { ...NO_FORM_EMAILS, ...stored }
}

/** The email question a copy goes to by default: the respondent's own email, else the first email question. */
export function suggestReceiptField(schema: FormSchemaV1): string | null {
  return identityOf(schema).email ?? allFields(schema).find(field => field.type === 'email')?.key ?? null
}

export const formEmailsOn = (emails: FormEmails) => !!(emails.team.length || emails.others.length || emails.receipt_field)

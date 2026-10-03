/**
 * Telling people apart on a public form (F10, owner 2026-10-03) — "is this response from someone who
 * already responded, without mistaking another person for them?"
 *
 * Identity = the respondent's OWN email (never a reference's, manager's or guardian's) and / or an
 * ID / account number, chosen in Form settings (suggested automatically). Matching:
 *   clear  — same email (normalised) or same ID → refused
 *   likely — near-identical email (a typo away) or ID, ideally with a similar name → the respondent
 *            confirms they are a different person; the response is flagged "possible duplicate"
 *   none   — accepted
 * Messages never reveal the other person's details (only a masked hint and the date).
 */
import type { FormField } from './build'
import { allFields } from './build'
import type { FormSchemaV1 } from './schema'

export interface IdentitySettings {
  /** Key of the email field that belongs to the person filling in (null = off). */
  email: string | null
  /** Key of an ID / account / membership number field (null = off). */
  id: string | null
  /** Ask for a one-time code sent to that email before submitting. */
  verify: boolean
}

// Emails that are about someone else, by their label or key.
const OTHER_PERSON = /\b(reference|referee|manager|supervisor|guardian|parent|emergency|contact person|next of kin|friend|partner|spouse|colleague|employer|company|business|billing|invoice|sponsor|assistant|secretary|recipient|cc)\b/i
const ID_WORDS = /\b(id|identity|identification|national|passport|membership|member|account|employee|student|staff|customer|patient|policy|licen[cs]e|registration|reference number|number)\b/i

const textOf = (field: FormField) => `${field.label ?? ''} ${field.key.replace(/_/g, ' ')}`

/** The email field that most likely belongs to the respondent (first email not about someone else). */
export function suggestEmailField(fields: FormField[]): string | null {
  const emails = fields.filter(f => f.type === 'email')
  return emails.find(f => !OTHER_PERSON.test(textOf(f)))?.key ?? null
}

/** A field that looks like an ID / account number (short text or number, labelled as one). */
export function suggestIdField(fields: FormField[]): string | null {
  return (
    fields.find(f => (f.type === 'short_text' || f.type === 'number') && ID_WORDS.test(textOf(f)) && !OTHER_PERSON.test(textOf(f)) && /\b(id|number|no)\b/i.test(textOf(f)))
      ?.key ?? null
  )
}

/** The form's identity settings: stored ones, or suggestions when the form never chose. */
export function identityOf(schema: FormSchemaV1): IdentitySettings {
  const stored = schema.settings?.identity
  const fields = allFields(schema)
  const exists = (key: string | null | undefined) => (key && fields.some(f => f.key === key) ? key : null)
  if (stored) return { email: exists(stored.email), id: exists(stored.id), verify: !!stored.verify && !!exists(stored.email) }
  return { email: suggestEmailField(fields), id: exists(schema.settings?.unique_field) ?? suggestIdField(fields), verify: false }
}

// ── Normalising ──────────────────────────────────────────────────────────────────────

const GMAIL = new Set(['gmail.com', 'googlemail.com'])
/** Case, spaces, plus-tags; Gmail also ignores dots in the name part. */
export function normaliseEmail(value: unknown): string | null {
  if (typeof value !== 'string' || !value.includes('@')) return null
  const [rawLocal, rawDomain] = value.trim().toLowerCase().split('@') as [string, string]
  const domain = rawDomain === 'googlemail.com' ? 'gmail.com' : rawDomain
  let local = rawLocal.split('+')[0]!
  if (GMAIL.has(domain)) local = local.replace(/\./g, '')
  return local && domain ? `${local}@${domain}` : null
}
/** Letters and digits only, upper case (AB-123 456 → AB123456). */
export function normaliseId(value: unknown): string | null {
  const text = typeof value === 'number' ? String(value) : typeof value === 'string' ? value : ''
  const clean = text.toUpperCase().replace(/[^A-Z0-9]/g, '')
  return clean.length >= 3 ? clean : null
}
/** Names: accents, case, punctuation and word order don't matter. */
export function normaliseName(value: unknown): string {
  const text = typeof value === 'string' ? value : value && typeof value === 'object' ? Object.values(value).filter(v => typeof v === 'string').join(' ') : ''
  return text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .sort()
    .join(' ')
}

// ── Similarity ───────────────────────────────────────────────────────────────────────

/** Edits needed to turn one text into the other (insert, delete, replace, swap neighbours). */
export function editDistance(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array<number>(b.length).fill(0)])
  for (let j = 1; j <= b.length; j++) d[0]![j] = j
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      d[i]![j] = Math.min(d[i - 1]![j]! + 1, d[i]![j - 1]! + 1, d[i - 1]![j - 1]! + cost)
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i]![j] = Math.min(d[i]![j]!, d[i - 2]![j - 2]! + 1)
    }
  return d[a.length]![b.length]!
}
/** 0–1: how alike two names are (1 = same once normalised). */
export function nameSimilarity(a: unknown, b: unknown): number {
  const x = normaliseName(a)
  const y = normaliseName(b)
  if (!x || !y) return 0
  if (x === y) return 1
  return 1 - editDistance(x, y) / Math.max(x.length, y.length)
}
/** Two emails a typo apart: same or near domain and a near-identical name part. */
function emailsNear(a: string, b: string): boolean {
  const [la, da] = a.split('@') as [string, string]
  const [lb, db] = b.split('@') as [string, string]
  const domainClose = da === db || editDistance(da, db) <= 1
  const allowed = Math.max(la.length, lb.length) >= 8 ? 2 : 1
  return domainClose && editDistance(la, lb) <= allowed
}

// ── Matching ─────────────────────────────────────────────────────────────────────────

export interface IdentityRecord {
  id: string
  submitted_at: string
  data: Record<string, unknown>
}
export type MatchReason = 'email' | 'id' | 'email_similar' | 'id_similar'
export interface IdentityMatch {
  level: 'none' | 'likely' | 'clear'
  reason?: MatchReason
  record?: IdentityRecord
}

/** Name-like answers of a response (full name, or first + last), for the "likely" check. */
function nameOf(fields: FormField[], data: Record<string, unknown>): string {
  const full = fields.find(f => f.type === 'full_name')
  if (full) return normaliseName(data[full.key])
  const parts = fields.filter(f => f.type === 'short_text' && /\b(first|last|given|family|sur)\s*name\b|\bname\b/i.test(textOf(f)) && !OTHER_PERSON.test(textOf(f)))
  return normaliseName(parts.map(f => data[f.key]).join(' '))
}

/** Compares a new response with earlier ones of the same form. */
export function matchIdentity(schema: FormSchemaV1, answers: Record<string, unknown>, earlier: IdentityRecord[], identity = identityOf(schema)): IdentityMatch {
  const fields = allFields(schema)
  const email = identity.email ? normaliseEmail(answers[identity.email]) : null
  const id = identity.id ? normaliseId(answers[identity.id]) : null
  if (!email && !id) return { level: 'none' }

  for (const record of earlier) {
    if (email && identity.email && normaliseEmail(record.data[identity.email]) === email) return { level: 'clear', reason: 'email', record }
    if (id && identity.id && normaliseId(record.data[identity.id]) === id) return { level: 'clear', reason: 'id', record }
  }
  const name = nameOf(fields, answers)
  for (const record of earlier) {
    const theirEmail = identity.email ? normaliseEmail(record.data[identity.email]) : null
    const theirId = identity.id ? normaliseId(record.data[identity.id]) : null
    const similarName = !name || nameSimilarity(name, nameOf(fields, record.data)) >= 0.75
    if (email && theirEmail && emailsNear(email, theirEmail) && similarName) return { level: 'likely', reason: 'email_similar', record }
    if (id && theirId && editDistance(id, theirId) <= 1 && similarName) return { level: 'likely', reason: 'id_similar', record }
  }
  return { level: 'none' }
}

/** "sa•••@yahoo.com" — enough to recognise your own email, never enough to learn someone else's. */
export function maskEmail(value: unknown): string {
  const email = typeof value === 'string' ? value.trim() : ''
  const [local, domain] = email.split('@')
  if (!local || !domain) return ''
  return `${local.slice(0, 2)}•••@${domain}`
}

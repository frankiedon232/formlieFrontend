/**
 * Submitted responses for the mock (F10 stores them, F11 lists and reviews them). One response per
 * fill-in session: the session's Formalie-Key maps to the response it created, so a repeat
 * (double click, retry after a dropped connection, back button) returns the same response.
 * Persisted across dev reloads.
 */
import { createHash } from 'node:crypto'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'

export interface StoredResponse {
  id: string
  form_id: string
  /** Published version the respondent filled in. */
  form_version: number | null
  submitted_at: string
  language: string
  data: Record<string, unknown>
  /** The fill-in session's submission id (Formalie-Key). */
  submission_id: string
  /** The browser it came from (device cookie), "already submitted from this browser" (F10). */
  device_id?: string
  /** SHA-256 of the answers, the exact same response twice is refused. */
  fingerprint?: string
  /** A similar earlier response (respondent said they're a different person), for the team to review (F11). */
  possible_duplicate?: { of: string; reason: string }
  /** Who sent it, when the form knows (F10 M3): an invitation, or a signed-in member. */
  respondent?: { kind: 'invite' | 'member'; id: string; name: string | null; email: string }
  /** How it came in. */
  channel: 'link' | 'embed' | 'api'
  meta: { ip: string; user_agent: string }
}

interface TenantResponses {
  responses: StoredResponse[]
}

const stores = new Map<string, TenantResponses>(
  Object.entries(loadPersisted<Record<string, TenantResponses>>('responses', {})),
)

export function responsesOf(tenant: MockTenant): TenantResponses {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { responses: [] }
    stores.set(tenant.id, store)
  }
  return store
}

export function saveResponses() {
  savePersisted('responses', () => Object.fromEntries(stores))
}

/** The response a fill-in session already created, if any. */
export const responseForSubmission = (tenant: MockTenant, formId: string, submissionId: string) =>
  responsesOf(tenant).responses.find(item => item.form_id === formId && item.submission_id === submissionId)

/** The answers in a stable order, hashed: the same response twice has the same fingerprint (web form and API alike). */
export function fingerprintOf(answers: Record<string, unknown>): string {
  const stable = Object.keys(answers)
    .sort()
    .map(key => [key, typeof answers[key] === 'string' ? (answers[key] as string).trim().toLowerCase() : answers[key]])
  return createHash('sha256').update(JSON.stringify(stable)).digest('hex')
}

/**
 * Submitted responses for the mock (F10 stores them, F11 lists and reviews them). One response per
 * fill-in session: the session's Idempotency-Key maps to the response it created, so a repeat
 * (double click, retry after a dropped connection, back button) returns the same response.
 * Persisted across dev reloads.
 */
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
  /** The fill-in session's submission id (Idempotency-Key). */
  submission_id: string
  /** How it came in. */
  channel: 'link' | 'embed'
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

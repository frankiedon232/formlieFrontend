/**
 * Save and resume (F10 M2): a respondent's unfinished answers, kept on the server under a long
 * random token (never an id). The token travels only in the respondent's resume link and the
 * open tab; submitting closes the draft, so a link can't create a second response.
 * Persisted across dev reloads; drafts expire after 30 days.
 */
import { randomBytes } from 'node:crypto'
import { loadPersisted, savePersisted } from '../core/persist'

export interface ResumeDraft {
  tenantId: string
  formId: string
  data: Record<string, unknown>
  /** Page index the respondent was on. */
  page: number
  email: string | null
  created_at: string
  updated_at: string
  expires_at: string
  closed: boolean
}

export const RESUME_TTL_DAYS = 30
const drafts = new Map<string, ResumeDraft>(Object.entries(loadPersisted<Record<string, ResumeDraft>>('resume', {})))

export function saveDrafts() {
  savePersisted('resume', () => Object.fromEntries(drafts))
}

export const newResumeToken = () => randomBytes(32).toString('base64url')

export function draftOf(token: string, formId: string): ResumeDraft | null {
  const draft = drafts.get(token)
  if (!draft || draft.formId !== formId) return null
  if (Date.parse(draft.expires_at) < Date.now()) {
    drafts.delete(token)
    saveDrafts()
    return null
  }
  return draft
}

export function putDraft(token: string, draft: ResumeDraft) {
  drafts.set(token, draft)
  saveDrafts()
}

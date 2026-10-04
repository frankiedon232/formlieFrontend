/**
 * The team's work on responses (F11): status, tags, notes, edited answers with their history, and
 * deletions. Kept by response id for sample and real responses alike, persisted across dev reloads.
 * Every change bumps its form's `reviewVersion`, which refreshes that form's cached responses only.
 */
import type { ResponseChange, ResponseNote, ResponseStatus } from '#shared/types/responses'
import { loadPersisted, savePersisted } from '../core/persist'

export interface ResponseReview {
  status?: ResponseStatus
  tags?: string[]
  notes?: ResponseNote[]
  history?: ResponseChange[]
  /** Answers changed by the team (key → new value); the original stays in the history. */
  data?: Record<string, unknown>
  deleted_at?: string
  /** "Not a duplicate": the possible-duplicate flag was looked at and cleared (F11 M2). */
  duplicate_cleared?: boolean
}

const reviews = new Map<string, ResponseReview>(Object.entries(loadPersisted<Record<string, ResponseReview>>('response-reviews', {})))
const versions = new Map<string, number>()

/** Changes whenever a response of this form is reviewed, edited, deleted or added. */
export const reviewVersion = (formId: string) => versions.get(formId) ?? 0
export const reviewOf = (id: string): ResponseReview | undefined => reviews.get(id)

/** Change a response's review; returns the stored review. */
export function updateReview(formId: string, id: string, change: (review: ResponseReview) => void): ResponseReview {
  const review = reviews.get(id) ?? {}
  change(review)
  reviews.set(id, review)
  touchResponses(formId)
  savePersisted('response-reviews', () => Object.fromEntries(reviews))
  return review
}

/** A form's responses changed (the cached index must be rebuilt). */
export function touchResponses(formId: string) {
  versions.set(formId, (versions.get(formId) ?? 0) + 1)
}

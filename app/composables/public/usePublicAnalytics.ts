import { isVisitId, newVisitId, type FillChannel } from '#shared/utils/analytics/events'
import { createFillRecorder, type FillRecorder } from '#shared/utils/analytics/recorder'

/**
 * Fill-in analytics for the public form page (link and embed; owner decision 2026-10-15, rules in
 * shared/utils/analytics). One visit id per visit, random and kept in this tab's sessionStorage (no
 * personal data); view / start / answer / page events go to POST /public/forms/{key}/events, each
 * once per visit, in the background, fire and forget: a failure never blocks the form or shows an error.
 * `?preview` (the portal's embed preview) records nothing. The submit sends the same id as `session`.
 */
export function usePublicAnalytics(key: string, channel: FillChannel) {
  const api = useApi()
  const route = useRoute()
  const storageKey = `formalie:visit:${key}`
  const enabled = import.meta.client && route.query.preview === undefined
  let memoryId: string | undefined
  let recorder: FillRecorder | null = null

  function visitId(): string {
    try {
      const existing = sessionStorage.getItem(storageKey)
      if (isVisitId(existing)) return existing
      const fresh = newVisitId()
      sessionStorage.setItem(storageKey, fresh)
      return fresh
    } catch {
      return (memoryId ??= newVisitId())
    }
  }

  function current(): FillRecorder | null {
    if (!enabled) return null
    const id = visitId()
    if (recorder?.session !== id) {
      recorder = createFillRecorder(id, channel, event => {
        api.post(`/public/forms/${encodeURIComponent(key)}/events`, event, { background: true }).catch(() => {
          // Analytics never gets in the way of filling in.
        })
      })
    }
    return recorder
  }

  /** The visit was sent: the next fill-in is a new visit. */
  function finished() {
    try {
      sessionStorage.removeItem(storageKey)
    } catch {
      // memory fallback below
    }
    memoryId = undefined
    recorder = null
  }

  return {
    /** The visit id for the submit body (`session`). */
    session: () => (import.meta.client ? visitId() : undefined),
    finished,
    view: () => current()?.view(),
    start: () => current()?.start(),
    page: (index: number) => current()?.page(index),
    answer: (field: string) => current()?.answer(field),
  }
}

/**
 * Help in context (F25 M3), one for the whole app: the help panel (the article for the page someone is on, or
 * a given article), the guided tour that is running, and "Show me" spotlights. Module-level state, so the "?"
 * in any header, an empty state or a help link opens the same panel.
 */
import type { HelpTour } from '#shared/types/help'

const open = ref(false)
const articleId = ref<string | null>(null)
const tour = ref<HelpTour | null>(null)
const step = ref(0)
/** A single control to point at ("Show me"), shown like a one-step tour. */
const spotlight = ref<string | null>(null)

export function useHelpPanel() {
  /** The help for the page you are on. */
  function openForPage() {
    articleId.value = null
    open.value = true
  }
  /** One article (from an empty state or a link). */
  function openArticle(id: string) {
    articleId.value = id
    open.value = true
  }
  function startTour(value: HelpTour) {
    open.value = false
    spotlight.value = null
    step.value = 0
    tour.value = value
  }
  const endTour = () => ((tour.value = null), (step.value = 0))
  return { open, articleId, tour, step, spotlight, openForPage, openArticle, startTour, endTour }
}

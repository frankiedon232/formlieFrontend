/**
 * Tips on new pages (F25, owner 2026-10-10): the first time someone opens a page that has a guided tour, a small
 * card offers it (Take the tour · Not now · Turn off tips). Each tour is offered once per person, remembered on the
 * server (`/me/tours`), so another browser or device doesn't offer it again; My profile switches tips off and
 * shows them all again. The tours themselves come once per language (`/help/tours`).
 */
import type { HelpTour, MyTours } from '#shared/types/help'
import { routeMatches } from '#shared/utils/help/routes'

const mine = ref<MyTours | null>(null)
const tours = ref<HelpTour[]>([])
const toursLang = ref<string | null>(null)
/** The tour being offered on this page (the card shows while set). */
const offer = ref<HelpTour | null>(null)

export function useTours() {
  const api = useApi()
  const { locale } = useI18n()
  const help = useHelpPanel()

  async function load() {
    try {
      if (!mine.value) mine.value = (await api.get<MyTours>('/me/tours', undefined, { background: true })).data
      if (toursLang.value !== locale.value) {
        tours.value = (await api.get<HelpTour[]>('/help/tours', { lang: locale.value }, { background: true })).data
        toursLang.value = locale.value
      }
    } catch {
      // Tips are a convenience: without them the page works as always
    }
  }

  async function save(body: { seen?: string; enabled?: boolean; reset?: true }) {
    try {
      mine.value = (await api.patch<MyTours>('/me/tours', body, { background: true })).data
    } catch {
      // Not saved: offered again next time, nothing worse
    }
  }

  /** Offer the page's tour if this person hasn't been offered it yet. */
  async function check(path: string) {
    offer.value = null
    await load()
    if (!mine.value?.enabled || help.tour.value) return
    const tour = tours.value.find(item => routeMatches(item.route, path))
    if (tour && !mine.value.seen.includes(tour.id)) offer.value = tour
  }

  function take() {
    const tour = offer.value
    if (!tour) return
    offer.value = null
    void save({ seen: tour.id })
    help.startTour(tour)
  }
  function later() {
    const tour = offer.value
    offer.value = null
    if (tour) void save({ seen: tour.id })
  }
  function turnOff() {
    offer.value = null
    void save({ enabled: false })
  }
  const setEnabled = (enabled: boolean) => save({ enabled })
  const showAgain = () => save({ reset: true })

  return { mine, offer, load, check, take, later, turnOff, setEnabled, showAgain }
}

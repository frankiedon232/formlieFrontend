/**
 * Announcements from the Formalie team (B16, `GET /platform/announcements`): banners, maintenance and
 * news for this workspace, in the person's language. Dismissed ones are remembered per person in this
 * browser (localStorage; ids only, nothing secret). Checked every 10 minutes in the background.
 */
import type { PlatformAnnouncement } from '#shared/types/support'

const list = ref<PlatformAnnouncement[]>([])
const dismissed = ref<string[]>([])
let started = false

const storageKey = (userId: string) => `formalie:announcements:dismissed:${userId}`

function readDismissed(userId: string | undefined): string[] {
  if (!userId) return []
  try {
    const value = JSON.parse(localStorage.getItem(storageKey(userId)) ?? '[]')
    return Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string').slice(-200) : []
  } catch {
    return []
  }
}

export function useAnnouncements() {
  const api = useApi()
  const session = useSession()
  const { locale } = useI18n()

  async function load() {
    if (!session.isAuthenticated.value) return
    try {
      list.value = (await api.get<PlatformAnnouncement[]>('/platform/announcements', { lang: locale.value }, { background: true })).data ?? []
    } catch {
      // Announcements are extra: keep what we had
    }
  }

  function start() {
    if (started || import.meta.server) return
    started = true
    dismissed.value = readDismissed(session.user.value?.id)
    void load()
    useIntervalFn(() => void load(), 10 * 60_000)
    watch(() => session.user.value?.id, id => {
      dismissed.value = readDismissed(id)
      void load()
    })
    watch(locale, () => void load())
  }

  function dismiss(id: string) {
    dismissed.value = [...dismissed.value.filter(item => item !== id), id]
    const userId = session.user.value?.id
    if (!userId) return
    try {
      localStorage.setItem(storageKey(userId), JSON.stringify(dismissed.value.slice(-200)))
    } catch {
      // Private window or storage blocked: hidden until the next reload
    }
  }

  const now = ref(Date.now())
  useIntervalFn(() => (now.value = Date.now()), 60_000)
  const visible = computed(() => visibleAnnouncements(list.value, dismissed.value, now.value))

  return { visible, load, start, dismiss }
}

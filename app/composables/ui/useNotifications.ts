/**
 * The signed-in person's notifications (F14 M4): one shared feed for the bell and its panel, checked
 * every minute in the background and whenever the panel opens. Texts come from `kind` + `params`.
 */
import type { AppNotification, NotificationEvent, NotificationFeed } from '#shared/types/notifications'

const feed = ref<NotificationFeed | null>(null)
const failed = ref(false)
let started = false

export const NOTIFICATION_ICONS: Record<NotificationEvent, string> = {
  response_new: 'i-lucide-inbox',
  response_duplicate: 'i-lucide-copy',
  form_limit: 'i-lucide-gauge',
  form_closing: 'i-lucide-calendar-clock',
  export_ready: 'i-lucide-file-down',
  webhook_failing: 'i-lucide-webhook',
  security_alert: 'i-lucide-shield-alert',
}

export function useNotifications() {
  const api = useApi()
  const { t } = useI18n()
  const { dateTime } = useFormat()

  async function load(background = true) {
    try {
      feed.value = (await api.get<NotificationFeed>('/notifications', undefined, { background })).data
      failed.value = false
    } catch {
      failed.value = true
    }
  }
  /** Starts the one-minute check (once for the whole app). */
  function start() {
    if (started || import.meta.server) return
    started = true
    void load()
    useIntervalFn(() => void load(), 60_000)
  }
  async function markRead(ids: string[] | 'all') {
    if (!feed.value) return
    // Read at once in the list; the server confirms
    const now = new Date().toISOString()
    feed.value = { items: feed.value.items.map(item => (ids === 'all' || ids.includes(item.id) ? { ...item, read_at: item.read_at ?? now } : item)), unread: ids === 'all' ? 0 : Math.max(0, feed.value.unread - feed.value.items.filter(item => ids.includes(item.id) && !item.read_at).length) }
    try {
      feed.value = (await api.post<NotificationFeed>('/notifications/read', ids === 'all' ? { all: true } : { ids }, { background: true })).data
    } catch {
      void load()
    }
  }
  async function clearRead() {
    feed.value = (await api.del<NotificationFeed>('/notifications/read')).data
  }

  /** The translated title and line of a notification. */
  function textOf(item: AppNotification) {
    const params = { ...item.params, date: item.params.date ? dateTime(String(item.params.date)) : '', reason: item.params.reason ? t(`notifications.reason.${item.params.reason}`) : '' }
    return { title: t(`notifications.event.${item.event}.title`, params), message: t(`notifications.event.${item.event}.message`, params) }
  }

  return { feed, failed, load, start, markRead, clearRead, textOf }
}

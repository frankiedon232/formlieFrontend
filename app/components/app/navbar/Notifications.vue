<!--
  Notifications panel (F14 M4): the person's feed, newest first, in Today and Earlier. Unread ones
  carry a dot; opening one marks it read and goes where it points. Mark all read, clear the read
  ones, and (admins) a link to Settings → Notifications to choose who hears about what.
-->
<script setup lang="ts">
import type { AppNotification } from '#shared/types/notifications'

const { t } = useI18n()
const { notificationsOpen } = useAppUi()
const { endSide } = useAppLocale()
const { relative, dateTime } = useFormat()
const notifications = useNotifications()
const { busy, run } = useBusy()
const feed = notifications.feed

watch(notificationsOpen, open => open && void notifications.load(false))
const { can } = useCan()
const isAdmin = computed(() => can('settings.manage'))

const groups = computed(() => {
  const items = feed.value?.items ?? []
  const today = new Date().toDateString()
  return [
    { key: 'today', items: items.filter(item => new Date(item.created_at).toDateString() === today) },
    { key: 'earlier', items: items.filter(item => new Date(item.created_at).toDateString() !== today) },
  ].filter(group => group.items.length)
})
const TONES: Partial<Record<AppNotification['event'], string>> = { security_alert: 'text-error', webhook_failing: 'text-warning', response_duplicate: 'text-warning', form_limit: 'text-warning' }

async function open(item: AppNotification) {
  if (!item.read_at) void notifications.markRead([item.id])
  if (item.link) {
    notificationsOpen.value = false
    await navigateTo(item.link)
  }
}
const hasRead = computed(() => (feed.value?.items ?? []).some(item => item.read_at))
</script>

<template>
  <USlideover v-model:open="notificationsOpen" :title="t('navbar.notifications')" :side="endSide" :ui="{ body: 'p-0 sm:p-0' }">
    <template #actions>
      <UButton v-if="feed?.unread" :label="t('notifications.markAll')" icon="i-lucide-check-check" color="neutral" variant="ghost" size="xs" @click="notifications.markRead('all')" />
    </template>
    <template #body>
      <div v-if="!feed && !notifications.failed.value" class="flex flex-col gap-3 p-4">
        <div v-for="n in 5" :key="n" class="flex gap-3"><USkeleton class="size-8 rounded-lg" /><div class="flex flex-1 flex-col gap-1.5"><USkeleton class="h-3.5 w-2/3" /><USkeleton class="h-3 w-full" /></div></div>
      </div>
      <AppEmpty v-else-if="!feed" icon="i-lucide-cloud-off" :title="t('notifications.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => notifications.load(false) }]" class="h-full" />
      <AppEmpty v-else-if="!feed.items.length" icon="i-lucide-bell" :title="t('navbar.noNotifications')" :description="t('notifications.emptyDesc')" variant="naked" class="h-full" :actions="isAdmin ? [{ label: t('notifications.settings'), icon: 'i-lucide-settings-2', color: 'neutral', variant: 'outline', to: '/settings/notifications', onClick: () => (notificationsOpen = false) }] : []" />
      <div v-else class="flex flex-col">
        <section v-for="group in groups" :key="group.key">
          <h3 class="sticky top-0 z-10 bg-default/95 px-4 pt-3 pb-1.5 text-[11px] font-medium tracking-wide text-muted uppercase backdrop-blur">{{ t(`notifications.${group.key}`) }}</h3>
          <ul class="flex flex-col">
            <li v-for="item in group.items" :key="item.id">
              <button type="button" class="flex w-full items-start gap-3 px-4 py-2.5 text-start transition-colors hover:bg-elevated/60 focus-visible:bg-elevated focus-visible:outline-none" @click="open(item)">
                <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon :name="NOTIFICATION_ICONS[item.event]" class="size-4" :class="TONES[item.event] ?? 'text-highlighted'" /></span>
                <span class="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span class="text-sm" :class="item.read_at ? 'text-default' : 'font-medium text-highlighted'">{{ notifications.textOf(item).title }}</span>
                  <span class="line-clamp-2 text-xs text-muted">{{ notifications.textOf(item).message }}</span>
                  <UTooltip :text="dateTime(item.created_at)"><span class="w-fit text-[11px] text-dimmed">{{ relative(item.created_at) }}</span></UTooltip>
                </span>
                <span v-if="!item.read_at" class="mt-1.5 size-2 shrink-0 rounded-full bg-inverted" :aria-label="t('notifications.unread')" />
              </button>
            </li>
          </ul>
        </section>
      </div>
    </template>
    <template v-if="feed?.items.length" #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <UButton :label="t('notifications.clearRead')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="sm" :disabled="!hasRead" :loading="busy" @click="run(() => notifications.clearRead())" />
        <UButton v-if="isAdmin" :label="t('notifications.settings')" icon="i-lucide-settings-2" color="neutral" variant="outline" size="sm" to="/settings/notifications" @click="notificationsOpen = false" />
      </div>
    </template>
  </USlideover>
</template>

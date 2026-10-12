<!--
  Strips across the top of the portal shell (B16): Formalie support's live session (everyone in the
  workspace sees who and until when; the support person also gets End session), then the Formalie
  team's announcements by tone, with a dismiss button when they may be dismissed. Nothing shows when
  there is nothing to say, so the shell keeps its full height.
-->
<script setup lang="ts">
import type { PlatformAnnouncement } from '#shared/types/support'

const { t } = useI18n()
const support = useSupportSession()
const announcements = useAnnouncements()
const auth = useAuth()
const { moment } = useFormat()
const { busy, run } = useBusy()
support.start()
announcements.start()

const supportText = computed(() => {
  const banner = support.banner.value
  if (!banner) return ''
  const values = { name: banner.staff_name, time: moment(banner.ends_at) }
  return banner.mode === 'write' ? t('support.banner.write', values) : t('support.banner.read', values)
})

async function endSession() {
  const ended = await run(async () => {
    await auth.endSupport()
    return true
  })
  if (ended) await navigateTo({ path: '/support', query: { ended: 'signed_out' } }, { replace: true })
}

const TONES: Record<PlatformAnnouncement['tone'], { color: 'neutral' | 'warning' | 'error'; icon: string }> = {
  info: { color: 'neutral', icon: 'i-lucide-megaphone' },
  warning: { color: 'warning', icon: 'i-lucide-triangle-alert' },
  critical: { color: 'error', icon: 'i-lucide-octagon-alert' },
}
const KIND_ICONS: Partial<Record<PlatformAnnouncement['kind'], string>> = { maintenance: 'i-lucide-wrench', news: 'i-lucide-sparkles' }
const linkOf = (item: PlatformAnnouncement) => safeAnnouncementLink(item.link_url)
const alertUi = { root: 'rounded-none px-3 py-2 sm:px-4', title: 'text-sm', description: 'text-xs', actions: 'items-center' }
</script>

<template>
  <div v-if="support.active.value || announcements.visible.value.length" class="flex shrink-0 flex-col" role="region" :aria-label="t('support.banner.region')">
    <UAlert
      v-if="support.active.value"
      color="neutral"
      variant="solid"
      icon="i-lucide-life-buoy"
      orientation="horizontal"
      :title="supportText"
      :description="support.isSupport.value && support.left.value != null ? t('support.banner.left', { time: countdownText(support.left.value) }) : undefined"
      :actions="support.isSupport.value ? [{ label: t('support.banner.end'), icon: 'i-lucide-log-out', color: 'neutral', variant: 'outline', size: 'xs', loading: busy, onClick: endSession }] : undefined"
      :ui="alertUi"
      aria-live="polite"
    />
    <UAlert
      v-for="item in announcements.visible.value"
      :key="item.id"
      :color="TONES[item.tone].color"
      variant="subtle"
      :icon="KIND_ICONS[item.kind] ?? TONES[item.tone].icon"
      orientation="horizontal"
      :title="item.title"
      :description="item.body ?? undefined"
      :close="item.dismissible ? { size: 'xs', ui: { base: 'shrink-0' } } : false"
      :actions="linkOf(item) ? [{ label: t('support.announcements.more'), icon: 'i-lucide-arrow-up-right', color: 'neutral', variant: 'outline', size: 'xs', to: linkOf(item)!, target: '_blank', class: 'rtl:[&_svg]:-scale-x-100' }] : undefined"
      :ui="{ ...alertUi, root: `${alertUi.root} border-b border-default` }"
      @update:open="open => !open && announcements.dismiss(item.id)"
    />
  </div>
</template>

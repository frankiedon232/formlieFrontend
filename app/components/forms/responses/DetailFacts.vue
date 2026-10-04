<!--
  Response facts as tiles (F11 panel): when it was sent, time taken, how it came in, language,
  device, form version. Icon in a soft square, the label small, the value clear.
-->
<script setup lang="ts">
import type { ResponseDetail } from '#shared/types/responses'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ response: ResponseDetail }>()
const { t } = useI18n()
const { dateTime, relative } = useFormat()
const { duration } = useResponseFormat()

const tiles = computed(() => {
  const r = props.response
  const locale = APP_LOCALES.find(item => item.code === r.language)
  const device = r.meta.device.toLowerCase()
  return [
    { icon: 'i-lucide-calendar-clock', label: t('responses.list.submitted'), value: relative(r.submitted_at), hint: dateTime(r.submitted_at) },
    { icon: 'i-lucide-timer', label: t('responses.detail.timeTaken'), value: r.duration_seconds != null ? duration(r.duration_seconds) : '-', hint: null },
    { icon: r.channel === 'embed' ? 'i-lucide-code-xml' : r.channel === 'api' ? 'i-lucide-plug' : 'i-lucide-link', label: t('responses.detail.cameIn'), value: t(`responses.channel.${r.channel}`), hint: null },
    { icon: locale?.flag ?? 'i-lucide-languages', label: t('responses.detail.language'), value: locale?.name ?? r.language, hint: null },
    { icon: device === 'phone' ? 'i-lucide-smartphone' : device === 'tablet' ? 'i-lucide-tablet' : 'i-lucide-monitor', label: t('responses.detail.device'), value: t(`responses.device.${device}`), hint: null },
    { icon: 'i-lucide-history', label: t('responses.detail.version'), value: r.form_version ? `v${r.form_version}` : '-', hint: null },
  ]
})
</script>

<template>
  <ul class="grid grid-cols-2 gap-2 sm:grid-cols-3">
    <li v-for="tile in tiles" :key="tile.label" class="flex items-center gap-2.5 rounded-lg border border-default p-2.5">
      <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated text-muted">
        <UIcon :name="tile.icon" class="size-4" />
      </span>
      <div class="flex min-w-0 flex-col">
        <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
        <UTooltip v-if="tile.hint" :text="tile.hint"><span class="truncate text-sm font-medium text-highlighted">{{ tile.value }}</span></UTooltip>
        <span v-else class="truncate text-sm font-medium text-highlighted">{{ tile.value }}</span>
      </div>
    </li>
  </ul>
</template>

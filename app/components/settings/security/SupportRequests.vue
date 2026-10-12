<!--
  Formalie's open requests for support access (B16): who asks, why, how much and how long, and when it
  runs out. Approve turns access on as asked; Decline says no. The row being answered shows a spinner.
-->
<script setup lang="ts">
import type { SupportRequest } from '#shared/types/support'

defineProps<{ requests: SupportRequest[]; busy: string | null; canManage: boolean }>()
const emit = defineEmits<{ approve: [request: SupportRequest]; decline: [request: SupportRequest] }>()
const { t } = useI18n()
const { relative, dateTime } = useFormat()
const hoursLabel = (hours: number) => (hours >= 24 ? t('settings.security.days', { n: hours / 24 }, hours / 24) : t('settings.security.hours', { n: hours }, hours))
</script>

<template>
  <div class="flex flex-col gap-2">
    <h3 class="text-xs font-medium text-highlighted">{{ t('support.access.requests', { n: requests.length }, requests.length) }}</h3>
    <ul class="flex flex-col gap-2">
      <li v-for="item in requests" :key="item.id" class="flex flex-col gap-3 rounded-lg border border-warning/40 bg-warning/5 p-3" :class="busy === item.id ? 'opacity-60' : ''">
        <div class="flex min-w-0 items-start gap-3">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default bg-default"><UIcon name="i-lucide-life-buoy" class="size-4 text-highlighted" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <p class="text-sm font-medium text-highlighted">{{ t('support.access.asks', { name: item.staff_name }) }}</p>
            <p class="text-sm break-words whitespace-pre-line text-default">{{ item.reason }}</p>
            <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
              <UBadge :label="t(`support.access.mode.${item.mode}`)" color="neutral" variant="outline" size="sm" :icon="item.mode === 'write' ? 'i-lucide-pencil' : 'i-lucide-eye'" />
              <UBadge :label="hoursLabel(item.hours)" color="neutral" variant="outline" size="sm" icon="i-lucide-timer" />
              <UTooltip :text="dateTime(item.created_at)"><span class="text-xs text-muted">{{ relative(item.created_at) }}</span></UTooltip>
              <span class="text-xs text-muted">· {{ t('support.access.requestEnds', { when: relative(item.expires_at) }) }}</span>
            </div>
          </div>
        </div>
        <div v-if="canManage" class="flex flex-wrap gap-2 sm:justify-end">
          <UButton :label="t('support.access.decline')" icon="i-lucide-x" color="neutral" variant="outline" size="sm" :disabled="!!busy" @click="emit('decline', item)" />
          <UButton :label="t('support.access.approve')" icon="i-lucide-check" color="neutral" size="sm" :loading="busy === item.id" :disabled="!!busy && busy !== item.id" @click="emit('approve', item)" />
        </div>
      </li>
    </ul>
  </div>
</template>

<!--
  Settings → Security (F14 M3): sign-in activity of the last 14 days in the KPI card style. On the left
  the sign-ins with their daily bars and small stats (failed, blocked, locked codes); on the right the
  latest attempts, each with who, what and where. Opens the audit trail for the rest.
-->
<script setup lang="ts">
import type { SecurityActivity } from '#shared/types/settings'

const props = defineProps<{ activity: SecurityActivity | null; failed?: boolean }>()
const emit = defineEmits<{ retry: [] }>()
const { t } = useI18n()
const { number, relative, dateTime } = useFormat()
const format = useAuditFormat()

const bars = computed(() => (props.activity?.days ?? []).map(day => ({ date: day.date, count: day.succeeded })))
const stats = computed(() => {
  const totals = props.activity?.totals
  if (!totals) return []
  return [
    { key: 'failed', value: totals.failed, dot: 'bg-amber-500' },
    { key: 'blocked', value: totals.blocked, dot: 'bg-red-500' },
    { key: 'locked', value: totals.locked, dot: 'bg-violet-500' },
  ]
})
const OUTCOME_ICONS = { success: 'i-lucide-circle-check', failure: 'i-lucide-circle-alert', blocked: 'i-lucide-shield-ban' } as const
const OUTCOME_TONES = { success: 'text-muted', failure: 'text-warning', blocked: 'text-error' } as const
</script>

<template>
  <AppEmpty v-if="failed && !activity" size="sm" icon="i-lucide-cloud-off" :title="t('settings.security.activityFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => emit('retry') }]" />
  <div v-else-if="!activity" class="grid gap-4 lg:grid-cols-2"><USkeleton class="h-44 rounded-xl" /><USkeleton class="h-44 rounded-xl" /></div>
  <div v-else class="grid gap-4 lg:grid-cols-2">
    <div class="flex flex-col gap-4 rounded-xl border border-default p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="flex min-w-0 flex-col">
          <span class="text-xs text-muted">{{ t('settings.security.signins') }}</span>
          <span class="text-3xl font-semibold text-highlighted tabular-nums">{{ number(activity.totals.succeeded) }}</span>
        </div>
        <UButton :label="t('settings.security.openAudit')" to="/audit?area=auth" icon="i-lucide-scroll-text" color="neutral" variant="outline" size="xs" />
      </div>
      <ChartsMiniBars :days="bars" :label="t('settings.security.signins')" height="h-16" />
      <div class="flex flex-wrap gap-x-5 gap-y-1.5 border-t border-default pt-3">
        <span v-for="stat in stats" :key="stat.key" class="flex items-center gap-1.5 text-xs text-muted">
          <span class="size-2 rounded-full" :class="stat.dot" />{{ t(`settings.security.stat.${stat.key}`) }}
          <span class="font-medium text-highlighted tabular-nums">{{ number(stat.value) }}</span>
        </span>
      </div>
    </div>

    <div class="flex min-w-0 flex-col rounded-xl border border-default">
      <div class="flex items-center justify-between gap-2 border-b border-default px-4 py-2.5">
        <span class="text-xs font-medium text-highlighted">{{ t('settings.security.recent') }}</span>
        <UButton :label="t('settings.security.onlyProblems')" to="/audit?area=auth&outcome=failure,blocked" color="neutral" variant="link" size="xs" trailing-icon="i-lucide-arrow-right" />
      </div>
      <AppEmpty v-if="!activity.recent.length" size="xs" icon="i-lucide-log-in" :title="t('settings.security.noRecent')" />
      <ul v-else class="flex max-h-56 flex-col divide-y divide-default overflow-y-auto">
        <li v-for="item in activity.recent" :key="item.id" class="flex items-center gap-3 px-4 py-2">
          <UIcon :name="OUTCOME_ICONS[item.outcome]" class="size-4 shrink-0" :class="OUTCOME_TONES[item.outcome]" />
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm text-highlighted">{{ format.actionLabel(item.action) }}</span>
            <span class="truncate text-xs text-muted">{{ item.name }} · <span class="font-mono">{{ item.ip }}</span></span>
          </span>
          <UTooltip :text="dateTime(item.at)"><span class="shrink-0 text-xs whitespace-nowrap text-muted">{{ relative(item.at) }}</span></UTooltip>
        </li>
      </ul>
    </div>
  </div>
</template>

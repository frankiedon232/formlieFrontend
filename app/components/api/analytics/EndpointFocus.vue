<!--
  One endpoint at a time (F13 M4, the design's "Project Overview"): the number of endpoints, ‹ › to
  step through the busiest, ↗ to its panel; its service, name, error share as the design's thick
  bar, three facts and its calls per day as slim bars.
-->
<script setup lang="ts">
import type { ApiAnalytics } from '#shared/types/apiService'

const props = defineProps<{ analytics: ApiAnalytics | null }>()
const { t, d } = useI18n()
const { number, percent } = useFormat()
const index = ref(0)
watch(() => props.analytics, () => (index.value = 0))
const list = computed(() => props.analytics?.endpoints ?? [])
const item = computed(() => list.value[index.value] ?? null)
const move = (by: number) => list.value.length && (index.value = (index.value + by + list.value.length) % list.value.length)
const link = computed(() => (item.value ? { path: '/api-service/endpoints', query: { endpoint: item.value.id } } : undefined))
const errorShare = computed(() => (item.value?.calls ? item.value.errors / item.value.calls : 0))
const points = computed(() => {
  const from = props.analytics ? Date.parse(`${props.analytics.from}T12:00:00Z`) : 0
  return (item.value?.trend ?? []).map((value, i) => ({ label: d(new Date(from + i * 86_400_000), { day: 'numeric', month: 'short' }), value }))
})
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <h2 class="text-sm font-semibold whitespace-nowrap text-highlighted">{{ t('apiService.analytics.endpoint') }}</h2>
        <UBadge :label="number(list.length)" color="neutral" variant="soft" size="sm" class="rounded-md tabular-nums" />
      </div>
      <div class="flex shrink-0 items-center gap-1.5">
        <UFieldGroup size="xs">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="list.length < 2" :aria-label="t('apiService.analytics.previous')" @click="move(-1)" />
          <UButton :label="item ? `/${item.name}` : '…'" color="neutral" variant="outline" class="max-w-28 font-mono sm:max-w-36 lg:max-w-24 2xl:max-w-36" :ui="{ label: 'truncate' }" :to="link" :disabled="!item" />
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="list.length < 2" :aria-label="t('apiService.analytics.next')" @click="move(1)" />
        </UFieldGroup>
        <UButton v-if="item" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="rtl:-scale-x-100" :to="link" :aria-label="t('apiService.actions.open')" />
      </div>
    </div>
    <div v-if="!analytics" class="flex flex-col gap-3"><USkeleton class="h-4 w-24" /><USkeleton class="h-7 w-3/4" /><USkeleton class="h-16 w-full" /></div>
    <AppEmpty v-else-if="!item" size="xs" icon="i-lucide-route" :title="t('apiService.emptyEndpoints')" />
    <template v-else>
      <div class="flex flex-col gap-1.5">
        <span class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-boxes" class="size-3.5" />{{ item.service }}</span>
        <NuxtLink :to="link!" class="truncate font-mono text-xl font-semibold text-highlighted hover:underline sm:text-2xl" dir="ltr">/{{ item.name }}</NuxtLink>
      </div>
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between text-sm">
          <span class="text-muted">{{ t('apiService.analytics.success') }}</span>
          <span class="font-semibold text-highlighted tabular-nums">{{ percent(1 - errorShare, 1) }}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted transition-[width] duration-500" :style="{ width: `${(1 - errorShare) * 100}%` }" /></div>
      </div>
      <dl class="grid grid-cols-3 gap-2">
        <div class="flex min-w-0 flex-col rounded-md bg-elevated/60 px-2.5 py-1.5"><dt class="truncate text-[11px] text-muted">{{ t('apiService.kpi.calls') }}</dt><dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ number(item.calls) }}</dd></div>
        <div class="flex min-w-0 flex-col rounded-md bg-elevated/60 px-2.5 py-1.5"><dt class="truncate text-[11px] text-muted">{{ t('apiService.kpi.errors') }}</dt><dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ number(item.errors) }}</dd></div>
        <div class="flex min-w-0 flex-col rounded-md bg-elevated/60 px-2.5 py-1.5"><dt class="truncate text-[11px] text-muted">p95</dt><dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ item.p95_ms == null ? '–' : t('dataSources.ms', { n: item.p95_ms }) }}</dd></div>
      </dl>
      <div class="mt-auto border-t border-default pt-4">
        <ChartsBars v-if="item.calls" :points="points" height="h-24" :unit="n => t('apiService.callsCount', { n: number(n) }, n)" />
      </div>
    </template>
  </UCard>
</template>

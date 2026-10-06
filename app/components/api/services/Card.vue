<!--
  A service (locked card format, rule 21): a "last call" pill, status and ⋯ on top; the name (red
  flag when more than 1 in 20 calls failed) and its description; endpoints, calls, errors and
  answer time in two columns; a divider, then the methods its endpoints answer; who made it and
  the 30-day calls at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiService } from '#shared/types/apiService'

const props = defineProps<{ item: ApiService; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const errorShare = computed(() => (props.item.calls_30d ? props.item.errors_30d / props.item.calls_30d : 0))
const facts = computed(() => [
  { key: 'endpoints', label: t('apiService.col.endpoints'), value: t('apiService.endpointsCount', { n: number(props.item.endpoints_count) }, props.item.endpoints_count) },
  { key: 'calls', label: t('apiService.col.calls'), value: number(props.item.calls_30d) },
  { key: 'errors', label: t('apiService.col.errors'), value: percent(errorShare.value, 1) },
  { key: 'time', label: t('apiService.kpi.time'), value: props.item.avg_ms == null ? '–' : t('dataSources.ms', { n: props.item.avg_ms }) },
])
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="busy ? 'pointer-events-none opacity-60' : ''" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-arrow-left-right'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ item.last_call_at ? t('apiService.lastCall', { when: relative(item.last_call_at) }) : t('apiService.neverCalled') }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="item.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="errorShare > 0.05" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.manyErrors')" />
        <span class="truncate text-base font-semibold text-highlighted">{{ item.name }}</span>
      </div>
      <p class="truncate text-sm text-muted">{{ item.description || t('apiService.noDescription') }}</p>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto pt-4">
      <div class="flex items-center justify-between gap-2 border-t border-default pt-3">
        <span class="text-xs text-muted">{{ t('apiService.col.methods') }}</span>
        <ApiMethods :methods="item.methods" size="xs" />
      </div>
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="item.created_by.name" size="2xs" />
          <span class="truncate text-xs text-muted">{{ item.created_by.name }}</span>
        </div>
        <ChartsSparkline :values="item.daily.map(day => day.count)" :width="72" :height="20" />
      </div>
    </div>
  </article>
</template>

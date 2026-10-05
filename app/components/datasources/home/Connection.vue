<!--
  One connection at a time on the Data sources overview (the design's "Project Overview"): the
  number of connections, ‹ connection › to step through them, ↗ to its panel; its engine, address
  and status, the name, uptime as the design's thick ink bar, three small facts, then its latest
  activity as the design's timeline, each with ↗ to the event in Activity.
-->
<script setup lang="ts">
import type { AuditEvent } from '#shared/types/audit'
import type { DataSourceRow } from '#shared/types/datasources'

const props = defineProps<{ sources: DataSourceRow[] | null }>()
const { t } = useI18n()
const api = useApi()
const { number, relative } = useFormat()
const format = useAuditFormat()

// The ones that need a look first, then the busiest
const ordered = computed(() => [...(props.sources ?? [])].sort((a, b) => Number(b.status === 'failing' || b.status === 'attention') - Number(a.status === 'failing' || a.status === 'attention') || b.operations_30d - a.operations_30d))
const index = ref(0)
watch(() => props.sources, () => (index.value = 0))
const source = computed(() => ordered.value[index.value] ?? null)
const move = (by: number) => ordered.value.length && (index.value = (index.value + by + ordered.value.length) % ordered.value.length)
const panel = computed(() => (source.value ? { path: '/data-sources/connections', query: { connection: source.value.id } } : undefined))

const events = ref<AuditEvent[] | null>(null)
watch(
  () => source.value?.id,
  async id => {
    if (!id) return
    events.value = null
    try {
      const { data } = await api.list<AuditEvent>('/audit-logs', { 'filter[area]': 'data', 'filter[resource_id]': id, page_size: 3, sort: '-occurred_at' }, { background: true })
      if (source.value?.id === id) events.value = data
    } catch {
      events.value = []
    }
  },
  { immediate: true },
)
const facts = computed(() => {
  const item = source.value
  if (!item) return []
  return [
    { key: 'latency', label: t('dataSources.kpi.latency'), value: item.latency_ms == null ? '–' : t('dataSources.ms', { n: item.latency_ms }) },
    { key: 'forms', label: t('dataSources.home.formsShort'), value: number(item.forms_count) },
    { key: 'ops', label: t('dataSources.home.ops30'), value: number(item.operations_30d) },
  ]
})
</script>

<template>
  <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <h2 class="text-sm font-semibold whitespace-nowrap text-highlighted">{{ t('dataSources.home.connection') }}</h2>
        <UBadge :label="number(sources?.length ?? 0)" color="neutral" variant="soft" size="sm" class="rounded-md tabular-nums" />
      </div>
      <div class="flex shrink-0 items-center gap-1.5">
        <UFieldGroup size="xs">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="ordered.length < 2" :aria-label="t('dataSources.home.previous')" @click="move(-1)" />
          <UButton :label="source?.name ?? '…'" color="neutral" variant="outline" class="max-w-28 sm:max-w-36 lg:max-w-24 2xl:max-w-36" :ui="{ label: 'truncate' }" :to="panel" :disabled="!source" />
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="outline" square class="rtl:-scale-x-100" :disabled="ordered.length < 2" :aria-label="t('dataSources.home.next')" @click="move(1)" />
        </UFieldGroup>
        <UButton v-if="source" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" square class="rtl:-scale-x-100" :to="panel" :aria-label="t('dataSources.home.openConnection')" />
      </div>
    </div>

    <div v-if="!sources" class="flex flex-col gap-3"><USkeleton class="h-4 w-32" /><USkeleton class="h-7 w-3/4" /><USkeleton class="h-3 w-full" /><USkeleton class="h-16 w-full" /></div>
    <template v-else-if="source">
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="flex min-w-0 items-center gap-1.5 text-xs text-muted">
            <UIcon :name="engineIcon(source.engine)" class="size-3.5 shrink-0" />
            <span class="truncate font-mono" dir="ltr">{{ source.address }}</span>
          </span>
          <DataStatusBadge :status="source.status" />
        </div>
        <NuxtLink :to="panel!" class="truncate text-xl font-semibold text-highlighted hover:underline focus-visible:underline focus-visible:outline-none sm:text-2xl">{{ source.name }}</NuxtLink>
        <p class="truncate text-sm text-muted">{{ [engineName(source.engine), source.database, source.server_version].filter(Boolean).join(' · ') }}</p>
      </div>

      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between text-sm">
          <span class="text-muted">{{ t('dataSources.uptime') }}</span>
          <span class="font-semibold text-highlighted tabular-nums">{{ source.uptime_30d == null ? '–' : `${number(source.uptime_30d, { maximumFractionDigits: 1 })}%` }}</span>
        </div>
        <div class="h-2 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted transition-[width] duration-500" :style="{ width: `${source.uptime_30d ?? 0}%` }" /></div>
      </div>

      <dl class="grid grid-cols-3 gap-2">
        <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col rounded-md bg-elevated/60 px-2.5 py-1.5">
          <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
          <dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ fact.value }}</dd>
        </div>
      </dl>

      <div class="flex flex-col gap-3 border-t border-default pt-4">
        <h3 class="text-sm font-semibold text-highlighted">{{ t('dataSources.home.latest') }}</h3>
        <div v-if="!events" class="flex flex-col gap-3"><USkeleton v-for="n in 2" :key="n" class="h-10 w-full" /></div>
        <p v-else-if="!events.length" class="text-sm text-muted">{{ t('dataSources.home.noEvents') }}</p>
        <ol v-else class="flex flex-col">
          <li v-for="(event, i) in events" :key="event.id" class="relative flex items-start gap-3 pb-3 last:pb-0">
            <span v-if="i < events.length - 1" class="absolute start-[5px] top-4 bottom-0 border-s border-dashed border-(--ui-border-accented)" aria-hidden="true" />
            <span class="mt-1 size-3 shrink-0 rounded-[3px] border-2" :class="i === 0 ? 'border-(--ui-text-highlighted) bg-inverted' : 'border-(--ui-border-accented) bg-elevated'" aria-hidden="true" />
            <div class="flex min-w-0 flex-1 flex-col">
              <span class="truncate text-xs text-muted">{{ relative(event.occurred_at) }} · {{ event.actor.name }}</span>
              <span class="truncate text-sm font-semibold text-highlighted">{{ format.actionLabel(event.action) }}</span>
            </div>
            <UButton :label="t('analytics.focus.view')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" class="shrink-0" :to="{ path: '/data-sources/activity', query: { event: event.id } }" />
          </li>
        </ol>
      </div>
    </template>
  </UCard>
</template>

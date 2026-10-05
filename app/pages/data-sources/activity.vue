<!--
  Data sources → Activity (F12 M5; locked list format, rule 21): everything that happened on the
  organisation's connections, straight from the audit trail (area `data`). Two chart cards (the
  last 30 days with daily bars; activity by kind as thin lines whose legend filters), then
  DataView (table / cards) with connection, kind and result filters, a date range, search and
  sort. A row opens the event (the audit trail's panel, `?event=`). `?connection=` and `?kind=`
  come from other pages (a connection's panel, Exports).
-->
<script setup lang="ts">
import type { AuditEvent } from '#shared/types/audit'
import type { DataSourceRow } from '#shared/types/datasources'
import { ACTIVITY_ACTIONS, ACTIVITY_KINDS, type ActivityInsights, type ActivityKind } from '#shared/utils/datasources/activity'

definePageMeta({ breadcrumb: 'nav.dataActivity' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const format = useAuditFormat()
const { endSide } = useAppLocale()
useHead({ title: () => t('nav.dataActivity') })

const insights = ref<ActivityInsights | null>(null)
const sources = ref<DataSourceRow[]>([])
onMounted(async () => {
  try {
    insights.value = (await api.get<ActivityInsights>('/datasources/activity/insights')).data
  } catch (error) {
    handle(error, { silent: true })
  }
  try {
    sources.value = (await api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' }, { background: true })).data
  } catch {
    sources.value = []
  }
})

const columns = computed<DataColumn[]>(() => [
  { key: 'occurred_at', label: t('audit.col.when'), sortable: true },
  { key: 'action', label: t('audit.col.action'), fixed: true },
  { key: 'connection', label: t('destinations.col.connection'), hideBelow: 'md' },
  { key: 'details', label: t('dataActivity.col.details'), hideBelow: 'lg' },
  { key: 'actor', label: t('audit.col.person'), hideBelow: 'sm' },
  { key: 'outcome', label: t('audit.col.result'), hideBelow: 'sm' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'connection', label: t('destinations.col.connection'), icon: 'i-lucide-database', options: sources.value.map(source => ({ value: source.id, label: source.name })) },
  { key: 'kind', label: t('dataActivity.col.kind'), icon: 'i-lucide-shapes', options: ACTIVITY_KINDS.map(kind => ({ value: kind, label: t(`dataActivity.kind.${kind}`) })) },
  { key: 'outcome', label: t('audit.filter.outcome'), icon: 'i-lucide-circle-dot', options: (['success', 'failure', 'blocked'] as const).map(value => ({ value, label: format.outcomeLabel(value), dot: OUTCOME_DOTS[value] })) },
])
const sortOptions = computed(() => [
  { label: t('audit.sortNewest'), value: '-occurred_at' },
  { label: t('audit.sortOldest'), value: 'occurred_at' },
])

// The audit trail, Data sources only; a kind becomes its actions, a connection its resource id
const fetcher: DataFetcher<AuditEvent> = (params, signal) => {
  const { 'filter[kind]': kind, 'filter[connection]': connection, ...rest } = params
  const kinds = typeof kind === 'string' && kind ? (kind.split(',') as ActivityKind[]) : []
  return api.list<AuditEvent>('/audit-logs', { ...rest, 'filter[area]': 'data', ...(kinds.length ? { 'filter[action]': kinds.flatMap(item => ACTIVITY_ACTIONS[item] ?? []).join(',') } : {}), ...(connection ? { 'filter[resource_id]': connection } : {}) }, { signal })
}

const kindFilter = computed(() => (typeof route.query.kind === 'string' && !route.query.kind.includes(',') ? route.query.kind : null))
const filterKind = (kind: string) => void router.replace({ query: { ...route.query, kind: kindFilter.value === kind ? undefined : kind, page: undefined } })

/** The useful facts of an event in one line (table, statement, rows, format). */
function details(event: AuditEvent) {
  const meta = event.metadata
  const parts = [meta.table, meta.statement && meta.statement.replace(/\s+/g, ' ').slice(0, 80), meta.name, meta.rows && t('dataActivity.rows', { n: number(Number(meta.rows)) }, Number(meta.rows)), meta.format?.toUpperCase()]
  return parts.filter(Boolean).join(' · ') || '–'
}

// The event panel (the audit trail's), `?event=` keeps it open
const selected = shallowRef<AuditEvent | null>(null)
const detailOpen = computed({ get: () => !!route.query.event, set: value => !value && closeEvent() })
function openEvent(event: AuditEvent) {
  selected.value = event
  void router.replace({ query: { ...route.query, event: event.id } })
}
function closeEvent() {
  const { event: _event, ...rest } = route.query
  void router.replace({ query: rest })
}
watch(
  () => route.query.event,
  async id => {
    if (typeof id !== 'string' || !id || selected.value?.id === id) return
    try {
      selected.value = (await api.get<AuditEvent>(`/audit-logs/${id}`)).data
    } catch (error) {
      handle(error)
      closeEvent()
    }
  },
  { immediate: true },
)
const applyFilter = (patch: Record<string, string>) => void navigateTo({ path: '/audit', query: patch })
</script>

<template>
  <AppPanel id="data-activity" :title="t('nav.dataActivity')" :subtitle="t('dataSources.section.activity')" subtitle-icon="i-lucide-activity">
    <template #actions>
      <UButton :label="t('dataActivity.fullTrail')" icon="i-lucide-scroll-text" color="neutral" variant="outline" :to="{ path: '/audit', query: { area: 'data' } }" />
    </template>

    <DatasourcesActivityOverview :insights="insights" :kind="kindFilter" @kind="filterKind" />

    <DataView
      id="data-activity"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-occurred_at"
      date-range
      :open-row="openEvent"
      :search-placeholder="t('dataActivity.search')"
      empty-icon="i-lucide-activity"
      :empty-title="t('dataActivity.emptyTitle')"
      :empty-description="t('dataActivity.emptyDesc')"
    >
      <template #occurred_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.occurred_at)">
          <span class="whitespace-nowrap">{{ relative(row.original.occurred_at) }}</span>
        </UTooltip>
      </template>
      <template #action-cell="{ row }">
        <span class="flex min-w-0 items-center gap-2.5">
          <UIcon :name="format.actionIcon(row.original.action)" class="size-4 shrink-0 text-muted" />
          <span class="truncate font-medium text-highlighted">{{ format.actionLabel(row.original.action) }}</span>
        </span>
      </template>
      <template #connection-cell="{ row }">
        <span class="truncate">{{ row.original.resource?.name ?? '–' }}</span>
      </template>
      <template #details-cell="{ row }">
        <span class="block max-w-80 truncate font-mono text-xs text-muted" dir="auto">{{ details(row.original) }}</span>
      </template>
      <template #actor-cell="{ row }">
        <UUser :name="row.original.actor.name" :avatar="{ alt: row.original.actor.name }" size="sm" :ui="{ name: 'truncate max-w-40' }" />
      </template>
      <template #outcome-cell="{ row }">
        <UBadge :label="format.outcomeLabel(row.original.outcome)" :color="format.outcomeColor(row.original.outcome)" variant="subtle" size="sm" class="rounded-md" />
      </template>
      <template #grid-card="{ row }">
        <AuditEventCard :event="row" :actions="[]" @open="openEvent" />
      </template>
    </DataView>

    <USlideover v-model:open="detailOpen" :side="endSide" :title="selected ? format.actionLabel(selected.action) : t('common.loading')" :description="selected ? `${selected.actor.name} · ${relative(selected.occurred_at)}` : undefined" :ui="{ content: 'w-full sm:max-w-xl' }">
      <template #body>
        <div v-if="!selected" class="space-y-4" :aria-label="t('common.loading')">
          <USkeleton class="h-6 w-40" />
          <USkeleton class="h-24 w-full" />
        </div>
        <AuditEventDetail v-else :event="selected" @open="openEvent" @filter="applyFilter" />
      </template>
    </USlideover>
  </AppPanel>
</template>

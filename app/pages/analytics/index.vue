<!--
  Analytics (F18, the design's dashboard: docs/design 092034). The period (date range, last 30 days
  by default, kept in the address) in the header with Download; five KPI cards (views, started,
  completed, completion rate, time to fill in) with their change; the conversion overview (started
  vs completed, Daily / Weekly / Monthly) beside one form at a time with where people stop; then
  every form's numbers (DataView table / cards). A form opens its panel: funnel, pages, questions.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { AnalyticsOverview, AnalyticsTotals, FormAnalyticsRow } from '#shared/types/analytics'

definePageMeta({ breadcrumb: 'nav.analytics' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { handle } = useErrorHandler()
const { number } = useFormat()
const { duration } = useResponseFormat()
useHead({ title: () => t('nav.analytics') })

// The period: ?from&to (default the last 30 days)
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)
const today = iso(Date.now())
const from = computed(() => (typeof route.query.from === 'string' && route.query.from ? route.query.from : iso(Date.now() - 29 * 86_400_000)))
const to = computed(() => (typeof route.query.to === 'string' && route.query.to ? route.query.to : today))
const setPeriod = (start: string, end: string) => void router.replace({ query: { ...route.query, from: start || undefined, to: end || undefined, page: undefined } })

const overview = ref<AnalyticsOverview | null>(null)
const focus = ref<FormAnalyticsRow[] | null>(null)
const focusTotal = ref(0)
async function load() {
  overview.value = null
  focus.value = null
  try {
    const [summary, top] = await Promise.all([
      api.get<AnalyticsOverview>('/analytics/overview', { from: from.value, to: to.value }),
      api.list<FormAnalyticsRow>('/analytics/forms', { from: from.value, to: to.value, page_size: 10, sort: '-completions' }),
    ])
    overview.value = summary.data
    focus.value = top.data
    focusTotal.value = top.meta.total
  } catch (error) {
    handle(error)
  }
}
const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<FormAnalyticsRow[]> } }>('view')
watch([from, to], () => {
  void load()
  void view.value?.refresh()
}, { immediate: true })

const change = (key: keyof AnalyticsTotals) => {
  const now = overview.value?.totals[key]
  const before = overview.value?.previous[key]
  return now != null && before ? Math.round(((now - before) / before) * 100) : null
}
const kpis = computed(() => {
  const totals = overview.value?.totals
  return [
    { key: 'views', icon: 'i-lucide-eye', label: t('analytics.views'), value: totals ? number(totals.views) : null },
    { key: 'starts', icon: 'i-lucide-pointer', label: t('analytics.started'), value: totals ? number(totals.starts) : null },
    { key: 'completions', icon: 'i-lucide-circle-check', label: t('analytics.completedLabel'), value: totals ? number(totals.completions) : null, to: '/responses' },
    { key: 'completion_rate', icon: 'i-lucide-percent', label: t('analytics.rate'), value: totals ? `${number(totals.completion_rate, { maximumFractionDigits: 1 })}%` : null },
    { key: 'median_seconds', icon: 'i-lucide-timer', label: t('analytics.time'), value: totals ? (totals.median_seconds ? duration(totals.median_seconds) : '–') : null, lower: true },
  ] as const
})

// Every form
const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('analytics.col.form'), sortable: true, fixed: true },
  { key: 'status', label: t('analytics.col.status'), hideBelow: 'md' },
  { key: 'views', label: t('analytics.views'), sortable: true, hideBelow: 'lg' },
  { key: 'starts', label: t('analytics.started'), sortable: true, hideBelow: 'md' },
  { key: 'completions', label: t('analytics.completedLabel'), sortable: true },
  { key: 'completion_rate', label: t('analytics.rate'), sortable: true, hideBelow: 'sm' },
  { key: 'median_seconds', label: t('analytics.time'), sortable: true, hideBelow: 'lg', hidden: true },
  { key: 'drop_off', label: t('analytics.col.stop'), hideBelow: 'lg' },
])
const filters = computed<DataFilter[]>(() => [])
const sortOptions = computed(() => [
  { label: t('analytics.sort.completions'), value: '-completions' },
  { label: t('analytics.sort.views'), value: '-views' },
  { label: t('analytics.sort.rateLow'), value: 'completion_rate' },
  { label: t('analytics.sort.rateHigh'), value: '-completion_rate' },
  { label: t('forms.sortName'), value: 'name' },
])
const fetcher: DataFetcher<FormAnalyticsRow> = (params, signal) => api.list<FormAnalyticsRow>('/analytics/forms', { ...params, from: from.value, to: to.value }, { signal })

const panelOpen = ref(false)
const openId = ref<string | null>(null)
const ids = ref<string[]>([])
function openForm(id: string) {
  const rows = view.value?.state.rows.value ?? []
  ids.value = rows.some(row => row.id === id) ? rows.map(row => row.id) : (focus.value ?? []).map(row => row.id)
  openId.value = id
  panelOpen.value = true
}
const rowActions = (row: FormAnalyticsRow): DropdownMenuItem[][] => [
  [
    { label: t('analytics.actions.details'), icon: 'i-lucide-chart-spline', onSelect: () => openForm(row.id) },
    { label: t('analytics.actions.perQuestion'), icon: 'i-lucide-chart-no-axes-combined', to: { path: `/forms/${row.id}/responses`, query: { view: 'insights' } } },
  ],
  [
    { label: t('analytics.actions.openForm'), icon: 'i-lucide-file-text', to: `/forms/${row.id}` },
    { label: t('analytics.actions.builder'), icon: 'i-lucide-pencil-ruler', to: `/forms/${row.id}/build` },
  ],
]

// Download: every form's numbers for the period as CSV (counts only, built here from the list)
const { busy: downloading, run } = useBusy()
const download = () =>
  run(
    async () => {
      const rows: FormAnalyticsRow[] = []
      for (let page = 1; page <= 50; page++) {
        const { data, meta } = await api.list<FormAnalyticsRow>('/analytics/forms', { from: from.value, to: to.value, page, page_size: 100, sort: 'name' })
        rows.push(...data)
        if (page >= meta.total_pages) break
      }
      const csv = analyticsCsv([
        [t('analytics.col.form'), t('analytics.col.status'), t('analytics.views'), t('analytics.started'), t('analytics.completedLabel'), t('analytics.rate'), t('analytics.time'), t('analytics.col.stop')],
        ...rows.map(row => [row.name, t(`status.${row.status}`), row.views, row.starts, row.completions, row.completion_rate, row.median_seconds, row.drop_off?.field_label ?? null]),
      ])
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      link.download = `formalie-analytics-${from.value}-${to.value}.csv`
      link.click()
      setTimeout(() => URL.revokeObjectURL(link.href), 1000)
    },
    { success: t('analytics.downloaded') },
  )
</script>

<template>
  <AppPanel id="analytics" :title="t('nav.analytics')" :subtitle="t('analytics.subtitle')" subtitle-icon="i-lucide-chart-column">
    <template #actions>
      <DataDateRangePicker :from="from" :to="to" @change="setPeriod" />
      <UButton :label="t('analytics.download')" icon="i-lucide-download" color="neutral" :loading="downloading" @click="download" />
    </template>

    <div class="flex shrink-0 snap-x gap-3 overflow-x-auto [scrollbar-width:none] sm:grid sm:grid-cols-3 sm:overflow-visible xl:grid-cols-5">
      <ChartsKpi
        v-for="kpi in kpis"
        :key="kpi.key"
        class="min-w-[13.5rem] snap-start sm:min-w-0"
        :label="kpi.label"
        :icon="kpi.icon"
        :value="kpi.value"
        :change="change(kpi.key)"
        :lower-is-better="'lower' in kpi"
        :to="'to' in kpi ? kpi.to : undefined"
      />
    </div>

    <div class="grid shrink-0 gap-4 lg:grid-cols-3">
      <AnalyticsConversion class="lg:col-span-2" :overview="overview" :change="change('completions')" />
      <AnalyticsFormFocus :forms="focus" :total="focusTotal" :from="from" :to="to" @open="openForm" />
    </div>

    <DataView
      id="analytics-forms"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-completions"
      :row-actions="rowActions"
      :open-row="row => openForm(row.id)"
      :search-placeholder="t('analytics.search')"
      empty-icon="i-lucide-chart-column"
      :empty-title="t('analytics.emptyTitle')"
      :empty-description="t('analytics.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-1.5">
          <UIcon v-if="row.original.starts >= 10 && row.original.completion_rate < 40" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('analytics.card.flag')" />
          <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
        </div>
      </template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" /></template>
      <template #views-cell="{ row }"><span class="tabular-nums">{{ number(row.original.views) }}</span></template>
      <template #starts-cell="{ row }"><span class="tabular-nums">{{ number(row.original.starts) }}</span></template>
      <template #completions-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-10 tabular-nums">{{ number(row.original.completions) }}</span>
          <ChartsSparkline :values="(row.original as FormAnalyticsRow).trend" :width="64" :height="18" class="hidden sm:block" />
        </div>
      </template>
      <template #completion_rate-cell="{ row }">
        <div class="flex min-w-28 items-center gap-2">
          <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${row.original.completion_rate}%` }" /></div>
          <span class="w-11 text-end text-xs tabular-nums">{{ number(row.original.completion_rate, { maximumFractionDigits: 1 }) }}%</span>
        </div>
      </template>
      <template #median_seconds-cell="{ row }"><span class="text-muted tabular-nums">{{ row.original.median_seconds ? duration(row.original.median_seconds) : '–' }}</span></template>
      <template #drop_off-cell="{ row }">
        <span v-if="row.original.drop_off" class="flex min-w-0 flex-col leading-tight">
          <span class="truncate text-sm">{{ row.original.drop_off.field_label }}</span>
          <span class="text-[11px] text-muted">{{ t('analytics.focus.leftShare', { n: number(row.original.drop_off.rate, { maximumFractionDigits: 1 }) }) }}</span>
        </span>
        <span v-else class="text-muted">–</span>
      </template>
      <template #empty-actions>
        <UButton :label="t('analytics.lastYear')" icon="i-lucide-calendar-range" color="neutral" variant="outline" @click="setPeriod(iso(Date.now() - 364 * 86_400_000), today)" />
      </template>
      <template #grid-card="{ row }">
        <AnalyticsFormCard :item="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <AnalyticsDetail :id="openId" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :from="from" :to="to" @go="id => (openId = id)" />
  </AppPanel>
</template>

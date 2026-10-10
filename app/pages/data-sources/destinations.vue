<!--
  Data sources → Destinations (F12 M2; locked list format, rule 21): every form that stores its
  responses in a database. Two chart cards (responses delivered, forms by delivery status with a
  legend that filters), then DataView (table / locked card) with status, connection and table
  filters, search and sort. A row or card opens its panel (`?destination=` keeps it open; with
  `&backfill=1` it offers to send earlier responses, right after setting up).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DataSourceRow } from '#shared/types/datasources'
import type { DestinationInsights, DestinationRow } from '#shared/types/destinations'

definePageMeta({ breadcrumb: 'nav.destinations' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const counts = useNavCounts()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const { can } = useCan()
useHead({ title: () => t('nav.destinations') })

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: { value: DestinationRow[] } } }>('view')
const insights = ref<DestinationInsights | null>(null)
const sources = ref<DataSourceRow[]>([])
async function loadInsights() {
  try {
    insights.value = (await api.get<DestinationInsights>('/destinations/insights')).data
  } catch (error) {
    handle(error, { silent: true })
  }
}
onMounted(async () => {
  void loadInsights()
  try {
    sources.value = (await api.list<DataSourceRow>('/datasources', { page_size: 100, sort: 'name' }, { background: true })).data
  } catch {
    sources.value = []
  }
})
async function refreshAll() {
  void counts.refresh(true)
  await Promise.all([view.value?.refresh(), loadInsights()])
}

const columns = computed<DataColumn[]>(() => [
  { key: 'form_name', label: t('destinations.col.form'), sortable: true, fixed: true },
  { key: 'connection', label: t('destinations.col.connection'), hideBelow: 'md' },
  { key: 'table', label: t('destinations.col.table'), hideBelow: 'lg' },
  { key: 'status', label: t('dataSources.col.status'), sortable: true },
  { key: 'sent_30d', label: t('destinations.kpi.sent30'), sortable: true, hideBelow: 'sm' },
  { key: 'failed', label: t('destinations.kpi.failed'), sortable: true, hideBelow: 'md' },
  { key: 'pending', label: t('destinations.kpi.pending'), sortable: true, hideBelow: 'lg', hidden: true },
  { key: 'last_delivery_at', label: t('destinations.kpi.last'), sortable: true, hideBelow: 'lg' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('dataSources.col.status'), icon: 'i-lucide-circle-dot', options: (['active', 'paused', 'failing'] as const).map(status => ({ value: status, label: t(`destinations.status.${status}`), dot: status === 'active' ? 'bg-green-500' : status === 'failing' ? 'bg-red-500' : 'bg-(--ui-text-dimmed)' })) },
  { key: 'datasource', label: t('destinations.col.connection'), icon: 'i-lucide-database', options: sources.value.map(source => ({ value: source.id, label: source.name })) },
  { key: 'table', label: t('destinations.col.table'), icon: 'i-lucide-table-2', options: [{ value: 'created', label: t('destinations.table.created') }, { value: 'existing', label: t('destinations.table.yours') }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'form_name' },
  { label: t('destinations.sort.busiest'), value: '-sent_30d' },
  { label: t('destinations.sort.failed'), value: '-failed' },
  { label: t('destinations.sort.recent'), value: '-last_delivery_at' },
])
const fetcher: DataFetcher<DestinationRow> = (params, signal) => api.list<DestinationRow>('/destinations', params, { signal })

const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const filterStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

const openId = computed(() => (typeof route.query.destination === 'string' ? route.query.destination : null))
const backfill = computed(() => route.query.backfill === '1')
const panelOpen = computed({
  get: () => !!openId.value,
  set: value => !value && void router.replace({ query: { ...route.query, destination: undefined, backfill: undefined } }),
})
const ids = ref<string[]>([])
const openRow = (row: DestinationRow) => {
  ids.value = (view.value?.state.rows.value ?? [row]).map(item => item.id)
  void router.replace({ query: { ...route.query, destination: row.id, backfill: undefined } })
}
const go = (id: string) => void router.replace({ query: { ...route.query, destination: id, backfill: undefined } })
watch(() => view.value?.state.rows.value, rows => rows && !ids.value.length && (ids.value = rows.map(row => row.id)))

const busyIds = ref(new Set<string>())
async function act(row: DestinationRow, work: () => Promise<unknown>, success: string) {
  busyIds.value = new Set([...busyIds.value, row.id])
  try {
    await work()
    toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    busyIds.value = new Set([...busyIds.value].filter(id => id !== row.id))
  }
}
async function remove(row: DestinationRow) {
  if (!(await confirm({ title: t('destinations.remove.title', { form: row.form.name }), description: t('destinations.remove.desc'), confirmLabel: t('destinations.remove.confirm'), danger: true }))) return
  await act(row, () => api.del(`/destinations/${row.id}`), t('destinations.toast.removed'))
}
// Changing how a form is stored needs data.storage; opening stays for everyone who can see it
const rowActions = (row: DestinationRow): DropdownMenuItem[][] =>
  [
    [
      { label: t('dataSources.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
      { label: t('destinations.actions.openForm'), icon: 'i-lucide-file-text', to: `/forms/${row.form.id}` },
      ...(can('data.storage')
        ? [
            { label: t('destinations.actions.change'), icon: 'i-lucide-columns-3', to: `/forms/${row.form.id}/storage` },
            row.status === 'paused'
              ? { label: t('destinations.actions.resume'), icon: 'i-lucide-circle-play', onSelect: () => void act(row, () => api.patch(`/destinations/${row.id}`, { paused: false }), t('destinations.toast.resumed')) }
              : { label: t('destinations.actions.pause'), icon: 'i-lucide-circle-pause', onSelect: () => void act(row, () => api.patch(`/destinations/${row.id}`, { paused: true }), t('destinations.toast.paused')) },
            ...(row.failed ? [{ label: t('destinations.actions.retryAll', { n: row.failed }, row.failed), icon: 'i-lucide-rotate-cw', onSelect: () => void act(row, () => api.post(`/destinations/${row.id}/retry`, {}), t('destinations.toast.retried', { n: row.failed }, row.failed)) }] : []),
          ]
        : []),
    ],
    can('data.storage') ? [{ label: t('destinations.actions.remove'), icon: 'i-lucide-undo-2', color: 'error' as const, onSelect: () => void remove(row) }] : [],
  ].filter(group => group.length)
</script>

<template>
  <AppPanel id="data-destinations" :title="t('nav.destinations')" :subtitle="t('dataSources.section.destinations')" subtitle-icon="i-lucide-send">
    <template #actions>
      <UButton v-if="can('data.storage')" :label="t('destinations.add')" icon="i-lucide-plus" color="neutral" to="/forms" />
    </template>

    <DestinationsOverview :insights="insights" :status="statusFilter" @status="filterStatus" />

    <DataView
      id="data-destinations"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="form_name"
      :row-actions="rowActions"
      :busy="row => busyIds.has(row.id)"
      :open-row="openRow"
      :search-placeholder="t('destinations.search')"
      empty-icon="i-lucide-send"
      :empty-title="t('destinations.emptyTitle')"
      :empty-description="t('destinations.emptyDesc')"
    >
      <template #form_name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-1.5">
          <UIcon v-if="row.original.status === 'failing'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('dataSources.needsLook')" />
          <span class="truncate font-medium text-highlighted">{{ row.original.form.name }}</span>
        </div>
      </template>
      <template #connection-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2">
          <DatasourcesEngineLogo :engine="row.original.datasource.engine" size="sm" />
          <span class="truncate">{{ row.original.datasource.name }}</span>
        </div>
      </template>
      <template #table-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <code class="max-w-56 truncate text-start font-mono text-xs" dir="ltr">{{ row.original.table.schema }}.{{ row.original.table.name }}</code>
          <span class="text-xs text-muted">{{ row.original.table.created ? t('destinations.table.created') : t('destinations.table.yours') }}</span>
        </div>
      </template>
      <template #status-cell="{ row }">
        <DataStatusBadge :status="row.original.status" :label="t(`destinations.status.${row.original.status}`)" />
      </template>
      <template #sent_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-12 tabular-nums">{{ number(row.original.sent_30d) }}</span>
          <ChartsSparkline :values="(row.original as DestinationRow).daily.map(day => day.count)" :width="72" :height="20" />
        </div>
      </template>
      <template #failed-cell="{ row }">
        <span class="tabular-nums" :class="row.original.failed ? 'font-medium text-error' : 'text-muted'">{{ number(row.original.failed) }}</span>
      </template>
      <template #pending-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.pending) }}</span>
      </template>
      <template #last_delivery_at-cell="{ row }">
        <UTooltip v-if="row.original.last_delivery_at" :text="dateTime(row.original.last_delivery_at)">
          <span class="whitespace-nowrap text-muted">{{ relative(row.original.last_delivery_at) }}</span>
        </UTooltip>
        <span v-else class="text-muted">–</span>
      </template>
      <template #empty-actions>
        <UButton v-if="can('data.storage')" :label="t('destinations.add')" icon="i-lucide-plus" color="neutral" to="/forms" />
      </template>
      <template #grid-card="{ row }">
        <DestinationsCard :destination="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <DestinationsDetail :id="openId" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :backfill="backfill" @go="go" @changed="refreshAll" />
  </AppPanel>
</template>

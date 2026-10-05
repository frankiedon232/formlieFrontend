<!--
  Data sources → Connections (F12 M1; locked list format, rule 21): two chart cards (activity,
  connections by status with a legend that filters), then every connection in DataView (table /
  locked card) with status, engine and access filters, search and sort. A row or card opens the
  connection's panel (`?connection=` keeps it open on reload and in shared links). Add connection
  in the header and the empty state.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { DATASOURCE_STATUSES, type DataSourceDetail, type DataSourceInsights, type DataSourceRow, type OtherTablesAccess } from '#shared/types/datasources'
import { SUPPORTED_DATABASES } from '#shared/utils/integrations/databases'

definePageMeta({ breadcrumb: 'nav.dataConnections' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const counts = useNavCounts()
const { handle } = useErrorHandler()
const { relative, dateTime } = useFormat()
useHead({ title: () => t('nav.dataConnections') })

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: { value: DataSourceRow[] } } }>('view')
const insights = ref<DataSourceInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<DataSourceInsights>('/datasources/insights')).data
  } catch (error) {
    handle(error, { silent: true })
  }
}
void loadInsights()
async function refreshAll() {
  void counts.refresh(true)
  await Promise.all([view.value?.refresh(), loadInsights()])
}

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('dataSources.col.connection'), sortable: true, fixed: true },
  { key: 'address', label: t('dataSources.summary.address'), hideBelow: 'lg' },
  { key: 'database', label: t('dataSources.summary.database'), hideBelow: 'lg', hidden: true },
  { key: 'access', label: t('dataSources.summary.access'), hideBelow: 'md' },
  { key: 'status', label: t('dataSources.col.status'), sortable: true },
  { key: 'uptime_30d', label: t('dataSources.uptime'), sortable: true, hideBelow: 'md' },
  { key: 'latency_ms', label: t('dataSources.kpi.latency'), sortable: true, hideBelow: 'lg', hidden: true },
  { key: 'operations_30d', label: t('dataSources.kpi.operations'), sortable: true, hideBelow: 'lg', hidden: true },
  { key: 'last_checked_at', label: t('dataSources.lastChecked'), sortable: true, hideBelow: 'sm' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('dataSources.col.status'), icon: 'i-lucide-circle-dot', options: DATASOURCE_STATUSES.map(status => ({ value: status, label: t(`status.${status}`), dot: DATASOURCE_STATUS_META[status].fill })) },
  { key: 'engine', label: t('dataSources.summary.engine'), icon: 'i-lucide-database', options: SUPPORTED_DATABASES.map(db => ({ value: db.key, label: db.name })) },
  { key: 'access', label: t('dataSources.summary.access'), icon: 'i-lucide-key-round', options: (['read_write', 'read', 'none'] as const).map(other => ({ value: other, label: t(`dataSources.access.other.${other}`) })) },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('dataSources.sort.checked'), value: '-last_checked_at' },
  { label: t('dataSources.sort.uptime'), value: 'uptime_30d' },
  { label: t('dataSources.sort.operations'), value: '-operations_30d' },
  { label: t('dataSources.sort.newest'), value: '-created_at' },
])
const fetcher: DataFetcher<DataSourceRow> = (params, signal) => api.list<DataSourceRow>('/datasources', params, { signal })

// The legend filters the list (one status at a time, like the sidebar).
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const filterStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel follows ?connection=
const openId = computed(() => (typeof route.query.connection === 'string' ? route.query.connection : null))
const panelOpen = computed({
  get: () => !!openId.value,
  set: value => !value && void router.replace({ query: { ...route.query, connection: undefined } }),
})
const ids = ref<string[]>([])
const openRow = (row: DataSourceRow) => {
  ids.value = (view.value?.state.rows.value ?? [row]).map(item => item.id)
  void router.replace({ query: { ...route.query, connection: row.id } })
}
const go = (id: string) => void router.replace({ query: { ...route.query, connection: id } })
watch(() => view.value?.state.rows.value, rows => rows && !ids.value.length && (ids.value = rows.map(row => row.id)))

const busyIds = ref(new Set<string>())
async function act(row: DataSourceRow, work: () => Promise<unknown>, success: string) {
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
async function toggle(row: DataSourceRow) {
  if (row.enabled && !(await confirm({ title: t('dataSources.disable.title', { name: row.name }), description: t('dataSources.disable.desc'), confirmLabel: t('dataSources.disable.confirm') }))) return
  await act(row, () => api.patch(`/datasources/${row.id}`, { enabled: !row.enabled }), row.enabled ? t('dataSources.toast.disabled') : t('dataSources.toast.enabled'))
}
async function duplicate(row: DataSourceRow) {
  await act(
    row,
    async () => {
      const { data } = await api.post<DataSourceDetail>(`/datasources/${row.id}/duplicate`)
      await navigateTo(`/data-sources/connections/${data.id}/edit`)
    },
    t('dataSources.toast.duplicated'),
  )
}
async function remove(row: DataSourceRow) {
  if (!(await confirm({ title: t('dataSources.delete.title', { name: row.name }), description: t('dataSources.delete.desc'), confirmLabel: t('dataSources.delete.confirm'), danger: true }))) return
  await act(row, () => api.del(`/datasources/${row.id}`), t('dataSources.toast.deleted'))
}
const rowActions = (row: DataSourceRow): DropdownMenuItem[][] => [
  [
    { label: t('dataSources.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('dataSources.actions.edit'), icon: 'i-lucide-pencil', to: `/data-sources/connections/${row.id}/edit` },
    { label: t('dataSources.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => void duplicate(row) },
    { label: row.enabled ? t('dataSources.actions.disable') : t('dataSources.actions.enable'), icon: row.enabled ? 'i-lucide-circle-pause' : 'i-lucide-circle-play', onSelect: () => void toggle(row) },
  ],
  [
    row.forms_count
      ? { label: t('dataSources.actions.deleteInUse'), icon: 'i-lucide-trash-2', disabled: true }
      : { label: t('dataSources.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) },
  ],
]
</script>

<template>
  <AppPanel id="data-connections" :title="t('nav.dataConnections')" :subtitle="t('dataSources.section.connections')" subtitle-icon="i-lucide-database">
    <template #actions>
      <UButton :label="t('dataSources.add')" icon="i-lucide-plus" color="neutral" to="/data-sources/connections/new" />
    </template>

    <DatasourcesOverview :insights="insights" :status="statusFilter" @status="filterStatus" />

    <DataView
      id="data-connections"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      default-view="table"
      :row-actions="rowActions"
      :busy="row => busyIds.has(row.id)"
      :open-row="openRow"
      :search-placeholder="t('dataSources.search')"
      empty-icon="i-lucide-database"
      :empty-title="t('dataSources.emptyTitle')"
      :empty-description="t('dataSources.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2.5">
          <DatasourcesEngineLogo :engine="row.original.engine" size="sm" />
          <div class="flex min-w-0 flex-col">
            <span class="flex min-w-0 items-center gap-1.5">
              <UIcon v-if="row.original.status === 'failing' || row.original.status === 'attention'" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('dataSources.needsLook')" />
              <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
            </span>
            <span class="truncate text-xs text-muted">{{ engineName(row.original.engine) }}{{ row.original.server_version ? ` ${row.original.server_version}` : '' }}</span>
          </div>
        </div>
      </template>
      <template #address-cell="{ row }">
        <span class="block max-w-56 truncate text-start font-mono text-xs text-default" dir="ltr">{{ row.original.address }}</span>
      </template>
      <template #database-cell="{ row }">
        <span class="font-mono text-xs" dir="ltr">{{ row.original.database }}</span>
      </template>
      <template #access-cell="{ row }">
        <UBadge :label="t(`dataSources.access.other.${row.original.access.other}`)" :icon="OTHER_ICON[row.original.access.other as OtherTablesAccess]" color="neutral" variant="outline" size="sm" class="rounded-md" />
      </template>
      <template #status-cell="{ row }">
        <div class="flex items-center gap-1.5">
          <DataStatusBadge :status="row.original.status" />
          <UTooltip v-if="row.original.missing_permissions" :text="t('dataSources.missingCount', { n: row.original.missing_permissions }, row.original.missing_permissions)">
            <UIcon name="i-lucide-key-round" class="size-3.5 text-warning" />
          </UTooltip>
        </div>
      </template>
      <template #uptime_30d-cell="{ row }">
        <DataShareBar v-if="row.original.uptime_30d !== null" :value="row.original.uptime_30d / 100" />
        <span v-else class="text-muted">–</span>
      </template>
      <template #latency_ms-cell="{ row }">
        <span class="tabular-nums">{{ row.original.latency_ms === null ? '–' : t('dataSources.ms', { n: row.original.latency_ms }) }}</span>
      </template>
      <template #operations_30d-cell="{ row }">
        <ChartsSparkline :values="(row.original as DataSourceRow).daily.map(day => day.count)" :width="72" :height="20" />
      </template>
      <template #last_checked_at-cell="{ row }">
        <UTooltip v-if="row.original.last_checked_at" :text="dateTime(row.original.last_checked_at)">
          <span class="whitespace-nowrap text-muted">{{ relative(row.original.last_checked_at) }}</span>
        </UTooltip>
        <span v-else class="text-muted">{{ t('dataSources.neverChecked') }}</span>
      </template>
      <template #empty-actions>
        <UButton :label="t('dataSources.add')" icon="i-lucide-plus" color="neutral" to="/data-sources/connections/new" />
      </template>
      <template #grid-card="{ row }">
        <DatasourcesCard :source="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <DatasourcesDetail :id="openId" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" @go="go" @changed="refreshAll" />
  </AppPanel>
</template>

<!--
  API service → Endpoints (F13 M1; locked list format, rule 21): every form turned into an API.
  Two chart cards (calls in the last 30 days; endpoints by method, the legend filters), then
  DataView (table / cards) with service, method and status filters, search and sort. A row or card
  opens its panel (`?endpoint=`); ⋯ / right-click: open, edit, copy address, on / off, delete.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiEndpoint, ApiInsights, ApiService } from '#shared/types/apiService'
import { API_METHODS } from '#shared/utils/urls/public'

definePageMeta({ breadcrumb: 'nav.apiEndpoints' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { relative, dateTime, number, percent } = useFormat()
useHead({ title: () => t('nav.apiEndpoints') })

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ApiEndpoint[]> } }>('view')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<ApiInsights | null>(null)
const services = ref<ApiService[]>([])
async function loadInsights() {
  try {
    insights.value = (await api.get<ApiInsights>('/api-endpoints/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(async () => {
  void loadInsights()
  try {
    services.value = (await api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' }, { background: true })).data
  } catch {
    services.value = []
  }
})
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights(), panel.value?.reload()])
const actions = useApiActions(refreshAll)

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('apiService.col.endpoint'), sortable: true, fixed: true },
  { key: 'service', label: t('apiService.col.service'), hideBelow: 'md' },
  { key: 'methods', label: t('apiService.col.methods'), hideBelow: 'sm' },
  { key: 'status', label: t('apiService.col.status'), hideBelow: 'sm' },
  { key: 'calls_30d', label: t('apiService.col.calls'), sortable: true },
  { key: 'errors_30d', label: t('apiService.col.errors'), sortable: true, hideBelow: 'lg' },
  { key: 'avg_ms', label: t('apiService.kpi.time'), sortable: true, hideBelow: 'lg', hidden: true },
  { key: 'last_call_at', label: t('apiService.col.lastCall'), sortable: true, hideBelow: 'md' },
  { key: 'updated_at', label: t('apiService.col.updated'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'service', label: t('apiService.col.service'), icon: 'i-lucide-boxes', options: services.value.map(service => ({ value: service.id, label: service.name })) },
  { key: 'method', label: t('apiService.col.methods'), icon: 'i-lucide-arrow-left-right', options: API_METHODS.map(method => ({ value: method, label: method })) },
  { key: 'status', label: t('apiService.col.status'), icon: 'i-lucide-circle-dot', options: [{ value: 'active', label: t('status.active'), dot: 'bg-green-500' }, { value: 'disabled', label: t('status.disabled'), dot: 'bg-(--ui-border-accented)' }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('apiService.sort.calls'), value: '-calls_30d' },
  { label: t('apiService.sort.errors'), value: '-errors_30d' },
  { label: t('apiService.sort.lastCall'), value: '-last_call_at' },
  { label: t('apiService.sort.changed'), value: '-updated_at' },
])
const fetcher: DataFetcher<ApiEndpoint> = (params, signal) => api.list<ApiEndpoint>('/api-endpoints', params, { signal })
const methodFilter = computed(() => (typeof route.query.method === 'string' && !route.query.method.includes(',') ? route.query.method : null))
const pickMethod = (method: string) => void router.replace({ query: { ...route.query, method: methodFilter.value === method ? undefined : method, page: undefined } })
const newLink = computed(() => ({ path: '/api-service/endpoints/new', query: typeof route.query.service === 'string' && !route.query.service.includes(',') ? { service: route.query.service } : {} }))

// The panel (`?endpoint=`)
const openId = computed(() => (typeof route.query.endpoint === 'string' ? route.query.endpoint : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, endpoint: undefined } }) })
const ids = computed(() => (view.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: ApiEndpoint) => void router.replace({ query: { ...route.query, endpoint: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, endpoint: id } })
async function remove(endpoint: ApiEndpoint) {
  if ((await actions.deleteEndpoint(endpoint)) && openId.value === endpoint.id) panelOpen.value = false
}
const setStatus = (endpoint: ApiEndpoint, active: boolean) => void actions.setEndpointStatus(endpoint, active ? 'active' : 'disabled')
// Changing endpoints needs api.endpoints (F22 R2 M4); without it the menu only opens and copies
const { can } = useCan()
const rowActions = (row: ApiEndpoint): DropdownMenuItem[][] => {
  const manage = can('api.endpoints')
  return [
    [
      { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
      ...(manage ? [{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', to: `/api-service/endpoints/${row.id}/edit` }] : []),
      { label: t('apiService.actions.copyUrl'), icon: 'i-lucide-link', onSelect: () => actions.copyUrl(row) },
    ],
    manage ? [{ label: row.status === 'active' ? t('apiService.actions.turnOff') : t('apiService.actions.turnOn'), icon: row.status === 'active' ? 'i-lucide-circle-pause' : 'i-lucide-circle-play', onSelect: () => setStatus(row, row.status !== 'active') }] : [],
    manage ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }] : [],
  ].filter(group => group.length)
}
defineShortcuts({ n: { usingInput: false, handler: () => can('api.endpoints') && void navigateTo(newLink.value) } })
</script>

<template>
  <AppPanel id="api-endpoints" :title="t('nav.apiEndpoints')" :subtitle="t('apiService.section.endpoints')" subtitle-icon="i-lucide-route">
    <template #actions>
      <UButton v-if="can('api.endpoints')" :label="t('apiService.actions.newEndpoint')" icon="i-lucide-plus" color="neutral" :to="newLink">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <ApiOverview :insights="insights" by="method" :selected="methodFilter" :count="t('nav.apiEndpoints')" @pick="pickMethod" />

    <DataView
      id="api-endpoints"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      :row-actions="rowActions"
      :busy="row => actions.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t('apiService.searchEndpoints')"
      empty-icon="i-lucide-route"
      :empty-title="t('apiService.emptyEndpoints')"
      :empty-description="t('apiService.emptyEndpointsDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.calls_30d && row.original.errors_30d / row.original.calls_30d > 0.05" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.manyErrors')" />
            <span class="truncate font-mono text-sm font-medium text-highlighted" dir="ltr">/{{ row.original.name }}</span>
          </span>
          <span class="max-w-72 truncate text-xs text-muted">{{ row.original.form.name }}</span>
        </div>
      </template>
      <template #service-cell="{ row }">
        <span class="flex min-w-0 items-center gap-1.5">
          <span class="truncate">{{ row.original.service.name }}</span>
          <UTooltip v-if="row.original.service.status !== 'active'" :text="t('apiService.serviceOff')"><UIcon name="i-lucide-circle-pause" class="size-3.5 shrink-0 text-warning" /></UTooltip>
        </span>
      </template>
      <template #methods-cell="{ row }"><ApiMethods :methods="row.original.methods" size="xs" /></template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" /></template>
      <template #calls_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-12 tabular-nums">{{ number(row.original.calls_30d) }}</span>
          <ChartsSparkline :values="(row.original as ApiEndpoint).daily.map(day => day.count)" :width="72" :height="20" class="hidden sm:block" />
        </div>
      </template>
      <template #errors_30d-cell="{ row }">
        <span class="tabular-nums" :class="row.original.calls_30d && row.original.errors_30d / row.original.calls_30d > 0.05 ? 'font-medium text-error' : 'text-muted'">{{ percent(row.original.calls_30d ? row.original.errors_30d / row.original.calls_30d : 0, 1) }}</span>
      </template>
      <template #avg_ms-cell="{ row }"><span class="text-muted tabular-nums">{{ row.original.avg_ms == null ? '–' : t('dataSources.ms', { n: row.original.avg_ms }) }}</span></template>
      <template #last_call_at-cell="{ row }">
        <UTooltip v-if="row.original.last_call_at" :text="dateTime(row.original.last_call_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_call_at) }}</span></UTooltip>
        <span v-else class="text-muted">{{ t('apiService.neverCalled') }}</span>
      </template>
      <template #updated_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span></template>
      <template #empty-actions>
        <UButton v-if="can('api.endpoints')" :label="t('apiService.actions.newEndpoint')" icon="i-lucide-plus" color="neutral" :to="newLink" />
      </template>
      <template #grid-card="{ row }">
        <ApiEndpointsCard :item="row" :actions="rowActions(row)" :busy="actions.busy.value === row.id" />
      </template>
    </DataView>

    <ApiEndpointsDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!actions.busy.value" @go="go" @status="setStatus" @remove="remove" @copy="actions.copyUrl" />
  </AppPanel>
</template>

<!--
  API service → Services (F13 M1; locked list format, rule 21): groups of endpoints, e.g. one per
  app or partner. Two chart cards (calls in the last 30 days; services by status, the legend
  filters), then DataView (table / cards) with status filter, search and sort. A row or card opens
  its panel (`?service=`); ⋯ / right-click: open, new endpoint, edit, on / off, duplicate, delete.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiInsights, ApiService } from '#shared/types/apiService'

definePageMeta({ breadcrumb: 'nav.apiServices' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { relative, dateTime, number, percent } = useFormat()
useHead({ title: () => t('nav.apiServices') })
const { can } = useCan()

const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ApiService[]> } }>('view')
const panel = useTemplateRef<{ reload: () => void }>('panel')
const insights = ref<ApiInsights | null>(null)
async function loadInsights() {
  try {
    insights.value = (await api.get<ApiInsights>('/api-services/insights', undefined, { background: !!insights.value })).data
  } catch {
    insights.value ??= null
  }
}
onMounted(loadInsights)
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights(), panel.value?.reload()])
const actions = useApiActions(refreshAll)

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('apiService.col.service'), sortable: true, fixed: true },
  { key: 'status', label: t('apiService.col.status'), hideBelow: 'sm' },
  { key: 'endpoints_count', label: t('apiService.col.endpoints'), sortable: true, hideBelow: 'md' },
  { key: 'methods', label: t('apiService.col.methods'), hideBelow: 'lg' },
  { key: 'calls_30d', label: t('apiService.col.calls'), sortable: true },
  { key: 'errors_30d', label: t('apiService.col.errors'), sortable: true, hideBelow: 'lg' },
  { key: 'last_call_at', label: t('apiService.col.lastCall'), sortable: true, hideBelow: 'md' },
  { key: 'created_at', label: t('apiService.col.created'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('apiService.col.status'), icon: 'i-lucide-circle-dot', options: [{ value: 'active', label: t('status.active'), dot: 'bg-green-500' }, { value: 'disabled', label: t('status.disabled'), dot: 'bg-(--ui-border-accented)' }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('apiService.sort.calls'), value: '-calls_30d' },
  { label: t('apiService.sort.endpoints'), value: '-endpoints_count' },
  { label: t('apiService.sort.lastCall'), value: '-last_call_at' },
  { label: t('apiService.sort.created'), value: '-created_at' },
])
const fetcher: DataFetcher<ApiService> = (params, signal) => api.list<ApiService>('/api-services', params, { signal })
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const pickStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

// The panel (`?service=`)
const openId = computed(() => (typeof route.query.service === 'string' ? route.query.service : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, service: undefined } }) })
const ids = computed(() => (view.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: ApiService) => void router.replace({ query: { ...route.query, service: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, service: id } })

// New / edit
const editOpen = ref(false)
const editing = ref<ApiService | null>(null)
function edit(service: ApiService | null) {
  editing.value = service
  editOpen.value = true
}
// `?new=1` (rail + menu, the setup guide) opens New service
watch(() => route.query.new, value => {
  if (!value) return
  if (can('api.service_create')) edit(null)
  void router.replace({ query: { ...route.query, new: undefined } })
}, { immediate: true })
async function saved(service: ApiService) {
  if (editing.value) useToast().add({ title: t('apiService.toast.serviceSaved', { name: service.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await refreshAll()
}
async function duplicate(service: ApiService) {
  const copy = await actions.duplicateService(service)
  if (copy) openRow(copy)
}
async function remove(service: ApiService) {
  if ((await actions.deleteService(service)) && openId.value === service.id) panelOpen.value = false
}
const setStatus = (service: ApiService, active: boolean) => void actions.setServiceStatus(service, active ? 'active' : 'disabled')
// Only what the role allows (F22 R2 M4): edit / delete per service (its `can`), the rest by permission
const rowActions = (row: ApiService): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('apiService.actions.viewEndpoints'), icon: 'i-lucide-route', to: { path: '/api-service/endpoints', query: { service: row.id } } },
    ...(can('api.endpoints') ? [{ label: t('apiService.actions.newEndpoint'), icon: 'i-lucide-plus', to: { path: '/api-service/endpoints/new', query: { service: row.id } } }] : []),
  ],
  [
    ...(row.can?.edit ? [{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) }] : []),
    ...(row.can?.edit ? [{ label: row.status === 'active' ? t('apiService.actions.turnOff') : t('apiService.actions.turnOn'), icon: row.status === 'active' ? 'i-lucide-circle-pause' : 'i-lucide-circle-play', onSelect: () => setStatus(row, row.status !== 'active') }] : []),
    ...(can('api.service_create') ? [{ label: t('apiService.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => void duplicate(row) }] : []),
  ],
  row.can?.delete ? [{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }] : [],
].filter(group => group.length)
defineShortcuts({ n: { usingInput: false, handler: () => can('api.service_create') && edit(null) } })
</script>

<template>
  <AppPanel id="api-services" :title="t('nav.apiServices')" :subtitle="t('apiService.section.services')" subtitle-icon="i-lucide-boxes">
    <template #actions>
      <UButton v-if="can('api.endpoints')" :label="t('apiService.actions.newEndpoint')" icon="i-lucide-route" color="neutral" variant="outline" to="/api-service/endpoints/new" class="hidden sm:inline-flex" />
      <UButton v-if="can('api.service_create')" :label="t('apiService.service.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)">
        <template #trailing><UKbd value="N" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </template>

    <ApiOverview :insights="insights" by="status" :selected="statusFilter" :count="t('nav.apiServices')" @pick="pickStatus" />

    <DataView
      id="api-services"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      :row-actions="rowActions"
      :busy="row => actions.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t('apiService.searchServices')"
      empty-icon="i-lucide-boxes"
      :empty-title="t('apiService.emptyServices')"
      :empty-description="t('apiService.emptyServicesDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.calls_30d && row.original.errors_30d / row.original.calls_30d > 0.05" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('apiService.manyErrors')" />
            <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
          </span>
          <span v-if="row.original.description" class="max-w-80 truncate text-xs text-muted">{{ row.original.description }}</span>
        </div>
      </template>
      <template #status-cell="{ row }"><DataStatusBadge :status="row.original.status" /></template>
      <template #endpoints_count-cell="{ row }"><span class="tabular-nums">{{ t('apiService.endpointsCount', { n: number(row.original.endpoints_count) }, row.original.endpoints_count) }}</span></template>
      <template #methods-cell="{ row }"><ApiMethods :methods="row.original.methods" size="xs" /></template>
      <template #calls_30d-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-12 tabular-nums">{{ number(row.original.calls_30d) }}</span>
          <ChartsSparkline :values="(row.original as ApiService).daily.map(day => day.count)" :width="72" :height="20" class="hidden sm:block" />
        </div>
      </template>
      <template #errors_30d-cell="{ row }">
        <span class="tabular-nums" :class="row.original.calls_30d && row.original.errors_30d / row.original.calls_30d > 0.05 ? 'font-medium text-error' : 'text-muted'">{{ percent(row.original.calls_30d ? row.original.errors_30d / row.original.calls_30d : 0, 1) }}</span>
      </template>
      <template #last_call_at-cell="{ row }">
        <UTooltip v-if="row.original.last_call_at" :text="dateTime(row.original.last_call_at)"><span class="whitespace-nowrap text-muted">{{ relative(row.original.last_call_at) }}</span></UTooltip>
        <span v-else class="text-muted">{{ t('apiService.neverCalled') }}</span>
      </template>
      <template #created_at-cell="{ row }"><span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span></template>
      <template #empty-actions>
        <UButton v-if="can('api.service_create')" :label="t('apiService.service.newTitle')" icon="i-lucide-plus" color="neutral" @click="edit(null)" />
      </template>
      <template #grid-card="{ row }">
        <ApiServicesCard :item="row" :actions="rowActions(row)" :busy="actions.busy.value === row.id" />
      </template>
    </DataView>

    <ApiServicesDetail :id="openId" ref="panel" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" :busy="!!actions.busy.value" @go="go" @edit="edit" @status="setStatus" @duplicate="duplicate" @remove="remove" />
    <ApiServicesEditModal v-model:open="editOpen" :service="editing" @saved="saved" />
  </AppPanel>
</template>

<!--
  API service → Request logs (F13 M4; locked list format, rule 21): every call to your endpoints.
  Two chart cards (calls in 30 days; by result, the legend filters), then DataView (table / cards)
  with endpoint, result, method and live / test filters, a date range (last 7 days by default),
  search (address, IP, request id, error code, token) and sort; a call opens its panel (`?log=`).
  Settings: keep bodies (masked). Download: the calls shown, as CSV (no bodies, never tokens).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiEndpoint, ApiLogEntry, ApiLogInsights } from '#shared/types/apiService'
import { API_METHODS } from '#shared/utils/urls/public'

definePageMeta({ breadcrumb: 'nav.apiLogs' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const { relative, dateTime } = useFormat()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
useHead({ title: () => t('nav.apiLogs') })

const list = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: Ref<ApiLogEntry[]>; params: () => Record<string, string | number> } }>('list')
const insights = ref<ApiLogInsights | null>(null)
const endpoints = ref<ApiEndpoint[]>([])
onMounted(async () => {
  try {
    const [a, b] = await Promise.all([api.get<ApiLogInsights>('/api-logs/insights'), api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })])
    insights.value = a.data
    endpoints.value = b.data
  } catch {
    insights.value ??= null
  }
})

const columns = computed<DataColumn[]>(() => [
  { key: 'at', label: t('apiService.logs.col.at'), sortable: true, fixed: true },
  { key: 'path', label: t('apiService.logs.col.call') },
  { key: 'status', label: t('apiService.logs.col.status'), sortable: true },
  { key: 'duration_ms', label: t('apiService.logs.col.duration'), sortable: true, hideBelow: 'md' },
  { key: 'token', label: t('apiService.logs.col.token'), hideBelow: 'lg' },
  { key: 'caller', label: t('apiService.logs.col.caller'), hideBelow: 'lg' },
  { key: 'request_id', label: t('apiService.logs.requestId'), hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'endpoint', label: t('apiService.col.endpoint'), icon: 'i-lucide-route', options: endpoints.value.map(item => ({ value: item.id, label: `/${item.name}` })) },
  { key: 'class', label: t('apiService.logs.col.status'), icon: 'i-lucide-circle-dot', options: (['2xx', '4xx', '5xx'] as const).map(value => ({ value, label: t(`apiService.logs.class.${value}`), dot: value === '2xx' ? 'bg-green-500' : value === '4xx' ? 'bg-amber-500' : 'bg-red-500' })) },
  { key: 'method', label: t('apiService.col.methods'), icon: 'i-lucide-arrow-left-right', options: API_METHODS.map(value => ({ value, label: value })) },
  { key: 'mode', label: t('apiService.tokens.col.mode'), icon: 'i-lucide-flask-conical', options: [{ value: 'live', label: t('apiService.tokens.mode.live') }, { value: 'test', label: t('apiService.tokens.mode.test') }] },
])
const sortOptions = computed(() => [
  { label: t('apiService.logs.sort.newest'), value: '-at' },
  { label: t('apiService.logs.sort.slowest'), value: '-duration_ms' },
  { label: t('apiService.logs.sort.status'), value: '-status' },
])
const fetcher: DataFetcher<ApiLogEntry> = (params, signal) => api.list<ApiLogEntry>('/api-logs', params, { signal })
const classFilter = computed(() => (typeof route.query.class === 'string' && !route.query.class.includes(',') ? route.query.class : null))
const pickClass = (value: string) => void router.replace({ query: { ...route.query, class: classFilter.value === value ? undefined : value, page: undefined } })

// The panel (`?log=`)
const openId = computed(() => (typeof route.query.log === 'string' ? route.query.log : null))
const panelOpen = computed({ get: () => !!openId.value, set: value => !value && router.replace({ query: { ...route.query, log: undefined } }) })
const ids = computed(() => (list.value?.state.rows.value ?? []).map(row => row.id))
const openRow = (row: ApiLogEntry) => void router.replace({ query: { ...route.query, log: row.id } })
const go = (id: string) => void router.replace({ query: { ...route.query, log: id } })
const rowActions = (row: ApiLogEntry): DropdownMenuItem[][] => [
  [
    { label: t('apiService.actions.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    {
      label: t('apiService.logs.copyId'),
      icon: 'i-lucide-copy',
      onSelect: () => {
        void copy(row.request_id)
        toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
      },
    },
    ...(row.endpoint ? [{ label: t('apiService.logs.openEndpoint'), icon: 'i-lucide-route', to: { path: '/api-service/endpoints', query: { endpoint: row.endpoint.id } } }] : []),
  ],
]

// Download the calls in view (the filters, search and dates of the list), up to 1,000, as CSV
const { busy: downloading, run } = useBusy()
const download = () =>
  run(
    async () => {
      const params = { ...(list.value?.state.params() ?? {}), page_size: 100 }
      const rows: ApiLogEntry[] = []
      for (let page = 1; page <= 10; page++) {
        const { data, meta } = await api.list<ApiLogEntry>('/api-logs', { ...params, page })
        rows.push(...data)
        if (page >= meta.total_pages) break
      }
      const csv = analyticsCsv([
        [t('apiService.logs.col.at'), t('apiService.col.methods'), t('apiService.logs.col.call'), t('apiService.logs.col.status'), t('apiService.logs.col.code'), t('apiService.logs.col.duration'), t('apiService.col.endpoint'), t('apiService.logs.col.token'), t('apiService.logs.col.caller'), t('apiService.logs.col.country'), t('apiService.logs.requestId')],
        ...rows.map(row => [row.at, row.method, row.path, row.status, row.code, row.duration_ms, row.endpoint?.name ?? null, row.token?.name ?? null, row.ip, row.country, row.request_id]),
      ])
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      link.download = `formalie-api-calls-${new Date().toISOString().slice(0, 10)}.csv`
      link.click()
      setTimeout(() => URL.revokeObjectURL(link.href), 1000)
    },
    { success: t('apiService.logs.downloaded') },
  )
const settingsOpen = ref(false)
</script>

<template>
  <AppPanel id="api-logs" :title="t('nav.apiLogs')" :subtitle="t('apiService.section.logs')" subtitle-icon="i-lucide-scroll-text">
    <template #actions>
      <UButton :label="t('apiService.logs.settings.title')" icon="i-lucide-settings-2" color="neutral" variant="outline" class="hidden sm:inline-flex" @click="settingsOpen = true" />
      <UButton :label="t('analytics.download')" icon="i-lucide-download" color="neutral" :loading="downloading" @click="download" />
    </template>

    <ApiLogsOverview :insights="insights" :klass="classFilter" @klass="pickClass" />

    <DataView
      id="api-logs"
      ref="list"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-at"
      date-range
      :row-actions="rowActions"
      :open-row="openRow"
      :search-placeholder="t('apiService.logs.search')"
      empty-icon="i-lucide-scroll-text"
      :empty-title="t('apiService.logs.empty')"
      :empty-description="t('apiService.logs.emptyDesc')"
    >
      <template #at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.at)"><span class="whitespace-nowrap text-muted tabular-nums">{{ relative(row.original.at) }}</span></UTooltip>
      </template>
      <template #path-cell="{ row }">
        <span class="flex min-w-0 items-center gap-2">
          <UBadge :label="row.original.method" color="neutral" variant="outline" size="xs" class="w-14 shrink-0 justify-center rounded-md font-mono" />
          <span class="max-w-80 truncate font-mono text-xs text-highlighted" dir="ltr">{{ row.original.path }}</span>
        </span>
      </template>
      <template #status-cell="{ row }">
        <span class="flex items-center gap-1.5">
          <ApiLogsStatus :status="row.original.status" :code="row.original.code" />
          <span v-if="row.original.code" class="hidden font-mono text-[11px] text-muted xl:inline">{{ row.original.code }}</span>
        </span>
      </template>
      <template #duration_ms-cell="{ row }"><span class="tabular-nums" :class="row.original.duration_ms > 1000 ? 'font-medium text-warning' : 'text-muted'">{{ t('dataSources.ms', { n: row.original.duration_ms }) }}</span></template>
      <template #token-cell="{ row }">
        <span v-if="row.original.token" class="flex min-w-0 items-center gap-1.5">
          <span class="max-w-36 truncate">{{ row.original.token.name }}</span>
          <UBadge v-if="row.original.token.mode === 'test'" :label="t('apiService.tokens.mode.test')" color="neutral" variant="soft" size="xs" class="rounded-md" />
        </span>
        <span v-else class="text-muted">{{ t('apiService.logs.noToken') }}</span>
      </template>
      <template #caller-cell="{ row }">
        <span class="flex min-w-0 items-center gap-1.5">
          <UIcon :name="row.original.country ? `i-circle-flags-${row.original.country.toLowerCase()}` : 'i-lucide-globe'" class="size-4 shrink-0" />
          <span class="max-w-40 truncate font-mono text-xs" dir="ltr">{{ row.original.ip }}</span>
        </span>
      </template>
      <template #request_id-cell="{ row }"><span class="font-mono text-[11px] text-muted" dir="ltr">{{ row.original.request_id }}</span></template>
      <template #grid-card="{ row }">
        <ApiLogsCard :item="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <ApiLogsDetail :id="openId" v-model:open="panelOpen" :ids="ids.length ? ids : openId ? [openId] : []" @go="go" />
    <ApiLogsSettingsModal v-model:open="settingsOpen" />
  </AppPanel>
</template>

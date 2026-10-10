<!--
  Data sources → Saved queries (F12 M4 part 2; locked list format, rule 21): your saved statements
  and the ones shared with the workspace. Two chart cards (runs in the last 30 days; read vs change
  with a legend that filters), then DataView (table / locked card) with connection, sharing and kind
  filters, search and sort. A row or card opens it in the Query editor; ⋯ / right-click: open, edit,
  share, copy, delete (yours only).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DataSourceRow } from '#shared/types/datasources'
import type { SavedQuery, SavedQueryInsights } from '#shared/types/query'

definePageMeta({ breadcrumb: 'nav.dataSavedQueries' })
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
const { copy } = useClipboard({ legacy: true })
// Saving and changing saved queries needs data.saved (writing a new one also the editor, data.query)
const { can } = useCan()
const canNew = computed(() => can('data.saved') && can('data.query'))
useHead({ title: () => t('nav.dataSavedQueries') })

const view = useTemplateRef<{ refresh: () => Promise<void> }>('view')
const insights = ref<SavedQueryInsights | null>(null)
const sources = ref<DataSourceRow[]>([])
async function loadInsights() {
  try {
    insights.value = (await api.get<SavedQueryInsights>('/saved-queries/insights')).data
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
const refreshAll = () => Promise.all([view.value?.refresh(), loadInsights()])

const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('query.saved.col.name'), sortable: true, fixed: true },
  { key: 'connection', label: t('destinations.col.connection'), hideBelow: 'md' },
  { key: 'kind', label: t('query.saved.col.kind'), hideBelow: 'sm' },
  { key: 'shared', label: t('query.saved.col.sharing'), hideBelow: 'lg' },
  { key: 'run_count', label: t('query.saved.col.runs'), sortable: true, hideBelow: 'sm' },
  { key: 'last_run_at', label: t('query.saved.col.lastRun'), sortable: true, hideBelow: 'lg' },
  { key: 'updated_at', label: t('query.saved.col.updated'), sortable: true, hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'datasource', label: t('destinations.col.connection'), icon: 'i-lucide-database', options: sources.value.map(source => ({ value: source.id, label: source.name })) },
  { key: 'scope', label: t('query.saved.col.sharing'), icon: 'i-lucide-users', options: [{ value: 'mine', label: t('query.saved.filterMine') }, { value: 'shared', label: t('query.saved.sharedShort') }] },
  { key: 'kind', label: t('query.saved.col.kind'), icon: 'i-lucide-square-terminal', options: [{ value: 'read', label: t('query.saved.kindRead') }, { value: 'change', label: t('query.saved.kindChange') }] },
])
const sortOptions = computed(() => [
  { label: t('forms.sortName'), value: 'name' },
  { label: t('query.saved.sortMostRun'), value: '-run_count' },
  { label: t('query.saved.sortRecentRun'), value: '-last_run_at' },
  { label: t('query.saved.sortChanged'), value: '-updated_at' },
])
const fetcher: DataFetcher<SavedQuery> = (params, signal) => api.list<SavedQuery>('/saved-queries', params, { signal })

const kindFilter = computed(() => (typeof route.query.kind === 'string' && !route.query.kind.includes(',') ? route.query.kind : null))
const filterKind = (kind: string) => void router.replace({ query: { ...route.query, kind: kindFilter.value === kind ? undefined : kind, page: undefined } })

const openRow = (row: SavedQuery) => void navigateTo({ path: '/data-sources/query', query: { ds: row.datasource.id, saved: row.id } })

// Changing yours: edit (name, description, sharing), share, delete
const saved = useSavedQueries(ref(null))
const editOpen = ref(false)
const editBusy = ref(false)
const editing = ref<SavedQuery | null>(null)
function edit(row: SavedQuery) {
  editing.value = row
  editOpen.value = true
}
async function saveEdit(values: { name: string; description: string | null; shared: boolean }) {
  if (!editing.value) return
  editBusy.value = true
  try {
    const data = await saved.update(editing.value.id, values)
    toast.add({ title: t('query.saved.updated', { name: data.name }), color: 'success', icon: 'i-lucide-circle-check' })
    editOpen.value = false
    await refreshAll()
  } catch (error) {
    handle(error)
  } finally {
    editBusy.value = false
  }
}
async function share(row: SavedQuery) {
  await saved.toggleShare(row)
  await refreshAll()
}
async function remove(row: SavedQuery) {
  if (await saved.remove(row)) await refreshAll()
}
function copySql(row: SavedQuery) {
  void copy(row.sql)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
const rowActions = (row: SavedQuery): DropdownMenuItem[][] => [
  [
    { label: t('query.saved.openEditor'), icon: 'i-lucide-square-terminal', onSelect: () => openRow(row) },
    { label: t('contextMenu.copy'), icon: 'i-lucide-copy', onSelect: () => copySql(row) },
  ],
  ...(row.mine && can('data.saved')
    ? [
        [
          { label: t('query.saved.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(row) },
          { label: row.shared ? t('query.saved.unshare') : t('query.saved.share'), icon: row.shared ? 'i-lucide-lock' : 'i-lucide-users', onSelect: () => void share(row) },
        ],
        [{ label: t('query.saved.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(row) }],
      ]
    : []),
]
</script>

<template>
  <AppPanel id="data-saved-queries" :title="t('nav.dataSavedQueries')" :subtitle="t('dataSources.section.savedQueries')" subtitle-icon="i-lucide-bookmark">
    <template #actions>
      <UButton v-if="canNew" :label="t('query.saved.new')" icon="i-lucide-plus" color="neutral" to="/data-sources/query" />
    </template>

    <QuerySavedOverview :insights="insights" :kind="kindFilter" @kind="filterKind" />

    <DataView
      id="data-saved-queries"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="name"
      :row-actions="rowActions"
      :busy="row => saved.busy.value === row.id"
      :open-row="openRow"
      :search-placeholder="t('query.saved.search')"
      empty-icon="i-lucide-bookmark"
      :empty-title="t('query.saved.emptyTitle')"
      :empty-description="t('query.saved.emptyDesc')"
    >
      <template #name-cell="{ row }">
        <div class="flex min-w-0 flex-col">
          <span class="flex min-w-0 items-center gap-1.5">
            <UIcon v-if="row.original.kind !== 'read'" name="i-lucide-flag" class="size-3.5 shrink-0 text-warning" :aria-label="t('query.saved.kindChange')" />
            <span class="truncate font-medium text-highlighted">{{ row.original.name }}</span>
          </span>
          <span v-if="row.original.description" class="truncate text-xs text-muted">{{ row.original.description }}</span>
        </div>
      </template>
      <template #connection-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2">
          <DatasourcesEngineLogo :engine="row.original.datasource.engine" size="sm" />
          <span class="truncate">{{ row.original.datasource.name }}</span>
        </div>
      </template>
      <template #kind-cell="{ row }">
        <UBadge :label="t(`query.kind.${row.original.kind}`)" color="neutral" variant="outline" size="sm" class="rounded-md" />
      </template>
      <template #shared-cell="{ row }">
        <span class="flex min-w-0 items-center gap-1.5 text-sm">
          <UIcon :name="row.original.shared ? 'i-lucide-users' : 'i-lucide-lock'" class="size-3.5 shrink-0 text-muted" />
          <span class="truncate">{{ row.original.shared ? t('query.saved.sharedShort') : t('query.saved.personal') }}</span>
          <span v-if="!row.original.mine" class="truncate text-xs text-muted">· {{ row.original.owner.name }}</span>
        </span>
      </template>
      <template #run_count-cell="{ row }">
        <div class="flex items-center gap-2">
          <span class="w-10 tabular-nums">{{ number(row.original.run_count) }}</span>
          <ChartsSparkline :values="(row.original as SavedQuery).daily.map(day => day.count)" :width="72" :height="20" />
        </div>
      </template>
      <template #last_run_at-cell="{ row }">
        <UTooltip v-if="row.original.last_run_at" :text="dateTime(row.original.last_run_at)">
          <span class="whitespace-nowrap text-muted">{{ relative(row.original.last_run_at) }}</span>
        </UTooltip>
        <span v-else class="text-muted">–</span>
      </template>
      <template #updated_at-cell="{ row }">
        <span class="whitespace-nowrap text-muted">{{ relative(row.original.updated_at) }}</span>
      </template>
      <template #empty-actions>
        <UButton v-if="canNew" :label="t('query.saved.new')" icon="i-lucide-plus" color="neutral" to="/data-sources/query" />
      </template>
      <template #grid-card="{ row }">
        <QuerySavedCard :item="row" :actions="rowActions(row)" />
      </template>
    </DataView>

    <QuerySaveModal v-if="can('data.saved')" v-model:open="editOpen" v-model:busy="editBusy" :sql="editing?.sql ?? ''" :connection="editing?.datasource.name ?? ''" :existing="editing" @save="saveEdit" />
  </AppPanel>
</template>

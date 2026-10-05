<!--
  Responses → Exports (F11 M3): every response export this person may see, in the shared DataView
  (rule 21 table / card; no chart cards, a utility list like Templates and Themes): file, form,
  format, which responses, rows, state, who made it, when, available until. Filter by format and
  state, search by file or form. A ready file downloads over a one-time private link; files are
  kept 7 days; remove deletes one for good. Exports being made update in the background.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ResponseExport } from '#shared/types/responses'

definePageMeta({ breadcrumb: 'nav.responsesExports' })
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()
useHead({ title: () => t('nav.responsesExports') })

const ICON = { xlsx: 'i-lucide-file-spreadsheet', csv: 'i-lucide-file-text', pdf: 'i-lucide-file-type' } as const
const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: { value: ResponseExport[] } } }>('view')
const columns = computed<DataColumn[]>(() => [
  { key: 'file_name', label: t('responses.exports.col.file'), fixed: true },
  { key: 'status', label: t('responses.exports.col.status') },
  { key: 'rows', label: t('responses.exports.col.rows'), hideBelow: 'sm' },
  { key: 'scope', label: t('responses.exports.col.scope'), hideBelow: 'lg' },
  { key: 'created_by', label: t('responses.exports.col.by'), hideBelow: 'lg' },
  { key: 'created_at', label: t('responses.exports.col.made'), sortable: true, hideBelow: 'sm' },
  { key: 'expires_at', label: t('responses.exports.available'), hideBelow: 'md' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'format', label: t('responses.export.formatLabel'), icon: 'i-lucide-file', options: (['xlsx', 'csv', 'pdf'] as const).map(value => ({ value, label: t(`responses.export.format.${value}`) })) },
  { key: 'status', label: t('responses.exports.col.status'), icon: 'i-lucide-circle-dot', options: (['ready', 'running', 'expired'] as const).map(value => ({ value, label: t(`responses.exports.status.${value}`) })) },
])
const sortOptions = computed(() => [
  { label: t('responses.list.newest'), value: '-created_at' },
  { label: t('responses.list.oldest'), value: 'created_at' },
])
const fetcher: DataFetcher<ResponseExport> = (params, signal) => api.list<ResponseExport>('/responses/exports', params, { signal })

// Exports being made: their progress in the background, without the page's loading bar.
let timer: ReturnType<typeof setInterval> | null = null
async function follow() {
  const rows = view.value?.state.rows.value ?? []
  const busyRows = rows.filter(row => row.status === 'queued' || row.status === 'running')
  if (!busyRows.length) return
  try {
    const fresh = await Promise.all(busyRows.map(row => api.get<ResponseExport>(`/responses/exports/${row.id}`, undefined, { background: true }).then(result => result.data)))
    const byId = new Map(fresh.map(item => [item.id, item]))
    if (view.value) view.value.state.rows.value = rows.map(row => byId.get(row.id) ?? row)
  } catch {
    // The next tick tries again.
  }
}
onMounted(() => (timer = setInterval(follow, 1000)))
onBeforeUnmount(() => timer && clearInterval(timer))

const busyIds = ref(new Set<string>())
async function withBusy(item: ResponseExport, work: () => Promise<void>) {
  busyIds.value = new Set([...busyIds.value, item.id])
  try {
    await work()
  } catch (error) {
    handle(error)
  } finally {
    busyIds.value = new Set([...busyIds.value].filter(id => id !== item.id))
  }
}
const download = (item: ResponseExport) =>
  withBusy(item, async () => {
    const { data } = await api.post<{ url: string }>(`/responses/exports/${item.id}/link`)
    window.location.assign(data.url)
  })
async function remove(item: ResponseExport) {
  if (!(await confirm({ title: t('responses.exports.deleteTitle', { name: item.file_name }), description: t('responses.exports.deleteDesc'), danger: true }))) return
  await withBusy(item, async () => {
    await api.del(`/responses/exports/${item.id}`)
    toast.add({ title: t('responses.exports.deleted'), color: 'success', icon: 'i-lucide-circle-check' })
    await view.value?.refresh()
  })
}
const rowActions = (item: ResponseExport): DropdownMenuItem[][] => [
  [
    ...(item.status === 'ready' ? [{ label: t('responses.export.download'), icon: 'i-lucide-download', onSelect: () => void download(item) }] : []),
    { label: t('responses.exports.openForm'), icon: 'i-lucide-inbox', to: `/forms/${item.form.id}/responses` },
  ],
  [{ label: t('responses.exports.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(item) }],
]
const openRow = (item: ResponseExport) => (item.status === 'ready' ? void download(item) : undefined)
</script>

<template>
  <AppPanel id="responses-exports" :title="t('nav.responsesExports')" :subtitle="t('responses.exports.subtitle')" subtitle-icon="i-lucide-file-down">
    <template #actions>
      <UButton :label="t('nav.responses')" icon="i-lucide-inbox" color="neutral" variant="outline" to="/responses" />
    </template>

    <DataView
      id="responses-exports"
      ref="view"
      :columns="columns"
      :fetcher="fetcher"
      :filters="filters"
      :sort-options="sortOptions"
      default-sort="-created_at"
      :row-actions="rowActions"
      :busy="row => busyIds.has(row.id)"
      :open-row="openRow"
      :search-placeholder="t('responses.exports.search')"
      empty-icon="i-lucide-file-down"
      :empty-title="t('responses.exports.emptyTitle')"
      :empty-description="t('responses.exports.emptyDesc')"
    >
      <template #file_name-cell="{ row }">
        <div class="flex min-w-0 items-center gap-2.5">
          <UIcon :name="ICON[row.original.format as ResponseExport['format']]" class="size-4 shrink-0 text-muted" />
          <div class="flex min-w-0 flex-col">
            <span class="truncate font-medium text-highlighted">{{ row.original.file_name }}</span>
            <span class="truncate text-xs text-muted">{{ row.original.form.name }}</span>
          </div>
        </div>
      </template>
      <template #status-cell="{ row }">
        <div v-if="row.original.status === 'queued' || row.original.status === 'running'" class="flex w-28 items-center gap-2">
          <UProgress :model-value="row.original.progress" color="neutral" size="xs" class="flex-1" />
          <span class="text-xs text-muted tabular-nums">{{ row.original.progress }}%</span>
        </div>
        <DataStatusBadge v-else :status="row.original.status" :label="t(`responses.exports.status.${row.original.status}`)" />
      </template>
      <template #rows-cell="{ row }">
        <span class="tabular-nums">{{ number(row.original.rows) }}</span>
      </template>
      <template #scope-cell="{ row }">
        <span>{{ t(`responses.exports.scope.${row.original.scope}`) }}</span>
      </template>
      <template #created_by-cell="{ row }">
        <UUser :name="row.original.created_by.name" :avatar="{ alt: row.original.created_by.name }" size="xs" />
      </template>
      <template #created_at-cell="{ row }">
        <UTooltip :text="dateTime(row.original.created_at)">
          <span class="whitespace-nowrap text-muted">{{ relative(row.original.created_at) }}</span>
        </UTooltip>
      </template>
      <template #expires_at-cell="{ row }">
        <span class="whitespace-nowrap" :class="row.original.status === 'expired' ? 'text-dimmed' : 'text-muted'">{{ row.original.status === 'expired' ? t('responses.exports.status.expired') : relative(row.original.expires_at) }}</span>
      </template>
      <template #empty-actions>
        <UButton :label="t('nav.responses')" icon="i-lucide-inbox" color="neutral" to="/responses" />
      </template>
      <template #grid-card="{ row }">
        <FormsResponsesExportCard :item="row" :actions="rowActions(row)" :busy="busyIds.has(row.id)" @download="download(row)" />
      </template>
    </DataView>
  </AppPanel>
</template>

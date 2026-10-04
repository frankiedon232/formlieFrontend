<!--
  The inbox list (F11): responses from every form the person may see, newest first, in the shared
  DataView: respondent, form, submitted, status, how it came in. Filters: form, status, channel,
  possible duplicates. A row opens the response; bulk: set status.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormSummary } from '#shared/types/forms'
import { RESPONSE_STATUSES, type ResponseRow, type ResponseStatus } from '#shared/types/responses'

const emit = defineEmits<{ open: [row: ResponseRow, rows: ResponseRow[]]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const toast = useToast()
const { relative, dateTime } = useFormat()
const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: { value: ResponseRow[] } } }>('view')

// Forms to filter by (those with responses first come from the list, sorted by name).
const forms = ref<{ value: string; label: string }[]>([])
onMounted(async () => {
  try {
    const { data } = await api.list<FormSummary>('/forms', { page_size: 100, sort: 'name' }, { background: true })
    forms.value = data.filter(form => form.responses_count > 0).map(form => ({ value: form.id, label: form.name }))
  } catch {
    forms.value = []
  }
})

const columns = computed<DataColumn[]>(() => [
  { key: 'respondent', label: t('responses.list.respondent'), sortable: true },
  { key: 'form', label: t('responses.list.form'), sortable: true, hideBelow: 'md' },
  { key: 'submitted_at', label: t('responses.list.submitted'), sortable: true, hideBelow: 'sm' },
  { key: 'status', label: t('responses.list.status'), sortable: true },
  { key: 'channel', label: t('responses.list.channel'), hideBelow: 'lg' },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'form', label: t('responses.list.form'), icon: 'i-lucide-file-text', options: forms.value },
  { key: 'status', label: t('responses.list.status'), icon: 'i-lucide-circle-dot', options: RESPONSE_STATUSES.map(value => ({ value, label: t(`status.${value}`), dot: RESPONSE_STATUS_META[value].fill })) },
  { key: 'channel', label: t('responses.list.channel'), icon: 'i-lucide-route', options: (['link', 'embed', 'api'] as const).map(value => ({ value, label: t(`responses.channel.${value}`) })) },
  { key: 'flag', label: t('responses.list.flags'), icon: 'i-lucide-flag', options: [{ value: 'duplicate', label: t('responses.list.possibleDuplicate') }] },
])
const sortOptions = computed(() => [
  { label: t('responses.list.newest'), value: '-submitted_at' },
  { label: t('responses.list.oldest'), value: 'submitted_at' },
  { label: t('responses.list.byForm'), value: 'form' },
  { label: t('responses.list.byStatus'), value: 'status' },
])
const fetcher: DataFetcher<ResponseRow> = (params, signal) => api.list<ResponseRow>('/responses', params, { signal })

const busyIds = ref(new Set<string>())
async function mark(ids: string[], status: ResponseStatus, after?: () => void) {
  busyIds.value = new Set([...busyIds.value, ...ids])
  try {
    const { data } = await api.post<{ done: number }>('/responses/bulk', { ids, action: 'status', value: status })
    toast.add({ title: t('responses.toast.marked', { n: data.done, status: t(`status.${status}`) }, data.done), color: 'success', icon: 'i-lucide-circle-check' })
    after?.()
    await view.value?.refresh()
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busyIds.value = new Set([...busyIds.value].filter(id => !ids.includes(id)))
  }
}
const statusItems = (ids: string[], after?: () => void): DropdownMenuItem[] =>
  RESPONSE_STATUSES.map(status => ({ label: t(`status.${status}`), icon: RESPONSE_STATUS_META[status].icon, onSelect: () => void mark(ids, status, after) }))
const rowActions = (row: ResponseRow): DropdownMenuItem[][] => [
  [
    { label: t('responses.list.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) },
    { label: t('responses.list.allOfForm'), icon: 'i-lucide-table-2', to: `/forms/${row.form.id}/responses` },
  ],
  [{ type: 'label', label: t('responses.list.markAs') }, ...statusItems([row.id]).filter((_, i) => RESPONSE_STATUSES[i] !== row.status)],
]
const openRow = (row: ResponseRow) => emit('open', row, view.value?.state.rows.value ?? [row])
defineExpose({ refresh: () => view.value?.refresh() })
</script>

<template>
  <DataView
    id="responses-inbox"
    ref="view"
    :columns="columns"
    :fetcher="fetcher"
    :filters="filters"
    :sort-options="sortOptions"
    default-sort="-submitted_at"
    date-range
    selectable
    :row-actions="rowActions"
    :busy="row => busyIds.has(row.id)"
    :open-row="openRow"
    :search-placeholder="t('responses.list.searchInbox')"
    empty-icon="i-lucide-inbox"
    :empty-title="t('responses.list.empty')"
    :empty-description="t('responses.list.emptyInbox')"
  >
    <template v-if="$slots.start" #toolbar-start>
      <slot name="start" />
    </template>
    <template #respondent-cell="{ row }">
      <FormsResponsesWho :row="row.original" @open="openRow(row.original)" />
    </template>
    <template #form-cell="{ row }">
      <NuxtLink :to="`/forms/${row.original.form.id}/responses`" class="block max-w-60 truncate text-default hover:underline">{{ row.original.form.name }}</NuxtLink>
      <span class="text-xs text-muted tabular-nums">#{{ row.original.number }}</span>
    </template>
    <template #submitted_at-cell="{ row }">
      <UTooltip :text="dateTime(row.original.submitted_at)">
        <span class="whitespace-nowrap text-muted">{{ relative(row.original.submitted_at) }}</span>
      </UTooltip>
    </template>
    <template #status-cell="{ row }">
      <DataStatusBadge :status="row.original.status" />
    </template>
    <template #channel-cell="{ row }">
      <span class="text-muted">{{ t(`responses.channel.${row.original.channel}`) }}</span>
    </template>

    <template #grid-card="{ row }">
      <FormsResponsesCard :row="row" :fields="[]" :actions="rowActions(row)" @open="openRow(row)" />
    </template>

    <template #bulk-actions="{ selected, clear }">
      <UDropdownMenu :items="statusItems(selected.map(row => row.id), clear)">
        <UButton :label="t('responses.list.markAs')" icon="i-lucide-circle-dot" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" />
      </UDropdownMenu>
    </template>
  </DataView>
</template>

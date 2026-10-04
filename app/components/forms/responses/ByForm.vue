<!--
  The Responses page list, grouped by form (owner 2026-10-04: forms first, responses only inside a
  form). DataView (rule 21): form, form status, new, responses, reviewed so far, 30-day trend, last
  response, owner; filters: review status (forms with new / reviewed… responses), form status,
  folder; sort: most new, latest response, most responses, name. A form opens its Responses page,
  filtered to the review status asked for.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormFolder } from '#shared/types/forms'
import { RESPONSE_STATUSES, type ResponseFormRow } from '#shared/types/responses'

const { t } = useI18n()
const api = useApi()
const route = useRoute()
const { relative, dateTime, number, percent } = useFormat()

const folders = ref<FormFolder[]>([])
onMounted(async () => {
  try {
    folders.value = (await api.get<FormFolder[]>('/folders', undefined, { background: true })).data
  } catch {
    folders.value = []
  }
})

const FORM_DOTS: Record<string, string> = { draft: 'bg-amber-500', published: 'bg-green-500', closed: 'bg-violet-600', archived: 'bg-(--ui-text-dimmed)' }
const columns = computed<DataColumn[]>(() => [
  { key: 'name', label: t('responses.list.form'), sortable: true, fixed: true },
  { key: 'status', label: t('forms.col.status'), hideBelow: 'md' },
  { key: 'new', label: t('status.new'), sortable: true },
  { key: 'total', label: t('forms.col.responses'), sortable: true, hideBelow: 'sm' },
  { key: 'reviewed', label: t('responses.byForm.reviewed'), hideBelow: 'lg' },
  { key: 'trend', label: t('responses.byForm.trend'), hideBelow: 'lg' },
  { key: 'last_at', label: t('responses.kpi.last'), sortable: true, hideBelow: 'sm' },
  { key: 'owner', label: t('forms.col.owner'), hideBelow: 'lg', hidden: true },
])
const filters = computed<DataFilter[]>(() => [
  { key: 'review', label: t('responses.byForm.withStatus'), icon: 'i-lucide-circle-dot', options: RESPONSE_STATUSES.map(value => ({ value, label: t(`status.${value}`), dot: RESPONSE_STATUS_META[value].fill })) },
  { key: 'form_status', label: t('forms.filterStatus'), icon: 'i-lucide-file-text', options: Object.keys(FORM_DOTS).map(value => ({ value, label: t(`status.${value}`), dot: FORM_DOTS[value] })) },
  { key: 'folder_id', label: t('forms.filterFolder'), icon: 'i-lucide-folder', options: [{ value: 'none', label: t('forms.noFolder') }, ...folders.value.map(folder => ({ value: folder.id, label: folder.name }))] },
])
const sortOptions = computed(() => [
  { label: t('responses.byForm.mostNew'), value: '-new' },
  { label: t('responses.byForm.latest'), value: '-last_at' },
  { label: t('responses.byForm.most'), value: '-total' },
  { label: t('forms.sortName'), value: 'name' },
])
const fetcher: DataFetcher<ResponseFormRow> = (params, signal) => api.list<ResponseFormRow>('/responses/forms', params, { signal })

/** Open a form's responses, filtered to the one review status asked for (sidebar New / Reviewed…). */
const reviewAsked = computed(() => (typeof route.query.review === 'string' && !route.query.review.includes(',') ? route.query.review : null))
const target = (row: ResponseFormRow) => `/forms/${row.id}/responses${reviewAsked.value ? `?status=${reviewAsked.value}` : ''}`
const rowActions = (row: ResponseFormRow): DropdownMenuItem[][] => [
  [
    { label: t('responses.byForm.openResponses'), icon: 'i-lucide-inbox', to: target(row) },
    { label: t('responses.tabs.summary'), icon: 'i-lucide-chart-no-axes-combined', to: `/forms/${row.id}/responses?view=insights` },
    { label: t('responses.byForm.openForm'), icon: 'i-lucide-file-text', to: `/forms/${row.id}` },
  ],
]
const reviewedShare = (row: ResponseFormRow) => (row.total ? (row.total - row.status_counts.new) / row.total : 0)
</script>

<template>
  <DataView
    id="responses-by-form"
    :columns="columns"
    :fetcher="fetcher"
    :filters="filters"
    :sort-options="sortOptions"
    default-sort="-new"
    default-view="grid"
    :row-actions="rowActions"
    :open-row="row => navigateTo(target(row))"
    :search-placeholder="t('responses.byForm.search')"
    empty-icon="i-lucide-inbox"
    :empty-title="t('responses.list.empty')"
    :empty-description="t('responses.list.emptyInbox')"
  >
    <template v-if="$slots.start" #toolbar-start>
      <slot name="start" />
    </template>
    <template #name-cell="{ row }">
      <div class="flex min-w-0 items-center gap-1.5">
        <UTooltip v-if="row.original.status_counts.new" :text="t('responses.byForm.newWaiting', { n: number(row.original.status_counts.new) }, row.original.status_counts.new)">
          <UIcon name="i-lucide-flag" class="size-3.5 shrink-0 text-error" />
        </UTooltip>
        <div class="flex min-w-0 flex-col">
          <NuxtLink :to="target(row.original)" class="truncate font-medium text-highlighted hover:underline">{{ row.original.name }}</NuxtLink>
          <span class="truncate text-xs text-muted">{{ row.original.folder?.name ?? t('forms.noFolder') }}</span>
        </div>
      </div>
    </template>
    <template #status-cell="{ row }">
      <DataStatusBadge :status="row.original.status" />
    </template>
    <template #new-cell="{ row }">
      <UBadge v-if="row.original.status_counts.new" :label="number(row.original.status_counts.new)" color="neutral" variant="solid" size="sm" class="rounded-md tabular-nums" />
      <span v-else class="text-muted">0</span>
    </template>
    <template #total-cell="{ row }">
      <span class="tabular-nums">{{ number(row.original.total) }}</span>
    </template>
    <template #reviewed-cell="{ row }">
      <div class="flex min-w-32 items-center gap-2">
        <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${reviewedShare(row.original) * 100}%` }" /></div>
        <span class="w-9 text-end text-xs tabular-nums">{{ percent(reviewedShare(row.original)) }}</span>
      </div>
    </template>
    <template #trend-cell="{ row }">
      <ChartsSparkline :values="row.original.daily" :width="80" :height="22" />
    </template>
    <template #last_at-cell="{ row }">
      <UTooltip v-if="row.original.last_at" :text="dateTime(row.original.last_at)">
        <span class="whitespace-nowrap text-muted">{{ relative(row.original.last_at) }}</span>
      </UTooltip>
    </template>
    <template #owner-cell="{ row }">
      <UUser :name="row.original.owner.name" :avatar="{ alt: row.original.owner.name }" size="xs" />
    </template>

    <template #grid-card="{ row }">
      <FormsResponsesFormCard :row="row" :actions="rowActions(row)" />
    </template>
  </DataView>
</template>

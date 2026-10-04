<!--
  A form's responses in the shared DataView (F11, CLAUDE.md rule 6): #, respondent, submitted,
  status, every question (the first four useful ones shown; move or show / hide any in Columns,
  remembered per form; ratings as slim bars like the design's progress column), notes. Filters: status, channel, possible duplicates, tags, and
  under "Questions" one per choice, yes / no or rating question plus "Left empty" (F11 M2); search covers
  the answers too. A row (or card) opens the response; bulk: set status, delete (editors).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { RESPONSE_STATUSES, type ResponseRow, type ResponseStatus } from '#shared/types/responses'
import { allFields, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { ANSWER_FILTER_PREFIX, filterValues } from '#shared/utils/forms/answer-filter'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ formId: string; schema: FormSchemaV1; canEdit: boolean }>()
const emit = defineEmits<{ open: [row: ResponseRow, rows: ResponseRow[]]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const { relative, dateTime, number } = useFormat()
const { text } = useResponseFormat()
const view = useTemplateRef<{ refresh: () => Promise<void>; state: { rows: { value: ResponseRow[] } } }>('view')

// ── Question columns: all of them, the first four useful ones shown (Columns moves / shows / hides)
const questions = computed(() => allFields(props.schema).filter(field => isInputField(field.type) && field.type !== 'payment'))
const byKey = computed(() => new Map(questions.value.map(field => [field.key, field])))
const shownFirst = computed(() => new Set(questions.value.filter(goodColumn).slice(0, 4).map(field => field.key)))

const columns = computed<DataColumn[]>(() => [
  { key: 'number', label: '#', sortable: true, class: 'w-16' },
  { key: 'respondent', label: t('responses.list.respondent'), sortable: true, fixed: true },
  { key: 'submitted_at', label: t('responses.list.submitted'), sortable: true, hideBelow: 'sm' },
  { key: 'status', label: t('responses.list.status'), sortable: true },
  ...questions.value.map(field => ({ key: `q_${field.key}`, label: field.label?.trim() || field.key, hideBelow: 'lg' as const, class: 'max-w-56', hidden: !shownFirst.value.has(field.key) })),
  { key: 'notes_count', label: t('responses.list.notes'), hideBelow: 'md', class: 'w-16' },
])
/** The card shows the first four questions shown in the table (same order). */
const cardFields = (shown: string[]) => shown.filter(key => key.startsWith('q_')).map(key => byKey.value.get(key.slice(2))!).filter(Boolean).slice(0, 4)
const fieldOf = (column: string): FormField | undefined => byKey.value.get(column.slice(2))
const meter = (field: FormField | undefined) => !!field && ['rating', 'scale', 'slider'].includes(field.type)
const maxOf = (field: FormField) => Number(field.props?.max ?? (field.type === 'rating' ? 5 : field.type === 'scale' ? 10 : 100))

// Tags in use on this form (for the Tags filter), loaded in the background.
const tags = ref<{ value: string; count: number }[]>([])
async function loadTags() {
  try {
    tags.value = (await api.get<{ value: string; count: number }[]>(`/forms/${props.formId}/responses/tags`, undefined, { background: true })).data
  } catch {
    tags.value = []
  }
}
watch(() => props.formId, loadTags, { immediate: true })

/** One filter per question with a short set of answers, labelled like the answers themselves. */
const questionFilters = computed<DataFilter[]>(() =>
  questions.value.flatMap(field => {
    const values = filterValues(field)
    if (!values) return []
    const label = (value: string) => (field.type === 'toggle' ? text(field, value === 'true') : field.options?.find(option => option.value === value)?.label ?? value)
    return [{ key: `${ANSWER_FILTER_PREFIX}${field.key}`, label: field.label?.trim() || field.key, options: values.map(value => ({ value, label: label(value) })), group: t('responses.filter.questions'), named: true }]
  }),
)
const filters = computed<DataFilter[]>(() => [
  { key: 'status', label: t('responses.list.status'), icon: 'i-lucide-circle-dot', options: RESPONSE_STATUSES.map(value => ({ value, label: t(`status.${value}`), dot: RESPONSE_STATUS_META[value].fill })) },
  { key: 'channel', label: t('responses.list.channel'), icon: 'i-lucide-route', options: (['link', 'embed', 'api'] as const).map(value => ({ value, label: t(`responses.channel.${value}`) })) },
  { key: 'flag', label: t('responses.list.flags'), icon: 'i-lucide-flag', options: [{ value: 'duplicate', label: t('responses.list.possibleDuplicate') }] },
  ...(tags.value.length ? [{ key: 'tag', label: t('responses.filter.tags'), icon: 'i-lucide-tag', options: tags.value.map(tag => ({ value: tag.value, label: `${tag.value} (${number(tag.count)})` })), named: true }] : []),
  ...questionFilters.value,
  { key: 'empty', label: t('responses.filter.empty'), icon: 'i-lucide-circle-dashed', options: questions.value.map(field => ({ value: field.key, label: field.label?.trim() || field.key })), group: t('responses.filter.questions'), named: true },
])
const sortOptions = computed(() => [
  { label: t('responses.list.newest'), value: '-submitted_at' },
  { label: t('responses.list.oldest'), value: 'submitted_at' },
  { label: t('responses.list.byStatus'), value: 'status' },
  { label: t('responses.list.byRespondent'), value: 'respondent' },
])
const fetcher: DataFetcher<ResponseRow> = (params, signal) => api.list<ResponseRow>(`/forms/${props.formId}/responses`, params, { signal })

// ── Actions (rows and bulk) ────────────────────────────────────────────────────────────
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const busyIds = ref(new Set<string>())
async function bulk(ids: string[], action: 'status' | 'delete', value?: ResponseStatus) {
  if (action === 'delete' && !(await confirm({ title: t('responses.delete.title', { n: ids.length }, ids.length), description: t('responses.delete.desc'), danger: true }))) return
  busyIds.value = new Set([...busyIds.value, ...ids])
  try {
    const { data } = await api.post<{ done: number; skipped: number }>('/responses/bulk', { ids, action, value })
    toast.add({ title: action === 'delete' ? t('responses.toast.deleted', { n: data.done }, data.done) : t('responses.toast.marked', { n: data.done, status: t(`status.${value}`) }, data.done), color: 'success', icon: 'i-lucide-circle-check' })
    await view.value?.refresh()
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    busyIds.value = new Set([...busyIds.value].filter(id => !ids.includes(id)))
  }
}
const statusItems = (ids: string[], after?: () => void): DropdownMenuItem[] =>
  RESPONSE_STATUSES.map(status => ({ label: t(`status.${status}`), icon: RESPONSE_STATUS_META[status].icon, onSelect: () => void bulk(ids, 'status', status).then(after) }))
const rowActions = (row: ResponseRow): DropdownMenuItem[][] => [
  [{ label: t('responses.list.open'), icon: 'i-lucide-panel-right-open', onSelect: () => openRow(row) }],
  [{ type: 'label', label: t('responses.list.markAs') }, ...statusItems([row.id]).filter((_, i) => RESPONSE_STATUSES[i] !== row.status)],
  ...(props.canEdit ? [[{ label: t('responses.list.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void bulk([row.id], 'delete') }]] : []),
]
const openRow = (row: ResponseRow) => emit('open', row, view.value?.state.rows.value ?? [row])

defineExpose({ refresh: () => view.value?.refresh(), rows: () => view.value?.state.rows.value ?? [] })
</script>

<template>
  <DataView
    :id="`responses-${formId}`"
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
    :search-placeholder="t('responses.list.search')"
    empty-icon="i-lucide-inbox"
    :empty-title="t('responses.list.empty')"
    :empty-description="t('responses.list.emptyDesc')"
  >

    <template #number-cell="{ row }">
      <span class="text-muted tabular-nums">#{{ row.original.number }}</span>
    </template>
    <template v-if="$slots.start" #toolbar-start>
      <slot name="start" />
    </template>
    <template #respondent-cell="{ row }">
      <FormsResponsesWho :row="row.original" @open="openRow(row.original)" />
    </template>
    <template #submitted_at-cell="{ row }">
      <UTooltip :text="dateTime(row.original.submitted_at)">
        <span class="whitespace-nowrap text-muted">{{ relative(row.original.submitted_at) }}</span>
      </UTooltip>
    </template>
    <template #status-cell="{ row }">
      <DataStatusBadge :status="row.original.status" />
    </template>
    <template v-for="key in byKey.keys()" :key="`h_${key}`" #[`q_${key}-header`]>
      <UTooltip :text="byKey.get(key)?.label || key">
        <span class="block max-w-44 truncate">{{ byKey.get(key)?.label || key }}</span>
      </UTooltip>
    </template>
    <template v-for="key in byKey.keys()" :key="key" #[`q_${key}-cell`]="{ row }">
      <div v-if="meter(fieldOf(`q_${key}`)) && row.original.answers[key] != null" class="flex w-28 items-center gap-2">
        <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${(Number(row.original.answers[key]) / maxOf(fieldOf(`q_${key}`)!)) * 100}%` }" />
        </div>
        <span class="text-xs text-muted tabular-nums">{{ number(Number(row.original.answers[key])) }}</span>
      </div>
      <span v-else class="block max-w-56 truncate text-default">{{ text(fieldOf(`q_${key}`), row.original.answers[key]) || '–' }}</span>
    </template>
    <template #notes_count-cell="{ row }">
      <span v-if="row.original.notes_count" class="inline-flex items-center gap-1 text-muted"><UIcon name="i-lucide-message-square" class="size-3.5" />{{ row.original.notes_count }}</span>
      <span v-else class="sr-only">0</span>
    </template>

    <template #grid-card="{ row, columns: shown }">
      <FormsResponsesCard :row="row" :fields="cardFields(shown)" :actions="rowActions(row)" @open="openRow(row)" />
    </template>

    <template #bulk-actions="{ selected, clear }">
      <UDropdownMenu :items="statusItems(selected.map(row => row.id), clear)">
        <UButton :label="t('responses.list.markAs')" icon="i-lucide-circle-dot" trailing-icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" />
      </UDropdownMenu>
      <UButton v-if="canEdit" :label="t('responses.list.delete')" icon="i-lucide-trash-2" color="error" variant="outline" size="sm" @click="bulk(selected.map(row => row.id), 'delete').then(clear)" />
    </template>
  </DataView>
</template>
